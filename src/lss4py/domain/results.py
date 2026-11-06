"""Typed analytical result models with provenance, assumptions, and interpretation context.

All public analytical methods return instances of AnalyticalResult or its subclasses.
Results preserve method metadata, input schema, assumptions, warnings, backend information,
and creation timestamp to enable reproducibility and auditable analysis chains.

Belt Level: Yellow Belt (v0.2 MVP foundation; completed workflows v0.3+)
Suitable When: You need to capture and communicate analytical decisions with full transparency.
Not Suitable When: You need raw NumPy arrays (convert results with .to_numpy() instead).

See ADR-0003, ADR-0004, TR-009, TR-015, TR-016, TR-020, TR-033.
"""

from __future__ import annotations

import json
from abc import ABC
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal, Self, TypeVar

import numpy as np

from lss4py.domain.bundles import AnalysisBundle as AnalysisBundle
from lss4py.domain.models import AssumptionNote

ResultT = TypeVar("ResultT")


@dataclass(slots=True)
class Provenance:
    """Metadata about how a result was computed.

    Provenance captures the method, version, parameters, backend,
    library versions, and assumptions used in analysis. This enables reproducibility
    and auditable analysis chains.
    """

    method: str
    """Name of the analytical method (e.g., 'lead_time', 'process_cycle_efficiency')."""

    method_version: str
    """Version of the method implementation (semantic versioning)."""

    package_version: str
    """Version of lss4py that computed this result."""

    backend: Literal["pandas", "polars", "pyarrow", "unknown"]
    """DataFrame backend used (pandas, polars, pyarrow, or unknown)."""

    parameters: dict[str, Any] = field(default_factory=dict)
    """Analysis parameters (e.g., {"start_column": "created_at", "unit": "hours"})."""

    created_at: datetime = field(default_factory=datetime.now)
    """Timestamp when the result was computed."""

    assumptions: list[AssumptionNote] = field(default_factory=list)
    """Analytical assumptions (e.g., time ordering, missing data policy)."""

    warnings: list[AssumptionNote] = field(default_factory=list)
    """Warnings raised during computation (e.g., small sample size, numerical instability)."""

    input_schema_fingerprint: str | None = None
    """Optional hash of input data schema for validation on rerun."""

    cohort_definition: str | None = None
    """Human-readable description of the analyzed cohort (e.g., 'Q3 intake cases')."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize provenance to a dictionary."""
        return {
            "method": self.method,
            "method_version": self.method_version,
            "package_version": self.package_version,
            "backend": self.backend,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "assumptions": [asdict(a) for a in self.assumptions],
            "warnings": [asdict(a) for a in self.warnings],
            "input_schema_fingerprint": self.input_schema_fingerprint,
            "cohort_definition": self.cohort_definition,
        }

    def to_json(self) -> str:
        """Serialize provenance to JSON."""
        return json.dumps(self.to_dict(), indent=2, allow_nan=False)


@dataclass(slots=True)
class AnalyticalResult(ABC):
    """Base class for all public analytical results.

    Every result from a Yellow Belt or higher analysis includes:
    - name: Human-readable description of what was analyzed
    - provenance: Full record of how the result was computed
    - interpretation_context: Guidance on when and how to use this result
    - metadata: Arbitrary key-value context (e.g., flags, tags)

    Results are editable; bundle capture takes detached copies for saved evidence.
    """

    name: str
    """Human-readable name (e.g., 'Lead Time', 'Process Cycle Efficiency %')."""

    provenance: Provenance
    """Full metadata about how this result was computed."""

    interpretation_context: str | None = None
    """Guidance on interpretation, caveats, and intended use cases."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Arbitrary key-value metadata (e.g., labels, tags, domain-specific flags)."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to a dictionary.

        This is the canonical serialization format for storage and round-tripping.
        """
        return {
            "result_type": self.__class__.__name__,
            "name": self.name,
            "provenance": self.provenance.to_dict(),
            "interpretation_context": self.interpretation_context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Restore a supported concrete result with validated arrays and provenance."""
        from lss4py.domain._result_io import restore_result
        from lss4py.errors import ValidationError

        result = restore_result(data)
        if cls is not AnalyticalResult and not isinstance(result, cls):
            raise ValidationError("Serialized result type differs from requested class.")
        return result

    def to_json(self) -> str:
        """Serialize result to JSON."""
        return json.dumps(self.to_dict(), indent=2, allow_nan=False)


@dataclass(slots=True)
class TimingResult(AnalyticalResult):
    """Result of a timing analysis (lead time, cycle time, wait time, etc.).

    Timing results capture per-row durations or aggregated statistics with explicit
    backend-neutral keying and units.
    """

    values: np.ndarray = field(default_factory=lambda: np.array([]))
    """Per-row or per-case timing values (NumPy array)."""

    unit: Literal["seconds", "minutes", "hours", "days", "percentage", "ratio"] = "hours"
    """Unit of measurement or dimensionless ratio."""

    keys: np.ndarray | None = None
    """Optional case/row identifiers (e.g., case IDs, row indices)."""

    percentiles: dict[str, float] | None = None
    """Optional p50, p90, p95, p99 percentiles (if aggregated)."""

    def to_numpy(self) -> np.ndarray:
        """Extract values as a NumPy array."""
        return self.values.copy()

    def to_frame(self, backend: str = "polars"):
        """Return an independent native table with explicit source positions and keys.

        Pandas/Arrow conversions require their optional backend dependencies.
        No pandas index is used as analytical identity. Legacy unkeyed results
        expose their existing positional identity as the key column.
        """
        rows = {
            "row_position": list(range(len(self.values))),
            "key": self.keys.tolist() if self.keys is not None else list(range(len(self.values))),
            "value": self.values.tolist(),
            "unit": [self.unit] * len(self.values),
        }
        return _native_result_frame(rows, backend)

    def to_dict(self) -> dict[str, Any]:
        """Serialize timing result to a dictionary."""
        base = super().to_dict()
        base.update(
            {
                "values": self.values.tolist(),
                "unit": self.unit,
                "keys": self.keys.tolist() if self.keys is not None else None,
                "percentiles": self.percentiles,
            }
        )
        return base


@dataclass(slots=True)
class YieldResult(AnalyticalResult):
    """Result of a yield or defect-rate analysis.

    Yield results capture computation of FTY (First-Time Yield), RTY (Rolled Throughput
    Yield), DPMO (Defects Per Million Opportunities), and defect rates with
    explicit opportunity counts and denominators.
    """

    value: float = 0.0
    """Computed yield, defect rate, or DPMO value."""

    unit: Literal["fraction", "percentage", "ppm"] = "fraction"
    """Unit of the value (0-1, 0-100, or parts per million)."""

    numerator: int | None = None
    """Count of defects or non-conformances (if available)."""

    denominator: int | None = None
    """Total opportunities or units (if available)."""

    method: str | None = None
    """Method used (e.g., 'funnel_stages', 'serial_yield', 'per_unit')."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize yield result to a dictionary."""
        base = super().to_dict()
        base.update(
            {
                "value": self.value,
                "unit": self.unit,
                "numerator": self.numerator,
                "denominator": self.denominator,
                "method": self.method,
            }
        )
        return base


@dataclass(slots=True)
class DefectYieldResult(AnalyticalResult):
    """Opportunity-based defect/rework estimates under a shared counting denominator.

    Fractions follow the retained R counting convention, not inferred unit success.
    The optional defects_per_unit rate requires an explicitly supplied unit count.
    """

    schema_version: str = "1.0"
    yield_fraction: float = 0.0
    first_time_yield: float = 0.0
    rolled_throughput_yield: float = 0.0
    dpmo: float = 0.0
    defect_count: int = 0
    rework_count: int = 0
    opportunities: int = 0
    units: int | None = None
    defects_per_unit: float | None = None
    bucket_defects: tuple[int, ...] = ()
    bucket_rework: tuple[int, ...] = ()
    bucket_first_time_yields: tuple[float, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize estimates, aligned buckets, and explicit denominator evidence."""
        base = AnalyticalResult.to_dict(self)
        fields = (
            "schema_version",
            "yield_fraction",
            "first_time_yield",
            "rolled_throughput_yield",
            "dpmo",
            "defect_count",
            "rework_count",
            "opportunities",
            "units",
            "defects_per_unit",
        )
        base.update({name: getattr(self, name) for name in fields})
        base.update(
            {
                "bucket_defects": list(self.bucket_defects),
                "bucket_rework": list(self.bucket_rework),
                "bucket_first_time_yields": list(self.bucket_first_time_yields),
            }
        )
        return base


@dataclass(slots=True)
class CapabilityResult(AnalyticalResult):
    """Result of a capability study (Cp, Cpk, Z-score, etc.).

    Capability results capture process centering and spread relative to specification
    limits, including confidence intervals and non-normal warnings.
    """

    cp: float | None = None
    """Potential capability index (spread vs. tolerance)."""

    cpk: float | None = None
    """Actual capability index (centering and spread vs. tolerance)."""

    z_score: float | None = None
    """Signed specification distance after any declared sigma shift; not a tail probability."""

    target: float | None = None
    """Process target or nominal value."""

    lsl: float | None = None
    """Lower specification limit."""

    usl: float | None = None
    """Upper specification limit."""

    mean: float | None = None
    """Process mean."""

    sigma: float | None = None
    """Process standard deviation (or estimate)."""

    count: int | None = None
    """Sample size used in the study."""

    confidence_level: float = 0.95
    """Confidence level for interval estimates (default 95%)."""

    confidence_interval: tuple[float, float] | None = None
    """Confidence interval for capability index (e.g., (Cpk_lower, Cpk_upper))."""

    method: str = "normal"
    """Method used (e.g., 'normal', 'box_cox', 'empirical', 'johnson')."""

    cpl: float | None = None
    """Lower component (mean - LSL)/(3s); absent for an upper-only specification."""

    cpu: float | None = None
    """Upper component (USL - mean)/(3s); absent for a lower-only specification."""

    cp_confidence_interval: tuple[float, float] | None = None
    """Chi-square confidence interval for Cp."""

    cpk_confidence_interval: tuple[float, float] | None = None
    """Approximate normal confidence interval for Cpk."""

    total: int = 0
    """Number of supplied measurements before missing-value exclusion."""

    missing: int = 0
    """Number of excluded null/NaN measurements."""

    unit: str | None = None
    """Shared measurement and specification unit; no conversion is inferred."""

    variation_estimator: str = "overall_sample_std"
    """Estimator actually used; does not imply within-subgroup or short-term variation."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize capability result to a dictionary."""
        base = AnalyticalResult.to_dict(self)
        base.update(
            {
                "cpl": self.cpl,
                "cpu": self.cpu,
                "cp_confidence_interval": self.cp_confidence_interval,
                "cpk_confidence_interval": self.cpk_confidence_interval,
                "total": self.total,
                "missing": self.missing,
                "unit": self.unit,
                "variation_estimator": self.variation_estimator,
                "cp": self.cp,
                "cpk": self.cpk,
                "z_score": self.z_score,
                "target": self.target,
                "lsl": self.lsl,
                "usl": self.usl,
                "mean": self.mean,
                "sigma": self.sigma,
                "count": self.count,
                "confidence_level": self.confidence_level,
                "confidence_interval": self.confidence_interval,
                "method": self.method,
            }
        )
        return base


@dataclass(slots=True)
class DescriptiveResult(AnalyticalResult):
    """Result of a descriptive statistical analysis.

    Descriptive results capture summaries like mean, median, percentiles, skew,
    kurtosis, and other distribution characteristics.
    """

    measurement_sum: float | None = None
    """Sum of valid measurements; unavailable for empty/overflowed observations."""

    mean: float | None = None
    """Mean (average)."""

    median: float | None = None
    """Median (50th percentile)."""

    std: float | None = None
    """Standard deviation."""

    variance: float | None = None
    """Variance."""

    skew: float | None = None
    """Skewness indicator."""

    kurtosis: float | None = None
    """Kurtosis indicator."""

    min_value: float | None = None
    """Minimum value."""

    max_value: float | None = None
    """Maximum value."""

    percentiles: dict[str, float] | None = None
    """Named percentiles (e.g., {"p25": 10.5, "p50": 15.0, "p75": 20.5})."""

    count: int | None = None
    """Sample size."""

    missing: int = 0
    """Count of missing values in the input."""

    total: int = 0
    """Total observations before missing-value exclusions; count is the valid count."""

    modes: list[float] = field(default_factory=list)
    """All tied modes in ascending order; empty when no value repeats."""

    mode_frequency: int = 0
    """Maximum observed frequency, including one when all values are unique."""

    unique_count: int = 0
    """Number of distinct valid measurements."""

    range: float | None = None
    """Maximum minus minimum."""

    iqr: float | None = None
    """Third quartile minus first quartile."""

    mad: float | None = None
    """Unscaled median absolute deviation from the median."""

    coefficient_of_variation: float | None = None
    """Standard deviation divided by mean, expressed as a ratio, not percent."""

    unit: str | None = None
    """Declared measurement unit; no unit conversion is performed."""

    group_keys: dict[str, Any] = field(default_factory=dict)
    """Group identifiers, serialized independently of any dataframe backend."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize descriptive result to a dictionary."""
        base = super().to_dict()
        base.update(
            {
                "measurement_sum": self.measurement_sum,
                "mean": self.mean,
                "median": self.median,
                "std": self.std,
                "variance": self.variance,
                "skew": self.skew,
                "kurtosis": self.kurtosis,
                "min_value": self.min_value,
                "max_value": self.max_value,
                "percentiles": self.percentiles,
                "count": self.count,
                "missing": self.missing,
                "total": self.total,
                "modes": self.modes,
                "mode_frequency": self.mode_frequency,
                "unique_count": self.unique_count,
                "range": self.range,
                "iqr": self.iqr,
                "mad": self.mad,
                "coefficient_of_variation": self.coefficient_of_variation,
                "unit": self.unit,
                "group_keys": self.group_keys,
            }
        )
        return base


@dataclass(slots=True)
class DistributionProfileResult(AnalyticalResult):
    """Prepared distribution evidence with exact observation identity."""

    values: np.ndarray = field(default_factory=lambda: np.array([]))
    keys: np.ndarray | None = None
    source_positions: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    unit: str | None = None
    count: int = 0
    total: int = 0
    missing: int = 0
    mean: float = 0.0
    median: float = 0.0
    std: float = 0.0
    skew: float | None = None
    kurtosis: float | None = None
    histogram_bin_method: str = "auto"
    histogram_edges: np.ndarray = field(default_factory=lambda: np.array([]))
    histogram_counts: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    histogram_density: np.ndarray = field(default_factory=lambda: np.array([]))
    ecdf_values: np.ndarray = field(default_factory=lambda: np.array([]))
    ecdf_probabilities: np.ndarray = field(default_factory=lambda: np.array([]))
    qq_distribution: str = "normal"
    qq_theoretical: np.ndarray = field(default_factory=lambda: np.array([]))
    qq_observed: np.ndarray = field(default_factory=lambda: np.array([]))
    qq_line_x: np.ndarray = field(default_factory=lambda: np.array([]))
    qq_line_y: np.ndarray = field(default_factory=lambda: np.array([]))
    qq_slope: float = 0.0
    qq_intercept: float = 0.0
    qq_r: float | None = None
    q1: float = 0.0
    q3: float = 0.0
    iqr: float = 0.0
    outlier_method: Literal["iqr", "none"] = "iqr"
    outlier_multiplier: float = 1.5
    lower_fence: float | None = None
    upper_fence: float | None = None
    lower_whisker: float = 0.0
    upper_whisker: float = 0.0
    outlier_values: np.ndarray = field(default_factory=lambda: np.array([]))
    outlier_source_positions: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    outlier_keys: np.ndarray | None = None
    shapiro_statistic: float | None = None
    shapiro_p_value: float | None = None
    normality_alpha: float = 0.05
    density_method: str | None = None
    density_bandwidth: float | None = None
    density_x: np.ndarray = field(default_factory=lambda: np.array([]))
    density_y: np.ndarray = field(default_factory=lambda: np.array([]))

    def to_frame(self, backend: str = "polars"):
        """Return detached observations with explicit source identity and anomaly flags."""
        flagged = set(self.outlier_source_positions.tolist())
        rows = {
            "source_position": self.source_positions.tolist(),
            "key": (
                self.keys.tolist()
                if self.keys is not None
                else self.source_positions.astype(object).tolist()
            ),
            "value": self.values.tolist(),
            "is_outlier": [position in flagged for position in self.source_positions.tolist()],
        }
        return _native_result_frame(rows, backend)

    def to_dict(self) -> dict[str, Any]:
        """Serialize exact observations and all prepared diagnostic evidence."""
        base = super().to_dict()
        base.update(
            {
                "values": self.values.tolist(),
                "keys": self.keys.tolist() if self.keys is not None else None,
                "source_positions": self.source_positions.tolist(),
                "unit": self.unit,
                "count": self.count,
                "total": self.total,
                "missing": self.missing,
                "mean": self.mean,
                "median": self.median,
                "std": self.std,
                "skew": self.skew,
                "kurtosis": self.kurtosis,
                "histogram_bin_method": self.histogram_bin_method,
                "histogram_edges": self.histogram_edges.tolist(),
                "histogram_counts": self.histogram_counts.tolist(),
                "histogram_density": self.histogram_density.tolist(),
                "ecdf_values": self.ecdf_values.tolist(),
                "ecdf_probabilities": self.ecdf_probabilities.tolist(),
                "qq_distribution": self.qq_distribution,
                "qq_theoretical": self.qq_theoretical.tolist(),
                "qq_observed": self.qq_observed.tolist(),
                "qq_line_x": self.qq_line_x.tolist(),
                "qq_line_y": self.qq_line_y.tolist(),
                "qq_slope": self.qq_slope,
                "qq_intercept": self.qq_intercept,
                "qq_r": self.qq_r,
                "q1": self.q1,
                "q3": self.q3,
                "iqr": self.iqr,
                "outlier_method": self.outlier_method,
                "outlier_multiplier": self.outlier_multiplier,
                "lower_fence": self.lower_fence,
                "upper_fence": self.upper_fence,
                "lower_whisker": self.lower_whisker,
                "upper_whisker": self.upper_whisker,
                "outlier_values": self.outlier_values.tolist(),
                "outlier_source_positions": self.outlier_source_positions.tolist(),
                "outlier_keys": (
                    self.outlier_keys.tolist() if self.outlier_keys is not None else None
                ),
                "shapiro_statistic": self.shapiro_statistic,
                "shapiro_p_value": self.shapiro_p_value,
                "normality_alpha": self.normality_alpha,
                "density_method": self.density_method,
                "density_bandwidth": self.density_bandwidth,
                "density_x": self.density_x.tolist(),
                "density_y": self.density_y.tolist(),
            }
        )
        return base


@dataclass(slots=True)
class QualityLossResult(AnalyticalResult):
    """Calibrated per-observation loss and empirical summaries with original row identity."""

    schema_version: str = "1.0"
    convention: str = "nominal"
    target: float | None = None
    tolerance: float = 1.0
    loss_at_tolerance: float = 0.0
    coefficient: float = 0.0
    values: np.ndarray = field(default_factory=lambda: np.array([], dtype=float))
    losses: np.ndarray = field(default_factory=lambda: np.array([], dtype=float))
    source_positions: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    keys: np.ndarray | None = None
    count: int = 0
    total: int = 0
    missing: int = 0
    mean_squared_deviation: float = 0.0
    average_loss: float = 0.0
    sample_loss: float = 0.0
    production_size: int | None = None
    total_loss: float | None = None
    unit: str | None = None
    loss_unit: str = "currency"

    def to_dict(self) -> dict[str, Any]:
        """Serialize calibrated evidence without recomputing losses or summaries."""
        base = AnalyticalResult.to_dict(self)
        for name in (
            "schema_version",
            "convention",
            "target",
            "tolerance",
            "loss_at_tolerance",
            "coefficient",
            "count",
            "total",
            "missing",
            "mean_squared_deviation",
            "average_loss",
            "sample_loss",
            "production_size",
            "total_loss",
            "unit",
            "loss_unit",
        ):
            base[name] = getattr(self, name)
        for name in ("values", "losses", "source_positions"):
            base[name] = getattr(self, name).tolist()
        base["keys"] = None if self.keys is None else self.keys.tolist()
        return base

    def to_frame(self, backend: str = "polars"):
        """Return detached row-level loss evidence in the requested eager backend."""
        return _native_result_frame(
            {
                "source_position": self.source_positions.tolist(),
                "key": self.source_positions.tolist() if self.keys is None else self.keys.tolist(),
                "measurement": self.values.tolist(),
                "loss": self.losses.tolist(),
            },
            backend,
        )


@dataclass(slots=True)
class CapabilityStudyResult(AnalyticalResult):
    """Explicit short-/long-term capability, distribution, and observed-risk evidence."""

    schema_version: str = "1.0"
    specification: dict[str, Any] = field(default_factory=dict)
    short_term_capability: CapabilityResult | None = None
    short_term_distribution: DistributionProfileResult | None = None
    short_term_nonconformance: dict[str, int | float] = field(default_factory=dict)
    long_term_capability: CapabilityResult | None = None
    long_term_distribution: DistributionProfileResult | None = None
    long_term_nonconformance: dict[str, int | float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize nested typed evidence without recalculating the study."""
        base = AnalyticalResult.to_dict(self)
        base.update(
            {
                "schema_version": self.schema_version,
                "specification": self.specification,
                "short_term_capability": (
                    None
                    if self.short_term_capability is None
                    else self.short_term_capability.to_dict()
                ),
                "short_term_distribution": (
                    None
                    if self.short_term_distribution is None
                    else self.short_term_distribution.to_dict()
                ),
                "short_term_nonconformance": self.short_term_nonconformance,
                "long_term_capability": (
                    None
                    if self.long_term_capability is None
                    else self.long_term_capability.to_dict()
                ),
                "long_term_distribution": (
                    None
                    if self.long_term_distribution is None
                    else self.long_term_distribution.to_dict()
                ),
                "long_term_nonconformance": self.long_term_nonconformance,
            }
        )
        return base


@dataclass(slots=True)
class MeanCIResult(AnalyticalResult):
    """Confidence interval for a population mean with an optional normality diagnostic."""

    mean: float = 0.0
    standard_deviation: float = 0.0
    standard_error: float = 0.0
    count: int = 0
    total: int = 0
    missing: int = 0
    confidence_level: float = 0.95
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    distribution: Literal["student_t", "normal"] = "student_t"
    critical_value: float = 0.0
    degrees_of_freedom: int | None = None
    variance_source: Literal["sample", "known_population"] = "sample"
    population_variance: float | None = None
    shapiro_statistic: float | None = None
    shapiro_p_value: float | None = None
    normality_alpha: float = 0.05
    unit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the inferential result without backend-specific objects."""
        base = super().to_dict()
        base.update(
            {
                "mean": self.mean,
                "standard_deviation": self.standard_deviation,
                "standard_error": self.standard_error,
                "count": self.count,
                "total": self.total,
                "missing": self.missing,
                "confidence_level": self.confidence_level,
                "confidence_interval": self.confidence_interval,
                "distribution": self.distribution,
                "critical_value": self.critical_value,
                "degrees_of_freedom": self.degrees_of_freedom,
                "variance_source": self.variance_source,
                "population_variance": self.population_variance,
                "shapiro_statistic": self.shapiro_statistic,
                "shapiro_p_value": self.shapiro_p_value,
                "normality_alpha": self.normality_alpha,
                "unit": self.unit,
            }
        )
        return base


@dataclass(slots=True)
class ControlChartResult(AnalyticalResult):
    """Moving-range evidence with explicit adjacent identities and frozen limits."""

    schema_version: str = "1.0"
    chart: Literal["moving_range"] = "moving_range"
    phase: Literal["I", "II"] = "I"
    moving_ranges: np.ndarray = field(default_factory=lambda: np.array([], dtype=float))
    pair_start_positions: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    pair_end_positions: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    pair_start_keys: np.ndarray | None = None
    pair_end_keys: np.ndarray | None = None
    lcl: float = 0.0
    center_line: float = 0.0
    ucl: float = 0.0
    signal_indices: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    signal_source_positions: np.ndarray = field(
        default_factory=lambda: np.array([], dtype=np.int64)
    )
    observation_count: int = 0
    baseline_observation_count: int = 0
    nsigmas: float = 3.0
    unit: str | None = None
    baseline_result_fingerprint: str | None = None

    def to_frame(self, backend: str = "polars"):
        """Return detached pair-level chart evidence in the requested backend."""
        start_keys = (
            self.pair_start_positions.tolist()
            if self.pair_start_keys is None
            else self.pair_start_keys.tolist()
        )
        end_keys = (
            self.pair_end_positions.tolist()
            if self.pair_end_keys is None
            else self.pair_end_keys.tolist()
        )
        signals = set(self.signal_indices.tolist())
        rows = {
            "pair_index": list(range(len(self.moving_ranges))),
            "start_source_position": self.pair_start_positions.tolist(),
            "end_source_position": self.pair_end_positions.tolist(),
            "start_key": start_keys,
            "end_key": end_keys,
            "moving_range": self.moving_ranges.tolist(),
            "signal": [index in signals for index in range(len(self.moving_ranges))],
        }
        return _native_result_frame(rows, backend)

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete pair identity, limits, signals, and baseline evidence."""
        base = AnalyticalResult.to_dict(self)
        base.update(
            {
                "schema_version": self.schema_version,
                "chart": self.chart,
                "phase": self.phase,
                "moving_ranges": self.moving_ranges.tolist(),
                "pair_start_positions": self.pair_start_positions.tolist(),
                "pair_end_positions": self.pair_end_positions.tolist(),
                "pair_start_keys": (
                    None if self.pair_start_keys is None else self.pair_start_keys.tolist()
                ),
                "pair_end_keys": (
                    None if self.pair_end_keys is None else self.pair_end_keys.tolist()
                ),
                "lcl": self.lcl,
                "center_line": self.center_line,
                "ucl": self.ucl,
                "signal_indices": self.signal_indices.tolist(),
                "signal_source_positions": self.signal_source_positions.tolist(),
                "observation_count": self.observation_count,
                "baseline_observation_count": self.baseline_observation_count,
                "nsigmas": self.nsigmas,
                "unit": self.unit,
                "baseline_result_fingerprint": self.baseline_result_fingerprint,
            }
        )
        return base


class OrderReconstructionResult(AnalyticalResult):
    """Inspectable order, activity/pass and source evidence under one declared policy.

    Tables retain scope columns. Filter to one scope before calling methods that
    require a single unique case column. Bundle snapshots detach this evidence.
    """

    def to_polars(self, table: str = "orders"):
        """Return a fresh frame of orders, collapsed activities, or source records."""
        import polars as pl

        if table not in ("orders", "activities", "activity_records", "source_records"):
            raise ValueError("Unknown reconstruction evidence table.")
        return pl.DataFrame(self.metadata[table]).select(self.metadata["table_columns"][table])


def _native_result_frame(rows: dict, backend: str):
    """Materialize a detached native result table without mandatory optional imports."""
    if backend == "polars":
        import polars as pl

        return pl.DataFrame(rows)
    if backend == "pandas":
        import pandas as pd

        return pd.DataFrame(rows)
    if backend == "pyarrow":
        import pyarrow as pa

        return pa.table(rows)
    raise ValueError("backend must be polars, pandas, or pyarrow.")


class ProcessMapResult(AnalyticalResult):
    """Typed direct-follow discovery counts with legacy read access to nodes and edges."""

    def __getitem__(self, key: str):
        """Retain existing nodes/edges lookup while returning detached observations."""
        from copy import deepcopy

        if key not in ("nodes", "edges"):
            raise KeyError(key)
        return deepcopy(self.metadata[key])

    def to_mapping(self) -> dict:
        """Export the original node/transition mapping for existing discovery consumers."""
        return {key: self[key] for key in ("nodes", "edges")}
