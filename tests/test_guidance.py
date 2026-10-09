"""Catalog completeness, candidate selection, and non-execution contracts."""

import inspect
import json
from dataclasses import FrozenInstanceError, replace

import pytest

import lss4py
from lss4py import AnalysisSuitability, ValidationError, get_analysis, get_candidates
from lss4py.guidance import register_analysis

METHODS = {
    "describe",
    "lead_time",
    "wait_time",
    "process_cycle_efficiency",
    "takt_time",
    "created_to_booked_yield",
    "booked_to_completed_yield",
    "rolled_yield",
}


def test_catalog_covers_supported_calculations():
    entries = get_candidates()
    assert {entry.name for entry in entries} == METHODS
    assert [entry.name for entry in entries] == sorted(METHODS)
    for entry in entries:
        assert callable(getattr(lss4py, entry.name))
        assert entry.belt_level in {"white", "yellow"}
        assert set(entry.alternatives) <= METHODS
        assert all(entry.required_fields)
        assert entry.assumptions and entry.prerequisites and entry.limits
        assert json.loads(json.dumps(entry.to_dict()))["name"] == entry.name


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("elapsed_time", ("lead_time",)),
        ("waiting_time", ("wait_time",)),
        ("value_add_share", ("process_cycle_efficiency",)),
        ("demand_pace", ("takt_time",)),
        ("summarize_measurements", ("describe",)),
        ("stage_conversion", ("booked_to_completed_yield", "created_to_booked_yield")),
        ("overall_conversion", ("rolled_yield",)),
        ("unknown", ()),
    ],
)
def test_declared_questions(question, expected):
    assert tuple(entry.name for entry in get_candidates(question)) == expected


def test_filters_match_supported_input_and_design_without_inspecting_data():
    assert get_candidates("elapsed_time", data_type="interval_event_log") == (
        get_analysis("lead_time"),
    )
    assert get_candidates("elapsed_time", data_type="numeric") == ()
    assert get_candidates(design_type="planning") == (get_analysis("takt_time"),)
    assert get_candidates(design_type="randomized_trial") == ()
    assert get_candidates(data_type="unsupported") == ()
    assert get_candidates("waiting_time", data_type="interval_event_log") == ()


def test_catalog_records_alternative_input_paths_and_current_limits():
    lead = get_analysis("lead_time")
    assert len(lead.required_fields) == 2
    assert "process_model" in lead.required_fields[1]
    wait = get_analysis("wait_time")
    assert wait.required_fields == (("lead_time_column", "cycle_time_column"),)
    assert any("unavailable" in limit for limit in wait.limits)
    assert get_analysis("describe").belt_level == "white"


def test_guidance_cannot_execute_an_analysis(monkeypatch):
    def fail(*_args, **_kwargs):
        pytest.fail("Guidance executed an analytical method")

    for name in METHODS:
        monkeypatch.setattr(lss4py, name, fail)
    assert len(get_candidates()) == 8
    assert get_analysis("describe").name == "describe"
    assert "data" not in inspect.signature(get_candidates).parameters


def test_registration_preserves_callable_and_prevents_ambiguous_names(monkeypatch):
    import lss4py.guidance as guidance

    monkeypatch.setattr(guidance, "_registry", {})
    entry = replace(get_candidates_entry(), name="example")
    calls = []

    def example():
        calls.append(True)
        return 42

    assert register_analysis(entry)(example) is example
    assert not calls
    assert get_candidates() == (entry,)
    assert not calls
    assert example() == 42
    with pytest.raises(ValidationError, match="already registered"):
        register_analysis(entry)(example)
    with pytest.raises(ValidationError, match="match"):
        register_analysis(replace(entry, name="other"))(example)


def get_candidates_entry():
    return AnalysisSuitability(
        name="example",
        family="descriptive",
        question_tags=("example",),
        belt_level="white",
        required_fields=(("column",),),
        data_types=("numeric",),
        design_types=("observational",),
        prerequisites=("Numeric values.",),
        assumptions=("Declared cohort.",),
        alternatives=("describe",),
        limits=("Summary only.",),
    )


def test_metadata_is_immutable_and_exports_are_independent():
    entry = get_analysis("describe")
    labels = ["example"]
    copied = replace(entry, question_tags=labels, required_fields=[["column"]])
    labels.append("changed")
    assert copied.question_tags == ("example",)
    assert copied.required_fields == (("column",),)
    with pytest.raises(FrozenInstanceError):
        copied.name = "changed"  # ty: ignore[invalid-assignment]
    payload = copied.to_dict()
    payload["name"] = "changed"
    assert copied.name == "describe"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", " "),
        ("family", None),
        ("belt_level", ""),
        ("question_tags", "string"),
        ("data_types", ()),
        ("design_types", ("observational", "observational")),
        ("assumptions", ("",)),
        ("required_fields", ()),
        ("required_fields", "column"),
        ("required_fields", (("column", "column"),)),
    ],
)
def test_invalid_metadata(field, value):
    with pytest.raises(ValidationError):
        replace(get_analysis("describe"), **{field: value})


@pytest.mark.parametrize("filters", [{"question": ""}, {"data_type": " "}, {"design_type": 1}])
def test_invalid_filters(filters):
    with pytest.raises(ValidationError):
        get_candidates(**filters)


def test_unknown_analysis_is_explicit():
    with pytest.raises(ValidationError, match="Unknown analysis"):
        get_analysis("unavailable")
