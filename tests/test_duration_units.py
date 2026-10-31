"""Explicit unit preparation preserves identity, clocks and native backend contracts."""

import json
import subprocess
import sys
from typing import Any

import narwhals as nw
import polars as pl
import pytest

from lss4py import (
    ColumnRule,
    DataContract,
    DescriptiveResult,
    UnsupportedInputError,
    ValidationError,
    convert_duration_columns,
    describe,
    normalize_data,
    validate_data,
)

BACKENDS = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)


def _convert(frame, **options):
    parameters: dict[str, Any] = {
        "columns": ["duration"],
        "source_unit": "minutes",
        "target_unit": "seconds",
        "clock": "cumulative operating time; closed hours excluded",
        **options,
    }
    return convert_duration_columns(frame, **parameters)


@BACKENDS
@pytest.mark.parametrize(
    ("source", "target", "expected"),
    [
        ("minutes", "seconds", [0.0, 90.0, 180.0]),
        ("hours", "seconds", [0.0, 5400.0, 10800.0]),
        ("hours", "minutes", [0.0, 90.0, 180.0]),
        ("seconds", "minutes", [0.0, 0.025, 0.05]),
        ("minutes", "hours", [0.0, 0.025, 0.05]),
        ("seconds", "hours", [0.0, 1.5 / 3600, 3.0 / 3600]),
    ],
)
def test_explicit_conversion_preserves_rows_columns_backend_and_source(
    frame_factory, source, target, expected
):
    frame = frame_factory({"id": ["003", "001", "002"], "duration": [0.0, 1.5, 3.0]})
    result = _convert(frame, source_unit=source, target_unit=target)
    native = result.to_native()
    assert type(native) is type(frame)
    observed = nw.from_native(native)
    assert observed["duration"].to_list() == pytest.approx(expected)
    assert observed["id"].to_list() == ["003", "001", "002"]
    assert nw.from_native(frame)["duration"].to_list() == [0.0, 1.5, 3.0]
    if hasattr(frame, "index"):
        assert native.index.equals(frame.index)
    evidence = result.to_dict()
    assert evidence["source_rows"] == [0, 1, 2]
    assert evidence["source_unit"] == source and evidence["target_unit"] == target
    assert evidence["calendar_conversion"] == "none"
    assert evidence["clock"] == "cumulative operating time; closed hours excluded"
    assert evidence["software_versions"]["pint"]
    assert json.loads(result.to_json()) == evidence
    evidence["source_rows"].clear()
    assert result.to_dict()["source_rows"] == [0, 1, 2]


@BACKENDS
def test_multiple_columns_preserve_order_and_produce_portable_result_evidence(frame_factory):
    frame = frame_factory({"id": ["001", "002"], "duration": [1.0, 2.0], "wait": [0.5, 0.0]})
    result = _convert(frame, columns=["duration", "wait"])
    native = result.to_native()
    assert nw.from_native(native)["wait"].to_list() == [30.0, 0.0]
    assert nw.from_native(native).columns == ["id", "duration", "wait"]
    summary = describe(native, column="duration", unit="seconds")
    summary.metadata["unit_conversion"] = result.to_dict()
    restored = DescriptiveResult.from_dict(json.loads(summary.to_json()))
    assert restored.mean == 90
    assert restored.metadata["unit_conversion"] == result.to_dict()


@pytest.mark.parametrize("alias", ["s", "sec", "second", "seconds"])
def test_second_aliases_are_explicit_and_preserved(alias):
    result = _convert(pl.DataFrame({"duration": [60]}), source_unit=alias, target_unit="min")
    assert result.to_native()["duration"].to_list() == [1.0]
    assert result.to_dict()["source_unit"] == alias
    assert result.to_dict()["canonical_source_unit"] == "second"


@pytest.mark.parametrize("source", ["min", "minute", "minutes", "h", "hr", "hour", "hours"])
def test_other_documented_aliases_have_physical_duration_meaning(source):
    expected = 60.0 if source in ("min", "minute", "minutes") else 3600.0
    assert _convert(pl.DataFrame({"duration": [1]}), source_unit=source).to_native()[
        "duration"
    ].to_list() == [expected]


@pytest.mark.parametrize(
    "unit",
    [
        "m",
        "meter",
        "kg",
        "%",
        "day",
        "days",
        "operating day",
        "fortnight",
        "min ",
        "bogus",
        None,
        1,
    ],
)
@pytest.mark.parametrize("role", ["source_unit", "target_unit"])
def test_unsupported_or_ambiguous_units_fail_without_calendar_inference(unit, role):
    with pytest.raises(ValidationError, match="Unsupported duration unit"):
        _convert(pl.DataFrame({"duration": [1]}), **{role: unit})


@pytest.mark.parametrize("clock", [None, 1, "", "\t"])
def test_clock_declaration_is_required(clock):
    with pytest.raises(ValidationError, match="clock"):
        _convert(pl.DataFrame({"duration": [1]}), clock=clock)


@pytest.mark.parametrize(
    "columns", [None, [], "duration", ["missing"], [1], ["duration", "duration"]]
)
def test_column_selection_is_explicit_and_unambiguous(columns):
    with pytest.raises(ValidationError, match="column"):
        _convert(pl.DataFrame({"duration": [1]}), columns=columns)


@pytest.mark.parametrize("value", [None, True, "1", -1, float("nan"), float("inf"), -float("inf")])
def test_incomplete_nonnumeric_or_negative_durations_fail(value):
    with pytest.raises(ValidationError, match="duration, row 0"):
        _convert(pl.DataFrame({"duration": [value]}))


@pytest.mark.parametrize(
    ("value", "target", "message"),
    [
        (1e308, "seconds", "finite"),
        (5e-324, "hours", "underflows"),
        (2**53 + 1, "seconds", "precision"),
    ],
)
def test_float_overflow_underflow_and_integer_precision_loss_are_rejected(value, target, message):
    with pytest.raises(ValidationError, match=message):
        _convert(pl.DataFrame({"duration": [value]}), target_unit=target)


def test_arbitrary_precision_integer_overflow_has_a_governed_error():
    frame = pl.DataFrame({"duration": pl.Series([10**400], dtype=pl.Object)})
    with pytest.raises(ValidationError, match="duration is not representable"):
        _convert(frame)


def test_empty_and_lazy_inputs_are_not_silently_prepared():
    with pytest.raises(ValidationError, match="at least one observation"):
        _convert(pl.DataFrame({"duration": []}))
    with pytest.raises(UnsupportedInputError):
        _convert(pl.DataFrame({"duration": [1]}).lazy())


def test_failed_second_column_does_not_mutate_the_input():
    frame = pl.DataFrame({"duration": [1.0], "wait": [-1.0]})
    with pytest.raises(ValidationError, match="wait, row 0"):
        _convert(frame, columns=["duration", "wait"])
    assert frame.to_dict(as_series=False) == {"duration": [1.0], "wait": [-1.0]}


def test_identity_conversion_and_returned_native_copy_remain_explicit():
    result = _convert(pl.DataFrame({"duration": [1.0]}), target_unit="minutes")
    assert result.to_dict()["factor"] == 1
    copied = result.to_native()
    copied.replace_column(0, pl.Series("duration", [99.0]))
    assert result.to_native()["duration"].to_list() == [1.0]


def test_existing_normalization_still_rejects_unit_mismatch_without_converting():
    frame = pl.DataFrame({"duration": [1.0]})
    contract = DataContract((ColumnRule("duration", unit="seconds"),))
    assert not validate_data(frame, contract=contract, source_units={"duration": "minutes"}).valid
    with pytest.raises(ValidationError):
        normalize_data(frame, contract=contract, source_units={"duration": "minutes"})
    assert frame["duration"].to_list() == [1.0]


def test_private_registry_ignores_application_redefinitions_and_does_not_replace_it():
    script = """
import pint
import polars as pl
from lss4py import convert_duration_columns
custom = pint.UnitRegistry(on_redefinition='ignore')
custom.define('minute = 7 * second')
pint.set_application_registry(custom)
assert pint.Quantity(1, 'minute').to('seconds').magnitude == 7
converted = convert_duration_columns(
    pl.DataFrame({'x': [1]}), columns=['x'], source_unit='min', target_unit='s', clock='elapsed'
)
assert converted.to_native()['x'].to_list() == [60.0]
assert pint.Quantity(1, 'minute').to('seconds').magnitude == 7
"""
    subprocess.run([sys.executable, "-c", script], check=True)


def test_numerical_import_does_not_initialize_pint():
    subprocess.run(
        [sys.executable, "-c", "import sys, lss4py; assert 'pint' not in sys.modules"], check=True
    )
