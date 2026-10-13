"""Governed Cp/Cpk reference, edge-domain, serialization, and backend contracts."""

import json
import math
from typing import Any, cast

import polars as pl
import pytest

from lss4py import CapabilityResult, Specification, ValidationError, capability_indices
from tests.reference_catalog import load_catalog

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
REFERENCE = next(e for e in load_catalog() if e["metadata"]["id"] == "r-sixsigma-baseline")
R_CASES = [c for c in REFERENCE["expected"] if c["method"] in {"ss.ca.cp", "ss.ca.cpk"}]


@pytest.mark.parametrize("case", R_CASES, ids=[c["id"] for c in R_CASES])
def test_genuine_sixsigma_reference(frame_factory, case):
    """Execute only supported Cp/Cpk claims against checksummed genuine R outputs."""
    args = case["parameters"]
    specification = Specification("Length", "mm", "lower", lsl=args.get("LSL"), usl=args.get("USL"))
    result = capability_indices(
        frame_factory({"x": args["x"]}),
        column="x",
        specification=specification,
        ci=args.get("ci", False),
    )
    field = "cp" if case["method"] == "ss.ca.cp" else "cpk"
    if args.get("ci"):
        field += "_confidence_interval"
    tolerance = case["tolerance"]
    assert getattr(result, field) == pytest.approx(
        case["expected"]["value"], abs=tolerance["absolute"], rel=tolerance["relative"]
    )


def test_complete_contract(frame_factory, neutral_payload, assert_equivalent, backend):
    """Retain specification, exclusions, provenance and input order across backends."""
    records = {"x": [8.0, 9.0, 10.0, 11.0, 12.0, None, float("nan")]}
    frame = frame_factory(records)
    original = frame.to_native() if hasattr(frame, "to_native") else frame
    original = original.clone() if isinstance(original, pl.DataFrame) else original
    if backend.startswith("pandas"):
        original = frame.copy(deep=True)
    spec = Specification(
        "Length", "mm", "target", target=10, lsl=7, usl=14, cohort="Explicitly selected cohort"
    )
    result = capability_indices(frame, column="x", specification=spec, ci=True)
    reference = capability_indices(pl.DataFrame(records), column="x", specification=spec, ci=True)
    assert_equivalent(neutral_payload(result), neutral_payload(reference))
    assert json.loads(json.dumps(result.to_dict(), allow_nan=False))["cpk"] == result.cpk
    assert json.loads(result.to_json())["result_type"] == "CapabilityResult"
    if backend == "pyarrow":
        assert frame is original  # Arrow tables are immutable; NaN makes equals nonreflexive.
    else:
        assert frame.equals(original)


@pytest.fixture
def sample_result(frame_factory):
    """A cohort with excluded measurements and explicit specification intent."""
    spec = Specification(
        "Length", "mm", "target", target=10, lsl=7, usl=14, cohort="Explicitly selected cohort"
    )
    return capability_indices(
        frame_factory({"x": [8.0, 9.0, 10.0, 11.0, 12.0, None, float("nan")]}),
        column="x",
        specification=spec,
        ci=True,
    )


def test_sample_components_and_exclusions(sample_result):
    """Component values use only retained measurements and the declared limits."""
    assert isinstance(sample_result, CapabilityResult)
    assert (sample_result.total, sample_result.count, sample_result.missing) == (7, 5, 2)
    assert (sample_result.cpl, sample_result.cpu) == pytest.approx(
        (1 / math.sqrt(2.5), 4 / (3 * math.sqrt(2.5)))
    )
    assert sample_result.cpk == sample_result.cpl


def test_specification_and_interpretation_metadata(sample_result):
    """Record the complete declaration and explicit overall-variation policy."""
    parameters = sample_result.provenance.parameters
    assert parameters["specification"]["usl"] == 14
    assert parameters["ddof"] == 1
    assert sample_result.provenance.cohort_definition == "Explicitly selected cohort"
    assert (sample_result.unit, sample_result.target, sample_result.z_score) == (
        "mm",
        10,
        sample_result.metadata["z_to_spec"],
    )


def test_sample_diagnostics(sample_result):
    """Exclusions and untested assumptions remain auditable."""
    assert {w.code for w in sample_result.provenance.warnings} == {
        "MISSING_OMITTED",
        "SMALL_SAMPLE",
    }
    assert sample_result.provenance.assumptions[0].code == "NORMAL_STABLE_INDEPENDENT"


@pytest.mark.parametrize(
    ("lsl", "usl", "cp", "cpk"),
    [(0, 6, 1, 1), (0, None, 1, 1), (None, 6, 1, 1), (4, 6, 1 / 3, -1 / 3), (3, 6, 0.5, 0)],
)
def test_independent_formula_and_signed_components(frame_factory, lsl, usl, cp, cpk):
    """The triple 2,3,4 has mean 3 and sample std 1; retain zero/negative Cpk."""
    result = capability_indices(
        frame_factory({"x": [2, 3, 4]}),
        column="x",
        specification=Specification("X", "mm", "lower", lsl=lsl, usl=usl),
        ci=True,
    )
    assert result.mean == 3
    assert result.sigma == 1
    assert result.cp == pytest.approx(cp)
    assert result.cpk == pytest.approx(cpk)
    assert result.confidence_interval == result.cpk_confidence_interval
    assert result.cpk_confidence_interval is not None
    lower, upper = result.cpk_confidence_interval
    assert lower < cpk < upper
    if cpk == 0:
        assert (lower, upper) == pytest.approx((-0.377195244692057, 0.377195244692057))


@pytest.mark.parametrize(
    ("values", "warning"),
    [
        ([], "INSUFFICIENT_DATA"),
        ([None], "INSUFFICIENT_DATA"),
        ([2], "INSUFFICIENT_DATA"),
        ([2, 2], "ZERO_VARIATION"),
        ([1e308, -1e308], "NUMERICAL_UNAVAILABLE"),
        ([0.0, 1e-200], "NUMERICAL_UNAVAILABLE"),
    ],
)
def test_unavailable_estimates_are_strict_json(frame_factory, values, warning):
    """Small, constant and numerically degenerate cohorts never emit infinite capability."""
    result = capability_indices(
        frame_factory({"x": values}),
        column="x",
        specification=Specification("X", "mm", "lower", usl=4),
        ci=True,
    )
    assert warning in {w.code for w in result.provenance.warnings}
    assert result.cp is None
    assert result.cpk is None
    assert result.confidence_interval is None
    json.dumps(result.to_dict(), allow_nan=False)


@pytest.mark.parametrize("values", [["1", "2"], [True, False], [1.0, float("inf")]])
def test_reject_nonmeasurement_values(frame_factory, values):
    """Do not coerce strings/booleans or admit infinite measurements."""
    with pytest.raises(ValidationError):
        capability_indices(
            frame_factory({"x": values}),
            column="x",
            specification=Specification("X", "mm", "lower", usl=4),
        )


@pytest.mark.parametrize(
    "options",
    [
        {"missing": "ignore"},
        {"ci": 1},
        {"confidence_level": 0},
        {"confidence_level": 1},
        {"confidence_level": True},
        {"confidence_level": float("nan")},
        {"confidence_level": "0.95"},
    ],
)
def test_reject_invalid_policy(frame_factory, options):
    """Require explicit valid policies and finite open-interval confidence levels."""
    with pytest.raises(ValidationError):
        capability_indices(
            frame_factory({"x": [1, 2]}),
            column="x",
            specification=Specification("X", "mm", "lower", usl=4),
            **options,
        )


def test_missing_and_specification_validation(frame_factory):
    """Cover genuine R invalid domains plus strict Python specification/exclusion policy."""
    frame = frame_factory({"x": [1.0, None, 2.0]})
    with pytest.raises(ValidationError, match="missing measurements"):
        capability_indices(
            frame,
            column="x",
            specification=Specification("X", "mm", "lower", usl=4),
            missing="raise",
        )
    with pytest.raises(ValidationError, match="one specification limit"):
        capability_indices(frame, column="x", specification=Specification("X", "mm", "lower"))
    with pytest.raises(ValidationError, match="must be a Specification"):
        capability_indices(frame, column="x", specification=cast(Any, {"usl": 4}))
    with pytest.raises(ValidationError, match="Select groups"):
        capability_indices(
            frame,
            column="x",
            specification=Specification("X", "mm", "lower", usl=4, group_by=("team",)),
        )
    with pytest.raises(ValidationError, match="Missing required columns"):
        capability_indices(
            frame, column="absent", specification=Specification("X", "mm", "lower", usl=4)
        )


def test_positive_affine_invariance_and_confidence_width(frame_factory):
    """Unit changes preserve indices; increasing confidence widens the interval."""
    values = list(range(1, 61))
    first = capability_indices(
        frame_factory({"x": values}),
        specification=Specification("X", "mm", "lower", lsl=0, usl=70),
        column="x",
        ci=True,
    )
    converted = capability_indices(
        frame_factory({"x": [v * 10 + 4 for v in values]}),
        specification=Specification("X", "other", "lower", lsl=4, usl=704),
        column="x",
        ci=True,
    )
    assert (first.cp, first.cpk) == pytest.approx((converted.cp, converted.cpk))
    wider = capability_indices(
        frame_factory({"x": values}),
        specification=Specification("X", "mm", "lower", lsl=0, usl=70),
        confidence_level=0.99,
        column="x",
        ci=True,
    )
    assert wider.cpk_confidence_interval is not None
    assert first.cpk_confidence_interval is not None
    assert wider.cpk_confidence_interval[0] < first.cpk_confidence_interval[0]
    assert wider.cpk_confidence_interval[1] > first.cpk_confidence_interval[1]
    assert first.provenance.warnings == []


@pytest.mark.parametrize(
    "case",
    [c for c in REFERENCE["invalid"] if c["method"] in {"ss.ca.cp", "ss.ca.cpk"}],
    ids=lambda c: c["id"],
)
def test_genuine_r_invalid_domains(frame_factory, case):
    """Preserve R invalid-domain rejection, with typed Python errors and messages."""
    args = case["parameters"]
    spec = Specification("X", "mm", "lower", lsl=args.get("LSL"), usl=args.get("USL"))
    assert case["expected"]["status"] == "error"
    with pytest.raises(ValidationError):
        capability_indices(frame_factory({"x": args["x"]}), column="x", specification=spec)


@pytest.mark.parametrize(
    ("limit", "warning"),
    [(1e200, "NUMERICAL_UNAVAILABLE"), (1.5e158, "NUMERICAL_INTERVAL_UNAVAILABLE")],
)
def test_extreme_index_and_interval_guard(frame_factory, limit, warning):
    """Even finite data can overflow indices or intervals; preserve strict JSON."""
    result = capability_indices(
        frame_factory({"x": [0.0, 1e-150]}),
        column="x",
        specification=Specification("X", "mm", "lower", usl=limit),
        ci=True,
        confidence_level=0.99,
    )
    assert warning in {w.code for w in result.provenance.warnings}
    assert result.cpk_confidence_interval is None
    json.dumps(result.to_dict(), allow_nan=False)
