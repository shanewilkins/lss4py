# v0.2.2 canonicalization differential and performance evidence

Assessed locally on 2026-11-05 against commit `68478f0` plus the Phase 6
evidence additions. Runtime: macOS arm64, Python 3.14.2 and the committed lock.
Timing and memory values characterize this machine; they are not universal
service-level objectives.

## Differential evidence

The accepted pre-migration implementation is
`074bf2e58abf45cd9da011f5aac0b8082a9f98d4`.

The complete neutral result fixture remains byte-identical:

- fixture: `tests/fixtures/canonicalization/v0.2.1-neutral-results.json`;
- SHA-256: `3dc056c5bebb6ed287bfab02004db113f74d6124c81eb8dc6eb24893d15090ed`;
- backends: pandas, pandas with hostile indexes, Polars and PyArrow; and
- comparison: every represented result value, missing count, warning, source
  position, key/group order, semantic schema fingerprint and provenance field,
  excluding creation time, source backend name, backend version and, after the
  0.2.2 identity selection, the intentionally changed package version.

The invalid-domain fixture was executed directly against the original commit:

- fixture: `tests/fixtures/canonicalization/v0.2.1-invalid-contract.json`;
- SHA-256: `cd7e6ab08b547f946eb08966d0aace8c65fd0768e98e745b7d31f281573114fe`;
- cases: 13 across descriptive, inference, distribution, capability, timing,
  deadline, stage yield, defect/rework yield and unsupported/lazy inputs; and
- comparison: acceptance/rejection status, exact exception class and message.

The current implementation matches both fixtures. Bundle tests additionally
capture every result family, serialize strict JSON, restore typed results and
require exact reserialization. Source-preservation and backend-contract tests
cover pandas indexes, null/NaN handling, Arrow chunks/dictionaries, timestamp
precision, group/key order and immutable caller inputs.

No differential was accepted or waived.

## Performance method

`tools/benchmark_canonicalization.py` creates deterministic 20,000-row inputs
for native Polars, pandas and PyArrow. A narrow frame has one selected numeric
column; a wide frame has that column plus 127 unused numeric columns.

Each scenario runs in a separate process. After one warmup, five observations
produce median wall times for:

1. selected-column canonical conversion;
2. private Pandera validation of the canonical frame; and
3. complete `describe` execution from the native source.

Python allocation is the maximum `tracemalloc` peak. Process memory is the
scenario high-water RSS minus the post-source baseline. The latter includes
first-touch library allocation and should be interpreted as a broad ceiling,
not an attribution of native buffers. Every scenario must:

- retain the complete source schema and row count;
- materialize exactly one selected column;
- complete each timed operation within 2 seconds; and
- remain within a 256 MiB process RSS delta.

These are regression budgets for the governed corpus, not public performance
guarantees.

## Observed performance

| Backend | Shape | Conversion (s) | Validation (s) | Total analysis (s) | Peak RSS delta (MiB) |
| --- | --- | ---: | ---: | ---: | ---: |
| Polars | narrow | 0.019009 | 0.005322 | 0.007510 | 18.391 |
| Polars | wide | 0.020768 | 0.005953 | 0.008829 | 16.406 |
| pandas | narrow | 0.044276 | 0.006300 | 0.016045 | 10.938 |
| pandas | wide | 0.036110 | 0.005556 | 0.020848 | 15.391 |
| PyArrow | narrow | 0.035718 | 0.005871 | 0.005917 | 9.172 |
| PyArrow | wide | 0.021128 | 0.004717 | 0.009194 | 17.875 |

All budgets pass. Wide-frame results confirm that only the declared measurement
column is materialized; the full source schema is inspected for provenance but
unused data columns are not copied into canonical analytical storage. Native
Polars still creates a detached selected-column frame to protect caller
immutability. pandas pays the deliberate scalar detachment cost that prevents
zero-copy aliasing and an accidental PyArrow dependency. PyArrow selection
retains immutable source semantics while allocating detached canonical evidence.

Raw evidence:

- `docs/assessments/v022-canonicalization-performance.json`;
- SHA-256: `af48a57c509fc8f538fee019b1c306fda66c9a9a5b1151ba46d27df4c3448387`.

## Before/after public-operation cost

The cost baseline is Phase 1 commit
`0c217cd9869b3ec162f1e8ff755655cbca76781c`. It contains the compatible lock
refresh but predates Pandera validation and canonical Polars execution, avoiding
dependency-refresh noise in the comparison. The same six deterministic
20,000-row scenarios ran against the baseline source and current working tree
in isolated subprocesses using the current locked environment. Each public
operation had one warmup followed by five observations.

| Backend | Shape | Validation before/after (s) | Validation ratio | `describe` before/after (s) | `describe` ratio | Peak RSS delta change (MiB) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Polars | narrow | 0.111466 / 0.125587 | 1.13x | 0.006947 / 0.010195 | 1.47x | +27.844 |
| Polars | wide | 0.111902 / 0.121660 | 1.09x | 0.007429 / 0.008176 | 1.10x | +25.312 |
| pandas | narrow | 0.117131 / 0.128215 | 1.09x | 0.007242 / 0.013430 | 1.85x | +35.891 |
| pandas | wide | 0.114391 / 0.153860 | 1.35x | 0.010152 / 0.019495 | 1.92x | +34.828 |
| PyArrow | narrow | 0.111068 / 0.125205 | 1.13x | 0.005456 / 0.005931 | 1.09x | +36.812 |
| PyArrow | wide | 0.114826 / 0.132339 | 1.15x | 0.008067 / 0.010442 | 1.29x | +33.750 |

Pandera-backed public validation adds 0.010–0.039 seconds and 0.76–0.78 MiB
of traced Python peak allocation on this corpus. Public `describe` adds
0.0005–0.0093 seconds. Its ratio is largest for pandas because the prior
operation was only 7–10 milliseconds; its traced Python peak increase is
0.28 MiB for pandas and at most 0.016 MiB for Polars and PyArrow.

The 25–37 MiB process high-water increase is material. It combines validation,
analysis and first-touch native-library allocation in each isolated process, so
it is useful as an end-to-end footprint observation but cannot be assigned
solely to canonical dataframe buffers. These single-machine timings are
regression evidence, not stable cross-machine performance claims.

Raw comparison evidence:

- `docs/assessments/v022-canonicalization-cost-comparison.json`;
- SHA-256: `556aaadb83482b2f607c2b74fc99f023638c76e558d44cda554a364412760581`.

## Packaging and dependency effects

`tools/capture_base_install.py` built and installed the wheel into a fresh
environment without test or optional extras.

| Measure | Observed |
| --- | ---: |
| Base wheel size | 141,500 bytes |
| Installed runtime packages | 44 |
| Fresh-process import median | 0.691379 seconds |
| Pandera | 0.35.0 |
| Polars | 2.1.0 |
| Narwhals | 2.28.0 |
| pandas present | No |
| PyArrow present | No |

The import median uses seven fresh processes. The retained observations include
one 9.287034-second cold-cache outlier; the other six range from 0.672321 to
0.700900 seconds. The median is reported without deleting the outlier.

Raw base evidence:

- `docs/assessments/v022-base-install.json`;
- SHA-256: `23774ce753934b8756d88709e9005142db11ef33e4a34dba8bbc7a6ce7eb351f`.

The same isolated build and installation procedure compared the Phase 1
baseline with the current working tree:

| Measure | Before | After | Change |
| --- | ---: | ---: | ---: |
| Base wheel size | 135,364 bytes | 141,500 bytes | +6,136 bytes (+4.5%) |
| Installed runtime packages | 39 | 44 | +5 |
| Fresh-process import median | 0.686288 s | 0.675754 s | -0.010534 s |

The added distributions are `pandera`, `packaging`, `typeguard`,
`typing-inspect` and `mypy_extensions`; none were removed. Both installations
exclude pandas and PyArrow. Each import series retains one roughly nine-second
cold-cache observation, while the seven-run medians differ by only 11
milliseconds. This run therefore provides no evidence of an import-time
regression, but it does not support claiming an import-time improvement either.

Raw comparison evidence:

- `docs/assessments/v022-release-footprint-comparison.json`;
- SHA-256: `2bb2c82c0a52929764debcc2c00d066808b07f0f6c7ba189925179a9fdcfce1e`.

The locked development environment audit inspected 103 distributions and found
zero known vulnerabilities. This is a dated advisory lookup, not a guarantee
about future disclosures or uninstalled optional dependency sets.

Raw audit evidence:

- `docs/assessments/v022-dependency-audit.json`;
- SHA-256: `1769015da69b6e9637becc8f2eddba62377105245b6c4d0c249dc30957ce3532`.

## Reproduction

```sh
uv run --locked python tools/benchmark_canonicalization.py \
  --output docs/assessments/v022-canonicalization-performance.json
uv run --locked python tools/capture_base_install.py \
  --output docs/assessments/v022-base-install.json
uv run --locked python tools/compare_canonicalization_cost.py \
  --output docs/assessments/v022-canonicalization-cost-comparison.json
uv run --locked python tools/compare_release_footprint.py \
  --output docs/assessments/v022-release-footprint-comparison.json
uv run --locked pip-audit --desc --format json \
  --output docs/assessments/v022-dependency-audit.json
uv run pytest -q tests/test_canonicalization_baseline.py --require-pyarrow
```

## Decision

Phase 6 passes. The canonical Polars implementation retains the governed 0.2.1
result and invalid-input contracts, keeps native source identity in provenance,
avoids wide-frame analytical materialization, satisfies the recorded local
performance budgets and preserves the base-install optional-backend boundary.
The trade is explicit: public operations add at most 39 milliseconds on the
governed 20,000-row corpus, isolated process high-water memory rises by
25–37 MiB, the wheel grows 6,136 bytes and the base installation adds five
distributions. In return, the release gains backend-independent validation,
detached canonical values, governed invalid-input behavior and one analytical
execution model. Given the small absolute latency and packaging changes, the
bounded memory increase and the correctness defects eliminated during
migration, this trade is accepted for v0.2.2. Phase 7 may record the accepted
architecture decision and these costs.
