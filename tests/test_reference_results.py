"""Offline numerical regressions against certified and independently derived fixtures."""

import math
from collections.abc import Callable
from copy import deepcopy
from typing import Any

import pytest

from lss4py import (
    ValidationError,
    booked_to_completed_yield,
    created_to_booked_yield,
    describe,
    lead_time,
    process_cycle_efficiency,
    rolled_yield,
    takt_time,
    wait_time,
)
from tests.reference_catalog import load_catalog

METHODS: dict[str, Callable[..., Any]] = {
    "describe": describe,
    "lead_time": lead_time,
    "wait_time": wait_time,
    "process_cycle_efficiency": process_cycle_efficiency,
    "takt_time": takt_time,
    "created_to_booked_yield": created_to_booked_yield,
    "booked_to_completed_yield": booked_to_completed_yield,
    "rolled_yield": rolled_yield,
}
CATALOG = [
    entry
    for entry in load_catalog()
    if entry["metadata"].get("validation_status") != "reference_only"
]
CASES = [(entry, case) for entry in CATALOG for case in entry["expected"]]
INVALID = [(entry, case) for entry in CATALOG for case in entry["invalid"]]
pytestmark = pytest.mark.parametrize(
    "backend",
    ["pandas", "pandas-indexed", "polars", "pyarrow"],
    indirect=True,
)


def _compare(actual, expected, tolerance):
    """Compare only certified/derived fields, keeping counts and identifiers exact."""
    if isinstance(expected, dict):
        for key, value in expected.items():
            _compare(actual[key], value, tolerance)
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for left, right in zip(actual, expected, strict=True):
            _compare(left, right, tolerance)
    elif isinstance(expected, float):
        assert math.isclose(
            actual, expected, rel_tol=tolerance["relative"], abs_tol=tolerance["absolute"]
        )
    else:
        assert type(actual) is type(expected)
        assert actual == expected


@pytest.mark.parametrize(
    ("entry", "case"),
    CASES,
    ids=[f"{entry['metadata']['id']}/{case['id']}" for entry, case in CASES],
)
def test_governed_numerical_reference(frame_factory, entry, case):
    """Run fixed expectations without deriving expected outputs from lss4py."""
    method = METHODS[case["method"]]
    if case["input_kind"] == "scalar":
        payload = {"value": method(**case["parameters"])}
    else:
        result = method(frame_factory(entry["inputs"]["columns"]), **case["parameters"])
        payload = result.to_dict()
    _compare(payload, case["expected"], case["tolerance"])


@pytest.mark.parametrize(
    ("entry", "case"),
    INVALID,
    ids=[f"{entry['metadata']['id']}/{case['id']}" for entry, case in INVALID],
)
def test_governed_invalid_input_reference(frame_factory, entry, case):
    """Preserve the checked-in analytical error contract on each backend."""
    columns = deepcopy(entry["inputs"]["columns"])
    columns.update(case["columns_override"])
    method = METHODS[case["method"]]
    args = () if case["method"] == "takt_time" else (frame_factory(columns),)
    with pytest.raises(ValidationError, match=case["message"]):
        method(*args, **case["parameters"])
