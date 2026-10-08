"""Polars-first ingestion for interval event logs."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from lss4py._event_log import (
    CANONICAL_EVENT_LOG_BINDINGS,
    CANONICAL_EVENT_LOG_COLUMNS,
    normalize_interval_event_log,
)
from lss4py.adapters.contracts import AdapterSchema, EventLogAdapter
from lss4py.domain import IntervalEventLog
from lss4py.errors import AdapterError, ValidationError


class EventLogCSVAdapter(EventLogAdapter):
    """Load an interval event log from CSV into canonical Polars columns.

    The source may use custom column names. They are renamed to ``case_id``,
    ``step_id``, ``started_at``, and ``completed_at`` during normalization.
    Other source columns are preserved.
    """

    def __init__(
        self,
        source_reference: str | Path,
        *,
        case_id_column: str = "case_id",
        step_id_column: str = "step_id",
        started_at_column: str = "started_at",
        completed_at_column: str = "completed_at",
    ) -> None:
        """Configure a CSV interval-event source and its semantic columns."""
        super().__init__(str(source_reference))
        source_columns = (
            case_id_column,
            step_id_column,
            started_at_column,
            completed_at_column,
        )
        if len(set(source_columns)) != len(source_columns):
            raise ValueError("Event-log source column mappings must be distinct.")

        self._source_columns = dict(zip(CANONICAL_EVENT_LOG_COLUMNS, source_columns, strict=True))

    def schema(self) -> AdapterSchema:
        """Return the schema of the normalized interval log."""
        _, schema = self.load()
        return schema

    def load(
        self,
        backend: str = "polars",
    ) -> tuple[IntervalEventLog, AdapterSchema]:
        """Read, normalize, and validate the configured CSV file."""
        if backend != "polars":
            raise ValueError("Core event-log adapters materialize the 'polars' backend only.")

        source_path = Path(self.source_reference)
        if not source_path.is_file():
            raise AdapterError(f"Event-log CSV does not exist or is not a file: {source_path}")

        self._validate_header(source_path)
        normalized = self._read_and_normalize(source_path)
        event_log = IntervalEventLog(normalized, metadata={"source": str(source_path)})
        schema = AdapterSchema(
            column_names=frozenset(normalized.columns),
            column_types={name: str(dtype) for name, dtype in normalized.schema.items()},
            row_count=normalized.height,
            key_columns=["case_id", "step_id", "started_at", "completed_at"],
            timestamp_columns=["started_at", "completed_at"],
            source_format="csv",
            backend="polars",
            transformations=(
                "renamed semantic columns to the canonical interval-event schema",
                "parsed started_at and completed_at as datetimes",
                "validated identifiers, timestamps, and nonnegative durations",
            ),
        )
        return event_log, schema

    def _validate_header(self, source_path: Path) -> None:
        """Reject CSV files that omit a configured semantic column."""
        try:
            header = pl.read_csv(source_path, n_rows=0, raise_if_empty=True, glob=False)
        except (OSError, pl.exceptions.PolarsError) as exc:
            raise AdapterError(f"Could not inspect event-log CSV '{source_path}': {exc}") from exc

        missing = [
            source_name
            for source_name in self._source_columns.values()
            if source_name not in header.columns
        ]
        if missing:
            raise AdapterError(
                "Event-log CSV is missing required source columns: " + ", ".join(missing)
            )

    def _read_and_normalize(self, source_path: Path) -> pl.DataFrame:
        """Read the CSV and apply canonical names, types, and validation."""
        schema_overrides = {source_name: pl.String for source_name in self._source_columns.values()}
        try:
            source = pl.read_csv(
                source_path,
                schema_overrides=schema_overrides,
                try_parse_dates=False,
                raise_if_empty=True,
                glob=False,
            )
            normalized = source.rename(
                {
                    source_name: canonical_name
                    for canonical_name, source_name in self._source_columns.items()
                    if source_name != canonical_name
                }
            )
            normalized = normalize_interval_event_log(
                normalized,
                bindings=CANONICAL_EVENT_LOG_BINDINGS,
            )
        except ValidationError as exc:
            raise AdapterError(f"Invalid event-log CSV '{source_path}': {exc}") from exc
        except (OSError, pl.exceptions.PolarsError) as exc:
            raise AdapterError(f"Could not load event-log CSV '{source_path}': {exc}") from exc
        return normalized


def load_event_log(
    path: str | Path,
    *,
    case_id_column: str = "case_id",
    step_id_column: str = "step_id",
    started_at_column: str = "started_at",
    completed_at_column: str = "completed_at",
) -> IntervalEventLog:
    """Load a CSV interval log as a validated canonical interval-event log."""
    adapter = EventLogCSVAdapter(
        path,
        case_id_column=case_id_column,
        step_id_column=step_id_column,
        started_at_column=started_at_column,
        completed_at_column=completed_at_column,
    )
    event_log, _ = adapter.load()
    return event_log
