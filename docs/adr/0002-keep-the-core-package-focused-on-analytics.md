# 0002: Keep the core package focused on analytics

- Status: Proposed
- Date: 2026-08-09
- Deciders: Maintainers
- Related requirements: UR-012, TR-008, TR-010

## Context

The project vision describes an ecosystem with an analytics core, human-facing
deliverables, and synthetic learning systems. The current repository already has
experimental reporting and workflow modules, so the package boundary needs to be
clear before those modules become public contracts.

## Decision

This repository's `lss4py` package owns process data contracts, calculations,
statistical analyses, process intelligence, and neutral analysis results.

Human-facing project templates and document production belong in a separate
deliverables package. Synthetic enterprise systems and teaching datasets belong in
a separate labs package. Those packages may depend on `lss4py`; the analytics core
must not depend on them.

Calculation APIs must remain usable without plotting or document-rendering
dependencies. The core may expose neutral serialization or analysis bundles when
they do not embed a deliverable format.

## Alternatives considered

- **Put the entire ecosystem in one package.** This simplifies discovery but
  couples analytics to educational assets, rendering, and synthetic systems.
- **Move every visualization out of the core.** This creates an unnecessarily
  rigid boundary; analytical plots may remain optional consumers of core result
  objects.
- **Let package boundaries emerge later.** Existing placeholders would then risk
  becoming accidental public contracts.

## Consequences

- Optional visualization integrations must not be required for calculations.
- `reporting` and deliverable-oriented APIs need boundary review before they are
  declared stable.
- Cross-package contracts should use typed, serializable core result models.
- Ecosystem repositories and their release plans are outside this roadmap unless
  explicitly added later.
