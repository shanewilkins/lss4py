# Preparing for v0.2

This guide covers the current working tree and proposed v0.2 contract. It is not
a published-version guarantee. The candidate now consistently reports 0.2.0; there are no local
release tags establishing a complete published-0.1-to-0.2 API diff. Check the
[release audit](assessments/v02-release-readiness.md) before upgrading a deployed
book or application. The draft [release notes](releases/v0.2.0.md) list additions.

## Public imports and observation models

Import supported calculations from `lss4py`. Private `_kernels` and historical
placeholder analytical modules are not supported import paths. Do not rewrite
callers to rely on experimental study or workflow stubs.

`EventLog` remains a compatibility alias for single-time discovery `EventStream`.
The interval CSV adapter returns `IntervalEventLog`; extract its canonical frame
with `.to_polars()` when a native table is needed. Keep that calendar contract
separate from numeric `NumericEventLog` activity/lifecycle observations. A single
timepoint lifecycle record needs a declared pairing policy before order
reconstruction; loading it does not infer intervals.

Core CSV ingestion produces Polars. Callers may supply supported eager pandas,
Polars or supported Arrow inputs directly to governed analytical APIs. Do not
convert frames merely to satisfy an assumed pandas-index identity contract.
Bind explicit case fields or retain source positions, and consult the
[backend limits](backend-contracts.md). Lazy/distributed inputs are unsupported.

## Explicit preparation

Preparation is opt-in; older calculations do not automatically run `validate_data`.
Declare roles and units before calculating with external data:

```python
import polars as pl
from lss4py import ColumnRule, DataContract, describe, validate_data

observations = pl.DataFrame({"case": ["001", "002", "003"], "minutes": [10.0, 20.0, 30.0]})
contract = DataContract(
    columns=(ColumnRule("case", kind="string"), ColumnRule("minutes", minimum=0, unit="minutes")),
    key_columns=("case",),
    duplicates="error",
)
report = validate_data(observations, contract=contract)
assert report.valid, report.to_json()
summary = describe(observations, column="minutes", unit="minutes", missing="raise")
assert summary.mean == 20
```

For CSVs use `CSVTabularAdapter(..., contract=...).load()` to retain the adapter
schema, validation and source hash, or `load_csv(..., contract=...)` for a frame.
`load_tabular_records` now implements declared CSV loading and requires a contract;
its earlier implementation was a stub. Literal string identifiers such as `001`
remain strings. No invalid rows are silently dropped. Explicit normalization and
exclusion choices belong in retained audit context.

## Timing and counting semantics

`lead_time` handles calendar endpoints; cumulative operating minutes must use
prepared order contracts or numeric activity reconstruction. They are no longer
coerced into datetime offsets. No midnight or overnight time is fabricated.

`wait_time(..., unit="minutes")` declares the common input/output unit; its legacy
default remains hours. It computes lead minus cycle without implicit conversion.
Both operands must be finite and nonnegative, and cycle cannot exceed lead. Its
residual does not separately identify setup, queues, rework or avoidable waste.
Missing/nonfinite timing and scalar inputs now fail rather than returning invalid
values or apparent 0% efficiency. Binary stage fractions are no longer truncated.
Declared boolean options must be actual booleans.

Timing APIs also accept `key_column` for unique portable scalar identities. Without
one, results retain positional identity; pandas indexes are ignored.
`result.to_frame("polars" | "pandas" | "pyarrow")` allocates an independent table
with explicit positions, keys, values and units. Invalid/duplicate keys fail.
Arrow now accepts the supported ISO offset/fractional datetime inputs. Numeric
operating times remain a distinct contract.

`map_process` now returns `ProcessMapResult`, preserving `result["nodes"]` and
`result["edges"]` lookup. Use `.to_mapping()` when a consumer needs the old plain
mapping; use `.to_dict()`/`.to_json()` for the full typed/auditable result. This is
a documented pre-1.0 result-contract change.

`select_analysis(name, reason=..., cohort=..., design_type=...)` stores an explicit
choice without inspecting data or executing analysis. Call `choice.record(result)`
to retain it in a matching typed result; scalar choices can be stored as
`choice.to_dict()` in audit context. Outcome/predictor and sampling declarations
are exposed for all thirteen registered methods.

Per-row PCE remains the default. For cohort efficiency explicitly select
`aggregation="cohort"` and bind case, lead and VA fields, units, clock, boundary,
cohort and VA convention. Use the matched-case ratio of sums; averaging row
percentages answers a different question. Promise misses compare eligible
readiness to the fixed deadline, with equality on time.

`describe(..., percentile_method="nearest_rank")` opts into rank-based tails;
the default stays linear. Its `median` remains the conventional middle-value
average for even samples. `measurement_sum` sums retained measurements; `total`
still counts original observations. Older serialized descriptive results without
a sum restore with `measurement_sum=None`.

Existing binary funnel yields retain their API. Defect/rework counts instead use
`process_yield` and an explicit opportunity population; defect and rework losses
must be disjoint. Specification Z distance is not generic standardization and a
sigma shift is an explicit assumption, not measured long-term performance.

## Bundle restoration and audit upgrades

`AnalysisBundle.from_json(saved)` restores results without recalculation or
resolving external sources. Legacy v1 is readable without inventing missing
software versions, source bytes or selections. `legacy.with_audit_context(...)`
upgrades only after the caller supplies that missing evidence. Unknown future
versions are rejected.

`AnalysisBundle.capture` requires source references, explicit result/input links,
cohort and software versions. Capture preserves method/package/backend versions;
do not rewrite a historical result's version to make an upgrade look current.
See the [complete capture example](analysis-bundles.md) and existing v1/v2
round-trip and migration regressions in `tests/test_bundles.py`.

ADR-0014 remains a proposed historical policy with illustrative APIs. Its example
automatic upgrades and deprecation decorator are not implemented guarantees;
accepted ADR-0019/0025 and the current bundle schema govern these operations.

## Executable worked examples

From a checkout with locked dependencies:

```sh
uv run --locked python examples/white_belt/preview.py
uv run --locked python examples/white_belt/reconstruct.py
uv run --locked python tools/reconstruct_book_simulation.py
```

The first consumes honestly labeled supplied order summaries. The second
reconstructs every order from the pinned 330 activity records. The third calculates
the four readouts from reconstructed orders and saves an audited bundle. All are
standalone; they do not require the sibling book or running its simulator.
Installed-wheel tests also execute the prepared notebook and reconstruction.

After acceptance, release and verify the official artifact first. Then update the
book's normal dependency lock and render its actual Chapter 9 environment. Do not
substitute local source overrides into the published book environment.
