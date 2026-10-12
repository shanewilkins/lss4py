# Optional R reference tooling

This directory is an independent development environment for executing genuine
SixSigma reference calculations. R packages are managed by `renv.lock`; Python
packages remain managed by `pyproject.toml` and `uv.lock`. Normal Python tests read
the checked-in JSON fixtures and do not start R.

Install **R 4.6.1** separately and put `Rscript` on `PATH`. The bootstrap pins
**renv 1.3.1**, and the lockfile pins **SixSigma 0.11.1**, **jsonlite 2.0.0**, and
their recursive dependencies. Source package installation requires a C/C++ build
toolchain (and, on Linux, the usual R development/system libraries).

From the repository root:

```sh
Rscript --vanilla tools/r-reference/bootstrap.R
Rscript --vanilla tools/r-reference/verify.R
```

Bootstrap downloads packages and restores `.library/` beside these scripts.
Bootstrap support packages and renv state live in `.bootstrap/` and `.renv/`.
These directories are ignored by Git. No root `.Rprofile`, automatic activation,
Python R bridge, or global R package installation is used. Repeating bootstrap
restores the same lockfile. Verification requires no downloads once restored and
rejects a different R version or any missing/mismatched locked package.

Verification runs the committed fixture generator against original inputs in a
temporary directory. It compares all nine valid and five invalid-domain cases:
numerical results use each fixture's absolute/relative tolerances; structure,
parameters, warnings, error messages, classes, and nonfinite string tokens compare
exactly. It leaves checked-in outputs, hashes, and provenance untouched. The
separate `R reference verification` workflow runs these same commands; Python CI
has no dependency on that workflow.

## Deliberate updates

To update package versions, install the intended versions in an isolated library,
then explicitly snapshot that library with `renv::snapshot(packages =
c("SixSigma", "jsonlite", "renv"), library = ..., project = ...,
lockfile = ..., prompt = FALSE)`. Review the complete lockfile diff. An R runtime
update also requires updating `common.R`, this document, and the R workflow.

To replace reference evidence, point `R_LIBS_USER` at the restored `.library/` and
run `tests/fixtures/reference/r-sixsigma-baseline/generate.R` directly without
`--verify`. Follow [fixture governance](../../docs/reference-fixtures.md): review
outputs, provenance, checksums, and version changes. The generator's own
`--verify` mode remains available for byte-for-byte verification on the original
platform; the tooling verifier allows documented float rounding differences
across platforms.

See the official [renv snapshot documentation](https://rstudio.github.io/renv/reference/snapshot.html)
for the recursive dependency lock format.
