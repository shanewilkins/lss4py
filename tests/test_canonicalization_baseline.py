"""Characterize dataframe semantics before canonical Polars execution."""

import json
from pathlib import Path

import pandas as pd
import polars as pl
import pytest

from lss4py import ColumnRule, DataContract, normalize_data, validate_data
from tests.test_bundles import results

BASELINE = Path(__file__).parent / "fixtures" / "canonicalization" / "v0.2.1-neutral-results.json"


def _neutral(result):
    """Remove only computation time and source-backend identity."""
    payload = result.to_dict()
    payload["provenance"].pop("backend")
    payload["provenance"].pop("created_at")
    payload["provenance"]["parameters"].pop("backend_version", None)
    return payload


@pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
def test_complete_neutral_result_baseline(frame_factory, assert_equivalent):
    """Freeze every current result family before changing dataframe execution."""
    expected = json.loads(BASELINE.read_text())
    actual, _ = results(frame_factory)
    assert_equivalent(
        {name: _neutral(result) for name, result in actual.items()},
        expected,
    )


def test_pandas_nullable_extension_dtypes_are_preserved_without_mutation():
    """Characterize nullable extension scalars before canonical conversion."""
    frame = pd.DataFrame(
        {
            "integer": pd.Series([1, None, 3], dtype="Int64"),
            "number": pd.Series([1.5, None, 3.5], dtype="Float64"),
            "flag": pd.Series([True, None, False], dtype="boolean"),
            "label": pd.Series(["a", None, "c"], dtype="string"),
        }
    )
    original = frame.copy(deep=True)
    contract = DataContract(
        (
            ColumnRule("integer", "integer", nullable=True),
            ColumnRule("number", nullable=True),
            ColumnRule("flag", "boolean", nullable=True),
            ColumnRule("label", "string", nullable=True),
        )
    )
    report = validate_data(frame, contract=contract)
    assert report.valid
    assert [(profile.observed_kind, profile.missing_count) for profile in report.profiles] == [
        ("numeric", 1),
        ("numeric", 1),
        ("boolean", 1),
        ("string", 1),
    ]
    assert [(issue.code, issue.rows) for issue in report.warnings] == [
        ("MISSING_VALUES", (1,)),
        ("MISSING_VALUES", (1,)),
        ("MISSING_VALUES", (1,)),
        ("MISSING_VALUES", (1,)),
    ]
    prepared = normalize_data(frame, contract=contract).to_polars()
    assert prepared.dtypes == [pl.Int64, pl.Float64, pl.Boolean, pl.String]
    assert prepared.to_dict(as_series=False) == {
        "integer": [1, None, 3],
        "number": [1.5, None, 3.5],
        "flag": [True, None, False],
        "label": ["a", None, "c"],
    }
    pd.testing.assert_frame_equal(frame, original)


def test_pandas_categorical_values_retain_order_and_string_semantics():
    """Treat categorical labels as strings without category-order side effects."""
    frame = pd.DataFrame(
        {
            "label": pd.Series(
                ["b", "a", "b"],
                dtype=pd.CategoricalDtype(categories=["a", "b"], ordered=True),
            )
        }
    )
    original = frame.copy(deep=True)
    contract = DataContract((ColumnRule("label", "string"),))
    report = validate_data(frame, contract=contract)
    assert report.profiles[0].observed_kind == "string"
    assert [(issue.code, issue.rows) for issue in report.warnings] == [("DUPLICATE_ROWS", (2,))]
    prepared = normalize_data(frame, contract=contract).to_polars()
    assert prepared["label"].to_list() == ["b", "a", "b"]
    assert prepared["label"].dtype == pl.String
    pd.testing.assert_frame_equal(frame, original)


def test_pyarrow_dictionary_and_chunked_arrays_retain_values_and_positions():
    """Characterize Arrow chunk and dictionary decoding without mutating input."""
    pa = pytest.importorskip("pyarrow")
    labels = pa.chunked_array(
        [
            pa.array(["b", "a"]).dictionary_encode(),
            pa.array(["b"]).dictionary_encode(),
        ]
    )
    measurements = pa.chunked_array([[1.0, None], [3.0]])
    table = pa.table({"label": labels, "measurement": measurements})
    original = table.to_pylist()
    schema = table.schema
    contract = DataContract(
        (
            ColumnRule("label", "string"),
            ColumnRule("measurement", nullable=True),
        )
    )
    report = validate_data(table, contract=contract)
    assert report.valid
    assert [(profile.observed_kind, profile.missing_count) for profile in report.profiles] == [
        ("string", 0),
        ("numeric", 1),
    ]
    assert [(issue.code, issue.rows) for issue in report.warnings] == [("MISSING_VALUES", (1,))]
    prepared = normalize_data(table, contract=contract).to_polars()
    assert prepared.to_dict(as_series=False) == {
        "label": ["b", "a", "b"],
        "measurement": [1.0, None, 3.0],
    }
    assert table.to_pylist() == original
    assert table.schema == schema
    assert table.column("label").num_chunks == 2
    assert table.column("measurement").num_chunks == 2
