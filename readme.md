# LSS4PY

LSS4PY is a Python 3.14 Lean Six Sigma utility library for the current Yellow Belt slice.

It is focused on repeatable process metrics and yield calculations.

It is not yet a full SPC, capability, simulation, or deliverables platform.

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

It also includes a process-model IR for integrating FLO-derived process structure with observed tabular data:

- `ProcessModelIR`
- `ProcessStepIR`
- `ProcessEdgeIR`
- `MetricBindingsIR`
- `LeadTimeBindingIR`
- `StageBindingsIR`
- `MetricSemanticsIR`

Topology-aware event-log calculations are also part of the current stable surface for:

- `lead_time`
- `wait_time`
- `process_cycle_efficiency`

## Contract

LSS4PY works from two inputs.

The FLO side supplies a normalized process model IR.

The pandas side supplies observed process data.

LSS4PY calculates metrics from both.

The IR defines process structure and semantic bindings.

The DataFrame provides timestamps, stage outcomes, and measured times.

Explicit per-call metric arguments override IR bindings.

Parallel paths and rework loops are represented in the IR with explicit graph edges.

Event-log rows are the canonical observed data shape for process-model-aware metrics.

The default elapsed-time interpretation for parallel paths is `critical_path` semantics.

An alternate `sum_all_branches` interpretation is also supported for event-log-aware calculations.

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
import pandas as pd

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

data = pd.DataFrame(
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

### Process Model IR

- `ProcessModelIR` is the top-level FLO-compatible process model contract.
- `ProcessStepIR` defines step ids, names, cycle-time columns, and value classification.
- `ProcessEdgeIR` defines sequence, parallel split, parallel join, and rework edges.
- `MetricBindingsIR` groups lead-time and stage-column bindings.
- `MetricSemanticsIR` defines process-metric interpretation defaults such as parallel timing.

### Topology-Aware Event-Log Metrics

- event-log-aware `lead_time` uses per-case event boundaries from observed rows.
- event-log-aware `wait_time` supports branch-aware elapsed work from explicit parallel edges.
- event-log-aware `process_cycle_efficiency` supports value-add calculations across parallel and rework-aware event logs.
- repeated step occurrences require explicit rework edges in the process model.
- overlapping step intervals require explicit parallel edges in the process model.

## What Is Not Stable Yet

These areas are not part of the stable book-facing API today:

- capability analysis
- SPC reporting
- simulation workflows
- bottleneck workflows
- before/after comparison workflows
- reporting bundles
- automatic `.flo` parsing inside `lss4py`

The IR and metric engine now support stable topology-aware event-log calculations for the current Yellow Belt slice.

Broader graph-driven semantics outside that slice are still future work.

## Development Status

This repository is in active pre-1.0 development.

The Yellow Belt metric surface above is the current stable target.

Other modules and ideas in the repository should be treated as experimental, internal, or future work unless they are explicitly listed in the stable surface.

## Validation

The repository is currently validated with:

- `uv sync`
- `uv run pytest`
- `uv run ruff check .`
- `uv run pyright`

## Roadmap

Near-term work is focused on:

- README and example quality
- FLO IR contract documentation
- Yellow Belt worked examples and capstone support

## License

MIT.

See `LICENSE.md`.
