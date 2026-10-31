# FLO-backed White Belt book workflow

The standalone [example](../examples/white_belt/flo_measure.py) runs the actual
book `.flo` and the governed Friday 91 CSV through the public FLO and LSS4PY APIs.
It keeps baseline classes in FLO, reconstructs measured orders, calculates the
book metrics, and saves an audited bundle plus the modeled value-stream diagram.
It requires no sibling checkout or simulation run.

## Run from this checkout

```sh
uv run --locked --extra integration python examples/white_belt/flo_measure.py \
  --model-dir tests/fixtures/ecosystem/book-model \
  --source examples/white_belt/event_log.csv \
  --output artifacts/book
```

For a wheel installation, install the wheel with `[integration]`, then run the
same example script using that environment's Python. Retain
`simulation_sources.json` and the observation `SOURCE_LICENSE.md` beside the
script. Supply the governed model fixture directory and CSV explicitly; they
are demonstration inputs, not installed package resources. To verify the entire
isolated wheel matrix:

```sh
uv run --locked python tools/check_wheel.py --ecosystem --artifacts-dir artifacts/ecosystem
```

That command copies the example and inputs outside the checkout, installs a
wheel with published FLO 0.5.0, and executes the script in a fresh subprocess.
It also tests base, pandas and storage installations independently.

## What the example measures

FLO validates and exports the native document. `ProcessProjection` binds CSV
activity identities to stable model node IDs. `derive_reconstruction_policy`
reads each mapped task's `value_class`; Python declares the measurement
boundary, cohort, right-first-time treatment and parallel-load accounting.
There are no duplicate baseline classification lists in the example.

The existing numeric ingestion contract supplies cumulative operating minutes
from 07:00, with closed hours already excluded. Reconstruction spans Drop-off
queue entry through final readiness notification work end. Wash/Dry use the
explicit parallel envelope convention; failed attempts are NVA. Setup and wait
are excluded from VA. No duration conversion is needed for this minutes-based
source. Modeled durations remain diagram facts and do not enter the arithmetic.

The installed acceptance test compares all eight reconstructed fields for every
one of the 39 orders with the independent prepared CSV, including WNF-003's two
Wash/two Dry loads and 82.7 VA minutes. Expected cohort results are:

| Measure | Baseline |
| --- | --- |
| VA / lead totals | 3535.3 / 25840.5 minutes |
| Cohort PCE | 13.7% |
| Mean lead | 662.6 minutes |
| Nearest-rank P90 among 21 eligible orders | 676.2 minutes |
| Deadline misses | 6 of 21 eligible orders |
| Corrections / affected orders | 5 / 5 |

The example is a pinned reproduction profile. It verifies the model artifacts,
producer export, mapping, projection and observed CSV against governed hashes.
Changed pinned inputs fail before evidence or rendering is written to a fresh
destination. For analytical scenarios with changed classifications, use the
[policy derivation API](order-reconstruction.md#derive-baseline-classes-from-flo)
with an explicitly revised projection; the scenario must not claim this pinned
baseline. The CSV-only example remains available independently.

## Saved evidence

The destination contains:

- `evidence.json`: audited v2 `AnalysisBundle` with typed reconstruction,
  descriptive, deadline and PCE results; source fingerprints and result links;
  numeric clock/boundary; model and producer revisions; mapping, classification
  attribution and remaining analyst conventions.
- `projection.json` and `policy-derivation.json`: separately inspectable copies
  of the projection and derivation evidence also held in the bundle.
- `modeled-value-stream.svg`: FLO's rendering of the declared model. It shows
  modeled facts; it is not a measured overlay.
- Copies of the original model, CSV, mapping, producer export, manifest,
  ingestion profile and both source licenses for verification and attribution.

Restoration validates the bundle and restores results without rerunning analysis:

```python
from pathlib import Path
from lss4py import AnalysisBundle
from lss4py.integration import ProcessProjection

output = Path("artifacts/book")
bundle = AnalysisBundle.from_json((output / "evidence.json").read_text())
bundle.verify_inputs({name: (output / name).read_bytes() for name in bundle.inputs})
projection = ProcessProjection.from_json((output / "projection.json").read_text())
assert projection.to_dict() == bundle.context["process_projection"]
reconstruction = bundle.get_result("reconstruction")
```

Input and bundle fingerprints detect accidental changes; they do not establish
source authenticity. The copied manifest records the book revision, licensing
and original source hashes. The standalone standard-library bundle validator
continues to validate the saved bundle without FLO.
