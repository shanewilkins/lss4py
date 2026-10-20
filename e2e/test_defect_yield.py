"""Installed-package defect/rework CSV study and strict JSON export."""

import json

import polars as pl
import pytest

from lss4py import ValidationError, process_yield


def test_defect_counting_csv_export(backend, fixtures, tmp_path):
    """Read original synthetic counts and export explicit opportunity and unit evidence."""
    path = fixtures / "defects.csv"
    if backend == "pandas":
        import pandas as pd

        frame = pd.read_csv(path)
    else:
        frame = pl.read_csv(path)
    result = process_yield(frame, opportunities=20, units=5, rework_column="rework")
    output = tmp_path / "defect-study.json"
    output.write_text(json.dumps(result.to_dict(), allow_nan=False))
    payload = json.loads(output.read_text())
    assert payload["result_type"] == "DefectYieldResult"
    assert payload["schema_version"] == "1.0"
    assert payload["defect_count"] == payload["rework_count"] == 3
    assert payload["opportunities"] == 20
    assert payload["units"] == 5
    assert payload["yield_fraction"] == 0.85
    assert payload["first_time_yield"] == 0.7
    assert payload["rolled_throughput_yield"] == pytest.approx(0.72675)
    assert payload["dpmo"] == 150000
    assert payload["defects_per_unit"] == 0.6
    assert payload["provenance"]["backend"] == backend
    with pytest.raises(ValidationError, match="cannot exceed"):
        process_yield(frame, opportunities=5, rework_column="rework")
