# 0019: Reconcile package boundaries and event-log contracts

- Status: Accepted
- Date: 2026-10-07
- Deciders: Maintainers
- Related requirements: UR-014, UR-015, UR-016, TR-001, TR-002, TR-013,
  TR-014, TR-015, TR-016, TR-017, TR-018
- Supersedes: the module-organization sections of ADR-0015
- Implements: ADR-0016
- Clarifies: ADR-0017 and ADR-0018

## Context

The repository had a stable package-root API but its implementation and documents
described conflicting internal structures. ADR-0016 required private `_kernels`,
while code remained in `kernels`. An `analytics` package duplicated the conceptual
responsibility of kernels and contained only placeholders. The public `EventLog`
type represented single timestamps while the CSV loader returned interval rows,
and support claims for PyArrow and branch-aware event metrics ran ahead of tests.

The v1.0 roadmap also promised no mandatory pandas or Polars dependency after
ADR-0018 had deliberately selected Polars as the canonical ingestion engine.

## Decision

1. Analytical implementations live in capability-oriented private modules under
   `lss4py/_kernels/`. Supported calculations are exported only from `lss4py`.
2. The placeholder `analytics` package is removed. A second analytical layer will
   not be introduced without a distinct responsibility and a new ADR.
3. `EventStream` names the single-timestamp observation model used by lightweight
   process discovery. `EventLog` remains a pre-1.0 compatibility alias.
4. `IntervalEventLog` is the public typed contract for validated activity intervals.
   It wraps an eager Polars frame with canonical `case_id`, `step_id`, `started_at`,
   and `completed_at` columns. Core event-log adapters return this type.
5. Public analytical functions may still accept governed eager native frames through
   Narwhals. pandas and Polars are supported when covered by parity tests. PyArrow is
   provisional until it passes the same method-level contract suite.
6. Polars remains a base dependency for canonical ingestion. The v1.0 promise is
   backend-neutral caller inputs, not an implementation with no concrete engine.
7. Workflows orchestrate domain operations and public contracts. They do not import
   adapters or private kernels. Reporting consumes typed domain results.
8. Documentation and compatibility claims must distinguish passing behavior from
   planned or xfailed behavior.

## Consequences

- Internal analytical modules can change without creating another public import path.
- Ingestion returns a self-identifying interval-log value instead of a bare frame.
- Existing `EventLog` callers continue to work during pre-1.0 migration, but new
  discovery code uses `EventStream`.
- Users may always extract a Polars frame with `IntervalEventLog.to_polars()`.
- Format adapters converge on one typed interval contract before calling analyses.
- PyArrow and branch-aware event metrics cannot be described as supported until
  their executable contract tests pass.
- Removing placeholder modules may break callers that imported experimental,
  undocumented stubs; those paths were never part of the package-root API.

## Alternatives considered

- **Keep both `analytics` and kernels.** Rejected because no stable responsibility
  separated the two and placeholders encouraged accidental support claims.
- **Return bare Polars frames from adapters.** Rejected because a frame does not
  identify which semantic event contract has already been validated.
- **Put the interval wrapper in adapters.** Rejected because kernels would then need
  to depend on the I/O layer or the package root would need calculation facades only
  to unwrap it.
- **Remove Polars before v1.0.** Rejected because it conflicts with the governed
  ingestion decision and adds complexity without improving caller interoperability.
