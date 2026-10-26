# Toolchain policy

Updated 2026-10-26. `pyproject.toml` defines tool policy and `uv.lock` selects
versions. Local hooks invoke `uv run --locked`; CI and release checks use the
same configuration. Run `uv run --locked pre-commit run --all-files
--hook-stage pre-push` to exercise the source gates locally. Ruff includes source
security checks; dependency audits run separately in CI and release builds.

CI and release workflows pin uv 0.13.5. The build backend is constrained to
`uv_build>=0.13.5,<0.14.0`, allowing that uv version's bundled backend without
the earlier version-range warning. Python remains explicitly pinned to 3.14.

## Ruff consolidation

- Ruff owns linting and formatting. CI and pre-push run both `ruff check .` and
  `ruff format --check .`; commit hooks fix changed Python/notebook files.
- `C901` limits individual functions to McCabe complexity 10 across the repository.
  Xenon and its Radon dependency are removed. This deliberately retires Xenon's
  module and overall-average limits; McCabe and Radon do not count every construct
  identically. The former per-function rank-B ceiling is not an exact metric
  equivalence claim.
- `D` enforces Google-style docstrings across source and tooling. Module, class
  and package presence checks (`D100`, `D101`, `D104`) remain disabled. Tests and
  installed-wheel tests are exempt from `D`. This expands the old pydocstyle
  enforcement scope. Ruff is the single documentation gate; pydocstyle and
  Interrogate are removed. There is no percentage-based docstring requirement.
- `C4` and `PIE` check redundant constructions. `RUF100` rejects obsolete
  suppressions, `RUF043` makes regex intent explicit in exception tests, and
  `PT012` isolates the operation expected to fail. `SIM102` and `SIM114` cover
  nested conditions and identical branches. Other rule families are introduced
  individually after reviewing their effect; neither `ALL` nor preview rules are
  enabled.
- `S` replaces the production-source Bandit scan. Tests, installed-wheel tests,
  tools and examples are exempt from `S`, preserving the former scan's scope.
  `S101` remains disabled, matching the previous `B101` exemption. `PLE2502`
  checks bidirectional Unicode across the repository, including outside production
  source. Security checks now run with ordinary Ruff lint in commit, pre-push,
  CI and release gates.

## Checks retained alongside Ruff

| Tool | Distinct responsibility |
| --- | --- |
| ty | Type checking rather than syntax-level lint. |
| import-linter | Architectural dependencies between package layers. |
| Vulture | Broader unused-code analysis, beyond unused imports and local variables. |
| pip-audit | Vulnerabilities in resolved third-party dependencies. |
| pytest-cov | Full-package statement coverage with a 90% minimum and no omitted modules. |
| Twine | Built distribution metadata validation. |

The 2026-10-26 review replaces Bandit for this package's current scope, without
claiming full plugin parity. The installed-tool comparison found B613, B614,
B615 and B703 without corresponding Ruff S codes. B613's bidirectional-Unicode
concern is addressed by Ruff `PLE2502`. B614 (PyTorch loading), B615 (Hugging Face
downloads) and B703 (Django `mark_safe`) concern APIs absent from production
source. Reassess security rules if those integrations are introduced. Matching
rule numbers alone do not establish identical detection semantics.

Bandit is removed from development dependencies and executable gates. The dated
v0.2.0 gate snapshot and its assessment reader retain the historical `bandit`
check name; they describe the original captured evidence, not a current command
or dependency requirement.

The former Interrogate 80% gate is retired. The selected Ruff `D` rules enforce
public callable documentation and Google-style formatting; class and private
member documentation is written where it explains behavior rather than to meet
a coverage percentage. Historical assessments retain their original docstring
coverage evidence.

## Test and installation gates

Commit hooks run only locked Ruff lint/format on changed files. Pre-push runs the suite once,
with required PyArrow and full-package coverage; it no longer repeats a plain
pytest run. The release workflow consumes that same pre-push gate instead of
repeating the coverage suite. CI runs the equivalent coverage command directly.
Source and installed-wheel tests use strict configuration, registered markers and
strict expected failures. A passing test still marked xfail fails the gate until
its obsolete marker is removed.

The source suite writes JUnit and coverage XML under `artifacts/tests`; the wheel
runner writes one JUnit report per enabled installation stage when given
`--artifacts-dir`. CI/release upload available reports even after a failed gate,
with a 14-day retention period. Generated artifacts are ignored by Git.

Installed-wheel studies remain separate: they reject source/editable imports and
development-plugin leakage, and exercise base, pandas, storage and ecosystem
installations. They do not contribute to the source coverage percentage. Neither
branch coverage nor coverage of an unfinished stub implies that its feature is
implemented. Historical release assessments retain the tools and measurements
that were actually used when their evidence was captured.

The release gate passes its already built wheel to `tools/check_wheel.py --wheel`.
That option never rebuilds the package; all installation stages use the supplied
artifact. Retained `wheel.json` records its SHA-256, and the runner rejects an
artifact changed during verification. The no-option path still builds a wheel
for ordinary development checks.

## Workflow maintenance

All Action references are pinned to full commit SHAs with version comments.
Dependabot proposes weekly grouped GitHub Actions updates; it does not merge
them automatically. Workflows default to read-only contents access, disable
checkout credential persistence, and set job timeouts. Only the PyPI publishing
job grants OIDC token permission. Postpublication verification reads its helper
from the release tag.

CI validates the hook configuration with the existing `pre-commit` tool and
checks workflows with actionlint 1.7.11. Its standalone Linux binary is verified
against a pinned SHA-256 before execution; updating that version requires
updating its checksum in the same change. Optional shellcheck/pyflakes integrations
are disabled, so actionlint adds no Python dependency. Locally, install actionlint
separately and run `actionlint -shellcheck= -pyflakes=`. Workflow linting remains
a CI check rather than a prerequisite for local Python hooks.
