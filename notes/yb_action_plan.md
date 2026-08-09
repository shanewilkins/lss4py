# Yellow Belt Action Plan

This document tracks the shortest path from the current scaffold to an honest Yellow Belt-ready `lss4py` release.

It is intentionally operational.

## Current State

- The environment is now aligned on Python 3.14.
- `uv sync`, `uv run pytest`, `uv run ruff check .`, and `uv run pyright` all pass under the current configuration.
- The stable public surface has been narrowed to implemented behavior rather than placeholder modules.
- A first Yellow Belt metrics slice exists for `lead_time`, `wait_time`, `process_cycle_efficiency`, and `takt_time`.
- The three core yield helpers now exist alongside the first metrics slice.
- The README now matches the actual stable Yellow Belt surface and documents the stable versus non-stable boundary.
- Worked examples are still outstanding.

## Progress Snapshot

- Phase 1 is complete.
- Phase 2 is complete.
- Phase 3 is in progress.
- Phase 3.5 is complete.
- Phase 4 has started only through executable tests.

## Yellow Belt Release Goal

The package should support a narrow, stable Yellow Belt slice:

- basic process metrics,
- yield helpers,
- tidy tabular inputs,
- explicit stable versus experimental boundaries,
- one canonical worked example,
- and tests strong enough for the book to depend on the documented behavior.

## Phase 1: Environment Recovery

Status: complete.

1. Align `pyproject.toml`, `.python-version`, lint settings, type-check settings, and README setup instructions on one supported Python version.
2. Rebuild the environment with `uv sync`.
3. Make `uv run pytest`, `uv run ruff check .`, and `uv run pyright` pass or fail on real code issues rather than configuration mismatch.

Exit criteria:

- A fresh clone can install and run the baseline validation commands.
- CI and local development use the same Python target.

Completed outcome:

- The repository now targets Python 3.14 consistently.
- The lockfile and local environment were rebuilt successfully.
- Baseline validation is green.

## Phase 2: Scope Correction

Status: complete.

1. Reduce public claims in the README to the actual Yellow Belt target.
2. Mark non-YB capabilities as future or experimental.
3. Remove placeholder APIs from stable export paths.

Exit criteria:

- Top-level imports only expose behavior the book can rely on.
- No stable API path ends in `NotImplementedError`.

Completed outcome:

- Placeholder analytics and workflow modules are no longer exported as stable top-level behavior.
- The stable root import surface now points at implemented domain and Yellow Belt functions.
- The README now describes the actual stable Yellow Belt surface.
- The README now distinguishes stable functions from future or experimental work.

## Phase 3: Stable Yellow Belt API

Status: functionally complete for the initial YB target, with documentation still pending.

Define and support a minimal stable API for:

- `lead_time`
- `wait_time`
- `process_cycle_efficiency`
- `takt_time`
- `created_to_booked_yield`
- `booked_to_completed_yield`
- `rolled_yield`

Design constraints:

- Accept tidy pandas inputs.
- Keep column naming explicit.
- Return simple, inspectable results.
- Do not hide the underlying pandas logic.

Exit criteria:

- Function signatures are documented.
- Examples and tests cover the stable behavior.

Completed outcome:

- `lead_time`, `wait_time`, `process_cycle_efficiency`, and `takt_time` are implemented.
- `created_to_booked_yield`, `booked_to_completed_yield`, and `rolled_yield` are implemented.
- These functions are exported from the package root as the first stable Yellow Belt slice.
- Behavior tests cover both valid and invalid inputs for the implemented metrics and yield helpers.

Remaining work:

- Document the stable function signatures in the README or dedicated docs.

## Phase 4: Examples and Validation

Status: not complete.

1. Add one Riverside-style worked example.
2. Add one capstone-style notebook or script path.
3. Add behavior tests for formula correctness, invalid inputs, and edge cases.

Exit criteria:

- Each stable Yellow Belt function has a worked example in the repo.
- Each stable Yellow Belt function has executable tests.

Completed outcome:

- The first stable metrics slice has executable tests.
- The yield helpers also have direct executable tests.

Remaining work:

- No worked example exists yet.
- No capstone-style notebook or script exists yet.

Dependency note:

- Phase 4 can proceed with examples that use the current stable DataFrame-plus-bindings contract.
- Examples that claim topology-aware branch or rework-loop metric behavior depend on Phase 3.5.

## Phase 3.5: Topology-Aware Metric Engine

Status: complete.

Goal:

- make parallel-path and rework-loop structure operational in metric calculations, not just representable in the IR.

Scope:

1. Interpret `ProcessEdgeIR` graph topology during metric calculation.
2. Support branch-aware elapsed-time calculations using the configured metric semantics.
3. Support rework-loop-aware calculations from event-log-shaped observed data.
4. Preserve the current explicit-column and binding-based metric paths for simpler use cases.

Exit criteria:

- event-log-aware metrics can use explicit graph edges for parallel paths.
- event-log-aware metrics can use explicit graph edges for rework loops.
- tests cover both topology-aware and non-topology-aware paths.

Completed outcome:

- event-log-aware `lead_time`, `wait_time`, and `process_cycle_efficiency` paths are implemented.
- parallel-path calculations support `critical_path` and `sum_all_branches` semantics.
- repeated-step validation now respects explicit rework edges.
- overlapping event validation now requires explicit parallel edges.
- tests cover topology-aware and non-topology-aware paths.

Non-goals:

- `.flo` parsing inside `lss4py`
- heuristic process discovery from observed data
- advanced simulation or optimization semantics

## Immediate Work Queue

1. Add one worked example that uses the stable metrics, yield helpers, and FLO IR bindings.
2. Add one capstone-style notebook or script path.
3. Expand worked examples to include topology-aware event-log cases.

## Current Decision

Use Python 3.14 as the working baseline for ongoing development.
The project horizon is long enough that targeting the current major Python release is the better default.

## FLO IR v1 Decisions

- `lss4py` will not parse `.flo` source directly.
- FLO is responsible for producing a normalized process model IR.
- `lss4py` will consume that IR together with a pandas DataFrame.
- The process model IR defines process structure and metric bindings.
- The DataFrame provides observed process data.
- Explicit per-call metric arguments override IR bindings.
- Parallel paths are in scope for IR v1.
- Rework loops are in scope for IR v1.
- Parallel paths and rework loops will be represented with explicit graph edges.
- Event-log rows are the canonical observed data shape for process-model-aware metrics.
- Elapsed-time metrics will default to a critical-path interpretation for parallel paths.
- Additive branch-work interpretations may be added later, but they are not the default contract.
- Automatic discovery or inference of process bindings from observed data remains out of scope.
