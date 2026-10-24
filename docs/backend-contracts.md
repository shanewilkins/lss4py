# Analytical backend contracts

Current native-frame APIs accept eager pandas DataFrames, Polars DataFrames and
PyArrow Tables through a shared Narwhals boundary. Unsupported inputs raise
`UnsupportedInputError`, both `ValidationError` and TypeError-compatible. Duplicate
or non-string column identities fail explicitly. Lazy/distributed plans are never
collected. Canonical CSV/domain ingestion still materializes Polars.

Typed `NumericEventLog` reconstruction has its own method-specific observation
contract and canonical frame; it does not pretend to accept arbitrary native
summary tables. Scalar `takt_time` accepts finite positive real quantities.

## Equivalence and identity

Shared and method-specific suites check values, neutral serialized results,
source preservation, invalid domains, missingness, dtype roles, key/group ordering
and repeated pandas indexes across all three backends. Comparison removes only
creation time, backend identity and backend library version. Semantic schema
fingerprints and all other numerical/context evidence must agree. Numerical
comparisons use declared tolerances; genuine R comparisons use their separately
versioned fixture tolerances.

Row-wise timing retains explicit `metadata["row_positions"]`. An optional
`key_column` binds unique portable scalar identities; duplicate, missing, blank
or nonfinite keys fail. Unkeyed legacy results retain `keys=None` and explicit
positional identity. `TimingResult.to_frame("polars" | "pandas" | "pyarrow")`
allocates an independent table with row_position, key, value and unit columns.
Interval lead times use declared case keys in first-observed order. No pandas
index is used as analytical identity. Grouped summaries retain first-observed
keys, including missing-key groups.

## Domains and missingness

Measured timing operands must be real numeric, finite and nonnegative. Per-row
PCE requires strictly positive lead; VA cannot exceed lead. Wait inputs use a
single declared common unit, defaulting to hours. No text/boolean duration
coercion or implicit unit conversion occurs. Exact binary stages may be numeric
0/1 or declared booleans; fractional stages are never truncated. Missing timing
or stage values fail. Empty/undefined aggregate denominators fail explicitly.

Descriptive and capability calculations retain their explicit omit/raise missing
policy and inspectable exclusions. Infinity is invalid. Strict prepared-order,
deadline and numeric activity contracts reject missing endpoints and invalid
identities; declared normalization remains opt-in. No calculation silently drops
records or invokes preparation on the caller's behalf.

Calendar endpoints are native datetimes or ISO date/time strings, handled at
microsecond precision. Aware instants normalize to UTC; naive instants remain
naive, and mixed awareness fails. Date-only strings and numeric operating times
are rejected. Fractional/timezone-offset ISO inputs now pass on Arrow as well as
pandas/Polars; the former strict xfail is removed. Non-ISO formats and arbitrary
nested/distributed frames are outside the contract.

## Allocations and provenance

Native inputs are read eagerly without mutation. Inspection/parsing and numeric
extraction allocate O(n) observations/arrays; normalization and native exports
allocate detached frames. Numeric log `.to_polars(copy=False)` deliberately exposes
its underlying frame, so reconstruction revalidates it before analysis. Retained
reconstruction evidence adds O(n) storage; these costs are not lazy execution.

Results retain schema identity, source order, missing policy, measurement context,
core/backend software versions and parameters. Audited bundles add exact source
bytes, selections, linked specifications and version checks. These records
identify a calculation; they do not automatically choose its question or cohort.

Run the required backend matrix with the locked storage extra:

```sh
uv run --locked --extra storage pytest --require-pyarrow
```

CI requires Arrow rather than silently skipping it. Installed-wheel storage tests
also verify ISO/native timing, domain rejection, explicit choices and Arrow result
exports. Optional process-mining, simulation and optimization declarations do not
claim implemented LSS4PY workflows for those engines.
