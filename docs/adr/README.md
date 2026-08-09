# Architecture Decision Records

ADRs capture decisions that are costly, confusing, or risky to rediscover. They
are intentionally short and are not substitutes for requirements or implementation
plans.

## Index

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-use-lightweight-document-governance.md) | Use lightweight document governance | Accepted |
| [0002](0002-keep-the-core-package-focused-on-analytics.md) | Keep the core package focused on analytics | Proposed |
| [0003](0003-own-analytical-workflows-and-delegate-primitives.md) | Own analytical workflows and delegate numerical primitives | Proposed |
| [0004](0004-support-dataframe-neutral-inputs-and-results.md) | Support dataframe-neutral inputs and results | Proposed |

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
