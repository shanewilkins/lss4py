"""Verify optional plotting failures and presentation of completed timing evidence."""

import builtins

import numpy as np
import polars as pl
import pytest

from lss4py import ValidationError, lead_time
from lss4py.domain import AssumptionNote
from lss4py.reporting.visualization import plot_timing


@pytest.fixture
def timing():
    result = lead_time(
        pl.DataFrame({"start": ["2026-09-01T08:00:00"], "end": ["2026-09-01T10:00:00"]}),
        start_column="start",
        end_column="end",
        unit="hours",
    )
    result.provenance.warnings.append(AssumptionNote("COHORT", "One complete case", "warning"))
    return result


def test_plot_rejects_non_timing_results_before_loading_optional_dependencies(monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        assert not name.startswith(("matplotlib", "seaborn"))
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    with pytest.raises(ValidationError, match="requires a TimingResult"):
        plot_timing(None)  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize("missing", ["matplotlib", "seaborn"])
def test_plot_explains_how_to_install_missing_optional_dependencies(timing, missing, monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] == missing:
            raise ModuleNotFoundError(f"No module named {missing}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    with pytest.raises(ImportError, match=r"Install lss4py\[visualization\]") as caught:
        plot_timing(timing)
    assert isinstance(caught.value.__cause__, ModuleNotFoundError)


@pytest.mark.parametrize("keyed", [False, True])
def test_plot_creates_axes_preserves_evidence_and_restores_style(timing, keyed):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    if keyed:
        timing.keys = np.array(["WNF-003"])
    before = timing.to_dict()
    style = matplotlib.rcParams.copy()
    ax = plot_timing(timing)
    try:
        assert np.asarray(ax.lines[0].get_ydata()).tolist() == [2]
        assert [label.get_text() for label in ax.get_xticklabels()] == (
            ["WNF-003"] if keyed else ["0"]
        )
        assert ax.get_xlabel() == ("Case" if keyed else "Observation")
        assert ax.get_ylabel() == "Observed duration (hours)"
        assert [text.get_text() for text in ax.texts] == ["One complete case"]
        assert timing.to_dict() == before
        assert dict(matplotlib.rcParams) == dict(style)
    finally:
        assert isinstance(ax.figure, Figure)
        plt.close(ax.figure)
