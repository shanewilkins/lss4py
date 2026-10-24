# v0.2 acceptance and release-readiness follow-through

Updated 2026-10-24. **The local acceptance defects are fixed.** Source, project and
provenance now share the **0.2.0 candidate** version. It has not been tagged or
published. The exact local gate outcomes and reviewed source fingerprints are
recorded in [the gate snapshot](v02-release-gates.json); the
[generated assessment](v02-release-readiness.json) verifies that snapshot against
the working tree.

The roadmap's 37 inherited/current v0.1/v0.2 requirements now comprise 36 Satisfied
and one Partial: **TR-038 remains open solely for actual publication and clean
installation of that official version**. The release workflow now performs this
verification after publishing. Local prepublication readiness and completed
publication are separate recorded states; the assessment's `ready` stays false
until the full publication requirement is verified. No Must criterion was removed,
waived or moved to a later release to get this result.

The [before-fixes assessment](v02-release-readiness-before-fixes.md) and its
[JSON](v02-release-readiness-before-fixes.json) preserve the original blockers.
Current statuses apply to the declared implemented APIs and numerical claims;
unimplemented R and later belt method families remain explicitly unclaimed.

## Corrections and current evidence

| Original gap | Implemented correction |
| --- | --- |
| Hardcoded wait units | `wait_time(..., unit="minutes")` declares the common measurement unit. All four time units are checked; the legacy default remains hours. No implicit rescaling occurs. |
| Negative/nonfinite timing inputs | Each operand is validated before arithmetic. Negative wait operands, missing/NaN/infinite durations, nonfinite scalar takt inputs, invalid units and overflow fail with governed errors. |
| Stage coercion | Stage yields validate exact binary values before conversion; fractional values are never truncated, text is never coerced, and declared boolean options reject truthiness coercion. |
| Inconsistent eager-input errors | One Narwhals boundary validates supported eager frames and column identities. `UnsupportedInputError` is both an LSS4PY validation error and TypeError-compatible. Lazy plans are never collected. |
| Arrow ISO parsing exception | ISO/native instants use a shared explicit microsecond parser, normalizing aware instants to UTC and rejecting missing or mixed-awareness endpoints. Offset/fractional ISO inputs now pass the full backend regression instead of xfail. |
| Row identity and exports | Timing results retain source positions or declared unique scalar keys. Duplicate/invalid explicit keys fail; pandas indexes do not become identity. Detached Polars/pandas/Arrow result exports preserve keys and values. |
| Result context | Every governed calculation records semantic schema fingerprint, method/package and core/backend versions, missing policy, population/selection context and allocation policy. Audited capture checks version consistency and preserves source links. |
| Guidance and explicit choices | Thirteen registered methods declare outcome/predictor types and sampling/design prerequisites. `select_analysis` captures the practitioner's declared choice without running calculations; matching results can retain that decision. |
| Plain discovery dictionary | `map_process` returns typed `ProcessMapResult` with portable restoration, source positions, counts and assumptions. Existing `result["nodes"]`/`["edges"]` reads still work; `.to_mapping()` exports the old mapping. |
| Core/optional dependencies | Unused statsmodels was removed from core. Base installation proves pandas/Arrow/rendering dependencies absent. Explicit pandas, Arrow/storage and FLO/plotting extras have isolated installed-wheel checks. |
| Packaging controls | Twine is locked release tooling. Publication requires source quality/Arrow acceptance, wheel+sdist metadata validation, source/project/tag version agreement and installed ecosystem checks. A separate job installs and verifies the exact official PyPI version after publication. |

Five governed reference datasets and the current claimed genuine R SixSigma cases
retain their original expectations and tolerances. These tests pass; this does
not turn unimplemented R APIs into compatibility claims. Current reference and
contract requirements are satisfied; future families inherit the same rules.

## Verification

The 0.2.0 candidate passes **1,750 tests with five expected failures and 95.22%
coverage**, with PyArrow required. The remaining expected failures are the
explicitly deferred branch-aware interval metrics, not the fixed Arrow parser.
The installed matrix separately verifies base, pandas, Arrow/storage and ecosystem
behavior. Exact final counts and artifact identity/metadata results are retained
in the gate snapshot. Locked pre-push, Ruff, ty, docstring, complexity, security,
dead-code and all eight layer boundaries are required before publication.

Dependency audit reports zero known vulnerabilities across 104 third-party dependencies in its [captured environment](v02-dependency-audit.json). The unpublished editable project is explicitly skipped and covered by source/security tests. This is a dated
check, not a guarantee about future advisories or unimplemented optional engines.
Local uv 0.13.5 emits a backend-range warning; builds/metadata checks pass and CI's
pinned uv 0.12.3 remains within the declared build requirement range.

```sh
uv run --locked --no-sync pre-commit run --all-files --hook-stage pre-push
uv run --locked --extra storage pytest --require-pyarrow --cov=src/lss4py --cov-fail-under=90
uv run --locked python tools/check_wheel.py --ecosystem
uv build --out-dir /tmp/lss4py-v02-candidate-dist
uv run --locked twine check /tmp/lss4py-v02-candidate-dist/*
uv run --locked python tools/check_release.py --dist /tmp/lss4py-v02-candidate-dist --tag v0.2.0
uv run --locked python tools/audit_v02_readiness.py --output docs/assessments/v02-release-readiness.json
```

The assessment generator reads the catalogs and reruns the five original probes.
It verifies the dated gate snapshot's source fingerprints, but does not rerun all
gates, publish packages or treat a pending official-install check as completed.

## Publication boundary

Draft [release notes](../releases/v0.2.0.md) and the
[migration guide](../migration-v0.2.md) reflect these actual corrections. All four
book answers remain unchanged, and supplied bundles/notebook output are refreshed
with current provenance. Historical reference fixtures are not rewritten to claim
that their original calculations used a newer package.

Next is reviewing/tagging and publishing the candidate through the governed release
workflow. Its postpublication job installs only from official PyPI, verifies the
exact package version and required public APIs in a fresh environment, and cannot
reuse the checkout or a locally built artifact. That job has not run for 0.2.0.
No release, upload or sibling book dependency change was made during this work.

After the official package passes that check, update the book's normal dependency
lock and execute/render Chapter 9 there. UR-046/TR-045 retain that separate book
publication gap; local source overrides are not a substitute.
