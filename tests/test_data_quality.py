"""Reusable data-quality reports and opt-in preparation across eager backends."""

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pandas as pd
import pytest

from lss4py import ColumnRule, DataContract, ValidationError, normalize_data, validate_data

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)


def contract(**options):
    """Declare identifier, bounded measurement, and ordered timestamp roles."""
    return DataContract(
        columns=(
            ColumnRule("id", "string"),
            ColumnRule("hours", minimum=0, nullable=True, unit="hours"),
            ColumnRule("start", "timestamp"),
            ColumnRule("end", "timestamp"),
        ),
        key_columns=("id",),
        timestamp_order=(("start", "end"),),
        **options,
    )


def records():
    """Use original synthetic observations with one missing value and a repeated key."""
    return {
        "id": ["a", "b", "a", "c"],
        "hours": [1.0, None, 2.0, 3.0],
        "start": ["2026-10-01T08:00:00-05:00"] * 4,
        "end": ["2026-10-01T09:30:00-05:00"] * 4,
        "unselected": [1, 2, 3, 4],
    }


def neutral(report):
    """Keep every diagnostic and policy while omitting backend identity."""
    payload = report.to_dict()
    payload.pop("backend")
    return payload


def test_report_and_backend_equivalence(frame_factory):
    """Return all nonblocking findings with positions rather than pandas labels."""
    frame = frame_factory(records())
    before = str(frame)
    report = validate_data(frame, contract=contract(), source_units={"hours": "hours"})
    expected = validate_data(
        pd.DataFrame(records()), contract=contract(), source_units={"hours": "hours"}
    )
    assert neutral(report) == neutral(expected)
    assert report.valid and not report.errors
    assert [(i.code, i.rows) for i in report.warnings] == [
        ("MISSING_VALUES", (1,)),
        ("DUPLICATE_ROWS", (2,)),
    ]
    assert report.profiles[1].missing_count == 1
    assert report.profiles[1].unique_count == 3
    assert report.row_count == 4
    assert str(frame) == before
    assert json.loads(report.to_json()) == json.loads(json.dumps(report.to_dict(), allow_nan=False))


def test_explicit_normalization_and_row_identity(frame_factory):
    """Exclude missing rows before keeping the first surviving key and preserve source evidence."""
    frame = frame_factory(records())
    before = str(frame)
    prepared = normalize_data(
        frame,
        contract=contract(),
        source_units={"hours": "hours"},
        drop_missing=True,
        drop_duplicates=True,
    )
    assert prepared.source_rows == (0, 3)
    assert prepared.after.valid
    assert prepared.before.row_count == 4 and prepared.after.row_count == 2
    output = prepared.to_polars()
    assert output.columns == ["id", "hours", "start", "end"]
    assert output["id"].to_list() == ["a", "c"]
    assert output["start"][0] == datetime(2026, 10, 1, 13, tzinfo=UTC)
    assert str(frame) == before
    json.dumps(prepared.to_dict(), allow_nan=False)


def test_normalization_copy_and_no_implicit_exclusions(frame_factory):
    """Preparation copies data but retains nullable observations and duplicate keys by default."""
    result = normalize_data(frame_factory(records()), contract=contract())
    assert result.source_rows == (0, 1, 2, 3)
    assert result.to_polars()["hours"].null_count() == 1
    copy = result.to_polars()
    copy.replace_column(0, copy["id"].rename("renamed"))
    assert result.to_polars().columns[0] == "id"
    assert "drop_missing_rows" not in result.transformations
    with pytest.raises(FrozenInstanceError):
        setattr(result, "source_rows", ())  # noqa: B010


@pytest.mark.parametrize(
    "value,code",
    [
        (float("inf"), "NONFINITE"),
        (-1, "OUT_OF_RANGE"),
        (True, "INVALID_TYPE"),
        ("1", "INVALID_TYPE"),
        (None, "MISSING_VALUES"),
        (float("nan"), "MISSING_VALUES"),
    ],
)
def test_blocking_numeric_domains(frame_factory, value, code):
    """Do not silently coerce text or booleans, ignore infinities, or omit missing values."""
    data = frame_factory({"x": [value]})
    rules = DataContract((ColumnRule("x", minimum=0),))
    report = validate_data(data, contract=rules)
    assert not report.valid
    assert report.errors[0].code == code
    assert report.errors[0].rows == (0,)
    with pytest.raises(ValidationError):
        normalize_data(data, contract=rules)


@pytest.mark.parametrize("value,valid", [(1.0, True), (0.5, False), (float(2**54), False)])
def test_integer_exactness(frame_factory, value, valid):
    """Integral floats are accepted only in the exact float64 integer range."""
    rules = DataContract((ColumnRule("x", "integer"),))
    report = validate_data(frame_factory({"x": [value]}), contract=rules)
    assert report.valid is valid


def test_missing_identifiers_and_duplicate_policies(frame_factory):
    """Missing keys block even for nullable fields; duplicate handling is a declared policy."""
    data = frame_factory({"id": ["a", "a", None]})
    column = ColumnRule("id", "string", nullable=True)
    strict = DataContract((column,), key_columns=("id",), duplicates="error")
    report = validate_data(data, contract=strict)
    assert {i.code for i in report.errors} == {"MISSING_VALUES", "DUPLICATE_ROWS"}
    result = normalize_data(data, contract=strict, drop_missing=True, drop_duplicates=True)
    assert result.source_rows == (0,)
    allow = DataContract((column,), duplicates="allow")
    assert {i.code for i in validate_data(data, contract=allow).warnings} == {"MISSING_VALUES"}


def test_drop_missing_precedes_deduplication(frame_factory):
    """A rejected first key occurrence must not erase the first complete later observation."""
    rules = DataContract((ColumnRule("id", "string"), ColumnRule("x")), key_columns=("id",))
    data = frame_factory({"id": ["a", "a"], "x": [None, 2.0]})
    prepared = normalize_data(data, contract=rules, drop_missing=True, drop_duplicates=True)
    assert prepared.source_rows == (1,)
    assert prepared.to_polars()["x"].to_list() == [2.0]


def test_all_declared_columns_define_duplicates_without_keys(frame_factory):
    """Extra columns do not change duplicate semantics outside the declared contract."""
    data = frame_factory({"x": [1, 1, 2], "extra": [1, 2, 3]})
    report = validate_data(data, contract=DataContract((ColumnRule("x"),)))
    assert report.warnings[0].rows == (1,)


@pytest.mark.parametrize(
    "end,code",
    [
        ("2026-10-01T07:00:00-05:00", "REVERSED_TIME"),
        ("2026-10-01T09:00:00", "MIXED_TIMEZONES"),
        ("bad", "INVALID_TIMESTAMP"),
        ("2026-10-01", "INVALID_TIMESTAMP"),
    ],
)
def test_timestamp_errors_are_structured(frame_factory, end, code):
    """Parse declared ISO timestamps consistently and distinguish order and awareness errors."""
    data = records()
    data["end"][0] = end
    report = validate_data(frame_factory(data), contract=contract())
    assert code in {i.code for i in report.errors}
    with pytest.raises(ValidationError):
        normalize_data(frame_factory(data), contract=contract(), drop_missing=True)


def test_native_timestamps_and_naive_normalization(frame_factory):
    """Native naive datetimes retain their wall time without inferring a timezone."""
    rules = DataContract((ColumnRule("time", "timestamp"),))
    result = normalize_data(frame_factory({"time": [datetime(2026, 10, 1, 8)]}), contract=rules)
    assert result.to_polars()["time"][0] == datetime(2026, 10, 1, 8)
    assert result.after.valid


def test_units_are_explicit_and_never_converted(frame_factory):
    """Unknown units warn; mismatches block without modifying measured quantities."""
    rules = DataContract((ColumnRule("x", unit="hours"),))
    data = frame_factory({"x": [60]})
    assert validate_data(data, contract=rules).warnings[0].code == "UNIT_UNVERIFIED"
    report = validate_data(data, contract=rules, source_units={"x": "minutes"})
    assert report.errors[0].code == "UNIT_MISMATCH"
    with pytest.raises(ValidationError, match="UNIT_MISMATCH"):
        normalize_data(data, contract=rules, source_units={"x": "minutes"})


def test_empty_missing_column_and_empty_preparation(frame_factory):
    """Empty input and dropping every row cannot produce an apparently usable table."""
    rules = DataContract((ColumnRule("x"),))
    missing = validate_data(frame_factory({"y": []}), contract=rules)
    assert {i.code for i in missing.errors} == {"EMPTY_DATA", "MISSING_COLUMN"}
    with pytest.raises(ValidationError, match="EMPTY_DATA"):
        normalize_data(frame_factory({"x": [None]}), contract=rules, drop_missing=True)


def test_non_string_and_nested_columns(frame_factory):
    """Reject unsupported nested measurement values without leaking backend exceptions."""
    report = validate_data(
        frame_factory({"x": [[1, 2]]}), contract=DataContract((ColumnRule("x"),))
    )
    assert report.errors[0].code == "INVALID_TYPE"
    assert report.profiles[0].observed_kind == "unsupported"


@pytest.mark.parametrize(
    "options",
    [
        {"drop_missing": "yes"},
        {"drop_duplicates": 1},
        {"source_units": {"missing": "hours"}},
        {"source_units": {"x": ""}},
        {"source_units": []},
    ],
)
def test_invalid_preparation_options(frame_factory, options):
    """Reject ambiguous caller policies without attempting a repair."""
    with pytest.raises(ValidationError):
        normalize_data(
            frame_factory({"x": [1]}), contract=DataContract((ColumnRule("x"),)), **options
        )


@pytest.mark.parametrize(
    "kind,value,code",
    [
        ("boolean", 1, "INVALID_TYPE"),
        ("string", "  ", "BLANK_VALUE"),
        ("numeric", 4, "OUT_OF_RANGE"),
        ("timestamp", 1, "INVALID_TIMESTAMP"),
    ],
)
def test_additional_scalar_domains(frame_factory, kind, value, code):
    """Keep boolean, text, timestamp and upper-bound policies explicit."""
    rule = ColumnRule("x", kind, maximum=3 if kind == "numeric" else None)
    report = validate_data(frame_factory({"x": [value]}), contract=DataContract((rule,)))
    assert report.errors[0].code == code
    assert report.profiles[0].invalid_count == 1


def test_mixed_numeric_keys_do_not_depend_on_dtype(frame_factory):
    """Integral numeric keys have the same duplicate identity after pandas float promotion."""
    data = frame_factory({"key": [1.0, 1.0, float("nan")]})
    rules = DataContract((ColumnRule("key", nullable=True),), key_columns=("key",))
    report = validate_data(data, contract=rules)
    assert report.warnings[0].code == "DUPLICATE_ROWS"
    assert report.warnings[0].rows == (1,)


def test_boolean_and_integer_normalization(frame_factory):
    """Preserve boolean domains and explicitly materialize integral values as integers."""
    rules = DataContract((ColumnRule("ok", "boolean"), ColumnRule("count", "integer")))
    prepared = normalize_data(frame_factory({"ok": [True], "count": [2.0]}), contract=rules)
    values = prepared.to_polars().row(0)
    assert values == (True, 2)
    assert type(values[1]) is int
    assert json.loads(prepared.to_json())["after"]["valid"]


def test_invalid_values_do_not_create_phantom_duplicates(frame_factory):
    """Unavailable parsed scalars cannot collapse distinct bad observations into duplicate keys."""
    rules = DataContract((ColumnRule("x"),))
    report = validate_data(frame_factory({"x": ["first", "second"]}), contract=rules)
    assert report.errors[0].code == "INVALID_TYPE"
    assert report.errors[0].rows == (0, 1)
    assert "DUPLICATE_ROWS" not in {issue.code for issue in report.issues}
