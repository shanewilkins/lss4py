"""Shared public calculation contracts, plus provisional Arrow characterization."""

from copy import deepcopy

import pandas as pd
import polars as pl
import pytest

import lss4py
from lss4py import (
    LeadTimeBindingIR,
    MetricBindingsIR,
    ProcessModelIR,
    StageBindingsIR,
    ValidationError,
    describe,
    lead_time,
)

pytestmark = pytest.mark.parametrize(
    "backend",
    ["pandas", "pandas-indexed", "polars", "pyarrow"],
    indirect=True,
)

# Roles/parameters and hand-calculated outcomes, not cross-language references.
CASES = [
    ("lead_time", {"start_column": "start", "end_column": "end"}, {"values": [10, 5, 2]}),
    (
        "wait_time",
        {"lead_time_column": "lead", "cycle_time_column": "cycle"},
        {"values": [6, 4, 1]},
    ),
    (
        "process_cycle_efficiency",
        {"lead_time_column": "lead", "value_add_time_column": "value_add"},
        {"values": [30, 20, 25]},
    ),
    (
        "created_to_booked_yield",
        {"created_column": "created", "booked_column": "booked"},
        {"value": 200 / 3, "numerator": 2, "denominator": 3},
    ),
    (
        "booked_to_completed_yield",
        {"booked_column": "booked", "completed_column": "completed"},
        {"value": 50, "numerator": 1, "denominator": 2},
    ),
    (
        "rolled_yield",
        {"created_column": "created", "booked_column": "booked", "completed_column": "completed"},
        {"value": 100 / 3},
    ),
    ("describe", {"column": "lead", "unit": "hours"}, {"mean": 17 / 3, "count": 3}),
]


def _copy_frame(frame):
    """Snapshot mutable backends; Arrow tables are immutable."""
    if isinstance(frame, pd.DataFrame):
        return frame.copy(deep=True)
    return frame.clone() if isinstance(frame, pl.DataFrame) else frame


@pytest.mark.parametrize(("method", "parameters", "expected"), CASES, ids=[c[0] for c in CASES])
def test_public_calculation_contract(
    backend,
    frame_factory,
    measurement_records,
    neutral_payload,
    assert_equivalent,
    method,
    parameters,
    expected,
):
    """Check estimates, full serialization, provenance identity, and input preservation."""
    frame = frame_factory(measurement_records)
    original = _copy_frame(frame)
    function = getattr(lss4py, method)
    result = function(frame, **parameters)
    reference = function(pl.DataFrame(measurement_records), **parameters)
    assert result.provenance.backend == ("pandas" if backend.startswith("pandas") else backend)
    assert_equivalent(neutral_payload(result), neutral_payload(reference))
    for field, value in expected.items():
        assert result.to_dict()[field] == pytest.approx(value)
    assert frame.equals(original)
    if method in {"lead_time", "wait_time", "process_cycle_efficiency"}:
        assert result.keys is None  # Row results use positions, never a pandas index.


def test_grouped_descriptive_contract(backend, frame_factory, neutral_payload, assert_equivalent):
    """Retain missing measurements and first-observed group order across backends."""
    records = {"team": ["B", "A", "B", None, None], "x": [2.0, 4.0, 6.0, None, 10.0]}
    result = describe(frame_factory(records), column="x", group_by="team")
    reference = describe(pl.DataFrame(records), column="x", group_by="team")
    assert [entry.group_keys for entry in result] == [{"team": "B"}, {"team": "A"}, {"team": None}]
    assert result[-1].missing == 1
    assert_equivalent(neutral_payload(result), neutral_payload(reference))


def test_interval_case_identity(
    backend,
    frame_factory,
    interval_records,
    interval_process_model,
    neutral_payload,
    assert_equivalent,
):
    """Explicit case keys follow first occurrence, independently of pandas labels."""
    frame = frame_factory(interval_records)
    original = _copy_frame(frame)
    result = lead_time(frame, process_model=interval_process_model)
    reference = lead_time(pl.DataFrame(interval_records), process_model=interval_process_model)
    assert result.keys is not None
    assert result.keys.tolist() == ["C2", "C1"]
    assert result.values.tolist() == [3, 2]
    assert result.provenance.backend == ("pandas" if backend.startswith("pandas") else backend)
    assert_equivalent(neutral_payload(result), neutral_payload(reference))
    assert frame.equals(original)


def test_explicit_arguments_override_process_bindings(backend, frame_factory, measurement_records):
    """Binding resolution is backend-neutral and explicit arguments take precedence."""
    model = ProcessModelIR(
        name="Bindings",
        bindings=MetricBindingsIR(
            lead_time=LeadTimeBindingIR(start_column="absent_start", end_column="absent_end"),
            stages=StageBindingsIR(created="absent_created", booked="absent_booked"),
        ),
    )
    frame = frame_factory(measurement_records)
    assert lead_time(
        frame, start_column="start", end_column="end", process_model=model
    ).values.tolist() == [10, 5, 2]
    result = lss4py.created_to_booked_yield(
        frame,
        created_column="created",
        booked_column="booked",
        process_model=model,
    )
    assert result.value == pytest.approx(200 / 3)


@pytest.mark.parametrize(("method", "parameters", "expected"), CASES, ids=[c[0] for c in CASES])
def test_missing_required_field_is_a_governed_error(
    backend,
    frame_factory,
    method,
    parameters,
    expected,
):
    """Every tabular calculation rejects absent fields through ValidationError."""
    with pytest.raises(ValidationError, match="Missing required columns"):
        getattr(lss4py, method)(frame_factory({"unrelated": [1]}), **parameters)


@pytest.mark.parametrize(("method", "parameters", "expected"), CASES, ids=[c[0] for c in CASES])
def test_invalid_domain_is_consistent(
    backend,
    frame_factory,
    measurement_records,
    method,
    parameters,
    expected,
):
    """Reject a concrete invalid domain for each public tabular method."""
    records = deepcopy(measurement_records)
    if method == "lead_time":
        records["end"][0] = "2026-01-01T07:00:00"
    elif method == "wait_time":
        records["cycle"][0] = 11.0
    elif method == "process_cycle_efficiency":
        records["lead"][0] = 0.0
    elif method == "describe":
        records["lead"][0] = float("inf")
    else:
        records["booked"][0] = 2
    with pytest.raises(ValidationError):
        getattr(lss4py, method)(frame_factory(records), **parameters)


@pytest.mark.parametrize("native_timestamps", [False, True], ids=["iso-strings", "datetimes"])
def test_timestamp_precision_and_timezone(backend, frame_factory, native_timestamps, request):
    """Preserve subsecond elapsed time and timezone-aware instants across backends."""
    from datetime import UTC, datetime, timedelta

    start = datetime(2026, 1, 1, 8, tzinfo=UTC)
    end = start + timedelta(seconds=1, microseconds=250000)
    if not native_timestamps:
        start, end = start.isoformat(), end.isoformat()
    result = lead_time(
        frame_factory({"start": [start], "end": [end]}),
        start_column="start",
        end_column="end",
        unit="seconds",
    )
    assert result.values.tolist() == [1.25]


def test_invalid_timestamp_uses_governed_error(frame_factory):
    """Translate backend parsing errors without mutating source observations."""
    frame = frame_factory({"start": ["not-a-timestamp"], "end": ["2026-01-01T11:00:00"]})
    with pytest.raises(ValidationError, match="Column 'start' contains invalid timestamps"):
        lead_time(frame, start_column="start", end_column="end")


@pytest.mark.parametrize(
    ("column", "invalid"),
    [
        ("case_id", None),
        ("step_id", None),
        ("started_at", None),
        ("completed_at", None),
        ("case_id", ""),
        ("step_id", "unknown"),
    ],
)
def test_interval_validation_is_backend_neutral(
    frame_factory,
    interval_records,
    interval_process_model,
    column,
    invalid,
):
    """Missing identifiers/timestamps and unknown steps are blocking event-log errors."""
    records = deepcopy(interval_records)
    records[column][0] = invalid
    with pytest.raises(ValidationError):
        lead_time(frame_factory(records), process_model=interval_process_model)
