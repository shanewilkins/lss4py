# Actual Wash n' Fold book model

Fixture `washnfold-book-model` version 1.0.0, accepted 2026-10-26 for sprint S1.

Source: Shane M. Wilkins, *Modern Process Improvement with Python*,
[modern-process-improvement](https://github.com/shanewilkins/modern-process-improvement),
`book/diagrams/washnfold.flo` at revision
`a10b7ecbc33908cffcafd4bbc3783b3447163406`. This is the model file's last-change
commit; its bytes also match the clean source checkout inspected at
`afca5fe41237ead0be2bdfce4e08341d7deaea12`.

The diagram is reused as original instructional material under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source repository's
full mixed-license notice is preserved in `SOURCE_LICENSE.md`. The `.flo` file
and notice are unmodified byte copies. `process-export.json` is the mechanically
produced JSON object from FLO 0.4.3's public `flo.export()` API, formatted with
two-space indentation and a terminal newline. The explicit activity mapping and
manifest are LSS4PY fixture declarations. No source simulation was rerun.

The actual book export was first checked against 0.4.2 and then reproduced
unchanged with published 0.4.3. Its projection fingerprint records 0.4.3 as the
producer; the original observation/model bytes and classification declarations
are unchanged.

`manifest.json` pins source identity, producer version, artifact hashes, the
projection fingerprint and the existing `washnfold-friday91` 1.0.0 observations.
The source activity CSV and prepared summary exactly match that adopted fixture;
neither is duplicated or revised here. Update this fixture only with a reviewed
version, source attribution, hashes and synchronized contract tests.

The export has 14 nodes, 14 edges, one packaging decision and two explicitly
marked rework edges. All eight observed activity names map to distinct task IDs.
`Wash` maps to `wash` (displayed as `Wash loads`); `Dry` to `dry` (`Dry loads`);
`Fold and package` to `fold_package` (`Reunite, fold, and package`). Display text
does not define observation identity. Routing nodes, queues, start and end have
no observation mapping.

All modeled duration metadata uses `min`. These are displayed/model facts;
observations independently declare cumulative operating minutes. The source
comments warn that order release wait overlaps load Wash wait. Do not add diagram
averages to observed durations or infer a work calendar from the unit spelling.

The bridge preserves the entire producer nodes/edges and their metadata. It does
not derive the numerical reconstruction policy from `value_class`, and its
calendar-event bindings do not describe the numeric activity CSV. See the
[S1 assessment](../../../../docs/assessments/v021-book-model.md) for the remaining
policy work and explicit conventions. This fixture does not claim the full
model-to-measurement workflow is implemented.

Offline tests require neither FLO nor the source checkout. The installed
ecosystem test reproduces validation/export with published `flo-lang==0.4.3` and
checks the projection fingerprint using the ordinary wheel runner:

```sh
uv run --locked python tools/check_wheel.py --ecosystem
```
