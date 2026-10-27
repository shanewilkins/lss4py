"""Portable projection validation is available in an ordinary wheel installation."""

import json
from importlib import metadata
from pathlib import Path

import pytest

from lss4py import ValidationError
from lss4py.integration import ProcessProjection

ROOT = Path(__file__).parent / "ecosystem/fixtures/book-model"


def test_base_install_declares_validation_dependency_and_restores_pinned_projection():
    """Use the bridge without requiring FLO's optional dependency tree."""
    requirements = metadata.requires("lss4py") or []
    assert any(
        requirement.startswith("pydantic") and ";" not in requirement
        for requirement in requirements
    )
    manifest = json.loads((ROOT / "manifest.json").read_text())
    projection = ProcessProjection.from_flo_export(
        json.loads((ROOT / "process-export.json").read_text()),
        source=manifest["observations"]["dataset_id"],
        model_revision=manifest["source"]["revision"],
        step_mapping=json.loads((ROOT / "activity-mapping.json").read_text()),
        flo_version=manifest["producer"]["version"],
    )
    assert projection.digest == manifest["bridge"]["projection_sha256"]


def test_installed_schema_rejects_boolean_coercion_with_a_public_field_error():
    """A portable JSON mutation cannot become a truthy rework declaration."""
    manifest = json.loads((ROOT / "manifest.json").read_text())
    export = json.loads((ROOT / "process-export.json").read_text())
    export["edges"][0]["rework"] = "true"
    with pytest.raises(ValidationError, match=r"export\.edges\.0\.rework"):
        ProcessProjection.from_flo_export(
            export,
            source="washnfold-friday91",
            model_revision=manifest["source"]["revision"],
            step_mapping=json.loads((ROOT / "activity-mapping.json").read_text()),
        )
