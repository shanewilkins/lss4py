"""Offline acceptance of the pinned book model and explicit observation identities."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from lss4py import ValidationError
from lss4py.integration import ProcessProjection

ROOT = Path(__file__).parent / "fixtures/ecosystem/book-model"
OBSERVATIONS = Path(__file__).parent / "fixtures/reference/washnfold-friday91"
MANIFEST = json.loads((ROOT / "manifest.json").read_text())
MAPPING = json.loads((ROOT / "activity-mapping.json").read_text())
CLASSES = {
    "dropoff": "RNVA",
    "sort_tag": "RNVA",
    "wash": "VA",
    "dry": "VA",
    "fold_package": "VA",
    "fold_correction": "NVA",
    "stage": "RNVA",
    "notify": "VA",
}


def _projection(payload=None, mapping=None):
    """Exercise the bridge without importing FLO or parsing its source format."""
    return ProcessProjection.from_flo_export(
        json.loads((ROOT / "process-export.json").read_text()) if payload is None else payload,
        source=MANIFEST["observations"]["dataset_id"],
        model_revision=MANIFEST["source"]["revision"],
        step_mapping=MAPPING if mapping is None else mapping,
        flo_version=MANIFEST["producer"]["version"],
    )


@pytest.mark.parametrize("name", MANIFEST["artifacts_sha256"])
def test_model_artifact_bytes_match_pinned_snapshot(name):
    assert (
        hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == MANIFEST["artifacts_sha256"][name]
    )


@pytest.mark.parametrize("name", MANIFEST["observations"]["artifacts_sha256"])
def test_book_model_uses_the_existing_observation_revision(name):
    assert (
        hashlib.sha256((OBSERVATIONS / name).read_bytes()).hexdigest()
        == MANIFEST["observations"]["artifacts_sha256"][name]
    )


def test_every_observed_activity_maps_to_a_classified_model_task():
    with (OBSERVATIONS / "event_log.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    conventions = json.loads((OBSERVATIONS / "conventions.json").read_text())
    assert conventions["version"] == MANIFEST["observations"]["version"] == "1.0.0"
    assert len(rows) == MANIFEST["observations"]["rows"] == 330
    assert len({row["Order ID"] for row in rows}) == MANIFEST["observations"]["orders"] == 39
    assert {row["Activity Name"] for row in rows} == set(MAPPING)
    assert len(MAPPING) == MANIFEST["observations"]["activities"] == 8
    projection = _projection()
    steps = {step.id: step for step in projection.to_process_model().steps}
    assert set(MAPPING.values()) == set(CLASSES)
    for activity, target in MAPPING.items():
        assert projection.resolve_activity(activity) == target
        raw = steps[target].metadata["flo"]
        assert raw["kind"] == "task"
        assert raw["metadata"]["value_class"] == CLASSES[target]


def test_book_export_preserves_full_topology_and_source_metadata():
    projection = _projection()
    payload = projection.to_dict()["export"]
    model = projection.to_process_model()
    assert projection.digest == MANIFEST["bridge"]["projection_sha256"]
    assert len(model.steps) == MANIFEST["bridge"]["nodes"] == 14
    assert len(model.edges) == MANIFEST["bridge"]["edges"] == 14
    assert payload["process"]["id"] == "wash_n_fold"
    assert payload["process"]["version"] == 2
    assert {step.id: step.metadata["flo"] for step in model.steps} == {
        node["id"]: node for node in payload["nodes"]
    }
    assert [edge.metadata["flo"] for edge in model.edges] == payload["edges"]
    assert ProcessProjection(projection.to_json()).digest == projection.digest


def test_packaging_decision_and_correction_return_preserve_their_meaning():
    edges = {
        (edge.source_step_id, edge.target_step_id): edge
        for edge in _projection().to_process_model().edges
    }
    passed = edges["packaging_check", "notification_queue"]
    failed = edges["packaging_check", "correction_queue"]
    returned = edges["fold_correction", "notification_queue"]
    assert passed.condition == "pass" and passed.kind == "sequence"
    assert failed.condition == "fail" and failed.kind == "rework"
    assert returned.kind == "rework"
    assert {key for key, edge in edges.items() if edge.kind == "rework"} == {
        ("packaging_check", "correction_queue"),
        ("fold_correction", "notification_queue"),
    }


def test_modeled_measurements_keep_their_original_units_and_identities():
    steps = {step.id: step for step in _projection().to_process_model().steps}
    measures = [
        value
        for step in steps.values()
        for value in step.metadata["flo"].get("metadata", {}).values()
        if isinstance(value, dict) and "unit" in value
    ]
    assert {measure["unit"] for measure in measures} == {"min"}
    assert steps["wash_release_queue"].metadata["flo"]["metadata"]["wait_time"] == {
        "value": 501.7,
        "unit": "min",
        "measurement_id": "order_batch_release_wait",
    }
    assert steps["wash"].metadata["flo"]["name"] == "Wash loads"
    assert MAPPING["Wash"] == "wash"
    assert MAPPING["Fold and package"] == "fold_package"
    with pytest.raises(ValidationError, match="Unmapped"):
        _projection().resolve_activity("Wash loads")


def test_model_mapping_cannot_merge_distinct_observed_activities():
    mapping = {**MAPPING, "Dry": "wash"}
    with pytest.raises(ValidationError, match="many-to-one"):
        _projection(mapping=mapping)


@pytest.mark.parametrize(
    ("version", "digest"),
    [
        ("0.4.2", "d708b8ac6c05428c6832f8dbaaae7899a1a9e967e5e9a31448a8992cb1de91ee"),
        ("0.4.3", "05ecf7542271617df2529fbb683189dfb45a7361c721322177a1145bf6118b20"),
    ],
)
def test_saved_book_projection_preserves_its_producer_version_and_fingerprint(version, digest):
    body = _projection().to_dict()
    body["flo_version"] = version
    restored = ProcessProjection(json.dumps(body))
    assert restored.to_dict()["flo_version"] == version
    assert restored.digest == digest
    assert ProcessProjection(restored.to_json()).digest == digest


@pytest.mark.parametrize("version", [None, ["0.4.3"], "0.5.0"])
def test_unsupported_producer_profiles_raise_governed_errors(version):
    body = _projection().to_dict()
    body["flo_version"] = version
    with pytest.raises(ValidationError, match="Unsupported process schema or FLO version"):
        ProcessProjection(json.dumps(body))
