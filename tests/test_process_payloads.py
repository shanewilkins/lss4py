"""Portable process validation retains wire data while rejecting ambiguous shapes."""

import hashlib
import json
from pathlib import Path

import pytest

from lss4py import ValidationError
from lss4py.integration import ProcessProjection

ROOT = Path(__file__).parent / "fixtures/ecosystem/book-model"


@pytest.fixture(params=["0.4.3", "0.5.0"])
def body(request):
    """Supply authored JSON without validating it before each mutation."""
    root = ROOT if request.param == "0.5.0" else ROOT.parent / "legacy-0.4.3/book-model"
    manifest = json.loads((root / "manifest.json").read_text())
    return {
        "schema_version": "1.0",
        "flo_version": manifest["producer"]["version"],
        "source": manifest["observations"]["dataset_id"],
        "model_revision": manifest["source"]["revision"],
        "export": json.loads((root / "process-export.json").read_text()),
        "step_mapping": json.loads((root / "activity-mapping.json").read_text()),
    }


def _set(body, path, value):
    """Change one nested value while keeping the surrounding payload valid."""
    for part in path[:-1]:
        body = body[part]
    body[path[-1]] = value


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), 1),
        (("source",), True),
        (("source",), "\x1c"),
        (("model_revision",), "  "),
        (("export", "process", "id"), 12),
        (("export", "process", "name"), None),
        (("export", "nodes"), []),
        (("export", "nodes", 0), "start"),
        (("export", "nodes", 0, "id"), True),
        (("export", "nodes", 0, "kind"), "branch"),
        (("export", "nodes", 0, "subprocess_parent"), "parent"),
        (("export", "nodes", 0, "branch"), {}),
        (("export", "edges"), {}),
        (("export", "edges", 0), []),
        (("export", "edges", 0, "source"), []),
        (("export", "edges", 0, "target"), {}),
        (("export", "edges", 0, "route"), "dispatch"),
        (("export", "edges", 0, "edge_type"), "conditional"),
        (("export", "edges", 0, "rework"), 1),
        (("export", "edges", 0, "rework"), "false"),
        (("export", "edges", 0, "handoff"), []),
        (("export", "edges", 0, "outcome"), 1),
        (("export", "edges", 0, "outcome"), "\t"),
        (("step_mapping",), {}),
        (("step_mapping",), []),
        (("step_mapping", "Wash"), 1),
    ],
)
def test_malformed_shapes_have_field_paths_and_public_errors(body, path, value):
    _set(body, path, value)
    body["export"]["private_annotation"] = "NOT_FOR_DIAGNOSTICS"
    with pytest.raises(ValidationError) as error:
        ProcessProjection.from_json(json.dumps(body))
    assert type(error.value) is ValidationError
    assert ".".join(map(str, path)) in str(error.value)
    assert "NOT_FOR_DIAGNOSTICS" not in str(error.value)


@pytest.mark.parametrize("field", ["schema_version", "export", "step_mapping"])
def test_missing_envelope_fields_fail_explicitly(body, field):
    del body[field]
    with pytest.raises(ValidationError, match=field):
        ProcessProjection.from_json(json.dumps(body))


def test_unknown_envelope_fields_are_rejected(body):
    body["unexpected"] = "value"
    with pytest.raises(ValidationError, match="unexpected: Extra inputs are not permitted"):
        ProcessProjection.from_json(json.dumps(body))


def test_extensible_producer_data_and_omitted_defaults_preserve_exact_snapshot(body):
    body["export"]["future_annotation"] = {"nested": [None, True, 1, 1.0, "001"]}
    body["export"]["process"]["future_identity"] = {"id": "  001  "}
    if body["flo_version"] == "0.5.0":
        body["export"]["nodes"][0]["extensions"] = {"annotations": ["arbitrary", "producer"]}
    else:
        body["export"]["nodes"][0]["metadata"] = ["arbitrary", "producer", "annotation"]
    body["export"]["edges"][0]["future_flag"] = {"value": False}
    body["source"] = "  original namespace  "
    expected = json.dumps(body, allow_nan=False, sort_keys=True, separators=(",", ":"))
    captured = ProcessProjection.from_json(json.dumps(body))
    assert captured.to_json() == expected
    assert captured.to_dict() == body
    assert captured.digest == hashlib.sha256(expected.encode()).hexdigest()
    assert "rework" not in captured.to_dict()["export"]["edges"][0]
    assert "subprocess_parent" not in captured.to_dict()["export"]["nodes"][0]


def test_explicit_optional_nulls_and_false_flags_are_not_omitted(body):
    body["export"]["nodes"][0].update(branch=None, subprocess_parent=None)
    fields = {"route": None, "outcome": None, "rework": None, "handoff": None}
    if body["flo_version"] != "0.5.0":
        fields.update(edge_type=None, rework=False, handoff=False)
    body["export"]["edges"][0].update(fields)
    assert ProcessProjection.from_json(json.dumps(body)).to_dict() == body


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_values_in_unknown_annotations_remain_nonportable(body, value):
    body["export"]["unknown_annotation"] = {"value": value}
    with pytest.raises(ValidationError, match="finite JSON"):
        ProcessProjection.from_json(json.dumps(body))


@pytest.mark.parametrize("value", [None, [], "not an envelope"])
def test_nonobject_json_has_a_governed_root_error(value):
    with pytest.raises(ValidationError, match=r"\$: Input should be a valid dictionary"):
        ProcessProjection.from_json(json.dumps(value))


def test_blank_activity_keys_are_rejected_with_mapping_context(body):
    body["step_mapping"]["  "] = "start"
    with pytest.raises(ValidationError, match="step_mapping"):
        ProcessProjection.from_json(json.dumps(body))


def test_semantic_reference_errors_keep_precise_edge_locations(body):
    body["export"]["edges"][0]["target"] = "missing"
    with pytest.raises(ValidationError, match=r"export\.edges\.0\.target: FLO edge references"):
        ProcessProjection.from_json(json.dumps(body))
