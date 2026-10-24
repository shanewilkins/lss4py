"""Installed optional Arrow contracts; collected only in the storage-extra environment."""

import pyarrow as pa
import pytest

from lss4py import ValidationError, lead_time, select_analysis, wait_time


def test_arrow_iso_instants_and_typed_result_export():
    """Preserve offset/fractional ISO instants and Arrow identity outside the checkout."""
    frame = pa.table(
        {
            "s": ["2026-01-01T08:00:00+00:00"],
            "e": ["2026-01-01T08:00:01.250000+00:00"],
            "id": ["001"],
        }
    )
    result = lead_time(frame, start_column="s", end_column="e", unit="seconds", key_column="id")
    assert result.values.tolist() == [1.25]
    assert result.to_frame("pyarrow")["key"].to_pylist() == ["001"]
    assert result.provenance.backend == "pyarrow"


def test_arrow_rejects_negative_operands_and_preserves_common_units():
    """Use the same strict timing domain in the installed optional backend."""
    with pytest.raises(ValidationError):
        wait_time(pa.table({"l": [-1.0], "c": [-2.0]}), lead_time_column="l", cycle_time_column="c")
    result = wait_time(
        pa.table({"l": [10.0], "c": [4.0]}),
        lead_time_column="l",
        cycle_time_column="c",
        unit="minutes",
    )
    choice = select_analysis(
        "wait_time",
        reason="Measure the supplied residual",
        cohort="All",
        design_type="observational",
    )
    choice.record(result)
    assert result.unit == "minutes"
    assert result.metadata["analysis_selection"]["reason"] == choice.reason
