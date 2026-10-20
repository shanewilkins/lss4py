# LSS4PY Documentation

This directory contains the governed product and engineering documentation for
LSS4PY. It distinguishes current repository evidence from intended future scope.

## Governed documents

- [User requirements](requirements/user-requirements.csv) define the outcomes the
  package must enable.
- [Technical requirements](requirements/technical-requirements.csv) define the
  testable constraints used to deliver those outcomes.
- [Requirements conventions and traceability](requirements/README.md) define IDs,
  status, priority, and change rules.
- [Architecture decision records](adr/README.md) record durable technical and
  product-architecture decisions.
- [Ecosystem integration decisions](adr/0022-ecosystem-integration-contracts-and-journey-gates.md)
  record the bridge, exchange/evidence contracts and two journey-protection test
  gates; ADR-0023 resolves plotting, and fishbone renderer ownership remains open.
- [Ecosystem integration guide](ecosystem-integration.md) documents the implemented
  first bridge, evidence persistence, plotting contract and installed-wheel journey.
- [Roadmap](roadmap.md) sequences requirement delivery without promising dates.
- [Next analytical slices](plans/next-analytical-slices.md) record the current
  completed capability-Z and defect/rework-yield slices without changing release ownership.
- [Analysis journey](analysis-journey.md) describes the end-to-end practitioner
  experience that the requirements cover.
- [R `SixSigma` compatibility matrix](sixsigma-compatibility.md) tracks the
  reference package surface and parity gaps.

## Current analytical guides

- [Auditable analysis bundles](analysis-bundles.md)

- [Data-quality reports and preparation](data-quality.md)

- [Descriptive statistics](descriptive-statistics.md)
- [Defect and rework yield](defect-yield.md)
- [Cp and Cpk](capability-indices.md)
- [CTQs and specifications](specifications.md)
- [Analysis guidance](analysis-guidance.md)
- [Analytical backend contracts](backend-contracts.md)
- [Governed numerical references](reference-fixtures.md)
- [Optional R reference environment](../tools/r-reference/README.md)

## Background and vision

The files in `copilot_prompts/` capture useful product vision, ecosystem ideas, and
writing concepts. They are inputs to requirements, not normative specifications.
In particular, a capability described there is not considered implemented until
the current code and validation demonstrate it.

## Evidence and precedence

The document types answer different questions:

1. User requirements state **why** an outcome matters and how a user can verify it.
2. Technical requirements state **what the implementation must guarantee**.
3. ADRs state **why a durable design choice was made**.
4. The roadmap states **when work is expected and which release owns it**.
5. The compatibility matrix states **how LSS4PY compares with R `SixSigma`**.

Documents must be reconciled when they conflict; the roadmap cannot weaken a
requirement, and an ADR cannot silently change a user outcome. For claims about
what works today, checked-in code and validation take precedence over plans and
prose.

## Lightweight change process

When behavior or scope changes:

1. update or add the affected user requirement;
2. update the linked technical requirements and traceability;
3. add an ADR only if the change makes a durable choice with meaningful
   alternatives or consequences;
4. update the roadmap if delivery order, release ownership, or milestone scope changes; and
5. update the README or compatibility matrix if public status changed.

Maintainers review these documents with the same change as the code whenever
practical. A separate governance ceremony is not required.
