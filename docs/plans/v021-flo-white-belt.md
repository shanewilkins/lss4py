# v0.2.1: FLO-backed White Belt measurement workflow

- Accepted scope: 2026-10-24.
- Status: In progress; S1 and S2 completed 2026-10-26.
- Release target: v0.2.1, following the v0.2.0 candidate.
- Existing requirement coverage: UR-003, UR-014, UR-046, UR-047;
  TR-003, TR-013, TR-040, TR-043, TR-044, TR-045, TR-046.
- This is an additional integration acceptance slice. Existing Satisfied statuses
  describe their verified current contracts and do not claim this workflow exists.

Demonstrate the book's actual process model and observed activity data working
through FLO and lss4py together. Keep the CSV-only route independently usable.
Do not change v0.2.0 package metadata or fold this integration into its candidate.

## Sprint draft: 2026-10-26

**Goal:** Run the book's actual FLO model and observed CSV through an installed
package to reproduce the governed baseline, with inspectable model-derived
classifications, explicit measurement conventions and saved audit evidence.

This draft combines the accepted FLO workflow, Pydantic pilot and planned Pint
unit support with targeted test hardening. Sprint dates, capacity and task owners are not assigned yet.
S1 and S2 are complete; S2a and subsequent integration implementation remain planned.
See the [S1 assessment](../assessments/v021-book-model.md) and its governed fixture.
The [S2 assessment](../assessments/v021-pydantic-pilot.md) records strict schemas,
unchanged snapshots, direct dependency placement and the measured code tradeoff.

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
| S2a: Add Pint for explicit unit handling | Define a bounded unit contract, verify Python 3.14/dependency compatibility, add Pint to the appropriate dependency group and lockfile, and implement explicit duration-unit validation/conversion at a declared boundary. | Seconds/minutes/hours conversions preserve physical quantities; incompatible dimensions and unknown units fail with governed errors; existing numeric + unit APIs, serialized payloads and baseline results remain compatible. Test registry isolation, backend parity, installed dependencies and conversion provenance. | S1 unit inventory; dependency and registry decisions below |
| S3: Derive declared measurement policy | Translate projected model classifications and explicit analyst conventions into the existing reconstruction policy. Select an orchestration location that satisfies layer rules. | Missing/conflicting classifications and ambiguous mappings fail clearly; display-name changes preserve identity; model classification changes affect policy/results or fail the pinned profile. | S1; S2 validates the final integration path |
| S4: Demonstrate and preserve the full route | Add an installed-package model + CSV example using existing reconstruction/measurement APIs, FLO rendering and saved audit evidence. | All 39 order expectations and the WNF-003 hand check pass; source hashes, model/producer revisions, mapping, classifications and remaining conventions survive export/restoration. Modeled durations do not alter observed metrics. | S2, S2a, S3 |
| S5: Harden coverage of supported behavior | Add CLI doctor/debug tests, isolated structured-logging and telemetry tests, integration evidence rejection tests, and reporting success/error-path tests. Prioritize adapter failures relevant to the new route. | Tests assert observable behavior and governed errors, avoid global telemetry/logging leakage, and run in the normal CI suite. Full-package coverage stays at least 90% without exclusions or a reduced threshold. | Can start after S1; final integration cases depend on S4 |
| S6: Close acceptance and document the pilot | Run quality and installed-package gates, document the runnable workflow and compatibility decisions, and record a recommendation on further Pydantic adoption. | Gate results identify the tested revision; requirements evidence reflects only demonstrated behavior; release notes describe the delivered scope and dependency changes. | S2–S5 |

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
4. Choose the public policy-derivation surface and orchestration location.
   `lss4py.integration` currently depends only on domain contracts; it must not
   start importing adapters, kernels or workflows to run the demonstration.
5. Decide whether Pint belongs in core or an optional extra based on the actual
   unit API and import path. Document one registry ownership policy without
   changing a caller's application registry. Keep numerical kernels operating on
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
