"""Reproduce the actual book model's pinned export using installed producer APIs."""

import hashlib
import json
import sys
from importlib import import_module, metadata
from pathlib import Path

from lss4py.integration import ProcessProjection

ROOT = Path(__file__).parent / "fixtures/book-model"


def test_actual_book_model_exports_and_projects_with_the_released_producer():
    """Prove compatibility without a sibling checkout or a replacement FLO parser."""
    flo = import_module("flo")
    assert metadata.version("flo-lang") == "0.4.3"
    assert Path(flo.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    manifest = json.loads((ROOT / "manifest.json").read_text())
    raw = (ROOT / "washnfold.flo").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["artifacts_sha256"]["washnfold.flo"]
    validated = flo.validate(raw.decode())
    exported = flo.export(raw.decode())
    assert validated.ok, validated.diagnostics
    assert exported.ok, exported.diagnostics
    assert exported.value is not None
    assert not validated.diagnostics and not exported.diagnostics
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
    assert "E1508" in {diagnostic.code for diagnostic in exported.diagnostics}
