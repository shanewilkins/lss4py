# FLO 0.5 alignment review

Reviewed and implemented 2026-10-30. Current capture defaults to published
FLO 0.5.0, with 0.4.2/0.4.3 restoration retained. The initial review below records
the pre-migration findings; the implementation outcome is recorded at the end.

## Initial review: sources and verification scope

- FLO checkout: `2264bcfb3a51e1cfa61fd8fe3bafd8550022c74e`, package 0.5.0.
  Normative sources: [migration guide](https://github.com/shanewilkins/FLO/blob/2264bcfb3a51e1cfa61fd8fe3bafd8550022c74e/docs/howto/migrate_to_0_5.md),
  [book-aligned contract](https://github.com/shanewilkins/FLO/blob/2264bcfb3a51e1cfa61fd8fe3bafd8550022c74e/docs/specs/book_aligned_contract.md),
  and `docs/specs/core_language.md` / `static_analysis.md` in that checkout.
- Actual book checkout: clean at
  `cefd20a8acb68636798666383510744cc351684c`; inspected
  [book/diagrams/washnfold.flo](https://github.com/shanewilkins/modern-process-improvement/blob/cefd20a8acb68636798666383510744cc351684c/book/diagrams/washnfold.flo).
- Producer probes used FLO's existing development environment and public
  `validate` / `export`, followed by `flo.render.render_artifact` for value-stream
  rendering. This is source-checkout verification, **not installed-wheel release
  acceptance**. Public package availability was not established.
- FLO has uncommitted changes to its changelog, timing analysis and timing tests.
  The timing change makes omitted/null `analysis_input` intentionally unselected
  without an invalid-duration warning, while retaining incomplete coverage.
  Probe results include that working-tree fix; they do not certify the exact
  committed candidate. Neither peer repository was modified by this review.

## Contract changes and LSS4PY impact

| FLO 0.5 meaning | Current LSS4PY assumption | Required alignment |
| --- | --- | --- |
| Package 0.5.0 is breaking; source `spec_version` remains `0.1`. | Integration extra/default pin is 0.4.3; envelope allows 0.4.2/0.4.3 only. | Dispatch validation and interpretation by explicit producer version. Preserve old saved projections and fingerprints. |
| `value_class` is first-class on work nodes. Omission and explicit `unknown` are distinct. | Policy reads `metadata.value_class` and attributes evidence to that path. | Read the version-appropriate field and record its exact provenance. Continue refusing to derive numeric classifications from missing/unknown values. |
| `cycle_time`, `wait_time`, `changeover_time` and process `lead_time` are supplied profiles. | Legacy fixtures keep scalar timings under metadata. | Preserve complete profiles, supporting results, population and provenance. Do not synthesize basis, selectors or counts. |
| `primary` selects display; optional `analysis_input` selects modeling. Missing/null analytical selection is not zero or a primary fallback. | No profile-aware bridge validation; existing measured arithmetic deliberately ignores model durations. | Keep observed reconstruction independent of modeled profiles. Any future duration consumer must honor the analytical selector explicitly. |
| `rework` and `handoff` are objects. `{}` asserts the relation; omission denotes none. | Schema requires booleans; `_project_edge` tests rework truthiness. | Validate structured relations and use presence (`is not None`) for 0.5; retain full evidence, including zero frequency. |
| Queue/wait `{ref: step_id.wait_time}` projects a work waiting profile directly, with path-local deduplication. | Legacy examples use copied durations and measurement identities. | Preserve references and full IDs, splitting at the last dot if consumed. Do not copy/add reference durations or infer shared populations from similar values. |
| Semantic metadata, workers, edge_type and retired aliases are rejected. `extensions` contains opaque annotations. | Frozen source and export follow the old shapes. | Replace the active source/export fixture with the actual migrated book revision; retain old fixtures for restoration tests. Keep LSS4PY's internal `metadata["flo"]` snapshot wrapper: that wrapper is not authored FLO semantic metadata. |
| Collections belong under `process`; work uses `performed_by`, `uses`, `consumes`, `produces`, `location`. | Producer fields are retained as extensible JSON. | Preserve canonical references/context; explicitly validate any fields the bridge interprets. Do not introduce FLO imports into the core or bridge. |
| Warning-only operations remain successful; diagnostics have normalized reports. | Example checks `.ok`, but successful-operation diagnostics are not saved in its evidence bundle. | Keep checking `.ok`; preserve warnings/report provenance instead of demanding an empty diagnostics list. |

Machine `cycle_time` means processing (P/T), and `changeover_time` means setup
(S/T). Neither is completion cadence C/T or a product transition C/O. Supplied
process lead time and derived modeled lead time remain different facts. Mixed
load/order populations cannot establish an empirical end-to-end duration by
adding displayed means. Static analysis still supplies no parallel critical-path
or rework-iteration policy.

This migration does not require broadening the bridge's documented topology
subset to all FLO node kinds or adopting FLO's internal Pydantic/NetworkX types.

## Executed compatibility probes

1. Existing frozen book source fails FLO 0.5 validation/export with `E0209` at
   `transitions[11].rework` (`true` must become an object). Fixing that first
   reported field alone would leave other retired source fields.
2. Current actual book source validates, exports and renders as a value-stream
   SVG: 14 nodes and 14 edges. Warnings are nonfatal; modeled lead time is null.
3. Its genuine export fails `ProcessProjection.from_flo_export` for producer
   0.5.0: unsupported version and object-valued rework fields. Declaring it 0.4.3
   still fails boolean validation; relabeling cannot adapt the contract.
4. Directly probing the existing edge projector with the genuine return edge
   `rework: {}` yields `kind="sequence"`. The current public schema blocks this
   today; widening it without changing the projector would introduce silent
   semantic loss.
5. Directly probing policy classification with the genuine `wash` node fails
   because it looks for retired `metadata.value_class`.

Existing consumer baseline verification passed: **123 tests** across
`tests/test_integration_contracts.py`, `tests/test_book_model.py`, and
`tests/test_derived_policy.py` (22.70 seconds). These validate the current legacy
contract, not 0.5 support. `git diff --check` also passed.

## Book fixture choice matters

The actual book retains `stage` / `notify`, notification **VA**, the independent
501.7-minute order-release queue, and deliberately display-only timing profiles
with **no `analysis_input`**. The 500.9-minute load-level Wash wait is not inserted
as an additional modeled order wait. Its comments explicitly refuse an
end-to-end modeled elapsed-time claim.

FLO's separate `examples/reference/book_washnfold.flo` also validates/exports/
renders, but uses `stage_collection` / `send_notification`, notification **RNVA**,
analytical selectors, and both order-release and load-wait profiles. It is useful
producer coverage, not a byte-compatible or semantically interchangeable
replacement for the book's model. Copying it would require mapping changes and
would change measured VA/PCE under the current reconstruction conventions.

The actual book's retained IDs and classifications suggest that its source
migration should preserve current observed arithmetic. This is an expectation,
not completed 0.5 consumer acceptance: recheck the independent 39-order result,
3535.3 VA minutes, 25840.5 lead minutes, five corrections, WNF-003's 82.7 VA
minutes, and cohort PCE after upgrading the consumer. Never rewrite these
baselines merely to match a different producer demonstration fixture.

## Implementation sequence and acceptance

1. Add producer-specific portable validation for 0.5 relations/classification and
   supported consumed profile fields. Keep legacy restoration semantics, exact
   JSON retention and digests unchanged; reject mismatched producer shapes.
2. Update relation projection and policy derivation together, including
   attribution `source_field: value_class` for 0.5. Keep domain reconstruction
   rules and observed-duration kernels independent of modeled timings.
3. Freeze the actual book source revision, genuine 0.5 export, source/license
   provenance, hashes and projection digest in a new governed fixture revision.
   Preserve old export/evidence restoration coverage separately.
4. Update the integration pin/lock, default producer, example version checks,
   e2e assertions and current documentation together. Audit calls that rely on
   the default producer version; old snapshots must declare their old version.
5. Run offline bridge/policy coverage and the actual installed-wheel ecosystem
   journey: validate/export/render native sources, reconstruct observed orders,
   persist/reload/verify evidence, and render saved observations independently.

Required edge cases: empty handoff/rework objects; absent relations; zero rework
frequency; different primary/analysis selectors; omitted/null `analysis_input`;
measured zero; unknown/unclassified work; population/provenance retention;
Unicode/dotted waiting IDs; unresolved/chained references; legacy restoration;
and preservation of nonfatal producer diagnostics. Reference/selector validity
requires producer semantic validation, not JSON Schema alone. The bridge should
not imply full FLO validation merely because it accepts a portable snapshot.

Initial assessment probes wrote temporary exports, reports and SVGs under
`/tmp/lss4py-flo05-review/`. Those read-only probes preceded the implementation.

## Implemented alignment

- `integration` pins published `flo-lang==0.5.0`; the lock and default capture
  version agree. Version-specific portable models keep the legacy envelope and
  exact JSON/fingerprints unchanged, while validating 0.5 profiles, relations,
  classifications and direct queue references. The topology subset is unchanged.
- Empty rework objects retain rework meaning. Policy derivation selects the
  version-appropriate classification field and records its exact source path.
  Profile results/context remain detached producer evidence, with no display-to-
  analysis fallback or use of model durations in observed reconstruction.
- Actual book fixture 2.0.0 uses clean book revision
  `cefd20a8acb68636798666383510744cc351684c`, byte-copied source/license and the
  published 0.5.0 export. Its projection fingerprint is
  `0d8f6567f23fe94176d14aecd26c92e16d13190c535abfcf7c696f82005bff50`.
  Prior source/export/manifest bytes are retained under `legacy-0.4.3/`.
- The book's notification VA classification remains as supplied, pending its
  team's semantic decision. Numeric data and independent expected results were
  not changed. Published producer warnings are saved in the example bundle's
  `producer_report`; the manifest retains the corresponding diagnostic snapshot.
- Regression tests cover selectors, measured zero, zero relation frequency,
  empty relations, namespaced statistics, portable evidence, Unicode/dotted IDs,
  invalid/chained references, classification provenance and legacy fingerprints.
  Installed producer tests exercise genuine 0.5 source/export/consumer boundaries.


## Final acceptance — 2026-10-31

- Full source suite: **2,073 passed, 5 expected failures**, **95.83% coverage**.
- Isolated exact-wheel matrix: **28 base, 38 pandas, 40 storage, 54 ecosystem**
  tests passed (**160 installed-wheel passes**). The ecosystem stage used
  published FLO 0.5.0 and exercised the actual book example, evidence restoration,
  source verification, structured relations and selector/reference cases.
- Observed baselines remain 3535.3 VA minutes, 25840.5 lead minutes, 13.7% cohort
  PCE, 39 orders and five corrections; WNF-003 retains 82.7 VA minutes.
- Ruff lint/format, ty, Vulture, all eight import contracts, lock consistency and
  `git diff --check` passed. Legacy projection fingerprints remain unchanged.
- Retained artifacts: `/tmp/lss4py-flo05-final-wheel/`, source test log
  `/tmp/lss4py-flo05-tests.log`, wheel log `/tmp/lss4py-flo05-wheel.log` and coverage
  `/tmp/lss4py-flo05-coverage.json`. Package version remains 0.2.0; no publication
  or peer repository modification was performed.
