# 0024: Explicit data-quality reports and opt-in normalization

- Status: Accepted
- Date: 2026-10-19
- Deciders: Maintainers
- Related requirements: UR-005, UR-015, UR-016, TR-005, TR-014, TR-015, TR-017, TR-022
- Clarifies: ADR-0008, ADR-0010, ADR-0018, ADR-0019

## Context

Interval ingestion validates structural inputs, while analytical kernels have
method-specific missingness and domain rules. Practitioners also need reusable
preflight evidence for other eager tables. Silently consolidating every existing
validator would change established calculation semantics. Data preparation also
needs explicit exclusions and source-row identity for an auditable rerun.

## Decision

Add immutable `ColumnRule`, `DataContract`, `ColumnProfile`, `DataIssue`, and
`DataValidationReport` domain contracts. `validate_data` inspects declared schema,
keys, missingness, duplicates, numeric domains, timestamps and units through the
eager Narwhals boundary. Stable issue codes carry severity, column roles and
original row positions. Contract and report serialization are versioned.

`normalize_data` shares that inspection engine and returns `NormalizedData` with
before/after reports, transformations and retained source positions. It copies
only declared columns into canonical Polars, normalizes null/NaN and timestamps,
and removes missing or duplicate rows only under explicit flags. Missing exclusion
precedes deduplication. It does not coerce numerical text or convert units. Aware
timestamps become UTC; native normalization uses microsecond precision. Other
blocking findings and empty prepared results fail explicitly.

Implementations remain private kernels with public package-root exports. No I/O,
numerical dependency, analytical method selection, or second analytical layer is
introduced. Existing analyses and interval-log validators retain their current
contracts. The two preparation functions are not analytical catalog candidates.

ADR-0010's proposed global diagnostic registry and migration of every analytical
warning are not prerequisites for this scoped report contract. Existing
AssumptionNote/AssumptionReport and analytical provenance stay compatible.

## Alternatives considered

- Mutate or clean during validation: rejected because inspection must preserve
  source evidence and exclusions require caller intent.
- Automatically run preflight in every existing analysis: deferred because each
  method has governed domain and missingness semantics that must not change.
- Return a cleaned native frame without evidence: rejected because callers need
  original positions, declared policies, and findings to explain selected data.
- General schema inference and ETL: excluded; callers declare semantic roles and
  continue to own units, cohorts and selection decisions.

## Consequences

The normalization contract documents materialization, column selection and
precision explicitly. Reports are portable between eager backends without
relying on pandas indexes or concrete dtype names. The validation scope does not
claim normality, stability, method suitability or complete distribution diagnostics;
TR-022 remains partial. General bundle restoration remains separate work.
