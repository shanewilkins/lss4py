# 0005: Result model hierarchy and base class

- Status: Proposed
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: TR-009, TR-020, TR-033

## Context

LSS4PY analyses return typed domain models (e.g., `MetricResult`, `PercentileProfile`,
`CapabilityResult`), but currently these are independent dataclasses with no shared
base or versioning contract. This creates several problems:

- No consistent way to serialize results for bundles (TR-033)
- Assumptions and diagnostics are surfaced differently across analyses
- Provenance (software version, backend used, input fingerprint) is not consistently
  tracked
- Result schema versions cannot be managed or migrated automatically
- Downstream consumers (notebooks, dashboards) cannot assume a stable envelope

## Decision

All multi-value analytical results will inherit from a shared base class
`AnalyticalResult` in `src/lss4py/domain/results.py`.

The base class provides:

- **Schema versioning:** `schema_version` (e.g., "capability_v1", "spc_v1") for
  forward compatibility and automatic migration.
- **Provenance:** `created_at`, `method`, `input_fingerprint` (hash of inputs for
  audit trail), `software_version`, `backend` (pandas, polars, pyarrow).
- **Assumptions and diagnostics:** Shared fields for `assumptions`, `warnings`,
  `diagnostics`, `interpretation_limits` so all analyses expose reasoning.
- **Serialization:** `to_dict()` and `from_dict()` methods using dataclass
  serialization + JSON-portable types (datetime → ISO string, etc.).

Domain-specific results (e.g., `CapabilityResult`, `ControlChartResult`) inherit
and extend with their own fields. Single-value results (e.g., `MetricResult` for
a scalar) remain lightweight and do not inherit unless they grow to multi-field
structures.

## Alternatives considered

- **Protocol-based (structural typing).** Each result type independently manages
  serialization. Rejected: inconsistent contracts; bundles lack a canonical
  envelope; difficult to build generic export logic.
- **Composition (ResultEnvelope wrapper).** Each analysis stays independent;
  metadata wrapped separately. Rejected: extra unwrapping required; users don't
  know what's inside; harder to discover result-specific fields.

## Consequences

- All new multi-value analyses must inherit from `AnalyticalResult` and populate
  `schema_version`, `method`, `assumptions`, `warnings`.
- Existing `MetricResult` and `PercentileProfile` are refactored to inherit (minor
  breaking change; addressed in v0.2 deprecation window).
- Bundles (TR-033) use this base contract for versioning and migration.
- Serialization tests become mandatory for all inherited result types.
- Post-hoc addition of assumptions/diagnostics to results is supported through
  shared fields and typed `DiagnosticNote` (see ADR-0010).
