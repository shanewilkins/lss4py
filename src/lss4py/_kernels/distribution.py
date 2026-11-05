"""Backend-neutral distribution evidence for diagnostic rendering and review."""

from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np
import scipy
from scipy import stats

from lss4py._frames import canonical_frame
from lss4py._kernels._distribution import shapiro_diagnostic
from lss4py._kernels._helpers import build_provenance
from lss4py._polars_extract import measurement_values, portable_key_values, source_positions
from lss4py.domain import AssumptionNote, DistributionProfileResult
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis

HistogramMethod = Literal["auto", "fd", "doane", "scott", "rice", "sturges", "sqrt"]
BandwidthMethod = Literal["scott", "silverman"]
OutlierMethod = Literal["iqr", "none"]

_HISTOGRAM_METHODS = {"auto", "fd", "doane", "scott", "rice", "sturges", "sqrt"}


def _probability(value: float, name: str) -> float:
    """Require a finite, non-boolean probability strictly inside the unit interval."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a finite number strictly between 0 and 1.")
    converted = float(value)
    if not math.isfinite(converted) or not 0 < converted < 1:
        raise ValidationError(f"{name} must be a finite number strictly between 0 and 1.")
    return converted


def _histogram_bins(value: HistogramMethod | int) -> HistogramMethod | int:
    """Validate an explicit bin count or one supported NumPy selection method."""
    if isinstance(value, bool):
        raise ValidationError("histogram_bins must be a positive integer or supported method.")
    if isinstance(value, int):
        if value <= 0:
            raise ValidationError("histogram_bins must be a positive integer or supported method.")
        return value
    if not isinstance(value, str):
        raise ValidationError("histogram_bins must be a positive integer or supported method.")
    if value not in _HISTOGRAM_METHODS:
        raise ValidationError(
            "histogram_bins must be auto, fd, doane, scott, rice, sturges, sqrt, "
            "or a positive integer."
        )
    return value


def _bandwidth(value: BandwidthMethod | float) -> BandwidthMethod | float:
    """Validate a named or positive scalar Gaussian KDE bandwidth factor."""
    if isinstance(value, str):
        if value not in ("scott", "silverman"):
            raise ValidationError("density_bandwidth must be scott, silverman, or positive.")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("density_bandwidth must be scott, silverman, or positive.")
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0:
        raise ValidationError("density_bandwidth must be scott, silverman, or positive.")
    return converted


def _shape(
    values: np.ndarray,
) -> tuple[float | None, float | None, list[AssumptionNote]]:
    """Calculate bias-corrected shape estimates when sample and variation permit."""
    warnings: list[AssumptionNote] = []
    if np.all(values == values[0]):
        warnings.append(
            AssumptionNote(
                "SHAPE_UNAVAILABLE",
                "Skewness and kurtosis are undefined for constant measurements.",
                severity="warning",
            )
        )
        return None, None, warnings
    skew = float(stats.skew(values, bias=False)) if len(values) >= 3 else None
    kurtosis = float(stats.kurtosis(values, fisher=True, bias=False)) if len(values) >= 4 else None
    if skew is None:
        warnings.append(
            AssumptionNote(
                "SKEW_UNAVAILABLE",
                "Bias-corrected skewness requires at least three valid measurements.",
                severity="warning",
            )
        )
    if kurtosis is None:
        warnings.append(
            AssumptionNote(
                "KURTOSIS_UNAVAILABLE",
                "Bias-corrected kurtosis requires at least four valid measurements.",
                severity="warning",
            )
        )
    return skew, kurtosis, warnings


def _density(
    values: np.ndarray,
    enabled: bool,
    bandwidth: BandwidthMethod | float,
    grid_points: int,
) -> tuple[str | None, float | None, np.ndarray, np.ndarray, list[AssumptionNote]]:
    """Prepare a Gaussian KDE grid without making rendering responsible for fitting."""
    if not enabled:
        return None, None, np.array([]), np.array([]), []
    if np.all(values == values[0]):
        return (
            None,
            None,
            np.array([]),
            np.array([]),
            [
                AssumptionNote(
                    "DENSITY_UNAVAILABLE",
                    "Gaussian KDE is undefined for constant measurements.",
                    severity="warning",
                )
            ],
        )
    try:
        estimator = stats.gaussian_kde(values, bw_method=bandwidth)
        resolved = float(math.sqrt(estimator.covariance[0, 0]))
        grid = np.linspace(values.min() - 3 * resolved, values.max() + 3 * resolved, grid_points)
        estimates = np.asarray(estimator(grid), dtype=float)
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise ValidationError(
            "Gaussian KDE could not be estimated for these measurements."
        ) from exc
    if (
        not math.isfinite(resolved)
        or not np.isfinite(grid).all()
        or not np.isfinite(estimates).all()
    ):
        raise ValidationError("Gaussian KDE did not produce finite evidence.")
    return "gaussian_kde", resolved, grid, estimates, []


def _validated_options(
    *,
    histogram_bins: HistogramMethod | int,
    outlier_method: OutlierMethod,
    outlier_multiplier: float,
    density: bool,
    density_bandwidth: BandwidthMethod | float,
    density_grid_points: int,
    normality_alpha: float,
    missing: Literal["omit", "raise"],
    unit: str | None,
    cohort: str | None,
) -> tuple[HistogramMethod | int, BandwidthMethod | float, float, float]:
    """Validate profile policies and return their normalized numeric values."""
    bins = _histogram_bins(histogram_bins)
    bandwidth = _bandwidth(density_bandwidth)
    alpha = _probability(normality_alpha, "normality_alpha")
    if outlier_method not in ("iqr", "none"):
        raise ValidationError("outlier_method must be 'iqr' or 'none'.")
    if isinstance(outlier_multiplier, bool) or not isinstance(outlier_multiplier, (int, float)):
        raise ValidationError("outlier_multiplier must be a finite positive number.")
    multiplier = float(outlier_multiplier)
    if not math.isfinite(multiplier) or multiplier <= 0:
        raise ValidationError("outlier_multiplier must be a finite positive number.")
    if not isinstance(density, bool):
        raise ValidationError("density must be a boolean.")
    if (
        isinstance(density_grid_points, bool)
        or not isinstance(density_grid_points, int)
        or not 32 <= density_grid_points <= 4096
    ):
        raise ValidationError("density_grid_points must be an integer from 32 through 4096.")
    if missing not in ("omit", "raise"):
        raise ValidationError("missing must be 'omit' or 'raise'.")
    if unit is not None and (not isinstance(unit, str) or not unit.strip()):
        raise ValidationError("unit must be a nonblank string when supplied.")
    if cohort is not None and (not isinstance(cohort, str) or not cohort.strip()):
        raise ValidationError("cohort must be a nonblank string when supplied.")
    return bins, bandwidth, alpha, multiplier


@register_analysis(
    AnalysisSuitability(
        name="distribution_profile",
        outcome_types=("numeric_measurement",),
        predictor_types=("none",),
        sampling_requirements=(
            "The supplied cohort and observation identity match the diagnostic question.",
        ),
        family="diagnostic",
        question_tags=("profile_distribution",),
        required_fields=(("column",),),
        data_types=("numeric",),
        prerequisites=(
            "At least two valid numeric measurements.",
            "Histogram, anomaly, normality and optional density policies are explicit.",
        ),
        assumptions=(
            "Flags prompt investigation and are not automatic exclusions.",
            "Normal Q-Q and Shapiro-Wilk evidence address marginal shape, not independence.",
        ),
        alternatives=("describe", "mean_confidence_interval"),
        limits=(
            "Does not establish stability, capability, causality or representative sampling.",
            "Serialized ECDF and Q-Q evidence reproduces the observed measurement values.",
        ),
        belt_level="yellow",
        design_types=("observational",),
    )
)
def distribution_profile(
    data: Any,
    *,
    column: str,
    key_column: str | None = None,
    histogram_bins: HistogramMethod | int = "auto",
    outlier_method: OutlierMethod = "iqr",
    outlier_multiplier: float = 1.5,
    density: bool = False,
    density_bandwidth: BandwidthMethod | float = "scott",
    density_grid_points: int = 256,
    normality_alpha: float = 0.05,
    missing: Literal["omit", "raise"] = "omit",
    unit: str | None = None,
    cohort: str | None = None,
) -> DistributionProfileResult:
    """Prepare explicit distribution, anomaly, Q-Q, ECDF and optional density evidence.

    The result retains valid observations, source positions and optional unique keys.
    Serializing it can therefore reproduce source measurements. Plotting functions
    consume the prepared arrays without selecting bins, fitting density, sorting,
    testing normality, or detecting outliers.
    """
    bins, bandwidth, alpha, multiplier = _validated_options(
        histogram_bins=histogram_bins,
        outlier_method=outlier_method,
        outlier_multiplier=outlier_multiplier,
        density=density,
        density_bandwidth=density_bandwidth,
        density_grid_points=density_grid_points,
        normality_alpha=normality_alpha,
        missing=missing,
        unit=unit,
        cohort=cohort,
    )

    selected = (column,) if key_column is None else (column, key_column)
    canonical = canonical_frame(data, selected)
    frame = canonical.to_polars(copy=False)
    supplied = measurement_values(frame, column)
    keys, _ = portable_key_values(frame, key_column)
    valid_mask = ~np.isnan(supplied)
    if missing == "raise" and not valid_mask.all():
        raise ValidationError(f"Column '{column}' contains missing measurements.")
    values = supplied[valid_mask]
    if len(values) < 2:
        raise ValidationError("Distribution profiles require at least two valid measurements.")
    positions = source_positions(frame, valid_mask)
    valid_keys = None if keys is None else keys[valid_mask]

    try:
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            edges = np.histogram_bin_edges(values, bins=bins)
            counts, _ = np.histogram(values, bins=edges)
            widths = np.diff(edges)
            histogram_density = counts / (len(values) * widths)
            order = np.argsort(values, kind="stable")
            ecdf_values = values[order]
            ecdf_probabilities = np.arange(1, len(values) + 1, dtype=float) / len(values)
            (qq_theoretical, qq_observed), (qq_slope, qq_intercept, qq_r) = stats.probplot(
                values, dist="norm", fit=True
            )
            qq_line_x = np.asarray([qq_theoretical[0], qq_theoretical[-1]], dtype=float)
            qq_line_y = qq_slope * qq_line_x + qq_intercept
            q1, median, q3 = np.percentile(values, [25, 50, 75], method="linear")
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1))
    except (ValueError, OverflowError, FloatingPointError) as exc:
        raise ValidationError("Distribution profile arithmetic did not remain finite.") from exc
    iqr = float(q3 - q1)
    if outlier_method == "iqr":
        lower_fence = float(q1 - multiplier * iqr)
        upper_fence = float(q3 + multiplier * iqr)
        outlier_mask = (values < lower_fence) | (values > upper_fence)
    else:
        lower_fence = upper_fence = None
        outlier_mask = np.zeros(len(values), dtype=bool)
    retained = values[~outlier_mask]
    lower_whisker = float(retained.min())
    upper_whisker = float(retained.max())

    skew, kurtosis, warnings = _shape(values)
    qq_correlation = float(qq_r) if math.isfinite(float(qq_r)) else None
    if qq_correlation is None:
        warnings.append(
            AssumptionNote(
                "QQ_CORRELATION_UNAVAILABLE",
                "Q-Q correlation is undefined for constant measurements.",
                severity="warning",
            )
        )
    shapiro_statistic, shapiro_p_value, normality_warnings = shapiro_diagnostic(values, alpha)
    warnings.extend(normality_warnings)
    density_method, resolved_bandwidth, density_x, density_y, density_warnings = _density(
        values, density, bandwidth, density_grid_points
    )
    warnings.extend(density_warnings)

    arrays = (
        edges,
        histogram_density,
        qq_theoretical,
        qq_observed,
        qq_line_x,
        qq_line_y,
        density_x,
        density_y,
    )
    scalars = (mean, std, q1, median, q3, qq_slope, qq_intercept)
    optional_shape = tuple(value for value in (skew, kurtosis) if value is not None)
    if not all(np.isfinite(array).all() for array in arrays) or not all(
        math.isfinite(float(value)) for value in (*scalars, *optional_shape)
    ):
        raise ValidationError("Distribution profile arithmetic did not remain finite.")

    parameters = {
        "column": column,
        "key_column": key_column,
        "histogram_bins": bins,
        "outlier_method": outlier_method,
        "outlier_multiplier": multiplier,
        "density": density,
        "density_bandwidth": bandwidth,
        "density_grid_points": density_grid_points,
        "normality_alpha": alpha,
        "missing": missing,
        "unit": unit,
        "cohort": cohort,
        "qq_distribution": "normal",
        "percentile_method": "linear",
    }
    provenance = build_provenance("distribution_profile", canonical, parameters)
    provenance.method_version = "1.0"
    provenance.warnings.extend(warnings)
    return DistributionProfileResult(
        name=f"Distribution profile: {column}",
        provenance=provenance,
        interpretation_context=(
            "Distribution and anomaly evidence prompts investigation; flags are not exclusions "
            "and normality diagnostics do not establish independence or stability."
        ),
        metadata={
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "evidence_sensitivity": (
                "Serialized observations, ECDF and Q-Q coordinates reproduce valid source values."
            ),
        },
        values=values,
        keys=valid_keys,
        source_positions=positions,
        unit=unit,
        count=len(values),
        total=len(supplied),
        missing=len(supplied) - len(values),
        mean=mean,
        median=float(median),
        std=std,
        skew=skew,
        kurtosis=kurtosis,
        histogram_bin_method=str(bins),
        histogram_edges=edges,
        histogram_counts=counts,
        histogram_density=histogram_density,
        ecdf_values=ecdf_values,
        ecdf_probabilities=ecdf_probabilities,
        qq_distribution="normal",
        qq_theoretical=np.asarray(qq_theoretical, dtype=float),
        qq_observed=np.asarray(qq_observed, dtype=float),
        qq_line_x=qq_line_x,
        qq_line_y=np.asarray(qq_line_y, dtype=float),
        qq_slope=float(qq_slope),
        qq_intercept=float(qq_intercept),
        qq_r=qq_correlation,
        q1=float(q1),
        q3=float(q3),
        iqr=iqr,
        outlier_method=outlier_method,
        outlier_multiplier=multiplier,
        lower_fence=lower_fence,
        upper_fence=upper_fence,
        lower_whisker=lower_whisker,
        upper_whisker=upper_whisker,
        outlier_values=values[outlier_mask],
        outlier_source_positions=positions[outlier_mask],
        outlier_keys=None if valid_keys is None else valid_keys[outlier_mask],
        shapiro_statistic=shapiro_statistic,
        shapiro_p_value=shapiro_p_value,
        normality_alpha=alpha,
        density_method=density_method,
        density_bandwidth=resolved_bandwidth,
        density_x=density_x,
        density_y=density_y,
    )
