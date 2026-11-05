"""Mean-confidence-interval references, diagnostics, and backend contracts."""

import json

import numpy as np
import polars as pl
import pytest

from lss4py import MeanCIResult, ValidationError, mean_confidence_interval
from tests.reference_catalog import load_catalog

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
REFERENCE = next(e for e in load_catalog() if e["metadata"]["id"] == "r-sixsigma-baseline")
R_CASES = [case for case in REFERENCE["expected"] if case["method"] == "ss.ci"]


@pytest.mark.parametrize("case", R_CASES, ids=lambda case: case["id"])
def test_genuine_sixsigma_reference(frame_factory, case):
    """Match genuine SixSigma intervals without inheriting its plotting side effects."""
    arguments = case["parameters"]
    result = mean_confidence_interval(
        frame_factory({"x": arguments["x"]}),
        column="x",
        population_variance=arguments.get("sigma2"),
        approximate_z=arguments.get("approx.z", False),
    )
    tolerance = case["tolerance"]
    assert result.confidence_interval == pytest.approx(
        case["expected"]["value"],
        abs=tolerance["absolute"],
        rel=tolerance["relative"],
    )


def test_complete_contract_and_backend_parity(
    frame_factory, neutral_payload, assert_equivalent, backend
):
    """Retain exclusions, provenance, diagnostics, serialization, and source immutability."""
    records = {"x": [8.0, 9.0, 10.0, 11.0, 12.0, None, float("nan")]}
    frame = frame_factory(records)
    if backend == "pyarrow":
        original = frame
    elif backend.startswith("pandas"):
        original = frame.copy(deep=True)
    else:
        original = frame.clone()
    result = mean_confidence_interval(
        frame,
        column="x",
        unit="mm",
        cohort="Selected production sample",
    )
    reference = mean_confidence_interval(
        pl.DataFrame(records),
        column="x",
        unit="mm",
        cohort="Selected production sample",
    )
    assert_equivalent(neutral_payload(result), neutral_payload(reference))
    assert isinstance(result, MeanCIResult)
    assert (result.total, result.count, result.missing) == (7, 5, 2)
    assert result.distribution == "student_t"
    assert result.degrees_of_freedom == 4
    assert result.variance_source == "sample"
    assert result.population_variance is None
    assert result.unit == "mm"
    assert result.shapiro_statistic is not None
    assert result.shapiro_p_value is not None
    assert result.provenance.parameters["formula_source"] == "SixSigma 0.11.1 ss.ci"
    assert result.provenance.cohort_definition == "Selected production sample"
    assert json.loads(result.to_json())["result_type"] == "MeanCIResult"
    assert MeanCIResult.from_dict(result.to_dict()).to_dict() == result.to_dict()
    if backend == "pyarrow":
        assert frame is original
    else:
        assert frame.equals(original)


def test_known_variance_and_explicit_approximation(frame_factory):
    """Distinguish a known population variance from an explicitly approximate z interval."""
    frame = frame_factory({"x": [8, 9, 10, 11, 12]})
    known = mean_confidence_interval(frame, column="x", population_variance=4)
    approximate = mean_confidence_interval(frame, column="x", approximate_z=True)
    assert known.distribution == approximate.distribution == "normal"
    assert known.variance_source == "known_population"
    assert known.population_variance == 4
    assert known.standard_deviation == 2
    assert approximate.variance_source == "sample"
    assert approximate.population_variance is None
    assert "APPROXIMATE_Z" in {warning.code for warning in approximate.provenance.warnings}


def test_sample_size_does_not_silently_select_z(frame_factory):
    """Retain Student's t for unknown variance even above the historical threshold of 30."""
    result = mean_confidence_interval(frame_factory({"x": list(range(31))}), column="x")
    assert result.distribution == "student_t"
    assert result.degrees_of_freedom == 30
    assert "SMALL_SAMPLE" not in {warning.code for warning in result.provenance.warnings}


def test_normality_diagnostics_are_advisory(frame_factory):
    """Report a clearly non-normal sample without withholding the interval."""
    result = mean_confidence_interval(
        frame_factory({"x": [0.0] * 19 + [100.0]}),
        column="x",
    )
    assert result.shapiro_p_value is not None
    assert result.shapiro_p_value < result.normality_alpha
    assert "NON_NORMAL_SAMPLE" in {warning.code for warning in result.provenance.warnings}
    assert result.confidence_interval[0] < result.mean < result.confidence_interval[1]


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ([3.0, 3.0], "NORMALITY_UNAVAILABLE"),
        ([3.0, 3.0, 3.0], "NORMALITY_UNAVAILABLE"),
        (list(range(5001)), "NORMALITY_UNAVAILABLE"),
    ],
)
def test_normality_unavailable_domains(frame_factory, values, code):
    """Keep the interval while declining unsupported or undefined Shapiro-Wilk diagnostics."""
    result = mean_confidence_interval(frame_factory({"x": values}), column="x")
    assert result.shapiro_statistic is None
    assert result.shapiro_p_value is None
    assert code in {warning.code for warning in result.provenance.warnings}


@pytest.mark.parametrize(
    "options",
    [
        {"confidence_level": 0},
        {"confidence_level": 1},
        {"confidence_level": True},
        {"confidence_level": float("nan")},
        {"confidence_level": "0.95"},
        {"normality_alpha": 0},
        {"normality_alpha": 1},
        {"normality_alpha": True},
        {"population_variance": -1},
        {"population_variance": float("inf")},
        {"population_variance": True},
        {"approximate_z": 1},
        {"missing": "ignore"},
        {"unit": ""},
        {"cohort": ""},
    ],
)
def test_invalid_options(frame_factory, options):
    """Reject ambiguous inferential policies rather than silently coercing them."""
    with pytest.raises(ValidationError):
        mean_confidence_interval(frame_factory({"x": [1, 2, 3]}), column="x", **options)


@pytest.mark.parametrize("values", [[], [1.0], [None, None], [float("nan"), 1.0]])
def test_insufficient_valid_measurements(frame_factory, values):
    """Require enough valid observations to estimate unknown sample spread."""
    with pytest.raises(ValidationError, match="at least two"):
        mean_confidence_interval(frame_factory({"x": values}), column="x")


def test_missing_policy_and_invalid_measurements(frame_factory):
    """Apply explicit missing policy and retain strict shared measurement validation."""
    with pytest.raises(ValidationError, match="missing"):
        mean_confidence_interval(
            frame_factory({"x": [1.0, 2.0, None]}),
            column="x",
            missing="raise",
        )
    for values in ([True, False], ["1", "2"], [1.0, float("inf")]):
        with pytest.raises(ValidationError):
            mean_confidence_interval(frame_factory({"x": values}), column="x")


def test_numerical_overflow_is_explicit(frame_factory):
    """Never serialize a success-shaped interval containing nonfinite arithmetic."""
    with pytest.raises(ValidationError, match="remain finite"):
        mean_confidence_interval(frame_factory({"x": [1e308, 1e308]}), column="x")


def test_positive_affine_equivariance(frame_factory):
    """A positive unit transformation moves and scales every dimensional estimate."""
    values = np.array([8.0, 9.0, 10.0, 11.0, 12.0])
    baseline = mean_confidence_interval(frame_factory({"x": values}), column="x")
    transformed = mean_confidence_interval(frame_factory({"x": 3 * values + 7}), column="x")
    assert transformed.mean == pytest.approx(3 * baseline.mean + 7)
    assert transformed.standard_deviation == pytest.approx(3 * baseline.standard_deviation)
    assert transformed.standard_error == pytest.approx(3 * baseline.standard_error)
    assert transformed.confidence_interval == pytest.approx(
        tuple(3 * endpoint + 7 for endpoint in baseline.confidence_interval)
    )
    assert transformed.shapiro_statistic == pytest.approx(baseline.shapiro_statistic)
    assert transformed.shapiro_p_value == pytest.approx(baseline.shapiro_p_value)
