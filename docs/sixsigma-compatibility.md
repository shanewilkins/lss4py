# R `SixSigma` Compatibility Matrix

This document maps the public analytical and visualization surface of the R
[`SixSigma`](https://cran.r-project.org/package=SixSigma) package to a proposed,
Pythonic LSS4PY surface.

Reference baseline:

- R package: `SixSigma` 0.11.1
- R reference: [CRAN help index](https://search.r-project.org/CRAN/refmans/SixSigma/html/00Index.html)
- LSS4PY snapshot: 0.1.0 on 2026-08-08

Bundled R example datasets are not treated as API features. Selected datasets may
instead become test fixtures for cross-language numerical parity.

## Status definitions

| Status | Meaning |
|---|---|
| Implemented | Public, tested LSS4PY behavior covers the R capability. |
| Partial | LSS4PY has related working behavior, but not the same contract or complete semantics. |
| Stub | A named LSS4PY entry point exists but raises `NotImplementedError`. |
| Gap | No corresponding LSS4PY implementation exists. |

`Partial` does not claim numerical parity. There are no `Implemented` rows in this
snapshot.

## User-requirement coverage

Every retained callable R capability maps to an explicit user outcome. Several R
functions share one requirement when they are steps in the same user journey.

| R `SixSigma` API | User requirement |
|---|---|
| `ss.ca.yield` | UR-022 defect and rework performance |
| `ss.ca.cp`, `ss.ca.cpk`, `ss.ca.z` | UR-023 capability indices |
| `ss.study.ca` | UR-024 capability study |
| `ss.cc` | UR-025 moving-range control chart |
| `ss.cc.getd2`, `ss.cc.getd3`, `ss.cc.getc4` | UR-026 control-chart constants |
| `ss.rr` | UR-013 Gage R&R |
| `ss.ci` | UR-021 mean confidence interval and diagnostics |
| `ss.lf`, `ss.lfa` | UR-027 Taguchi quality loss |
| `ss.pMap` | UR-019 declared process map |
| `ss.ceDiag` | UR-020 cause-and-effect model |
| `climProfiles`, `outProfiles`, `smoothProfiles`, `plotProfiles`, `plotControlProfiles` | UR-028 profile monitoring |
| `ss.heli` | UR-034 paper-helicopter training asset |

## Capability and yield

| R `SixSigma` API | R behavior | Proposed LSS4PY API | Status | Current evidence / parity requirement |
|---|---|---|---|---|
| `ss.ca.cp` | Process capability index Cp, optionally with a confidence interval | `capability_indices(...).cp` | Gap | No governed capability calculation exists. Match one- and two-sided specification handling, missing-value policy, and confidence intervals. |
| `ss.ca.cpk` | Centered process capability index Cpk, optionally with a confidence interval | `capability_indices(...).cpk` | Gap | No governed capability calculation exists. Match lower/upper component selection and confidence intervals. |
| `ss.ca.z` | Sigma score from process data and specification limits | `capability_indices(...).z` | Gap | No governed capability calculation exists. Match one-sided limits and the R package's short-term interpretation. |
| `ss.ca.yield` | Yield, first-time yield, rolled-throughput yield, and DPMO from defect/rework counts | `process_yield(defects, *, rework=None, opportunities=1)` returning `YieldResult` | Partial | `rolled_yield()` and two stage-yield helpers work on binary funnel stages, not defect/rework vectors. Add the R counting semantics and validate against `ss.ca.yield()` fixtures. |
| `ss.study.ca` | Capability-study plots, normality checks, specification limits, target, and short-/long-term views | `capability_study(...)` returning `CapabilityStudyResult`; plotting kept in a visualization layer | Gap | No governed capability study exists. Calculation results must be usable without rendering; plots should consume the typed result. |

## Statistical process control

| R `SixSigma` API | R behavior | Proposed LSS4PY API | Status | Current evidence / parity requirement |
|---|---|---|---|---|
| `ss.cc` | Moving-range control chart with Phase I/II limits and out-of-control points | `control_chart(..., chart="moving_range")` returning `ControlChartResult` | Gap | No governed SPC calculation exists. Match LCL, center line, UCL, phase, and flagged observations before adding more chart families. |
| `ss.cc.getd2` | Relative-range constant d2 for a sample size | `control_chart_constants(n).d2` | Gap | Match supported sample sizes and error behavior. |
| `ss.cc.getd3` | Relative-range constant d3 for a sample size | `control_chart_constants(n).d3` | Gap | Match supported sample sizes and error behavior. |
| `ss.cc.getc4` | Bias-correction constant c4 for a sample size | `control_chart_constants(n).c4` | Gap | Match supported sample sizes and error behavior. |

`ss.cc.constants` is the R documentation topic shared by the three exported lookup
functions, not a fourth callable API.

## Measurement and basic statistics

| R `SixSigma` API | R behavior | Proposed LSS4PY API | Status | Current evidence / parity requirement |
|---|---|---|---|---|
| `ss.rr` | Crossed or nested Gage R&R, ANOVA, variance components, study variation, ndc, and six diagnostic plots | `gage_rr(...)` returning `GageRRResult` | Gap | Support crossed and nested studies. Keep ANOVA/variance tables and plotting separate, while matching variance-component and distinct-category calculations. |
| `ss.ci` | Confidence interval for a mean plus normality diagnostics and plots | `mean_confidence_interval(...)` returning `MeanCIResult`; `plot_mean_diagnostics(result)` | Gap | Separate inference from side effects. Match confidence bounds and document any deliberate difference in normality tests. |

## Quality loss

| R `SixSigma` API | R behavior | Proposed LSS4PY API | Status | Current evidence / parity requirement |
|---|---|---|---|---|
| `ss.lf` | Taguchi loss for one observed CTQ value | `quality_loss(value, *, tolerance, target, loss_at_tolerance)` | Gap | Scalar and array-like inputs should use the same nominal-the-best formula as R. |
| `ss.lfa` | Quality-loss analysis with loss coefficient, MSD, average loss, optional total loss, text, and plot output | `quality_loss_analysis(...)` returning `QualityLossResult` | Gap | Return data only from the analysis function; provide formatting and plotting separately. Cover nominal-, smaller-, and larger-the-better conventions used by R. |

## Process-definition visuals

| R `SixSigma` API | R behavior | Proposed LSS4PY API | Status | Current evidence / parity requirement |
|---|---|---|---|---|
| `ss.pMap` | Draws a supplied process map with overall inputs/outputs and step-level x/y characteristics | `plot_process_map(process_model, ...)` | Partial | `map_process(EventStream)` currently discovers nodes and transition counts from observed events. `ProcessModelIR` represents explicit topology, but neither reproduces the R diagram contract. Preserve discovery and visualization as separate operations. |
| `ss.ceDiag` | Cause-and-effect (Ishikawa/fishbone) diagram grouped by cause family | `plot_cause_effect(effect, causes_by_group, ...)` | Gap | Prefer a mapping such as `Mapping[str, Sequence[str]]` over parallel vectors. Rendering is the parity target. |

## Profile monitoring

| R `SixSigma` API | R behavior | Proposed LSS4PY API | Status | Current evidence / parity requirement |
|---|---|---|---|---|
| `climProfiles` | Phase I prototype profile and confidence bands | `profile_control_limits(...)` returning `ProfileLimitsResult` | Gap | Accept NumPy arrays and pandas frames; match prototype and band calculations, smoothing flags, and alpha. |
| `outProfiles` | Identifies out-of-control profiles and their outside-band proportions | `detect_out_of_control_profiles(...)` returning `ProfileOutliersResult` | Gap | Match labels, indices, outside proportions, and tolerance threshold. |
| `smoothProfiles` | Regularizes profiles using support-vector regression | `smooth_profiles(...)` | Gap | Place the ML dependency behind an optional extra and document parameter translation. |
| `plotProfiles` | Plots profiles, optional limits, and optional out-of-control filtering | `plot_profiles(...)` | Gap | Accept the typed limit/outlier results directly. |
| `plotControlProfiles` | Plots each profile's outside-band proportion against a tolerance | `plot_profile_control(...)` | Gap | Visualization-only parity. |

## Training utility

| R `SixSigma` API | R behavior | Proposed LSS4PY API | Status | Current evidence / parity requirement |
|---|---|---|---|---|
| `ss.heli` | Writes an A4 paper-helicopter PDF template | `paper_helicopter_template(path, ...)` | Gap | Low-priority educational asset. It should use an explicit output path and return that path. |

## LSS4PY extensions without a direct R `SixSigma` equivalent

These are intentional Python-first/product-specific capabilities, not compatibility
gaps:

| LSS4PY API | Current status | Purpose |
|---|---|---|
| `lead_time` | Stable | Per-row or per-case elapsed process time. |
| `wait_time` | Stable for explicit measured columns | Lead time less active cycle time; branch-aware interval-log semantics remain planned. |
| `process_cycle_efficiency` | Stable for explicit measured columns | Value-add time divided by lead time; branch-aware interval-log semantics remain planned. |
| `takt_time` | Stable | Available production time divided by customer demand. |
| `created_to_booked_yield` | Stable | Binary stage-conversion yield. |
| `booked_to_completed_yield` | Stable | Binary stage-conversion yield. |
| `rolled_yield` | Stable | Product of the two configured stage yields. |
| `ProcessModelIR` and related IR types | Stable for the current Yellow Belt slice | Explicit process topology and metric bindings, including parallel and rework semantics. |
| `map_process` | Experimental | Discovers activity nodes and transition counts from an event log. |

## Delivery governance

The [roadmap](roadmap.md) owns delivery order; this matrix owns compatibility
coverage and status. Numerical parity acceptance is governed by
[TR-007](requirements/technical-requirements.csv).
