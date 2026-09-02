# 0008: Adapter normalization layer

- Status: Proposed
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: UR-014, UR-016, TR-013, TR-014

## Context

LSS4PY needs to ingest data from multiple sources (CSV files, databases, telemetry
APIs, event logs) without forcing users to write normalized loaders for every
source. However, source SDKs should not leak into analytical APIs (UR-016, UR-012).

Currently, adapter functions are stubs (`NotImplementedError`). A clear normalization
contract is needed so adapters can validate and normalize data before it reaches
calculations.

## Decision

Implement adapters as per-source classes inheriting from base adapter types
(`TabularAdapter`, `EventLogAdapter`) in `src/lss4py/adapters/`. Each adapter:

1. Takes a source reference (path, URI, connection string).
2. Provides a `schema()` method to inspect columns/types without loading.
3. Provides a `load(backend=...)` method to load and normalize to a backend-neutral
   form (Narwhals DataFrame for tabular; `EventLog` domain model for event logs).
4. Returns an `AdapterSchema` documenting column names, types, row count, required
   keys, and any transformations applied.

For stateless sources (e.g., CSV), also provide functional pipeline helpers
(`load_csv_and_normalize()`) for quick use cases.

Adapters handle:

- **Schema validation:** required fields, type coercion, null handling
- **Error translation:** source SDK exceptions → `AdapterError` with actionable
  messages (no SDK imports leak into analytics)
- **Backend selection:** user chooses pandas, Polars, or PyArrow

Concrete adapters:

- `CSVTabularAdapter` – CSV files
- `EventLogCSVAdapter` – CSV with event-log semantics
- `DatabaseAdapter` – SQL databases (future; extensible)

## Alternatives considered

- **Functional pipeline only.** Simpler for CSV. Rejected: no reuse; hard for
  stateful sources (databases, APIs).
- **Adapter factory + registry.** Runtime discovery. Rejected: indirection; harder
  to debug; not necessary pre-1.0.

## Consequences

- Adapters are optional imports; not required for core analytics.
- `AdapterSchema` is the canonical contract between adapters and calculations;
  validation is optional but recommended (UR-016).
- Adapter tests use mock sources and schema validation; no real databases required.
- Breaking changes to adapter contracts trigger deprecation (ADR-0014).
- Optional extras (e.g., `storage`, `databases`) gate specific adapter dependencies.
