# 0028: Canonicalize supported eager analytical inputs to Polars

- Status: Accepted
- Date: 2026-11-05
- Deciders: Maintainers
- Related requirements: UR-015, TR-002, TR-010, TR-014, TR-017, TR-022
- Partially supersedes: ADR-0018 analytical-execution language
- Clarifies: ADR-0004, ADR-0009, ADR-0013, ADR-0024

## Context

LSS4PY accepts eager pandas, Polars and PyArrow inputs, but maintaining analytical
expressions through a dataframe-neutral facade left backend-specific conversion,
copying, null, object and timestamp behavior inside the calculation boundary.
Validation also needed one governed structural representation without making a
specific dataframe library part of the public input contract.

The v0.2.2 migration found concrete correctness risks: mutable pandas sources
could alias canonical values, pandas conversion could accidentally require
PyArrow, heterogeneous object columns needed explicit detached storage, and
duplicate and timestamp identity needed semantics stricter than a validation
library's defaults. The accepted 0.2.1 result and invalid-input contracts,
original source provenance and optional-backend installation boundary had to
remain intact.

ADR-0018 already selects Polars for canonical ingestion. This decision extends
that representation to analytical execution while retaining broad public eager
inputs.

## Decision

- Public tabular analyses continue to accept governed eager pandas DataFrames,
  Polars DataFrames and PyArrow Tables. Lazy or distributed plans are rejected
  and never collected implicitly.
- Narwhals is confined to the private compatibility boundary. It recognizes
  eager native inputs, assists conversion of selected columns to Polars and
  restores native output only for explicit preparation operations. Analytical
  kernels do not execute Narwhals expressions.
- Each analytical call creates a detached canonical Polars frame containing only
  its declared columns. Full source schema, row count and order remain available
  as provenance evidence without copying unused analytical columns.
- The caller's backend is the source backend; Polars is the execution backend.
  Results report the source backend and its version rather than relabeling every
  analysis as Polars.
- pandas indexes never define row or analytical identity. APIs use explicit
  portable keys or source positions.
- Pandera is private structural-validation machinery over canonical Polars only.
  It does not coerce values, drop rows, mutate caller data or define the public
  exception contract.
- LSS4PY owns public errors, issue codes, duplicate policy, governed timestamp
  precision, units, portable identity, missingness and analytical cross-column
  semantics. Pandera findings are translated into those contracts.
- Copy and allocation behavior is explicit. Selected values are detached to
  protect caller immutability; no zero-copy guarantee is made. pandas and
  PyArrow remain optional and absent from the base installation.

## Alternatives considered

- **Continue analytical execution through Narwhals expressions.** Rejected
  because backend-specific behavior remained observable inside calculations and
  complicated one authoritative validation path.
- **Validate and calculate independently in each native backend.** Rejected
  because it multiplies semantic implementations and parity risk.
- **Require callers to provide Polars.** Rejected because it would violate the
  accepted backend-neutral public input requirement.
- **Collect lazy inputs automatically.** Rejected because collection cost,
  ordering and failure behavior must be explicit public decisions.
- **Canonicalize complete source frames or promise zero-copy conversion.**
  Rejected because unused wide columns should not become analytical allocations,
  while detached selected values are required for immutable evidence.

## Consequences

- One canonical representation now governs structural validation and dataframe
  execution while public inputs remain backend-neutral.
- Differential fixtures freeze both valid result payloads and invalid-input
  behavior. Backend, source-preservation, R-reference and installed-wheel gates
  remain required.
- Pandera and four support distributions join the base installation. Against the
  Phase 1 baseline, the wheel grows 6,136 bytes and the installed package count
  grows from 39 to 44; pandas and PyArrow still do not leak into the base install.
- On the governed 20,000-row corpus, public validation adds 10–39 milliseconds,
  `describe` adds 0.5–9.3 milliseconds and isolated process high-water memory
  rises by 25–37 MiB. These local measurements are regression evidence, not
  service-level guarantees.
- The measured cost is accepted because the boundary removes backend-dependent
  correctness paths, protects canonical values from source mutation, centralizes
  validation semantics and preserves exact governed behavior.
- ADR-0018 remains authoritative for adapter ingestion and canonical event-log
  materialization; its implication that analytical execution may remain
  dataframe-neutral is superseded by this decision.

## Requirement reconciliation

- **UR-015 and TR-002:** broad eager public inputs remain accepted without manual
  caller conversion.
- **TR-010:** Polars, Narwhals and Pandera are governed core dependencies; pandas
  and PyArrow remain optional.
- **TR-014:** Narwhals remains the recognition, conversion and native-restoration
  boundary, not the analytical execution engine.
- **TR-017:** equivalent governed results and errors are verified after
  canonicalization.
- **TR-022:** reusable data-quality reports gain private noncoercing
  Pandera-backed structural evidence while LSS4PY retains semantic ownership.

