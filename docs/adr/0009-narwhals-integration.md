# 0009: Narwhals integration for backend-neutral inputs

- Status: Proposed
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: UR-012, UR-015, TR-002, TR-014, TR-015, TR-016, TR-017

## Context

Current stable metrics accept pandas DataFrames and return pandas Series. This
makes pandas semantics (index, missing-value behavior) part of the public contract,
forcing Polars or PyArrow users to convert or accept duplicated workflows.

ADR-0004 proposes dataframe-neutral inputs, but implementation is incomplete.
Narwhals is designed for library authors needing dataframe-agnostic operations
across pandas, Polars, and PyArrow without installing those backends.

## Decision

Make Narwhals a base runtime dependency. All new tabular analytics APIs will:

1. Accept eager DataFrames via Narwhals' `IntoFrame` protocol (pandas, Polars,
   PyArrow supported; lazy inputs rejected with actionable error).
2. Use Narwhals internally for column/row operations; extract to NumPy arrays only
   for numerical kernels (via `extract_series()` helpers).
3. Return typed `KeyedMetricResult` instead of pandas Series, with explicit key
   columns and backend-neutral values.
4. Pass parameterized backend-parity tests (pandas, Polars) for every tabular
   calculation (ADR-0013).

**Migration timeline:**

- **v0.2:** Add Narwhals dependency; convert adapters and new analyses.
- **v0.3:** Convert existing Yellow Belt metrics (lead_time, yield, etc.).
- **v0.4+:** Pandas becomes optional extra; Narwhals-only internal APIs.

After migration, `lead_time()` example:

```python
def lead_time(
    event_log: IntoFrame,  # Accepts pandas, Polars, PyArrow
    *,
    case_id_column: str,
    started_at_column: str,
    completed_at_column: str,
    unit: TimeUnit = "hours",
) -> KeyedMetricResult:
    frame = nw.from_native(event_log, eager_only=True)
    # ... Narwhals operations
    return KeyedMetricResult(keys=..., values=..., unit=unit)
```

## Alternatives considered

- **Keep pandas as canonical internal frame.** Simplest but forces conversions on
  other backends. Rejected: violates UR-015.
- **Use Polars as canonical.** Changes favored backend rather than removing coupling.
  Rejected: same coupling problem.
- **Use `__dataframe__` protocol.** Official guidance from pandas/Polars discourages
  new use. Rejected.
- **Arrow tables only.** Requires user conversion before every analysis. Rejected:
  weakens Python-native experience.

## Consequences

- Current pandas-returning APIs require pre-1.0 migration with deprecation window.
- Backend equivalence tests become mandatory for all tabular calculations.
- Extracting arrays for NumPy kernels must be explicit and tested (null handling,
  dtype, materialization policy).
- Zero-copy behavior is not promised; correctness takes priority.
- Lazy/distributed frames (Dask, Spark) remain future scope; not supported in v0.2+.
- Pandas is no longer mandatory for base install after v0.3 (optional extra).
