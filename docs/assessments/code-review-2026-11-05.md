# LSS4PY code review — 2026-11-05

The assessment below records the review snapshot. A dated completion addendum at
the end records subsequent work on recommendations R1–R5 without rewriting the
original findings or ratings.

## Shared findings

**No open product defects established in this follow-up.** The original review
found three P2 defects; all three are now fixed and verified. The assessments
below rate the current implementation, including the uncommitted fixes. Testing
recommendations remain distinct from proven product defects.

### F1 — [P2] Incompatible baseline and monitoring units

**Status: Fixed and verified.**

At the original target, Phase II copied limits without checking measurement
units. A baseline from `[1, 2, 3]` minutes accepted `[60, 120, 180]` seconds,
retained UCL approximately `3.2665`, labeled it seconds, and signaled both ranges.
The observations represent the same variation after unit conversion, so the
result could prompt an unnecessary special-cause investigation.

The current [unit compatibility check](/Users/shane/lss4py/src/lss4py/_kernels/control_chart.py:148)
rejects a different explicit unit and inherits the baseline unit when omitted.
Conversion remains an explicit caller responsibility. A baseline with no unit
cannot acquire a new declared unit through monitoring.

Acceptance was met by
[`test_phase_ii_preserves_baseline_units`](/Users/shane/lss4py/tests/test_control_chart.py:251)
across the governed backend matrix and the
[installed-wheel regression](/Users/shane/lss4py/e2e/test_control_chart.py:11).
Both rejection and the resulting unit/provenance are checked.

### F2 — [P2] Absolute tolerance allowed material edits to tiny baseline limits

**Status: Fixed and verified.**

The original baseline comparison used an absolute tolerance of `1e-12`. For
`[0, 1e-15, 2e-15]`, changing UCL from approximately `3.27e-15` to `9e-13` passed
validation. Monitoring `[0, 1e-13]` then lost the signal produced by the original
baseline. The defect depended on measurement scale and an edited result; it did
not affect every ordinary chart.

The current [limit comparison](/Users/shane/lss4py/src/lss4py/_kernels/control_chart.py:68)
retains relative tolerance `1e-12` and removes the absolute tolerance floor.
[`test_baseline_limit_integrity_across_scales`](/Users/shane/lss4py/tests/test_control_chart.py:273)
checks intact restored baselines, expected signals, and rejection of material
edits at zero, `1e-15`, ordinary, and `1e100` scales. The installed-wheel
regression also verifies the original tiny-scale counterexample.

### F3 — [P2] Portable pair keys could contradict source adjacency

**Status: Fixed and verified.**

The original validator accepted matching array lengths without establishing that
overlapping pairs described one source sequence. Replacing the ending keys of
source keys `["a", "b", "c"]` with `["wrong", "wrong"]` survived typed restoration
and subsequent baseline reuse. This could misidentify observations in exported
evidence and charts.

The current [pair-key validator](/Users/shane/lss4py/src/lss4py/_bundle_schema.py:490)
requires nonmissing portable scalars, matching overlapping endpoints with scalar
type preserved, and a unique reconstructed source sequence.
[`test_reject_inconsistent_portable_pair_keys`](/Users/shane/lss4py/tests/test_control_chart.py:297)
checks contradictory endpoints, duplicate keys, nulls, blank strings, nested
values, and integer/float identity mismatches through restoration and baseline
reuse. The installed-wheel regression rejects the original corrupted payload.

## Comparison and reviewer relationship

- **Date:** November 5, 2026, America/Chicago.
- **Base:** `v0.2.2`, `b35805b9835a5728e62d005fbdb72edbefbe70c8`.
- **Original reviewed target / current HEAD:**
  `cccbdd5fb125857313303e4c4724fb9eb3953fdc`.
- **Current assessed target:** that HEAD plus the unstaged fixes in
  `src/lss4py/_kernels/control_chart.py`, `src/lss4py/_bundle_schema.py`,
  `tests/test_control_chart.py`, and `docs/control-charts.md`, plus the untracked
  `e2e/test_control_chart.py`. There were no staged changes at report preparation.
- The local review-prompt edits supplied the assessment instructions; they are
  outside the analytical product verdict. This report is a new review artifact.
- The committed comparison contains 46 changed files, including analytical APIs,
  result exchange, reporting, reference fixtures, documentation, dependency/test
  changes, and GitHub Actions updates. This is a focused change review rather
  than a whole-project release audit.

One Codex reviewer applied six perspectives. The reviewer found the original
defects and authored their subsequent fixes and regression tests, so this
follow-up includes self-review. Separate sections are not independent expert
endorsements. Genuine R execution supplies an independent numerical implementation
for retained cases; it is not independent professional review of the whole API.

## Persona scorecard

Ratings apply to declared contracts in this change. **Strong** requires persuasive
validation without an established material gap in assessed scope; **Adequate**
means credible support with bounded remaining gaps; **Needs improvement** means
an evidenced weakness needs correction; **Insufficient evidence** means a material
question prevents a defensible judgment. Confidence describes the evidence for
the assessment, not how favorable the rating is. Ratings are not averaged.

| Persona | Applicable | Current rating | Confidence | Basis |
| --- | --- | --- | --- | --- |
| Quality engineer / SPC specialist | Yes | Adequate | Medium | Phase and interpretation contracts are explicit; F1/F2 are fixed. Practitioner usability has not been independently observed. |
| Applied statistician / numerical reviewer | Yes | Adequate | Medium | Retained R cases reproduce; estimators and sample roles are explicit. Generated checks do not independently establish every formula or numerical boundary. |
| Dataframe interoperability reviewer | Yes | Adequate | Medium | Required backend matrix passes and chart identity is checked. The composed study's named equivalence test repeats one backend rather than comparing different backends. |
| Serialization and integrity reviewer | Yes | Adequate | Medium | Nested restoration and malformed evidence checks exist; F3 is fixed. Exhaustive consistency of every nested parameter has not been established. |
| Test skeptic | Yes | Needs improvement | High | Direct inspection establishes redundant same-backend comparison and bounded property strategies; earlier passing tests missed F1–F3. These are bounded test weaknesses, not additional product failures. |
| Library integration and reporting reviewer | Yes | Adequate | Medium | All four wheel stages and plotting tests pass. The new chart has a wheel regression; the new composed capability-study entry point still lacks its own wheel journey. |

These are the first explicit persona ratings for this review. The three historical
defects remain visible above but are not counted as current open defects.

## 1. Quality engineer / SPC specialist

**Examined:** the Phase I-to-Phase II user path, adjacent-pair identity, signal
interpretation, units, and capability-study sample roles in
[control-charts.md](/Users/shane/lss4py/docs/control-charts.md),
[capability-study.md](/Users/shane/lss4py/docs/capability-study.md), and their kernels.

**Strengths and findings:** monitoring reuses frozen limits, rejects Phase II as
a baseline, and retains a fingerprint of the supplied Phase I result. Missing
observations are rejected rather than silently creating adjacency. The docs
distinguish control limits from specifications and avoid equating a lack of
signals with demonstrated stability. Capability sample horizons are caller
declarations; neither normality nor an argument name certifies stability or
collection design. F1 and F2 mattered because plausible outputs could change an
operational decision; their verified fixes address the demonstrated triggers.

**Recommendation:** R1, a worked monitoring example with a unit-conversion step
and a signaled pair, would make the corrected contract easier to use. This is a
nonblocking documentation improvement, not a demand for broader SPC methods.

**Limits:** no independent quality engineer or practitioner evaluated the workflow.
Baseline suitability, independence, and meaningful sequence remain caller
responsibilities. Broader chart families and rules are explicitly future scope.

## 2. Applied statistician / numerical reviewer

**Examined:** MR(2) constants and limits, strict signal inequalities, frozen limits,
the capability-study composition, child capability/distribution calculations,
observed nonconformance, and R fixture generation/verification.

**Strengths and findings:** the MR calculation uses explicit closed-form span-two
constants; retained genuine R Phase I/II cases reproduce within documented
tolerances. The study delegates capability estimates and diagnostics to existing
calculations, uses separately supplied samples, and counts observations outside
inclusive specification boundaries. The documented `ddof=1` estimate is overall
sample variation, not a pooled within-subgroup estimate or an inferred long-term
sigma shift. F2 is fixed without introducing a measurement-scale floor.

**Recommendation:** R2, add scale/translation properties with independently
specified mathematical relationships. Existing chart properties calculate
expected ranges using the same NumPy difference primitive and derive expected
signals from returned limits; they do not independently prove the limit formula.

**Limits:** the property strategies explicitly exclude subnormals and bound
magnitudes; capability-study generators also bound specification widths. The R
verifier establishes retained cases, not exhaustive numerical correctness.
`ss.study.ca` returns no structured numerical study result, so complete composed
study parity is not claimed or established.

## 3. Dataframe interoperability reviewer

**Examined:** canonical ingestion and extraction, chart source preservation,
indexed pandas behavior, result frame exports, and the new study tests over
pandas, indexed pandas, Polars, and PyArrow.

**Strengths and findings:** all required backend variants passed. Chart tests
compare normalized results to a separate Polars calculation and check source
preservation and pair identities. The implementation uses source positions and
explicit keys rather than pandas indexes. F3 now protects identity after portable
restoration as well as ingestion.

**Recommendation:** R3, replace the redundant composed-study comparison with
cross-backend and mixed-backend comparisons. In
[`test_explicit_short_and_long_term_study`](/Users/shane/lss4py/tests/test_capability_study.py:35),
both `result` and `reference` use the same parametrized `frame_factory`. That
comparison establishes repeated-call consistency after removing timestamps, not
equality between backend implementations. The direct count assertions remain useful.

**Limits:** passing each backend's example does not by itself establish complete
nested payload parity. Mixed short-/long-term backend combinations deserve
explicit coverage because the public documentation permits them. No backend
disagreement was reproduced; this recommendation concerns evidence quality.

## 4. Serialization and integrity reviewer

**Examined:** result serialization/restoration, chart baseline validation, nested
study validation, source/specification/software links, and audited bundles under
accepted ADR-0025.

**Strengths and findings:** restoration reconstructs typed evidence without
executing the analytical kernels. Study validation checks child result types,
counts, specifications, optional long-term completeness, and observed counts
against stored measurements. Chart validation checks pair positions, signals,
and limits; F3 adds the missing pair-key invariants. F2 protects baseline reuse
against the demonstrated material limit edit. Audited bundle tests preserve
typed children and explicit source associations.

**Recommendation:** R4, extend malformed composed-study fixtures beyond the
existing observed-risk mutation. This would strengthen evidence that exchanged
studies reject inconsistent nested state rather than only preserve valid state.

**Limits:** fingerprints detect snapshot inconsistency; they do not authenticate
the source or establish statistical correctness. A Phase II payload alone cannot
prove that its limits came from the exact baseline named by a fingerprint without
that baseline evidence. Complete parent/child parameter consistency was not
exhaustively probed, and is an open validation question rather than an asserted bug.

## 5. Test skeptic

**Examined:** example assertions, property strategies and oracles, backend
comparisons, historical counterexamples, new regressions, and wheel test coverage.

**Strengths and findings:** the new regressions encode the demonstrated failures
and test both intact acceptance and corrupted rejection. They cover zero, tiny,
ordinary, and large scales and execute the critical chart path from an installed
wheel. Full-suite success provides useful regression evidence beyond the edited
functions. The original 232 focused checks had passed despite F1–F3, illustrating
why passing tests alone were insufficient.

**Recommendations:** prioritize R3's ineffective comparison, then R2's independent
properties and R4's malformed nested evidence. This persona's `Needs improvement`
rating concerns those concrete weaknesses; it does not convert absent coverage
into product defects or block this bounded change after the proven fixes.

**Limits:** 96.07% is statement coverage, not branch or mutation coverage. Generated
cases use finite budgets and constrained domains. No mutation-testing campaign
was performed, and none is required to accept these specific fixes.

## 6. Library integration and reporting reviewer

**Examined:** public exports, optional visualization loading, result-only chart
rendering, caller-supplied axes, package boundaries, CI configuration, and isolated
wheel installs with successive extras.

**Strengths and findings:** the reporting implementation plots stored ranges,
limits, signals, phase, and ending keys/positions rather than calculating a new
chart. Reporting tests check stored evidence and axes behavior. All eight import
contracts passed. Base, pandas, storage, and ecosystem wheel stages passed,
including the new chart regression without relying on editable imports.

**Recommendation:** R5, add an installed-wheel journey invoking the new
`capability_study` API. The existing
[`e2e/test_studies.py::test_capability_study`](/Users/shane/lss4py/e2e/test_studies.py:181)
actually invokes `capability_indices`, so its name should not be mistaken for
coverage of the newly added composed entry point.

**Limits:** no image was visually inspected during this review; programmatic plot
checks do not prove label readability for large charts. Hosted GitHub Actions,
package publication, and production installation were not executed. A composed
study figure remains explicitly deferred, not a missing current implementation.

## Consolidated recommendations and open questions

No required fix remains open for F1–F3. The following improvements are nonblocking
for continuing the declared analytical slice. Order reflects the most useful
next validation work, not additional defect severity.

| ID | Priority / action | Consequence addressed | Acceptance condition and validation |
| --- | --- | --- | --- |
| R3 | Next iteration: genuine study backend comparisons | Same-backend repetition can miss backend-specific divergence. | Compare normalized complete nested payloads against one canonical backend; cover pandas/indexed pandas/Polars/Arrow and mixed short-/long-term inputs, including `missing="omit"`. Run with required PyArrow. |
| R2 | Next iteration: independent analytical properties | Internally consistent but wrong limits can satisfy current assertions. | Test that positive scaling scales ranges/limits and preserves signals, safe translation preserves ranges, and tampering rejection remains valid under scaling. Include zero/tiny/large deterministic cases and independently stated expected relationships; retain R fixtures. |
| R5 | Next iteration: installed composed-study journey | Source tests do not directly establish this API's installed customer path. | Invoke public `capability_study` with short/long samples, export and restore typed children and an audited bundle, and assert known observed counts and shared context in the applicable wheel stages. |
| R4 | Next iteration: malformed study evidence matrix | Valid round trips leave important rejection paths untested. | Exercise mismatched child counts/specifications, incomplete long-term triples, and wrong child types; require governed rejection from result restoration and audited bundle loading. Determine and document intended shared-parameter consistency before asserting it as an invariant. |
| R1 | Documentation follow-up: practical monitoring example | Users may misunderstand unit inheritance or act directly on a signal. | Add a reproducible example with explicit conversion before monitoring, inherited units, pair-level signal identity, and an investigation-oriented interpretation. Validate calculations through the public API; human review is needed to assess clarity. |

Remaining questions are bounded: how much parent/child parameter consistency is
promised at exchange boundaries; whether a practitioner can follow the monitoring
example without confusing specification and control limits; and whether large
keyed charts remain readable. None was established as a current product defect.
Within-subgroup estimation, non-normal capability, additional chart families,
automatic recalibration, and a composed study figure remain separate future scope.

## Coverage and validation record

The current assessment reuses checks actually executed in the immediately
preceding review/fix work in this chat. Analytical code and tests have not changed
since those post-fix checks; subsequent edits changed only review instructions.
This report did not rerun passing checks merely to produce a new narrative.
Counts below distinguish pre-fix evidence from current verification.

| Check actually executed | Result | What it establishes |
| --- | --- | --- |
| Focused locked pytest selection, `--extra storage --require-pyarrow`, covering charts/properties, studies/properties, reporting, bundles, reference catalog | Original: 232 passed; after fixes: 284 passed | Focused contracts and counterexamples across configured backends; original passing result did not establish absence of defects. |
| `uv run --locked --extra storage pytest --require-pyarrow --cov=src/lss4py --cov-report=term --cov-report=xml:/tmp/lss4py-fix-coverage.xml` | 2,638 passed, 5 xfailed; 96.07% statement coverage | Source regression suite passed the configured 90% threshold; expected failures are not passing feature implementations. |
| `uv run --locked python tools/check_wheel.py --ecosystem --artifacts-dir /tmp/lss4py-fix-wheel` | Base 33; pandas 44; storage 46; ecosystem 60 passed; zero failures/errors/skips in reports | Isolated wheel installation and existing customer paths plus the new chart regression. Stages overlap and are not a count of unique scenarios. |
| `Rscript --vanilla tools/r-reference/verify.R` | All 31 retained cases reproduced | Genuine locked R fixture replication before fixes; subsequent changes did not alter numerical formulas, generator, or R evidence. |
| `uv run --locked ruff check .` and `uv run --locked ruff format --check .` | Passed; 248 files already formatted | Configured lint and formatting checks passed after fixes. |
| `uv run --locked ty check` | Passed | Configured static types passed. |
| `uv run --locked import-linter lint --config lint_imports_config.ini` | 8 contracts kept, 0 broken | Configured dependency directions remained intact. |
| `git diff --check` | Passed | Patch whitespace checks passed. |

The initial focused pytest command selected `tests/test_control_chart.py`,
`tests/test_control_chart_properties.py`, `tests/test_capability_study.py`,
`tests/test_capability_study_properties.py`, `tests/test_reporting.py`,
`tests/test_reference_catalog.py`, and `tests/test_bundles.py`.

The Python environment used CPython 3.14.2 on macOS. Some uv checks initially
encountered cache permissions and were rerun with approved cache access; the
reported outcomes are the successful executions. No reference fixtures were
overwritten. No product changes were made while preparing this report.

Wheel tested after fixes:
`lss4py-0.2.2-py3-none-any.whl`, SHA-256
`e20237bd880924a34d67ec1d8e79b31a8b5fbf83784cd89dd6438af3898bf14f`.
Reports are currently available under `/tmp/lss4py-fix-wheel/tests/` and coverage
under `/tmp/lss4py-fix-coverage.xml`; these temporary files are not durable
repository evidence.

Selected current source fingerprints bind the follow-up to the uncommitted fixes:

| File | SHA-256 |
| --- | --- |
| `src/lss4py/_kernels/control_chart.py` | `89710f7fa6a87a09c6d7a5fc6a817a270d2177c933e77f17462f545080acc9a3` |
| `src/lss4py/_kernels/capability_study.py` | `eb41ce33f7f08eda7aaf33e25dab3751b0866abffc5411c0b4635298385b2461` |
| `src/lss4py/_bundle_schema.py` | `038bf3935bfc61db679998049b0021f1b21879c30a46e3abf75de30fb0985374` |
| `tests/test_control_chart.py` | `b1cfe6404bcc4870123303d2c4b93ffd35a84b44ae9565fd04856f7e7e47636b` |
| `e2e/test_control_chart.py` | `aa257bfbc6634126ca3f761a5275e1faffefe1e7ee0340be96d539871887fac8` |

Not performed: fresh dependency vulnerability audit, hosted CI/action execution,
visual-reference acceptance, independent practitioner/SME review, exhaustive
malformed nested-payload exploration, or publication. This review does not reuse
an older release assessment as proof of those outcomes.

## Decision

**The current change can proceed within its declared scope.** F1–F3 are fixed
and verified, and no additional product blocker was established. The test
skeptic's lower rating identifies concrete improvements in the strength of
evidence, especially the redundant study comparison and missing installed
composed-study journey. Address those in the next testing iteration. This is
approval of the assessed change, including its current local fixes, rather than
a whole-project release or publication certification.

## Recommendation completion addendum — 2026-11-05

All five recommendations have been implemented and checked. This follow-up adds
tests, examples, and documentation; it makes no further analytical implementation
changes beyond the previously verified F1–F3 fixes. HEAD remains `cccbdd5` and
the changes are local and uncommitted.

| Recommendation | Completed work | Verification |
| --- | --- | --- |
| R3 — backend comparisons | Replaced the repeated same-backend reference with a canonical Polars reference. Added all 16 short-/long-term backend combinations under complete and explicit-omit policies, checking complete normalized parent/child payloads plus actual backend/version provenance, retained/excluded counts, and nondefault shared confidence/normality settings. Normalization removes only backend identity/version and calculation timestamps. | Required PyArrow source suite passed. [`tests/test_capability_study.py`](/Users/shane/lss4py/tests/test_capability_study.py), with independent factories in [`tests/conftest.py`](/Users/shane/lss4py/tests/conftest.py). |
| R5 — installed study journey | Added a public `capability_study` CSV journey with an explicit missing row, hand-derived short-term mean/Cp/Cpk and observed counts, typed nested restoration, and a saved/reopened audited bundle with source verification and specification links. | New journey passed in every wheel stage. [`e2e/test_capability_study.py`](/Users/shane/lss4py/e2e/test_capability_study.py). |
| R2 — independent analytical properties | Added translation invariance and positive-scaling properties for moving ranges, limits, and signal identity, plus scaled Phase II baseline reuse and tamper rejection. Binary scaling spans exponents −400 through 400; integer translations avoid introducing rounding cancellation into the asserted mathematical relationships. Existing deterministic zero/tiny/large regressions and genuine R references remain. | Source suite passed the generated properties. [`tests/test_control_chart_properties.py`](/Users/shane/lss4py/tests/test_control_chart_properties.py). |
| R4 — malformed nested evidence | Added count/specification/wrong-child-type mutations for both sample roles and every incomplete long-term triple. Each case must fail direct restoration and audited JSON loading. Edited bundles are re-fingerprinted so rejection exercises semantic validation rather than merely a stale digest. Documented shared-setting propagation and the limits of restoration versus explicit analytical replay. | Source suite and subsequent focused study rerun passed. [`tests/test_capability_study.py`](/Users/shane/lss4py/tests/test_capability_study.py), [`docs/capability-study.md`](/Users/shane/lss4py/docs/capability-study.md). |
| R1 — worked monitoring example | Added an executable example retaining raw seconds, explicitly deriving minutes, inheriting the baseline unit, and tracing the signaled pair `g → h`. The guide explains baseline suitability, batch adjacency, specification/control-limit distinctions, and investigation without asserting a cause. | Example executed successfully with assertions: baseline center 1.8 minutes, UCL approximately 5.8798 minutes, monitoring ranges `[10, 1]`, and ending source position `[1]`. [`examples/yellow_belt/monitoring.py`](/Users/shane/lss4py/examples/yellow_belt/monitoring.py), [`docs/control-charts.md`](/Users/shane/lss4py/docs/control-charts.md). |

Fresh follow-up validation:

- `uv run --locked --extra storage pytest --require-pyarrow --cov=src/lss4py --cov-report=term --cov-report=xml:/tmp/lss4py-followups-coverage.xml --junitxml=/tmp/lss4py-followups-source.xml`:
  **2,708 passed, 5 xfailed, 96.07% statement coverage**.
- `uv run --locked python tools/check_wheel.py --ecosystem --artifacts-dir /tmp/lss4py-followups-wheel`:
  **base 34, pandas 46, storage 48, ecosystem 62 passed**, with zero failures or
  errors. The stages overlap; these are not unique-scenario totals.
- The final fixture refinement preserves comparison against the original computed
  study rather than comparing two restored copies. Its subsequent focused run,
  `uv run --locked --extra storage pytest --require-pyarrow tests/test_capability_study.py`,
  passed **92 tests**. The full-suite count above precedes that fixture-only refinement.
- Ruff lint, formatting, ty, Vulture, all eight import contracts, and
  `git diff --check` passed. The monitoring example's assertions passed on execution.

The wheel digest remained
`e20237bd880924a34d67ec1d8e79b31a8b5fbf83784cd89dd6438af3898bf14f`, consistent
with no additional packaged implementation changes. The expanded wheel journeys
exercise that same artifact. Reports under `/tmp/lss4py-followups-*` are temporary.

The specific test weaknesses behind the earlier `Needs improvement` assessment
have been addressed; the test-skeptic follow-up rating is **Adequate**, with
**High** confidence in closure of these named recommendations. This does not
establish exhaustive correctness. Independent practitioner validation, complete
provenance-parameter certification on restoration, visual acceptance, and future
analytical features retain the limits stated above. The runnable documentation
has been checked technically; no external usability study was performed.

**Follow-up decision:** R1–R5 no longer stand in the way of the next functional
requirement implementation phase. The declared-scope decision remains that the
change can proceed.
