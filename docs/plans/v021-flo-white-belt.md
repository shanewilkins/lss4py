# v0.2.1: FLO-backed White Belt measurement workflow

- Accepted scope: 2026-10-24.
- Status: Planned; implementation has not started.
- Release target: v0.2.1, following the v0.2.0 candidate.
- Existing requirement coverage: UR-003, UR-014, UR-046, UR-047;
  TR-003, TR-013, TR-040, TR-043, TR-044, TR-045, TR-046.
- This is an additional integration acceptance slice. Existing Satisfied statuses
  describe their verified current contracts and do not claim this workflow exists.

Demonstrate the book's actual process model and observed activity data working
through FLO and lss4py together. Keep the CSV-only route independently usable.
Do not change v0.2.0 package metadata or fold this integration into its candidate.

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
