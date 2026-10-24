# LSS4PY v0.2 progress and continuation

Updated 2026-10-24. **Local acceptance corrections are complete.** Package metadata is the
unreleased 0.2.0 candidate; official publication/verification remains pending. The [dated acceptance audit](assessments/v02-release-readiness.md) and
[machine-readable requirement matrix](assessments/v02-release-readiness.json) own
the current verification snapshot. The roadmap continues to own release scope;
requirement registers own status and criteria.

## Implemented and verified

The private kernel boundary, explicit root exports, typed calculation results,
Polars ingestion and optional eager analytical backends are implemented. Shared
backend contracts cover the original metrics and prepared book calculations;
PyArrow now passes the supported ISO/native and measurement contracts. [Data quality](data-quality.md),
[CTQs/specifications](specifications.md), thirteen registered
[analysis candidates](analysis-guidance.md), and
[audited bundles](analysis-bundles.md) provide the contract foundation.

[Descriptive statistics](descriptive-statistics.md),
[Cp/Cpk and governing-limit Z](capability-indices.md), and
[defect/rework yield](defect-yield.md) have governed numerical references and
explicit conventions. The [reference catalog](reference-fixtures.md) contains five
versioned datasets, including genuine R SixSigma outputs and the pinned book case.

The dedicated [book preview](book-preview.md) is implemented with supplied data,
rendered output, an executed notebook, a chapter-ready excerpt and an audited
bundle. Numeric preparation, nearest-rank P90, fixed-deadline promise evaluation
and cohort PCE pass their independent acceptance values.

All thirteen selected [simulation sources](simulation-ingestion.md) ingest with
declared schemas, source hashes and validation evidence. The separate public
[activity-to-order reconstruction](order-reconstruction.md) is also implemented:
39 complete orders match the independent prepared summaries, retaining all 330
source records, load/pass/classification evidence and five corrections across
five orders. This delivers the declared v0.3-owned reconstruction slice early;
it does not reassign release ownership or complete the wider v0.3 MVP.

## Completed acceptance follow-through

The older timing unit/domain defects, exact binary validation, row identity/native
exports, per-result provenance, Arrow ISO parsing, explicit guidance/selection,
typed discovery results and core optional-dependency boundary are fixed. Current
reference and contract criteria are verified against implemented APIs; future
method families remain unclaimed. The registers now show 36 inherited/current
requirements Satisfied and only TR-038 Partial for actual publication.

## Next work, in order

1. Review the 0.2.0 candidate and its [release notes](releases/v0.2.0.md) and
   [migration guide](migration-v0.2.md). The dated gate snapshot is source-fingerprinted.
2. Tag/publish through the governed workflow. It requires source quality/Arrow,
   metadata/version identity and installed-wheel checks, then verifies the exact
   official PyPI package in a fresh environment. This has not run for 0.2.0.
3. Update the sibling book's normal package dependency/lockfile and render Chapter 9
   after that official package is verified. UR-046/TR-045 retain this book gap;
   no local source override replaces publication integration.

## Deferred scope

Branch-aware interval wait/PCE, general branch reconstruction, lifecycle pairing,
OCEL interchange and later belt workflows remain outside the delivered slice.
Full R-package parity, complete capability studies, SPC, simulation and reporting
workflows are not implemented merely because placeholder modules exist. Preserve
supported claims in the README, compatibility matrix and roadmap.

## Release gates

Run the locked pre-push hooks and additional CI gates; package metadata validation
currently needs a separate Twine invocation. See the audit for exact commands and
results. Keep PyArrow installed and require it for the full backend suite. The
installed-wheel ecosystem journey must pass in an isolated environment. Passing
these implementation checks does not override open requirement acceptance.

The [audit generator](../tools/audit_v02_readiness.py) re-reads roadmap ownership,
requirement/traceability catalogs and the timing probes. Regenerate its JSON after
status or scope changes; it does not publish packages or decide to waive criteria.
