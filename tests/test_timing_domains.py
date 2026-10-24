"""Cross-backend timing domains, common units and exact binary-stage regression."""

import pytest

from lss4py import (
    ValidationError,
    created_to_booked_yield,
    lead_time,
    process_cycle_efficiency,
    takt_time,
    wait_time,
)

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)


@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf"), float("-inf"), None])
def test_wait_rejects_invalid_operands(backend, frame_factory, value):
    frame = frame_factory({"lead": [value], "cycle": [value]})
    with pytest.raises(ValidationError):
        wait_time(frame, lead_time_column="lead", cycle_time_column="cycle")


@pytest.mark.parametrize("unit", ["seconds", "minutes", "hours", "days"])
def test_wait_preserves_explicit_common_units(backend, frame_factory, unit):
    result = wait_time(
        frame_factory({"lead": [10.0], "cycle": [4.0]}),
        lead_time_column="lead",
        cycle_time_column="cycle",
        unit=unit,
    )
    assert result.unit == unit
    assert result.values.tolist() == [6.0]
    assert result.provenance.parameters["unit"] == unit


@pytest.mark.parametrize("value", [float("nan"), float("inf"), None, "10", True])
def test_per_row_pce_rejects_invalid_measurements(backend, frame_factory, value):
    with pytest.raises(ValidationError):
        process_cycle_efficiency(
            frame_factory({"lead": [value], "va": [1.0]}),
            lead_time_column="lead",
            value_add_time_column="va",
        )


@pytest.mark.parametrize("value", [0.5, 1.5, float("nan"), None, "1"])
def test_stage_yield_never_truncates_or_coerces(backend, frame_factory, value):
    with pytest.raises(ValidationError):
        created_to_booked_yield(
            frame_factory({"created": [1], "booked": [value]}),
            created_column="created",
            booked_column="booked",
        )


def test_missing_calendar_endpoint_fails(backend, frame_factory):
    with pytest.raises(ValidationError):
        lead_time(
            frame_factory({"s": [None], "e": ["2026-01-01T01:00:00"]}),
            start_column="s",
            end_column="e",
        )


@pytest.mark.parametrize("unit", ["fortnights", None, 1])
def test_invalid_units_fail_with_domain_error(backend, frame_factory, unit):
    with pytest.raises(ValidationError):
        wait_time(
            frame_factory({"lead": [10], "cycle": [4]}),
            lead_time_column="lead",
            cycle_time_column="cycle",
            unit=unit,
        )


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), float("-inf"), None, True, "1", 0, -1]
)
def test_takt_rejects_invalid_scalars(backend, value):
    with pytest.raises(ValidationError):
        takt_time(available_time=value, customer_demand=2)
    with pytest.raises(ValidationError):
        takt_time(available_time=2, customer_demand=value)


@pytest.mark.parametrize("as_percentage", ["false", 1, None])
def test_percentage_options_do_not_use_truthiness(backend, frame_factory, as_percentage):
    frame = frame_factory({"created": [1], "booked": [1]})
    with pytest.raises(ValidationError, match="boolean"):
        created_to_booked_yield(
            frame, created_column="created", booked_column="booked", as_percentage=as_percentage
        )


def test_unsupported_input_remains_type_error_and_lss4py_error(backend):
    from lss4py import LSS4PyError

    with pytest.raises(LSS4PyError) as error:
        wait_time({"l": [1], "c": [0]}, lead_time_column="l", cycle_time_column="c")
    assert isinstance(error.value, TypeError)
