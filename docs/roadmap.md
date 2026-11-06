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
| **Yellow** | MVP Complete | v0.3 | Explicit process measures, descriptive/visual evidence, null-model exercises, introductory comparisons and supplied-chart interpretation | Apply straightforward tools to measure and identify improvement opportunities |
| **Green** | Professional Depth | v0.5 | MSA/Gage R&R, control charts, capability studies, hypothesis tests, DOE, bottleneck analysis | Design and execute controlled comparisons with statistical confidence |
| **Black** | Master Depth | v0.7 | Advanced MSA, regression, full DOE portfolio, simulation, robust optimization | Lead organization-wide transformation and predictive modeling |
| **Polish** | Integration & Polish | v0.8–v0.9 | Naming, documentation, diagnostics, performance, accessibility | Stabilize the practitioner contract |
| **Stable** | Semantic Versioning | v1.0 | Supported API and compatibility guarantees | Publish stable contract; practitioners can update confidently |

The roadmap owns release scope. Proposed ADRs describe intent and do not
add acceptance obligations; accepted ADRs govern their recorded decisions.

LSS4PY's MVP is a practitioner-complete **Yellow Belt toolkit at v0.3** (odd: complete).
Green Belt infrastructure is built at v0.4 (even: core methods), validated and completed at v0.5 (odd: workflows & ergonomics).
Black Belt infrastructure is built at v0.6 (even: core methods), validated and completed at v0.7 (odd: workflows & ergonomics).
Versions v0.8–v0.9 close gaps and polish the API before v1.0 declares semantic versioning.

Belt labels describe the analyses the package supports. They are not certification claims.

| Release | Product gate | Scope |
| --- | --- | --- |
| **v0.1** | Baseline honesty and control | Establish the governed documentation set, compatibility matrix, explicit stable-versus-experimental boundary, locked quality gates, and the initial stable Yellow Belt slice for current metrics, yields, and process-model-aware event-log calculations. |
| **v0.2** | Contract foundation | Adopt backend-neutral input and result contracts, add reusable validation and normalization, define CTQ/specification and provenance models, introduce analysis-guidance and parity-fixture scaffolding, and preserve the working v0.1 slice while those contracts migrate. |
| **v0.3** | **MVP: Yellow Belt analytical workflows** | Support Polars evidence preparation, explicit cohorts and elapsed-time/deadline/FPY/route-specific RTY; descriptive/stratified tables and histogram/Pareto/scatter/time-order inputs or helpers; Lady Tasting Tea and repeatable sampling/randomization; confidence intervals and supplied one-sample/paired/independent-sample t workflows using established implementations; instructor-reviewed charts with explicit baselines, subgrouping, limits and signal rules. Learners interpret supplied charts; independent selection stays later. Keep inputs, intermediate tables, effects, units, exclusions and limitations inspectable. Taguchi is outside the milestone; the separate model authoring/evidence-display/diagram-comparison workflow belongs to FLO. |
| **v0.4** | Green Belt infrastructure | Build core Green Belt analytical machinery: implement Gage R&R and MSA kernels; add hypothesis testing infrastructure (t-tests, ANOVA, correlation); implement control chart algorithms (I-MR, X-bar/R, attribute); add capability study kernels with Box-Cox transformation; implement foundational DOE kernels; and build process bottleneck/variant analysis infrastructure. Numerical parity validation against R `SixSigma`. |
| **v0.5** | **Green Belt complete** | Validate Green Belt contract: create end-to-end DMAIC workflows with MSA validation, hypothesis testing with effect sizes and confidence intervals, control chart designs with rational subgrouping, capability studies including non-normal methods, before/after comparisons, foundational DOE with guidance, process bottleneck analysis, and stronger control-plan workflows. Include Green Belt governance tags, parameterized backend-parity tests, and reproducible worked examples. |
| **v0.6** | Black Belt infrastructure | Build core Black Belt analytical machinery: implement advanced MSA (component of variance, nested designs); add advanced regression kernels (multiple, logistic, GLM, smoothing); implement full DOE portfolio infrastructure (response surface methods, optimization algorithms); build discrete-event simulation engine; implement profile monitoring and conformance/drift detection; add robust optimization solvers; and validate against R `SixSigma` and NIST reference cases. |
| **v0.7** | **Black Belt complete** | Validate Black Belt contract: create end-to-end transformation workflows with advanced MSA screening, predictive modeling with interpretation, response surface design and analysis, multi-objective optimization scenarios, discrete-event simulation with redesign capabilities, profile monitoring with control limits, and conformance/drift detection. Include Black Belt governance tags, parameterized backend-parity tests, complete R `SixSigma` parity study, and reproducible transformation scenario examples. |
| **v0.8** | Integration and gap closure | Close cross-workflow, backend-parity, numerical-validation, performance, and compatibility gaps discovered while assembling complete projects. Add no new belt-level capability category. |
| **v0.9** | **Polish only; feature freeze** | Stabilize naming and signatures, finish documentation and examples, improve errors and diagnostics, verify accessibility and plotting semantics, harden serialization and migrations, benchmark performance, and complete packaging and upgrade guidance. |
| **v1.0** | Stable practitioner contract | Publish the supported API and compatibility guarantees under semantic versioning. Every claimed belt workflow is documented, tested, and reproducible. Callers are not required to supply pandas or Polars inputs, while core ingestion may continue to use Polars internally. |

The [current status](STATUS.md) separates published and unreleased behavior.
The [0.3 checklist](plans/v03-yellow-belt.md) is the implementation queue and
records acceptance for its remaining slices.

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
- **v0.3:** UR-004, UR-007, UR-012, UR-014, UR-021, UR-022, UR-023, UR-025, UR-029, UR-030, UR-041, UR-046, UR-047.
- **v0.4:** UR-008, UR-009, UR-010, UR-013, UR-035, UR-036, UR-037.
- **v0.5:** UR-010, UR-019, UR-020, UR-024, UR-030, UR-038, UR-039, UR-040, UR-041, UR-044.
- **v0.6:** UR-011, UR-028, UR-031, UR-032, UR-039, UR-043.
- **v0.7:** UR-006, UR-009, UR-011, UR-013, UR-028, UR-031, UR-032, UR-035, UR-039, UR-040, UR-042, UR-043.

### Technical requirements

- **v0.1:** TR-001, TR-003, TR-004, TR-005, TR-008, TR-011.
- **v0.2:** TR-002, TR-007, TR-009, TR-010, TR-014, TR-015, TR-016, TR-017, TR-018, TR-019, TR-020, TR-021, TR-033, TR-037, TR-038, TR-039, TR-041, TR-042.
- **v0.3:** TR-006, TR-012, TR-013, TR-022, TR-023, TR-028, TR-030, TR-032, TR-035, TR-040, TR-043, TR-044, TR-045, TR-046.
- **v0.4:** TR-024, TR-025, TR-027, TR-028, TR-029, TR-030, TR-031, TR-034, TR-047.
- **v0.5:** TR-022, TR-028, TR-032, TR-035, TR-036.
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

### Yellow Belt scope revision — 2026-11-06

The maintainer removed Taguchi loss from Yellow Belt; UR-027/TR-026 move to the
later horizon with no committed release. Preserve the existing unreleased WIP
and its regression evidence. Its completion is not a 0.3 gate.

The remaining 0.3 path is bounded by the maintainer's five **analytical**
workflows: explicit process measures/cohorts; descriptive/stratified visualization;
null-model enumeration/sampling; introductory intervals/t comparisons with
practical importance; and instructor-reviewed chart production for learner
interpretation. The [workflow plan](plans/v03-yellow-belt.md) records concrete
acceptance and the ordered exercise-to-API/library/example/gap inventory.

The separate model describe/validate/render/revise, model-evidence display and
current/proposed diagram comparison table belongs to **FLO**. Reuse existing
integration contracts and preserve analytical timing/evidence semantics; do not
turn that table into LSS4PY authoring/rendering requirements.

0.3 owns bounded supplied-comparison slices of UR-008/UR-038/TR-028 and
instructor-chart slices of UR-010/TR-024, while their full-family ownership
remains v0.4/v0.5. Independent chart selection, general inferential/DOE portfolios
and broader SPC engines are not Yellow Belt prerequisites. Keep existing MR and
capability work intact.

Full R process-map/fishbone representation (UR-019/UR-020), composed capability
presentation (UR-024), multimodality/violin work (UR-030/TR-022) and persistent
control plans (UR-044/TR-036) complete at v0.5. UR-030/TR-022 and UR-041/TR-035
retain their 0.3 taught descriptive/Pareto slices with broader criteria carried
forward explicitly. No full-family Must acceptance is claimed in 0.3. Proposed
ADR-0015's older feature list adds no release gate.

## Milestone and release gates

A method is ready for its declared slice when:

- relevant user and technical acceptance criteria are met with implementation evidence;
- typed results preserve units, assumptions, warnings and provenance;
- governed eager backends agree, with required PyArrow coverage;
- positive, invalid-input, boundary and independent numerical checks pass; and
- at least one reproducible worked example demonstrates the supported contract.

A belt milestone additionally needs its complete practitioner workflow, appropriate
suitability guidance, exported evidence/plots and reconciled traceability. Keep
cross-release families Partial until their full registered contract is satisfied;
record acceptance of individual release slices separately. Do not waive an unmet
Must requirement or silently move ownership. Explicit Should deferrals must state
their effect on the milestone claim.

Before publication, run configured quality/security gates, wheel/source builds,
metadata/identity checks and isolated exact-wheel journeys. Prepare version,
release notes and migration guidance. Publication is complete only after the
release process succeeds and a clean installation from the official index is
verified. A prior dated audit is evidence of its own revision, not certification
of the next release.

## Delivery records

Completed implementation detail belongs in the analytical guides, release notes
and dated assessments rather than a second roadmap work queue:

- [0.2.2 release](releases/v0.2.2.md): published canonical analytical boundary.
- [FLO integration acceptance](assessments/v021-sprint-acceptance.md) and
  [FLO 0.5 alignment](assessments/flo-05-alignment.md): scoped book integration.
- [Book reconstruction](order-reconstruction.md): delivered 0.3-owned slice;
  book deployment remains a separate acceptance item.
- [2026-11-05 review](assessments/code-review-2026-11-05.md): chart/study fixes and
  completion of the five review follow-ups.
