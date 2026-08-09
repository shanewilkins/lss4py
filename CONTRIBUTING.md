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

The `pre-commit` stage keeps local commits fast by running Ruff on changed files.

The `pre-push` stage and CI run the locked repository-wide quality gates.

Run the same checks before submitting a pull request:

```bash
uv lock --check
uv run --locked lint-imports
uv run --locked ruff check .
uv run --locked pyright
uv run --locked xenon --max-absolute B --max-modules A --max-average A src/lss4py tests
uv run --locked pytest
uv run --locked vulture src tests --min-confidence 80
```

CI additionally enforces 95% coverage on the current supported slice and runs a
built-wheel smoke test outside the source tree.

## Contribution expectations

- Keep changes focused and include tests for new or changed behavior.
- Validate invalid inputs, boundary cases, and statistical assumptions explicitly.
- Return governed LSS4PY result models rather than exposing an upstream library's
  result object as the stable API.
- Keep calculations independent from optional plotting and document-generation
  dependencies.
- Preserve dataframe-neutral public contracts. Tabular behavior should be tested
  with pandas and Polars when applicable.
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
