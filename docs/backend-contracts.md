# Analytical backend contracts

The shared suite exercises the original seven public tabular calculations with eager
pandas and Polars frames. `takt_time` accepts scalar arguments and has no
dataframe backend. `EventStream` discovery and validation use their own domain
contract; they are not tabular-input APIs.

## Shared fixtures and comparisons

`tests/conftest.py` supplies frame factories, aligned measurement/stage records,
interleaved interval records, process bindings, and neutral-payload comparisons.
The default factory matrix includes pandas with a normal index, pandas with
non-default duplicate labels, and Polars. Existing descriptive tests reuse it.
`tests/test_backend_contracts.py` extends that matrix with provisional PyArrow
Tables. Frames are built independently from records; test construction does not
convert pandas to Polars or Arrow.

The shared suite checks hand-calculated estimates and compares the complete
serialized result against the Polars result. It removes only computation time
and backend identity, which necessarily differ. Numerical comparisons use
`rtol=1e-12` and `atol=1e-12`; identifiers, ordering, counts, warnings, units,
parameters, and method metadata must match. These synthetic fixtures are not R
SixSigma reference cases and make no cross-language parity claim. The additional
`capability_indices` API has the same four-backend contract in
`tests/test_capability.py`, including separately governed genuine R Cp/Cpk cases.

Row-wise timing results use positions (`keys=None`), without carrying pandas
index labels into the result. Interval results use explicit case identifiers in
first-observed case order, even when event rows are interleaved or step order is
reversed. Grouped descriptive results retain first-observed group order and
missing-key groups. Calls preserve the input frame, including pandas indexes.

Missing fields and tested invalid domains raise `ValidationError` on each tested
backend. Interval identifiers and timestamps cannot be null; unknown steps and
blank identifiers fail validation. Descriptive missingness follows its explicit
policy. `tests/test_input_contracts.py` checks that all eight tabular methods
reject raw dictionaries, record lists, NumPy arrays, pandas/Polars Series, and
Polars LazyFrames with `TypeError`; input rejection does not collect a lazy plan.

## Timestamp calculations

Row-wise `lead_time` explicitly parses string columns through Narwhals and uses
its duration namespace to extract microseconds, preserving fractional seconds.
Native datetime columns retain timezone information. ISO string parsing infers
formats through the backend; arbitrary mixed formats and mixed timezone
awareness are not guaranteed equivalent. Prefer native datetime columns for
complex timestamp data. The shared tests cover ordinary ISO strings and native
timezone-aware values, with a 1.25-second precision regression.

Interval ingestion materializes Polars, and validates source null masks before
string identifiers can be inferred from missing pandas values. Source pandas
and Arrow frames are copied into the canonical frame; no pandas index is used.

## Provisional PyArrow scope

The current shared cases pass for numeric duration calculations, binary stage
yields, descriptive statistics and grouping, per-case interval lead time, and
row-wise lead time with basic ISO strings or native timestamp columns. This is
case-by-case evidence, not a guarantee for every Arrow schema or timestamp format.

**Known exception:** Arrow's inferred parsing of the tested timezone-offset ISO
strings (including a fractional completion time) raises `ValidationError`.
Supply native Arrow timestamp columns for that case. The test is marked strict
`xfail`, restricted to `ValidationError`: a successful future implementation
produces an XPASS failure and requires revisiting this exception. Unrelated errors
remain failures.

Install the locked optional storage extras to run Arrow cases:

```bash
uv sync --locked --group dev --extra storage
uv run --locked pytest tests/test_backend_contracts.py --require-pyarrow
```

Without PyArrow, local Arrow cases skip explicitly. CI installs the storage extra
and passes `--require-pyarrow` so absence is an error rather than a silent skip.
Polars remains the canonical file-ingestion backend; pandas and Arrow remain
optional analytical-input backends.

The suite is scaffolding for broader contracts. Complete timing/yield policies
for nulls, nonfinite values, coercion, and uncommon schemas still need reusable
validation work. Broader Arrow compatibility and governed numerical-reference
fixtures remain open; the relevant requirements are recorded as partial.


## Explicit data-quality inspection and preparation

`validate_data` and `normalize_data` share an independently tested eager-backend
contract for missingness, finite numeric/integer domains, boolean and text roles,
key/row duplicates, ISO/native timestamps, unit declarations and source preservation.
See [data quality](data-quality.md) for the complete policies and materialization
costs. Offset and fractional ISO timestamps are checked by the declared parser;
normalization can supply native UTC timestamp columns to downstream calculations.
The existing row-wise Arrow parsing exception above remains a separate contract.
No calculation silently invokes this preparation or changes its missingness policy.
