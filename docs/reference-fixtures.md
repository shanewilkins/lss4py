# Governed numerical-reference fixtures

The offline test catalog in `tests/fixtures/reference/manifest.json` separates
certified published expectations from original arithmetic examples. It validates
current supported methods; R-generated baselines are recorded separately from passing Python regressions.
Reference-only R snapshots do not claim Python parity.

| Dataset ID | Version | Reference basis | Intended methods |
| --- | --- | --- | --- |
| `nist-numacc1` | 1.0.0 | NIST-certified sample mean and sample standard deviation | `describe` |
| `synthetic-summary` | 1.0.0 | Independently derived five-point moments, spread and quantiles, with one omitted null | `describe` |
| `synthetic-process` | 1.0.0 | Direct timestamp subtraction, duration ratios, funnel counts and planning pace | Timing, yield, `takt_time` |
| `r-sixsigma-baseline` | 1.2.0 | Executed SixSigma 0.11.1 on R 4.6.1; reference-only | R Cp, Cpk, Z and defect/rework yield |

All four are **test fixtures**. They are not production evidence, teaching datasets,
or package-bundled data APIs. The test-only loader is `tests/reference_catalog.py`;
no test support or reference files are imported by the runtime library.

## Evidence and integrity

Each dataset declares a stable ID and version, intended analyses, purpose, source
kind/author/citation/version/access date, derivation, attribution, redistribution
status and notice, row/field schema, semantic differences, and artifact paths.
Inputs, expected outputs, and invalid cases have SHA-256 checksums over their exact
UTF-8 file bytes. Reformatting an artifact intentionally requires updating its
checksum and reviewing the change. Checksums detect changes; they are not a
substitute for reviewing the reference source or expected-value derivation.

Expected cases specify method, parameters, frame/scalar input kind, selected
expected fields, absolute and relative tolerances, tolerance justification, and
independent numerical basis. Unreferenced output fields are deliberately not
certified. Counts, identifiers and nulls compare exactly. Synthetic floating-point
estimates allow `atol=1e-12` and `rtol=1e-12`. NumAcc1's mean and sample standard
deviation are exactly representable and must match with zero tolerance.

`tests/test_reference_results.py` runs the cases with pandas, duplicate/non-default
pandas indexes, Polars and provisional Arrow. Invalid cases carry explicit
`ValidationError` types and expected messages. `tests/test_reference_catalog.py`
checks corruption, provenance/license omissions, duplicate IDs, schema violations,
escaping paths, invalid tolerances and unsupported R claims. Tests use fixed
checked-in expectations, never expected values computed by `lss4py` itself. Normal
test runs require neither network access nor R. Reference-only R cases are checked
for governance and integrity, and are excluded from Python numerical regression
dispatch until corresponding supported methods exist. `tests/test_capability.py`
now explicitly validates the Cp/Cpk subset, and `tests/test_capability_z.py`
validates specification Z distances; defect/rework yield is validated by `tests/test_defect_yield.py`.

## Published reference

[NIST NumAcc1](https://www.itl.nist.gov/div898/strd/univ/numacc1.html) is a constructed
three-observation numerical-accuracy example. Its
[data file](https://www.itl.nist.gov/div898/strd/univ/data/NumAcc1.dat) certifies a
mean of 10000002 and sample standard deviation of 1 (denominator n-1). The fixture
reconstructs the three integers in the published order: 10000001, 10000003,
10000002. NIST's autocorrelation value is excluded because `describe` does not
compute it. The input is a compact, independently authored JSON reconstruction;
the original NIST file and its prose are not redistributed.

The authored fixture JSON follows the repository MIT license. That does not
relicense NIST source material. NIST is acknowledged as the source of the
certification; consult its [source terms](https://www.nist.gov/open/license) before
adding third-party source files, full datasets, or derived teaching material.

## Independent derivations

For the valid values 1, 2, 3, 4, 5, the sum is 15 and the sum of squared deviations
from 3 is 10. Thus the sample variance is 10/4, standard deviation is sqrt(5/2),
and CV is sqrt(5/2)/3. The stored square-root values were rounded from 50-digit
Decimal arithmetic. Symmetry gives skewness zero; the fourth-deviation sum of 34
gives uncorrected Pearson kurtosis 1.7, then sample-corrected excess kurtosis -6/5.
Quartiles/tails use linear interpolation; median absolute deviation is 1.
The sixth, null observation contributes only to total and missing counts.

Synthetic process cases record every direct calculation in `expected.json`.
They include percentage/fraction options and the original eight supported calculations
across the catalog; Cp/Cpk use the genuine R subset. Funnel yields mean conversion through the configured stages;
they do not reproduce SixSigma's defect/rework counting semantics. The scalar
`takt_time` case requires no frame, regardless of the surrounding backend matrix.

## Adding or changing a fixture

1. Select a stable ID and increment the dataset version for substantive changes.
2. Check source attribution and redistribution terms. Classify it as a test
   fixture or a teaching dataset, and record any semantic differences.
3. Author `inputs.json`, `expected.json`, and `invalid.json`. Every expected value
   needs a documented independent basis. Do not use the implementation under test
   to generate its reference answer. Published certified fixtures may have no
   invalid cases; synthetic/generated cases should exercise invalid domains.
4. Declare the schema and intended methods. Compute each artifact hash, for
   example `shasum -a 256 tests/fixtures/reference/<id>/inputs.json`, and enter it
   in the manifest. No helper silently blesses modified expected values.
5. Run the catalog and reference tests, then the repository quality gates:

```bash
uv run --locked pytest tests/test_reference_catalog.py tests/test_reference_results.py
# With the optional storage extra installed:
uv run --locked pytest tests/test_reference_results.py --require-pyarrow
```

## R SixSigma acceptance

The catalog reserves source kind `r_sixsigma`. Such an entry must declare package
`SixSigma`, package version `0.11.1`, R runtime version, generation time and command,
a checksummed generator artifact, invalid-input evidence, and explicit semantic
differences. Metadata validation cannot prove that a generator was executed;
reviewers must inspect the script and actual generation evidence.

The `r-sixsigma-baseline` entry now has this source kind and
`validation_status="reference_only"`. It was generated using R 4.6.1 and SixSigma
0.11.1, with complete session information and 17-digit JSON output. Its seventeen valid
cases include two-sided and upper-only Cp, Cp/Cpk confidence limits, offset Cpk,
short-/long-term Z, and yield with/without rework. Six invalid-domain cases record
actual R errors, warnings, or returned values rather than assuming rejection.

Important recorded differences: `ss.ca.yield` returns a data frame; its DPU field
is the sum of defects. Zero opportunities return infinities, while mismatched
vectors recycle with a warning. Nonfinite outputs use explicit JSON string tokens
(`NA`, `NaN`, `Inf`, `-Inf`), not invalid JSON numbers. Python process_yield rejects those domains explicitly; see
[defect/rework yield](defect-yield.md) for the intentional differences.

The genuine installed package namespace is called by the original MIT-licensed
`generate.R` script; no upstream R implementation or bundled dataset is copied.
The package source URL/checksum, generator checksum, captured runtime provenance,
and fixture artifacts are recorded in the manifest. Optional R development tools
are isolated in [tools/r-reference](../tools/r-reference/README.md), with R 4.6.1,
SixSigma 0.11.1, jsonlite 2.0.0, and a separate recursive `renv.lock`. Install the
R runtime separately, then restore and verify from the repository root:

```bash
Rscript --vanilla tools/r-reference/bootstrap.R
Rscript --vanilla tools/r-reference/verify.R
```

The tooling verifier generates outputs in a temporary directory and applies the
declared numerical tolerances, comparing metadata and nonfinite tokens exactly.
A separate R workflow runs this check; Python dependencies and CI remain
independent of the R environment.

The fixture generator's direct `--verify` mode compares expected/error files
byte-for-byte. Without `--verify`, that generator writes artifacts and provenance;
review changes, update artifact checksums and source metadata, and increment the
fixture version when the reference changes substantively. The first generation
and a second byte-for-byte verification run succeeded locally.

TR-007 remains partial because additional retained R method families need reference
coverage. Cp/Cpk estimates and intervals, specification Z distances, and four
defect/rework yield cases now pass with documented semantic differences. The R
compatibility statuses remain Partial. NIST certification, Python backend
equivalence, and hand-derived examples must never be relabeled as R parity.
