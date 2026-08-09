# Roadmap to LSS4PY 1.0

LSS4PY's MVP is a practitioner-complete **Yellow Belt toolkit at v0.3**.
The path to 1.0 adds Green Belt depth at v0.5, Black Belt depth at v0.7, then freezes feature scope so v0.9 can focus entirely on polish.
Belt labels describe the analyses the package supports.
They are not certification claims.

| Release | Product gate | Scope |
| --- | --- | --- |
| **v0.1** | Baseline honesty and control | Establish the governed documentation set, compatibility matrix, explicit stable-versus-experimental boundary, locked quality gates, and the initial stable Yellow Belt slice for current metrics, yields, and process-model-aware event-log calculations. |
| **v0.2** | Contract foundation | Adopt backend-neutral input and result contracts, add reusable validation and normalization, define CTQ/specification and provenance models, introduce analysis-guidance and parity-fixture scaffolding, and preserve the working v0.1 slice while those contracts migrate. |
| **v0.3** | **MVP: Yellow Belt complete** | Support an end-to-end basic DMAIC project: define CTQs and process maps; validate data; calculate time, efficiency, yield, defects, DPMO, descriptive and tail statistics; create Pareto and cause-and-effect analyses; estimate a mean; assess basic stability and capability with run/I-MR charts and Cp/Cpk/Z; quantify quality loss; establish an initial baseline; create a basic control plan; and export reproducible results and plots. Include governed worked examples and the applicable R `SixSigma` parity cases. |
| **v0.4–v0.5** | **Green Belt complete** | Add Gage R&R and practical MSA, broader variable and attribute control charts, full capability studies including governed non-normal methods, hypothesis tests and effect estimates, before/after comparisons, correlation and regression, foundational DOE, process bottleneck/variant analysis, and stronger control-plan workflows. |
| **v0.6–v0.7** | **Black Belt complete** | Add advanced MSA, regression and designed experiments, profile monitoring, process conformance and drift analysis, queueing and discrete-event simulation, robust optimization, and reproducible redesign scenarios. Complete the retained analytical surface of R `SixSigma`, including documented intentional differences. |
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

### Technical requirements

- **v0.1:** TR-001, TR-003, TR-004, TR-005, TR-008, TR-010, TR-011, TR-012, TR-018.
- **v0.2:** TR-002, TR-007, TR-009, TR-014, TR-015, TR-016, TR-017, TR-019, TR-020, TR-021, TR-033, TR-037.
- **v0.3:** TR-006, TR-013, TR-022, TR-023, TR-024, TR-026, TR-028, TR-030, TR-032, TR-035, TR-036.

## Release gates

A belt milestone is complete only when its workflows:

- cover the relevant user and technical requirements in the governed CSVs;
- return typed, backend-neutral results with assumptions, warnings, and provenance;
- have pandas and Polars contract parity where tabular input is involved;
- include positive, invalid-input, and numerical-reference tests; and
- are demonstrated by at least one reproducible, end-to-end project example.

The major post-MVP expansion path is:

- **v0.5:** UR-008–010, UR-013, UR-024, UR-035–041, and UR-044.
- **v0.7:** UR-006, UR-009, UR-011, UR-013, UR-028, UR-031–032, UR-035, and UR-039–043.

Some requirements span belt levels and therefore recur as their methods deepen.
UR-034, the paper-helicopter training asset, is not required for the analytical 1.0 contract and remains deferred ecosystem or curriculum scope.
