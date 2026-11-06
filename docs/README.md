# LSS4PY documentation

Start with [current status and continuation](STATUS.md), then the
[0.3 workflow and delivery plan](plans/v03-yellow-belt.md). The README distinguishes
published 0.2.2 behavior from unreleased checkout additions.

## Product and engineering contracts

- [Roadmap](roadmap.md): release scope and ownership.
- [User requirements](requirements/user-requirements.csv),
  [technical requirements](requirements/technical-requirements.csv), and
  [traceability conventions](requirements/README.md): outcomes, criteria and status.
- [Analysis journey](analysis-journey.md): intended practitioner workflow.
- [Architecture decisions](adr/README.md): durable decisions and their status.
  Accepted ADRs govern their scope; proposed/superseded records are not new obligations.
- [R SixSigma compatibility](sixsigma-compatibility.md): retained evidence,
  intentional differences and gaps, separate from product completion.

## Analytical and integration guides

- [Backend contracts](backend-contracts.md), [data quality](data-quality.md),
  [CTQs/specifications](specifications.md), and [analysis guidance](analysis-guidance.md).
- [Descriptive statistics](descriptive-statistics.md),
  [mean confidence intervals](mean-confidence-interval.md), and
  [distribution profiles/plots](distribution-profile.md).
- [Capability indices](capability-indices.md) and [defect/rework yield](defect-yield.md).
- [Unreleased MR charts](control-charts.md), including the
  [worked monitoring script](../examples/yellow_belt/monitoring.py), and
  [unreleased capability studies](capability-study.md).
- [Duration conversion](duration-units.md) and [audited bundles](analysis-bundles.md).
- [Ecosystem integration](ecosystem-integration.md),
  [FLO-backed book workflow](flo-book-workflow.md), and
  [activity-to-order reconstruction](order-reconstruction.md).
- [Prepared White Belt preview](book-preview.md) and
  [simulation-source ingestion](simulation-ingestion.md).
- [Numerical references](reference-fixtures.md) and
  [optional locked R environment](../tools/r-reference/README.md).

## Release and review evidence

- [0.2.2 release](releases/v0.2.2.md), [0.2.1 release](releases/v0.2.1.md),
  [0.2.0 release](releases/v0.2.0.md), and [v0.2 migration](migration-v0.2.md).
- [2026-11-05 code review and follow-up completion](assessments/code-review-2026-11-05.md).
- [0.2.2 canonicalization baseline](assessments/v022-canonicalization-baseline.md)
  and [measured acceptance evidence](assessments/v022-canonicalization-evidence.md).
- [FLO integration acceptance](assessments/v021-sprint-acceptance.md),
  [FLO 0.5 alignment](assessments/flo-05-alignment.md),
  [book model assessment](assessments/v021-book-model.md), and
  [Pydantic boundary pilot](assessments/v021-pydantic-pilot.md).
- [Historical 0.2 readiness audit](assessments/v02-release-readiness.md) and
  [book fixture/API assessment](assessments/book-preview.md).

Dated assessments and machine-readable snapshots describe their recorded source
state. Their pending tasks, counts and fingerprints are not current release
certification. Preserve them as evidence rather than rewriting old results.

## Historical implementation plans

These preserve accepted scope/design and links from assessments; they are not
active work queues:

- [White Belt preview/reconstruction](plans/white-belt-book-preview.md).
- [0.2.1 FLO integration](plans/v021-flo-white-belt.md).
- [0.2.2 Pandera/canonical Polars](plans/v022-pandera-canonical-polars.md).

Earlier scaffold status/action notes and the duplicate analytical-slices plan
were removed after consolidation into STATUS and the 0.3 checklist. Git history
retains them. Product-vision material in `copilot_prompts/` remains background,
not implementation evidence or an additional specification.

## Evidence and change rules

Requirements own outcomes and acceptance; technical requirements own constraints;
accepted ADRs explain durable choices; the roadmap owns releases; the compatibility
matrix owns R comparisons. Current implementation and validation establish what
works. Reconcile contradictions explicitly rather than silently weakening criteria.

With each behavior change, update affected requirement evidence/traceability,
public guides and compatibility claims. Change roadmap ownership explicitly if
scope changes. Add an ADR only for a durable choice with meaningful alternatives.
Keep current status and the single implementation checklist aligned in the same
change. A separate governance ceremony is not required.
