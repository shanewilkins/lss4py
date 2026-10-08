# Contributing to LSS4PY

Thank you for helping make Lean Six Sigma analysis more accessible in Python.
Contributions may include code, tests, numerical fixtures, documentation, examples,
or corrections to the governed requirements and compatibility matrix.

## Before you start

For a substantial feature, public API change, or new dependency, open an issue
before investing heavily in implementation. Describe the user problem, the
proposed scope, and any Lean Six Sigma or statistical references involved.

The project roadmap targets complete practitioner workflows rather than a loose
collection of statistical wrappers. New analytical features should fit the
[analysis journey](docs/analysis-journey.md) and the
[roadmap](docs/roadmap.md).

## Development setup

LSS4PY currently requires Python 3.14 and uses
[uv](https://docs.astral.sh/uv/) for its locked environment.

```bash
git clone https://github.com/shanewilkins/lss4py.git
cd lss4py
uv sync --locked --group dev
uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
```

The `pre-commit` stage runs Ruff on changed files and the locked test suite without coverage.

The `pre-push` stage and CI run the locked repository-wide quality gates.

Run the same checks before submitting a pull request:

```bash
uv lock --check
uv run --locked lint-imports
uv run --locked ruff check .
uv run --locked ty check
uv run --locked xenon --max-absolute B --max-modules A --max-average A src/lss4py tests
uv run --locked pytest
uv run --locked vulture src tests --min-confidence 80
```

CI additionally enforces 95% coverage on the current supported slice and runs a
built-wheel smoke test outside the source tree.

## Releases

LSS4PY publishes to PyPI from GitHub Actions through trusted publishing.

The release workflow lives in `.github/workflows/release.yml`.

Publishing starts when a GitHub release is published for a version tag such as `v0.1.0`.

The workflow builds distributions in one job and publishes them to PyPI from a separate `pypi` environment job with `id-token: write`.

For a brand-new PyPI project, configure a pending publisher on PyPI before the first release.

Use these values for the first `lss4py` publisher:

- PyPI project name: `lss4py`
- GitHub owner: `shanewilkins`
- GitHub repository: `lss4py`
- GitHub workflow name: `release.yml`
- GitHub environment name: `pypi`

After the pending publisher exists on PyPI, publish the GitHub release or rerun the failed release workflow.

## Contribution expectations

- Keep changes focused and include tests for new or changed behavior.
- Validate invalid inputs, boundary cases, and statistical assumptions explicitly.
- Return governed LSS4PY result models rather than exposing an upstream library's
  result object as the stable API.
- Keep calculations independent from optional plotting and document-generation
  dependencies.
- Preserve dataframe-neutral analytical contracts. Core file adapters materialize
  Polars; analytical behavior should be tested with pandas and Polars when applicable.
- Cite authoritative formulas or reference implementations for new numerical
  methods. R `SixSigma` compatibility claims require versioned fixtures and
  documented tolerances.
- Update user requirements, technical requirements, and traceability when behavior
  or scope changes. Add an ADR when a durable architectural choice is involved.
- Update documentation and examples alongside public behavior.

See [docs/README.md](docs/README.md) for the documentation hierarchy and lightweight
governance process.

## Pull requests

A pull request should explain the user outcome, implementation approach, validation
performed, and any compatibility or migration impact. Draft pull requests are
welcome for early design feedback. A contribution is ready for review when the
locked quality gates pass and its documentation is complete.

By contributing, you agree that your contribution will be licensed under the
[MIT License](LICENSE.md).
