"""Tests for Polars-first CSV interval-event ingestion."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from lss4py import (
    EventLogBindingsIR,
    EventLogCSVAdapter,
    IntervalEventLog,
    MetricBindingsIR,
    ProcessEdgeIR,
    ProcessModelIR,
    ProcessStepIR,
    lead_time,
    load_event_log,
)
from lss4py.errors import AdapterError


def _write_csv(path: Path, text: str) -> Path:
    """Write one compact CSV test fixture."""
    path.write_text(text, encoding="utf-8")
    return path


def _process_model() -> ProcessModelIR:
    """Return a sequential process model using canonical interval columns."""
    return ProcessModelIR(
        name="Intake",
        steps=[
            ProcessStepIR(id="intake", name="Intake"),
            ProcessStepIR(id="review", name="Review"),
        ],
        edges=[ProcessEdgeIR(source_step_id="intake", target_step_id="review")],
        bindings=MetricBindingsIR(
            event_log=EventLogBindingsIR(
                case_id_column="case_id",
                step_id_column="step_id",
                started_at_column="started_at",
                completed_at_column="completed_at",
            )
        ),
    )


def test_load_event_log_returns_canonical_interval_log(tmp_path: Path) -> None:
    """CSV ingestion should preserve extras and normalize the analytical columns."""
    path = _write_csv(
        tmp_path / "events.csv",
        "case,activity,start,end,owner\n"
        "001,intake,2026-09-01T08:00:00,2026-09-01T09:00:00,Ada\n"
        "001,review,2026-09-01T09:30:00,2026-09-01T11:00:00,Lin\n",
    )

    result = load_event_log(
        path,
        case_id_column="case",
        step_id_column="activity",
        started_at_column="start",
        completed_at_column="end",
    )

    assert isinstance(result, IntervalEventLog)
    assert result.columns == ["case_id", "step_id", "started_at", "completed_at", "owner"]
    frame = result.to_polars()
    assert frame.get_column("case_id").to_list() == ["001", "001"]
    assert frame.schema["started_at"] == pl.Datetime("us")
    assert frame.schema["completed_at"] == pl.Datetime("us")
    assert frame is not result.frame
    assert result.to_polars(copy=False) is result.frame


def test_csv_adapter_reports_normalized_schema(tmp_path: Path) -> None:
    """AdapterSchema should describe the materialized Polars result."""
    path = _write_csv(
        tmp_path / "events.csv",
        "case_id,step_id,started_at,completed_at\n"
        "C1,intake,2026-09-01T08:00:00,2026-09-01T09:00:00\n",
    )

    event_log, schema = EventLogCSVAdapter(path).load()

    assert event_log.height == 1
    assert schema.row_count == 1
    assert schema.backend == "polars"
    assert schema.source_format == "csv"
    assert schema.key_columns == ["case_id", "step_id", "started_at", "completed_at"]
    assert schema.timestamp_columns == ["started_at", "completed_at"]
    assert schema.validate_required_fields(["case_id", "completed_at"]) == []
    assert len(schema.transformations) == 3


def test_interval_event_log_requires_canonical_polars_schema() -> None:
    """The public wrapper should reject ambiguous event shapes."""
    with pytest.raises(ValueError, match="missing canonical columns"):
        IntervalEventLog(pl.DataFrame({"case_id": ["C1"]}))


def test_loaded_event_log_feeds_per_case_lead_time(tmp_path: Path) -> None:
    """The ingestion slice should terminate in a governed analytical result."""
    path = _write_csv(
        tmp_path / "events.csv",
        "case_id,step_id,started_at,completed_at\n"
        "C2,intake,2026-09-01T08:00:00,2026-09-01T09:00:00\n"
        "C1,intake,2026-09-02T10:00:00,2026-09-02T11:00:00\n"
        "C2,review,2026-09-01T09:30:00,2026-09-01T11:00:00\n",
    )
    events = load_event_log(path)

    result = lead_time(events, process_model=_process_model(), unit="hours")

    assert result.keys is not None
    assert result.keys.tolist() == ["C2", "C1"]
    assert result.values.tolist() == [3.0, 1.0]
    assert result.provenance.backend == "polars"
    assert result.provenance.parameters["data_shape"] == "interval_event_log"


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (
            "case_id,step_id,started_at\nC1,intake,2026-09-01T08:00:00\n",
            "missing required source columns: completed_at",
        ),
        (
            "case_id,step_id,started_at,completed_at\nC1,intake,not-a-time,2026-09-01T09:00:00\n",
            "Could not normalize interval event-log values",
        ),
        (
            "case_id,step_id,started_at,completed_at\n"
            "C1,intake,2026-09-01T10:00:00,2026-09-01T09:00:00\n",
            "negative durations",
        ),
    ],
)
def test_csv_adapter_translates_invalid_source_data(
    tmp_path: Path,
    contents: str,
    message: str,
) -> None:
    """Source and normalization failures should use the adapter exception family."""
    path = _write_csv(tmp_path / "invalid.csv", contents)

    with pytest.raises(AdapterError, match=message):
        load_event_log(path)


def test_csv_adapter_rejects_missing_file(tmp_path: Path) -> None:
    """A missing source should produce an actionable AdapterError."""
    missing = tmp_path / "missing.csv"

    with pytest.raises(AdapterError, match="does not exist or is not a file"):
        load_event_log(missing)


def test_csv_adapter_rejects_non_polars_materialization(tmp_path: Path) -> None:
    """Core ingestion should have one explicit materialization backend."""
    path = _write_csv(
        tmp_path / "events.csv",
        "case_id,step_id,started_at,completed_at\n"
        "C1,intake,2026-09-01T08:00:00,2026-09-01T09:00:00\n",
    )

    with pytest.raises(ValueError, match=r"materialize.*polars"):
        EventLogCSVAdapter(path).load(backend="pandas")
