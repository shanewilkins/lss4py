# Extending LSS4PY Data Ingestion

LSS4PY separates source-specific I/O from analytical functions. Core event-log
adapters materialize validated Polars `DataFrame` objects inside an
`IntervalEventLog`. Analytical functions accept that contract directly and may also
accept other governed eager dataframe inputs through Narwhals.

## Canonical interval-event shape

An interval event log has four required semantic columns:

| Canonical column | Meaning |
| --- | --- |
| `case_id` | Identifier for one process instance |
| `step_id` | Identifier for the observed process step |
| `started_at` | Activity-interval start timestamp |
| `completed_at` | Activity-interval completion timestamp |

`EventLogCSVAdapter` maps source column names into this shape, preserves additional
columns, parses timestamps, and rejects missing identifiers or negative durations.

```python
from lss4py import EventLogCSVAdapter, lead_time

adapter = EventLogCSVAdapter(
    "events.csv",
    case_id_column="case",
    step_id_column="activity",
    started_at_column="start_time",
    completed_at_column="end_time",
)
events, schema = adapter.load()
result = lead_time(events, process_model=process_model)
```

Use `load_event_log(...)` for the typed interval contract. Call
`events.to_polars()` when direct Polars operations are needed.

## Building an external adapter

External tabular adapters inherit from `TabularAdapter`; event-log adapters inherit
from `EventLogAdapter`. A tabular adapter returns a Polars frame and an
`AdapterSchema`. A calendar event-log adapter returns `IntervalEventLog` and
`AdapterSchema`; numeric-clock adapters use the distinct `NumericEventLog` and
explicit activity/lifecycle bindings. Shared mechanical contract validation lives
outside kernels, so adapters do not import analytical implementations. See the
[numeric and tabular ingestion guide](simulation-ingestion.md).

```python
from typing import Literal

import polars as pl

from lss4py.adapters import AdapterSchema, TabularAdapter


class WarehouseAdapter(TabularAdapter):
    def schema(self) -> AdapterSchema:
        frame, schema = self.load()
        return schema

    def load(
        self,
        backend: Literal["polars"] = "polars",
    ) -> tuple[pl.DataFrame, AdapterSchema]:
        if backend != "polars":
            raise ValueError("WarehouseAdapter materializes Polars only")

        frame = read_warehouse_as_polars(self.source_reference)
        schema = AdapterSchema(
            column_names=frozenset(frame.columns),
            column_types={name: str(dtype) for name, dtype in frame.schema.items()},
            row_count=frame.height,
            backend="polars",
            source_format="warehouse",
        )
        return frame, schema
```

Translate source client and parsing failures into `AdapterError`. Use
`ValidationError` inside reusable normalization code, then translate it at the I/O
boundary. Do not import private analytical kernels or workflows from an adapter.

## Required adapter tests

Test at least:

- a valid source and its normalized column types;
- missing source and required-column errors;
- null, blank, malformed, and invalid-domain values;
- preservation of identifiers, timestamps, extra columns, and source row order;
- the `AdapterSchema` contents and declared transformations; and
- one end-to-end analytical result that matches the equivalent in-memory input.

Analytical methods still require pandas/Polars parity where governed. That parity
belongs to the analytical contract; it does not require file adapters to emit both
backends.

## Format registry boundary

ADR-0017 reserves a registry for routing future formats such as OCEL and XES. Do
not add format detection to analytical functions. A new format adapter should
normalize to the canonical Polars representation and then reuse the same validators
and calculations.

The registry itself is not yet a stable extension API. Until it is implemented,
external packages should expose their adapter class directly.
