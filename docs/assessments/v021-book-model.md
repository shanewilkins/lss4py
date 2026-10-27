# v0.2.1 S1: actual book model and producer contract

Assessed 2026-10-26. **S1 is complete:** the actual book model validates and
exports through released FLO 0.4.3 and is representable by the existing
`ProcessProjection` bridge. No producer or bridge compatibility repair is needed
for this model. Pydantic, Pint, policy derivation and the full measurement route
remain subsequent sprint tasks.

The producer was advanced from 0.4.2 after checking published 0.4.3. The book's
JSON export is unchanged. Original synthetic 0.4.2 payloads remain accepted and
retain their version/fingerprint on restoration. That older synthetic source
needed a separate review-work/decision pair to satisfy 0.4.3's E1508 validation;
its original bytes are retained in `legacy-0.4.2/`, with observed expectations
unchanged. The bridge accepts both producer profiles and defaults new captures
to 0.4.3.

FLO already uses Pydantic; it owns native-document validation through its public
facade. S2 should validate LSS4PY's portable exchange and analytical contracts,
without depending on private FLO models or duplicating its native source rules.

## Pinned evidence

The governed [book-model fixture](../../tests/fixtures/ecosystem/book-model/README.md)
contains unmodified `.flo` and license bytes, the public producer export, an
explicit activity mapping and a
[manifest](../../tests/fixtures/ecosystem/book-model/manifest.json).

| Property | Verified value |
| --- | --- |
| Source | Shane M. Wilkins, *Modern Process Improvement with Python* |
| Model path | `book/diagrams/washnfold.flo` |
| Model last-change revision | `a10b7ecbc33908cffcafd4bbc3783b3447163406` |
| Inspected clean checkout | `afca5fe41237ead0be2bdfce4e08341d7deaea12` |
| Original model SHA-256 | `d3593510d5a8fc5bb80bbfa6b86f3185c446936b1d4bc168207e11a2273f2d49` |
| Model identity | `wash_n_fold`, version 2 |
| Producer | Published `flo-lang==0.4.3`, public `flo.validate()` and `flo.export()` |
| Producer diagnostics | None for validation or export |
| Export topology | 14 nodes, 14 edges, including one decision and two marked rework edges |
| Observations | Existing `washnfold-friday91` 1.0.0: 330 activity rows, 39 orders, eight activities |
| Modeled duration spellings | `min` in processing, setup and wait metadata |

The current source CSV and prepared summary match the adopted fixture
byte-for-byte. The source model's last-change revision also matches that
fixture's recorded source revision. No data regeneration or numerical expectation
change was required. The instructional diagram is attributed under the source
repository's CC BY 4.0 terms; its complete mixed-license notice is retained.

## Explicit activity identities

| Observed activity | Model step ID | Baseline model class |
| --- | --- | --- |
| Drop-off and ticket | `dropoff` | RNVA |
| Sort and tag | `sort_tag` | RNVA |
| Wash | `wash` | VA |
| Dry | `dry` | VA |
| Fold and package | `fold_package` | VA |
| Fold correction | `fold_correction` | NVA |
| Stage for collection | `stage` | RNVA |
| Send readiness notification | `notify` | VA |

All observed labels are covered exactly once. Display names differ for Wash,
Dry and Fold/package; they are not matched heuristically. The remaining six
model nodes are routing/queue/start/end nodes without an observed-activity
mapping. The pass edge goes from `packaging_check` to `notification_queue`; the
fail edge enters `correction_queue`, and corrected packages rejoin
`notification_queue`. Both declared rework flags and pass/fail outcomes survive
projection.

## Compatibility and remaining contracts

The bridge preserves each complete producer node and edge in its `flo` metadata,
including worker declarations, class labels, measured/display fields and routing
attributes. Its current accepted node kinds and edge semantics cover this
export; no unsupported route/subprocess/branch declaration was found. A JSON
round-trip preserves the projection fingerprint recorded in the manifest.

Three boundaries still need explicit handling downstream:

1. **S3 classification derivation:** `value_class` is retained inside producer
   metadata. The bridge currently leaves `ProcessStepIR.value_classification`
   at its general default rather than translating RNVA/NVA. S3 must derive an
   explicit policy from the preserved labels, rejecting missing/conflicting
   classes for measured tasks. Do not use that default as the book's VA policy.
2. **S2a clock and units:** the diagram uses `min`, while observations declare
   numeric cumulative operating minutes with closed hours already excluded.
   Matching duration dimensions does not establish calendar semantics. The
   bridge's calendar-event bindings are not bindings for this numeric CSV;
   retain its existing `NumericLogContract` and reconstruction conventions.
3. **S3 analyst conventions:** right-first-time overrides and Wash/Dry
   load-envelope aggregation remain explicit declarations. The graph does not
   encode parallel child-load timing as split/join nodes. Source comments also
   identify overlapping release/Wash waits. Model duration averages must not
   enter observed PCE arithmetic or be double-counted.

This slice adds no analytical method, new parser, implicit conversion, or claim
that the model-backed 13.7% PCE demonstration is complete. Existing requirement
statuses and numerical fixture versions remain unchanged.

## Reproduction and acceptance

Offline source tests verify pinned artifact/observation hashes, complete mapping,
topology, decision/rework preservation, model metadata and unit spellings. They
require neither FLO nor a sibling checkout:

```sh
uv run --locked pytest tests/test_book_model.py tests/test_integration_contracts.py
```

The isolated installed-wheel ecosystem test calls the published producer APIs
on the pinned `.flo`, compares the resulting JSON object with the stored export,
and checks the existing bridge's fingerprint and mapping:

```sh
uv run --locked python tools/check_wheel.py --ecosystem --artifacts-dir artifacts/ecosystem
```

The wheel runner copies these fixtures into its isolated suite. A sibling source
checkout and editable producer imports are unnecessary. S1's tests establish
source/export compatibility; S4 remains responsible for the full file-to-measures
route and all independently governed baseline calculations.

The final local source gates pass with 1,771 tests and five explicitly deferred
expected failures, at 93.19% full-package statement coverage. The isolated wheel
matrix passes 24 base, 33 pandas, 35 storage and 42 ecosystem tests (134 total),
including reproduction of the actual book export with published FLO 0.4.3 and
rejection of the legacy source's invalid timing placement. Ruff, formatting,
Vulture, lock consistency, typing and all eight import-boundary contracts pass.
