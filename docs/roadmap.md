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
| **v1.0** | Stable practitioner contract | Publish the supported API and compatibility guarantees under semantic versioning. Every claimed belt workflow is documented, tested, and reproducible. Callers are not required to supply pandas or Polars inputs, while core ingestion may continue to use Polars internally. |

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
- **v0.2:** UR-006, UR-015, UR-016, UR-017, UR-018, UR-033, UR-045, UR-048, UR-049.
- **v0.3:** UR-004, UR-007, UR-010, UR-012, UR-014, UR-021, UR-022, UR-023, UR-024, UR-025, UR-027, UR-029, UR-030, UR-041, UR-044, UR-046, UR-047.
- **v0.4:** UR-008, UR-009, UR-013, UR-035, UR-036, UR-037.
- **v0.5:** UR-010, UR-024, UR-038, UR-039, UR-040, UR-041.
- **v0.6:** UR-011, UR-028, UR-031, UR-032, UR-039, UR-043.
- **v0.7:** UR-006, UR-009, UR-011, UR-013, UR-028, UR-031, UR-032, UR-035, UR-039, UR-040, UR-042, UR-043.

### Technical requirements

- **v0.1:** TR-001, TR-003, TR-004, TR-005, TR-008, TR-011.
- **v0.2:** TR-002, TR-007, TR-009, TR-010, TR-014, TR-015, TR-016, TR-017, TR-018, TR-019, TR-020, TR-021, TR-033, TR-037, TR-038, TR-039, TR-041, TR-042.
- **v0.3:** TR-006, TR-012, TR-013, TR-022, TR-023, TR-024, TR-026, TR-028, TR-030, TR-032, TR-035, TR-036, TR-040, TR-043, TR-044, TR-045, TR-046.
- **v0.4:** TR-025, TR-026, TR-027, TR-028, TR-029, TR-030, TR-031, TR-034, TR-047.
- **v0.5:** TR-032, TR-035, TR-036.
- **v0.6:** TR-029, TR-031.
- **v0.7:** TR-025, TR-027, TR-029, TR-030, TR-031, TR-034.

The former v0.5–v0.7 references to TR-039–TR-045 had no corresponding
register definitions. TR-039–TR-045 now identify the book requirements and are
assigned above. Later-release MSA, modeling, simulation, profile, conformance,
and non-normal capability work remains covered by its existing registered
families and release scopes. The former undefined placeholder was removed before
TR-046 and TR-047 were assigned to the ingestion contracts in ADR-0026.

### Ingestion contract delivery

[ADR-0026](adr/0026-method-specific-input-contracts-and-ocel-interchange.md)
sets the firm boundary at validated, method-specific inputs (TR-046). The v0.2
book sprint implements its prepared numeric operating-time slice; v0.3 owns
completion for the declared book reconstruction scope. Future method families
inherit this boundary without requiring one universal input shape. OCEL is a
future interchange format, not a requirement for callers of ordinary analyses.
TR-047 assigns object-preserving OCEL ingestion and explicit analytical projection
contracts to v0.4 infrastructure; v0.5 completes practitioner workflows. Supported
OCEL version/profile and serializations must be selected before implementation.

## v0.2.1 integration follow-up

The accepted [FLO-backed White Belt workflow](plans/v021-flo-white-belt.md) is
Planned for v0.2.1. Ingest the actual book `.flo` through FLO's public producer
API and the existing projection bridge, explicitly map observations to stable
step IDs, derive baseline value classes from the model, and reuse observed
reconstruction/PCE calculations. Preserve the CSV-only route. This increment
extends the existing UR-003/UR-014/UR-046/UR-047 and
TR-003/TR-013/TR-040/TR-043/TR-044/TR-045/TR-046 contracts; their current statuses
do not imply this additional integration is implemented. v0.2.0 retains its
completed local acceptance scope and candidate version.

## White Belt book delivery slices

The [book sprint plan](plans/white-belt-book-preview.md) sequences delivery of the
`fromTheBook.md` criteria preserved in the requirement registers. The original sequence assigned assessment and the prepared-summary preview to
v0.2, with separate reconstruction owned by v0.3. Assessment, preview, numeric
ingestion and the declared activity-to-order route are now implemented. The
v0.3 reconstruction slice was delivered early; ownership remains unchanged.
The [v0.2 audit](assessments/v02-release-readiness.md) identifies the current
acceptance blockers before an official release and book dependency update.

The adopted book acceptance source is
[`washnfold-friday91` version 1.0.0](../tests/fixtures/reference/washnfold-friday91/conventions.json),
pinned from the October 22 split staging/notification case on October 23. Its
PCE gate is 13.7%, total VA 3535.3 min, and WNF-003 VA 82.7 min. Changes require
a reviewed fixture version and synchronized requirement/gate updates.

| Release | Book acceptance slice |
| --- | --- |
| v0.2 | Prepared-summary bindings and numeric operating clock (TR-039), eligible promise evaluation (UR-048/TR-041), cohort PCE (UR-049/TR-042), and the summary/nearest-rank portion of UR-004/TR-006. Deliver the rendered four-measure cell and prepared-input portions of UR-046, TR-043, TR-044, and TR-045. |
| v0.3 | Complete UR-046/UR-047 and TR-040/TR-043/TR-044/TR-045 through separately reproducible activity-to-order reconstruction, parallel-load and correction evidence, incomplete-case handling, and the WNF-003 hand check. |

Cross-release requirements keep their full acceptance criteria. They remain
Planned until implementation evidence exists and Partial while only one route
passes; delivering the prepared preview does not satisfy the full book contract.
The v0.2 book gate covers its stated slice. The v0.3 reconstruction gate now has
passing implementation evidence; official book release integration remains open.

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

### 2026-10-24 reconstruction delivery

The declared White Belt activity-to-order slice is implemented and verified against
all 39 independent prepared summaries, with raw activity/load/pass evidence,
parallel envelopes, classification, complete-path validation and correction counts.
TR-040/TR-043/TR-044/TR-046 and UR-047 are satisfied for this slice. The standalone
full route is tested from installed wheels. UR-046/TR-045 remain Partial for
official release and book publication integration. See
[order reconstruction](order-reconstruction.md).

### 2026-10-24 acceptance corrections

The v0.2 candidate now consistently identifies as 0.2.0. The earlier timing,
backend, result/provenance, guidance and dependency acceptance gaps are closed
against current implemented APIs and numerical claims; future method families
remain outside those claims. Release automation now enforces local acceptance and
performs clean official-index verification after publication. TR-038 remains
Partial until that target version is actually published and verified; this is a
postpublication gate, not an omitted prerelease check. No tag/publication or book
lockfile change was made. The [source-fingerprinted assessment](assessments/v02-release-readiness.json)
distinguishes prepublication readiness from completed publication.
