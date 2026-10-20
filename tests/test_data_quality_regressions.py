"""Regression coverage for canonical precision and numeric materialization."""

from datetime import UTC, datetime

import pandas as pd
import polars as pl
import pytest

from lss4py import ColumnRule, DataContract, ValidationError, normalize_data, validate_data


def nanosecond_column(backend, timezone):
    """Build native nanosecond inputs without prematurely truncating their precision."""
    ticks = [100, 900, 1100]
    if backend.startswith("pandas"):
        return pd.to_datetime(ticks, unit="ns", utc=timezone is not None)
    if backend == "polars":
        return pl.Series(ticks).cast(pl.Datetime("ns", time_zone=timezone))
    import pyarrow as pa

    return pa.array(ticks, type=pa.timestamp("ns", tz=timezone))


def check_default_duplicate_policy(frame, rules):
    """Keep duplicates under warnings, and reject them under the blocking policy."""
    if rules.duplicates == "error":
        with pytest.raises(ValidationError, match="DUPLICATE_ROWS"):
            normalize_data(frame, contract=rules)
    else:
        retained = normalize_data(frame, contract=rules)
        assert retained.source_rows == (0, 1, 2)
        assert retained.after.issues == retained.before.issues


@pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
@pytest.mark.parametrize("timezone", [None, "UTC"])
@pytest.mark.parametrize("duplicates", ["warn", "error"])
def test_native_nanosecond_keys_use_canonical_precision(
    backend, frame_factory, timezone, duplicates
):
    """Inspect and deduplicate the same microsecond identities across native backends."""
    frame = frame_factory({"time": nanosecond_column(backend, timezone)})
    original = str(frame)
    rules = DataContract(
        (ColumnRule("time", "timestamp"),), key_columns=("time",), duplicates=duplicates
    )
    report = validate_data(frame, contract=rules)
    assert report.profiles[0].unique_count == 2
    assert [(issue.code, issue.rows) for issue in report.issues] == [("DUPLICATE_ROWS", (1,))]
    check_default_duplicate_policy(frame, rules)
    result = normalize_data(frame, contract=rules, drop_duplicates=True)
    assert result.source_rows == (0, 2)
    assert result.before == report
    assert result.after.valid and not result.after.issues
    zone = UTC if timezone else None
    assert result.to_polars()["time"].to_list() == [
        datetime(1970, 1, 1, tzinfo=zone),
        datetime(1970, 1, 1, microsecond=1, tzinfo=zone),
    ]
    assert str(frame) == original


def numeric_column(backend, source):
    """Keep mixed Python numeric objects in pandas and equivalent native numeric columns."""
    if backend.startswith("pandas"):
        return pd.Series(source, dtype=object)
    return [float(v) if v is not None else None for v in source]


@pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
@pytest.mark.parametrize("values", [[1, 2.5], [2.5, 1]])
@pytest.mark.parametrize("nullable", [False, True])
def test_mixed_numeric_values_materialize_in_either_order(backend, frame_factory, values, nullable):
    """Valid numeric objects normalize like native float columns without changing rows."""
    source = values + [None] if nullable else values
    frame = frame_factory({"x": numeric_column(backend, source)})
    original = str(frame)
    rules = DataContract((ColumnRule("x", nullable=nullable),))
    assert validate_data(frame, contract=rules).valid
    result = normalize_data(frame, contract=rules)
    assert result.source_rows == tuple(range(len(source)))
    assert result.to_polars()["x"].to_list() == source
    assert result.to_polars()["x"].dtype == pl.Float64
    assert result.after.valid
    assert str(frame) == original


@pytest.mark.parametrize("values", [[2**53 + 1, 2.5], [2.5, 2**53 + 1]])
def test_mixed_numeric_materialization_does_not_round_exact_integers(values):
    """Common float storage must not silently round exact source integers."""
    frame = pd.DataFrame({"x": pd.Series(values, dtype=object)})
    rules = DataContract((ColumnRule("x"),))
    assert validate_data(frame, contract=rules).valid
    with pytest.raises(ValidationError, match="materialized"):
        normalize_data(frame, contract=rules)
