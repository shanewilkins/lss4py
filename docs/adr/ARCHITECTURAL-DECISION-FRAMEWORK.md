# Architectural Decision Framework: LSS4PY v0.2–v1.0

**Date:** 2026-09-02  
**Status:** Draft for Review  
**Audience:** Maintainers, Ecosystem Partners  

This document recommends approaches for 10 core architectural decisions, scoped to v0.2 (Contract Foundation) through v1.0 (Stable). Decisions are grounded in:

- Existing codebase patterns (dataclass models, pandas current state, validation structure)
- User base: balanced (advanced practitioners + learners + data analysts)
- Opinionation: moderate (sensible defaults + guidance; user can override)
- Visualization: results only; plotting external responsibility
- Pandas optional by v0.2; Narwhals-only for new APIs
- Extras within lss4py (gated imports for viz/simulation/optimization/PM4Py)
- Ecosystem packages: managed separately; lss4py is analytics core
- Serialization: JSON portability required
- Backends: Pandas + Polars fully; PyArrow stretch
- Scale: hundreds of thousands of rows; batch analysis
- R parity: pragmatic (same structure; small numerical differences OK)

---

## 1. Result Model Hierarchy & Serialization

### Current State
- `MetricResult`, `PercentileProfile`, `AssumptionReport` are standalone dataclasses
- No base class; no serialization contract
- Assumptions collected per-result; warnings absent

### Problem
- Results don't share a common versioning or serialization interface
- Bundles (TR-033) lack a canonical shape
- Different analyses expose assumptions differently

### Approach A: Protocol-Based (Structural Typing)
**Pros:**
- No deep inheritance; good for gradual adoption
- Each analysis owns its result shape
- Serialization is per-type (Pydantic validators, `__post_init__`, etc.)

**Cons:**
- Inconsistent serialization across analyses
- Hard to build generic bundle/export logic
- Users must learn each result's serialization API

### Approach B: Base Result Class + Mixins (Recommended)
**Pros:**
- Shared versioning, provenance, and serialization layer
- Consistent bundle parity across all analyses
- Gradual migration: inherit from base; keep domain-specific fields
- Easy to add post-hoc assumptions/diagnostics

**Cons:**
- Inheritance hierarchy; some overhead for simple results
- Base class must remain minimal and stable pre-1.0

### Approach C: Composition (ResultEnvelope)
**Pros:**
- Each analysis stays independent
- Envelope is purely metadata; no coupling to domain logic

**Cons:**
- Extra wrapping layer; users always unwrap to get to analysis-specific fields
- Result discovery becomes harder (users don't know what's inside an envelope)

### **Recommendation: Approach B**

**Structure:**

```python
# src/lss4py/domain/results.py
@dataclass(slots=True)
class AnalyticalResult:
    """Base class for all LSS4PY multi-value analyses."""
    
    schema_version: str  # e.g., "capability_v1", "spc_v1"
    created_at: datetime
    method: str  # e.g., "normal_capability", "moving_range_chart"
    
    # Provenance
    input_fingerprint: str | None = None  # Hash of inputs for audit trail
    software_version: str = "0.2.0"  # Populated at module load
    backend: Literal["pandas", "polars", "pyarrow"] = "pandas"
    
    # Assumptions, warnings, diagnostics
    assumptions: list[AssumptionNote] = field(default_factory=list)
    warnings: list[AssumptionNote] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    
    # Interpretation context
    interpretation_limits: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Serialize to JSON-portable dict."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AnalyticalResult":
        """Deserialize from JSON dict with schema validation."""
        # Validate schema_version; migrate if needed
        return cls(**data)
```

Domain-specific results inherit and extend:

```python
@dataclass(slots=True)
class CapabilityResult(AnalyticalResult):
    cp: float
    cpk: float
    cpu: float | None
    cpl: float | None
    z_score: float
    specification_model: SpecificationModel
    mean_estimate: float
    variation_estimate: float
    sample_size: int
    confidence_level: float | None
    # ... etc
```

**Serialization** (TR-033):
- Use `dataclasses.asdict()` + `json.JSONEncoder` with custom handlers for datetime, Decimal
- Store in versioned bundles alongside input fingerprint + software versions
- Migration handled by schema_version + explicit converters

---

## 2. Numerical Kernel Delegation Strategy

### Current State
- NumPy, SciPy, statsmodels are dependencies
- No explicit kernel abstractions; calculations scattered across modules
- No parity fixtures yet

### Problem
- Hard to swap implementations (e.g., testing alternative algorithms)
- R parity fixtures need clear provenance
- Users don't know which upstream library provided a result

### Approach A: Thin Wrapper Functions
**Pros:**
- Minimal overhead; direct scipy/statsmodels calls
- Easy to debug; source code is visible

**Cons:**
- Replicate validation/handling across modules
- Hard to version parity independently

### Approach B: Kernel Submodule + Registry (Recommended)
**Pros:**
- Centralized validation and array extraction
- Clear provenance (result.kernel_version tracks upstream)
- Easy to test in isolation

**Cons:**
- Extra abstraction layer

### Approach C: Lazy Kernel Dispatch (callable registry)
**Pros:**
- Can swap at runtime (useful for testing alternatives)

**Cons:**
- Overkill for MVP; adds complexity

### **Recommendation: Approach B**

**Structure:**

```python
# src/lss4py/kernels/__init__.py
# Organize by LSS domain:
#   capability.py  (Cp, Cpk, Z, confidence intervals)
#   yield_.py      (yield, FTY, RTY, DPMO)
#   spc.py         (moving range, I-chart, other chart families)
#   msا.py         (Gage R&R, ANOVA, variance components)
#   inference.py   (confidence intervals, hypothesis tests, effect estimates)
#   quality_loss.py (Taguchi)

# Example: capability kernel
# src/lss4py/kernels/capability.py
@dataclass(slots=True)
class CapabilityKernelResult:
    """Raw output from capability calculation."""

    cp: float
    cpk: float
    cpu: float | None
    cpl: float | None
    z_score: float
    mean: float
    std_dev: float

    # Provenance
    formula_source: str  # e.g., "AIAG 4th ed" or "R SixSigma 0.11.1"
    scipy_version: str
    numpy_version: str

    confidence_interval: tuple[float, float] | None = None
    ci_method: str | None = None


def calculate_capability_normal(
    data: np.ndarray,
    lsl: float | None,
    usl: float | None,
    target: float | None = None,
    confidence_level: float | None = None,
    **kwargs,
) -> CapabilityKernelResult:
    """
    Calculate Cp, Cpk, Z for normal process data.

    Delegates to scipy/numpy; returns raw kernel output.
    Validation, typing, assumptions happen at workflow layer.
    """
    # Extract, validate array
    # Call scipy._stats for variation estimates
    # Return typed result with provenance
    ...


# Kernel registry for parity
_KERNEL_VERSIONS = {
    "capability_normal": ("AIAG", "scipy==1.15.0", "numpy==2.2.0"),
}


def get_kernel_version(kernel_name: str) -> str:
    """Get parity version string for fixtures."""
    return _KERNEL_VERSIONS.get(kernel_name, "unknown")
```

**R Parity Fixtures** (TR-007):
- Store in `tests/fixtures/r_parity/`
- Each fixture includes: inputs, expected outputs, R version, tolerance
- Parameterized pytest runs each fixture against the kernel
- Tolerance is documented and pragmatic (e.g., ±1e-6 for numeric stability)

---

## 3. Analysis Suitability Registry

### Current State
- No registry; no guidance system
- ADR-0003 proposes it; not implemented

### Problem
- UR-017: users should see candidates, not auto-selection
- No way to reason about which analysis fits a question/design
- Guidance needs to prevent misuse without being preachy

### Approach A: Decorator-Based Registry (Recommended)
**Pros:**
- Decentralized; each analysis documents itself
- Easy to discover (scan docstrings + metadata)
- Minimal overhead

**Cons:**
- Requires discipline; inconsistent if not enforced

### Approach B: Central Config (YAML/JSON)
**Pros:**
- Single source of truth; easy to audit

**Cons:**
- Couples governance to data files; hard to evolve with code
- Synchronization burden

### Approach C: Guidance API (separate module)
**Pros:**
- Decouples guidance from implementation

**Cons:**
- Hard to keep in sync; guidance can stale

### **Recommendation: Approach A + lightweight registry**

**Structure:**

```python
# src/lss4py/guidance/__init__.py
from dataclasses import dataclass
from enum import Enum


class AnalysisFamily(Enum):
    CAPABILITY = "capability"
    INFERENCE = "inference"
    SPC = "spc"
    MSA = "msa"
    QUALITY_LOSS = "quality_loss"
    # ... etc


@dataclass(slots=True)
class AnalysisSuitability:
    """Describes when an analysis is appropriate."""

    family: AnalysisFamily
    name: str  # e.g., "normal_capability_study"
    question_tag: str  # e.g., "can_process_meet_specs"

    # Applicability
    required_scale: int  # minimum sample size
    data_types: frozenset[str]  # e.g., {"numeric_continuous"}
    design_types: frozenset[str]  # e.g., {"observational", "one_sample"}

    # Assumptions
    assumptions: list[str]  # e.g., ["normality", "independence"]
    assumption_checks: frozenset[str]  # e.g., {"shapiro_wilk", "qq_plot"}

    # Alternatives
    alternatives: list[str]  # similar analyses

    # Interpretation limits
    limits: list[str]  # e.g., "does not imply causation"

    def can_run_with(self, data_type: str, sample_size: int, design: str) -> bool:
        """Quick check: is this analysis plausible for user's setup?"""
        return (
            data_type in self.data_types
            and sample_size >= self.required_scale
            and design in self.design_types
        )


# Registry (discoverable via inspect/reflection)
_REGISTRY: dict[str, AnalysisSuitability] = {}


def register_analysis(suitability: AnalysisSuitability):
    """Decorator to register an analysis."""

    def wrapper(func):
        _REGISTRY[suitability.name] = suitability
        func._lss4py_suitability = suitability
        return func

    return wrapper


def get_candidates(
    question_tag: str,
    data_type: str,
    sample_size: int,
    design: str,
) -> list[AnalysisSuitability]:
    """Find analyses that fit the user's question/setup."""
    return [
        s
        for s in _REGISTRY.values()
        if s.question_tag == question_tag and s.can_run_with(data_type, sample_size, design)
    ]


# Usage in analytics module
@register_analysis(
    AnalysisSuitability(
        family=AnalysisFamily.CAPABILITY,
        name="normal_capability_study",
        question_tag="can_process_meet_specs",
        required_scale=30,
        data_types=frozenset(["numeric_continuous"]),
        design_types=frozenset(["observational", "random_sample"]),
        assumptions=["normality", "independence"],
        assumption_checks=frozenset(["shapiro_wilk", "qq_plot"]),
        alternatives=["non_normal_capability", "empirical_capability"],
        limits=["requires stable process", "does not account for future special causes"],
    )
)
def capability_study(data: pd.DataFrame | pl.DataFrame, **kwargs) -> CapabilityResult: ...
```

**No Auto-Selection:** Guidance returns candidates; user explicitly chooses. Core analytics function requires explicit `method="normal_capability_study"` parameter.

---

## 4. Adapter & Normalization Layer

### Current State
- Adapter functions are stubs (NotImplementedError)
- No schema for normalized output
- No error handling from source SDKs

### Problem
- UR-014: users need predictable contracts for ingestion
- UR-016: validation must be separate from calculations
- Adapters must hide source SDK complexity

### Approach A: Per-Source Adapter Classes (Recommended)
**Pros:**
- Clear contracts per source (CSV, database, telemetry)
- Stateful (connection pooling, caching)
- Easy to mock for testing

**Cons:**
- More code per adapter

### Approach B: Functional Pipeline
**Pros:**
- Simple; composable

**Cons:**
- Hard to handle stateful sources (databases, APIs)

### Approach C: Adapter Factory + Registry
**Pros:**
- Runtime discovery; extensible

**Cons:**
- Indirection; harder to debug

### **Recommendation: Approach A**

**Structure:**

```python
# src/lss4py/adapters/contracts.py
@dataclass(slots=True)
class AdapterSchema:
    """Normalized schema after ingestion."""

    column_names: frozenset[str]
    column_types: dict[str, str]  # {"col": "datetime", "count": "int64", ...}
    row_count: int
    key_columns: list[str]  # e.g., ["case_id"] for event logs
    timestamp_columns: list[str] | None = None

    def validate_required_fields(self, required: Iterable[str]) -> list[str]:
        """Return missing required fields."""
        return [f for f in required if f not in self.column_names]


class TabularAdapter:
    """Base class for tabular ingestion."""

    def __init__(self, source_reference: str):
        """source_reference: path, URI, connection string, etc."""
        self.source_reference = source_reference

    def schema(self) -> AdapterSchema:
        """Inspect source without loading."""
        ...

    def load(self, **kwargs) -> tuple[pd.DataFrame | pl.DataFrame, AdapterSchema]:
        """Load and normalize; return native frame + schema."""
        ...

    def validate_load(self, required_fields: list[str]) -> list[str]:
        """Quick check before loading: are required fields present?"""
        return self.schema().validate_required_fields(required_fields)


# Concrete adapters
class CSVTabularAdapter(TabularAdapter):
    """Load CSV files."""

    def schema(self) -> AdapterSchema:
        # Peek at first few rows
        ...

    def load(self, **kwargs) -> tuple[pd.DataFrame | pl.DataFrame, AdapterSchema]:
        # Use Narwhals + backend parameter
        # Preserve dtypes; fail on parse errors
        ...


class EventLogAdapter:
    """Base class for event log ingestion."""

    def __init__(self, source_reference: str):
        self.source_reference = source_reference

    def schema(self) -> AdapterSchema:
        """Expected fields: case_id, activity, timestamp, [resource], [payload]."""
        ...

    def load(self, **kwargs) -> tuple[EventLog, AdapterSchema]:
        """Load and normalize to LSS4PY EventLog contract."""
        ...


# Usage
adapter = CSVTabularAdapter("process_data.csv")
schema = adapter.schema()
missing = schema.validate_required_fields(["case_id", "timestamp", "duration"])
if missing:
    raise AdapterError(f"Missing required fields: {missing}")

frame, validated_schema = adapter.load(backend="polars")
# frame is now a Polars DataFrame
# validated_schema documents what was loaded
```

**Error Handling:**
- Adapters catch source SDK exceptions; wrap in `AdapterError` with actionable message
- No SDK imports in analytics modules
- Schema validation is optional but recommended (UR-016)

---

## 5. Narwhals Integration Pattern

### Current State
- Narwhals is not yet a dependency
- Current code uses pandas directly

### Problem
- TR-002, TR-014, TR-015, TR-017: need backend-neutral API
- Extraction to NumPy must be explicit and tested

### Approach A: Narwhals Everywhere (Recommended)
**Pros:**
- Consistent; all tabular input goes through Narwhals
- Forces backend parity tests

**Cons:**
- Migration effort for existing code

### Approach B: Adapter Layer Only
**Pros:**
- Gradual adoption; existing code unchanged

**Cons:**
- Inconsistent; some code uses pandas, some Narwhals

### Approach C: Lazy Bridge (accept pandas, convert on demand)
**Pros:**
- Backward compatible

**Cons:**
- Hidden overhead; users don't know conversion is happening

### **Recommendation: Approach A (phased)**

**v0.2 Phase 1:** Add Narwhals dependency; convert adapters + new analyses  
**v0.3 Phase 2:** Convert remaining Yellow Belt metrics  
**v0.4+:** Remove pandas as mandatory; make it an optional extra

**Pattern:**

```python
# src/lss4py/adapters/_narwhals_helpers.py
import narwhals as nw
from narwhals.typing import IntoFrame


def load_frame(data: IntoFrame, backend: Literal["pandas", "polars", "pyarrow"] | None = None):
    """Normalize eager dataframe input."""
    frame = nw.from_native(data, eager_only=True, allow_series=False)

    if backend:
        # Materialize to requested backend
        native = frame.to_native()
        if backend == "polars":
            import polars as pl

            return pl.from_pandas(native) if isinstance(native, pd.DataFrame) else native
        # ... etc

    return frame


def extract_series(
    frame: nw.DataFrame,
    column: str,
    dtype: str | None = None,
) -> np.ndarray:
    """Extract validated column as NumPy array."""
    series = frame[column]

    if dtype:
        series = series.cast(dtype)

    # Handle nulls: drop or explicit value?
    if series.null_count() > 0:
        # User decision in calling function; here just document
        # Convert to native to get NaNs
        pass

    native = series.to_native()
    return np.asarray(native)


def result_from_native(
    output: pd.Series,
    keys: nw.Series,
    backend_hint: str,
) -> KeyedMetricResult:
    """Convert calculation result back to backend-neutral form."""
    # Preserve key column; return typed result
    ...


# Usage in workflow
def lead_time(
    event_log: IntoFrame,
    *,
    case_id_column: str,
    started_at_column: str,
    completed_at_column: str,
    unit: TimeUnit = "hours",
) -> KeyedMetricResult:
    """Calculate lead time per case."""

    frame = load_frame(event_log, backend=None)  # Stay in Narwhals

    # Extract keys and duration columns
    case_ids = frame[case_id_column]
    started = extract_series(frame, started_at_column, dtype="datetime[μs]")
    completed = extract_series(frame, completed_at_column, dtype="datetime[μs]")

    # Calculate in NumPy
    durations_seconds = (completed - started).astype("timedelta64[s]").astype(float)
    durations_unit = durations_seconds / _SECONDS_PER_UNIT[unit]

    # Return typed result with keys
    return KeyedMetricResult(
        keys=case_ids.to_native(),
        values=durations_unit,
        unit=unit,
        name="lead_time",
    )
```

**Backend-Parity Tests:**

```python
# tests/test_lead_time.py
import pandas as pd
import polars as pl
import pytest


@pytest.mark.parametrize("backend", ["pandas", "polars"])
def test_lead_time_parity(backend):
    """Ensure identical results across backends."""

    # Prepare same data in both backends
    pandas_frame = pd.DataFrame(
        {
            "case_id": ["A", "B", "A"],
            "started": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "completed": ["2026-01-05", "2026-01-04", "2026-01-06"],
        }
    )

    polars_frame = pl.from_pandas(pandas_frame)

    # Calculate with both
    result_pd = lead_time(pandas_frame, ...)
    result_pl = lead_time(polars_frame, ...)

    # Values should be numerically equivalent
    np.testing.assert_array_almost_equal(result_pd.values, result_pl.values)

    # Keys should match (order matters)
    assert result_pd.keys == result_pl.keys
```

---

## 6. Assumption, Warning & Diagnostic Model

### Current State
- `AssumptionNote` + `AssumptionReport` exist
- Warnings not yet surfaced consistently
- Diagnostics scattered (shapiro test, qq plot data, etc.)

### Problem
- UR-005, UR-017: users need to see assumptions before acting
- TR-022, TR-030: diagnostics need to be queryable, not just printed
- Different analyses expose diagnostics differently

### Approach A: Unified Note Hierarchy (Recommended)
**Pros:**
- Consistent treatment of assumptions/warnings/diagnostics
- Queryable; can filter by severity or code
- Integrates with bundles and serialization

**Cons:**
- Might be too uniform for complex diagnostics (e.g., full ANOVA tables)

### Approach B: Separate Diagnostic Class
**Pros:**
- Assumptions, warnings, diagnostics are distinct

**Cons:**
- Results become more complex; multiple fields to populate

### Approach C: Callable/Function Diagnostics
**Pros:**
- Lazy evaluation; expensive checks only on demand

**Cons:**
- Results are incomplete; users might miss critical diagnostics

### **Recommendation: Approach A + Diagnostic Registry**

**Structure:**

```python
# src/lss4py/domain/diagnostics.py


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(slots=True)
class DiagnosticNote:
    code: str  # e.g., "normality_fail_shapiro", "sample_size_low"
    message: str
    severity: Severity = Severity.INFO
    details: dict[str, Any] = field(default_factory=dict)  # e.g., {"p_value": 0.03}


class DiagnosticRegistry:
    """Centralized definitions for all diagnostic codes."""

    _CODES = {
        "sample_size_low": DiagnosticNote(
            code="sample_size_low",
            message="Sample size < 30; normal approximation may not hold.",
            severity=Severity.WARNING,
        ),
        "normality_fail_shapiro": DiagnosticNote(
            code="normality_fail_shapiro",
            message="Shapiro-Wilk test suggests non-normality.",
            severity=Severity.WARNING,
        ),
        "outliers_detected_zscore": DiagnosticNote(
            code="outliers_detected_zscore",
            message="Outliers detected via Z-score (>3σ).",
            severity=Severity.INFO,
        ),
        # ... more
    }

    @classmethod
    def create(cls, code: str, details: dict[str, Any] | None = None) -> DiagnosticNote:
        """Create a diagnostic note from a registered code."""
        if code not in cls._CODES:
            raise ValueError(f"Unknown diagnostic code: {code}")

        base = cls._CODES[code]
        if details:
            return DiagnosticNote(
                code=base.code,
                message=base.message,
                severity=base.severity,
                details=details,
            )
        return base


# Result model includes diagnostics
@dataclass(slots=True)
class AnalyticalResult(AnalyticalResult):
    assumptions: list[DiagnosticNote] = field(default_factory=list)
    warnings: list[DiagnosticNote] = field(default_factory=list)
    diagnostics: dict[str, DiagnosticNote] = field(default_factory=dict)


# Usage
def capability_study(data, lsl, usl, **kwargs) -> CapabilityResult:
    result = CapabilityResult(...)

    # Check assumptions
    if sample_size < 30:
        result.warnings.append(
            DiagnosticRegistry.create("sample_size_low", {"sample_size": sample_size})
        )

    # Run diagnostic tests
    shapiro_stat, shapiro_p = scipy.stats.shapiro(data)
    result.diagnostics["shapiro_wilk"] = DiagnosticRegistry.create(
        "normality_fail_shapiro" if shapiro_p < 0.05 else "normality_pass_shapiro",
        {"p_value": float(shapiro_p), "statistic": float(shapiro_stat)},
    )

    return result


# Serialization: DiagnosticNote -> dict -> JSON
def note_to_dict(note: DiagnosticNote) -> dict:
    return {
        "code": note.code,
        "message": note.message,
        "severity": note.severity.value,
        "details": note.details,
    }
```

**Interpretation:** Results carry assumptions + diagnostics so users (and bundles) can reason about reliability without external knowledge.

---

## 7. Optional Extras & Import Strategy

### Current State
- Extras defined in pyproject.toml (process-mining, simulation, optimization, visualization, storage)
- No gating logic yet

### Problem
- UR-012: core must work without viz/simulation/etc.
- Users should get helpful errors if they try viz without matplotlib installed

### Approach A: Try/Except at Import (Recommended)
**Pros:**
- Simple; lightweight
- Errors are immediate and clear

**Cons:**
- Verbose if many dependencies

### Approach B: Lazy Proxies (importlib)
**Pros:**
- No error until function is called
- Cleaner code

**Cons:**
- Errors are delayed; confusing to debug

### Approach C: Separate Entry Points
**Pros:**
- No coupling

**Cons:**
- Hard to discover (users don't know viz functions exist)

### **Recommendation: Approach A (centralized gating module)**

**Structure:**

```python
# src/lss4py/_extras.py
"""Centralized import gating for optional dependencies."""

import sys
from typing import Any


def _check_extra(name: str, install_group: str) -> None:
    """Raise helpful error if optional extra is not installed."""
    extras = {
        "matplotlib": ("visualization", "uv pip install lss4py[visualization]"),
        "seaborn": ("visualization", "uv pip install lss4py[visualization]"),
        "simpy": ("simulation", "uv pip install lss4py[simulation]"),
        "pm4py": ("process-mining", "uv pip install lss4py[process-mining]"),
        "pulp": ("optimization", "uv pip install lss4py[optimization]"),
        "pyarrow": ("storage", "uv pip install lss4py[storage]"),
    }
    
    if name not in sys.modules and name not in extras:
        raise ModuleNotFoundError(f"Unknown optional dependency: {name}")
    
    if name not in sys.modules:
        install_group, install_cmd = extras[name]
        raise ModuleNotFoundError(
            f"Optional dependency '{name}' is not installed. "
            f"Install the '{install_group}' extra with:\n  {install_cmd}"
        )


def get_extra(name: str) -> Any:
    """Import optional dependency with helpful error."""
    _check_extra(name, "")
    return __import__(name)


# Usage in workflow modules
def plot_capability_study(result: CapabilityResult, **kwargs):
    """Visualization only; returns matplotlib figure."""
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # Check at function boundary
    try:
        sns  # Will error if not installed
    except NameError:
        _check_extra("seaborn", "visualization")
    
    fig, axes = plt.subplots(2, 2)
    # ... plotting logic
    return fig


# Or gate entire module
# src/lss4py/reporting/visualization.py
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    _HAS_VISUALIZATION = True
except ImportError:
    _HAS_VISUALIZATION = False
    
    def __getattr__(name):
        if not _HAS_VISUALIZATION:
            raise ImportError(
                "Visualization module requires matplotlib and seaborn. "
                "Install with: uv pip install lss4py[visualization]"
            )


# Explicit check in docstring + type hints
def plot_capability_study(result: CapabilityResult) -> "matplotlib.figure.Figure":
    """
    Plot capability study results.
    
    Requires: lss4py[visualization]
    
    Raises:
        ImportError: if matplotlib or seaborn are not installed.
    """
    if not _HAS_VISUALIZATION:
        raise ImportError(
            "Visualization module requires matplotlib and seaborn. "
            "Install with: uv pip install lss4py[visualization]"
        )
    ...
```

**Base Installation Check (in CI):**

```bash
# .github/workflows/ci.yml
- name: Test base install (no extras)
  run: uv pip install lss4py --no-cache-dir
  
- name: Test analytics work without viz
  run: uv run python -c "from lss4py import lead_time; print(lead_time)"
  
- name: Test viz import fails gracefully
  run: |
    uv run python -c "from lss4py.reporting.visualization import plot_capability_study" 2>&1 | grep "visualization extra"
```

---

## 8. Visualization Result Contracts

### Current State
- No visualization layer; ADR-0002 says plotting is optional
- Seaborn, matplotlib in optional extras

### Problem
- UR-029: users need plots from results without recalculation
- TR-032: plots consume typed results; avoid hidden calculations
- No agreed-upon return type (matplotlib figure? Plotly? Object?)

### Approach A: Return Native Library Objects (Recommended)
**Pros:**
- Users already know matplotlib/plotly API
- No wrapping; easy to customize

**Cons:**
- Tight coupling to one plotting library
- Hard to swap later

### Approach B: LSS4PY Plot Wrapper
**Pros:**
- Consistent contract; can add LSS4PY methods

**Cons:**
- Extra indirection; users have to learn LSS4PY API

### Approach C: Data-Only (return dict/JSON)
**Pros:**
- Backend-agnostic; users choose rendering

**Cons:**
- Users have to write plotting code; defeats "make good LSS the default"

### **Recommendation: Approach A (pure matplotlib/plotly return)**

**Constraint:** Core analytics remain 100% independent of visualization.

**Pattern:**

```python
# src/lss4py/reporting/visualization.py (optional extra)


def plot_capability_study(
    result: CapabilityResult,
    *,
    style: Literal["matplotlib", "plotly"] = "matplotlib",
) -> Any:  # matplotlib.figure.Figure or plotly.graph_objects.Figure
    """
    Plot capability study results.

    Args:
        result: CapabilityResult from capability_study().
        style: "matplotlib" (default) or "plotly".

    Returns:
        matplotlib Figure or plotly Figure object.

    Notes:
        - No recalculation; uses result.diagnostics directly.
        - All limits, units, assumptions preserved from result.
        - Requires: lss4py[visualization]

    Examples:
        >>> from lss4py import capability_study
        >>> from lss4py.reporting.visualization import plot_capability_study
        >>> result = capability_study(data, lsl=10, usl=20)
        >>> fig = plot_capability_study(result, style="matplotlib")
        >>> fig.show()
    """

    if not _HAS_VISUALIZATION:
        raise ImportError(
            "Visualization requires matplotlib/seaborn. "
            "Install: uv pip install lss4py[visualization]"
        )

    if style == "matplotlib":
        return _plot_capability_matplotlib(result)
    elif style == "plotly":
        return _plot_capability_plotly(result)
    else:
        raise ValueError(f"Unknown style: {style}")


def _plot_capability_matplotlib(result: CapabilityResult) -> "matplotlib.figure.Figure":
    """Return matplotlib figure; seaborn styles applied."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    with sns.axes_style("whitegrid"):
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # Plot 1: Data histogram + normal curve
        ax = axes[0, 0]
        ax.hist(result.data, bins=30, density=True, alpha=0.6, label="Data")
        # ... overlay fitted normal
        ax.set_title("Histogram and Fitted Normal")

        # Plot 2: Q-Q plot
        ax = axes[0, 1]
        scipy.stats.probplot(result.data, dist="norm", plot=ax)
        ax.set_title("Q-Q Plot")

        # Plot 3: Capability indices
        ax = axes[1, 0]
        # Bar plot of Cp, Cpk, CPU, CPL
        ...

        # Plot 4: Diagnostic notes
        ax = axes[1, 1]
        ax.axis("off")
        diagnostic_text = "\n".join(f"• {note.message}" for note in result.diagnostics.values())
        ax.text(0.1, 0.9, diagnostic_text, transform=ax.transAxes, fontsize=10)

        plt.tight_layout()
        return fig


def _plot_capability_plotly(result: CapabilityResult) -> Any:
    """Return plotly Figure; interactive."""
    import plotly.graph_objects as go

    fig = go.Figure()

    # Subplots or traces
    # ...

    return fig
```

**Key Principle:**  
Plot functions **consume** typed results; they **never** recalculate. All necessary data (diagnostics, flagged observations, limits) is in the result already.

---

## 9. Testing Strategy for Cross-Backend Parity

### Current State
- Tests are pandas-only
- No Polars or PyArrow fixtures

### Problem
- TR-017: backend equivalence is mandatory, not nice-to-have
- R parity (TR-007) needs versioned fixtures
- Different backends might have numerical drift

### Approach A: Parameterized Fixtures (Recommended)
**Pros:**
- Clear; every test runs across all backends
- Drift is caught immediately

**Cons:**
- Test matrix explodes; slower CI

### Approach B: Smoke Tests + Regression Fixtures
**Pros:**
- Faster; focused validation

**Cons:**
- Might miss backend-specific bugs

### Approach C: Separate Test Suites
**Pros:**
- Each backend has its own fixtures

**Cons:**
- Hard to maintain; drift between suites

### **Recommendation: Approach A (with pytest parametrization + R fixtures)**

**Structure:**

```python
# tests/conftest.py

import pandas as pd
import polars as pl
import pytest

@pytest.fixture(params=["pandas", "polars"])
def backend(request):
    """Parametrize all tests across backends."""
    return request.param

@pytest.fixture
def sample_process_data(backend):
    """Provide identical data in both formats."""
    
    pandas_df = pd.DataFrame({
        "case_id": ["A", "B", "A", "C", "B"],
        "started": pd.to_datetime([
            "2026-01-01 08:00",
            "2026-01-01 09:00",
            "2026-01-01 08:30",
            "2026-01-01 10:00",
            "2026-01-01 09:30",
        ]),
        "completed": pd.to_datetime([
            "2026-01-01 10:00",
            "2026-01-01 11:30",
            "2026-01-01 09:00",
            "2026-01-01 12:00",
            "2026-01-01 11:00",
        ]),
    })
    
    if backend == "pandas":
        return pandas_df
    elif backend == "polars":
        return pl.from_pandas(pandas_df)


# tests/test_lead_time.py

def test_lead_time_calculation(sample_process_data, backend):
    """Lead time calculation should be identical across backends."""
    
    result = lead_time(
        sample_process_data,
        case_id_column="case_id",
        started_at_column="started",
        completed_at_column="completed",
        unit="hours",
    )
    
    expected_values = np.array([2.0, 2.5, 0.5, 2.0, 1.5])
    np.testing.assert_array_almost_equal(result.values, expected_values)
    
    # Keys should match (order matters)
    if backend == "pandas":
        assert list(result.keys) == ["A", "B", "A", "C", "B"]
    elif backend == "polars":
        assert result.keys.to_list() == ["A", "B", "A", "C", "B"]


# tests/fixtures/r_parity/

# Directory structure:
# r_parity/
#   capability/
#     normal_capability_v1/
#       inputs.json       # Input data + parameters
#       expected_outputs.json  # Expected Cp, Cpk, Z, etc.
#       metadata.json     # R version, scipy version, tolerance
#   spc/
#     moving_range_v1/
#       ...

# tests/test_r_parity.py

import json
from pathlib import Path

R_PARITY_DIR = Path(__file__).parent / "fixtures" / "r_parity"

def load_r_parity_fixture(family: str, name: str):
    """Load R parity fixture."""
    fixture_dir = R_PARITY_DIR / family / name
    
    with open(fixture_dir / "inputs.json") as f:
        inputs = json.load(f)
    
    with open(fixture_dir / "expected_outputs.json") as f:
        expected = json.load(f)
    
    with open(fixture_dir / "metadata.json") as f:
        metadata = json.load(f)
    
    return inputs, expected, metadata


@pytest.mark.parametrize(
    "family,name",
    [
        ("capability", "normal_capability_v1"),
        ("spc", "moving_range_v1"),
        # ... add more as implemented
    ],
)
def test_r_parity(family, name):
    """Ensure numerical parity with R SixSigma."""
    
    inputs, expected, metadata = load_r_parity_fixture(family, name)
    
    # Run LSS4PY calculation
    if family == "capability":
        result = capability_study(
            pd.DataFrame(inputs["data"]),
            lsl=inputs["lsl"],
            usl=inputs["usl"],
        )
        actual = {
            "cp": result.cp,
            "cpk": result.cpk,
            "z_score": result.z_score,
        }
    
    # Compare within tolerance
    tolerance = metadata.get("tolerance", 1e-5)
    for key in expected:
        assert abs(actual[key] - expected[key]) < tolerance, (
            f"{key}: expected {expected[key]}, got {actual[key]}"
        )


# CI Integration
# .github/workflows/ci.yml
jobs:
  test:
    strategy:
      matrix:
        python-version: ["3.14"]
        backend: ["pandas", "polars"]
    steps:
      - name: Run tests with ${{ matrix.backend }}
        run: |
          uv run pytest \
            -v \
            --backend=${{ matrix.backend }} \
            --tb=short
```

**R Parity Fixture Format:**

```json
{
  "inputs.json": {
    "data": [[1.5, 2.1, 1.9, 2.3], ...],
    "lsl": 1.0,
    "usl": 3.0,
    "sample_size": 50
  },
  "expected_outputs.json": {
    "cp": 1.33,
    "cpk": 1.10,
    "z_score": 3.3
  },
  "metadata.json": {
    "r_package": "SixSigma",
    "r_version": "0.11.1",
    "r_fixture_date": "2026-08-08",
    "scipy_version": "1.15.0",
    "numpy_version": "2.2.0",
    "tolerance": 1e-5,
    "notes": "Normal capability with two-sided spec"
  }
}
```

---

## 10. Versioning & Migration Policy

### Current State
- Pre-1.0; roadmap owns major releases (v0.2, v0.3, etc.)
- ADR-0001 proposes governance; no migration plan yet

### Problem
- TR-012: examples must remain runnable across versions
- Bundle schemas (TR-033) need migration paths
- Public APIs can change pre-1.0, but users need clear guidance

### Approach A: Strict Deprecation Cycle (Recommended)
**Pros:**
- Clear migration path; users know when to update
- Bundles can be upgraded automatically

**Cons:**
- Slower to evolve

### Approach B: Silent Migration
**Pros:**
- Fast; no need for transition code

**Cons:**
- Breaking; existing examples/bundles fail

### Approach C: Version-Gated Features
**Pros:**
- Both old and new code can coexist

**Cons:**
- Complex codebase; hard to maintain

### **Recommendation: Approach A (with explicit migration window)**

**Policy:**

```python
# src/lss4py/_version.py
__version__ = "0.2.0"
__major_release__ = "v0.2"  # Roadmap release owning this version


# Deprecation utilities
import warnings


def deprecated(
    removed_in: str,  # e.g., "0.3.0"
    alternative: str | None = None,
    message: str | None = None,
):
    """Decorator for deprecated functions."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            msg = message or (
                f"{func.__name__} is deprecated and will be removed in {removed_in}. "
            )
            if alternative:
                msg += f"Use {alternative} instead."

            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        wrapper.__doc__ = f"[DEPRECATED in {removed_in}] {func.__doc__ or ''}"
        return wrapper

    return decorator


# Usage
@deprecated(removed_in="0.3.0", alternative="capability_study")
def capability_report(event_log: EventLog) -> AssumptionReport:
    """Alias for capability_study; removed in v0.3."""
    return capability_study(event_log)
```

**Bundle Migration:**

```python
# src/lss4py/reporting/bundles.py


@dataclass
class AnalysisBundle:
    schema_version: str  # e.g., "bundle_v1", "bundle_v2"
    results: list[AnalyticalResult]
    metadata: dict

    @classmethod
    def load(cls, data: dict) -> "AnalysisBundle":
        """Load and migrate if needed."""
        schema_version = data.get("schema_version", "bundle_v1")

        if schema_version == "bundle_v1":
            return cls._migrate_v1_to_v2(data)
        elif schema_version == "bundle_v2":
            return cls(**data)
        else:
            raise ValueError(f"Unknown bundle schema: {schema_version}")

    @classmethod
    def _migrate_v1_to_v2(cls, data: dict) -> "AnalysisBundle":
        """Upgrade v1 bundle to v2."""
        # Transform old structure -> new structure
        data["schema_version"] = "bundle_v2"
        # ... other migrations
        return cls(**data)
```

**Documentation:**

```markdown
# LSS4PY Version Policy

## Pre-1.0 Stability

Versions 0.1–0.9 are under active development. Breaking changes are allowed
with notice:

- **Feature deprecation:** Announced in release notes; deprecated APIs work for
  2+ release cycles with DeprecationWarning.
- **Result schema changes:** Bundle schema_version increments; old bundles are
  migrated on load.
- **Numerical changes:** Kernel version tracked; parity fixtures updated.

## Upgrade Guide by Release

### 0.2.0 → 0.3.0
- `capability_report()` → `capability_study()`
- Bundle schema v1 → v2 (automatic migration)
- Narwhals-based APIs do not return pandas Series; use KeyedMetricResult instead

### 0.3.0 → 0.4.0
- (Planned: Green Belt features; see roadmap)
```

**Testing Migrations:**

```python
# tests/test_migrations.py


def test_bundle_v1_loads_as_v2():
    """Old bundles can be loaded and upgraded."""

    v1_data = {
        "schema_version": "bundle_v1",
        "results": [...],
    }

    bundle = AnalysisBundle.load(v1_data)
    assert bundle.schema_version == "bundle_v2"
    assert len(bundle.results) == len(v1_data["results"])
```

---

## Implementation Roadmap

### v0.2 (Contract Foundation)

1. **Result model base class** (Decision 1) ✓
2. **Narwhals integration** (Decision 5) – add dependency, convert adapters
3. **Kernel organization** (Decision 2) – yield, capability, SPC stubs
4. **Adapter contracts** (Decision 4) – CSV, event-log adapter functions
5. **DiagnosticNote registry** (Decision 6) – centralize assumptions/warnings

### v0.3 (Yellow Belt MVP)

6. **Numerical kernels** – fill capability, yield, SPC stubs
7. **Analysis registry** (Decision 3) – decorate existing analyses
8. **Backend-parity tests** (Decision 9) – parameterized pandas/Polars suite
9. **R parity fixtures** (Decision 9) – check in initial fixtures + tests
10. **Optional extras gating** (Decision 7) – visualization, simulation

### v0.4+

- **Visualization contracts** (Decision 8) – plot functions consuming results
- **Deprecation cycle** (Decision 10) – first breaking changes with warning
- **Pandas → optional** – Narwhals-only internal; pandas is extra

---

## Summary Table

| Decision | Recommendation | Rationale |
|---|---|---|
| 1. Result models | Base AnalyticalResult class | Shared versioning, provenance, serialization |
| 2. Kernels | Submodule + registry | Clear boundaries; testable in isolation |
| 3. Analysis registry | Decorator-based + DiagnosticRegistry | Discoverable; prevents silent auto-selection |
| 4. Adapters | Per-source classes with schema contract | Stateful, clear error handling |
| 5. Narwhals | Full integration; phased migration | Backend-neutral by design |
| 6. Diagnostics | Unified DiagnosticNote hierarchy | Queryable assumptions/warnings/diagnostics |
| 7. Extras | Centralized gating + helpful errors | Clear installation guidance |
| 8. Visualization | Native matplotlib/plotly return; no wrapping | Users know the API; no recalculation |
| 9. Backend parity | Parameterized tests + R fixtures | Automatic drift detection |
| 10. Versioning | Strict deprecation cycle with migration helpers | Clear upgrade path |

