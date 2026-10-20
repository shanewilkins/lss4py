"""Validated and immutable data-quality policy contracts."""

import json
from dataclasses import FrozenInstanceError
from typing import Any, cast

import pandas as pd
import pytest

from lss4py import ColumnRule, DataContract, ValidationError, normalize_data, validate_data


@pytest.mark.parametrize(
    "options",
    [
        {"name": ""},
        {"name": None},
        {"kind": "guess"},
        {"nullable": "yes"},
        {"unit": ""},
        {"minimum": True},
        {"maximum": float("inf")},
        {"minimum": 2, "maximum": 1},
        {"kind": "string", "minimum": 0},
        {"minimum": "1"},
        {"minimum": 10**400},
    ],
)
def test_invalid_column_rule(options: dict[str, Any]):
    """Reject ambiguous labels, domains, unit declarations and coercion policies."""
    with pytest.raises(ValidationError):
        ColumnRule(**cast(Any, {"name": "x", **options}))


@pytest.mark.parametrize(
    "options",
    [
        {"columns": []},
        {"columns": ["x"]},
        {"columns": None},
        {"columns": [ColumnRule("x"), ColumnRule("x")]},
        {"key_columns": ["missing"]},
        {"key_columns": ["x", "x"]},
        {"key_columns": "x"},
        {"duplicates": "drop"},
        {"schema_version": "2.0"},
        {"timestamp_order": [("x", "x")]},
        {"timestamp_order": ["xy"]},
        {"timestamp_order": [("x",)]},
    ],
)
def test_invalid_data_contract(options: dict[str, Any]):
    """Reject incomplete schema references, unknown versions and implicit drop policies."""
    with pytest.raises(ValidationError):
        DataContract(**cast(Any, {"columns": [ColumnRule("x")], **options}))


def test_contract_is_detached_and_roundtrips():
    """Serialize the exact policy and detach mutable caller sequences."""
    columns = [ColumnRule("x", minimum=0, unit="hours")]
    keys = ["x"]
    contract = DataContract(cast(Any, columns), key_columns=cast(Any, keys))
    columns.clear()
    keys.clear()
    payload = json.loads(json.dumps(contract.to_dict(), allow_nan=False))
    assert DataContract.from_dict(payload) == contract
    payload["columns"][0]["unit"] = "minutes"
    assert contract.columns[0].unit == "hours"
    with pytest.raises(FrozenInstanceError):
        setattr(contract, "duplicates", "allow")  # noqa: B010


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"columns": [{"name": "x", "unexpected": 1}]},
        {"columns": [{"name": "x"}], "unknown": 1},
        {"columns": None},
        {"columns": [{"name": "x"}], "schema_version": "2"},
    ],
)
def test_invalid_serialized_policy(payload):
    """Malformed or incompatible policy exports produce package validation errors."""
    with pytest.raises(ValidationError):
        DataContract.from_dict(payload)


@pytest.mark.parametrize("columns", [["x", "x"], [0, 1]])
def test_ambiguous_observed_schema(columns):
    """Structural schema failures use domain errors rather than ambiguous column selection."""
    frame = pd.DataFrame([[1, 2]], columns=columns)
    with pytest.raises(ValidationError, match="column names"):
        validate_data(frame, contract=DataContract((ColumnRule("x"),)))


def test_unmaterializable_integer_is_explicit():
    """Inspection preserves exact integers; preparation reports canonical storage limits."""
    frame = pd.DataFrame({"x": [10**100]}, dtype=object)
    contract = DataContract((ColumnRule("x", "integer"),))
    assert validate_data(frame, contract=contract).valid
    with pytest.raises(ValidationError, match="canonical Polars"):
        normalize_data(frame, contract=contract)


def test_contract_type_is_checked():
    """An invalid policy object cannot silently disable data-quality checks."""
    with pytest.raises(ValidationError, match="DataContract"):
        validate_data(pd.DataFrame({"x": [1]}), contract=cast(Any, None))
