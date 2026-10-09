"""CTQ specification validation, immutability, and serialization contracts."""

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast

import polars as pl
import pytest

from lss4py import AnalysisWindow, Specification, ValidationError, describe


def test_minimal_and_targetless_specifications():
    """Allow framing a CTQ before targets or acceptance limits are available."""
    spec = Specification(name="Lead time", unit="hours", direction="lower")
    assert spec.lsl is spec.usl is spec.target is None
    assert spec.group_by == () and spec.schema_version == "1.0"
    assert Specification.from_json(spec.to_json()) == spec


@pytest.mark.parametrize("limits", [{"usl": 8}, {"lsl": 0}, {"lsl": 0, "usl": 8}])
def test_one_and_two_sided_specifications(limits):
    """One- and two-sided specifications need not declare a nominal target."""
    spec = Specification(name="Duration", unit="hours", direction="lower", **limits)
    assert spec.target is None
    assert Specification.from_dict(spec.to_dict()) == spec


def test_full_roundtrip():
    """Retain every analytical contract field through strict JSON and dict round trips."""
    window = AnalysisWindow(
        start=datetime(2026, 1, 1, tzinfo=UTC), end=datetime(2026, 2, 1, tzinfo=UTC)
    )
    spec = Specification(
        name="Fill volume",
        unit="mL",
        direction="target",
        target=500,
        lsl=495,
        usl=505,
        defect_definition="A fill outside the inclusive volume limits.",
        opportunity_definition="One inspected bottle fill.",
        opportunities_per_unit=1,
        group_by=("line", "shift"),
        cohort="Released production batches",
        time_window=window,
        decision_context="Decide whether filling performance meets customer needs.",
    )
    assert spec.target == 500.0 and isinstance(spec.target, float)
    payload = spec.to_dict()
    assert payload["time_window"]["start"] == "2026-01-01T00:00:00+00:00"
    assert payload["group_by"] == ["line", "shift"]
    assert Specification.from_dict(payload) == spec
    assert Specification.from_json(spec.to_json()) == spec
    assert json.loads(spec.to_json()) == payload


def test_target_at_specification_boundary():
    """Specification limits are inclusive and do not imply a centered target."""
    spec = Specification(
        name="Score", unit="points", direction="higher", target=100, lsl=0, usl=100
    )
    assert spec.target == spec.usl


@pytest.mark.parametrize(
    "options",
    [
        {"name": ""},
        {"name": "   "},
        {"unit": None},
        {"unit": 3},
        {"unit": ""},
        {"direction": "sideways"},
        {"direction": "target"},
        {"lsl": 5, "usl": 5},
        {"lsl": 6, "usl": 5},
        {"target": 1, "lsl": 2},
        {"target": 3, "usl": 2},
        {"target": True},
        {"target": "1"},
        {"lsl": float("inf")},
        {"usl": float("-inf")},
        {"target": float("nan")},
        {"target": 10**400},
        {"defect_definition": ""},
        {"opportunity_definition": " "},
        {"cohort": 2},
        {"decision_context": False},
        {"group_by": "line"},
        {"group_by": ["line", "line"]},
        {"group_by": [""]},
        {"group_by": [None]},
        {"group_by": {"line"}},
        {"time_window": {}},
        {"schema_version": "2.0"},
    ],
)
def test_invalid_declarations(options):
    """Reject ambiguous labels, contradictory bounds, and untyped context."""
    parameters: dict[str, Any] = {
        "name": "Duration",
        "unit": "hours",
        "direction": "lower",
        **options,
    }
    with pytest.raises(ValidationError):
        Specification(**parameters)


@pytest.mark.parametrize("count", [0, -1, True, 1.5, "2"])
def test_invalid_opportunity_counts(count):
    """A fixed per-unit opportunity count must be a positive integer."""
    with pytest.raises(ValidationError, match="positive integer"):
        Specification(
            name="Errors",
            unit="count",
            direction="lower",
            opportunities_per_unit=count,
            opportunity_definition="Inspected fields",
        )


def test_count_requires_definition():
    """Do not record a denominator without saying what an opportunity represents."""
    with pytest.raises(ValidationError, match="requires an opportunity_definition"):
        Specification(name="Errors", unit="count", direction="lower", opportunities_per_unit=3)
    spec = Specification(
        name="Errors",
        unit="count",
        direction="lower",
        opportunity_definition="Each inspected field",
    )
    assert spec.opportunities_per_unit is None  # Variable denominators remain possible.


def test_immutable_and_detached_serialization():
    """Mutating caller lists or exported payloads cannot invalidate a specification."""
    payload = {"name": "Duration", "unit": "hours", "direction": "lower", "group_by": ["line"]}
    spec = Specification.from_dict(payload)
    payload["group_by"].append("shift")
    assert spec.group_by == ("line",)
    with pytest.raises(FrozenInstanceError):
        cast(Any, spec).usl = 8
    exported = spec.to_dict()
    exported["group_by"].append("station")
    assert spec.group_by == ("line",)
    window = AnalysisWindow(start=datetime(2026, 1, 1))
    with pytest.raises(FrozenInstanceError):
        cast(Any, window).start = datetime(2026, 2, 1)


@pytest.mark.parametrize("field", ["ucl", "lcl", "control_limits", "unexpected"])
def test_control_and_unknown_fields_rejected(field):
    """A control-limit declaration is never silently treated as a specification."""
    payload = {"name": "Duration", "unit": "hours", "direction": "lower", field: 3}
    with pytest.raises(ValidationError, match="Unknown fields"):
        Specification.from_dict(payload)


@pytest.mark.parametrize("payload", [{}, [], None, {"name": "Duration"}])
def test_invalid_payload(payload):
    """Malformed objects have domain errors instead of constructor exceptions."""
    with pytest.raises(ValidationError):
        Specification.from_dict(payload)


@pytest.mark.parametrize("value", ["{", "[]", "null", "5", None])
def test_invalid_json(value):
    """JSON parsing and object-shape failures are explicit."""
    with pytest.raises(ValidationError):
        Specification.from_json(value)


def test_serialized_nonfinite_number_rejected():
    """Even permissive JSON nonfinite tokens are rejected during model validation."""
    with pytest.raises(ValidationError, match="finite"):
        Specification.from_json('{"name":"Duration","unit":"hours","direction":"lower","usl":NaN}')


@pytest.mark.parametrize(
    "window",
    [
        {},
        {"start": "2026-01-01"},
        {"start": datetime(2026, 1, 1), "end": datetime(2026, 1, 1)},
        {"start": datetime(2026, 2, 1), "end": datetime(2026, 1, 1)},
        {"start": datetime(2026, 1, 1), "end": datetime(2026, 2, 1, tzinfo=UTC)},
    ],
)
def test_invalid_window(window):
    """Reject empty, non-datetime, reversed, and mixed-awareness observation windows."""
    with pytest.raises(ValidationError):
        AnalysisWindow(**window)


@pytest.mark.parametrize(
    "endpoints",
    [
        {"start": datetime(2026, 1, 1)},
        {"end": datetime(2026, 2, 1)},
        {"start": datetime(2026, 1, 1), "end": datetime(2026, 2, 1)},
    ],
)
def test_open_and_naive_windows(endpoints):
    """Support declared open bounds and preserve explicitly naive timestamps."""
    window = AnalysisWindow(**endpoints)
    assert AnalysisWindow.from_dict(window.to_dict()) == window


def test_offset_window():
    """Compare aware endpoints by instant and preserve their declared offsets."""
    window = AnalysisWindow(
        start=datetime(2026, 1, 1, 8, tzinfo=timezone(timedelta(hours=-5))),
        end=datetime(2026, 1, 1, 14, tzinfo=UTC),
    )
    assert AnalysisWindow.from_dict(window.to_dict()) == window
    start = window.to_dict()["start"]
    assert start is not None and start.endswith("-05:00")


@pytest.mark.parametrize("payload", [[], {"start": 5}, {"start": "not-a-date"}, {"bad": None}])
def test_invalid_window_payload(payload):
    """Serialized windows reject unknown keys and invalid ISO endpoints."""
    with pytest.raises(ValidationError):
        AnalysisWindow.from_dict(payload)


def test_pairing_with_describe_does_not_filter():
    """Specifications supply labels/grouping without silently filtering a cohort."""
    spec = Specification(
        name="Duration",
        unit="hours",
        direction="lower",
        usl=4,
        cohort="Future study",
        group_by=("team",),
    )
    observations = pl.DataFrame({"team": ["A", "A"], "hours": [2, 8]})
    results = describe(observations, column="hours", unit=spec.unit, group_by=spec.group_by)
    assert results[0].mean == 5 and results[0].count == 2
    assert spec.usl == 4  # No automatic defect classification or capability calculation.


def test_documented_example():
    """Keep the specification-and-summary example executable."""
    from pathlib import Path

    guide = Path(__file__).resolve().parents[1] / "docs" / "specifications.md"
    example = guide.read_text().split("```python\n")[1].split("```")[0]
    exec(compile(example, str(guide), "exec"), {})
