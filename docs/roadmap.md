# Roadmap to LSS4PY 1.0

LSS4PY supports practitioner progression from awareness to mastery, aligned to Six Sigma belt certifications.
Belt levels describe the analytical sophistication available to practitioners at each skill tier,
not internal package organization.

## Release Strategy

LSS4PY releases follow a **two-phase pattern** per belt level:

1. **Even releases** (v0.2, v0.4, v0.6, v0.8): Build infrastructure and implement core methods
   - Implement analytical algorithms and kernels
   - Validate numerical accuracy against reference implementations (R `SixSigma`, NIST)
   - Establish backend-neutral contracts and data models
   - May include experimental workflows; not yet complete for practitioner use

2. **Odd releases** (v0.1, v0.3, v0.5, v0.7, v0.9): Validate contracts, complete workflows, improve quality
   - Create end-to-end workflows demonstrating practical DMAIC/transformation cycles
   - Add governance tags and belt-level guidance to all analyses
   - Implement parameterized backend-parity tests
   - Write reproducible worked examples and reference cases
   - Improve error messages, diagnostics, and documentation
   - Declare belt level "complete" and ready for practitioner use

**Result:** Green Belt complete at v0.5; Black Belt complete at v0.7; stable API at v1.0.

**Belt Level → Release Milestone Mapping:**

| Belt | Milestone | Release | Scope | User Journey |
|---|---|---|---|---|
| **White** | Contract Foundation | v0.2 | Data validation, schema inspection, basic descriptive stats, CTQ definition | Understand the data, process, and question before analysis |
| **Yellow** | MVP Complete | v0.3 | Time metrics, efficiency, yield, defect rates, Pareto, basic capability, quality loss | Apply straightforward tools to measure and identify improvement opportunities |
| **Green** | Professional Depth | v0.5 | MSA/Gage R&R, control charts, capability studies, hypothesis tests, DOE, bottleneck analysis | Design and execute controlled comparisons with statistical confidence |
| **Black** | Master Depth | v0.7 | Advanced MSA, regression, full DOE portfolio, simulation, robust optimization | Lead organization-wide transformation and predictive modeling |
| **Polish** | Integration & Polish | v0.8–v0.9 | Naming, documentation, diagnostics, performance, accessibility | Stabilize the practitioner contract |
| **Stable** | Semantic Versioning | v1.0 | Supported API and compatibility guarantees | Publish stable contract; practitioners can update confidently |

See [ADR-0015](docs/adr/0015-belt-level-governance.md) for governance detail.

LSS4PY's MVP is a practitioner-complete **Yellow Belt toolkit at v0.3** (odd: complete).
Green Belt infrastructure is built at v0.4 (even: core methods), validated and completed at v0.5 (odd: workflows & ergonomics).
Black Belt infrastructure is built at v0.6 (even: core methods), validated and completed at v0.7 (odd: workflows & ergonomics).
Versions v0.8–v0.9 close gaps and polish the API before v1.0 declares semantic versioning.

Belt labels describe the analyses the package supports. They are not certification claims.

| Release | Product gate | Scope |
| --- | --- | --- |
| **v0.1** | Baseline honesty and control | Establish the governed documentation set, compatibility matrix, explicit stable-versus-experimental boundary, locked quality gates, and the initial stable Yellow Belt slice for current metrics, yields, and process-model-aware event-log calculations. |
| **v0.2** | Contract foundation | Adopt backend-neutral input and result contracts, add reusable validation and normalization, define CTQ/specification and provenance models, introduce analysis-guidance and parity-fixture scaffolding, and preserve the working v0.1 slice while those contracts migrate. |
| **v0.3** | **MVP: Yellow Belt complete** | Support an end-to-end basic DMAIC project: define CTQs and process maps; validate data; calculate time, efficiency, yield, defects, DPMO, descriptive and tail statistics; create Pareto and cause-and-effect analyses; estimate a mean; assess basic stability and capability with run/I-MR charts and Cp/Cpk/Z; quantify quality loss; establish an initial baseline; create a basic control plan; and export reproducible results and plots. Include governed worked examples and the applicable R `SixSigma` parity cases. |
| **v0.4** | Green Belt infrastructure | Build core Green Belt analytical machinery: implement Gage R&R and MSA kernels; add hypothesis testing infrastructure (t-tests, ANOVA, correlation); implement control chart algorithms (I-MR, X-bar/R, attribute); add capability study kernels with Box-Cox transformation; implement foundational DOE kernels; and build process bottleneck/variant analysis infrastructure. Numerical parity validation against R `SixSigma`. |
| **v0.5** | **Green Belt complete** | Validate Green Belt contract: create end-to-end DMAIC workflows with MSA validation, hypothesis testing with effect sizes and confidence intervals, control chart designs with rational subgrouping, capability studies including non-normal methods, before/after comparisons, foundational DOE with guidance, process bottleneck analysis, and stronger control-plan workflows. Include Green Belt governance tags, parameterized backend-parity tests, and reproducible worked examples. |
| **v0.6** | Black Belt infrastructure | Build core Black Belt analytical machinery: implement advanced MSA (component of variance, nested designs); add advanced regression kernels (multiple, logistic, GLM, smoothing); implement full DOE portfolio infrastructure (response surface methods, optimization algorithms); build discrete-event simulation engine; implement profile monitoring and conformance/drift detection; add robust optimization solvers; and validate against R `SixSigma` and NIST reference cases. |
| **v0.7** | **Black Belt complete** | Validate Black Belt contract: create end-to-end transformation workflows with advanced MSA screening, predictive modeling with interpretation, response surface design and analysis, multi-objective optimization scenarios, discrete-event simulation with redesign capabilities, profile monitoring with control limits, and conformance/drift detection. Include Black Belt governance tags, parameterized backend-parity tests, complete R `SixSigma` parity study, and reproducible transformation scenario examples. |
| **v0.8** | Integration and gap closure | Close cross-workflow, backend-parity, numerical-validation, performance, and compatibility gaps discovered while assembling complete projects. Add no new belt-level capability category. |
| **v0.9** | **Polish only; feature freeze** | Stabilize naming and signatures, finish documentation and examples, improve errors and diagnostics, verify accessibility and plotting semantics, harden serialization and migrations, benchmark performance, and complete packaging and upgrade guidance. |
| **v1.0** | Stable practitioner contract | Publish the supported API and compatibility guarantees under semantic versioning. Every claimed belt workflow is documented, tested, reproducible, and usable without a mandatory pandas or Polars dependency. |

## Release-targeting rules

The requirement CSVs own **status**, **priority**, and broad **product horizon**.
This roadmap owns the exact release targeting for `v0.1`, `v0.2`, `v0.3`, and later milestones.

Release targeting answers a different question than status.
A requirement may appear as `Partial` or `Planned` while still being owned by a release.
Changing the release that owns a requirement is a roadmap change, not a silent CSV edit.

## Primary release ownership

The lists below identify the release that primarily owns each requirement family.
Later releases inherit any earlier requirement that is still not satisfied.

### User requirements

- **v0.1:** UR-001, UR-002, UR-003, UR-005.
- **v0.2:** UR-006, UR-015, UR-016, UR-017, UR-018, UR-033, UR-045.
- **v0.3:** UR-004, UR-007, UR-010, UR-012, UR-014, UR-021, UR-022, UR-023, UR-024, UR-025, UR-027, UR-029, UR-030, UR-041, UR-044.
- **v0.4:** UR-008, UR-009, UR-013, UR-035, UR-036, UR-037.
- **v0.5:** UR-010, UR-024, UR-038, UR-039, UR-040, UR-041.
- **v0.6:** UR-011, UR-028, UR-031, UR-032, UR-039, UR-043.
- **v0.7:** UR-006, UR-009, UR-011, UR-013, UR-028, UR-031, UR-032, UR-035, UR-039, UR-040, UR-042, UR-043.

### Technical requirements

- **v0.1:** TR-001, TR-003, TR-004, TR-005, TR-008, TR-011.
- **v0.2:** TR-002, TR-007, TR-009, TR-010, TR-014, TR-015, TR-016, TR-017, TR-018, TR-019, TR-020, TR-021, TR-033, TR-037, TR-038.
- **v0.3:** TR-006, TR-012, TR-013, TR-022, TR-023, TR-024, TR-026, TR-028, TR-030, TR-032, TR-035, TR-036.
- **v0.4:** TR-025, TR-026, TR-027, TR-028, TR-029, TR-030, TR-031, TR-034.
- **v0.5:** TR-032, TR-035, TR-036, TR-039, TR-040.
- **v0.6:** TR-039, TR-040, TR-041, TR-042, TR-043, TR-044.
- **v0.7:** TR-041, TR-042, TR-043, TR-044, TR-045, TR-046.

## Release philosophy

**Even releases (v0.2, v0.4, v0.6, v0.8):** Implement core infrastructure and algorithms

- Add new analytical methods and kernels
- Validate numerical accuracy against reference implementations (R, NIST)
- Implement backend-neutral contracts
- Build internal APIs and registries
- May include experimental or incomplete workflows

**Odd releases (v0.1, v0.3, v0.5, v0.7, v0.9):** Validate contracts, tighten quality, improve ergonomics

- Complete end-to-end workflows and DMAIC projects
- Add governance tags and belt-level guidance
- Create parameterized backend-parity tests
- Write worked examples and reference scenarios
- Improve error messages and diagnostic reports
- Finalize documentation and API ergonomics
- Declare methods "complete" for a belt level

## Release gates

A method is release-ready when:

- It covers relevant user and technical requirements in the requirement CSVs
- It returns typed, backend-neutral results with assumptions, warnings, and provenance
- It has pandas and Polars contract parity where tabular input is involved
- It includes positive, invalid-input, and numerical-reference tests
- It is demonstrated by at least one reproducible, worked example

A belt milestone is complete only when:

- All methods for that belt level pass release gates
- End-to-end workflows demonstrate DMAIC or transformation cycles
- Governance tags clarify suitability and alternatives
- Traceability matrix shows all relevant requirements satisfied

A release is publishable only when:

- All required methods and workflows pass method release gates
- Wheel (`.whl`) and source (`.tar.gz`) distributions build successfully: `uv build` returns exit code 0
- Package metadata (name, version, dependencies, classifiers) is correct and complete
- PyPI upload succeeds with proper formatting and no warnings
- Version is bumped in `pyproject.toml` and tagged in VCS
- Changelog is updated with release notes and requirement/TR traceability
- Installation and import verification passes on the published package
