# LSS4PY Architecture

**Document status:** Approved

**Last updated:** 2026-10-07

**Audience:** Maintainers, contributors, and auditors

LSS4PY is a process-aware analytical core. It combines observed process data with
an explicit process model and returns typed, reproducible analytical results. It is
not a general ETL system, document-production platform, or line-for-line wrapper
around R `SixSigma`.

## Runtime flow

```text
Source files ──▶ adapters ──▶ IntervalEventLog (canonical Polars)
                                      │
Eager pandas / Polars / PyArrow ──────┤
                                      ▼
ProcessModelIR ───────────────▶ public analysis functions
                                      │
                                      ▼
                              private _kernels
                                      │
                                      ▼
                         typed AnalyticalResult models
```

Polars is the concrete ingestion and interval-log materialization engine. Narwhals
is the compatibility boundary for supported eager analytical inputs. Numerical
primitives may use NumPy, SciPy, or statsmodels behind LSS4PY result contracts.

## Layers and contracts

### Public API

**Location:** `lss4py/__init__.py`

The package root is the supported import surface for calculations, core domain
types, the CSV interval-log loader, and stable workflows.

```python
from lss4py import IntervalEventLog, ProcessModelIR, lead_time, load_event_log
```

Internal module paths are not compatibility promises. Public functions may be
implemented in private modules and re-exported from the package root.

### Domain contracts

**Location:** `lss4py/domain/`

The domain layer owns process topology, metric bindings, analytical results, and
the two distinct observed-event concepts:

- `EventStream` contains single-timestamp observations used by lightweight
  discovery helpers such as `map_process`.
- `IntervalEventLog` contains activity intervals backed by a canonical eager
  Polars frame with `case_id`, `step_id`, `started_at`, and `completed_at`.
- `EventLog` is a pre-1.0 compatibility alias for `EventStream` and should not be
  used in new code.

The domain layer does not import adapters, kernels, workflows, reporting, the CLI,
or observability modules.

### Adapters

**Location:** `lss4py/adapters/`

Adapters own source-specific I/O and normalize data before analysis. Core event-log
adapters return an `IntervalEventLog` plus `AdapterSchema`; they do not implement
statistical calculations or select analytical methods.

The current implementation supports CSV interval logs. A future private registry
may route OCEL, XES, database, or telemetry sources without changing kernel APIs.

### Private kernels

**Location:** `lss4py/_kernels/`

Private kernels own calculations, formula validation, and construction of typed
results. They may depend on domain contracts and shared private normalization
helpers, but never on adapters, workflows, reporting, observability, or the CLI.

There is no separate `analytics` layer. New analytical methods belong in a
capability-oriented `_kernels` module and are exposed deliberately from
`lss4py/__init__.py` when their contracts are ready.

### Shared interval-log normalization

**Location:** `lss4py/_event_log.py`

This private module converts supported eager inputs into the canonical interval
shape and validates identifiers, timestamps, durations, declared steps, rework,
and parallel overlaps. It is shared by adapters and private kernels.

### Workflows

**Location:** `lss4py/workflows/`

Workflows orchestrate public domain operations. They do not own numerical formulas
and do not import adapters or private kernels. `map_process` is the only currently
supported workflow; other workflow modules remain experimental placeholders.

### Reporting, observability, and CLI

These modules remain experimental. Calculations must work without plotting or
document-generation dependencies. Reporting consumes typed results rather than
reaching into adapters or workflows. The CLI consumes the public API only.

## Dependency rules

| Source layer | May depend on | Must not depend on |
| --- | --- | --- |
| Package root | Domain, adapters, private kernels, supported workflows | Private implementation details outside deliberate re-exports |
| Domain | External foundational libraries | Any other LSS4PY layer |
| Adapters | Domain, errors, private normalization | Private kernels, workflows, reporting |
| Private kernels | Domain, errors, private normalization | Adapters, workflows, reporting, observability, CLI |
| Workflows | Domain and other public contracts | Adapters and private kernels |
| Reporting | Domain result contracts | Adapters and workflows |
| CLI | Package-root public API | Adapters and private kernels |

`lint_imports_config.ini` enforces the corresponding forbidden-import contracts.

## Backend support policy

- Core file adapters materialize eager Polars frames.
- Public tabular analyses accept governed eager inputs through Narwhals.
- pandas and Polars require parity tests for every claimed tabular method.
- PyArrow support is provisional until the same contract suite covers it.
- Lazy, streaming, and distributed inputs are out of scope until a separate ADR
  defines explicit collection and execution semantics.
- Public analytical results use LSS4PY types with explicit values, keys, units,
  assumptions, warnings, and provenance rather than backend-specific indexes.

## Adding a capability

1. Define or extend the typed result and domain contracts.
2. Add the implementation to an appropriate private `_kernels` module.
3. Test valid inputs, invalid inputs, numerical references, and backend parity.
4. Re-export the supported function from `lss4py/__init__.py`.
5. Update requirements, compatibility claims, examples, and the roadmap.

Belt levels describe suitability and practitioner progression. They do not determine
module names or create separate Yellow, Green, or Black Belt implementation trees.

## Current and planned boundaries

| Area | Current contract | Planned extension |
| --- | --- | --- |
| File ingestion | CSV interval logs | General tabular, OCEL, XES, database, telemetry |
| Dataframes | Eager pandas and Polars tested; PyArrow provisional | Broader parity after contract tests |
| Timing | Row timing plus per-case interval-log lead time | Branch-aware event-log wait time and PCE |
| Yield | Binary stage and rolled funnel yield | Defect, rework, FTY, RTY, DPMO |
| Workflows | Lightweight process discovery | Bottleneck, comparison, simulation |
| Studies | None stable yet | Descriptive, capability, SPC, MSA, inference, DOE |

See [ADR-0019](adr/0019-reconcile-package-boundaries-and-event-log-contracts.md)
for the decision that reconciled the private-kernel, ingestion, and event-log
contracts.
