"""Independent calibration, R evidence, domains, portability and backend contracts."""

import json
from importlib.metadata import version
from typing import Any

import numpy as np
import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from lss4py import (
    AnalysisBundle,
    InputReference,
    QualityLossResult,
    ValidationError,
    __version__,
    quality_loss,
    quality_loss_analysis,
)
from lss4py._bundle_schema import bundle_fingerprint
from lss4py.domain import AnalyticalResult
from tests.reference_catalog import load_catalog

REFERENCE = next(e for e in load_catalog() if e["metadata"]["id"] == "r-sixsigma-baseline")
LOSS_CASES = [c for c in REFERENCE["expected"] if c["method"] == "ss.lfa"]
BACKENDS = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)


@BACKENDS
@pytest.mark.parametrize("case", LOSS_CASES, ids=lambda case: case["id"])
def test_genuine_r_loss_analysis(frame_factory, case):
    parameters = case["parameters"]
    convention = {"lfa-nominal": "nominal", "lfa-smaller": "smaller", "lfa-larger": "larger"}[
        case["id"]
    ]
    target = parameters["lfa.Y0"] if convention == "nominal" else None
    result = quality_loss_analysis(
        frame_factory({"x": [row["x"] for row in parameters["lfa.data"]]}),
        column="x",
        tolerance=parameters["lfa.Delta"],
        loss_at_tolerance=parameters["lfa.L0"],
        convention=convention,
        target=target,
        production_size=parameters.get("lfa.size"),
    )
    expected = case["expected"]["value"]
    assert result.coefficient == pytest.approx(expected["lfa.k"])
    assert result.mean_squared_deviation == pytest.approx(expected["lfa.MSD"])
    assert result.average_loss == pytest.approx(expected["lfa.avLoss"])
    assert result.total_loss == (None if expected["lfa.Loss"] == "NA" else expected["lfa.Loss"])


def test_r_scalar_parity_and_explicit_nonunit_tolerance_difference():
    for case in REFERENCE["expected"]:
        if case["method"] != "ss.lf":
            continue
        options = case["parameters"]
        result = quality_loss(
            options["lfa.Y1"],
            target=options["lfa.Y0"],
            tolerance=options["lfa.Delta"],
            loss_at_tolerance=options["lfa.L0"],
        )
        if case["id"] == "lf-nonunit-tolerance-difference":
            assert case["expected"]["value"] == 1
            assert result.losses.tolist() == [2]  # The declared boundary cost.
        else:
            assert result.losses == pytest.approx(np.atleast_1d(case["expected"]["value"]))


@BACKENDS
@pytest.mark.parametrize(
    "convention,values,expected,msd",
    [
        ("nominal", [8.0, 10.0, 12.0], [8.0, 0.0, 8.0], 8 / 3),
        ("smaller", [0.0, 1.0, 2.0], [0.0, 2.0, 8.0], 5 / 3),
        ("larger", [1.0, 2.0, 4.0], [32.0, 8.0, 2.0], 7 / 16),
    ],
)
def test_full_backend_payload_and_source_identity(
    frame_factory, neutral_payload, assert_equivalent, convention, values, expected, msd
):
    records = {"x": [*values, None], "id": ["a", "b", "c", "missing"]}
    source = frame_factory(records)
    options: dict[str, Any] = {
        "column": "x",
        "key_column": "id",
        "tolerance": 2,
        "loss_at_tolerance": 8,
        "convention": convention,
        "target": 10 if convention == "nominal" else None,
        "missing": "omit",
        "production_size": 100,
        "unit": "mm",
        "loss_unit": "USD",
    }
    result = quality_loss_analysis(source, **options)
    reference = quality_loss_analysis(pl.DataFrame(records), **options)
    assert_equivalent(neutral_payload(result), neutral_payload(reference))
    assert result.losses == pytest.approx(expected)
    assert result.mean_squared_deviation == pytest.approx(msd)
    assert (result.count, result.total, result.missing) == (3, 4, 1)
    assert result.source_positions.tolist() == [0, 1, 2]
    assert result.keys is not None
    assert result.keys.tolist() == ["a", "b", "c"]
    assert result.average_loss == pytest.approx(sum(expected) / 3)
    assert result.sample_loss == pytest.approx(sum(expected))
    assert result.total_loss == pytest.approx(100 * sum(expected) / 3)
    assert result.provenance.warnings[0].code == "MISSING_OMITTED"
    # Reusing the original must reproduce exclusions: analysis did not delete its row.
    with pytest.raises(ValidationError, match="missing measurements"):
        quality_loss_analysis(source, column="x", target=10, tolerance=2, loss_at_tolerance=8)
    for backend in ("polars", "pandas", "pyarrow"):
        assert len(result.to_frame(backend)) == 3
    restored = QualityLossResult.from_dict(json.loads(result.to_json()))
    assert restored.to_dict() == result.to_dict()
    assert restored.source_positions.dtype == np.int64


@settings(max_examples=60)
@given(
    tolerance=st.floats(min_value=0.01, max_value=100),
    cost=st.one_of(st.just(0.0), st.floats(min_value=1e-6, max_value=10000)),
)
def test_calibration_boundary_and_monotonicity(tolerance, cost):
    nominal = quality_loss(
        [10, 10 + tolerance], target=10, tolerance=tolerance, loss_at_tolerance=cost
    )
    smaller = quality_loss(
        [0, tolerance, 2 * tolerance],
        convention="smaller",
        tolerance=tolerance,
        loss_at_tolerance=cost,
    )
    larger = quality_loss(
        [tolerance, 2 * tolerance], convention="larger", tolerance=tolerance, loss_at_tolerance=cost
    )
    assert nominal.losses == pytest.approx([0, cost], rel=1e-10, abs=0)
    assert smaller.losses == pytest.approx([0, cost, 4 * cost], rel=1e-12, abs=0)
    assert larger.losses == pytest.approx([cost, cost / 4], rel=1e-12, abs=0)


@pytest.mark.parametrize(
    "options",
    [
        {"tolerance": 0},
        {"tolerance": -1},
        {"tolerance": True},
        {"tolerance": float("inf")},
        {"loss_at_tolerance": -1},
        {"loss_at_tolerance": "2"},
        {"target": None},
        {"convention": "auto"},
        {"convention": "smaller", "target": 1},
        {"convention": "larger", "target": float("inf")},
        {"production_size": 1.5},
        {"production_size": True},
        {"production_size": -1},
        {"unit": ""},
        {"loss_unit": None},
        {"tolerance": 1e-300},
        {"tolerance": 1e300},
    ],
)
def test_invalid_calibration(options):
    arguments: dict[str, Any] = {"tolerance": 2, "loss_at_tolerance": 8, "target": 10, **options}
    with pytest.raises(ValidationError):
        quality_loss(11, **arguments)


@pytest.mark.parametrize(
    "value", [True, "11", None, [1, None], [1, float("nan")], [float("inf")], [[1, 2]], []]
)
def test_invalid_scalar_sequence(value):
    with pytest.raises(ValidationError):
        quality_loss(value, target=10, tolerance=2, loss_at_tolerance=8)


@pytest.mark.parametrize("convention,value", [("smaller", -1), ("larger", 0), ("larger", -1)])
def test_invalid_characteristic_domains(convention, value):
    with pytest.raises(ValidationError):
        quality_loss(value, convention=convention, tolerance=2, loss_at_tolerance=8)


def test_zero_cost_zero_production_and_single_observation():
    result = quality_loss(12, target=10, tolerance=2, loss_at_tolerance=0, production_size=0)
    assert result.losses.tolist() == [0]
    assert result.total_loss == result.sample_loss == result.average_loss == 0
    assert result.mean_squared_deviation == 4
    assert result.provenance.backend == "unknown"
    assert result.provenance.parameters["input_kind"] == "scalar"
    assert quality_loss(12, target=10, tolerance=2, loss_at_tolerance=8).total_loss is None


def test_overflow_and_underflow_reject_nonportable_results():
    for value in (1e200, 1e-200):
        with pytest.raises(ValidationError, match="arithmetic"):
            quality_loss(value, target=0, tolerance=1, loss_at_tolerance=1)
    with pytest.raises(ValidationError, match="Production-loss"):
        quality_loss(2, target=0, tolerance=1, loss_at_tolerance=1, production_size=10**400)


def test_audited_loss_and_semantic_corruption(monkeypatch):
    result = quality_loss([8, 10, 12], target=10, tolerance=2, loss_at_tolerance=8)
    bundle = AnalysisBundle.capture(
        "Calibrated loss",
        results={"loss": result},
        inputs={
            "sample": InputReference.from_bytes("x.csv", b"x\n8\n10\n12\n", selection="All rows")
        },
        result_inputs={"loss": ["sample"]},
        cohort_definition="Original observations",
        software_versions={
            "lss4py": __version__,
            **{p: version(p) for p in ("numpy", "scipy", "narwhals")},
        },
    )
    import importlib

    kernel = importlib.import_module("lss4py._kernels.quality_loss")
    monkeypatch.setattr(
        kernel, "_estimates", lambda *a: pytest.fail("Restoration reran calculation")
    )
    assert isinstance(
        AnalysisBundle.from_json(bundle.to_json()).get_result("loss"), QualityLossResult
    )
    for field, value in (
        ("average_loss", 100),
        ("coefficient", 100),
        ("source_positions", [0, 0, 2]),
        ("production_size", 10),
    ):
        body = bundle.to_dict()
        payload = body["results"]["loss"]["result"]
        payload[field] = value
        with pytest.raises(ValidationError):
            AnalyticalResult.from_dict(payload)
        body["sha256"] = bundle_fingerprint({k: v for k, v in body.items() if k != "sha256"})
        with pytest.raises(ValidationError):
            AnalysisBundle.from_dict(body)


@pytest.mark.parametrize("cost", [5e-324, 2.2250738585e-313])
def test_subnormal_calibration_is_rejected(cost):
    with pytest.raises(ValidationError, match="underflowed"):
        quality_loss(12, target=10, tolerance=2, loss_at_tolerance=cost)
