# LSS4PY Architecture

**Document status:** Approved

**Last updated:** 2026-10-23

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

## Analytical ownership

[ADR-0020](adr/0020-delegate-numerical-algorithms-and-own-analytical-contracts.md) defines responsibility for
numerical reuse and analytical contracts. LSS4PY owns domain semantics, estimator
and exclusion policies, typed results, diagnostics, provenance, and interpretation.
Established scientific libraries supply numerical algorithms where their behavior
meets that contract; small auditable domain formulas may remain in private kernels.

Calculations can return typed results directly. Studies orchestrate public
calculations and diagnostics; optional presentation consumes those results.
R SixSigma parity concerns documented behavior and outcomes, with reference tests
and explicit differences. It does not mandate identical APIs, a second statistics
stack, or a separate raw-result/wrapper layer for every calculation.

[ADR-0021](adr/0021-reuse-flo-and-established-presentation-libraries.md) assigns
process and value-stream rendering to FLO through optional, explicit contract
translation. Statistical plots consume LSS4PY results through established plotting
libraries. Scientific algorithms are delegated after estimator/contract review;
fishbone renderer selection remains open. Core analytics require neither FLO nor
rendering dependencies. Modeled process timing and observed measurements retain
separate identities and provenance when integrated.

[ADR-0022](adr/0022-ecosystem-integration-contracts-and-journey-gates.md) defines
explicit versioned identity, source evidence and selection contracts and the two
journey gates. [ADR-0023](adr/0023-matplotlib-contract-with-seaborn-convenience.md)
defines native Matplotlib objects with optional Seaborn convenience.

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

### Analysis guidance

**Location:** `lss4py/guidance/`

Private kernels declare immutable suitability metadata through decorators. The
package root exposes `AnalysisSuitability`, `get_analysis`, and `get_candidates`.
Guidance queries match declared intent and return metadata without inspecting
data or executing methods. Guidance cannot import kernels or IO/orchestration
layers; domain contracts remain independent of guidance.

### Adapters

**Location:** `lss4py/adapters/`

Adapters own source-specific I/O and normalize data before analysis. Core event-log
adapters return an `IntervalEventLog` plus `AdapterSchema`; they do not implement
statistical calculations or select analytical methods.

The current implementation supports CSV interval logs. A future private registry
may route OCEL, XES, database, or telemetry sources without changing kernel APIs.

Declared tabular CSVs now use `CSVTabularAdapter`; numeric-clock activity and
lifecycle sources use `NumericEventLogCSVAdapter` and the distinct
`NumericEventLog`/`NumericLogContract` domain contract. Adapters share mechanical
schema inspection and normalization through `_data_quality`, outside analytical
kernels. `_frames` provides shared backend identity. Source order, extra columns,
source hashes and validation findings remain inspectable. Lifecycle pairing and
order reconstruction are separate analytical operations.

[ADR-0026](adr/0026-method-specific-input-contracts-and-ocel-interchange.md)
defines the planned ingestion boundary: validated inputs specific to each method.
Users supply structured observations and declare identities, units, clocks,
cohorts, boundaries, and aggregation/classification policies. Adapters handle
documented mapping, parsing, and validation; methods still enforce preconditions
for direct callers. Prepared measurements can enter analyses directly without
conversion to event logs.

The implemented IntervalEventLog is a calendar-datetime interval contract.
Numeric operating-time inputs need a distinct explicit clock contract; fabricated
timestamps are not a valid conversion. Future OCEL adapters preserve objects and
relationships, then use explicit analytical projection policies where a method
needs one case or interval population. OCEL support remains planned, and is not
required for prepared measurements or the book preview. Kernels do not load files
or invoke format adapters.

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
The initial `reporting.visualization.plot_timing` consumes a completed timing
result and returns native axes; its optional imports occur only when called.

### Ecosystem integration

**Location:** `lss4py/integration/`

The optional bridge accepts FLO 0.5.0's public JSON export and translates a bounded
supported projection into ProcessModelIR. It preserves declared step identities,
parallel/rework topology, source semantics and modeled metadata. It imports domain
contracts and private Pydantic exchange schemas, without FLO, kernels, adapters
or rendering. Pydantic is a direct base dependency so portable JSON validation
does not require the optional FLO producer. Schemas validate shapes without
serializing over the original snapshot. Versioned evidence
manifests capture completed timing/descriptive results and explicit study context;
restoration does not recalculate. The external reference workflow composes FLO and
LSS4PY public operations and keeps modeled diagrams and observed metrics separate.
See the [integration guide](ecosystem-integration.md) for supported semantics.

### Explicit unit preparation

**Location:** `lss4py/_units.py`, with `DurationConversion` in `domain/units.py`.

The public `convert_duration_columns` operation converts selected eager duration
columns before analysis. Its private lazy Pint registry owns physical factors;
caller application registries are neither consumed nor replaced. Native backend,
row order and non-selected columns are preserved. Portable evidence records the
explicit units, unchanged clock, factor, source positions and Pint version.
Existing numerical methods and normalization retain their unit behavior.
See [duration units](duration-units.md) and [ADR-0027](adr/0027-explicit-duration-conversion-and-private-pint-registry.md).

## Dependency rules

| Source layer | May depend on | Must not depend on |
| --- | --- | --- |
| Package root | Domain, adapters, private kernels, supported workflows | Private implementation details outside deliberate re-exports |
| Domain | External foundational libraries | Any other LSS4PY layer |
| Adapters | Domain, errors, private normalization | Private kernels, workflows, reporting, integration |
| Private kernels | Domain, errors, private normalization | Adapters, workflows, reporting, observability, CLI, integration |
| Workflows | Domain and other public contracts | Adapters and private kernels |
| Reporting | Domain result contracts, optional plotting libraries | Adapters, workflows, integration |
| Integration | Domain contracts, errors, portable JSON | Kernels, adapters, workflows, reporting, observability, CLI, guidance |
| CLI | Package-root public API | Adapters and private kernels |

`lint_imports_config.ini` enforces the corresponding forbidden-import contracts.

## Backend support policy

- Core file adapters materialize eager Polars frames.
- Public tabular analyses accept governed eager inputs through Narwhals.
- pandas and Polars require parity tests for every claimed tabular method.
- PyArrow passes the declared current eager contracts, including ISO/native timestamp precision. Unsupported shapes remain outside the accepted boundary.
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
| File ingestion | Calendar interval, declared tabular, and numeric activity/lifecycle CSVs | OCEL, XES, database, telemetry |
| Dataframes | Eager pandas, Polars and PyArrow tested | Additional shapes require explicit contract tests |
| Timing | Row timing plus per-case interval-log lead time | Branch-aware event-log wait time and PCE |
| Yield | Binary stage and rolled funnel yield | Defect, rework, FTY, RTY, DPMO |
| Workflows | Lightweight process discovery | Bottleneck, comparison, simulation |
| Studies | Typed numeric descriptive summaries, including grouping | Capability, SPC, MSA, inference, DOE |

See [ADR-0019](adr/0019-reconcile-package-boundaries-and-event-log-contracts.md)
for the decision that reconciled the private-kernel, ingestion, and event-log
contracts.
