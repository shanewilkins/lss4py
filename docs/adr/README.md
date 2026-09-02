# Architecture Decision Records

ADRs capture decisions that are costly, confusing, or risky to rediscover. They
are intentionally short and are not substitutes for requirements or implementation
plans.

## Index

### Foundational Governance & Scope (0001–0004)

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-use-lightweight-document-governance.md) | Use lightweight document governance | Accepted |
| [0002](0002-keep-the-core-package-focused-on-analytics.md) | Keep the core package focused on analytics | Proposed |
| [0003](0003-own-analytical-workflows-and-delegate-primitives.md) | Own analytical workflows and delegate numerical primitives | Proposed |
| [0004](0004-support-dataframe-neutral-inputs-and-results.md) | Support dataframe-neutral inputs and results | Proposed |

### v0.2–v1.0 Architectural Framework (0005–0014)

These decisions formalize the architectural framework for contract foundation (v0.2) through stable release (v1.0).
See [ARCHITECTURAL-DECISION-FRAMEWORK.md](ARCHITECTURAL-DECISION-FRAMEWORK.md) for 2–3 alternatives + rationale per decision.

| ADR | Decision | Status |
|---|---|---|
| [0005](0005-result-model-hierarchy.md) | Result model hierarchy and base class | Proposed |
| [0006](0006-numerical-kernel-delegation.md) | Numerical kernel delegation and registry | Proposed |
| [0007](0007-analysis-suitability-registry.md) | Analysis suitability registry | Proposed |
| [0008](0008-adapter-normalization-layer.md) | Adapter normalization layer | Proposed |
| [0009](0009-narwhals-integration.md) | Narwhals integration for backend-neutral inputs | Proposed |
| [0010](0010-diagnostic-model.md) | Unified diagnostic model | Proposed |
| [0011](0011-optional-extras-strategy.md) | Optional extras strategy | Proposed |
| [0012](0012-visualization-contracts.md) | Visualization contracts | Proposed |
| [0013](0013-backend-parity-testing.md) | Backend parity testing | Proposed |
| [0014](0014-versioning-and-migration-policy.md) | Versioning and migration policy | Proposed |

### Practitioner Progression & Governance (0015+)

| ADR | Decision | Status |
|---|---|---|
| [0015](0015-belt-level-governance.md) | Belt-level governance and practitioner progression | Proposed |

## When to write an ADR

Write an ADR when a choice:

- changes a public contract or package boundary;
- selects between credible architectural alternatives;
- introduces a dependency or data contract that will be difficult to reverse; or
- resolves a recurring design question.

Do not write an ADR for routine implementation details, backlog ordering, or a
decision that can be expressed completely as a requirement.

## Naming and lifecycle

- Use `NNNN-short-kebab-case-title.md` with monotonically increasing numbers.
- Start as `Proposed` when review is still needed.
- Change to `Accepted`, `Rejected`, or `Superseded` after a decision.
- Never rewrite the decision history of an accepted ADR. Supersede it with a new
  ADR and link both records.
- Copy [the template](template.md) for a new record.
