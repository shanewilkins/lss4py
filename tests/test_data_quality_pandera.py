"""Differential evidence for canonical Polars/Pandera data-quality execution."""

import pandas as pd
import polars as pl

from lss4py import ColumnRule, DataContract, normalize_data, validate_data
from lss4py import _data_quality as implementation


def test_public_validation_sends_only_declared_polars_columns_to_pandera(monkeypatch):
    """Keep source provenance while executing structural checks on canonical Polars."""
    observed = {}
    original = implementation._validate_structural

    def capture(frame, contract, *, source_positions=None):
        observed["type"] = type(frame)
        observed["columns"] = frame.columns
        observed["positions"] = source_positions
        return original(frame, contract, source_positions=source_positions)

    monkeypatch.setattr(implementation, "_validate_structural", capture)
    source = pd.DataFrame(
        {"value": [1.0, 2.0], "ignored": ["not", "canonicalized"]},
        index=[17, 17],
    )
    report = validate_data(source, contract=DataContract((ColumnRule("value"),)))
    assert observed == {
        "type": pl.DataFrame,
        "columns": ["value"],
        "positions": (0, 1),
    }
    assert report.backend == "pandas"
    assert report.column_names == ("value", "ignored")
    assert report.row_count == 2


def test_mixed_pandas_object_values_keep_row_level_diagnostics():
    """Avoid conversion errors while retaining valid neighboring scalar identity."""
    source = pd.DataFrame({"value": pd.Series([1, True, "2", float("nan")], dtype=object)})
    contract = DataContract((ColumnRule("value", nullable=True),))
    report = validate_data(source, contract=contract)
    assert [(issue.code, issue.severity, issue.rows) for issue in report.issues] == [
        ("INVALID_TYPE", "error", (1, 2)),
        ("MISSING_VALUES", "warning", (3,)),
    ]
    assert report.profiles[0].observed_kind == "boolean|numeric|string"
    assert report.profiles[0].unique_count == 1
    assert report.profiles[0].invalid_count == 2


def test_normalization_still_returns_detached_polars_with_source_rows():
    """The validation migration does not change public preparation output."""
    source = pd.DataFrame({"value": pd.Series([1, 2.5, None], dtype=object)})
    source.index = [8, 8, -1]
    prepared = normalize_data(
        source,
        contract=DataContract((ColumnRule("value", nullable=True),)),
    )
    output = prepared.to_polars()
    assert output.schema == pl.Schema({"value": pl.Float64})
    assert output["value"].to_list() == [1.0, 2.5, None]
    assert prepared.source_rows == (0, 1, 2)
