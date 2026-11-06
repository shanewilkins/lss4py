# 0.3 Yellow Belt workflow and delivery plan

Updated 2026-11-06. This is the implementation queue for the
[roadmap's 0.3 gate](../roadmap.md). [Current status](../STATUS.md) separates
published behavior, unreleased additions and parked work.

## Scope decision

The maintainer's five analytical workflows below define LSS4PY's remaining path
to 0.3. The separate describe/validate/render/revise, model-evidence attachment,
and current/proposed diagram table was intended for **the FLO team**. It is
integration context, not additional LSS4PY implementation or release scope.

Taguchi quality loss is explicitly outside Yellow Belt. Preserve its existing
kernel, exports, typed results, bundle handling, plotting, tests and R fixtures
as parked unreleased work in progress. Do not continue that investigation or
make its completion a 0.3 gate. UR-027/TR-026 remain later product requirements
without a committed release.

## Workflows and acceptance deliverables

| Workflow we are teaching | Required LSS4PY support and reviewable deliverable |
| --- | --- |
| **Prepare evidence → define a cohort → calculate process measures** | Supported paths from Polars tables to elapsed-time, deadline, first-pass-yield and route-specific rolled-yield calculations. Keep denominator populations, exclusions, unfinished cases and units explicit. Retain prepared/intermediate tables and source keys so a learner can hand-check the result. |
| **Describe → stratify → visualize** | Counts, proportions, mean, median, SD, quartiles/IQR and percentiles; inputs or helpers for histograms, Pareto charts, scatterplots and time-ordered displays. Declare percentile conventions and return inspectable intermediate tables. Preserve group identity, ordering and missingness so pooled summaries do not conceal population changes. |
| **Specify a null model → enumerate/simulate → interpret** | Lady Tasting Tea plus repeatable sampling/randomization examples. Show the null model, statistic, enumeration space or sampling procedure, seeds, assignments and calculated results. Separate exact enumeration from simulated estimates and state the tail/counting convention and finite-simulation limitations. |
| **Estimate → compare → assess practical importance** | Confidence intervals and introductory one-sample, paired and independent-sample t workflows using established statistical implementations. State input requirements, estimand/design, effect estimates and limitations, with interpretation against an operational threshold. Keep matched-pair identity and exclusions inspectable; do not infer causality or automatic method suitability. |
| **Read process behavior over time** | Produce instructor-reviewed control-chart examples with explicit baseline, subgrouping, limits and signal rules. Retain the ordered data, baseline/phase identity, limit method and flagged observations so instructors can verify the chart. Learners interpret supplied charts; independent chart selection remains later work. |

The complete deliverable is a small, runnable set of Yellow Belt investigations
with visible input, calculation, output and interpretation, demonstrated in the
intended notebook workflow and from an installed wheel. Riverside supplies the
process case; Lady Tasting Tea and sampling/randomization are separate teaching
investigations. Do not force every method into one dataset or project.

## Existing starting points and gaps to check

- [Prepared White Belt evidence](../book-preview.md),
  [reconstruction](../order-reconstruction.md), numeric ingestion and Polars
  contracts already establish explicit clocks, boundaries, cohorts and source
  identity. Check their applicability to Yellow Belt inputs; the Wash n' Fold
  acceptance fixture is not a substitute for Riverside acceptance.
- Existing timing/PCE, deadline and stage/defect yield APIs cover useful slices.
  A stage-conversion funnel or product of arbitrary stage yields does not by
  itself prove route-specific first-pass/rolled-yield semantics. Define eligible
  entrants, route membership, repeat attempts and unfinished-case treatment first.
- `describe`, `distribution_profile` and their result-only plots supply much of
  the descriptive surface. Verify SD convention, quartile/percentile method,
  category denominators, stratification and exportable intermediate tables.
  Pareto, scatter and time-order requirements may use explicit prepared inputs
  and established renderers; a new plotting framework is not assumed.
- `mean_confidence_interval` already provides mean intervals with explicit policy
  and diagnostic evidence. One-sample, paired and independent-sample t workflows
  need an exercise-to-API gap review. Delegate statistics to established numerical
  implementations and own input/design/result/interpretation contracts.
- Existing MR(2) Phase I/II results and plots are a starting point for instructor
  examples, not proof of every desired chart or subgroup design. Select the actual
  teaching examples and their instructor-approved methods before adding support.
- NumPy/SciPy and notebook code may supply enumeration, random sampling and
  randomization primitives. A teaching experiment does not require a general
  DOE engine, simulation platform or new package API if transparent example code
  meets the contract.

Planning context inspected in the sibling `modern-process-improvement` repo:
`notes/yellow_belt_structure_and_objectives.md` (proposal dated 2026-11-03),
`book/content/yellow_belt/what_yellow_belt_is_for.qmd`, and
`templates/yellow_belt_a3_notebook_template.py`. These explain the Riverside/A3
and anticipated YB09–14/YB18–19 investigations; the maintainer's five workflows
above own this package's scope. The proposal/current-template differences do not
add package gates. Pin any reused source data and expected answers before relying
on them for acceptance. No sibling files were changed.

## Remaining work, in order

| Gate | Bounded work | Acceptance evidence |
| --- | --- | --- |
| 1. Map the five investigations to existing APIs and gaps | Select minimal process/cohort data, descriptive strata, Lady Tasting Tea and sampling examples, supplied t designs and instructor-reviewed charts. Record the primitive, input contract and expected output for each. | One workflow-to-API/library/example/gap inventory, pinned input provenance/license/revision, hand-checkable expected answers and exact launch commands. Identify package work versus notebook/FLO responsibilities. Stop investigation at the gaps required by these five workflows. |
| 2. Complete process-measure and descriptive paths | Close actual gaps in Polars preparation/cohort selection, elapsed time, deadline, FPY, route-specific RTY, descriptive/grouped/category tables and display inputs/helpers. | Source-to-result hand checks with explicit units, denominators, exclusions and unfinished cases; route/branch and repeat-attempt cases; declared SD/percentile conventions; inspectable tables; readable histogram, Pareto, scatter and time-order examples. Do not silently pool incompatible populations or drop unfinished observations. |
| 3. Complete null-model and sampling investigations | Build visible exact enumeration and seeded sampling/randomization examples using established primitives. | Lady Tasting Tea null/assignment/statistic/tail counting agrees with an independent enumerated answer. Retain seeds, generator/method/software context and assignments for reruns; test seed reproducibility where stochastic. Show finite-sampling variation and avoid treating a sampled estimate as exact. No general simulation framework. |
| 4. Complete introductory estimation/comparison | Demonstrate mean and mean-difference intervals plus specified one-sample, paired and independent-sample t workflows. Add only missing governed analytical contracts. | Independent reference/hand checks; explicit design and matching; confidence level, alternative and variance/estimator policy; effects, interval, sample sizes and test output; missing/invalid/degenerate-input behavior; interpretation against a practical threshold and stated suitability/causality limits. No automatic test selector or full inferential portfolio. |
| 5. Complete instructor-reviewed behavior-over-time examples | Select the chart designs needed for teaching and produce verified data/results/figures using established calculations and existing support where possible. | Instructor-reviewed baseline, subgrouping, phase, limit formulas, rules and signals; independent numerical checks; explicit order and incomplete-data handling; stable limits when applying a fixed baseline; plotted labels/units/signals agree with retained results. Independent chart selection and a broad SPC engine remain later work. |
| 6. Verify integrated delivery and release | Run the investigation set from an isolated LSS4PY wheel and managed notebook environment; inspect artifacts and reconcile requirement evidence. | Fresh reruns reproduce key answers and intermediate tables. Inspect notebook/print output for changed figures. Run applicable configured quality/security/build/metadata gates and exact-wheel journeys; prepare version/notes/migration and complete publication/index verification. Track inherited White Belt book dependency/Chapter 9 render acceptance separately (UR-046/TR-045); it requires no new analytics. |

**Start with Gate 1.** Each implementation change must close a named gap from
these workflows. A nearby R API, broad curriculum topic or optional renderer is
not by itself a reason to expand 0.3. Do not require a technique in a project
solely because it appears in a taught investigation.

## Integration context: FLO responsibilities

FLO owns the describe/validate/render/revise example's native model authoring,
validation and rendering, attachment/display of model evidence, and readable
current/proposed process-model exports. LSS4PY owns its bounded analytical
projection, calculations and result/evidence contracts. Reuse the documented
[exchange](../ecosystem-integration.md) and
[FLO-backed example](../flo-book-workflow.md).

Keep observations, modeled/estimated/synthetic values and unknowns distinct.
When a LSS4PY calculation consumes model-related data, retain units, observation
counts, sources, population and explicit mapping. Unknown must not become zero.
Parallel effort is not elapsed time; exclusive routes are not all traversed by
one case; rework occurrences must not be silently counted once or twice. These
are relevant analytical boundaries, not a mandate to implement FLO's diagram
comparison or a general graph-total engine. Unsupported totals stay unavailable
with a reason. Current documented measured overlays remain unsupported; separate
labeled observed summaries must not be described as working overlays.

## Requirement traceability and explicit deferrals

| Workflow / retained obligation | Requirement families and release treatment |
| --- | --- |
| Process measures and explicit cohorts | UR-001–005/UR-014–016/UR-022/UR-047–049; TR-001–005/TR-013/TR-046, with TR-040–044 retained for the specific book fixture. Existing Satisfied rows cover their recorded slice; they do not establish acceptance of new route-specific Yellow Belt cases. |
| Descriptive, stratified and visual evidence | UR-004/UR-029/UR-030/UR-041; TR-009/TR-022/TR-032/TR-035. 0.3 owns the taught summary/Pareto/display slice; broader multimodality, violin and contingency-analysis families remain later completion. |
| Null-model and reproducible sampling examples | UR-007/UR-045; TR-012/TR-033/TR-037. Transparent supplied examples and independent reference answers satisfy this slice without committing to a DOE or simulation framework. |
| Introductory interval/t comparisons | UR-008/UR-021/UR-038; TR-028. Bounded 0.3 slices cover the specified supplied designs and effects; full parametric/nonparametric portfolios, multiplicity workflows, independent design/method selection and DOE remain v0.4/v0.5. |
| Instructor-reviewed charts | UR-010/UR-025/UR-029; TR-024/TR-032. Support production/verification of supplied teaching charts in 0.3. Full chart selection, broader chart families and rule engines remain v0.4/v0.5; existing MR work is retained. |
| Cross-cutting evidence and delivery | UR-005/UR-007/UR-012/UR-016/UR-033; TR-007/TR-009/TR-011/TR-012/TR-019/TR-020/TR-033/TR-038/TR-046. Retain result restoration, provenance and applicable backend/installed-wheel checks. |
| Taguchi quality loss (UR-027/TR-026) | Parked unreleased WIP, outside Yellow Belt; no committed later release. Preserve implementation, tests and R fixtures without further feature investigation on this path. |
| Other former 0.3 feature gates | Full R map/fishbone parity (UR-019/UR-020), composed capability figures (UR-024), extra diagnostic families (UR-030/TR-022) and persistent control-plan services (UR-044/TR-036) are not prerequisites for the five workflows. Full acceptance remains v0.5; existing work is retained. |

The milestone claim is support for these five declared Yellow Belt analytical
workflows, not completion of every broader requirement or R compatibility family.
Cross-release families remain Partial/Planned until their full criteria are met.
This is an explicit release-scope revision; it does not claim full-family Must
acceptance or mark a family Satisfied from planning text.

## Completion rule for changes

Preserve existing source, tests and fixtures. Select the established primitive
and input/design/missingness/unit/identity policies before coding. Follow accepted
ADR-0020/0021/0023/0026/0028 boundaries. New package behavior needs typed
results/restoration where applicable, guidance and actionable errors, positive/
invalid/boundary and independent numerical evidence, supported eager-backend
parity with PyArrow, and applicable installed-wheel checks. Rendering consumes
results or explicit governed inputs without hidden estimation and needs actual
artifact inspection when changed. Run the locked R verifier if R evidence changes.
Dated source checks do not establish new release or book acceptance.
