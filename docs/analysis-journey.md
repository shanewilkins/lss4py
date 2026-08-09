# LSS4PY Analysis Journey

LSS4PY is intended to help a practitioner move from an improvement question to an
auditable decision. It is not merely a menu of R-compatible functions. The user
requirements catalog records the detailed outcomes; this document supplies the
journey that connects them.

## 1. Prepare the evidence

The practitioner brings a pandas, Polars, or other supported table, or loads a
governed process/event-log source. LSS4PY identifies the schema, preserves explicit
case and row keys, validates timestamps and measurement fields, and reports data
quality before analysis.

Relevant requirements: UR-003, UR-014, UR-015, UR-016.

## 2. Define the process and question

The practitioner identifies the CTQ, unit, opportunity, target, specification
limits, cohort, process steps, and decision to be made. Declared process structure
and cause hypotheses can be represented without pretending they were inferred from
the observations.

Relevant requirements: UR-017, UR-018, UR-019, UR-020.

## 3. Measure the current system

The practitioner establishes trustworthy measurement and baseline performance:
time and efficiency metrics, stage and defect yield, tail summaries, confidence
intervals, measurement-system studies, and distribution diagnostics.

Relevant requirements: UR-001, UR-002, UR-004, UR-013, UR-021, UR-022, UR-030,
UR-035.

## 4. Analyze stability, capability, and drivers

The practitioner distinguishes instability from incapability, then investigates
where variation and delay are associated with process structure, cohorts, factors,
and defect categories. LSS4PY exposes assumptions and evidence; it does not turn an
association into a causal claim.

Relevant requirements: UR-005, UR-009, UR-010, UR-023 through UR-028, UR-031,
UR-032, UR-036 through UR-041.

## 5. Improve and choose

The practitioner compares before/after cohorts, quantifies quality loss, evaluates
queueing and redesign scenarios, and weighs robust capacity or resource choices.
Simulation and optimization results remain distributions and tradeoffs rather than
false point certainty.

Relevant requirements: UR-008, UR-011, UR-027, UR-038 through UR-043.

## 6. Control and learn

The practitioner establishes reusable baselines, control limits, rules, and profile
monitoring; detects drift; records signals; and can reproduce the analysis against
the same versioned evidence later.

Relevant requirements: UR-025, UR-028, UR-031, UR-036, UR-044.

## 7. Communicate and teach

Every analysis can produce an inspectable result bundle for notebooks, optional
plots, downstream deliverables, or review. Worked examples and reference datasets
support learning without being confused with production evidence. Educational
assets that do not belong in the analytics core remain explicit ecosystem scope.

Relevant requirements: UR-006, UR-007, UR-012, UR-029, UR-033, UR-034, UR-045.

## Product interaction model

For a governed analysis, LSS4PY should:

1. **frame** the analytical question and required fields;
2. **validate** data, design, and assumptions;
3. **suggest** appropriate analyses and explain alternatives;
4. **compute** only the analyses the user chooses;
5. **diagnose** uncertainty, assumption failures, and sensitivity;
6. **return** typed, backend-neutral results; and
7. **export** provenance sufficient to reproduce and review the result.

This interaction model is the practical meaning of an assistive analytical facade.

