"""Release-blocking contract repairs through the installed base package."""

import polars as pl
import pytest

from lss4py import (
    AnalysisBundle,
    EventStream,
    ProcessMapResult,
    ValidationError,
    map_process,
    select_analysis,
    wait_time,
)


def test_installed_contract_repairs():
    """Retain typed discovery and explicit wait units without optional backends."""
    result = wait_time(
        pl.DataFrame({"id": ["001"], "l": [10.0], "c": [4.0]}),
        lead_time_column="l",
        cycle_time_column="c",
        key_column="id",
        unit="minutes",
    )
    assert result.values.tolist() == [6.0]
    assert result.to_frame()["key"].to_list() == ["001"]
    with pytest.raises(ValidationError):
        wait_time(
            pl.DataFrame({"l": [-1.0], "c": [-2.0]}), lead_time_column="l", cycle_time_column="c"
        )
    discovered = map_process(
        EventStream(
            events=[
                {"case_id": "01", "activity": "A", "timestamp": "2026-01-01T08:00:00Z"},
                {"case_id": "01", "activity": "B", "timestamp": "2026-01-01T09:00:00Z"},
            ]
        )
    )
    selection = select_analysis(
        "map_process",
        reason="Inspect observed transitions",
        cohort="One case",
        design_type="observational",
    )
    selection.record(discovered)
    bundle = AnalysisBundle.from_json(AnalysisBundle("Discovery", [discovered]).to_json())
    assert isinstance(bundle.results[0], ProcessMapResult)
    assert bundle.results[0]["edges"] == {"A": {"B": 1}}
