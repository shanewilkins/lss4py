# ADR-0015: Belt-Level Governance and Practitioner Progression

**Status:** Proposed

> The practitioner-progression decision remains proposed. ADR-0019 supersedes
> this record's module-organization examples and implementation roadmap.

**Context:**

LSS4PY supports a progression from foundation to mastery aligned to Six Sigma belt certifications.
Belt levels describe the *analytical sophistication* available to practitioners at each skill tier,
not the package's internal file organization.

Internal organization (adapters, analytics, kernels, workflows) is by *function*, not belt level.
A single module (e.g., `analytics/`) may contain methods spanning multiple belt levels.

Belt governance answers: "What analyses should a practitioner at this level use for decision-making?"

**Decision:**

We define four belt levels, each supported by a development milestone:

| Belt Level | Release | Milestone | User Analyses | Characteristics |
|---|---|---|---|---|
| **White Belt** | v0.2 | **Contract Foundation** | Data validation, schema inspection, basic descriptive stats, CTQ definition | Awareness; understand the data, process, and question before analysis. No causal or predictive claims. Governed by UR-001–005, UR-014–018. |
| **Yellow Belt** | v0.3 | **MVP Complete** | Time metrics, efficiency, yield, defect rates, descriptive statistics, Pareto/cause-effect, basic capability, process-aware aggregations, quality loss | Basic improvement; apply straightforward tools to measure current system and identify obvious improvement opportunities. Governed by UR-004, UR-007, UR-010, UR-012, UR-014, UR-021–025, UR-027, UR-029–030. |
| **Green Belt** | v0.5 | **Professional Depth** | Measurement systems (Gage R&R, MSA), control charts (I-MR, X-bar/R/S, attribute), capability studies (normal and non-normal), hypothesis tests, effect estimates, before/after comparisons, correlation/regression, foundational DOE, process bottleneck analysis | Professional project management; design and execute controlled comparisons, validate measurement system, and support team decisions with statistical confidence. Governed by UR-008–010, UR-013, UR-024, UR-035–041. |
| **Black Belt** | v0.7 | **Master Depth** | Advanced MSA, advanced regression, full DOE portfolio, response surface methods, process monitoring and profile analysis, conformance/drift detection, discrete-event simulation, robust optimization, redesign scenario evaluation | Strategic improvement; lead organization-wide transformation programs, design complex experiments, optimize multi-objective systems, and build predictive/monitoring models. Governed by UR-006, UR-009, UR-011, UR-013, UR-028, UR-031–032, UR-035, UR-039–043. |

**Supported Workflows by Belt**

### White Belt (v0.2)

- *Assess data readiness*: Import data, validate schema, detect missing/invalid values, understand distributions
- *Frame the question*: Define CTQ, unit, opportunity, specification limits, target, hypothesis
- *Establish baseline*: Describe mean, median, spread, outliers (no tests or claims of stability)

### Yellow Belt (v0.3)

- *Measure current state*: Calculate lead time, cycle time, efficiency, yield (stage or rolled)
- *Identify obvious waste*: Pareto analysis of defect categories, cause-and-effect diagrams
- *Assess basic capability*: Is the process meeting specification? (Cp/Cpk with caution)
- *Detect gross instability*: Run charts, I-MR charts (basic pattern recognition)
- *Quantify quality loss*: Economic impact of defects and variation
- *Model simple processes*: Event-log aggregations with process awareness

### Green Belt (v0.4–v0.5)

- *Validate measurement system*: Gage R&R, repeatability/reproducibility thresholds
- *Control the current state*: Design X-bar/R or attribute control plans, establish rational subgroups
- *Assess true capability*: Box-Cox transformation, probability plots, Anderson-Darling tests
- *Test hypotheses*: t-tests, ANOVA, chi-square, correlation significance
- *Quantify improvement*: Before/after paired comparisons, effect sizes, confidence intervals
- *Explore relationships*: Scatter plots, correlation/regression, interaction plots
- *Design screening experiments*: 2k, 2k-p factorial designs
- *Analyze processes*: Bottleneck identification, variant analysis, parallel-path metrics

### Black Belt (v0.6–v0.7)

- *Advanced measurement*: Component of variance, nested designs, automated Gage R&R screening
- *Predictive modeling*: Multiple regression, logistics regression, CART/tree methods
- *Optimization*: DOE on factors and levels, response surface methods, multi-objective optimization
- *Simulation*: Discrete-event queuing and redesign scenarios (discrete/continuous)
- *Monitoring & conformance*: Profile monitoring, control limits on complex statistics, drift detection
- *Advanced inference*: Non-linear regression, generalized linear models, Bayesian estimation

**Module Organization (Functional, NOT by Belt)**

Modules are organized by analytical function. Governance tags identify which belt level can employ each analysis:

```
src/lss4py/
├── adapters/              [White, Yellow, Green, Black]
├── analytics/
│   ├── descriptive.py     [White, Yellow]
│   ├── capability.py      [Yellow, Green, Black]
│   ├── spc.py            [Yellow, Green]
│   ├── inference.py      [Green, Black]     (planned)
│   ├── doe.py            [Green, Black]     (planned)
│   └── simulation.py      [Black]            (planned)
├── domain/
│   ├── models.py          [White, Yellow, Green, Black]
│   ├── validation.py      [White, Yellow, Green, Black]
│   └── diagnostics.py     [Yellow, Green, Black]
├── kernels/               [All; internal API only]
├── reporting/             [White, Yellow, Green, Black]
├── workflows/             [Orchestrate by belt]
└── yellow_belt.py         [DEPRECATED; refactor into analytics/] ⚠️
```

### Governance Tags in Code

Each public analysis function includes a docstring tag:

```python
def my_analysis(...) -> Result:
    """
    Analyze X using Y method.
    
    **Belt Level:** Green Belt (hypothesis testing)
    
    **Suitable When:** You have paired samples and want to test if the mean differs.
    
    **Not Suitable When:** Samples are unpaired, or you need effect size or confidence intervals.
    
    **Related Methods:** independent samples t-test, Welch's t-test, paired ANOVA.
    """
```

**Consequences**

1. **Practitioners have a clear learning path:** White → Yellow → Green → Black, matched to LSS training.
2. **Governance is explicit but decoupled from filenames:** Analysts don't get confused by "yellow_belt.py".
3. **Module organization scales:** New methods added to `analytics/` are governed by belt level in their docstrings, not the filename.
4. **Workflows can orchestrate by belt:** `workflows/yellow_belt/` aggregates Yellow Belt analyses into DMAIC projects.
5. **Quality gates are belt-specific:** Tests, benchmarks, and parity requirements vary by belt.

**Implementation Roadmap**

| Phase | Release | Action |
|---|---|---|
| 1 | v0.2 | Create this ADR; tag yellow_belt.py and adapter analyses with White/Yellow labels |
| 2 | v0.3 | Add Green Belt labels to control-chart and capability analyses; begin refactoring yellow_belt.py |
| 3 | v0.4 | Move Yellow Belt analyses into appropriate analytics/ submodules; deprecate yellow_belt.py |
| 4 | v0.5 | Implement Green Belt analyses in analytics/; add Green Belt governance tags and examples |
| 5 | v0.6–v0.7 | Implement Black Belt analyses; complete belt-level workflow orchestration |

**Open Questions**

- Should we create top-level workflow orchestrators (workflows/yellow_belt.py, workflows/green_belt.py)?
- Should each belt level have its own requirements traceability matrix?
- How do we handle cross-belt methods (e.g., regression used by both Green and Black)?

**Related**

- ADR-0001: Lightweight document governance (belt levels are a governance structure)
- ADR-0002: Package focus on analytics (belt levels describe analytical scope)
- Roadmap.md: Release-to-belt mapping
- UR (user requirements) and TR (technical requirements) CSVs: Belt-level requirement ownership
