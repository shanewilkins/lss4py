# LSS4PY v0.2 Progress & Continuation Guide

**Last updated:** 2026-10-12
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
- [Analysis guidance](analysis-guidance.md): decorator registration for all nine
  supported calculations, immutable method metadata, deterministic candidate
  queries, requirements/assumptions/alternatives/limits, and non-execution tests.

- [Shared backend contracts](backend-contracts.md): all seven tabular calculations
  across pandas, pandas with duplicate/non-default indexes, Polars, and provisional
  Arrow; full-payload comparison, input preservation, keys/group ordering, invalid
  domains, missing fields, and unsupported/lazy input rejection. CI requires Arrow.
- Parity regressions corrected: row-wise lead time parses Polars timestamp strings
  and preserves fractional seconds through Narwhals; interval normalization retains
  pandas nulls rather than turning missing case IDs into string identifiers.

- [Governed numerical references](reference-fixtures.md): four versioned test
  datasets, NIST-certified location/spread and independent arithmetic for all eight
  original supported calculations; explicit tolerances, source/license/schema metadata,
  artifact checksums, invalid-input cases, and offline catalog validation.
  Genuine SixSigma 0.11.1 Cp/Cpk/Z/yield outputs are now generated with R 4.6.1,
  a checksummed generator and session provenance. A second run reproduced the
  artifacts exactly. They are reference-only until corresponding Python methods
  are implemented. Cp/Cpk point and interval cases now have passing Python parity
  tests; eight specification Z cases also pass. Defect/rework yield remains reference-only.

- [Cp/Cpk capability indices](capability-indices.md): explicit Specification,
  overall sample variation, one/two-sided components, confidence intervals,
  exclusions, signed/degenerate diagnostics, and genuine R/backend tests.
  Capability Z distance now reuses Cpk with an explicit sigma shift;
  defect/rework yield is the next planned contract in the
  [next analytical slices](plans/next-analytical-slices.md), governed by
  [ADR-0020](adr/0020-delegate-numerical-algorithms-and-own-analytical-contracts.md).

## Next work, in order

1. **Reusable validation reporting (UR-016).** Extend the existing input
   normalization beyond interval logs, with explicit missingness/duplicate/unit
   policies and structured diagnostics. Avoid changing formula semantics while
   consolidating validators. Broaden shared backend edge contracts for nulls,
   nonfinite values, coercion, and uncommon schemas; Arrow offset/fractional
   timestamp strings remain a documented provisional exception.
2. **Auditable bundle contract (UR-033) and result gaps (TR-009).** Review current
   result/bundle models against neutral versioned serialization and rerun
   requirements; retain input references and software/method context.
3. **Guidance expansion (UR-017, TR-019).** Add study-design/outcome/predictor
   metadata as future analyses arrive. Schema suitability checks remain separate
   from catalog filtering. Keep practitioner selection explicit.
4. **Retained-method parity (TR-007).** Consume the generated Cp/Cpk/Z/yield
   reference baselines as corresponding Python capabilities arrive; extend cases
   and record intentional validation/contract differences. Additional retained R
   method families still need generated fixtures.
5. **v0.2 acceptance.** Complete requirement evidence, migration/worked examples,
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
