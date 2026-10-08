# 0018: Use Polars as the canonical ingestion backend

- Status: Accepted
- Date: 2026-09-18
- Deciders: Maintainers
- Related requirements: UR-014, UR-015, UR-016, TR-002, TR-013, TR-014,
  TR-015, TR-017
- Clarifies: ADR-0004, ADR-0008, ADR-0009, ADR-0017

## Context

LSS4PY wants analytical functions to accept supported eager dataframe backends
without making pandas index or null semantics part of the public result contract.
At the same time, file adapters need one predictable materialized representation.
Treating every dataframe engine as an equal adapter output adds branching to I/O,
validation, documentation, and extension contracts without improving an analysis.

The first governed ingestion workflow is an interval event log. It contains case
and step identifiers plus explicit start and completion timestamps. ADR-0019 names
the single-timestamp discovery model `EventStream` and introduces
`IntervalEventLog` as the typed wrapper for canonical interval data.

## Decision

Polars is the canonical eager materialization backend for LSS4PY core adapters.

- Polars is a base runtime dependency; pandas is an optional compatibility extra
  and development dependency.
- Core file adapters return `IntervalEventLog` values backed by validated Polars
  `DataFrame` objects, together with an `AdapterSchema`. They do not offer a
  per-call pandas output option.
- The first canonical interval-event schema is `case_id`, `step_id`, `started_at`,
  and `completed_at`. Source columns may be mapped into those names.
- Analytical functions continue to accept supported eager pandas, Polars, and
  PyArrow inputs through Narwhals. Polars-first ingestion does not make the public
  analytical API Polars-only.
- Event-log normalization may deliberately materialize non-Polars eager inputs as
  Polars. Provenance records the caller's original backend, and tests cover
  equivalent pandas and Polars results.
- Lazy and streaming ingestion requires a separate decision. Core statistical
  methods must not trigger an implicit collection.
- The format registry described by ADR-0017 may route CSV, OCEL, XES, or future
  formats, but every core format adapter targets the same canonical Polars shape.

## Alternatives considered

- **Pandas as the canonical adapter output.** Rejected because it preserves the
  dependency and index semantics the project is already migrating away from.
- **Let every adapter choose pandas or Polars.** Rejected because it doubles the
  adapter contract and pushes backend selection into source-specific code.
- **Expose Narwhals frames as adapter results.** Rejected because Narwhals is a
  compatibility facade rather than a user-facing storage and I/O engine.
- **Make every analytical API Polars-only.** Rejected because callers should not
  have to convert an already-supported eager frame before analysis.

## Consequences

- File-ingestion documentation and examples use Polars by default.
- pandas remains covered by analytical backend-parity tests but is not installed by
  the base package solely for ingestion.
- Adapter normalization, copying, timestamp parsing, and column renaming must be
  visible in `AdapterSchema` and errors must use `AdapterError`.
- The old public adapter documentation that promised selectable materialization
  backends is superseded.
