"""Installed CSV-to-validation-to-preparation-to-analysis journey."""

import json

import polars as pl

from lss4py import ColumnRule, DataContract, describe, normalize_data, validate_data


def test_quality_preparation_journey(backend, fixtures, tmp_path):
    """Prepare explicitly, retain source evidence, and analyze only the selected rows."""
    path = fixtures / "quality.csv"
    if backend == "pandas":
        import pandas as pd

        data = pd.read_csv(path)
    else:
        data = pl.read_csv(path)
    contract = DataContract(
        (
            ColumnRule("id", "string"),
            ColumnRule("hours", minimum=0, unit="hours", nullable=True),
            ColumnRule("started", "timestamp"),
            ColumnRule("completed", "timestamp"),
        ),
        key_columns=("id",),
        timestamp_order=(("started", "completed"),),
    )
    units = {"hours": "hours"}
    report = validate_data(data, contract=contract, source_units=units)
    assert report.valid
    assert {issue.code for issue in report.warnings} == {"MISSING_VALUES", "DUPLICATE_ROWS"}
    prepared = normalize_data(
        data, contract=contract, source_units=units, drop_missing=True, drop_duplicates=True
    )
    assert prepared.source_rows == (0, 3)
    summary = describe(prepared.to_polars(), column="hours", unit="hours")
    assert summary.count == 2 and summary.mean == 2
    output = tmp_path / "quality-study.json"
    output.write_text(
        json.dumps(
            {"preparation": prepared.to_dict(), "summary": summary.to_dict()}, allow_nan=False
        )
    )
    exported = json.loads(output.read_text())
    assert exported["preparation"]["before"]["backend"] == backend
    assert exported["preparation"]["after"]["valid"]
