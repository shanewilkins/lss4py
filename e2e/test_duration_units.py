"""Installed duration preparation keeps the book's declared operating-time baseline."""

import json
from pathlib import Path

import pytest

from lss4py import convert_duration_columns, describe, process_cycle_efficiency


def test_installed_conversion_preserves_book_ratio_of_sums_and_unit_evidence(read_csv):
    """Convert real prepared durations without treating operating time as calendar time."""
    path = Path(__file__).parent / "fixtures/white_belt/order_summary.csv"
    data = read_csv(path)
    lead = "Operating L/T (min)"
    va = "VA time (min)"
    clock = "cumulative operating minutes; closed hours excluded"
    converted = convert_duration_columns(
        data, columns=[lead, va], source_unit="minutes", target_unit="hours", clock=clock
    )
    frame = converted.to_native()
    summary = describe(frame, column=lead, unit="hours")
    assert summary.measurement_sum == pytest.approx(25840.5 / 60)
    assert summary.count == 39
    pce = process_cycle_efficiency(
        frame,
        lead_time_column=lead,
        value_add_time_column=va,
        aggregation="cohort",
        case_id_column="Order ID",
        unit="hours",
        clock=clock,
        boundary="Drop-off through readiness notification",
        cohort="All 39 book orders",
        value_add_convention="Right-first-time work; staging RNVA",
    )
    assert pce.values.tolist() == pytest.approx([100 * 3535.3 / 25840.5])
    assert round(pce.values[0], 1) == 13.7
    pce.metadata["duration_conversion"] = converted.to_dict()
    payload = json.loads(pce.to_json())
    assert payload["metadata"]["duration_conversion"]["clock"] == clock
    assert payload["metadata"]["duration_conversion"]["calendar_conversion"] == "none"
    restored = convert_duration_columns(
        frame, columns=[lead, va], source_unit="hours", target_unit="minutes", clock=clock
    )
    assert describe(
        restored.to_native(), column=va, unit="minutes"
    ).measurement_sum == pytest.approx(3535.3)
