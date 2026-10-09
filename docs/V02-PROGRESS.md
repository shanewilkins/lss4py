# LSS4PY v0.2 Progress & Continuation Guide

**Last updated:** 2026-10-09
**Status:** Contract foundation in progress; package version remains 0.1.0.

The [roadmap](roadmap.md) owns release targeting. Requirement CSVs own status and
acceptance criteria. This guide records current implementation and the next work;
it does not declare v0.2 complete.

## Implemented foundation

- Private `_kernels` and explicit package-root exports, enforced layer boundaries,
  typed timing/yield results, provenance, and serialization.
- Supported eager analytical inputs through Narwhals; canonical Polars ingestion
  per ADR-0018. pandas is an optional analytical backend.
- CSV interval-log ingestion with schema reporting, field normalization,
  identifier/timestamp/duration validation, and canonical `IntervalEventLog`.
- Process-aware per-case event-log lead time, explicit keys, declared parallel
  and rework topology validation, and pandas/Polars parity cases.
- [`describe`](descriptive-statistics.md): typed location, spread, shape, tail,
  missingness, grouping, warnings, provenance, and pandas/Polars tests.
- [`Specification` and `AnalysisWindow`](specifications.md): immutable CTQ,
  units, direction, acceptance limits, opportunities, grouping/cohort/window,
  decision context, validated versioning, and serialization. Declaration does
  not imply automatic filtering or conformance calculations.
- [Analysis guidance](analysis-guidance.md): decorator registration for all eight
  supported calculations, immutable method metadata, deterministic candidate
  queries, requirements/assumptions/alternatives/limits, and non-execution tests.

## Next work, in order

1. **Shared backend-parity scaffolding (TR-002, TR-014).** Consolidate fixtures
   for timing, yield, descriptive, and interval-log paths. Exercise pandas and
   Polars consistently, non-default indexes, unsupported/lazy inputs, and
   document the provisional PyArrow surface.
2. **Governed numerical-reference fixtures (TR-007, TR-037).** Establish a
   manifest with source/version/license/checksum and expected values/tolerances.
   Add retained R SixSigma reference cases with actual generated outputs and
   provenance. Do not label hand-calculated Python cases as R parity.
3. **Reusable validation reporting (UR-016).** Extend the existing input
   normalization beyond interval logs, with explicit missingness/duplicate/unit
   policies and structured diagnostics. Avoid changing formula semantics while
   consolidating validators.
4. **Auditable bundle contract (UR-033) and result gaps (TR-009).** Review current
   result/bundle models against neutral versioned serialization and rerun
   requirements; retain input references and software/method context.
5. **Guidance expansion (UR-017, TR-019).** Add study-design/outcome/predictor
   metadata as future analyses arrive. Schema suitability checks remain separate
   from catalog filtering. Keep practitioner selection explicit.
6. **v0.2 acceptance.** Complete requirement evidence, migration/worked examples,
   packaging checks, and release gates before bumping the version.

## Deferred scope

Branch-aware interval-event wait time and process-cycle efficiency remain future
work. Those current APIs require explicit measurement columns. Capability, SPC,
hypothesis testing, simulation, and reporting workflows are not stable merely
because placeholder modules/result types exist. See the README and roadmap for
current public scope and later Yellow/Green/Black Belt ownership.

The old September checklist described adapter and kernel work that has since
landed. Do not recreate `_adapters` or move canonical ingestion away from Polars
based on that obsolete plan; current architecture and ADR-0018/0019 govern.

## Validation

Run the locked pre-push gates and the additional CI checks before a release:

```bash
uv run --locked pre-commit run --all-files --hook-stage pre-push
uv run --locked ruff check .
uv run --locked bandit -r src/lss4py --skip B101
uv run --locked pip-audit --desc
uv build
```

CI also verifies the built wheel outside the source tree. Repository coverage is
currently configured at 90%; see `pyproject.toml` for covered-slice exclusions.
Some event-log integration tests retain expected failures for deferred branch
calculations. Validation outcomes for this change are recorded in the accompanying
review/chat; commands here are continuation instructions, not a permanent claim
that future checkouts pass.
