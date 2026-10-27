# Ecosystem baseline and exchange contracts

The initial bridge lives in `lss4py.integration`, with no FLO imports or mandatory
rendering dependency. It accepts the public JSON export from FLO **0.4.3** and
retains **0.4.2** payload restoration. The
optional `integration` extra installs that released package; numerical analysis
uses the existing NumPy/SciPy stack. The `visualization` extra provides
Matplotlib and Seaborn. See [ADR-0022](adr/0022-ecosystem-integration-contracts-and-journey-gates.md)
and [ADR-0023](adr/0023-matplotlib-contract-with-seaborn-convenience.md).

Portable projection shapes are validated with Pydantic, declared directly in the
base package so the bridge continues to work without FLO. The outer envelope is
closed; producer objects remain extensible. Validation uses a typed view while
serialization retains the original JSON, including omissions and unknown
annotations. Errors retain `lss4py.errors.ValidationError` and identify nested
fields such as `export.edges.0.rework`. See the
[Pydantic pilot assessment](assessments/v021-pydantic-pilot.md) for the dependency
and compatibility decisions. FLO still owns its native-document validation.

## Initial supported contracts

- `ProcessProjection.from_flo_export(...)` captures schema-shaped JSON, FLO
  version, source namespace, explicit model revision and activity-to-step mapping.
  It preserves source metadata and all supported node/edge identities. Labels and
  row position never determine identity. `to_process_model()` produces the existing
  analytical contract without importing upstream IR classes.
- Exchange schema **1.0** covers start/end/task/queue/decision and explicit
  parallel split/join nodes. Rework, handoff and outcome metadata are preserved.
  Generic branches, subprocess hierarchy, dispatch routes and unrecognized edge
  semantics are rejected. This is a bounded projection, not full FLO conformance
  analysis or a guarantee that declared graph reachability is checked by lead time.
- `EvidenceManifest.create(...)` snapshots completed timing/descriptive results,
  process identity, source hashes/references, explicit cohort/exclusions, timezone
  and ordering policy, and software versions. Saving/reloading validates schema,
  method context, units, case identity and the evidence fingerprint.
- `SourceEvidence` hashes and `verify_sources(...)` check explicitly supplied
  source snapshots. Hashes detect accidental changes; they are not signatures or
  proof that a chosen analysis is appropriate. The caller owns source loading.
- `MetricAnnotation` initially references an already computed grouped mean for
  one exact `step_id`. Observed values/units are obtained from the result and never
  overwrite modeled values. Missing estimates remain unavailable.
- `restore_timing(...)` reconstructs a saved `TimingResult` without a kernel call.
  `lss4py.reporting.visualization.plot_timing(...)` draws that result, accepts an
  existing Matplotlib axes and returns native axes. It displays diagnostic messages
  and preserves order, units and input data. It never displays or saves implicitly.

The public bridge/API is an initial pre-1.0 contract. Unsupported schema/version
combinations fail explicitly. It can be extracted when demonstrated reuse or
independent release needs warrant a package boundary.

## First reference journey

```sh
uv run --locked python tools/check_wheel.py --ecosystem \
  --artifacts-dir /tmp/lss4py-ecosystem-artifacts
```

The runner builds the candidate LSS4PY wheel, copies fixtures/tests outside the
source tree and tests a clean base install, then pandas, then published FLO 0.4.3
and the visualization extra. It rejects editable/source imports and leaked test
plugins. All dependency versions are constrained by `uv.lock`.

The ecosystem study calls `flo.export()` and `flo.validate()` from the supported
facade, projects the JSON contract, loads interleaved CSV observations, resolves
source activity IDs, and explicitly selects cases with intake and close events.
The incomplete case is recorded as excluded. Observed span and per-step activity
summaries are computed, persisted, reloaded and checked independently. Rendering
saved observed evidence succeeds with analytical functions and Seaborn estimation
disabled.

Artifacts include the manifest, source snapshots, observed annotation JSON, FLO's
modeled value-stream SVG and an observed-duration chart in SVG/PNG. **Measured
overlays are not supported:** FLO's public renderer retains modeled facts, and
observed metrics are separate, labeled artifacts. Fishbones and a possible general
rendering package remain open decisions.

## Acceptance and enforcement

`tests/test_integration_contracts.py` tests schema/version rejection, topology and
handoff preservation, renamed/reordered labels, identity/mapping errors, explicit
unit conversion, cohort/exclusion consistency, source/evidence fingerprints,
nullable annotations and restoration/rendering without recomputation. A fresh
interpreter proves core plus bridge import requires no FLO/Matplotlib/Seaborn.
Import-linter forbids core layers from depending on the bridge and the bridge from
depending on analytical implementations, adapters or rendering.

`e2e/ecosystem/test_journey.py` checks the real released producer's export against
the frozen contract fixture and the installed-package input-to-artifact journey.
Semantic SVG/plot checks establish exact case/step association, units, modeled/
observed labels and exclusion messages. Agg text bounds catch clipped labels;
fixed-size/font visual comparison guards the observed PNG. FLO's diagram output
is checked for deterministic rendering and both flow surfaces. Its visual layout
is also governed by FLO's own renderer tests; this suite does not duplicate that
renderer's complete visual corpus.

CI's existing `smoke` job now runs the complete ecosystem journey and uploads
evidence/graphics. The release build job requires it before publishing artifacts.
The LSS4PY maintainer owns these fixtures, compatibility pin and gates until a
separate integration owner/package is established. Increasing the supported
version set or changing semantic/visual fixtures requires explicit review.
