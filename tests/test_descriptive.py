"""Descriptive contracts, numerical references, and pandas/Polars parity."""

import json

import numpy as np
import pandas as pd
import polars as pl
import pytest

from lss4py import DescriptiveResult, ValidationError, describe


def test_reference_summary(frame_factory):
    """Check a five-point symmetric reference with hand-calculated moments."""
    frame = frame_factory({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
    result = describe(frame, column="x", unit="hours")
    assert isinstance(result, DescriptiveResult)
    assert (result.total, result.count, result.missing, result.unique_count) == (5, 5, 0, 5)
    assert result.mean == result.median == 3
    assert result.unit == "hours"
    assert result.provenance.parameters["bias_corrected"] is True
    assert result.provenance.parameters["percentile_method"] == "linear"
    assert "NO_REPEATED_MODE" in {w.code for w in result.provenance.warnings}
    encoded = json.loads(json.dumps(result.to_dict(), allow_nan=False))
    assert encoded["total"] == 5 and encoded["unit"] == "hours"
    assert json.loads(result.to_json())["result_type"] == "DescriptiveResult"


def test_reference_spread_and_shape(frame_factory):
    """Check sample spread, shape, and linear percentiles against fixed references."""
    result = describe(frame_factory({"x": [1.0, 2.0, 3.0, 4.0, 5.0]}), column="x")
    assert result.variance == 2.5
    assert result.std == pytest.approx(np.sqrt(2.5))
    assert result.skew == 0
    assert result.kurtosis == pytest.approx(-1.2)
    assert result.min_value == 1 and result.max_value == 5 and result.range == 4
    assert result.iqr == 2 and result.mad == 1
    assert result.coefficient_of_variation == pytest.approx(np.sqrt(2.5) / 3)
    assert result.percentiles == pytest.approx(
        {"p25": 2, "p50": 3, "p75": 4, "p90": 4.6, "p95": 4.8, "p99": 4.96}
    )
    assert result.modes == [] and result.mode_frequency == 1


def test_population_and_pearson_options(frame_factory):
    """Population spread and Pearson kurtosis are explicit alternatives."""
    result = describe(
        frame_factory({"x": [1, 2, 3, 4, 5]}),
        column="x",
        ddof=0,
        excess_kurtosis=False,
        percentiles=[0, 100, 12.5],
    )
    assert result.variance == 2
    assert result.kurtosis == pytest.approx(1.8)
    assert result.percentiles is not None
    assert result.percentiles["p12.5"] == 1.5
    assert result.percentiles["p0"] == 1 and result.percentiles["p100"] == 5


def test_modes_and_missing(frame_factory):
    """Retain all tied modes and distinguish null/NaN exclusions from valid data."""
    result = describe(frame_factory({"x": [1.0, 1.0, 2.0, 2.0, None, float("nan")]}), column="x")
    assert result.modes == [1, 2] and result.mode_frequency == 2
    assert (result.total, result.count, result.missing) == (6, 4, 2)
    assert result.mean == 1.5
    assert "MISSING_OMITTED" in {w.code for w in result.provenance.warnings}


@pytest.mark.parametrize("values", [[], [None, None], [float("nan")]])
def test_no_valid_data(frame_factory, values):
    """Empty or entirely missing input returns explicit unavailable estimates."""
    result = describe(frame_factory({"x": values}), column="x")
    assert result.count == 0 and result.total == len(values)
    assert result.mean is None and result.std is None and result.modes == []
    assert "NO_VALID_DATA" in {w.code for w in result.provenance.warnings}
    json.dumps(result.to_dict(), allow_nan=False)


@pytest.mark.parametrize("values", [[1.0], [1.0, 2.0], [1.0, 2.0, 4.0]])
def test_small_samples(frame_factory, values):
    """Bias-corrected estimates respect minimum sample sizes."""
    result = describe(frame_factory({"x": values}), column="x")
    assert (result.std is None) == (len(values) < 2)
    assert (result.skew is None) == (len(values) < 3)
    assert result.kurtosis is None


def test_constant(frame_factory):
    """Constant measurements have zero spread, but undefined standardized shape."""
    result = describe(frame_factory({"x": [3, 3, 3, 3]}), column="x")
    assert result.std == result.variance == result.mad == result.iqr == 0
    assert result.coefficient_of_variation == 0
    assert result.modes == [3] and result.mode_frequency == 4
    assert result.skew is None and result.kurtosis is None
    assert "CONSTANT_DATA" in {w.code for w in result.provenance.warnings}


@pytest.mark.parametrize("values", [[-2, -1], [-1, 1], [0, 0], [-1.0, 1.0 + 1e-14]])
def test_cv_nonpositive_or_near_zero(frame_factory, values):
    """Do not present unstable or nonpositive-mean CV values as meaningful."""
    result = describe(frame_factory({"x": values}), column="x")
    assert result.coefficient_of_variation is None
    assert "CV_UNAVAILABLE" in {w.code for w in result.provenance.warnings}


def test_interval_scale(frame_factory):
    """Interval scales lack the meaningful zero required for CV."""
    result = describe(frame_factory({"x": [20, 21, 22]}), column="x", measurement_scale="interval")
    assert result.coefficient_of_variation is None
    assert result.mean == 21


def test_grouping_parity(frame_factory):
    """Retain first-seen order, multiple keys, null groups, and source immutability."""
    frame = frame_factory(
        {
            "team": ["b", "a", "b", None, None],
            "shift": [1, 1, 1, 2, 2],
            "x": [2.0, 4.0, 6.0, None, 10.0],
        }
    )
    original = frame.clone() if isinstance(frame, pl.DataFrame) else frame.copy(deep=True)
    results = describe(frame, column="x", group_by=["team", "shift"])
    assert [r.group_keys for r in results] == [
        {"team": "b", "shift": 1},
        {"team": "a", "shift": 1},
        {"team": None, "shift": 2},
    ]
    assert [r.mean for r in results] == [4, 4, 10]
    assert results[2].missing == 1
    assert results[0].provenance.parameters["group_keys"] == results[0].group_keys
    assert len(describe(frame, column="x", group_by="shift")) == 2
    assert frame.equals(original)
    for result in results:
        json.dumps(result.to_dict(), allow_nan=False)


def test_empty_groups(frame_factory):
    """An empty grouped input has no observed groups."""
    assert describe(frame_factory({"g": [], "x": []}), column="x", group_by="g") == []


@pytest.mark.parametrize("values", [[True, False], ["1", "2"], [float("inf")], [float("-inf")]])
def test_invalid_measurements(frame_factory, values):
    """Never coerce text/booleans or silently discard infinite measurements."""
    with pytest.raises(ValidationError):
        describe(frame_factory({"x": values}), column="x")


@pytest.mark.parametrize(
    "options",
    [
        {"ddof": -1},
        {"ddof": True},
        {"percentiles": [-1]},
        {"percentiles": [101]},
        {"percentiles": [float("nan")]},
        {"percentiles": [[50]]},
        {"percentiles": ["bad"]},
        {"missing": "ignore"},
        {"measurement_scale": "ordinal"},
        {"excess_kurtosis": 1},
        {"group_by": ["g", "g"]},
        {"group_by": "absent"},
    ],
)
def test_invalid_options(options):
    """Reject invalid statistical conventions and grouping configurations."""
    with pytest.raises(ValidationError):
        describe(pl.DataFrame({"x": [1, 2], "g": [1, 2]}), column="x", **options)


def test_missing_policy_and_column(frame_factory):
    """Missing='raise' rejects omissions, and absent measurements give a domain error."""
    frame = frame_factory({"x": [1.0, None]})
    with pytest.raises(ValidationError, match="missing"):
        describe(frame, column="x", missing="raise")
    with pytest.raises(ValidationError, match="Missing required"):
        describe(frame, column="absent")


def test_group_keys_dates_and_rejection():
    """Serialize date group keys, rejecting nested and infinite identifiers."""
    from datetime import date

    result = describe(pl.DataFrame({"g": [date(2026, 1, 1)], "x": [2]}), column="x", group_by="g")[
        0
    ]
    assert result.group_keys == {"g": "2026-01-01"}
    for key in [float("inf"), [1, 2]]:
        with pytest.raises(ValidationError, match="Group identifiers"):
            describe(pl.DataFrame({"g": [key], "x": [2]}), column="x", group_by="g")


def test_numerical_overflow_is_json_safe():
    """Unavailable numerical estimates never leak nonstandard JSON NaN/Infinity."""
    result = describe(pl.DataFrame({"x": [-1e308, 1e308, 1e308, -1e308]}), column="x")
    assert "NUMERICAL_UNAVAILABLE" in {w.code for w in result.provenance.warnings}
    json.dumps(result.to_dict(), allow_nan=False)


def test_asymmetric_moments(frame_factory):
    """Verify nonzero adjusted skewness and kurtosis from hand-calculated moments."""
    result = describe(frame_factory({"x": [1, 2, 3, 6]}), column="x")
    # Centered moments: m2=14/4, m3=18/4; correction sqrt(n*(n-1))/(n-2).
    assert result.skew == pytest.approx(np.sqrt(3) * 4.5 / 3.5**1.5)
    assert result.kurtosis == pytest.approx(1.5)


def test_near_constant_shape(frame_factory):
    """Numerically negligible variation produces diagnostics rather than SciPy warnings."""
    result = describe(frame_factory({"x": [1.0, 1.0, 1.0, 1.0 + 2e-16]}), column="x")
    assert result.skew is None and result.kurtosis is None
    assert "NUMERICAL_SHAPE" in {w.code for w in result.provenance.warnings}


def test_nullable_pandas_groups():
    """Pandas extension-array missing keys match Polars null-group semantics."""
    frame = pd.DataFrame(
        {"g": pd.Series(["a", pd.NA], dtype="string"), "x": pd.Series([1, pd.NA], dtype="Float64")}
    )
    results = describe(frame, column="x", group_by="g")
    assert results[1].group_keys == {"g": None}
    assert results[1].missing == 1


def test_empty_group_selection():
    """Reject ambiguous empty grouping requests."""
    with pytest.raises(ValidationError, match="at least one"):
        describe(pl.DataFrame({"x": [1]}), column="x", group_by=[])


def test_documented_example():
    """Keep the worked example executable as the public contract evolves."""
    from pathlib import Path

    guide = Path(__file__).resolve().parents[1] / "docs" / "descriptive-statistics.md"
    example = guide.read_text().split("```python\n")[1].split("```")[0]
    exec(compile(example, str(guide), "exec"), {})
