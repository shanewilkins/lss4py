"""Explicit row identity, provenance and detached native-frame result conversions."""

import json

import pytest

from lss4py import AnalysisBundle, ValidationError, describe, select_analysis, wait_time

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)


@pytest.mark.parametrize("keys", [["001", "002"], [7, 11], [1.25, 2.5], [False, True]])
def test_explicit_scalar_keys_survive_serialization(backend, frame_factory, keys):
    result = wait_time(
        frame_factory({"id": keys, "l": [10.0, 20.0], "c": [2.0, 4.0]}),
        lead_time_column="l",
        cycle_time_column="c",
        key_column="id",
        unit="minutes",
    )
    assert result.keys is not None
    assert result.keys.tolist() == keys
    assert json.loads(result.to_json())["keys"] == keys
    assert result.to_frame()["key"].to_list() == keys
    assert result.metadata["row_positions"] == [0, 1]


@pytest.mark.parametrize("keys", [["a", "a"], [1, 1], [None, "a"], ["", "a"], [float("nan"), 1.0]])
def test_ambiguous_keys_fail(backend, frame_factory, keys):
    with pytest.raises(ValidationError):
        wait_time(
            frame_factory({"id": keys, "l": [10.0, 20.0], "c": [2.0, 4.0]}),
            lead_time_column="l",
            cycle_time_column="c",
            key_column="id",
        )


@pytest.mark.parametrize("target", ["pandas", "polars", "pyarrow"])
def test_native_export_retains_positions_and_does_not_mutate_result(backend, frame_factory, target):
    result = wait_time(
        frame_factory({"l": [10.0], "c": [2.0]}), lead_time_column="l", cycle_time_column="c"
    )
    snapshot = result.to_dict()
    native = result.to_frame(target)
    assert len(native) == 1
    assert result.to_dict() == snapshot
    assert result.to_frame()["key"].to_list() == [0]


def test_complete_result_context_without_implicit_filter(backend, frame_factory):
    result = describe(frame_factory({"x": [1.0, 2.0, None]}), column="x", missing="omit")
    assert result.provenance.input_schema_fingerprint is not None
    assert len(result.provenance.input_schema_fingerprint) == 64
    assert result.provenance.parameters["runtime_versions"]["numpy"]
    assert result.provenance.parameters["missing"] == "omit"
    assert result.provenance.cohort_definition
    assert result.total == 3 and result.missing == 1


def test_explicit_method_selection_records_without_executing(backend, frame_factory):
    selection = select_analysis(
        "describe",
        reason="Summarize supplied observations",
        cohort="All two observations",
        design_type="observational",
    )
    result = describe(frame_factory({"x": [1.0, 3.0]}), column="x")
    selection.record(result)
    restored = AnalysisBundle.from_json(AnalysisBundle("Selected", [result]).to_json())
    assert restored.results[0].metadata["analysis_selection"]["reason"] == selection.reason
    assert selection.suitability.outcome_types == ("numeric_measurement",)
    assert selection.suitability.predictor_types == ("none",)


def test_selection_rejects_incompatible_method_or_design(backend, frame_factory):
    result = describe(frame_factory({"x": [1.0]}), column="x")
    choice = select_analysis(
        "wait_time", reason="Declared wait measurement", cohort="All", design_type="observational"
    )
    with pytest.raises(ValidationError, match="match"):
        choice.record(result)
    with pytest.raises(ValidationError, match="design"):
        select_analysis("describe", reason="A reason", cohort="All", design_type="randomized_trial")
