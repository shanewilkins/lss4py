# LSS4PY

LSS4PY is a Python-first toolkit for modern Lean Six Sigma practice in complex, service-oriented, and telemetry-rich systems.

It focuses on mathematically honest process analysis, with percentiles and tail risk (p50/p90/p95/p99) treated as first-class signals for decision-making.

## Why LSS4PY

Classical process improvement often relies heavily on averages and normality assumptions. In real-world operations (healthcare, logistics, customer service, IT operations, financial services), rare but extreme outcomes can dominate customer pain and business cost.

LSS4PY is built to make those outcomes visible and actionable.

## Vision

LSS4PY treats Lean Six Sigma as a computational discipline:

- Python-first and reproducible by default
- Explicit statistical assumptions and diagnostics
- Percentile- and tail-aware analysis for prioritization
- Workflow integration across operations, IT, and data teams

## Core Scope (Current Direction)

The package is being built to support end-to-end process improvement workflows:

1. Ingest process data (tabular/event-log/telemetry exports)
2. Compute cycle, lead, and wait-time distributions
3. Run percentile-aware before/after comparisons
4. Perform SPC and capability analysis with explicit assumptions
5. Identify bottlenecks from event-log-style data
6. Support simulation-informed redesign decisions
7. Produce reproducible, code-backed project outputs

## Design Principles

- Thin integration layer over the scientific Python ecosystem
- Process-centric abstractions over ad hoc scripting
- Tail-risk-first summaries instead of average-only reporting
- Reproducibility and inspectability by default
- Enterprise realism without unnecessary platform complexity

## What LSS4PY Is Not

- Not a BI dashboard platform
- Not a GUI framework
- Not a reimplementation of established stats libraries
- Not a certification shortcut

## Ecosystem Direction

This repository is the analytics core (`lss4py`). The broader planned ecosystem includes:

- `lss4py` — Core analytics and process intelligence
- `lss4py-deliverables` — Structured Lean Six Sigma artifacts and reports
- `lss4py-labs` — Synthetic enterprise-style datasets and process generators

## Installation and Environment (uv)

This project uses `uv` for environment and dependency management.

### Requirements

- Python 3.12+
- uv

### Quick start

```bash
uv sync
```

This creates a local `.venv` and installs the package in editable mode.

To run package commands in the managed environment:

```bash
uv run python -c "import lss4py; print('lss4py ready')"
```

## Project Status

Early-stage foundation work is in progress. API surface, modules, and workflows will evolve as core capabilities are implemented.

## Contributing

Contributions, issues, and ideas are welcome. Please open an issue describing:

- the process-improvement use case,
- the expected analytical behavior, and
- any assumptions or data constraints.

## License

MIT. See `license.md`.