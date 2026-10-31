# Actual Wash n' Fold book model

Fixture `washnfold-book-model` version 2.0.0, accepted 2026-10-30.

Source: Shane M. Wilkins, *Modern Process Improvement with Python*,
[modern-process-improvement](https://github.com/shanewilkins/modern-process-improvement),
`book/diagrams/washnfold.flo` at clean revision
`cefd20a8acb68636798666383510744cc351684c`.

The source and mixed-license notice are byte copies. Diagrams are reused under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); `SOURCE_LICENSE.md`
retains the complete notice. `process-export.json` was mechanically generated
by published FLO 0.5.0's public `flo.export()` API, formatted with two-space
indentation and a terminal newline. The mapping and manifest are explicit
LSS4PY fixture declarations. No simulation or observation data was regenerated.

The manifest pins the source revision, producer, diagnostic records, artifact
hashes, projection fingerprint, and unchanged `washnfold-friday91` 1.0.0
observations. All 330 observations across 39 orders and eight activities retain
their existing identities. The model retains 14 nodes and 14 edges, with one
packaging decision and two explicitly declared rework edges; the return relation
is the meaningful empty object `rework: {}`.

FLO 0.5 supplies first-class value classes and measurement profiles. This actual
book model intentionally supplies no `analysis_input`: means are display evidence,
not modeled elapsed-time inputs. Profiles retain simulated basis, distinct order/
load/correction populations, observation context, evidence references and measured
zero. Notification remains VA as currently declared by the book. FLO's separate
reference fixture differs and is not a replacement for this source.

Order-release waiting overlaps the load Wash wait. No displayed mean enters the
observed arithmetic. Policy derivation reads model-owned classifications and
records `source_field: value_class`; analyst conventions still own boundaries,
parallel-load envelopes and failed-attempt treatment. Calendar bindings on the
general ProcessModelIR do not define this numerical CSV's operating clock.

The manifest retains warnings from published 0.5.0, including its known
invalid-duration warnings for unselected analytical inputs. Warning-only producer
operations succeed; the standalone example saves the normalized report in its
evidence bundle. A local upstream fix is not substituted for the pinned release.

The previous book model/export/manifest are preserved under
`../legacy-0.4.3/book-model/` for exact legacy restoration and policy tests.
Offline tests need neither FLO nor the book checkout. Installed-wheel acceptance:

```sh
uv run --locked python tools/check_wheel.py --ecosystem
```
