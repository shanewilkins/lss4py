"""Explicit short-/long-term capability-study orchestration contracts."""

import json
from importlib.metadata import version

import numpy as np
import polars as pl
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
from lss4py._bundle_schema import bundle_fingerprint
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


def neutral_study(result, neutral_payload):
    """Normalize only declared backend identity and timestamps at every result level."""
    payload = neutral_payload(result)
    for role in ("short_term", "long_term"):
        for kind in ("capability", "distribution"):
            child = getattr(result, f"{role}_{kind}")
            payload[f"{role}_{kind}"] = None if child is None else neutral_payload(child)
        payload["metadata"].pop(f"{role}_backend")
    return payload


def test_explicit_short_and_long_term_study(
    frame_factory, specification, neutral_payload, assert_equivalent
):
    short = frame_factory({"value": [9.0, 10.0, 11.0, 10.0, 9.5, 10.5]})
    long = frame_factory({"value": [7.0, 9.0, 10.0, 11.0, 13.0, 10.0]})
    result = capability_study(
        short,
        column="value",
        specification=specification,
        long_term_data=long,
    )
    reference = capability_study(
        pl.DataFrame({"value": [9.0, 10.0, 11.0, 10.0, 9.5, 10.5]}),
        column="value",
        specification=specification,
        long_term_data=pl.DataFrame({"value": [7.0, 9.0, 10.0, 11.0, 13.0, 10.0]}),
    )
    assert_equivalent(
        neutral_study(result, neutral_payload),
        neutral_study(reference, neutral_payload),
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


@pytest.mark.parametrize("long_backend", ["pandas", "pandas-indexed", "polars", "pyarrow"])
@pytest.mark.parametrize("missing", ["raise", "omit"])
def test_mixed_backend_study_parity(
    frame_factory,
    frame_factory_for_backend,
    backend,
    long_backend,
    missing,
    specification,
    neutral_payload,
    assert_equivalent,
):
    short_values = [9.0, 10.0, 11.0, 10.0]
    long_values = [7.0, 10.0, 13.0, 12.0]
    if missing == "omit":
        short_values.insert(1, None)
        long_values.append(None)
    result = capability_study(
        frame_factory({"value": short_values}),
        long_term_data=frame_factory_for_backend(long_backend)({"value": long_values}),
        column="value",
        specification=specification,
        missing=missing,
        confidence_level=0.9,
        normality_alpha=0.1,
    )
    reference = capability_study(
        pl.DataFrame({"value": short_values}),
        long_term_data=pl.DataFrame({"value": long_values}),
        column="value",
        specification=specification,
        missing=missing,
        confidence_level=0.9,
        normality_alpha=0.1,
    )
    for role, source_backend in (("short_term", backend), ("long_term", long_backend)):
        expected_backend = "pandas" if source_backend.startswith("pandas") else source_backend
        assert result.metadata[f"{role}_backend"] == expected_backend
        for kind in ("capability", "distribution"):
            child = getattr(result, f"{role}_{kind}")
            assert child.provenance.backend == expected_backend
            assert child.provenance.parameters["backend_version"] == version(expected_backend)
            assert child.count == 4
            assert child.total == (5 if missing == "omit" else 4)
            assert child.missing == (1 if missing == "omit" else 0)
        assert getattr(result, f"{role}_capability").confidence_level == 0.9
        assert getattr(result, f"{role}_distribution").normality_alpha == 0.1
    assert result.provenance.backend == result.metadata["short_term_backend"]
    assert_equivalent(
        neutral_study(result, neutral_payload), neutral_study(reference, neutral_payload)
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


@pytest.fixture
def study_evidence(frame_factory, specification):
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
    return bundle, result


def test_audited_bundle_restores_nested_study_evidence(study_evidence):
    bundle, result = study_evidence
    restored = AnalysisBundle.from_json(bundle.to_json()).get_result("study")
    assert isinstance(restored, CapabilityStudyResult)
    assert restored.to_dict() == result.to_dict()


@pytest.mark.parametrize("role", ["short_term", "long_term"])
@pytest.mark.parametrize("corruption", ["count", "specification", "child_type"])
def test_rejects_inconsistent_nested_evidence(study_evidence, role, corruption):
    bundle, _ = study_evidence
    body = bundle.to_dict()
    payload = body["results"]["study"]["result"]
    child = payload[f"{role}_capability"]
    if corruption == "count":
        child["count"] += 1
        child["total"] += 1
        message = "study counts disagree"
    elif corruption == "specification":
        child["lsl"] = 6.0
        message = "study specification disagrees"
    else:
        payload[f"{role}_capability"] = payload[f"{role}_distribution"]
        message = "capability-study evidence"
    assert_rejected_result_and_bundle(payload, body, message)


@pytest.mark.parametrize("missing_child", ["capability", "distribution", "nonconformance"])
def test_rejects_incomplete_long_term_evidence(study_evidence, missing_child):
    bundle, _ = study_evidence
    body = bundle.to_dict()
    payload = body["results"]["study"]["result"]
    payload[f"long_term_{missing_child}"] = None
    assert_rejected_result_and_bundle(payload, body, "Incomplete long-term")


def assert_rejected_result_and_bundle(payload, body, message):
    """Reseal edited evidence to distinguish semantic rejection from hash mismatch."""
    with pytest.raises(ValidationError, match=message):
        AnalyticalResult.from_dict(payload)
    body["sha256"] = bundle_fingerprint(
        {key: value for key, value in body.items() if key != "sha256"}
    )
    with pytest.raises(ValidationError, match=message):
        AnalysisBundle.from_json(json.dumps(body))
