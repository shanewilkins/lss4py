# 0014: Versioning and migration policy

- Status: Proposed
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: TR-012, TR-033

## Context

LSS4PY is pre-1.0 and will undergo significant changes across v0.2–v0.9 (roadmap).
Bundles and examples must remain reproducible, but public APIs will evolve.
Users need a clear policy on when breaking changes are acceptable and how to migrate.

## Decision

LSS4PY follows a **strict deprecation cycle** with an explicit migration window:

### Deprecation Policy

1. **Feature deprecation:**
   - Announce in release notes with removal version (e.g., "Removed in 0.3.0").
   - Use `@deprecated()` decorator; issue `DeprecationWarning` at runtime.
   - Old function/API remains functional for ≥2 release cycles.
   - Removal is only allowed at major milestones (v0.3, v0.4, etc.).

   Example:

   ```python
   @deprecated(removed_in="0.3.0", alternative="capability_study")
   def capability_report(event_log):
       """Alias for capability_study; removed in v0.3."""
       return capability_study(event_log)
   ```

2. **Result schema changes:**
   - `AnalyticalResult.schema_version` increments (e.g., "capability_v1" →
     "capability_v2").
   - `AnalysisBundle` includes `schema_version`.
   - Loader includes `from_dict()` migration logic; old bundles auto-upgrade on
     load.

   Example:

   ```python
   @classmethod
   def load(cls, data: dict):
       schema_version = data.get("schema_version", "bundle_v1")
       if schema_version == "bundle_v1":
           return cls._migrate_v1_to_v2(data)
       return cls(**data)
   ```

3. **Numerical changes:**
   - Kernel version tracked in result provenance.
   - R parity fixtures updated when kernels change (ADR-0013).
   - Tolerance documented in fixture metadata.

4. **Documentation changes:**
   - Suitability registry (ADR-0007) question tags and categories are not stable
     pre-1.0.
   - Guidance candidates may change between releases.

### Migration Guides

Each release publishes a migration guide:

```markdown
# LSS4PY 0.2.0 → 0.3.0 Migration Guide

## Removed APIs
- `capability_report()` → `capability_study()` (deprecated in 0.2; removed in 0.3)
- `rolled_yield()` → `process_yield(rework=..., opportunities=...)`

## Schema Changes
- Bundle schema v1 → v2 (automatic migration on load)
- MetricResult now returns KeyedMetricResult (Narwhals-based)

## Breaking Changes
- Pandas no longer mandatory; use `uv pip install lss4py[pandas-support]` if needed
- Lead time returns KeyedMetricResult, not pandas Series
```

## Alternatives considered

- **Silent migration.** Fast but breaking; examples/bundles fail silently. Rejected:
  violates governance principle (ADR-0001).
- **No deprecation; immediate breaking changes.** Acceptable pre-1.0 but user-
  hostile. Rejected: examples and bundles need stability windows.
- **Version-gated features (old + new coexist).** Complex codebase. Rejected:
  maintenance burden; better to deprecate and remove.

## Consequences

- Deprecation warnings appear in v0.2–v0.3; removal in v0.3+.
- Users have ≥2 release cycles to update code and bundles.
- Tests include migration tests (old API still works, issues warning).
- Breaking changes trigger a minor version bump (e.g., v0.2.1 → v0.3.0) and are
  highlighted in release notes.
- v1.0 commits to semantic versioning; breaking changes only in major versions.
- CI includes checks for deprecated API usage (warns on deprecation imports).

### Example Timeline

**v0.2.0 (Aug 2026):**
- New API: `capability_study()`
- Old API: `capability_report()` → `@deprecated(removed_in="0.3.0")`

**v0.2.1 (Sep 2026):**
- Users have 1 release to migrate

**v0.3.0 (Oct 2026):**
- `capability_report()` removed
- Bundle schema v1 → v2 (auto-migrated on load)
- Migration guide published
