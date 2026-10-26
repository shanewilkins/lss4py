# LSS4PY

LSS4PY is a Python 3.14 Lean Six Sigma utility library for the current Yellow Belt slice.

It is focused on repeatable process metrics, yield calculations, and descriptive statistics.

It is not yet a full SPC, capability, simulation, or deliverables platform.

## Release status

The working tree prepares the unreleased **0.2.0 candidate**. The
[v0.2 acceptance follow-through](docs/assessments/v02-release-readiness.md)
records the completed local fixes and verification. Actual publication and
verification of the official PyPI package remain pending. See the
[release notes](docs/releases/v0.2.0.md) and [migration guide](docs/migration-v0.2.md).

## Stable Today

The current stable surface is intentionally small.

It includes these public functions:

- `lead_time`
- `wait_time`
- `process_cycle_efficiency`
- `takt_time`
- `created_to_booked_yield`
- `booked_to_completed_yield`
- `rolled_yield`
- `process_yield` (defect/rework counts, opportunity Yield/FTY/RTY, and DPMO)
- `describe` (typed descriptive statistics, optionally grouped)
- `capability_indices` (Cp/Cpk/components/intervals and explicit specification Z)
- `reconstruct_orders` (declared numeric activity-to-order accounting policy)
- `validate_order_summary` (prepared numeric order contract and consistency checks)
- `deadline_performance` (fixed-deadline misses with explicit eligible/ineligible cases)

The [White Belt preview](docs/book-preview.md) includes a runnable cell, rendered
output and inspectable evidence from pinned prepared observations. `describe`
supports explicit nearest-rank percentiles and measurement sums;
`process_cycle_efficiency(aggregation="cohort")` returns a ratio of sums with
cohort identities and denominator evidence.

See the [descriptive statistics guide](docs/descriptive-statistics.md) for examples
and the statistical conventions.

It also includes a process-model IR for integrating FLO-derived process structure with observed tabular data:

- `ProcessModelIR`
- `ProcessStepIR`
- `ProcessEdgeIR`
- `MetricBindingsIR`
- `LeadTimeBindingIR`
- `StageBindingsIR`
- `MetricSemanticsIR`
- `EventLogBindingsIR`

`Specification` and `AnalysisWindow` define reusable, validated CTQs, targets,
acceptance limits, and analytical context. See the
[specification guide](docs/specifications.md) for validation rules and an example
paired with `describe`.

It also includes stable event-log contracts and helpers:

- `EventStream`
- `IntervalEventLog`
- `EventLogCSVAdapter`
- `load_event_log`
- `CSVTabularAdapter` and `load_csv` for declared-schema CSV inputs
- `NumericLogContract`, `NumericEventLog`, `NumericEventLogCSVAdapter`, and
  `load_numeric_event_log` for numeric activity/lifecycle observations
- `validate_event_log`
- `map_process`

The [simulation ingestion guide](docs/simulation-ingestion.md) demonstrates all
current White Belt simulation sources, including numeric operating-clock logs,
with source hashes, explicit types/identities, and validation evidence.

Interval-event calculations are part of the current stable surface for:

- `lead_time`

`select_analysis` records an explicit practitioner choice without executing it.
`get_candidates` and `get_analysis` expose method requirements, assumptions, and
limits without executing analyses. See the [analysis guidance guide](docs/analysis-guidance.md).

`validate_data` returns structured, non-mutating data-quality reports against an
explicit `DataContract`. `normalize_data` prepares declared columns with auditable,
opt-in row exclusions. See the [data-quality guide](docs/data-quality.md) for
schema, key, timestamp, unit, missingness and duplicate policies.

`AnalysisBundle.capture` saves typed analyses with source hashes, selections,
software versions and linked specifications. Bundles restore without recalculation;
a standalone standard-library validator supports reviewers without analytical
dependencies. See the [analysis-bundle guide](docs/analysis-bundles.md).

## Contract

LSS4PY works from two inputs.

The FLO side supplies a normalized process model IR.

The observed-data side accepts supported eager dataframe inputs through Narwhals.
Core file ingestion materializes validated Polars frames by default, as recorded in
[ADR-0018](docs/adr/0018-use-polars-as-the-canonical-ingestion-backend.md). pandas
remains an optional analytical-input backend rather than the package's canonical
storage contract. See the [backend contract guide](docs/backend-contracts.md)
for tested equivalence, row/case identity, and supported eager input shapes.

LSS4PY calculates metrics from both.

The IR defines process structure and semantic bindings.

The DataFrame provides timestamps, stage outcomes, and measured times.

Explicit per-call metric arguments override IR bindings.

Parallel paths and rework loops are represented in the IR with explicit graph edges.

Event-log rows are the canonical observed data shape for process-model-aware metrics.

Per-case lead time uses the earliest observed start and latest observed completion.
Branch-aware wait time and process-cycle efficiency remain planned work.

## Quick Start

### Requirements

- Python 3.14
- `uv`

### Install

```bash
uv sync
```

### Verify

```bash
uv run python -c "import lss4py; print('lss4py ready')"
```

## Example

```python
import polars as pl

from lss4py import (
    LeadTimeBindingIR,
    MetricBindingsIR,
    MetricSemanticsIR,
    ProcessEdgeIR,
    ProcessModelIR,
    ProcessStepIR,
    StageBindingsIR,
    created_to_booked_yield,
    lead_time,
    process_cycle_efficiency,
    rolled_yield,
    wait_time,
)

process_model = ProcessModelIR(
    name="Client intake",
    steps=[
        ProcessStepIR(
            id="review",
            name="Review",
            cycle_time_column="review_hours",
            value_classification="non_value_add",
        ),
        ProcessStepIR(
            id="approve",
            name="Approve",
            cycle_time_column="approval_hours",
            value_classification="value_add",
        ),
    ],
    edges=[
        ProcessEdgeIR(source_step_id="review", target_step_id="approve", kind="sequence"),
        ProcessEdgeIR(source_step_id="approve", target_step_id="review", kind="rework"),
    ],
    bindings=MetricBindingsIR(
        lead_time=LeadTimeBindingIR(
            start_column="created_at",
            end_column="completed_at",
        ),
        stages=StageBindingsIR(
            created="created",
            booked="booked",
            completed="completed",
        ),
    ),
    metric_semantics=MetricSemanticsIR(parallel_timing="critical_path"),
)

data = pl.DataFrame(
    {
        "created_at": ["2026-01-01T08:00:00", "2026-01-02T09:00:00"],
        "completed_at": ["2026-01-01T18:00:00", "2026-01-02T15:00:00"],
        "review_hours": [2.0, 1.0],
        "approval_hours": [1.0, 2.0],
        "created": [1, 1],
        "booked": [1, 1],
        "completed": [1, 0],
    }
)

lead = lead_time(data, process_model=process_model)
wait = wait_time(data, process_model=process_model)
pce = process_cycle_efficiency(data, process_model=process_model)
created_booked = created_to_booked_yield(data, process_model=process_model)
rolled = rolled_yield(data, process_model=process_model)
```

### Ingest an interval event log

CSV interval logs use four semantic fields. Source names can be mapped during
loading; the returned `IntervalEventLog` wraps a Polars frame with canonical names.

```python
from lss4py import (
    EventLogBindingsIR,
    MetricBindingsIR,
    ProcessModelIR,
    ProcessStepIR,
    lead_time,
    load_event_log,
)

events = load_event_log(
    "process-events.csv",
    case_id_column="case",
    step_id_column="activity",
    started_at_column="start_time",
    completed_at_column="end_time",
)

process = ProcessModelIR(
    name="Client intake",
    steps=[
        ProcessStepIR(id="review", name="Review"),
        ProcessStepIR(id="approve", name="Approve"),
    ],
    bindings=MetricBindingsIR(
        event_log=EventLogBindingsIR(
            case_id_column="case_id",
            step_id_column="step_id",
            started_at_column="started_at",
            completed_at_column="completed_at",
        )
    ),
)

case_lead_time = lead_time(events, process_model=process, unit="hours")
```

## API Summary

### Basic Process Metrics

- `lead_time(data, ..., process_model=None)` returns per-row elapsed time from start to end timestamps.
- `wait_time(data, ..., process_model=None)` returns per-row lead time minus active cycle time.
- `process_cycle_efficiency(data, ..., process_model=None)` returns per-row value-add time divided by lead time.
- `takt_time(available_time=..., customer_demand=...)` returns a scalar pace target.

### Yield Helpers

- `created_to_booked_yield(data, ..., process_model=None)` returns first-stage conversion yield.
- `booked_to_completed_yield(data, ..., process_model=None)` returns second-stage conversion yield.
- `rolled_yield(data, ..., process_model=None)` returns end-to-end rolled yield.

See the [defect/rework yield guide](docs/defect-yield.md) for the separate
`process_yield` counting contract, denominator definitions, R mapping, and example.

### Process Model IR

- `ProcessModelIR` is the top-level FLO-compatible process model contract.
- `ProcessStepIR` defines step ids, names, cycle-time columns, and value classification.
- `ProcessEdgeIR` defines sequence, parallel split, parallel join, and rework edges.
- `MetricBindingsIR` groups lead-time and stage-column bindings.
- `MetricSemanticsIR` defines process-metric interpretation defaults such as parallel timing.
- `EventLogBindingsIR` defines the case, step, start, and end columns for event-log-aware metrics.

### Event-Log Contracts And Helpers

- `EventStream` represents single-timestamp activity observations used by discovery helpers.
- `EventLog` remains a pre-1.0 compatibility alias for `EventStream`.
- `IntervalEventLog` wraps a validated canonical Polars interval frame.
- `load_event_log(path, ...)` loads and validates an interval-event CSV into that contract.
- `EventLogCSVAdapter` exposes both the normalized interval log and its `AdapterSchema`.
- `validate_event_log(event_log)` returns machine-readable warnings for empty logs or missing required event fields.
- `map_process(event_log)` returns discovered activity nodes and transition counts from observed event order.

### Topology-Aware Event-Log Metrics

- event-log-aware `lead_time` uses per-case event boundaries from observed rows.
- repeated step occurrences require explicit rework edges in the process model.
- overlapping step intervals require explicit parallel edges in the process model.

## What Is Not Stable Yet

These areas are not part of the stable book-facing API today:

- full capability studies and within-subgroup variation
- SPC reporting
- simulation workflows
- bottleneck workflows
- before/after comparison workflows
- reporting bundles
- branch-aware event-log wait time and process-cycle efficiency
- automatic `.flo` parsing inside `lss4py`

The IR and metric engine support validated, per-case lead time from interval-event
logs. Broader branch-aware calculations are still future work.


## Development Status

This repository is in active pre-1.0 development.

The Yellow Belt metric surface above is the current stable target.

Other modules and ideas in the repository should be treated as experimental, internal, or future work unless they are explicitly listed in the stable surface.

## Validation

The [numerical-reference catalog](docs/reference-fixtures.md) checks current methods
against NIST-certified and independently derived expected values. R SixSigma
Cp/Cpk estimates, intervals, and specification Z distances now pass R baselines; broader
R parity remains future work. See [capability indices](docs/capability-indices.md).

Optional [R reference tooling](tools/r-reference/README.md) has its own dependency
lock and CI workflow. Install R 4.6.1 separately, then run
`Rscript --vanilla tools/r-reference/bootstrap.R` and
`Rscript --vanilla tools/r-reference/verify.R`. Ordinary Python development and
tests use only the Python environment.

The repository is currently validated with:

- `uv lock --check`
- `uv sync --locked --group dev --extra storage`
- `uv run --locked ruff check .`
- `uv run --locked ruff format --check .`
- `uv run --locked pre-commit validate-config`
- `uv run --locked ty check`
- `uv run --locked import-linter lint --config lint_imports_config.ini`
- `uv run --locked --extra storage pytest --require-pyarrow --cov=src/lss4py --cov-fail-under=90`
- `uv run --locked vulture src tests --min-confidence 80`
- `uv run --locked pip-audit --desc`

Install both local hook stages with:

```bash
uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
```

The `pre-commit` stage runs locked Ruff lint/format on changed files. It does not
run the test suite; full tests run at pre-push and in CI.

The `pre-push` stage and CI run the full locked repository-wide gates.
Pre-push runs the suite once with coverage and requires the Arrow backend;
Ruff includes production-source security checks; CI and release builds additionally
require the dependency vulnerability audit.
Ruff and Vulture hooks use the project's locked tools rather than separate hook
environments. See [toolchain policy](docs/toolchain.md) for rule selection and
the distinct checks retained alongside Ruff.

CI enforces 90% statement coverage across the full package and runs
[installed-wheel end-to-end studies](e2e/README.md) outside the source tree.
These exercise CSV ingestion, timing/yield analyses, capability studies, JSON
exports, and failure scenarios in base and pandas-extra installations. Run them
locally with `uv run --locked python tools/check_wheel.py`.
CI and the release build also require the
[FLO ecosystem journey](docs/ecosystem-integration.md), using published FLO 0.4.2
and the candidate LSS4PY wheel. Run it with
`uv run --locked python tools/check_wheel.py --ecosystem`.
To verify an already built release artifact without rebuilding it, pass
`--wheel dist/lss4py-0.2.0-py3-none-any.whl`. Add `--artifacts-dir artifacts/ecosystem`
to retain per-installation JUnit reports, the tested wheel's SHA-256 and ecosystem
evidence. CI retains source JUnit/coverage XML and installed-wheel reports for 14 days.

## Roadmap

The governed [roadmap](docs/roadmap.md) targets a complete Yellow Belt MVP at
v0.3, Green Belt capability at v0.5, Black Belt capability at v0.7, and a
feature-frozen polish phase at v0.9 before the stable 1.0 contract.

See the [documentation index](docs/README.md) for user requirements, technical
requirements, ADRs, and governance conventions. R `SixSigma` coverage is tracked
separately in the [compatibility matrix](docs/sixsigma-compatibility.md).

## License

LSS4PY is available under the [MIT License](LICENSE.md).

See [CONTRIBUTING.md](CONTRIBUTING.md) to contribute and
[SECURITY.md](SECURITY.md) to report a vulnerability privately.

The White Belt [activity-to-order example](examples/white_belt/reconstruct.py)
now reconstructs all 39 pinned orders through public numeric contracts, retaining
load/pass/classification and correction evidence. See the
[reconstruction guide](docs/order-reconstruction.md) and saved
[audited bundle](examples/white_belt/reconstruction-bundle.json).
