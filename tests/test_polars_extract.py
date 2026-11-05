"""Shared canonical Polars extraction semantics."""

from datetime import date

import numpy as np
import polars as pl
import pytest

from lss4py._kernels.descriptive import _group_value
from lss4py._polars_extract import (
    binary_stage_values,
    first_observed_groups,
    measurement_values,
    missing_mask,
    nonnegative_measurements,
    portable_key_values,
    require_columns,
    source_positions,
)
from lss4py.errors import ValidationError


@pytest.mark.parametrize(
    "values",
    [
        [1.0, None, 2.5, float("nan")],
        [1, 2, 3, 4],
        [None, None, None, None],
    ],
)
def test_measurement_values_retain_nullable_float_semantics(values):
    """Retain nullable float arrays and numerical values exactly."""
    frame = pl.DataFrame({"value": values})
    actual = measurement_values(frame, "value")
    np.testing.assert_equal(
        actual,
        np.asarray([np.nan if value is None else value for value in values], dtype=float),
    )


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (["1", "2"], "numeric measurements"),
        ([True, False], "numeric measurements"),
        ([1.0, float("inf")], "contains infinity"),
    ],
)
def test_measurement_values_retain_governed_failures(values, message):
    """Reject text, booleans, and infinity without conversion."""
    frame = pl.DataFrame({"value": values})
    with pytest.raises(ValidationError, match=message):
        measurement_values(frame, "value")


@pytest.mark.parametrize("values", [[0.0, 2.5], [-1.0, 2.0], [1.0, None]])
def test_nonnegative_measurements_retain_complete_domain(values):
    """Share completeness, finiteness, and nonnegative policy."""
    frame = pl.DataFrame({"value": values})
    if any(value is None or value < 0 for value in values):
        with pytest.raises(ValidationError):
            nonnegative_measurements(frame, "value")
    else:
        np.testing.assert_equal(nonnegative_measurements(frame, "value"), values)


@pytest.mark.parametrize(
    "values",
    [
        [True, False, True],
        [1, 0, 1],
        [1.0, 0.0, 1.0],
    ],
)
def test_binary_stage_values_retain_exact_binary_domain(values):
    """Accept booleans and exact numeric binary observations."""
    frame = pl.DataFrame({"stage": values})
    np.testing.assert_equal(binary_stage_values(frame, "stage"), np.asarray(values, dtype=np.int64))


@pytest.mark.parametrize("values", [[1, 0.5], [True, None], [1, None]])
def test_binary_stage_values_retain_invalid_domains(values):
    """Reject fractional and missing stage observations."""
    frame = pl.DataFrame({"stage": values}, strict=False)
    with pytest.raises(ValidationError):
        binary_stage_values(frame, "stage")


def test_missing_mask_combines_null_nan_and_object_missingness():
    """Use one portable mask for physical and object-backed measurements."""
    numeric = pl.Series("value", [1.0, None, float("nan")])
    objects = pl.Series("value", [1, None, float("nan"), "x"], dtype=pl.Object)
    assert missing_mask(numeric).tolist() == [False, True, True]
    assert missing_mask(objects).tolist() == [False, True, True, False]


def test_source_positions_apply_only_valid_boolean_masks():
    """Retain exact source positions after analytical missing-value selection."""
    frame = pl.DataFrame({"value": [1, 2, 3]})
    assert source_positions(frame).tolist() == [0, 1, 2]
    assert source_positions(frame, np.array([True, False, True])).tolist() == [0, 2]
    for invalid in (
        np.array([1, 0, 1]),
        np.array([[True, False, True]]),
        np.array([True]),
    ):
        with pytest.raises(ValidationError, match="boolean arrays"):
            source_positions(frame, invalid)


@pytest.mark.parametrize("key_column", [None, "key"])
def test_portable_keys_retain_identity_and_position_metadata(key_column):
    """Preserve keys and positional metadata without backend labels."""
    frame = pl.DataFrame({"key": ["b", "a"], "value": [1, 2]})
    actual = portable_key_values(frame, key_column)
    if key_column is None:
        assert actual == (None, {"row_positions": [0, 1], "key_column": None})
    else:
        np.testing.assert_equal(actual[0], np.asarray(["b", "a"], dtype=object))
        assert actual[1] == {"row_positions": [0, 1], "key_column": "key"}


@pytest.mark.parametrize("keys", [["a", "a"], ["", "b"], [1.0, float("inf")], [None, "a"]])
def test_portable_keys_retain_governed_failures(keys):
    """Reject duplicate, blank, nonfinite, and missing identities."""
    frame = pl.DataFrame({"key": keys}, strict=False)
    with pytest.raises(ValidationError):
        portable_key_values(frame, "key")


def test_first_observed_groups_match_legacy_order_and_positions():
    """Retain composite and missing groups in first-seen order."""
    frame = pl.DataFrame(
        {
            "team": ["B", "A", "B", None, None],
            "day": [
                date(2026, 1, 2),
                date(2026, 1, 1),
                date(2026, 1, 2),
                date(2026, 1, 1),
                date(2026, 1, 1),
            ],
        }
    )
    actual = first_observed_groups(frame, ("team", "day"), _group_value)
    assert [(keys, list(rows)) for keys, rows in actual] == [
        ({"team": "B", "day": "2026-01-02"}, [0, 2]),
        ({"team": "A", "day": "2026-01-01"}, [1]),
        ({"team": None, "day": "2026-01-01"}, [3, 4]),
    ]


def test_require_columns_reports_all_missing_in_requested_order():
    """Use the existing governed missing-column diagnostic."""
    with pytest.raises(ValidationError, match="Missing required columns: b, c"):
        require_columns(pl.DataFrame({"a": [1]}), "b", "a", "c")
