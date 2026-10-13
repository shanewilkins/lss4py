# 0021: Reuse FLO and established presentation libraries

- Status: Accepted
- Date: 2026-10-13
- Deciders: Maintainer direction in architecture discussion
- Related requirements: UR-003, UR-006, UR-019, UR-020, UR-025, UR-029,
  TR-003, TR-007, TR-008, TR-018, TR-024
- Supersedes: [ADR-0012](0012-visualization-contracts.md)
- Complements: [ADR-0020](0020-delegate-numerical-algorithms-and-own-analytical-contracts.md)
  and [ADR-0019](0019-reconcile-package-boundaries-and-event-log-contracts.md)

## Context

R SixSigma combines calculations and plotting in several functions. Its moving-
range control chart calculates limits and flags observations before drawing a
ggplot2 chart. Its cause-and-effect function draws supplied grouped hypotheses
with R grid graphics. Equivalent practitioner outcomes require both usable data
and optional rendering, but do not require reproducing those implementation choices.

The FLO ecosystem already owns process-diagram rendering, including a maintained
value-stream-map renderer. FLO's current design consumes canonical FLO process IR
and a typed value-stream analysis projection, emitting SVG over its accepted
ELK/SVG platform where layout is required. Recreating that platform in LSS4PY would
duplicate existing responsibilities.

## Decision

1. **Keep calculations independent of presentation.** Analytical APIs return
   typed, serializable results with estimates, limits, units, observation/case
   identity, exclusions, diagnostics and provenance. Statistical chart renderers
   consume those results without fitting models, estimating limits, evaluating
   rules or choosing statistical methods. They return native plotting objects or
   explicit artifacts; they do not require an interactive display or write files
   unless the caller requests export.

2. **Reuse FLO for process and value-stream diagrams.** LSS4PY owns observed-data
   analysis and its existing normalized ProcessModelIR contract. FLO owns its
   canonical process model, diagram projections, layout and rendering. Optional
   integration translates supported contracts through a narrow, versioned mapping;
   core calculations do not import FLO or parse `.flo` files. Preserve stable
   step/case identifiers, units, metric definitions and source provenance. Define
   the supported measured-annotation schema before promising overlays. Modeled
   FLO timing and measured LSS4PY timing remain distinguishable, with missing or
   unsupported annotations reported explicitly. Do not copy FLO internals or build
   another process-map renderer in this repository.

3. **Reuse the scientific and plotting ecosystem.** Start with existing NumPy,
   SciPy and statsmodels dependencies for array operations, distributions, tests,
   fitting and ANOVA. Evaluate other libraries when they supply a needed mature
   algorithm. Optional statistical plotting can use Matplotlib, already declared
   in the visualization extra. Additional backends are justified by concrete user
   needs rather than a mandatory two-backend API. LSS4PY owns domain policies and
   adapts upstream output into governed result contracts.

4. **Treat fishbone diagrams as supplied hypothesis structure.** A typed model
   preserves the effect, ordered groups and candidate causes, labeled as
   hypotheses. Rendering accepts this model without inventing causes or asserting
   causal evidence. Before implementing layout, review FLO extension capabilities
   and existing diagram libraries. Current FLO value-stream support is not evidence
   of fishbone support; renderer ownership is a follow-up selection, not an assumed
   FLO feature. Do not create a general diagram engine for this single capability.

5. **Review reuse before each parity slice.** Map the R behavior to the practitioner
   contract, inspect available upstream implementations, and record the selected
   estimator, defaults and deliberate differences. A similar function name does
   not establish compatibility. In particular, mixed-model ML/REML variance
   components do not automatically reproduce ANOVA-based Gage R&R estimates.
   Retain small documented domain formulas where reuse would add complexity or
   change semantics; do not implement statistical fitting, optimizers or a layout
   engine from scratch.

6. **Validate analysis and rendering separately, then together.** Numerical
   fixtures test estimates, limits, flags and invalid-domain policy. Rendering
   checks test plotted values, labels, units, limit positions, highlighted points,
   hypothesis preservation and legible exported artifacts. End-to-end tests use
   the installed package and optional integration to verify real input-to-artifact
   journeys. Base installation must remain usable without visualization or FLO.

## Reuse candidates for the compatibility work

These are review starting points, not completed integrations or parity claims.

| Capability | Machinery to reuse or evaluate | LSS4PY responsibility |
|---|---|---|
| Moving-range SPC | NumPy reductions; reviewed SPC implementations/constants; Matplotlib rendering | Observation order, baseline/Phase I/II policy, limit semantics, flags and provenance |
| Mean confidence interval and diagnostics | SciPy distributions/tests and statsmodels inference | Estimand, design, missingness, assumptions and interpretation |
| Gage R&R | statsmodels fitting/ANOVA; review estimator equivalence before MixedLM | Crossed/nested design, variance-component policy, study variation and ndc |
| Capability study | Existing capability estimates plus SciPy/statsmodels diagnostics | Explicit study orchestration, estimator choice and combined auditable results |
| Taguchi loss and defect/rework yield | NumPy reductions and transparent domain arithmetic | CTQ/loss conventions, counting semantics and denominators |
| Profile smoothing | Evaluate scikit-learn SVR behind an optional dependency | Orientation, parameter translation, profile identity and reference behavior |
| Declared process/value-stream diagrams | FLO's process/render contracts | Measured results and explicit mapping of supported semantic annotations |
| Cause-and-effect diagram | Evaluate existing diagram rendering and FLO extension fit | Structured candidate causes and preservation of hypothesis meaning |

## Sources

- SixSigma [moving-range chart](https://search.r-project.org/CRAN/refmans/SixSigma/html/ss.cc.html)
  and [cause-and-effect diagram](https://search.r-project.org/CRAN/refmans/SixSigma/html/ss.ceDiag.html).
- FLO repository: `docs/design/renderers/value_stream.md`,
  `docs/specs/value_stream_map.md`, and
  `docs/design/adr/render_stack_elk_svg_typst.md`, inspected on 2026-10-13.
- [SciPy statistical functions](https://docs.scipy.org/doc/scipy/reference/stats.html),
  [statsmodels ANOVA](https://www.statsmodels.org/stable/generated/statsmodels.stats.anova.anova_lm.html),
  [statsmodels MixedLM](https://www.statsmodels.org/stable/_modules/statsmodels/regression/mixed_linear_model.html),
  [Matplotlib figure export](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html),
  and [scikit-learn SVR](https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVR.html).

## Alternatives considered

- **Mirror R functions, including implicit plots.** Couples analysis to graphics
  and obscures reusable calculations and auditable results.
- **Build a process/diagram platform in LSS4PY.** Duplicates FLO and increases
  layout, export and maintenance obligations.
- **Delegate every domain decision to an upstream package.** Loses explicit
  practitioner semantics and may silently substitute different estimators.

## Consequences

Implementation plans include an upstream-reuse review and distinguish analytical
contracts from presentation contracts. Optional integration must use reviewed
public interfaces and compatibility tests. This decision adds no dependency,
runtime integration, renderer, compatibility promotion or release completion.
