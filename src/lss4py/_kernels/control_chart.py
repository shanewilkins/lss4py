"""Moving-range control charts with explicit Phase I and frozen Phase II limits."""

from __future__ import annotations

from math import isclose, isfinite, pi, sqrt
from numbers import Real
from typing import Any, Literal

import numpy as np

from lss4py._bundle_schema import BundleValidationError, bundle_fingerprint, validate_result
from lss4py._frames import canonical_frame
from lss4py._kernels._helpers import build_provenance
from lss4py._polars_extract import measurement_values, portable_key_values
from lss4py.domain import AssumptionNote, ControlChartResult
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis

_D2_2 = 2 / sqrt(pi)
_D3_2 = sqrt(2 * (1 - 2 / pi))


def _nsigmas(value: float) -> float:
    """Require a finite positive control-limit width."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError("nsigmas must be a finite positive number.")
    normalized = float(value)
    if not isfinite(normalized) or normalized <= 0:
        raise ValidationError("nsigmas must be a finite positive number.")
    return normalized


def _unit(value: str | None) -> None:
    """Require a portable nonblank unit when one is declared."""
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ValidationError("unit must be a nonblank string or None.")


def _limits(ranges: np.ndarray, nsigmas: float) -> tuple[float, float, float]:
    """Estimate MR limits using the n=2 relative-range constants."""
    center = float(np.mean(ranges))
    spread_ratio = _D3_2 / _D2_2
    lower = max(0.0, center * (1 - nsigmas * spread_ratio))
    upper = center * (1 + nsigmas * spread_ratio)
    if not all(isfinite(value) for value in (lower, center, upper)):
        raise ValidationError("Moving-range limit arithmetic overflowed.")
    return lower, center, upper


def _baseline(
    result: ControlChartResult,
    nsigmas: float,
) -> tuple[float, float, float, str]:
    """Validate one intact Phase I result before reusing its frozen limits."""
    if not isinstance(result, ControlChartResult):
        raise ValidationError("baseline must be a Phase I ControlChartResult.")
    if result.phase != "I" or result.chart != "moving_range":
        raise ValidationError("baseline must be a Phase I moving-range result.")
    if not isclose(result.nsigmas, nsigmas, rel_tol=0, abs_tol=0):
        raise ValidationError("nsigmas must match the Phase I baseline.")
    try:
        payload = result.to_dict()
        validate_result(payload)
    except (BundleValidationError, TypeError, ValueError) as exc:
        raise ValidationError("baseline is not an intact ControlChartResult.") from exc
    expected = _limits(result.moving_ranges, nsigmas)
    actual = (result.lcl, result.center_line, result.ucl)
    if not all(
        isclose(left, right, rel_tol=1e-12, abs_tol=0)
        for left, right in zip(actual, expected, strict=True)
    ):
        raise ValidationError("baseline limits differ from its Phase I observations.")
    return (*actual, bundle_fingerprint(payload))


@register_analysis(
    AnalysisSuitability(
        name="control_chart",
        family="spc",
        question_tags=("process_stability", "special_cause_monitoring"),
        required_fields=(("column",),),
        data_types=("numeric",),
        prerequisites=(
            "At least two complete measurements in meaningful sequential source order.",
        ),
        assumptions=(
            "Adjacent observations are comparable and source order is the monitoring order.",
        ),
        alternatives=("describe", "distribution_profile"),
        limits=(
            "The first slice supports moving ranges of two only.",
            "No run, trend, zone, subgroup, attribute-chart, or automatic recalibration rules.",
        ),
        belt_level="yellow",
        design_types=("sequential_observational",),
        sampling_requirements=(
            "Phase I estimates limits from the supplied sequence; Phase II reuses "
            "an intact Phase I result.",
        ),
    )
)
def control_chart(
    data: Any,
    *,
    column: str,
    chart: Literal["moving_range"] = "moving_range",
    baseline: ControlChartResult | None = None,
    nsigmas: float = 3.0,
    key_column: str | None = None,
    unit: str | None = None,
) -> ControlChartResult:
    """Calculate an MR(2) control chart without rendering or implicit recalibration.

    Phase I estimates limits from adjacent absolute differences in the supplied
    source order. Phase II accepts only an intact Phase I ``ControlChartResult``
    and copies its limits; it never recalculates them from monitoring data.
    Missing values are rejected because omitting a row would invent a new
    adjacency. Optional keys must be unique portable scalars; source positions
    always preserve each adjacent pair independently of pandas indexes.
    """
    if chart != "moving_range":
        raise ValidationError("chart must be 'moving_range'.")
    width = _nsigmas(nsigmas)
    _unit(unit)
    columns = tuple(dict.fromkeys((column, *(() if key_column is None else (key_column,)))))
    canonical = canonical_frame(data, columns)
    frame = canonical.to_polars(copy=False)
    values = measurement_values(frame, column)
    if np.isnan(values).any():
        raise ValidationError(f"Column '{column}' contains missing measurements.")
    if len(values) < 2:
        raise ValidationError("Moving-range charts require at least two measurements.")
    keys, identity = portable_key_values(frame, key_column)
    with np.errstate(over="ignore", invalid="ignore"):
        ranges = np.abs(np.diff(values))
    if not np.isfinite(ranges).all():
        raise ValidationError("Moving-range arithmetic overflowed.")

    if baseline is None:
        phase: Literal["I", "II"] = "I"
        lcl, center, ucl = _limits(ranges, width)
        baseline_count = len(values)
        baseline_fingerprint = None
        baseline_schema_fingerprint = canonical.source_schema_fingerprint
    else:
        phase = "II"
        lcl, center, ucl, baseline_fingerprint = _baseline(baseline, width)
        if unit is not None and unit != baseline.unit:
            raise ValidationError(
                "unit must match the Phase I baseline; convert inputs explicitly."
            )
        unit = baseline.unit
        baseline_count = baseline.observation_count
        baseline_schema_fingerprint = baseline.provenance.input_schema_fingerprint

    signals = np.flatnonzero((ranges < lcl) | (ranges > ucl)).astype(np.int64)
    parameters = {
        "column": column,
        "chart": chart,
        "phase": phase,
        "nsigmas": width,
        "key_column": key_column,
        "unit": unit,
        "moving_range_span": 2,
        "limit_estimator": "mean_moving_range_d2_d3",
        "baseline_result_fingerprint": baseline_fingerprint,
        "baseline_schema_fingerprint": baseline_schema_fingerprint,
    }
    provenance = build_provenance(
        "control_chart",
        canonical,
        parameters,
        assumptions=[
            {
                "code": "SEQUENTIAL_COMPARABLE_OBSERVATIONS",
                "message": "Source order is meaningful and adjacent observations are comparable.",
            }
        ],
    )
    provenance.method_version = "1.0"
    if phase == "II":
        provenance.assumptions.append(
            AssumptionNote(
                "FROZEN_PHASE_I_BASELINE",
                "Phase II limits come from the supplied intact Phase I result.",
            )
        )
    return ControlChartResult(
        name=f"Moving-range control chart: {column}",
        provenance=provenance,
        interpretation_context=(
            "Signals identify adjacent changes outside the declared MR limits; "
            "they do not diagnose a cause or certify process stability."
        ),
        metadata={
            **identity,
            "d2": _D2_2,
            "d3": _D3_2,
            "moving_range_span": 2,
        },
        phase=phase,
        moving_ranges=ranges,
        pair_start_positions=np.arange(len(values) - 1, dtype=np.int64),
        pair_end_positions=np.arange(1, len(values), dtype=np.int64),
        pair_start_keys=None if keys is None else keys[:-1].copy(),
        pair_end_keys=None if keys is None else keys[1:].copy(),
        lcl=lcl,
        center_line=center,
        ucl=ucl,
        signal_indices=signals,
        signal_source_positions=(signals + 1).astype(np.int64),
        observation_count=len(values),
        baseline_observation_count=baseline_count,
        nsigmas=width,
        unit=unit,
        baseline_result_fingerprint=baseline_fingerprint,
    )
