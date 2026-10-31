"""Reproduce the actual book model's pinned export using installed producer APIs."""

import hashlib
import json
import sys
from importlib import import_module, metadata
from pathlib import Path

import pytest

from lss4py.integration import ProcessProjection

ROOT = Path(__file__).parent / "fixtures/book-model"


def test_actual_book_model_exports_and_projects_with_the_released_producer():
    """Prove compatibility without a sibling checkout or a replacement FLO parser."""
    flo = import_module("flo")
    assert metadata.version("flo-lang") == "0.5.0"
    assert flo.__file__ is not None
    assert Path(flo.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    manifest = json.loads((ROOT / "manifest.json").read_text())
    raw = (ROOT / "washnfold.flo").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["artifacts_sha256"]["washnfold.flo"]
    validated = flo.validate(raw.decode())
    exported = flo.export(raw.decode())
    assert validated.ok, validated.diagnostics
    assert exported.ok, exported.diagnostics
    assert exported.value is not None
    assert validated.report.error_count == exported.report.error_count == 0
    assert (
        json.loads(json.dumps(exported.report.as_dict()["diagnostics"]))
        == manifest["producer"]["diagnostics"]
    )
    payload = json.loads(exported.value)
    assert payload == json.loads((ROOT / "process-export.json").read_text())
    mapping = json.loads((ROOT / "activity-mapping.json").read_text())
    projection = ProcessProjection.from_flo_export(
        payload,
        source=manifest["observations"]["dataset_id"],
        model_revision=manifest["source"]["revision"],
        step_mapping=mapping,
        flo_version=metadata.version("flo-lang"),
    )
    assert projection.digest == manifest["bridge"]["projection_sha256"]
    model = projection.to_process_model()
    assert len(model.steps) == 14 and len(model.edges) == 14
    assert [projection.resolve_activity(activity) for activity in mapping] == list(mapping.values())
    assert sum(edge.kind == "rework" for edge in model.edges) == 2


def test_current_producer_rejects_legacy_processing_time_on_a_decision():
    """Preserving an old export must not claim its source passes new validation."""
    flo = import_module("flo")
    source = (ROOT.parent / "legacy-0.4.2/baseline.flo").read_text()
    exported = flo.export(source)
    assert not exported.ok
    assert exported.report.error_count > 0


@pytest.mark.parametrize("selection", ["omitted", None, "zero"])
def test_real_producer_preserves_selectors_unicode_references_and_empty_relations(selection):
    """Cross the installed producer/consumer boundary with 0.5-only evidence."""
    flo = import_module("flo")
    profile = {
        "basis": "observed",
        "results": {
            "mean": {"method": "mean", "value": 2, "unit": "min"},
            "zero": {"method": "median", "value": 0, "unit": "min"},
        },
        "primary": "mean",
        "observation_count": 3,
        "observation_unit": "order",
        "evidence_ref": "test:three-orders",
    }
    if selection != "omitted":
        profile["analysis_input"] = selection
    identifier = "工序.洗 衣"
    source = json.dumps(
        {
            "spec_version": "0.1",
            "process": {"id": "selectors", "name": "Selector evidence"},
            "steps": [
                {"id": "start", "kind": "start"},
                {"id": "queue", "kind": "queue", "wait_time": {"ref": f"{identifier}.wait_time"}},
                {
                    "id": identifier,
                    "kind": "task",
                    "value_class": "VA",
                    "cycle_time": profile,
                    "wait_time": profile,
                },
                {"id": "end", "kind": "end"},
            ],
            "transitions": [
                {"source": "start", "target": "queue", "handoff": {}},
                {"source": "queue", "target": identifier},
                {"source": identifier, "target": "end", "rework": {}},
            ],
        }
    )
    exported = flo.export(source)
    assert exported.ok, exported.diagnostics
    assert exported.value is not None
    payload = json.loads(exported.value)
    projection = ProcessProjection.from_flo_export(
        payload, source="three-orders", model_revision="v1", step_mapping={"Wash": identifier}
    )
    assert projection.to_dict()["export"] == payload
    node = next(n for n in payload["nodes"] if n["id"] == identifier)
    assert node["cycle_time"] == profile
    model = projection.to_process_model()
    assert model.edges[-1].kind == "rework"
    assert model.edges[0].metadata["flo"]["handoff"] == {}
