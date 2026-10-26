"""Customer CSV-to-JSON studies using only the installed public package."""

import json
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

import lss4py
from lss4py import (
    AdapterError,
    EventLogBindingsIR,
    LeadTimeBindingIR,
    MetricBindingsIR,
    ProcessEdgeIR,
    ProcessModelIR,
    ProcessStepIR,
    Specification,
    StageBindingsIR,
    ValidationError,
    booked_to_completed_yield,
    capability_indices,
    created_to_booked_yield,
    describe,
    lead_time,
    load_event_log,
    process_cycle_efficiency,
    rolled_yield,
    takt_time,
    wait_time,
)


def event_model():
    """Declare the observed parallel reviews and explicit review rework."""
    return ProcessModelIR(
        name="Client intake",
        steps=[
            ProcessStepIR(id=name, name=name) for name in ("intake", "review", "approval", "close")
        ],
        edges=[
            ProcessEdgeIR(source_step_id="intake", target_step_id="review", kind="parallel_split"),
            ProcessEdgeIR(
                source_step_id="intake", target_step_id="approval", kind="parallel_split"
            ),
            ProcessEdgeIR(source_step_id="review", target_step_id="close", kind="parallel_join"),
            ProcessEdgeIR(source_step_id="approval", target_step_id="close", kind="parallel_join"),
            ProcessEdgeIR(source_step_id="review", target_step_id="review", kind="rework"),
        ],
        bindings=MetricBindingsIR(
            event_log=EventLogBindingsIR(
                case_id_column="case_id",
                step_id_column="step_id",
                started_at_column="started_at",
                completed_at_column="completed_at",
            )
        ),
    )


def load_events(path):
    """Map a source system's column names to the canonical event-log contract."""
    return load_event_log(
        path,
        case_id_column="case",
        step_id_column="activity",
        started_at_column="start",
        completed_at_column="end",
    )


def assert_provenance(payload, method, backend):
    """Require usable audit metadata to survive disk export."""
    provenance = payload["provenance"]
    assert provenance["method"] == method
    assert provenance["backend"] == backend
    assert provenance["method_version"]
    assert provenance["package_version"] == lss4py.__version__
    assert provenance["created_at"]
    assert payload["interpretation_context"]


def test_intake_baseline(fixtures, read_csv, backend, expected, export_json):
    """Combine timestamps, measured work and funnel outcomes into an exported baseline."""
    frame = read_csv(fixtures / "intake.csv")
    model = ProcessModelIR(
        name="Client intake",
        bindings=MetricBindingsIR(
            lead_time=LeadTimeBindingIR(start_column="created_at", end_column="closed_at"),
            stages=StageBindingsIR(created="created", booked="booked", completed="completed"),
        ),
    )
    lead = lead_time(frame, process_model=model, unit="hours")
    # Analyst preparation is explicit: all durations use hours and rows retain source order.
    prepared = (
        frame.with_columns(pl.Series("lead_hours", lead.values))
        if backend == "polars"
        else (frame.assign(lead_hours=lead.values))
    )
    results = {
        "lead": lead,
        "wait": wait_time(
            prepared, lead_time_column="lead_hours", cycle_time_column="active_hours"
        ),
        "pce": process_cycle_efficiency(
            prepared,
            lead_time_column="lead_hours",
            value_add_time_column="value_add_hours",
        ),
        "created_booked": created_to_booked_yield(frame, process_model=model),
        "booked_completed": booked_to_completed_yield(frame, process_model=model),
        "rolled": rolled_yield(frame, process_model=model),
        "summary": describe(prepared, column="lead_hours", unit="hours"),
    }
    exported = export_json("intake-baseline", results)
    baseline = expected["intake"]
    for key in ("lead", "wait", "pce"):
        assert exported[key]["values"] == pytest.approx(baseline[key])
        assert exported[key]["keys"] is None
    for key in ("created_booked", "booked_completed", "rolled"):
        assert exported[key]["value"] == pytest.approx(baseline[key])
        assert exported[key]["unit"] == "percentage"
    assert exported["created_booked"]["numerator"] == 3
    assert exported["created_booked"]["denominator"] == 4
    assert exported["booked_completed"]["numerator"] == 2
    assert exported["booked_completed"]["denominator"] == 3
    for field in ("mean", "median", "std"):
        assert exported["summary"][field] == pytest.approx(baseline[f"lead_{field}"])
    assert exported["lead"]["unit"] == exported["wait"]["unit"] == "hours"
    assert exported["pce"]["unit"] == "percentage"
    assert exported["summary"]["count"] == 4
    assert takt_time(available_time=8, customer_demand=4) == baseline["takt"]
    for key, method in (
        ("lead", "lead_time"),
        ("wait", "wait_time"),
        ("pce", "process_cycle_efficiency"),
        ("created_booked", "created_to_booked_yield"),
        ("booked_completed", "booked_to_completed_yield"),
        ("rolled", "rolled_yield"),
        ("summary", "describe"),
    ):
        assert_provenance(exported[key], method, backend)


def test_event_log_study(fixtures, expected, export_json):
    """Ingest unordered cases, parallel work and rework without double-counting elapsed time."""
    events = load_events(fixtures / "events.csv")
    lead = lead_time(events, process_model=event_model(), unit="hours")
    minutes = lead_time(events, process_model=event_model(), unit="minutes")
    summary = describe(pl.DataFrame({"hours": lead.values}), column="hours", unit="hours")
    exported = export_json("event-study", {"lead": lead, "minutes": minutes, "summary": summary})
    assert events.to_polars()["case_id"].to_list()[:2] == ["002", "001"]
    assert events.to_polars()["owner"].to_list()[0] == "Lin"
    for key, unit in (("lead", "hours"), ("minutes", "minutes")):
        assert exported[key]["keys"] == expected["events"]["keys"]
        assert exported[key]["values"] == expected["events"][unit]
        assert exported[key]["unit"] == unit
        assert_provenance(exported[key], "lead_time", "polars")
        assert exported[key]["provenance"]["parameters"]["data_shape"] == "interval_event_log"
    assert exported["summary"]["mean"] == expected["events"]["mean"]


def test_capability_study(fixtures, read_csv, backend, expected, export_json):
    """Restore a CTQ, account for blanks, and export estimates, intervals and diagnostics."""
    frame = read_csv(fixtures / "measurements.csv")
    spec = Specification.from_json((fixtures / "specification.json").read_text())
    assert Specification.from_json(spec.to_json()) == spec
    result = capability_indices(
        frame,
        column="diameter",
        specification=spec,
        missing="omit",
        ci=True,
        sigma_shift=1.5,
    )
    summary = describe(frame, column="diameter", unit="mm")
    groups = describe(frame, column="diameter", group_by="machine", unit="mm")
    exported = export_json(
        "diameter-study",
        {
            "capability": result,
            "summary": summary,
            "machine_b": groups[0],
            "machine_a": groups[1],
        },
    )
    capability = exported["capability"]
    for field, value in expected["capability"].items():
        assert capability[field] == pytest.approx(value, rel=1e-12, abs=1e-12)
    assert capability["unit"] == "mm"
    assert capability["variation_estimator"] == "overall_sample_std"
    assert capability["confidence_interval"] == capability["cpk_confidence_interval"]
    assert_provenance(capability, "capability_indices", backend)
    provenance = capability["provenance"]
    assert provenance["parameters"]["specification"] == json.loads(spec.to_json())
    assert provenance["cohort_definition"] == "September inspection sample"
    assert {warning["code"] for warning in provenance["warnings"]} == {
        "MISSING_OMITTED",
        "SMALL_SAMPLE",
        "SIGMA_SHIFT_ASSUMED",
    }
    assert "NORMAL_STABLE_INDEPENDENT" in {note["code"] for note in provenance["assumptions"]}
    assert exported["summary"]["count"] == 5
    assert exported["summary"]["missing"] == 1
    for key, machine, count, missing in (("machine_b", "B", 3, 0), ("machine_a", "A", 2, 1)):
        assert exported[key]["group_keys"] == {"machine": machine}
        assert exported[key]["count"] == count
        assert exported[key]["missing"] == missing
        assert exported[key]["mean"] == 10


def test_installed_cli(tmp_path):
    """Invoke the wheel's console script from outside the repository."""
    executable = Path(sys.executable).with_name(
        "lss4py.exe" if sys.platform == "win32" else "lss4py"
    )
    completed = subprocess.run(
        [str(executable), "doctor"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "scaffold is ready" in completed.stdout


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (
            "case,activity,start\n001,intake,2026-09-01T08:00:00\n",
            "missing required source columns",
        ),
        ("case,activity,start,end\n001,intake,not-a-time,2026-09-01T09:00:00\n", "normalize"),
        (
            "case,activity,start,end\n001,intake,2026-09-01T10:00:00,2026-09-01T09:00:00\n",
            "negative durations",
        ),
        (
            "case,activity,start,end\n,intake,2026-09-01T08:00:00,2026-09-01T09:00:00\n",
            "null values",
        ),
    ],
    ids=["missing-column", "bad-timestamp", "negative-duration", "missing-case"],
)
def test_invalid_event_source(tmp_path, contents, message):
    """Require useful ingestion errors for corrupt files in the installed package."""
    source = tmp_path / "invalid.csv"
    source.write_text(contents)
    with pytest.raises(AdapterError, match=message):
        load_events(source)


def test_missing_event_file(tmp_path):
    """Reject unavailable source files through the public adapter error contract."""
    with pytest.raises(AdapterError, match="does not exist"):
        load_events(tmp_path / "missing.csv")


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("unknown-step", "missing from process model"),
        ("undeclared-rework", "rework"),
        ("undeclared-parallel", "parallel edges"),
    ],
)
def test_invalid_event_topology(fixtures, tmp_path, failure, message):
    """Check topology validation after a real CSV has been ingested."""
    source = fixtures / "events.csv"
    model = event_model()
    if failure == "unknown-step":
        modified = tmp_path / "unknown.csv"
        modified.write_text(source.read_text().replace("approval", "unknown"))
        source = modified
    elif failure == "undeclared-rework":
        model.edges = [edge for edge in model.edges if edge.kind != "rework"]
    else:
        model.edges = [edge for edge in model.edges if edge.kind == "rework"]
    with pytest.raises(ValidationError, match=message):
        lead_time(load_events(source), process_model=model)


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("negative-lead", "negative"),
        ("too-much-work", "Wait time cannot be negative"),
        ("invalid-funnel", "cannot exceed"),
    ],
)
def test_invalid_intake_study(fixtures, tmp_path, read_csv, failure, message):
    """Reject impossible customer observations on both CSV-reading backends."""
    contents = (fixtures / "intake.csv").read_text()
    if failure == "negative-lead":
        contents = contents.replace("2026-09-01T18:00:00", "2026-09-01T07:00:00")
    elif failure == "too-much-work":
        contents = contents.replace(",4,3,1,1,1", ",11,3,1,1,1")
    else:
        contents = contents.replace(",1,0,0", ",1,0,1")
    source = tmp_path / "invalid-intake.csv"
    source.write_text(contents)
    frame = read_csv(source)
    if failure == "invalid-funnel":
        with pytest.raises(ValidationError, match=message):
            rolled_yield(
                frame,
                created_column="created",
                booked_column="booked",
                completed_column="completed",
            )
    elif failure == "negative-lead":
        with pytest.raises(ValidationError, match=message):
            lead = lead_time(frame, start_column="created_at", end_column="closed_at")
    else:
        lead = lead_time(frame, start_column="created_at", end_column="closed_at")
        prepared = pl.DataFrame({"lead": lead.values, "active": frame["active_hours"]})
        with pytest.raises(ValidationError, match=message):
            wait_time(prepared, lead_time_column="lead", cycle_time_column="active")


def test_strict_measurement_policy(fixtures, read_csv):
    """A blank CSV measurement must not silently disappear under the strict policy."""
    frame = read_csv(fixtures / "measurements.csv")
    spec = Specification.from_json((fixtures / "specification.json").read_text())
    with pytest.raises(ValidationError, match="missing measurements"):
        capability_indices(frame, column="diameter", specification=spec, missing="raise")
