# Requirements Governance

## Catalogs

- [User requirements](user-requirements.csv) contain one row per user outcome.
- [Technical requirements](technical-requirements.csv) contain one row per
  implementation constraint.
- [Traceability](traceability.csv) contains one row per user-to-technical
  requirement relationship.

The CSV files are UTF-8, use a single header row, and follow standard CSV quoting.
Long prose remains in individual cells so the catalogs can be filtered, joined, or
imported without parsing Markdown sections.

User requirements include a `journey_stage` column using one or more of `prepare`,
`define`, `measure`, `analyze`, `improve`, `control`, `communicate`, `learn`, and
`cross_cutting`. Multiple stages are separated by semicolons. The
[analysis journey](../analysis-journey.md) defines their meaning.

The `product_horizon` values are `current_yellow_belt`, `near_term`, `later`, and
`backlog`.
`product_horizon` is intentionally broader than a point release.
Exact release targeting for `v0.1`, `v0.2`, `v0.3`, and later milestones remains owned by the [roadmap](../roadmap.md).

Use the two fields differently:

- `product_horizon` says how close a requirement is to the product's active scope.
- the roadmap says which release primarily owns that requirement.
- `status` says how much checked-in evidence currently exists.

## Identification

- User requirements use `UR-NNN`.
- Technical requirements use `TR-NNN`.
- IDs are permanent and are not reused after retirement.

## Priority

| Priority | Meaning |
| --- | --- |
| Must | Required for the declared product slice or a safe, credible release of it. |
| Should | Important to the product direction, but a release can proceed with an explicit deferral. |
| Could | Valuable future scope that does not define the current release. |

## Status

| Status | Meaning |
| --- | --- |
| Satisfied | Checked-in implementation and relevant validation meet the acceptance criteria. |
| Partial | Some acceptance criteria are implemented and validated; material work remains. |
| Planned | The requirement is accepted as scope but has no adequate implementation yet. |
| Deferred | The requirement is intentionally outside the active roadmap horizon. |

Status is evidence-based. A placeholder, roadmap entry, or prose description alone
does not satisfy a requirement.

## Traceability rule

Every user requirement must link to at least one technical requirement.
Every technical requirement must identify the user requirements or governance concern it supports.
Roadmap release targets reference both where useful.

A requirement change should preserve its history in version control. If an outcome
is no longer wanted, mark it `Deferred` and explain why rather than silently
deleting it.
