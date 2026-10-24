# Ingesting the White Belt simulation sources

The current simulation exports can now be loaded through public lss4py adapters.
The [captured ingestion manifest](assessments/white-belt-ingestion.json) records
actual source hashes, schemas, row counts, contracts, clock declarations,
transformations and validation findings for all 13 selected files.

| Source | Rows | Observation shape |
| --- | ---: | --- |
| `washnfold_event_log.csv` | 330 | Four-endpoint numeric activity records |
| `washnfold_representative_current_lifecycle_log.csv` | 1632 | Single-time numeric lifecycle events |
| `washnfold_learner_order_summary.csv` | 39 | Prepared learner order measurements |
| `washnfold_representative_activity_summary.csv` | 8 | Aggregate activity summaries |
| `washnfold_representative_order_metrics.csv` | 39 | Full-precision simulation order metrics |
| `washnfold_replication_metrics.csv` | 400 | Scenario/run observations |
| `washnfold_replication_summary.csv` | 100 | Scenario/metric summaries |
| `washnfold_paired_scenario_comparison.csv` | 33 | Supplied scenario comparisons |
| `washnfold_capacity_summary.csv` | 4 | Supplied capacity estimates |
| `washnfold_simulation_parameters.csv` | 26 | Parameter/value declarations |
| `washnfold_representative_run.csv` | 1 | Representative-run selection |
| `washnfold_calendar_year_metrics.csv` | 208 | Calendar-year simulation results |
| `washnfold_baseline_readout.csv` | 13 | Completed baseline readout |

The source selection follows the book data README's current exports, plus its
calendar-year output and derived baseline readout. Historical batch/pull and
combined Stage and notify files are outside this selection. Each table retains
its own grain; importing aggregate or scenario rows does not turn them into
individual customer orders or recompute their estimates. These are synthetic
simulation sources. Their supplied precision is preserved; the learner summaries
remain explicitly rounded source observations.

## Numeric activity and lifecycle logs

```python
from lss4py import NumericLogContract, load_numeric_event_log

contract = NumericLogContract(
    case_id_column="Order ID",
    load_id_column="Load ID",
    activity_column="Activity Name",
    pass_column="Pass",
    time_columns=(
        "Queue Entry (elapsed min)",
        "Setup Start (elapsed min)",
        "Work Start (elapsed min)",
        "Work End (elapsed min)",
    ),
    unit="minutes",
    clock="cumulative operating minutes from 07:00; closed hours excluded",
    boundary="Drop-off queue entry through final readiness notification",
)
activities = load_numeric_event_log("washnfold_event_log.csv", contract=contract)
observations = activities.to_polars()
```

`NumericEventLog` is a validated eager Polars observation model. It preserves
original column names, rows and extra fields. `NumericLogContract` identifies the
case, activity, pass/occurrence, optional child load, ordered time fields, unit,
clock and boundary. Additional `ColumnRule` declarations type and validate other
fields. The original source hash and loading transformations are retained in
metadata. `NumericEventLogCSVAdapter.load()` also returns an `AdapterSchema` with
the complete validation report and source evidence.

For single-time lifecycle events, bind one `time_columns` entry and a
`lifecycle_column`. Use `scope_columns` for scenario and simulation-run identity.
Scope and case identities are strings, preserving values such as `001`; the
book profile deliberately reads run IDs as string identity components on this
path. Occurrence/pass numbers remain integers. The full identity includes scope,
case, activity, pass, child load and lifecycle where declared.

Order-level null child IDs are preserved and participate in composite identity;
they do not collide with a child whose literal ID is `None`. Parallel child loads
and repeated passes remain separate records. Duplicate full identities, missing
required fields/endpoints, nonfinite/negative times, invalid pass numbers and
out-of-order activity endpoints fail explicitly with source-row findings.
Single-time events are not globally reordered: source order and simultaneous
events are preserved.

No numeric time is parsed as a calendar date, and no overnight time is introduced.
Calendar `IntervalEventLog` and its existing CSV adapter remain separate. Loading
numeric events does not pair lifecycle endpoints, collapse parallel loads,
reconstruct complete orders, derive activity durations, or select VA policy.
Those operations require explicit analytical contracts. The separate
[order reconstruction route](order-reconstruction.md) now accepts four-endpoint
activity records under the declared book policy. Single-time lifecycle pairing
remains separate.

## Other tabular sources

```python
from lss4py import CSVTabularAdapter, ColumnRule, DataContract

schema = DataContract(
    columns=(
        ColumnRule("Order ID", kind="string"),
        ColumnRule("Operating L/T (min)", minimum=0, unit="minutes"),
    ),
    key_columns=("Order ID",),
    duplicates="error",
)
orders, evidence = CSVTabularAdapter(
    "washnfold_learner_order_summary.csv",
    contract=schema,
    clock="cumulative operating minutes from 07:00; closed hours excluded",
).load()
```

`CSVTabularAdapter` reads one UTF-8 byte snapshot. Optional `expected_sha256`
checks that exact snapshot before parsing. Target-to-source `bindings` support
explicit source-column mappings. Numeric, integer, boolean and timestamp parsing
occur only for declared fields. Boolean tokens are `true`/`false` or
`True`/`False`; Y/N fields remain strings unless a separate explicit mapping is
chosen. Timestamp declarations use the existing governed ISO parsing policy.

The default null token is the empty CSV field. `NA`, `N/A`, whitespace and
leading-zero identities are not silently cleaned or inferred. Undeclared extras
remain strings, in source order. No source rows or extra columns are dropped.
Invalid headers, duplicate columns, ragged/blank records, mapping collisions,
missing fields, type/domain errors, duplicate declared keys, unreadable files,
invalid UTF-8 and checksum mismatches raise `AdapterError` or a declaration-time
`ValidationError`. Rows in findings are zero-based data-record positions.

`load_csv` is the convenience frame-only entry point; use the adapter's `load`
for its source hash, actual dtypes, units, bindings, transformations and validation
report. Shared mechanical data validation lives outside analytical kernels so
adapters can enforce the same `DataContract` without importing calculations.
The public `validate_data`/`normalize_data` entry points retain their behavior.

## Reproduce the live ingestion

The [source profiles](../examples/white_belt/simulation_sources.json) explicitly
declare the 13 filenames, shapes, types, keys, nullability and known time units.
They are inspectable example configuration, rather than a book-specific runtime
helper or automatic business-schema discovery. Pinned representative activity,
learner summary and baseline readout hashes protect the adopted fixture version.

```bash
uv run --locked python tools/ingest_book_simulation.py \
  --source ../modern-process-improvement/data/washnfold \
  --output /tmp/white-belt-ingestion.json
```

The script invokes the public adapters for each declared source and reports
validation evidence. It does not run the simulation, alter the sibling book,
merge cohorts, or silently fall back to historical exports. The prepared-data
[preview](book-preview.md) now uses the declared CSV adapter before its order-level
validation and calculations; its four displayed answers remain unchanged.

Validation on 2026-10-23: all 13 selected live sources loaded successfully. The
full suite with required PyArrow passed 1,512 tests, with six expected failures
and 95.71% coverage. Isolated installed-wheel workflows passed 22 base-install
tests and 31 pandas-extra tests, including numeric ingestion and the supplied
preview notebook. Static, docstring, complexity, dead-code, security and all eight
import-boundary checks passed.
