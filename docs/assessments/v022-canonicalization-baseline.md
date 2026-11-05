# v0.2.2 canonicalization baseline

Assessed locally on 2026-11-05. **Phase 1 of the v0.2.2 Pandera and canonical
Polars plan is complete.** This record freezes the accepted 0.2.1 dataframe
behavior before the internal execution and validation boundary changes.

## Baseline identity

- Baseline commit:
  `074bf2e58abf45cd9da011f5aac0b8082a9f98d4`.
- Locked dependency file SHA-256:
  `c0dc2bcb498064faaf96df7f02465211a4a8142cdd9a78e5a8dc8bf6c5c2edd9`.
- Neutral result fixture SHA-256:
  `3dc056c5bebb6ed287bfab02004db113f74d6124c81eb8dc6eb24893d15090ed`.
- Runtime: local macOS, Python 3.14.2, locked dependencies.

The Phase 1 commit includes a compatible dependency refresh without changing
the declared dependency ranges. All results below were reproduced against that
committed lock, including Pydantic 2.14.3.

The neutral fixture records complete payloads for every current result family
represented by the governed bundle tests. It removes only nondeterministic
creation time and source-backend identity. Differential tests reproduce the
fixture from ordinary pandas, hostile-index pandas, Polars and PyArrow inputs.
The fixture retains the 0.2.1 package version as historical evidence; comparisons
after release identity selection remove that one field while separately requiring
the current result provenance to report the current package version.

## Characterized dataframe behavior

The Phase 1 suite adds explicit coverage for:

- pandas nullable integer, float, boolean and string extension dtypes;
- ordered pandas categoricals, including retained row order and string
  analytical semantics;
- pandas indexes that are duplicate, named or otherwise analytically hostile;
- PyArrow dictionary arrays and multi-chunk numeric arrays;
- retained null row positions and source values;
- immutable pandas and PyArrow source objects;
- complete neutral analytical results across all three supported eager
  dataframe backends; and
- eager-only rejection for mean intervals and distribution profiles, completing
  the existing shared lazy/unsupported-input matrix.

Existing contract and backend tests continue to cover timezone-aware values,
null-versus-NaN behavior, non-string columns, row ordering and the remaining
public analytical functions. Lazy Polars plans are rejected without collection.

## Gate results

| Gate | Local result |
| --- | --- |
| Locked pre-push source gates | Pass: Ruff, formatting, hook validation, Vulture, lock consistency, coverage, import boundaries and typing |
| Full source suite | 2,377 tests; 0 failures; 0 errors; 5 skipped or explicitly deferred cases |
| Full-package line coverage | 96% |
| Governed R verification | 28 of 28 cases reproduced |
| Exact-wheel base installation | 28 passed |
| Exact-wheel pandas installation | 38 passed |
| Exact-wheel storage/PyArrow installation | 40 passed |
| Exact-wheel FLO/plotting ecosystem installation | 54 passed |

Installed-wheel reports, wheel identity and ecosystem outputs are retained under
ignored `artifacts/v022-phase1/`. Source JUnit and coverage reports are retained
under ignored `artifacts/tests/`. These are local baseline evidence, not release
or hosted-CI claims.

Reproduce the source and installed gates with:

```sh
uv run --locked pre-commit run --all-files --hook-stage pre-push
uv run --locked python tools/check_wheel.py --ecosystem \
  --artifacts-dir artifacts/v022-phase1
```

## Decision

The 0.2.1 baseline is green and reproducible. Phase 2 may add the bounded Pandera
Polars dependency. Subsequent phases must compare supported-backend acceptance,
public errors, result payloads and source immutability against this baseline.
This assessment does not approve any analytical formula or public API change.
