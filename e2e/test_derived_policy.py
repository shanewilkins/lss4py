"""Derive portable policy using an ordinary installed wheel without FLO imports."""

import json
from pathlib import Path

from lss4py.integration import (
    ProcessProjection,
    ReconstructionConventions,
    derive_reconstruction_policy,
)

ROOT = Path(__file__).parent / "ecosystem/fixtures/book-model"


def test_installed_model_derived_policy_retains_attribution():
    """Use producer JSON and model-owned classes in the base installation."""
    manifest = json.loads((ROOT / "manifest.json").read_text())
    mapping = json.loads((ROOT / "activity-mapping.json").read_text())
    projection = ProcessProjection.from_flo_export(
        json.loads((ROOT / "process-export.json").read_text()),
        source=manifest["observations"]["dataset_id"],
        model_revision=manifest["source"]["revision"],
        step_mapping=mapping,
    )
    conventions = ReconstructionConventions(
        arrival_activity="Drop-off and ticket",
        readiness_activity="Send readiness notification",
        required_activities=tuple(a for a in mapping if a != "Fold correction"),
        parallel_activities=("Wash", "Dry"),
        rework_column="Rework Y/N",
        rework_value="Y",
        non_rework_value="N",
        correction_activity="Fold correction",
        cohort="All 39 orders in washnfold-friday91 v1.0.0",
        value_add_convention="Right-first-time processing; failed attempts are NVA.",
        parallel_load_count_column="Compatible Loads",
    )
    derived = derive_reconstruction_policy(
        projection, observed_activities=tuple(mapping), conventions=conventions
    )
    assert set(derived.policy.value_add_activities) == {
        "Wash",
        "Dry",
        "Fold and package",
        "Send readiness notification",
    }
    assert json.loads(derived.to_json())["projection_sha256"] == projection.digest
    assert derived.to_dict()["classifications"]["Fold correction"]["value_class"] == "NVA"
