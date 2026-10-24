# v0.2 acceptance and release-readiness audit

Assessed 2026-10-24 against the uncommitted working tree. **Not ready to release.**
Version metadata remains 0.1.0, with no local release tags. No version bump, tag,
publication or sibling-book dependency change was made.

The roadmap assigns 37 user/technical requirements to v0.1/v0.2, including inherited
obligations: 17 are Satisfied and 20 Partial. Eighteen Partial requirements are
Must; two are Should. This audit does not waive or retarget any of them. Broad
requirements may span later method families; that does not require implementing
future families now, but current-slice completion or an explicit roadmap scope
statement is needed before claiming release acceptance.

The [JSON assessment](v02-release-readiness-before-fixes.json) records every criterion, current
gap and evidence reference, roadmap ownership, traceability validation, source
fingerprints and reproducible public-API probes. Regenerate it with:

```sh
uv run --locked python tools/audit_v02_readiness.py --output docs/assessments/v02-release-readiness.json
```

The command assesses the catalogs and captures probes; it does not rerun all
release gates. Its JSON names this dated report for separately verified gate
results. A report written successfully is not a passing release decision.

## Confirmed blockers

| Finding | Observed public behavior | Required follow-through |
| --- | --- | --- |
| Timing unit contract | `wait_time` has no unit argument and always returns `unit="hours"`. | Declare the common input/output time unit, preserve a documented default, and test supported units. |
| Negative timing inputs | Lead -1 and cycle -2 produce wait +1 instead of a domain error. | Validate each operand, not only the final difference, through the supported eager backend matrix. |
| Nonfinite timing inputs | NaN wait produces NaN; infinite per-row PCE lead produces 0%; infinite available takt time produces infinity. | Reject or explicitly handle missing/nonfinite inputs under a documented policy before reduction/division. Validate both scalar and tabular paths and retain meaningful LSS4PY errors. |
| Remaining current contracts | Backend/coercion, copy/materialization, row keys, per-result provenance, suitability metadata and current numerical/dependency evidence are still Partial. | Close the criteria for the declared current surface. Use the matrix to distinguish current missing behavior from future method families; no blanket promotion based on the book route. |
| Distribution acceptance | Local distributions and metadata validate, but release automation omits Twine and official target-version publication/install is unverified. | Enforce metadata validation, reconcile version sources, complete candidate review and verify the officially published artifact. |

The first three findings reproduce in the existing default numeric timing APIs,
not the new strict prepared/reconstruction paths. UR-001, UR-005 and TR-005 have
been corrected from Satisfied to Partial. TR-038 moves from Planned to Partial
because local distribution evidence now exists. Stale method/dataset/result-family
counts and obsolete reconstruction milestones are reconciled. Full acceptance
criteria and roadmap ownership are preserved.

Current required unit/domain corrections are distinct from later interval branch
wait/PCE and lifecycle pairing. Fixing them does not require OCEL or general
parallel-workflow inference.

## Verified gates

| Gate | Result and boundary |
| --- | --- |
| Locked pre-push hooks | Passed: vulture, `uv lock --check`, interrogate, pydocstyle, coverage, import-linter, ty, xenon and pytest. |
| Required-Arrow full suite | 1,546 passed, six expected failures, 95.53% coverage. Reused the immediately preceding 2026-10-24 full run; production code has not changed during this audit. Pre-push independently reran tests/coverage. |
| Static/security checks | Ruff, ty, Bandit, docstrings, complexity, dead-code and all eight import-boundary checks pass. |
| Dependency vulnerabilities | `pip-audit --desc --format json` reports zero known vulnerabilities across 97 installed dependencies. This is a dated environment audit, not a guarantee about future advisories or every optional extra. [Captured output](v02-dependency-audit.json). |
| Distributions | `uv build --out-dir /tmp/lss4py-v02-audit-dist` builds a wheel and sdist. Both pass isolated `twine check`. Artifacts still identify version 0.1.0. |
| Installed wheel | `tools/check_wheel.py --ecosystem` passes 23 base, 32 pandas-extra and 37 ecosystem tests, including FLO/plotting and the prepared/reconstruction examples outside the source tree. |
| Requirement integrity | All 49 user requirements trace to technical requirements; 96 total registered requirements have unique IDs and valid traceability endpoints. Counts and source fingerprints are in the JSON assessment. |

Exact primary commands used:

```sh
uv run --locked --no-sync pre-commit run --all-files --hook-stage pre-push
.venv/bin/python -m pytest --require-pyarrow --cov=src/lss4py --cov-report=term --cov-fail-under=90
.venv/bin/ruff check .
.venv/bin/ty check
.venv/bin/bandit -r src/lss4py --skip B101 -q
.venv/bin/pip-audit --desc --format json --output /tmp/lss4py-v02-pip-audit.json
uv build --out-dir /tmp/lss4py-v02-audit-dist
uv tool run --from twine twine check /tmp/lss4py-v02-audit-dist/lss4py-0.1.0.tar.gz /tmp/lss4py-v02-audit-dist/lss4py-0.1.0-py3-none-any.whl
uv run --locked --no-sync python tools/check_wheel.py --ecosystem --artifacts-dir /tmp/lss4py-v02-ecosystem
```

The sandbox initially could not resolve PyPI for the dependency audit. The approved
network-enabled retry succeeded. No failed attempt is counted as a passing gate.
Builds warn that the locally running uv 0.13.5 is outside the project's declared
uv-build requirement range; builds and metadata validation succeed. CI's pinned
uv 0.12.3 falls within that range. This audit did not change the lockfile or
introduce a new project dependency for Twine.

## Next implementation slice and publication sequence

First repair the older default timing unit/domain behavior and its cross-backend
regressions. Then close the remaining contract criteria against current APIs,
using the matrix to record evidence or an explicit scope decision. Draft
[release notes](../releases/v0.2.0.md) and a
[migration/worked-example guide](../migration-v0.2.md) are prepared.

Before tagging, make version metadata consistent in `pyproject.toml`, root
`__version__`, kernel provenance and bundle defaults; refresh example artifacts
whose version context changes. Require passing release/metadata and installed-wheel
checks on the reviewed candidate. The release workflow publishes when a GitHub
release is published; creating that release is a consequential publishing action.

After the official artifact is available, verify a clean installation from the
package index. Only then update the sibling book's normal dependency lock, execute
and render Chapter 9 in its actual environment, and close UR-046/TR-045. The
standalone examples already reproduce all four measures; this publication step
has not been executed or replaced by a local source override.

## Inherited v0.1 and current v0.2 requirement matrix

Status remains the register's full requirement status. An open Must row needs
current-slice evidence or an explicit scope decision; a future feature stub does
not close it. See the JSON for complete acceptance text and current gaps.

| Requirement | Owner | Priority | Status |
| --- | --- | --- | --- |
| UR-001 — Calculate core process-time metrics | v0.1 | Must | Partial |
| UR-002 — Calculate stage and rolled yield | v0.1 | Must | Satisfied |
| UR-003 — Combine an explicit process model with observed event data | v0.1 | Must | Satisfied |
| UR-005 — Understand assumptions and invalid inputs | v0.1 | Must | Partial |
| UR-006 — Reproduce R SixSigma analytical results | v0.2 | Must | Partial |
| UR-015 — Use any supported dataframe backend | v0.2 | Must | Partial |
| UR-016 — Validate and normalize analytical data | v0.2 | Must | Satisfied |
| UR-017 — Receive analysis guidance without surrendering judgment | v0.2 | Must | Partial |
| UR-018 — Define the CTQ and analytical contract | v0.2 | Must | Satisfied |
| UR-033 — Export an auditable analysis bundle | v0.2 | Must | Satisfied |
| UR-045 — Use curated reference datasets | v0.2 | Should | Partial |
| UR-048 — Evaluate a fixed customer promise on an explicit cohort | v0.2 | Must | Satisfied |
| UR-049 — Calculate cohort efficiency with a consistent denominator | v0.2 | Must | Satisfied |
| TR-001 — Maintain an explicit public API | v0.1 | Must | Satisfied |
| TR-002 — Accept backend-neutral observed data | v0.2 | Must | Partial |
| TR-003 — Keep the process-model contract explicit | v0.1 | Must | Satisfied |
| TR-004 — Make event-log topology semantics deterministic | v0.1 | Must | Satisfied |
| TR-005 — Reject invalid analytical inputs explicitly | v0.1 | Must | Partial |
| TR-007 — Validate R SixSigma parity with versioned fixtures | v0.2 | Must | Partial |
| TR-008 — Separate calculation from rendering | v0.1 | Must | Satisfied |
| TR-009 — Use typed analytical result models | v0.2 | Must | Partial |
| TR-010 — Preserve the analytics-core dependency boundary | v0.2 | Must | Partial |
| TR-011 — Run repository quality gates | v0.1 | Must | Satisfied |
| TR-014 — Use Narwhals as the analytical dataframe compatibility boundary | v0.2 | Must | Partial |
| TR-015 — Make materialization and copy behavior explicit | v0.2 | Must | Partial |
| TR-016 — Return backend-neutral keyed metric results | v0.2 | Must | Partial |
| TR-017 — Enforce cross-backend analytical equivalence | v0.2 | Must | Partial |
| TR-018 — Delegate numerical primitives behind governed kernels | v0.2 | Must | Partial |
| TR-019 — Provide an analysis suitability registry | v0.2 | Must | Partial |
| TR-020 — Record analysis provenance and interpretation context | v0.2 | Must | Partial |
| TR-021 — Model CTQs and specifications explicitly | v0.2 | Must | Satisfied |
| TR-033 — Define a versioned neutral analysis-bundle schema | v0.2 | Must | Satisfied |
| TR-037 — Govern reference datasets and fixtures | v0.2 | Should | Partial |
| TR-038 — Distribute wheel and verify PyPI packaging | v0.2 | Must | Partial |
| TR-039 — Bind book observations and cumulative operating minutes explicitly | v0.2 | Must | Satisfied |
| TR-041 — Keep promise eligibility and deadline evaluation separate | v0.2 | Must | Satisfied |
| TR-042 — Aggregate cohort PCE as a ratio of sums | v0.2 | Must | Satisfied |
