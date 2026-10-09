"""Backend-neutral descriptive summaries with explicit statistical conventions."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal, cast, overload

import narwhals as nw
import numpy as np
import scipy
from scipy import stats

from lss4py._kernels._helpers import build_provenance, require_columns
from lss4py.domain import AssumptionNote, DescriptiveResult
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis


def _warn(result: DescriptiveResult, code: str, message: str) -> None:
    """Attach a structured diagnostic to a summary."""
    result.provenance.warnings.append(AssumptionNote(code, message, severity="warning"))


def _options(ddof: int, percentiles: Sequence[float]) -> list[float]:
    """Validate options and always retain quartiles for the five-number summary."""
    if isinstance(ddof, bool) or not isinstance(ddof, int) or ddof not in (0, 1):
        raise ValidationError("ddof must be 0 (population) or 1 (sample).")
    try:
        levels = np.asarray(percentiles, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValidationError("percentiles must be numeric levels between 0 and 100.") from exc
    if levels.ndim != 1 or not np.all(np.isfinite(levels) & (levels >= 0) & (levels <= 100)):
        raise ValidationError("percentiles must be finite levels between 0 and 100.")
    return sorted(set(levels.tolist()) | {25.0, 50.0, 75.0})


def _measurements(frame: nw.DataFrame, column: str) -> np.ndarray:
    """Extract only a numeric measurement column; never coerce text or booleans."""
    require_columns(frame, column)
    series = frame[column]
    if series.null_count() == len(series):
        return np.full(len(series), np.nan)
    if not series.dtype.is_numeric():
        raise ValidationError(f"Column '{column}' must contain numeric measurements.")
    values = np.asarray(series.cast(nw.Float64).to_numpy(), dtype=float)
    if np.isinf(values).any():
        raise ValidationError(f"Column '{column}' contains infinity; correct it before analysis.")
    return values


def _group_value(value: Any) -> Any:
    """Normalize group identifiers to hashable JSON-compatible scalar values."""
    if value is None or isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and np.isfinite(value):
        return value
    raise ValidationError("Group identifiers must be finite scalars, dates, or missing values.")


def _groups(frame: nw.DataFrame, columns: list[str]) -> list[tuple[dict, list[int]]]:
    """Partition observations in first-seen order, retaining missing group identifiers."""
    groups: dict[tuple, list[int]] = {}
    selected = frame.select(columns)
    nulls = selected.select(nw.all().is_null())
    for index, (row, missing) in enumerate(
        zip(selected.iter_rows(), nulls.iter_rows(), strict=True)
    ):
        key = tuple(
            _group_value(None if is_null else value)
            for value, is_null in zip(row, missing, strict=True)
        )
        groups.setdefault(key, []).append(index)
    return [(dict(zip(columns, key, strict=True)), indices) for key, indices in groups.items()]


def _location(result: DescriptiveResult, values: np.ndarray, levels: list[float]) -> None:
    """Calculate location, robust spread, percentiles, and frequency summaries."""
    result.mean = float(np.mean(values))
    result.median = float(np.median(values))
    result.min_value = float(np.min(values))
    result.max_value = float(np.max(values))
    result.range = result.max_value - result.min_value
    result.mad = float(np.median(np.abs(values - result.median)))
    quantiles = np.percentile(values, levels, method="linear")
    result.percentiles = {
        f"p{level:g}": float(value) for level, value in zip(levels, quantiles, strict=True)
    }
    result.iqr = result.percentiles["p75"] - result.percentiles["p25"]
    unique, counts = np.unique(values, return_counts=True)
    result.unique_count = len(unique)
    result.mode_frequency = int(counts.max())
    if result.mode_frequency > 1:
        result.modes = unique[counts == result.mode_frequency].tolist()
    else:
        _warn(result, "NO_REPEATED_MODE", "All valid values are unique; no repeated-value mode.")


def _spread(result: DescriptiveResult, values: np.ndarray, ddof: int, scale: str) -> None:
    """Calculate classical spread and guard interpretation of relative variability."""
    if len(values) <= ddof:
        _warn(result, "INSUFFICIENT_SPREAD", "Standard deviation and variance need more data.")
        return
    result.variance = float(np.var(values, ddof=ddof))
    result.std = float(np.std(values, ddof=ddof))
    mean = cast(float, result.mean)  # _location populates the mean before spread is calculated.
    threshold = 1e-12 * float(np.max(np.abs(values)))
    if scale != "ratio" or mean <= threshold:
        _warn(
            result, "CV_UNAVAILABLE", "CV needs a ratio scale and a positive, non-negligible mean."
        )
    else:
        result.coefficient_of_variation = result.std / mean


def _shape(result: DescriptiveResult, values: np.ndarray, excess: bool) -> None:
    """Calculate bias-corrected shape only when sample size and variability suffice."""
    if np.all(values == values[0]):
        _warn(result, "CONSTANT_DATA", "Skewness and kurtosis are undefined for constant data.")
        return
    if np.max(np.abs(values - np.mean(values))) <= np.finfo(float).eps * abs(np.mean(values)):
        _warn(result, "NUMERICAL_SHAPE", "Variation is too small for reliable shape estimates.")
        return
    if len(values) >= 3:
        result.skew = float(stats.skew(values, bias=False))
    else:
        _warn(result, "INSUFFICIENT_SKEW", "Bias-corrected skewness needs at least 3 values.")
    if len(values) >= 4:
        result.kurtosis = float(stats.kurtosis(values, fisher=excess, bias=False))
    else:
        _warn(result, "INSUFFICIENT_KURTOSIS", "Bias-corrected kurtosis needs at least 4 values.")


def _summarize(
    frame: nw.DataFrame, values: np.ndarray, parameters: dict[str, Any], group_keys: dict
) -> DescriptiveResult:
    """Build one auditable summary, including exclusions and unavailable values."""
    valid = values[~np.isnan(values)]
    result = DescriptiveResult(
        name=f"Descriptive statistics: {parameters['column']}",
        provenance=build_provenance("describe", frame, {**parameters, "group_keys": group_keys}),
        interpretation_context=(
            "Describes observed measurements, not process stability or capability. "
            "CV is a ratio; multiply by 100 for percent. MAD is unscaled."
        ),
        count=len(valid),
        total=len(values),
        missing=len(values) - len(valid),
        unit=parameters["unit"],
        group_keys=group_keys,
        metadata={"numpy_version": np.__version__, "scipy_version": scipy.__version__},
    )
    if result.missing:
        _warn(result, "MISSING_OMITTED", f"Excluded {result.missing} null/NaN measurements.")
    if not len(valid):
        _warn(result, "NO_VALID_DATA", "No valid measurements; statistics are unavailable.")
        return result
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        _location(result, valid, parameters["percentiles"])
        _spread(result, valid, parameters["ddof"], parameters["measurement_scale"])
        _shape(result, valid, parameters["excess_kurtosis"])
    _finite_statistics(result)
    return result


def _finite_statistics(result: DescriptiveResult) -> None:
    """Replace numerical overflow or ill-conditioned estimates with explicit diagnostics."""
    fields = (
        "mean",
        "median",
        "std",
        "variance",
        "skew",
        "kurtosis",
        "range",
        "iqr",
        "mad",
        "coefficient_of_variation",
    )
    for name in fields:
        value = getattr(result, name)
        if value is not None and not np.isfinite(value):
            setattr(result, name, None)
            _warn(
                result, "NUMERICAL_UNAVAILABLE", f"{name} is numerically undefined or overflowed."
            )
    if result.percentiles is not None:
        for key, value in list(result.percentiles.items()):
            if not np.isfinite(value):
                del result.percentiles[key]
                _warn(result, "NUMERICAL_UNAVAILABLE", f"{key} overflowed and is unavailable.")


def _policies(missing: str, scale: str, excess: bool) -> None:
    """Validate explicit interpretation and exclusion policies."""
    if missing not in ("omit", "raise") or scale not in ("ratio", "interval"):
        raise ValidationError("Invalid missing policy or measurement_scale.")
    if not isinstance(excess, bool):
        raise ValidationError("excess_kurtosis must be a boolean.")


def _group_columns(frame: nw.DataFrame, group_by: str | Sequence[str] | None) -> list[str]:
    """Resolve and validate grouping columns without silently dropping keys."""
    columns = [group_by] if isinstance(group_by, str) else list(group_by or [])
    if group_by is not None and not columns:
        raise ValidationError("group_by must contain at least one column.")
    if len(set(columns)) != len(columns):
        raise ValidationError("group_by columns must be unique.")
    require_columns(frame, *columns)
    return columns


@overload
def describe(
    data: Any,
    *,
    column: str,
    group_by: None = None,
    percentiles: Sequence[float] = (90, 95, 99),
    ddof: int = 1,
    missing: Literal["omit", "raise"] = "omit",
    excess_kurtosis: bool = True,
    measurement_scale: Literal["ratio", "interval"] = "ratio",
    unit: str | None = None,
) -> DescriptiveResult: ...


@overload
def describe(
    data: Any,
    *,
    column: str,
    group_by: str | Sequence[str],
    percentiles: Sequence[float] = (90, 95, 99),
    ddof: int = 1,
    missing: Literal["omit", "raise"] = "omit",
    excess_kurtosis: bool = True,
    measurement_scale: Literal["ratio", "interval"] = "ratio",
    unit: str | None = None,
) -> list[DescriptiveResult]: ...


@register_analysis(
    AnalysisSuitability(
        name="describe",
        family="descriptive",
        question_tags=("summarize_measurements",),
        required_fields=(("column",),),
        data_types=("numeric",),
        prerequisites=(
            "An eager numeric measurement column; optional explicit grouping columns.",
            "Variance needs count > ddof; skewness needs three values; kurtosis four.",
        ),
        assumptions=("The declared cohort and measurement scale match the question.",),
        alternatives=("lead_time",),
        limits=(
            "Cannot establish normality, stability, capability, causality or independence.",
            "CV requires ratio scale and a sufficiently positive mean.",
        ),
        belt_level="white",
        design_types=("observational",),
    )
)
def describe(
    data: Any,
    *,
    column: str,
    group_by: str | Sequence[str] | None = None,
    percentiles: Sequence[float] = (90, 95, 99),
    ddof: int = 1,
    missing: Literal["omit", "raise"] = "omit",
    excess_kurtosis: bool = True,
    measurement_scale: Literal["ratio", "interval"] = "ratio",
    unit: str | None = None,
) -> DescriptiveResult | list[DescriptiveResult]:
    """Summarize a numeric dataframe column, optionally within groups.

    White Belt: suitable for understanding location, spread, shape, and missingness;
    not a test of normality, stability, or capability. Accepts eager pandas/Polars
    frames through Narwhals and materializes only the selected measurements and
    grouping keys, without mutating the input. Text and boolean measurements and
    infinities are rejected. Nulls and NaNs follow the explicit missing policy.

    Sample variance/std use ddof=1 (0 selects population). Shape estimates are
    bias-corrected; excess kurtosis is the default. Quartiles are always included;
    additional percentile levels use NumPy's linear interpolation. Mode lists all
    tied repeated values. MAD is unscaled. CV requires a declared ratio scale and
    positive mean greater than 1e-12 times the largest absolute measurement.

    Returns one DescriptiveResult without grouping; otherwise a list in first-seen
    group order, retaining null groups. Empty grouped inputs return an empty list.
    Undefined estimates are None with structured provenance warnings.
    """
    levels = _options(ddof, percentiles)
    _policies(missing, measurement_scale, excess_kurtosis)
    frame = nw.from_native(data, eager_only=True)
    values = _measurements(frame, column)
    if missing == "raise" and np.isnan(values).any():
        raise ValidationError(f"Column '{column}' contains missing measurements.")
    columns = _group_columns(frame, group_by)
    parameters = {
        "column": column,
        "group_by": columns,
        "percentiles": levels,
        "ddof": ddof,
        "missing": missing,
        "excess_kurtosis": excess_kurtosis,
        "bias_corrected": True,
        "percentile_method": "linear",
        "measurement_scale": measurement_scale,
        "unit": unit,
        "cv_near_zero_relative_tolerance": 1e-12,
        "mad_scale": "unscaled",
    }
    if group_by is None:
        return _summarize(frame, values, parameters, {})
    return [
        _summarize(frame, values[indices], parameters, keys)
        for keys, indices in _groups(frame, columns)
    ]
