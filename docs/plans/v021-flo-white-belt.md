# v0.2.1: FLO-backed White Belt measurement workflow

- Accepted scope: 2026-10-24.
- Status: Accepted locally 2026-10-27; S1–S6 complete. Release/publication steps remain separate.
- Release target: v0.2.1, following the v0.2.0 candidate.
- Existing requirement coverage: UR-003, UR-014, UR-046, UR-047;
  TR-003, TR-013, TR-040, TR-043, TR-044, TR-045, TR-046.
- This additional integration is verified by the S6 acceptance assessment.
  Requirement statuses retain their declared scope; publication remains separate.

Demonstrate the book's actual process model and observed activity data working
through FLO and lss4py together. Keep the CSV-only route independently usable.
Do not change v0.2.0 package metadata or fold this integration into its candidate.

## Contract alignment follow-up: 2026-10-30

Current producer capture targets published FLO 0.5.0; legacy 0.4.2/0.4.3
projection restoration remains supported. The actual book model is fixture
version 2.0.0, retaining its current classifications and display-only profiles.
See the [alignment assessment](../assessments/flo-05-alignment.md) for the contract
changes and updated validation. The dated S1–S6 records below remain historical.

## Sprint draft: 2026-10-26

**Goal:** Run the book's actual FLO model and observed CSV through an installed
package to reproduce the governed baseline, with inspectable model-derived
classifications, explicit measurement conventions and saved audit evidence.

This draft combines the accepted FLO workflow, Pydantic pilot and planned Pint
unit support with targeted test hardening. Sprint dates, capacity and task owners are not assigned yet.
S1–S6 are complete. The [final acceptance assessment](../assessments/v021-sprint-acceptance.md)
records the tested working-tree/wheel identities, combined gates and release handoff.
See the [S1 assessment](../assessments/v021-book-model.md) and its governed fixture.
The [S2 assessment](../assessments/v021-pydantic-pilot.md) records strict schemas,
unchanged snapshots, direct dependency placement and the measured code tradeoff.
The [duration unit contract](../duration-units.md) and [ADR-0027](../adr/0027-explicit-duration-conversion-and-private-pint-registry.md)
record the separate conversion boundary and private Pint registry.

### Starting evidence

- Full-package statement coverage is now enabled in `pyproject.toml`, including
  adapters, CLI, observability, reporting, legacy event-log code and unfinished
  workflows. The local CI-command run recorded in this chat passed 1,750 tests
  with five expected failures and **93.19% coverage** against the unchanged 90%
  gate. Branch coverage is not enabled.
- The previously excluded CLI and observability modules measured 0%; integration
  evidence measured 87%, the FLO bridge 92%, and reporting visualization 83%.
  These identify test priorities, not evidence that the implemented calculations
  fail. Unimplemented workflow stubs remain visible in the denominator.
- Existing reconstruction and independent baseline fixtures are reusable. The
  producer was pinned to 0.4.2 at planning time. S1 now verifies published 0.4.3
  against the actual book model and retains restoration of 0.4.2 payloads.
- The dated v0.2.0 readiness assessment records publication and book dependency
  integration as pending. Verify their current state before release work; do not
  treat that historical assessment as proof of current publication status.

### Ordered backlog

| Item | Deliverable | Completion evidence | Dependency |
| --- | --- | --- | --- |
| S1: Freeze source and producer contract — Complete 2026-10-26 | Govern the actual `.flo`, public producer export, source revision/hashes, attribution and explicit activity-to-step mapping. Record supported and unsupported semantics. | Actual model passes released FLO 0.4.3 and the existing bridge: 14 nodes, 14 edges, all eight observed activities mapped, source/observation bytes pinned. Legacy 0.4.2 payload restoration is retained. See the [assessment](../assessments/v021-book-model.md). | None |
| S2: Pilot Pydantic at the JSON boundary — Complete 2026-10-26 | Strict private schemas replace structural checks; graph/mapping rules remain explicit. Pydantic is declared directly in core to preserve base-installation bridge access. | Source gates and all installed stages pass, alongside a 325-case differential probe. Original snapshots/fingerprints and extensible producer data are retained; public errors identify nested fields. See the [assessment](../assessments/v021-pydantic-pilot.md) for code-size and dependency costs. | S1 schema/profile decision |
| S2a: Add Pint for explicit unit handling — Complete 2026-10-27 | Direct core Pint dependency and separate `convert_duration_columns` preparation API. Private lazy registry; explicit seconds/minutes/hours aliases and unchanged clock declaration. | Source gates and all installed stages pass, including the unchanged 39-order book PCE after explicit conversion. Backend/identity preservation, governed errors, registry isolation and portable conversion evidence are verified. Days/calendars and implicit conversion remain outside the contract. See [duration units](../duration-units.md). | S1 unit inventory; registry/dependency decisions in ADR-0027 |
| S3: Derive declared measurement policy — Complete 2026-10-27 | Translate projected model classifications and explicit analyst conventions into the existing reconstruction policy. Select an orchestration location that satisfies layer rules. | `integration.derive_reconstruction_policy` returns the existing domain policy plus portable attribution. Missing/invalid classes, unmapped observed/analyst activities and correction conflicts fail clearly. All 39 orders match; model class changes affect VA/PCE; names and modeled durations do not. See [policy derivation](../order-reconstruction.md#derive-baseline-classes-from-flo). | S1; S2 validates the final integration path |
| S4: Demonstrate and preserve the full route — Complete 2026-10-27 | Add an installed-package model + CSV example using existing reconstruction/measurement APIs, FLO rendering and saved audit evidence. | Standalone `examples/white_belt/flo_measure.py` runs native FLO + CSV through installed packages. Every order field, WNF-003 and cohort readouts pass; audited bundle restoration retains model/producer versions, source snapshots, mapping/classes and analyst rules. FLO renders the modeled value stream. Changed pinned inputs fail before success artifacts. See the [workflow](../flo-book-workflow.md). | S2, S2a, S3 |
| S5: Harden coverage of supported behavior — Complete 2026-10-27 | Add CLI doctor/debug tests, isolated structured-logging and telemetry tests, integration evidence rejection tests, and reporting success/error-path tests. Prioritize adapter failures relevant to the new route. | Normal CI now verifies CLI help/doctor/debug, real JSON logging/filtering/context/exceptions, locally exported parent/child spans, rehashed malformed evidence, plot creation/labels/warnings/style/dependency failures, numeric schema identity and CSV parse/storage diagnostics. Logging configuration/context are restored; local telemetry providers flush and shut down without replacing the global provider. See S5 verification below. | Can start after S1; final integration cases depend on S4 |
| S6: Close acceptance and document the pilot — Complete 2026-10-27 | Run quality and installed-package gates, document the runnable workflow and compatibility decisions, and record a recommendation on further Pydantic adoption. | Final source gates pass (1,983 passed, five expected failures, 95.71% coverage); the exact-wheel matrix passes all 157 installed tests. Dependency audit, distribution metadata and workflow checks pass. The acceptance assessment records executable/wheel hashes, the bounded Pydantic recommendation and release limitations; draft v0.2.1 notes document dependency changes. | S2–S5 |

### S3 verification: 2026-10-27

The locked pre-push gates pass: 1,932 source tests passed, five expected
failures, 93.65% full-package statement coverage, all eight import boundaries,
Ruff, formatting, Vulture, lock consistency and ty. The new derivation module
has complete statement coverage. Regression tests compare every order/activity
table with the CSV-only baseline, preserve derivation evidence through result
JSON, and verify the notification classification changes VA/PCE without changing
lead time. Display-name and modeled-duration mutations leave measurements intact.

The isolated wheel matrix also passes all 153 tests: 28 base, 38 pandas,
40 storage and 47 ecosystem. Base installation verifies derivation from portable
FLO exports without requiring the FLO package. Reports are retained under
`artifacts/tests/` and `artifacts/ecosystem/tests/`.

### S4 verification: 2026-10-27

The isolated wheel matrix passes 157 tests: 28 base, 38 pandas, 40 storage
and 51 ecosystem. The actual model/CSV subprocess route restores all five typed
results and compares every order against the independent prepared summary. It
checks source fingerprints, model/producer identity, mapping/classes, analyst
rules, WNF-003 load evidence and the FLO SVG structure. Three changed-source
cases reject the pinned profile without success artifacts. The source gates
retain 1,932 passes, five expected failures and 93.65% full-package coverage.
Artifacts are retained under `artifacts/ecosystem/book/`. Requirement evidence
links were extended for the demonstrated route; publication-related statuses
remain unchanged.

### S5 verification: 2026-10-27

Added 51 normal-CI behavior and rejection cases in `tests/test_observability.py`,
`tests/test_reporting.py`, `tests/test_adapter_failures.py` and
`tests/test_integration_contracts.py`. The final source suite passes 1,983 tests
with five expected failures. Full-package statement coverage increased from
93.65% to **95.71%** (3,684 statements, 158 missing), with the unchanged 90% gate
and no exclusions. CLI, logging, telemetry, integration evidence, timing plotting
and the numeric CSV adapter each reach 100% statement coverage. This does not
claim branch coverage or completion of deferred features.

The locked pre-push checks pass; final adapter assertion changes also pass the
full required-Arrow coverage command, Ruff/formatting, Vulture and ty. All eight
import boundaries remain intact. JUnit and coverage XML are retained under
`artifacts/tests/`. JSON logging restores root handlers/level, structlog
configuration (including its configured state) and context variables. Real SDK
spans are exported and flushed through local providers that are shut down;
global tracer-provider installation is intercepted and the original provider is
unchanged. Plot tests close created figures and check that style and analytical
results are unchanged. Evidence mutations are rehashed to verify semantic
rejection rather than merely checksum rejection.

No production code, dependencies or installed E2E cases changed in S5. The S4
157-test installed matrix remains its recorded evidence; the final combined
installed-package run belongs to S6. Deferred workflow and Markdown-rendering
stubs remain visible in coverage and unimplemented.

### S6 verification: 2026-10-27

All combined acceptance gates pass against the recorded working tree and selected
wheel. See the [acceptance assessment](../assessments/v021-sprint-acceptance.md)
for exact identities, gate results, retained artifacts, Pydantic recommendation
and remaining release steps. The standalone implementation scope is accepted;
package metadata remains 0.2.0 and publication/sibling-book integration were not
performed. The [v0.2.1 release notes](../releases/v0.2.1.md) are a draft.

### Decisions to settle during S1/S2/S2a

1. Pin the actual book model revision and verify access and redistribution
   attribution. Keep the existing numerical fixture expectations unchanged unless
   a separately reviewed fixture revision is necessary.
2. Establish the Pydantic dependency location before changing imports. Core
   calculations must remain usable without FLO; preserve existing bridge import
   and installation contracts or explicitly document a required compatibility
   decision. Preserve the standalone standard-library bundle validator.
   FLO already depends on Pydantic and owns validation of its native documents.
   Keep using its public facade; do not import private source/render models or
   reproduce native-document checks. The LSS4PY pilot validates its portable
   exchange envelopes, mappings and analytical declarations, including saved or
   externally supplied JSON. If LSS4PY imports Pydantic directly, declare that
   dependency explicitly in the chosen scope rather than relying on FLO's
   transitive dependency, and use a compatible version range.
3. Separate producer fields that are intentionally extensible from closed
   envelopes. Match current accepted payload behavior rather than applying
   `extra="forbid"` indiscriminately. Preserve original producer data used in
   canonical snapshots and fingerprints when validating it.
4. Resolved by S3: `lss4py.integration.derive_reconstruction_policy` accepts
   `ReconstructionConventions` and observed vocabulary, returning the existing
   domain policy with detached classification evidence. It imports no kernels
   or data adapters. Full-route orchestration remains S4. Original constraint:
   `lss4py.integration` currently depends only on domain contracts; it must not
   start importing adapters, kernels or workflows to run the demonstration.
5. Resolved by ADR-0027: Pint is a core dependency for a separate preparation
   operation with a private lazy registry, without changing a caller's application
   registry. Keep numerical kernels operating on
   normalized magnitudes and explicit units; preserve portable JSON rather than
   storing registry-bound quantity objects in bundles.
6. Define accepted unit spellings and explicit conversion requests. Duration
   dimensions do not establish clock semantics: calendar elapsed time and numeric
   operating time remain distinct. An operating day requires a declared work
   calendar/conversion rule; do not silently interpret it as 24 operating hours.
   Counts, opportunities and percent/ratio meanings remain analytical contracts.
   Offset-temperature support and general custom-unit contexts are deferred.

### Sprint exit and scope control

The primary acceptance criteria below remain the numerical and behavioral gate.
In addition, run the locked source quality checks, the full-package coverage
command, and `tools/check_wheel.py --ecosystem --storage` for the final revision.
The source suite measures coverage; the isolated wheel suite independently
checks installation boundaries and does not contribute to that percentage.

The five expected v0.3 failures remain explicitly deferred. Do not implement
unfinished bottleneck/comparison/simulation/report rendering workflows merely
to improve coverage. Broad Pydantic conversion, specification migration and
branch-coverage gating are outside this sprint's committed scope.

If capacity is constrained, preserve S1–S4 (including S2a) and the tests required to demonstrate
them; additional unrelated adapter/reporting error cases are the first candidates
to defer. Record any deferred work explicitly. Publication/tagging and sibling
book lockfile changes remain separate release steps after acceptance, not
assumed outcomes of this planning draft.

## Inputs and responsibilities

Use the book's `book/diagrams/washnfold.flo` and the governed Friday 91 activity
CSV. Pin the selected model revision, original bytes/hash and redistribution
attribution alongside the existing licensed/checksummed observations. Check that
the model and CSV describe the adopted split staging/notification revision.

FLO parses and validates its native document and exports through its supported
public API. Reuse `lss4py.integration.ProcessProjection` and the released producer
profile already covered by the ecosystem bridge. Do not add a second FLO parser
or make FLO a mandatory numerical-core dependency. Check the actual book export
against bridge capabilities; report unsupported semantics rather than silently
flattening or discarding them.

An explicit mapping binds CSV activity identities to stable FLO step IDs. The
book labels already differ: CSV `Wash` maps to `wash`, whose display name is
`Wash loads`. Renaming display text must not change the calculation. Unmapped,
ambiguous or missing referenced activities fail with inspectable findings.

The process model supplies step identity, declared topology and baseline
VA/RNVA/NVA classes. Observations supply actual durations and rework occurrences.
The mapping/convention record supplies the numeric clock, endpoint bindings,
cohort and measurement boundary, plus the book's right-first-time override and
Wash/Dry load-envelope convention. These last rules are not fully expressed in
the current `.flo` diagram and must remain visible declarations.

Diagram `cycle_time`, `changeover_time`, waits and queue averages remain modeled
or displayed facts. They must never replace measured timestamps or be added into
the observed PCE calculation. The diagram explicitly notes overlapping release
and Wash waits, which must not be double-counted.

## Implementation sequence

1. Govern the actual book FLO fixture, producer export and explicit activity/step
   mapping; verify the existing bridge can represent its decisions/rework path.
2. Add a supported integration operation that derives baseline activity classes
   from projected FLO metadata and combines them with explicit measurement rules.
   Detect invalid/missing/conflicting classifications. Record which rules came
   from FLO and which were supplied by the analyst.
3. Pass that declared policy into existing numeric reconstruction and public
   measurement APIs. Reuse their arithmetic and preserve source/load/pass evidence.
4. Add a standalone installed-package example: FLO document + CSV -> validated
   export/projection -> bound observations -> reconstructed orders -> PCE and
   other baseline readouts -> saved evidence and process rendering.
5. Record both original source hashes, producer/model revisions, mapping,
   classification provenance and remaining conventions in the audit bundle.
   Update documentation and requirements evidence only for passing behavior.

## Acceptance

- Execute the real file-to-result route against an installed lss4py wheel and the
  supported released FLO package, without a sibling checkout or editable imports.
- Derive baseline classes from FLO rather than duplicating the activity class
  lists in Python. Prove a model classification change affects the derived policy
  and measured VA/PCE, or fails under an explicitly pinned acceptance profile.
- Ignore modeled duration changes when calculating observed measures. A display
  label rename preserves identity and results. Mapping/classification/model
  mismatches fail clearly; no fuzzy name matching or silent fallback occurs.
- Match the pinned independent baseline for all 39 orders and WNF-003: VA/lead
  totals 3535.3/25840.5 minutes, PCE 13.7%, mean lead 662.6 minutes, eligible P90
  676.2 minutes, six misses among 21 eligible orders, five corrections affecting
  five orders. Preserve WNF-003's two Wash loads, two Dry loads and 82.7 VA minutes.
- Retain the CSV-only workflow and its existing results. The numerical core works
  without FLO installed; only the explicit integration route requires its extra.
- Use FLO rendering for the declared model. Keep measured evidence clearly
  labeled; no unsupported measured overlay or renderer is required.
- Pass required backend, reference, quality and installed ecosystem checks.

## Boundaries

No general branch inference, lifecycle pairing, OCEL, diagram-duration PCE,
new plotting engine, automatic activity matching or automatic analytical method
selection is required. This does not expand the general v0.3 Yellow Belt MVP.
Official book publication integration follows the released package dependency
process; it remains distinct from the standalone reproducible demonstration.
