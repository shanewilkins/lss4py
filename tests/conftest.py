"""Shared eager-backend factories and analytical contract data."""

from copy import deepcopy
from importlib import import_module

import pandas as pd
import polars as pl
import pytest

from lss4py import (
    EventLogBindingsIR,
    MetricBindingsIR,
    ProcessEdgeIR,
    ProcessModelIR,
    ProcessStepIR,
)


def pytest_addoption(parser):
    """Let CI require the provisional Arrow matrix rather than silently skip it."""
    parser.addoption(
        "--require-pyarrow", action="store_true", help="Fail if PyArrow is unavailable"
    )


@pytest.fixture(params=["pandas", "pandas-indexed", "polars"])
def backend(request):
    """Select governed eager inputs, including duplicate/non-default pandas labels."""
    return request.param


@pytest.fixture
def frame_factory(backend, request):
    """Build independent frames directly from records without cross-backend conversion."""
    if backend == "polars":
        return pl.DataFrame
    if backend == "pyarrow":
        arrow = (
            import_module("pyarrow")
            if request.config.getoption("--require-pyarrow")
            else pytest.importorskip("pyarrow")
        )
        return arrow.table

    def pandas_frame(records):
        """Use hostile index labels to expose accidental label-based row identity."""
        frame = pd.DataFrame(records)
        if backend == "pandas-indexed":
            frame.index = pd.Index([17 if i % 2 == 0 else -3 for i in range(len(frame))])
        return frame

    return pandas_frame


@pytest.fixture
def measurement_records():
    """Supply aligned timestamps, durations, and nested stage outcomes."""
    return {
        "start": ["2026-01-01T08:00:00", "2026-01-02T09:00:00", "2026-01-03T10:00:00"],
        "end": ["2026-01-01T18:00:00", "2026-01-02T14:00:00", "2026-01-03T12:00:00"],
        "lead": [10.0, 5.0, 2.0],
        "cycle": [4.0, 1.0, 1.0],
        "value_add": [3.0, 1.0, 0.5],
        "created": [1, 1, 1],
        "booked": [1, 1, 0],
        "completed": [1, 0, 0],
    }


@pytest.fixture
def interval_records():
    """Interleave cases and step order to expose index/order assumptions."""
    return {
        "case_id": ["C2", "C1", "C2"],
        "step_id": ["review", "intake", "intake"],
        "started_at": ["2026-09-01T09:30:00", "2026-09-02T08:00:00", "2026-09-01T08:00:00"],
        "completed_at": ["2026-09-01T11:00:00", "2026-09-02T10:00:00", "2026-09-01T09:00:00"],
    }


@pytest.fixture
def interval_process_model():
    """Declare the shared sequential interval-log bindings and topology."""
    return ProcessModelIR(
        name="Intake",
        steps=[
            ProcessStepIR(id="intake", name="Intake"),
            ProcessStepIR(id="review", name="Review"),
        ],
        edges=[ProcessEdgeIR(source_step_id="intake", target_step_id="review")],
        bindings=MetricBindingsIR(
            event_log=EventLogBindingsIR(
                case_id_column="case_id",
                step_id_column="step_id",
                started_at_column="started_at",
                completed_at_column="completed_at",
            )
        ),
    )


@pytest.fixture
def neutral_payload():
    """Remove only backend identity and computation time from serialized results."""

    def normalize(result):
        """Retain all numerical, ordering, warning, and method metadata for comparison."""
        if isinstance(result, list):
            return [normalize(item) for item in result]
        payload = deepcopy(result.to_dict())
        payload["provenance"].pop("backend")
        payload["provenance"].pop("created_at")
        return payload

    return normalize


@pytest.fixture
def assert_equivalent():
    """Compare complete neutral payloads with explicit floating-point tolerances."""

    def compare(actual, expected):
        """Compare nested fields without discarding result-contract differences."""
        if isinstance(expected, dict):
            assert actual.keys() == expected.keys()
            for key in expected:
                compare(actual[key], expected[key])
        elif isinstance(expected, list):
            assert len(actual) == len(expected)
            for left, right in zip(actual, expected, strict=True):
                compare(left, right)
        elif isinstance(expected, float):
            assert actual == pytest.approx(expected, rel=1e-12, abs=1e-12)
        else:
            assert actual == expected

    return compare
