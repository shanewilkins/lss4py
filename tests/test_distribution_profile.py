"""Distribution-profile evidence, identity, diagnostics, and backend contracts."""

import json

import numpy as np
import polars as pl
import pytest

from lss4py import DistributionProfileResult, ValidationError, distribution_profile

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)


def test_hand_calculated_profile(frame_factory):
    """Check bins, ECDF, IQR flags and source identity against direct arithmetic."""
    result = distribution_profile(
        frame_factory(
            {
                "id": ["a", "b", "c", "d", "e", "f", "missing"],
                "x": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0, None],
            }
        ),
        column="x",
        key_column="id",
        histogram_bins=2,
        unit="minutes",
    )
    assert isinstance(result, DistributionProfileResult)
    assert (result.total, result.count, result.missing) == (7, 6, 1)
    assert result.values.tolist() == [1, 2, 3, 4, 5, 100]
    assert result.keys is not None
    assert result.keys.tolist() == ["a", "b", "c", "d", "e", "f"]
    assert result.source_positions.tolist() == [0, 1, 2, 3, 4, 5]
    assert result.histogram_edges.tolist() == [1, 50.5, 100]
    assert result.histogram_counts.tolist() == [5, 1]
    assert result.histogram_density.tolist() == pytest.approx([5 / (6 * 49.5), 1 / (6 * 49.5)])
    assert result.ecdf_values.tolist() == [1, 2, 3, 4, 5, 100]
    assert result.ecdf_probabilities.tolist() == pytest.approx(
        [1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6, 1]
    )
    assert (result.q1, result.median, result.q3, result.iqr) == (2.25, 3.5, 4.75, 2.5)
    assert (result.lower_fence, result.upper_fence) == (-1.5, 8.5)
    assert (result.lower_whisker, result.upper_whisker) == (1, 5)
    assert result.outlier_values.tolist() == [100]
    assert result.outlier_source_positions.tolist() == [5]
    assert result.outlier_keys is not None
    assert result.outlier_keys.tolist() == ["f"]
    assert result.unit == "minutes"


def test_complete_backend_parity_and_source_immutability(
    frame_factory, neutral_payload, assert_equivalent, backend
):
    """Preserve complete evidence and hostile pandas identity without mutating input."""
    records = {
        "id": ["a", "b", "c", "d", "e", "f"],
        "x": [1.0, 2.0, 3.0, 4.0, None, 6.0],
    }
    frame = frame_factory(records)
    if backend == "pyarrow":
        original = frame
    elif backend.startswith("pandas"):
        original = frame.copy(deep=True)
    else:
        original = frame.clone()
    result = distribution_profile(
        frame,
        column="x",
        key_column="id",
        histogram_bins="sturges",
        density=True,
        density_bandwidth="silverman",
        density_grid_points=64,
        cohort="Selected measurement cohort",
    )
    reference = distribution_profile(
        pl.DataFrame(records),
        column="x",
        key_column="id",
        histogram_bins="sturges",
        density=True,
        density_bandwidth="silverman",
        density_grid_points=64,
        cohort="Selected measurement cohort",
    )
    assert_equivalent(neutral_payload(result), neutral_payload(reference))
    assert result.density_method == "gaussian_kde"
    assert result.density_bandwidth is not None
    assert len(result.density_x) == len(result.density_y) == 64
    assert result.provenance.cohort_definition == "Selected measurement cohort"
    assert result.metadata["evidence_sensitivity"]
    assert json.loads(result.to_json())["result_type"] == "DistributionProfileResult"
    assert DistributionProfileResult.from_dict(result.to_dict()).to_dict() == result.to_dict()
    if backend == "pyarrow":
        assert frame is original
    else:
        assert frame.equals(original)


def test_observation_frame_preserves_positions_keys_and_flags(frame_factory):
    """Expose portable row evidence without substituting a pandas index for identity."""
    result = distribution_profile(
        frame_factory({"id": ["a", "b", "c", "d"], "x": [1, 2, 3, 100]}),
        column="x",
        key_column="id",
    )
    frame = result.to_frame()
    assert frame["source_position"].to_list() == [0, 1, 2, 3]
    assert frame["key"].to_list() == ["a", "b", "c", "d"]
    assert frame["is_outlier"].to_list() == [False, False, False, True]


def test_no_outlier_policy_retains_observations_without_fences(frame_factory):
    """Disable anomaly flags explicitly without changing the observation population."""
    result = distribution_profile(
        frame_factory({"x": [1, 2, 3, 100]}),
        column="x",
        outlier_method="none",
    )
    assert result.lower_fence is result.upper_fence is None
    assert result.outlier_values.tolist() == []
    assert result.lower_whisker == 1
    assert result.upper_whisker == 100


def test_constant_sample_keeps_available_evidence(frame_factory):
    """Retain histogram, ECDF and Q-Q evidence while declining undefined diagnostics."""
    result = distribution_profile(
        frame_factory({"x": [3.0, 3.0, 3.0, 3.0]}),
        column="x",
        density=True,
    )
    assert result.std == 0
    assert result.skew is result.kurtosis is None
    assert result.qq_r is None
    assert result.shapiro_statistic is result.shapiro_p_value is None
    assert result.density_method is result.density_bandwidth is None
    assert result.density_x.tolist() == result.density_y.tolist() == []
    codes = {warning.code for warning in result.provenance.warnings}
    assert {
        "SHAPE_UNAVAILABLE",
        "QQ_CORRELATION_UNAVAILABLE",
        "NORMALITY_UNAVAILABLE",
        "DENSITY_UNAVAILABLE",
    } <= codes


def test_qq_coordinates_and_line_are_complete(frame_factory):
    """Retain one ordered observed/theoretical pair per valid measurement."""
    result = distribution_profile(
        frame_factory({"x": [1.0, 2.0, 3.0, 4.0, 5.0]}),
        column="x",
    )
    assert len(result.qq_theoretical) == len(result.qq_observed) == result.count
    assert np.diff(result.qq_theoretical).min() > 0
    assert result.qq_observed.tolist() == [1, 2, 3, 4, 5]
    assert result.qq_line_x.tolist() == [
        result.qq_theoretical[0],
        result.qq_theoretical[-1],
    ]
    assert result.qq_line_y == pytest.approx(
        result.qq_slope * result.qq_line_x + result.qq_intercept
    )


@pytest.mark.parametrize(
    ("values", "warning_code"),
    [
        ([1.0, 2.0], "NORMALITY_UNAVAILABLE"),
        (list(range(5001)), "NORMALITY_UNAVAILABLE"),
    ],
)
def test_shapiro_sample_bounds_are_explicit(frame_factory, values, warning_code):
    """Keep normality evidence unavailable outside the declared Shapiro range."""
    result = distribution_profile(frame_factory({"x": values}), column="x")
    assert result.shapiro_statistic is result.shapiro_p_value is None
    assert warning_code in {warning.code for warning in result.provenance.warnings}


def test_nonfinite_derived_arithmetic_is_rejected(frame_factory):
    """Translate overflow in statistical preparation to the public validation error."""
    with pytest.raises(ValidationError, match="arithmetic did not remain finite"):
        distribution_profile(
            frame_factory({"x": [-1e308, 1e308]}),
            column="x",
        )


@pytest.mark.parametrize(
    "options",
    [
        {"histogram_bins": 0},
        {"histogram_bins": True},
        {"histogram_bins": "unknown"},
        {"histogram_bins": []},
        {"outlier_method": "z"},
        {"outlier_multiplier": 0},
        {"outlier_multiplier": True},
        {"density": 1},
        {"density_bandwidth": "other"},
        {"density_bandwidth": 0},
        {"density_grid_points": 31},
        {"density_grid_points": 4097},
        {"density_grid_points": True},
        {"normality_alpha": 0},
        {"normality_alpha": 1},
        {"normality_alpha": True},
        {"missing": "ignore"},
        {"unit": ""},
        {"cohort": ""},
    ],
)
def test_invalid_options(frame_factory, options):
    """Reject ambiguous preparation policies rather than relying on library coercion."""
    with pytest.raises(ValidationError):
        distribution_profile(frame_factory({"x": [1, 2, 3]}), column="x", **options)


@pytest.mark.parametrize("values", [[], [1.0], [None, None], [float("nan"), 1.0]])
def test_insufficient_valid_measurements(frame_factory, values):
    """Require enough valid observations to characterize a distribution."""
    with pytest.raises(ValidationError, match="at least two"):
        distribution_profile(frame_factory({"x": values}), column="x")


def test_missing_identity_and_measurement_failures(frame_factory):
    """Apply strict shared identity and measurement contracts."""
    with pytest.raises(ValidationError, match="missing"):
        distribution_profile(
            frame_factory({"x": [1.0, 2.0, None]}),
            column="x",
            missing="raise",
        )
    with pytest.raises(ValidationError, match="unique"):
        distribution_profile(
            frame_factory({"id": ["a", "a"], "x": [1.0, 2.0]}),
            column="x",
            key_column="id",
        )
    for values in ([True, False], ["1", "2"], [1.0, float("inf")]):
        with pytest.raises(ValidationError):
            distribution_profile(frame_factory({"x": values}), column="x")
