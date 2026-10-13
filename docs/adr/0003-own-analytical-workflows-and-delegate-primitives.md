# 0003: Own analytical workflows and delegate numerical primitives

- Status: Superseded
- Date: 2026-08-09
- Deciders: Maintainers
- Superseded by: [ADR-0020](0020-delegate-numerical-algorithms-and-own-analytical-contracts.md) (2026-10-12)
- Related requirements: UR-005, UR-017, UR-029, UR-033, TR-018, TR-019, TR-020

## Context

LSS4PY needs to decide whether it is a collection of thin wrappers around existing
statistics packages, a new statistics implementation, or an assistant for doing
Lean Six Sigma analysis well. Thin wrappers would preserve the fragmentation and
implicit assumptions users already face. Reimplementing general statistics would
duplicate mature libraries and create unnecessary correctness risk.

## Decision

LSS4PY will be an **assistive analytical facade**.

The project owns:

- Lean Six Sigma concepts, terminology, and workflow-level APIs;
- analysis suitability guidance tied to the user's question and data;
- validation of study design, structure, and domain constraints;
- explicit assumptions, warnings, provenance, and interpretation boundaries;
- stable, typed LSS4PY result contracts; and
- orchestration of calculations, diagnostics, and optional visualizations.

The project delegates general numerical primitives to mature libraries such as
NumPy, SciPy, and statsmodels when their behavior meets the governed contract.
LSS4PY may implement small domain formulas directly when they are stable and
auditable, or when exact R `SixSigma` parity requires it.

Guidance may recommend candidate analyses and explain tradeoffs, but it must not
silently choose or run a statistical test solely from the observed data. The user
retains control of the analytical question, cohort definition, and decision.

Underlying library result objects are implementation details. Public study APIs
return LSS4PY result models so assumptions and provenance do not disappear when a
backend changes.

## Alternatives considered

- **Expose thin wrappers only.** This reduces implementation effort but does not
  deliver the project's promise of making good analytical habits the default.
- **Implement a complete statistics stack.** This maximizes control but duplicates
  mature work and expands the validation burden dramatically.
- **Automatically select the best test.** This appears helpful but can hide the
  user's actual question, study-design problems, and the consequences of repeated
  model selection.

## Consequences

- Each analysis needs a suitability contract in addition to a formula.
- Result models and diagnostics are part of the public API, not optional polish.
- Numerical dependencies remain replaceable behind parity and contract tests.
- Scope must be managed by complete user journeys rather than one wrapper per
  upstream function.

