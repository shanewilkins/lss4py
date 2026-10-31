"""FLO 0.5 evidence preserves selectors, relations and legacy restoration."""

import json

import pytest

from lss4py import ValidationError
from lss4py.integration import ProcessProjection, derive_reconstruction_policy
from tests.test_book_model import MAPPING, ROOT, _projection
from tests.test_derived_policy import _conventions


def _payload():
    return _projection().to_dict()["export"]


def _task(payload):
    return next(n for n in payload["nodes"] if n["id"] == "wash")


@pytest.mark.parametrize("selection", ["omitted", None, "mean", "zero"])
def test_profiles_preserve_display_and_analysis_selections_without_fallback(selection):
    payload = _payload()
    profile = _task(payload)["cycle_time"]
    profile["results"]["zero"] = {"method": "median", "value": 0, "unit": "min"}
    profile["results"]["support"] = {
        "method": "lss4py.v1:interval-estimate",
        "value": [1, 2],
        "unit": "min",
        "parameters": {"cohort": ["a", None, True]},
    }
    if selection != "omitted":
        profile["analysis_input"] = selection
    projection = _projection(payload)
    assert projection.to_dict()["export"] == payload
    assert ProcessProjection.from_json(projection.to_json()).digest == projection.digest
    assert (
        derive_reconstruction_policy(
            projection, observed_activities=tuple(MAPPING), conventions=_conventions()
        ).policy
        == derive_reconstruction_policy(
            _projection(), observed_activities=tuple(MAPPING), conventions=_conventions()
        ).policy
    )


@pytest.mark.parametrize("relation", ["rework", "handoff"])
@pytest.mark.parametrize("value", [{}, {"extensions": {"reviewed": True}}, None])
def test_empty_structured_relations_retain_presence_and_evidence(relation, value):
    payload = _payload()
    edge = payload["edges"][0]
    edge[relation] = value
    model = _projection(payload).to_process_model()
    assert model.edges[0].metadata["flo"] == edge
    expected = "rework" if relation == "rework" and value is not None else "sequence"
    assert model.edges[0].kind == expected


def test_rework_zero_frequency_is_retained_with_its_population():
    payload = _payload()
    frequency = {
        "basis": "simulated",
        "numerator": 0,
        "denominator": 39,
        "observation_unit": "order",
        "evidence_ref": "sample:v1",
    }
    payload["edges"][0]["rework"] = {"frequency": frequency}
    edge = _projection(payload).to_process_model().edges[0]
    assert edge.kind == "rework"
    assert edge.metadata["flo"]["rework"]["frequency"] == frequency


@pytest.mark.parametrize("identifier", ["wash", "工序.洗 衣", "step.with.dots"])
def test_waiting_reference_retains_complete_identity_and_owned_profile(identifier):
    payload = _payload()
    work = _task(payload)
    work["id"] = identifier
    work["wait_time"] = work["cycle_time"]
    for edge in payload["edges"]:
        for field in ("source", "target"):
            if edge[field] == "wash":
                edge[field] = identifier
    queue = next(n for n in payload["nodes"] if n["id"] == "wash_release_queue")
    queue["wait_time"] = {"ref": f"{identifier}.wait_time"}
    projection = _projection(payload, mapping={**MAPPING, "Wash": identifier})
    assert projection.to_dict()["export"] == payload
    assert projection.resolve_activity("Wash") == identifier


@pytest.mark.parametrize(
    "reference",
    ["wash", "wash.cycle_time", "missing.wait_time", "notification_queue.wait_time", ".wait_time"],
)
def test_waiting_references_cannot_chain_or_target_missing_work_evidence(reference):
    payload = _payload()
    next(n for n in payload["nodes"] if n["kind"] == "queue")["wait_time"] = {"ref": reference}
    with pytest.raises(ValidationError, match=r"wait_time.ref"):
        _projection(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("primary", "missing"),
        ("analysis_input", "missing"),
        ("basis", "inferred"),
        ("observation_count", True),
        ("observation_count", 0),
        ("observation_unit", None),
    ],
)
def test_invalid_profile_context_and_selections_fail(field, value):
    payload = _payload()
    _task(payload)["cycle_time"][field] = value
    with pytest.raises(ValidationError, match="cycle_time"):
        _projection(payload)


@pytest.mark.parametrize(
    "value,unit",
    [
        (True, "min"),
        (-1, "min"),
        ("2", "min"),
        ([2], "min"),
        (1, "kg"),
        (1e308, "d"),
        (10**400, "min"),
    ],
)
def test_selected_durations_must_be_usable_even_when_display_only(value, unit):
    payload = _payload()
    _task(payload)["cycle_time"]["results"]["mean"].update(value=value, unit=unit)
    with pytest.raises(ValidationError, match="cycle_time"):
        _projection(payload)


@pytest.mark.parametrize(
    "method,parameters",
    [
        ("custom", None),
        ("percentile", None),
        ("percentile", {"percentile": True}),
        ("percentile", {"percentile": 101}),
    ],
)
def test_invalid_statistic_declarations_fail(method, parameters):
    payload = _payload()
    _task(payload)["cycle_time"]["results"]["mean"].update(method=method, parameters=parameters)
    with pytest.raises(ValidationError, match="cycle_time"):
        _projection(payload)


def test_supplied_process_lead_time_and_percentile_evidence_survive_without_modeling():
    payload = _payload()
    profile = _task(payload)["cycle_time"]
    profile["results"]["mean"].update(method="percentile", parameters={"percentile": 95})
    payload["process"]["lead_time"] = profile
    assert _projection(payload).to_dict()["export"] == payload


@pytest.mark.parametrize(
    "value", [(1, 2), {1: "one"}, {1, 2}, {"nested": float("nan")}, [float("inf")]]
)
def test_unselected_evidence_must_be_portable_finite_json(value):
    payload = _payload()
    _task(payload)["cycle_time"]["results"]["extra"] = {
        "method": "lss4py:custom",
        "value": value,
        "unit": "min",
    }
    with pytest.raises(ValidationError, match=r"JSON|finite"):
        _projection(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("rework", True),
        ("handoff", False),
        (
            "rework",
            {
                "frequency": {
                    "basis": "observed",
                    "numerator": 40,
                    "denominator": 39,
                    "observation_unit": "order",
                }
            },
        ),
        ("handoff", {"type": "imaginary"}),
        ("edge_type", "rework"),
    ],
)
def test_legacy_or_contradictory_relations_are_rejected(field, value):
    payload = _payload()
    payload["edges"][0][field] = value
    with pytest.raises(ValidationError, match=r"export.edges.0"):
        _projection(payload)


@pytest.mark.parametrize(
    "kind,field,value",
    [
        ("decision", "cycle_time", "profile"),
        ("decision", "wait_time", "profile"),
        ("task", "wait_time", {"ref": "wash.wait_time"}),
    ],
)
def test_measurements_and_references_require_applicable_nodes(kind, field, value):
    payload = _payload()
    node = next(n for n in payload["nodes"] if n["kind"] == kind)
    node[field] = _task(payload)["cycle_time"] if value == "profile" else value
    with pytest.raises(ValidationError, match="require"):
        _projection(payload)


@pytest.mark.parametrize("version", ["0.4.2", "0.4.3"])
def test_legacy_policy_derivation_preserves_classification_provenance(version):
    legacy = ROOT.parent / "legacy-0.4.3/book-model"
    manifest = json.loads((legacy / "manifest.json").read_text())
    projection = ProcessProjection.from_flo_export(
        json.loads((legacy / "process-export.json").read_text()),
        source=manifest["observations"]["dataset_id"],
        model_revision=manifest["source"]["revision"],
        step_mapping=MAPPING,
        flo_version=version,
    )
    derived = derive_reconstruction_policy(
        projection, observed_activities=tuple(MAPPING), conventions=_conventions()
    )
    assert derived.to_dict()["classifications"]["Wash"]["source_field"] == "metadata.value_class"
    assert derived.policy.value_add_activities == (
        "Dry",
        "Fold and package",
        "Send readiness notification",
        "Wash",
    )
