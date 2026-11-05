"""Explicit short-/long-term capability-study orchestration contracts."""

import json
from importlib.metadata import version

import numpy as np
import pytest

from lss4py import (
    AnalysisBundle,
    CapabilityStudyResult,
    InputReference,
    Specification,
    ValidationError,
    __version__,
    capability_study,
)
from lss4py.domain import AnalyticalResult

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)


@pytest.fixture
def specification():
    return Specification(
        "Fill volume",
        "ml",
        "target",
        target=10,
        lsl=8,
        usl=12,
    )


def test_explicit_short_and_long_term_study(frame_factory, specification, assert_equivalent):
    short = frame_factory({"value": [9.0, 10.0, 11.0, 10.0, 9.5, 10.5]})
    long = frame_factory({"value": [7.0, 9.0, 10.0, 11.0, 13.0, 10.0]})
    result = capability_study(
        short,
        column="value",
        specification=specification,
        long_term_data=long,
    )
    reference = capability_study(
        frame_factory({"value": [9.0, 10.0, 11.0, 10.0, 9.5, 10.5]}),
        column="value",
        specification=specification,
        long_term_data=frame_factory({"value": [7.0, 9.0, 10.0, 11.0, 13.0, 10.0]}),
    )

    def without_created_at(value):
        if isinstance(value, dict):
            return {
                key: without_created_at(item) for key, item in value.items() if key != "created_at"
            }
        if isinstance(value, list):
            return [without_created_at(item) for item in value]
        return value

    assert_equivalent(
        without_created_at(result.to_dict()),
        without_created_at(reference.to_dict()),
    )
    assert result.short_term_capability is not None
    assert result.short_term_distribution is not None
    assert result.long_term_capability is not None
    assert result.long_term_distribution is not None
    assert result.short_term_capability.variation_estimator == "overall_sample_std"
    assert result.short_term_nonconformance == {
        "total": 6,
        "below_lsl": 0,
        "above_usl": 0,
        "nonconforming": 0,
        "nonconforming_rate": 0,
    }
    assert result.long_term_nonconformance == {
        "total": 6,
        "below_lsl": 1,
        "above_usl": 1,
        "nonconforming": 2,
        "nonconforming_rate": 1 / 3,
    }
    assert result.provenance.parameters["sample_role_policy"] == (
        "explicit_short_term_and_optional_long_term"
    )


def test_long_term_sample_is_optional(frame_factory, specification):
    result = capability_study(
        frame_factory({"value": [9.0, 10.0, 11.0]}),
        column="value",
        specification=specification,
    )
    assert result.long_term_capability is None
    assert result.long_term_distribution is None
    assert result.long_term_nonconformance is None
    assert {note.code for note in result.provenance.assumptions} == {
        "EXPLICIT_SAMPLE_ROLES",
        "STABILITY_NOT_ESTABLISHED",
    }


def test_roundtrip_restores_nested_typed_evidence(frame_factory, specification):
    result = capability_study(
        frame_factory({"value": [9.0, 10.0, 11.0]}),
        column="value",
        specification=specification,
        long_term_data=frame_factory({"value": [8.5, 10.0, 11.5]}),
    )
    restored = AnalyticalResult.from_dict(json.loads(result.to_json()))
    assert isinstance(restored, CapabilityStudyResult)
    assert restored.to_dict() == result.to_dict()
    assert restored.short_term_distribution is not None
    assert restored.short_term_distribution.values.dtype == np.float64


def test_rejects_missing_values_by_default_in_either_sample(frame_factory, specification):
    with pytest.raises(ValidationError, match="missing measurements"):
        capability_study(
            frame_factory({"value": [9.0, None, 11.0]}),
            column="value",
            specification=specification,
        )
    with pytest.raises(ValidationError, match="missing measurements"):
        capability_study(
            frame_factory({"value": [9.0, 10.0, 11.0]}),
            column="value",
            specification=specification,
            long_term_data=frame_factory({"value": [9.0, None, 11.0]}),
        )


def test_schema_rejects_edited_observed_risk(frame_factory, specification):
    result = capability_study(
        frame_factory({"value": [7.0, 10.0, 13.0]}),
        column="value",
        specification=specification,
    )
    payload = result.to_dict()
    payload["short_term_nonconformance"]["below_lsl"] = 0
    payload["short_term_nonconformance"]["above_usl"] = 0
    payload["short_term_nonconformance"]["nonconforming"] = 0
    payload["short_term_nonconformance"]["nonconforming_rate"] = 0
    with pytest.raises(ValidationError, match="disagree with observations"):
        AnalyticalResult.from_dict(payload)


def test_audited_bundle_restores_nested_study_evidence(frame_factory, specification):
    short_raw = b"value\n9\n10\n11\n"
    long_raw = b"value\n8.5\n10\n11.5\n"
    result = capability_study(
        frame_factory({"value": [9.0, 10.0, 11.0]}),
        column="value",
        specification=specification,
        long_term_data=frame_factory({"value": [8.5, 10.0, 11.5]}),
    )
    bundle = AnalysisBundle.capture(
        "Capability study",
        results={"study": result},
        inputs={
            "short": InputReference.from_bytes(
                "short.csv", short_raw, selection="Explicit short-term sample"
            ),
            "long": InputReference.from_bytes(
                "long.csv", long_raw, selection="Explicit long-term sample"
            ),
        },
        result_inputs={"study": ["short", "long"]},
        cohort_definition="Explicit short- and long-term samples",
        software_versions={
            "lss4py": __version__,
            "narwhals": version("narwhals"),
            "numpy": version("numpy"),
            "scipy": version("scipy"),
            result.provenance.backend: version(result.provenance.backend),
        },
        specifications={"ctq": specification},
        result_specifications={"study": ["ctq"]},
    )
    restored = AnalysisBundle.from_json(bundle.to_json()).get_result("study")
    assert isinstance(restored, CapabilityStudyResult)
    assert restored.to_dict() == result.to_dict()
