"""Model-derived classifications preserve measured arithmetic and attribution."""

import json
from dataclasses import asdict, replace

import polars as pl
import pytest

from lss4py import (
    NumericLogContract,
    OrderReconstructionResult,
    ValidationError,
    load_numeric_event_log,
    reconstruct_orders,
)
from lss4py.integration import ReconstructionConventions, derive_reconstruction_policy
from tests.test_book_model import MAPPING, _projection
from tests.test_reconstruction import EXAMPLE, FIXTURE


@pytest.fixture
def log():
    profile = json.loads((EXAMPLE.HERE / "simulation_sources.json").read_text())["profiles"][0]
    return load_numeric_event_log(
        FIXTURE / "event_log.csv", contract=NumericLogContract.from_dict(profile["contract"])
    )


def _conventions():
    values = asdict(EXAMPLE.POLICY)
    del values["value_add_activities"]
    del values["required_non_value_add_activities"]
    return ReconstructionConventions(**values)


def _derive(payload=None, conventions=None, activities=tuple(MAPPING)):
    return derive_reconstruction_policy(
        _projection(payload),
        observed_activities=activities,
        conventions=_conventions() if conventions is None else conventions,
    )


def _payload():
    return _projection().to_dict()["export"]


def _node(payload, step="notify"):
    return next(n for n in payload["nodes"] if n["id"] == step)


def test_derived_policy_matches_all_independent_order_expectations(log):
    derived = _derive()
    actual = reconstruct_orders(log, policy=derived.policy)
    reference = reconstruct_orders(log, policy=EXAMPLE.POLICY)
    for table in ("orders", "activities", "source_records", "activity_records"):
        assert actual.to_polars(table).equals(reference.to_polars(table))
    orders = actual.to_polars()
    assert orders.height == 39
    assert orders["value_add"].sum() == pytest.approx(3535.3)
    assert orders["lead_time"].sum() == pytest.approx(25840.5)
    assert actual.metadata["correction_occurrences"] == 5
    assert orders.filter(pl.col("Order ID") == "WNF-003")["value_add"][0] == pytest.approx(82.7)
    actual.metadata["policy_derivation"] = derived.to_dict()
    restored = OrderReconstructionResult.from_dict(json.loads(actual.to_json()))
    assert restored.metadata["policy_derivation"] == derived.to_dict()


def test_classification_change_changes_measured_va_and_pce(log):
    payload = _payload()
    _node(payload)["value_class"] = "RNVA"
    before = reconstruct_orders(log, policy=_derive().policy)
    after = reconstruct_orders(log, policy=_derive(payload).policy)
    notification = (
        before.to_polars("activities")
        .filter(pl.col("activity") == "Send readiness notification")["value_add"]
        .sum()
    )
    assert notification > 0
    assert after.to_polars()["value_add"].sum() == pytest.approx(3535.3 - notification)
    assert after.to_polars()["lead_time"].equals(before.to_polars()["lead_time"])
    assert 100 * after.to_polars()["value_add"].sum() / 25840.5 < 100 * 3535.3 / 25840.5
    assert (
        _derive(payload).to_dict()["projection_sha256"] != _derive().to_dict()["projection_sha256"]
    )


def test_names_and_modeled_durations_do_not_change_policy_or_measurements(log):
    payload = _payload()
    for node in payload["nodes"]:
        node["name"] = "An unrelated display label"
        if node["kind"] == "task":
            node["cycle_time"] = {
                "basis": "target",
                "results": {"mean": {"method": "mean", "value": 999999, "unit": "hr"}},
                "primary": "mean",
            }
    assert _derive(payload).policy == _derive().policy
    assert (
        reconstruct_orders(log, policy=_derive(payload).policy)
        .to_polars()
        .equals(reconstruct_orders(log, policy=_derive().policy).to_polars())
    )


def test_evidence_is_detached_and_identifies_model_and_analyst_sources():
    derived = _derive()
    evidence = derived.to_dict()
    assert json.loads(derived.to_json()) == evidence
    assert evidence["projection_sha256"] == _projection().digest
    assert evidence["classifications"]["Wash"] == {
        "step_id": "wash",
        "value_class": "VA",
        "source_field": "value_class",
    }
    assert "value_add_activities" not in evidence["analyst_conventions"]
    evidence["classifications"].clear()
    assert len(derived.to_dict()["classifications"]) == 8


@pytest.mark.parametrize("value", [None, "", "va", "unknown", "UNKNOWN", 1, True, [], {}])
def test_missing_or_invalid_classes_fail_with_identity(value):
    payload = _payload()
    _node(payload)["value_class"] = value
    with pytest.raises(ValidationError, match="value_class"):
        _derive(payload)


@pytest.mark.parametrize("metadata", [None, [], "VA", {}])
def test_missing_or_invalid_metadata_fails(metadata):
    payload = _payload()
    _node(payload)["metadata"] = metadata
    with pytest.raises(ValidationError, match=r"retired FLO 0\.5 fields"):
        _derive(payload)


def test_absent_metadata_and_class_fail():
    payload = _payload()
    del _node(payload)["value_class"]
    with pytest.raises(ValidationError, match=r"Send readiness notification.*notify.*value_class"):
        _derive(payload)


def test_routing_nodes_cannot_be_measured_tasks():
    payload = _payload()
    node = _node(payload)
    node.clear()
    node.update(id="notify", kind="queue")
    with pytest.raises(ValidationError, match="must map to task"):
        _derive(payload)


@pytest.mark.parametrize("value", ["VA", "RNVA"])
def test_correction_class_conflicts_are_rejected(value):
    payload = _payload()
    _node(payload, "fold_correction")["value_class"] = value
    with pytest.raises(ValidationError, match="Correction activity"):
        _derive(payload)


@pytest.mark.parametrize("field", ["arrival_activity", "readiness_activity", "correction_activity"])
def test_unmapped_analyst_declarations_fail(field):
    with pytest.raises(ValidationError, match="Unmapped analyst activities"):
        _derive(conventions=replace(_conventions(), **{field: "Missing"}))


@pytest.mark.parametrize("activities", [(), "Wash", [None], [" "], ["Wash", "Wash"], ["Missing"]])
def test_invalid_or_unmapped_observation_vocabulary_fails(activities):
    with pytest.raises(ValidationError, match=r"observed_activities|Unmapped observed"):
        _derive(activities=activities)


def test_invalid_contract_objects_raise_public_errors():
    with pytest.raises(ValidationError, match="ProcessProjection and ReconstructionConventions"):
        derive_reconstruction_policy(None, observed_activities=tuple(MAPPING), conventions={})  # ty: ignore[invalid-argument-type]


def test_conventions_freeze_lists_and_validate_existing_domain_rules():
    rules = replace(_conventions(), parallel_activities=["Wash", "Dry"])
    assert rules.parallel_activities == ("Wash", "Dry")
    with pytest.raises(ValidationError, match="must differ"):
        replace(rules, rework_value="N")
