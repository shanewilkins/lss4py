"""Typed analytical result models with provenance, assumptions, and interpretation context.

All public analytical methods return instances of AnalyticalResult or its subclasses.
Results preserve method metadata, input schema, assumptions, warnings, backend information,
and creation timestamp to enable reproducibility and auditable analysis chains.

Belt Level: Yellow Belt (v0.2 MVP foundation; completed workflows v0.3+)
Suitable When: You need to capture and communicate analytical decisions with full transparency.
Not Suitable When: You need raw NumPy arrays (convert results with .to_numpy() instead).

See ADR-0003, ADR-0004, TR-009, TR-015, TR-016, TR-020, TR-033.
"""

import json
from abc import ABC
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal, TypeVar

import numpy as np

from lss4py.domain.models import AssumptionNote

ResultT = TypeVar("ResultT")


@dataclass(slots=True)
class Provenance:
    """Metadata about how a result was computed.

    Provenance is immutable and captures the method, version, parameters, backend,
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
        return json.dumps(self.to_dict(), indent=2)


@dataclass(slots=True)
class AnalyticalResult(ABC):
    """Base class for all public analytical results.

    Every result from a Yellow Belt or higher analysis includes:
    - name: Human-readable description of what was analyzed
    - provenance: Full record of how the result was computed
    - interpretation_context: Guidance on when and how to use this result
    - metadata: Arbitrary key-value context (e.g., flags, tags)

    Results are immutable to prevent silent invalidation of provenance.
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

    def to_json(self) -> str:
        """Serialize result to JSON."""
        return json.dumps(self.to_dict(), indent=2)


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
    """Equivalent Z-score (defect rate proxy)."""

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize capability result to a dictionary."""
        base = super().to_dict()
        base.update(
            {
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
class AnalysisBundle:
    """Versioned container for one or more related analysis results.

    An AnalysisBundle bundles typed results, shared provenance assumptions,
    interpretation context, and specifications for serialization and round-tripping.
    Used in notebooks, reports, and analytical workflows.

    See TR-033, ADR-0002.
    """

    name: str
    """Title of the analysis bundle (e.g., 'Q3 Intake Process Baseline')."""

    results: list[AnalyticalResult]
    """List of analytical results (at least one)."""

    bundle_version: str = "1.0"
    """Schema version of this bundle format."""

    package_version: str = "0.2.0"
    """LSS4PY version that created this bundle."""

    created_at: datetime = field(default_factory=datetime.now)
    """Timestamp when the bundle was created."""

    cohort_definition: str | None = None
    """Human-readable description of the analyzed population."""

    specification_metadata: dict[str, Any] | None = None
    """References to CTQ and specification models used in analysis."""

    interpretation_notes: str | None = None
    """Bundle-level interpretation guidance or caveats."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Arbitrary key-value metadata (e.g., project ID, analyst name)."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize bundle to a dictionary."""
        return {
            "bundle_type": "AnalysisBundle",
            "bundle_version": self.bundle_version,
            "name": self.name,
            "package_version": self.package_version,
            "created_at": self.created_at.isoformat(),
            "cohort_definition": self.cohort_definition,
            "specification_metadata": self.specification_metadata,
            "interpretation_notes": self.interpretation_notes,
            "metadata": self.metadata,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self) -> str:
        """Serialize bundle to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisBundle:
        """Deserialize bundle from a dictionary.

        Note: This is a skeleton implementation. Full deserialization with result
        type dispatch will be implemented in v0.3 workflows.
        """
        if data.get("bundle_type") != "AnalysisBundle":
            raise ValueError("Invalid bundle type")

        # Validate bundle version compatibility
        bundle_version = data.get("bundle_version", "1.0")
        if bundle_version != "1.0":
            raise ValueError(f"Unsupported bundle version: {bundle_version}")

        # Placeholder: results deserialization with type dispatch
        # Full implementation in v0.3+ with AnalysisRegistry
        results = data.get("results", [])
        if not results:
            raise ValueError("Bundle must contain at least one result")

        return cls(
            name=data["name"],
            results=[],  # Stub: would dispatch on result_type
            bundle_version=bundle_version,
            package_version=data.get("package_version", "0.2.0"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            cohort_definition=data.get("cohort_definition"),
            specification_metadata=data.get("specification_metadata"),
            interpretation_notes=data.get("interpretation_notes"),
            metadata=data.get("metadata", {}),
        )
