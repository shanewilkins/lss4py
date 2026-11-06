# Current status and continuation

Updated 2026-11-06. Start here for the implemented state; use the
[0.3 checklist](plans/v03-yellow-belt.md) for the remaining work and acceptance
criteria. The [roadmap](roadmap.md) owns release scope and the
[requirement catalogs](requirements/README.md) own status and criteria.

## Published versus unreleased

**0.2.2 is published and verified from official PyPI.** Its release tag is
`b35805b9835a5728e62d005fbdb72edbefbe70c8`. It includes the canonical Polars /
private Pandera boundary, supported eager pandas/Polars/PyArrow inputs, time and
yield metrics, descriptive/tail statistics, Cp/Cpk/Z, mean inference, distribution
diagnostics and their optional plots, data quality, specifications, guidance,
audited bundles, and the scoped book reconstruction route. See the
[release record](releases/v0.2.2.md).

**The checkout also contains unreleased 0.3 work:**

- [MR(2) charts](control-charts.md), with Phase I limits, frozen Phase II
  monitoring, source-pair identity, result-only plotting and genuine R references.
- [Capability studies](capability-study.md), composing explicit short-/long-term
  capability, distribution and observed nonconformance evidence with typed
  restoration. The variation estimator is overall sample standard deviation;
  sample roles do not establish stability or subgroup design.

Package metadata still says `0.2.2`; it does not make checkout additions available
in that published wheel. The README separates the two surfaces.

## Verified baseline

The [2026-11-05 code review and completion addendum](assessments/code-review-2026-11-05.md)
record the three corrected chart/integrity defects and closure of all five review
recommendations. The follow-up source suite passed 2,708 tests with five expected
failures and 96.07% statement coverage. The wheel stages passed 34 base, 46
pandas, 48 storage and 62 ecosystem tests. These are dated verification results,
not a promise that later edits have passed the same checks.

Completed review follow-through includes genuine mixed-backend study comparisons,
independent chart scaling/translation properties, malformed nested evidence
rejection, an installed composed-study journey and a runnable
[monitoring example](../examples/yellow_belt/monitoring.py).

## Next work

Start with the [0.3 analytical workflow plan](plans/v03-yellow-belt.md#remaining-work-in-order).
The maintainer's five LSS4PY workflows define the remaining gate:

1. Prepare evidence, define cohorts, and calculate elapsed time, deadlines, FPY
   and route-specific RTY with explicit denominators/exclusions/unfinished cases.
2. Describe, stratify and visualize using inspectable tables and declared
   summary/percentile conventions.
3. Specify null models, enumerate/simulate and interpret Lady Tasting Tea and
   repeatable sampling/randomization examples with visible seeds and assignments.
4. Estimate and compare through intervals and introductory one-sample, paired and
   independent-sample t workflows, including effects and practical importance.
5. Produce instructor-reviewed control-chart examples with explicit baseline,
   subgrouping, limits and rules. Learners interpret supplied charts;
   independent chart selection remains later work.

Next map these investigations to existing APIs, established libraries, transparent
notebook examples and concrete package gaps. Pin inputs and expected answers.
The separate model describe/validate/render/revise, model-evidence and diagram
comparison table belongs to **FLO**, not additional LSS4PY release scope.

**Taguchi quality loss is parked work in progress, outside Yellow Belt and the
0.3 gate by the maintainer's 2026-11-06 scope decision.** Existing kernel, exports,
typed results, bundle handling, plotting, tests and R fixtures remain intact and
unreleased. Their presence does not establish completed acceptance or a promise
to publish them in 0.3. UR-027/TR-026 remain later work without a committed release.
Do not resume that investigation as the next task.

Existing MR/capability and other analytical work is retained. Broad inference/SPC
portfolios, full capability presentation, persistent control plans and full R
map/fishbone parity are not extra gates. Requirement families remain Partial/
Planned until their own full acceptance is met.

The White Belt preview and all 39 reconstructed orders are implemented and tested
from wheels. **Book deployment remains recorded as unverified:** confirm the
sibling book's ordinary published-package dependency/lockfile and render Chapter 9
against the pinned answers before closing UR-046/TR-045. No local-source override
or new analytics is required for that deployment step.

Completed implementation plans, release notes and assessments remain historical
records. Their old pending tasks and test counts are not the current work queue.
