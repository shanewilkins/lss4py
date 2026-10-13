"""Specification Z distance and explicit-shift behavior against genuine R evidence."""

import json

import pytest

from lss4py import Specification, ValidationError, capability_indices
from tests.reference_catalog import load_catalog

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
REFERENCE = next(e for e in load_catalog() if e["metadata"]["id"] == "r-sixsigma-baseline")
Z_CASES = [case for case in REFERENCE["expected"] if case["method"] == "ss.ca.z"]


@pytest.mark.parametrize("case", Z_CASES, ids=lambda case: case["id"])
def test_genuine_r_z_reference(frame_factory, case):
    """Match lower/upper/two-sided and signed R distances, including LT=True."""
    args = case["parameters"]
    result = capability_indices(
        frame_factory({"x": args["x"]}),
        column="x",
        specification=Specification("X", "mm", "lower", lsl=args.get("LSL"), usl=args.get("USL")),
        sigma_shift=1.5 if args.get("LT", False) else 0,
    )
    tolerance = case["tolerance"]
    assert result.z_score == pytest.approx(
        case["expected"]["value"], rel=tolerance["relative"], abs=tolerance["absolute"]
    )
    assert result.cpk is not None
    assert result.metadata["z_to_spec"] == pytest.approx(3 * result.cpk)


@pytest.mark.parametrize("shift", [0, 1.5, 2.0])
def test_shift_preserves_estimates_and_intervals(frame_factory, shift):
    """Only the declared Z adjustment changes; the underlying Cp/Cpk calculation is reused."""
    frame = frame_factory({"x": [2, 3, 4]})
    spec = Specification("X", "mm", "lower", lsl=0, usl=6)
    original = capability_indices(frame, column="x", specification=spec, ci=True)
    shifted = capability_indices(frame, column="x", specification=spec, ci=True, sigma_shift=shift)
    fields = (
        "cp",
        "cpk",
        "cpl",
        "cpu",
        "mean",
        "sigma",
        "count",
        "cp_confidence_interval",
        "cpk_confidence_interval",
    )
    assert {field: getattr(shifted, field) for field in fields} == {
        field: getattr(original, field) for field in fields
    }
    assert shifted.z_score == 3 - shift
    assert shifted.provenance.parameters["sigma_shift"] == shift
    assert ("SIGMA_SHIFT_ASSUMED" in {w.code for w in shifted.provenance.warnings}) == bool(shift)


@pytest.mark.parametrize(
    "shift", [-1, True, "1.5", None, float("nan"), float("inf"), -float("inf"), 10**400]
)
def test_invalid_shift_is_rejected(frame_factory, shift):
    """Never coerce ambiguous values or silently introduce a shift assumption."""
    with pytest.raises(ValidationError, match="sigma_shift must be a finite nonnegative number"):
        capability_indices(
            frame_factory({"x": [2, 3, 4]}),
            column="x",
            specification=Specification("X", "mm", "lower", usl=6),
            sigma_shift=shift,
        )


@pytest.mark.parametrize("values", [[], [None], [1], [1, 1], [1e308, -1e308]])
def test_z_remains_unavailable_with_cpk(frame_factory, values):
    """A shift cannot create a Z estimate when sample variation is unavailable."""
    result = capability_indices(
        frame_factory({"x": values}),
        column="x",
        specification=Specification("X", "mm", "lower", usl=6),
        sigma_shift=1.5,
    )
    assert (result.cpk, result.z_score, result.metadata["z_to_spec"]) == (None, None, None)
    json.dumps(result.to_dict(), allow_nan=False)


def test_missing_policy_and_signed_zero(frame_factory):
    """Exclusions preserve the retained count; a shift can make zero distance negative."""
    frame = frame_factory({"x": [2.0, 3.0, 4.0, None, float("nan")]})
    spec = Specification("X", "mm", "lower", lsl=3, usl=6)
    result = capability_indices(frame, column="x", specification=spec, sigma_shift=1.5)
    assert (result.count, result.missing, result.metadata["z_to_spec"], result.z_score) == (
        3,
        2,
        0,
        -1.5,
    )
    with pytest.raises(ValidationError, match="missing measurements"):
        capability_indices(frame, column="x", specification=spec, missing="raise", sigma_shift=1.5)


@pytest.mark.parametrize(
    ("lsl", "shift", "distance_available"), [(2e158, 0, False), (2e157, 1.7e308, True)]
)
def test_z_arithmetic_overflow(frame_factory, lsl, shift, distance_available):
    """Guard overflow of either derived distance or its shifted value, preserving Cpk."""
    result = capability_indices(
        frame_factory({"x": [0.0, 1e-150]}),
        column="x",
        specification=Specification("X", "mm", "higher", lsl=lsl),
        sigma_shift=shift,
    )
    assert result.cpk is not None
    assert result.z_score is None
    assert (result.metadata["z_to_spec"] is not None) == distance_available
    assert "NUMERICAL_Z_UNAVAILABLE" in {w.code for w in result.provenance.warnings}
    json.dumps(result.to_dict(), allow_nan=False)


def test_genuine_r_missing_limits_domain(frame_factory):
    """Retain the R rejection domain with a governed Python specification error."""
    case = next(c for c in REFERENCE["invalid"] if c["id"] == "z-no-limits")
    assert case["expected"]["status"] == "error"
    with pytest.raises(ValidationError, match="at least one specification limit"):
        capability_indices(
            frame_factory({"x": case["parameters"]["x"]}),
            column="x",
            specification=Specification("X", "mm", "lower"),
        )
