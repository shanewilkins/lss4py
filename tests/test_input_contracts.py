"""Unsupported input boundaries shared by all public tabular calculations."""

import numpy as np
import pandas as pd
import polars as pl
import pytest

import lss4py


@pytest.fixture(
    params=[
        "dictionary",
        "records",
        "numpy-array",
        "pandas-series",
        "polars-series",
        "polars-lazy",
    ]
)
def unsupported_input(request):
    """Supply rejected native inputs, including a lazy plan that must not execute."""
    factories = {
        "dictionary": lambda: {"x": [1]},
        "records": lambda: [{"x": 1}],
        "numpy-array": lambda: np.array([1]),
        "pandas-series": lambda: pd.Series([1]),
        "polars-series": lambda: pl.Series("x", [1]),
        "polars-lazy": lambda: pl.DataFrame({"x": [1]}).lazy(),
    }
    return factories[request.param]()


@pytest.mark.parametrize(
    "method",
    [
        "lead_time",
        "wait_time",
        "process_cycle_efficiency",
        "created_to_booked_yield",
        "booked_to_completed_yield",
        "rolled_yield",
        "describe",
        "capability_indices",
    ],
)
def test_tabular_methods_require_eager_frames(method, unsupported_input):
    """Reject unsupported/lazy inputs before attempting field resolution or analysis."""
    parameters = {"column": "x"} if method == "describe" else {}
    if method == "capability_indices":
        parameters = {
            "column": "x",
            "specification": lss4py.Specification("CTQ", "mm", "lower", usl=2),
        }
    with pytest.raises(TypeError):
        getattr(lss4py, method)(unsupported_input, **parameters)


def test_lazy_plan_is_not_collected(monkeypatch):
    """Input rejection must not execute the supplied lazy computation."""

    def fail(*_args, **_kwargs):
        pytest.fail("Lazy plan was executed")

    monkeypatch.setattr(pl.LazyFrame, "collect", fail)
    with pytest.raises(TypeError):
        lss4py.describe(pl.DataFrame({"x": [1]}).lazy(), column="x")
