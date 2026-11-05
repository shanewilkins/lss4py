"""Property tests for moving-range identities, limits, signals, and frozen baselines."""

import json
from math import ldexp

import numpy as np
import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from lss4py import ControlChartResult, ValidationError, control_chart
from lss4py.domain import AnalyticalResult

MEASUREMENT = st.floats(
    min_value=-1e100,
    max_value=1e100,
    allow_nan=False,
    allow_infinity=False,
    allow_subnormal=False,
)
MEASUREMENTS = st.lists(
    MEASUREMENT,
    min_size=2,
    max_size=30,
)


@settings(max_examples=60)
@given(
    values=st.lists(st.integers(-1000, 1000), min_size=2, max_size=30),
    offset=st.integers(-1000000, 1000000),
    exponent=st.integers(-400, 400),
)
def test_translation_and_positive_scaling_preserve_chart_decisions(values, offset, exponent):
    # Integer translations and binary scaling are exact here, so cancellation
    # cannot invalidate the mathematical invariants being tested.
    original = control_chart(pl.DataFrame({"x": values}), column="x")
    translated = control_chart(pl.DataFrame({"x": [x + offset for x in values]}), column="x")
    scaled = control_chart(pl.DataFrame({"x": [ldexp(x, exponent) for x in values]}), column="x")
    assert translated.moving_ranges.tolist() == original.moving_ranges.tolist()
    for field in ("lcl", "center_line", "ucl"):
        assert getattr(translated, field) == getattr(original, field)
        assert getattr(scaled, field) == pytest.approx(
            ldexp(getattr(original, field), exponent), rel=1e-12, abs=0
        )
    assert scaled.moving_ranges == pytest.approx(
        [ldexp(value, exponent) for value in original.moving_ranges], rel=1e-12, abs=0
    )
    for chart in (translated, scaled):
        assert chart.signal_indices.tolist() == original.signal_indices.tolist()
        assert chart.signal_source_positions.tolist() == original.signal_source_positions.tolist()


@settings(max_examples=50)
@given(exponent=st.integers(-400, 400))
def test_scaled_frozen_baseline_preserves_signals_and_rejects_edits(exponent):
    baseline = control_chart(
        pl.DataFrame({"x": [ldexp(x, exponent) for x in (0, 1, 2)]}), column="x"
    )
    observations = pl.DataFrame({"x": [0.0, ldexp(100, exponent)]})
    result = control_chart(observations, column="x", baseline=baseline)
    assert result.signal_indices.tolist() == [0]
    assert (result.lcl, result.center_line, result.ucl) == (
        baseline.lcl,
        baseline.center_line,
        baseline.ucl,
    )
    baseline.ucl *= 2
    with pytest.raises(ValidationError, match="limits differ"):
        control_chart(observations, column="x", baseline=baseline)


@settings(max_examples=75)
@given(values=MEASUREMENTS, nsigmas=st.floats(min_value=0.25, max_value=6))
def test_moving_range_result_invariants(values, nsigmas):
    result = control_chart(
        pl.DataFrame({"value": values}),
        column="value",
        nsigmas=nsigmas,
    )
    expected_ranges = np.abs(np.diff(np.asarray(values, dtype=float)))
    assert result.observation_count == len(values)
    assert len(result.moving_ranges) == len(values) - 1
    assert result.moving_ranges == pytest_approx_array(expected_ranges)
    assert result.pair_start_positions.tolist() == list(range(len(values) - 1))
    assert result.pair_end_positions.tolist() == list(range(1, len(values)))
    assert 0 <= result.lcl <= result.center_line <= result.ucl
    expected_signals = np.flatnonzero(
        (expected_ranges < result.lcl) | (expected_ranges > result.ucl)
    )
    assert result.signal_indices.tolist() == expected_signals.tolist()
    assert result.signal_source_positions.tolist() == (expected_signals + 1).tolist()


@settings(max_examples=50)
@given(baseline_values=MEASUREMENTS, monitoring_values=MEASUREMENTS)
def test_phase_ii_reuses_exact_phase_i_limits(baseline_values, monitoring_values):
    baseline = control_chart(
        pl.DataFrame({"value": baseline_values}),
        column="value",
    )
    monitored = control_chart(
        pl.DataFrame({"value": monitoring_values}),
        column="value",
        baseline=baseline,
    )
    assert monitored.phase == "II"
    assert (monitored.lcl, monitored.center_line, monitored.ucl) == (
        baseline.lcl,
        baseline.center_line,
        baseline.ucl,
    )
    assert monitored.baseline_observation_count == len(baseline_values)
    assert monitored.baseline_result_fingerprint


@settings(max_examples=50)
@given(values=MEASUREMENTS)
def test_control_chart_roundtrip_preserves_every_field(values):
    result = control_chart(pl.DataFrame({"value": values}), column="value")
    restored = AnalyticalResult.from_dict(json.loads(result.to_json()))
    assert isinstance(restored, ControlChartResult)
    assert restored.to_dict() == result.to_dict()


@settings(max_examples=30)
@given(values=st.lists(MEASUREMENT, max_size=1))
def test_control_chart_rejects_insufficient_generated_sequences(values):
    with pytest.raises(ValidationError, match="at least two"):
        control_chart(pl.DataFrame({"value": values}), column="value")


@settings(max_examples=30)
@given(
    before=st.lists(MEASUREMENT, min_size=1, max_size=10),
    after=st.lists(MEASUREMENT, max_size=10),
)
def test_control_chart_rejects_generated_missing_adjacencies(before, after):
    with pytest.raises(ValidationError, match="missing measurements"):
        control_chart(
            pl.DataFrame({"value": [*before, None, *after]}),
            column="value",
        )


def pytest_approx_array(expected):
    """Compare generated floating arrays with the calculation's stored precision."""
    return pytest.approx(expected, rel=1e-14, abs=1e-14)
