"""Moving-range Phase I/II, R-reference, identity, and invalid-domain contracts."""

import json
from copy import deepcopy
from importlib.metadata import version
from typing import Any, cast

import numpy as np
import polars as pl
import pytest

from lss4py import (
    AnalysisBundle,
    ControlChartResult,
    InputReference,
    ValidationError,
    __version__,
    control_chart,
)
from lss4py.domain import AnalyticalResult
from tests.reference_catalog import load_catalog

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
REFERENCE = next(e for e in load_catalog() if e["metadata"]["id"] == "r-sixsigma-baseline")
R_CASES = [case for case in REFERENCE["expected"] if case["method"] == "ss.cc"]


@pytest.mark.parametrize("case", R_CASES, ids=lambda case: case["id"])
def test_genuine_sixsigma_reference(frame_factory, case):
    """Match genuine SixSigma MR Phase I/II limits, phase, and one-based signals."""
    parameters = case["parameters"]
    baseline = None
    if "cdata" in parameters:
        baseline = control_chart(
            frame_factory({"x": [row["x"] for row in parameters["cdata"]]}),
            column="x",
        )
    result = control_chart(
        frame_factory({"x": [row["x"] for row in parameters["data"]]}),
        column="x",
        baseline=baseline,
    )
    expected = case["expected"]["value"]
    tolerance = case["tolerance"]
    assert (result.lcl, result.center_line, result.ucl) == pytest.approx(
        (expected["LCL"], expected["CL"], expected["UCL"]),
        abs=tolerance["absolute"],
        rel=tolerance["relative"],
    )
    assert result.phase == expected["phase"]
    expected_signals = expected["out"]
    if isinstance(expected_signals, int):
        expected_signals = [expected_signals]
    assert (result.signal_indices + 1).tolist() == expected_signals


def test_complete_phase_i_contract_and_pair_identity(
    frame_factory, neutral_payload, assert_equivalent, backend
):
    """Preserve adjacent source positions/keys, source data, and complete payload parity."""
    records = {
        "sample": ["a", "b", "c", "d", "e"],
        "x": [10.0, 11.0, 12.0, 13.0, 30.0],
    }
    frame = frame_factory(records)
    if backend == "pyarrow":
        original = frame
    else:
        original = frame.to_native() if hasattr(frame, "to_native") else frame
        original = original.clone() if isinstance(original, pl.DataFrame) else deepcopy(original)
    result = control_chart(frame, column="x", key_column="sample", unit="minutes")
    reference = control_chart(
        pl.DataFrame(records), column="x", key_column="sample", unit="minutes"
    )
    assert_equivalent(neutral_payload(result), neutral_payload(reference))
    assert result.moving_ranges.tolist() == [1, 1, 1, 17]
    assert result.pair_start_positions.tolist() == [0, 1, 2, 3]
    assert result.pair_end_positions.tolist() == [1, 2, 3, 4]
    assert result.pair_start_keys is not None
    assert result.pair_end_keys is not None
    assert result.pair_start_keys.tolist() == ["a", "b", "c", "d"]
    assert result.pair_end_keys.tolist() == ["b", "c", "d", "e"]
    assert result.signal_source_positions.tolist() == [4]
    assert result.to_frame().to_dict(as_series=False)["signal"] == [
        False,
        False,
        False,
        True,
    ]
    assert result.provenance.backend == ("pandas" if backend.startswith("pandas") else backend)
    if backend == "pyarrow":
        assert frame is original
    else:
        assert frame.equals(original)


def test_phase_ii_reuses_intact_phase_i_limits(frame_factory):
    """Copy frozen Phase I limits and retain a fingerprint of the exact baseline result."""
    baseline = control_chart(frame_factory({"x": [10, 11, 9, 10, 14, 13]}), column="x")
    result = control_chart(
        frame_factory({"x": [10, 20, 19]}),
        column="x",
        baseline=baseline,
    )
    assert result.phase == "II"
    assert (result.lcl, result.center_line, result.ucl) == (
        baseline.lcl,
        baseline.center_line,
        baseline.ucl,
    )
    assert result.baseline_observation_count == 6
    assert result.baseline_result_fingerprint
    assert result.provenance.parameters["baseline_result_fingerprint"] == (
        result.baseline_result_fingerprint
    )
    assert result.signal_indices.tolist() == [0]
    assert {note.code for note in result.provenance.assumptions} == {
        "SEQUENTIAL_COMPARABLE_OBSERVATIONS",
        "FROZEN_PHASE_I_BASELINE",
    }


def test_result_roundtrip_and_strict_json(frame_factory):
    """Restore typed arrays and portable baseline evidence without recalculation."""
    baseline = control_chart(
        frame_factory({"sample": [1, 2, 3], "x": [2.0, 4.0, 3.0]}),
        column="x",
        key_column="sample",
    )
    restored = AnalyticalResult.from_dict(json.loads(baseline.to_json()))
    assert isinstance(restored, ControlChartResult)
    assert restored.to_dict() == baseline.to_dict()
    assert restored.moving_ranges.dtype == np.float64
    assert restored.pair_start_positions.dtype == np.int64
    corrupted = baseline.to_dict()
    corrupted["signal_indices"] = [0]
    with pytest.raises(ValidationError, match="signals disagree"):
        AnalyticalResult.from_dict(corrupted)


def test_audited_bundle_roundtrip_without_recalculation(frame_factory):
    """Persist and restore complete chart evidence through the portable bundle schema."""
    result = control_chart(frame_factory({"x": [1.0, 2.0, 1.0]}), column="x")
    raw = b"x\n1\n2\n1\n"
    bundle = AnalysisBundle.capture(
        "Moving-range baseline",
        results={"mr": result},
        inputs={
            "observations": InputReference.from_bytes(
                "observations.csv",
                raw,
                selection="All three sequential observations",
            )
        },
        result_inputs={"mr": ["observations"]},
        cohort_definition="Three sequential observations",
        software_versions={
            "lss4py": __version__,
            "narwhals": version("narwhals"),
            "numpy": version("numpy"),
            "scipy": version("scipy"),
            result.provenance.backend: version(result.provenance.backend),
        },
        context={"observation_order": "source row order"},
    )
    restored = AnalysisBundle.from_json(bundle.to_json())
    assert restored.to_json() == bundle.to_json()
    assert isinstance(restored.get_result("mr"), ControlChartResult)
    restored.verify_inputs({"observations": raw})


@pytest.mark.parametrize(
    ("records", "message"),
    [
        ({"x": []}, "at least two"),
        ({"x": [1]}, "at least two"),
        ({"x": [1, None]}, "missing measurements"),
        ({"x": [1.0, float("nan")]}, "missing measurements"),
        ({"x": [1.0, float("inf")]}, "contains infinity"),
        ({"x": [1e308, -1e308]}, "arithmetic overflowed"),
        ({"x": ["1", "2"]}, "numeric measurements"),
        ({"x": [True, False]}, "numeric measurements"),
    ],
)
def test_reject_invalid_measurement_domains(frame_factory, records, message):
    """Reject incomplete, nonnumeric, nonfinite, and numerically unsafe sequences."""
    with pytest.raises(ValidationError, match=message):
        control_chart(frame_factory(records), column="x")


@pytest.mark.parametrize(
    "options",
    [
        {"chart": "individuals"},
        {"nsigmas": 0},
        {"nsigmas": -1},
        {"nsigmas": float("nan")},
        {"nsigmas": True},
        {"unit": ""},
    ],
)
def test_reject_invalid_chart_policy(frame_factory, options):
    """Keep the first SPC slice narrow and require explicit finite policy."""
    with pytest.raises(ValidationError):
        control_chart(frame_factory({"x": [1, 2]}), column="x", **options)


def test_reject_duplicate_keys_and_changed_baseline(frame_factory):
    """Require portable pair identity and reject edited or mismatched Phase I evidence."""
    with pytest.raises(ValidationError, match="duplicate keys"):
        control_chart(
            frame_factory({"key": ["a", "a"], "x": [1, 2]}),
            column="x",
            key_column="key",
        )
    baseline = control_chart(frame_factory({"x": [1, 2, 3]}), column="x")
    baseline.ucl += 1
    with pytest.raises(ValidationError, match="limits differ"):
        control_chart(frame_factory({"x": [1, 4]}), column="x", baseline=baseline)
    with pytest.raises(ValidationError, match="Phase I"):
        control_chart(
            frame_factory({"x": [1, 4]}),
            column="x",
            baseline=cast(Any, object()),
        )


def test_reject_phase_ii_as_baseline_and_nsigma_mismatch(frame_factory):
    """Prevent chained recalibration and require the declared Phase I limit width."""
    phase_i = control_chart(frame_factory({"x": [1, 2, 3]}), column="x", nsigmas=2)
    phase_ii = control_chart(
        frame_factory({"x": [1, 4]}),
        column="x",
        baseline=phase_i,
        nsigmas=2,
    )
    with pytest.raises(ValidationError, match="Phase I"):
        control_chart(
            frame_factory({"x": [1, 4]}),
            column="x",
            baseline=phase_ii,
            nsigmas=2,
        )
    with pytest.raises(ValidationError, match="must match"):
        control_chart(frame_factory({"x": [1, 4]}), column="x", baseline=phase_i)


@pytest.mark.parametrize("baseline_unit", [None, "minutes"])
def test_phase_ii_preserves_baseline_units(frame_factory, baseline_unit):
    baseline = control_chart(frame_factory({"x": [1.0, 2.0, 3.0]}), column="x", unit=baseline_unit)
    for explicit_unit in (None, baseline_unit):
        result = control_chart(
            frame_factory({"x": [1.0, 2.0, 3.0]}),
            column="x",
            baseline=baseline,
            unit=explicit_unit,
        )
        assert result.unit == baseline_unit
        assert result.provenance.parameters["unit"] == baseline_unit
        assert result.signal_indices.tolist() == []
    with pytest.raises(ValidationError, match="unit must match"):
        control_chart(
            frame_factory({"x": [60.0, 120.0, 180.0]}),
            column="x",
            baseline=baseline,
            unit="seconds",
        )


@pytest.mark.parametrize("scale", [0.0, 1e-15, 1.0, 1e100])
def test_baseline_limit_integrity_across_scales(frame_factory, scale):
    baseline = control_chart(frame_factory({"x": [0.0, scale, 2 * scale]}), column="x")
    restored = AnalyticalResult.from_dict(json.loads(baseline.to_json()))
    assert isinstance(restored, ControlChartResult)
    monitoring = frame_factory({"x": [0.0, max(1e-13, 100 * scale)]})
    intact = control_chart(monitoring, column="x", baseline=restored)
    assert intact.signal_indices.tolist() == [0]
    restored.ucl = max(9e-13, 900 * scale)
    with pytest.raises(ValidationError, match="limits differ"):
        control_chart(monitoring, column="x", baseline=restored)


@pytest.mark.parametrize(
    ("starts", "ends", "message"),
    [
        (["a", "b"], ["wrong", "wrong"], "adjacent observations"),
        (["a", "b"], ["b", "a"], "Duplicate"),
        (["a", None], [None, "c"], "portable"),
        (["a", " "], [" ", "c"], "portable"),
        (["a", ["b"]], [["b"], "c"], "portable"),
        (["a", {"id": "b"}], [{"id": "b"}, "c"], "portable"),
        (["a", 1], [1.0, "c"], "adjacent observations"),
    ],
)
def test_reject_inconsistent_portable_pair_keys(frame_factory, starts, ends, message):
    baseline = control_chart(
        frame_factory({"x": [1.0, 2.0, 3.0], "key": ["a", "b", "c"]}),
        column="x",
        key_column="key",
    )
    payload = json.loads(baseline.to_json())
    payload["pair_start_keys"] = starts
    payload["pair_end_keys"] = ends
    with pytest.raises(ValidationError, match=message):
        AnalyticalResult.from_dict(payload)
    baseline.pair_start_keys = np.array(starts, dtype=object)
    baseline.pair_end_keys = np.array(ends, dtype=object)
    with pytest.raises(ValidationError, match="not an intact"):
        control_chart(frame_factory({"x": [1.0, 2.0]}), column="x", baseline=baseline)
