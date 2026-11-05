"""Verify optional plotting failures and presentation of completed timing evidence."""

import builtins

import numpy as np
import polars as pl
import pytest

from lss4py import (
    ValidationError,
    control_chart,
    distribution_profile,
    lead_time,
    mean_confidence_interval,
)
from lss4py.domain import AssumptionNote
from lss4py.reporting.visualization import (
    plot_box,
    plot_control_chart,
    plot_ecdf,
    plot_histogram,
    plot_mean_interval,
    plot_qq,
    plot_timing,
)


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


@pytest.fixture
def distribution():
    return distribution_profile(
        pl.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 20.0]}),
        column="value",
        histogram_bins=2,
        density=True,
        density_grid_points=64,
        unit="minutes",
    )


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


def test_mean_interval_plot_uses_stored_estimate_and_bounds():
    result = mean_confidence_interval(
        pl.DataFrame({"value": [1.0, 2.0, 4.0, 8.0]}),
        column="value",
        unit="minutes",
    )
    ax = plot_mean_interval(result)
    try:
        from matplotlib.collections import LineCollection

        assert np.asarray(ax.lines[0].get_xdata()).tolist() == [result.mean]
        errors = ax.collections[0]
        assert isinstance(errors, LineCollection)
        assert errors.get_segments()[0][:, 0].tolist() == pytest.approx(
            list(result.confidence_interval)
        )
        assert ax.get_xlabel() == "Mean (minutes)"
    finally:
        import matplotlib.pyplot as plt

        plt.close("all")


def test_control_chart_plot_uses_stored_pair_identity_limits_and_signals():
    result = control_chart(
        pl.DataFrame(
            {
                "sample": ["a", "b", "c", "d", "e"],
                "value": [10.0, 11.0, 12.0, 13.0, 30.0],
            }
        ),
        column="value",
        key_column="sample",
        unit="minutes",
    )
    before = result.to_dict()
    ax = plot_control_chart(result)
    try:
        lines = {line.get_label(): line for line in ax.lines}
        assert np.asarray(lines["Moving range"].get_xdata()).tolist() == [1, 2, 3, 4]
        assert np.asarray(lines["Moving range"].get_ydata()).tolist() == [1, 1, 1, 17]
        assert np.asarray(lines["LCL"].get_ydata()).tolist() == [result.lcl, result.lcl]
        assert np.asarray(lines["Center line"].get_ydata()).tolist() == [
            result.center_line,
            result.center_line,
        ]
        assert np.asarray(lines["UCL"].get_ydata()).tolist() == [result.ucl, result.ucl]
        assert np.asarray(ax.collections[0].get_offsets()).tolist() == [[4.0, 17.0]]
        assert [label.get_text() for label in ax.get_xticklabels()] == ["b", "c", "d", "e"]
        assert ax.get_xlabel() == "Ending key"
        assert ax.get_ylabel() == "Moving range (minutes)"
        assert ax.get_title().endswith("Phase I")
        assert result.to_dict() == before
    finally:
        import matplotlib.pyplot as plt

        plt.close("all")


def test_control_chart_plot_accepts_caller_axes_and_positional_identity():
    import matplotlib.pyplot as plt

    result = control_chart(pl.DataFrame({"value": [1.0, 2.0, 1.0]}), column="value")
    _, supplied = plt.subplots()
    try:
        assert plot_control_chart(result, ax=supplied) is supplied
        assert [label.get_text() for label in supplied.get_xticklabels()] == ["1", "2"]
        assert supplied.get_xlabel() == "Ending observation"
    finally:
        plt.close("all")


def test_distribution_plots_use_stored_evidence(distribution):
    import matplotlib.pyplot as plt

    axes = [
        plot_histogram(distribution, density=True, show_kde=True),
        plot_ecdf(distribution),
        plot_qq(distribution),
        plot_box(distribution),
    ]
    try:
        from matplotlib.patches import Rectangle

        histogram, ecdf, qq, box = axes
        bars = histogram.patches
        rectangles = [patch for patch in bars if isinstance(patch, Rectangle)]
        assert len(rectangles) == len(bars)
        assert [patch.get_height() for patch in rectangles] == pytest.approx(
            distribution.histogram_density
        )
        assert np.asarray(histogram.lines[0].get_xdata()).tolist() == pytest.approx(
            distribution.density_x
        )
        assert np.asarray(ecdf.lines[0].get_xdata()).tolist() == pytest.approx(
            distribution.ecdf_values
        )
        assert np.asarray(ecdf.lines[0].get_ydata()).tolist() == pytest.approx(
            distribution.ecdf_probabilities
        )
        offsets = np.asarray(qq.collections[0].get_offsets())
        assert offsets[:, 0].tolist() == pytest.approx(distribution.qq_theoretical)
        assert offsets[:, 1].tolist() == pytest.approx(distribution.qq_observed)
        assert np.asarray(qq.lines[0].get_ydata()).tolist() == pytest.approx(distribution.qq_line_y)
        rectangle = box.patches[0]
        assert isinstance(rectangle, Rectangle)
        assert rectangle.get_x() == distribution.q1
        assert rectangle.get_width() == distribution.iqr
    finally:
        plt.close("all")


@pytest.mark.parametrize("plotter", [plot_histogram, plot_ecdf, plot_qq, plot_box])
def test_distribution_plots_accept_caller_axes(distribution, plotter):
    import matplotlib.pyplot as plt

    _, supplied = plt.subplots()
    try:
        assert plotter(distribution, ax=supplied) is supplied
    finally:
        plt.close("all")


def test_renderers_do_not_recompute_histograms(monkeypatch, distribution):
    monkeypatch.setattr(
        np,
        "histogram",
        lambda *args, **kwargs: pytest.fail("renderer recomputed evidence"),
    )
    ax = plot_histogram(distribution)
    try:
        assert ax.patches
    finally:
        import matplotlib.pyplot as plt

        plt.close("all")


def test_histogram_requires_prepared_density_evidence():
    result = distribution_profile(
        pl.DataFrame({"value": [1.0, 2.0, 3.0]}),
        column="value",
    )
    with pytest.raises(ValidationError, match="requires density=True"):
        plot_histogram(result, show_kde=True)
    with pytest.raises(ValidationError, match="does not contain density"):
        plot_histogram(result, density=True, show_kde=True)


@pytest.mark.parametrize(
    ("plotter", "match"),
    [
        (plot_mean_interval, "MeanCIResult"),
        (plot_control_chart, "ControlChartResult"),
        (plot_histogram, "DistributionProfileResult"),
        (plot_ecdf, "DistributionProfileResult"),
        (plot_qq, "DistributionProfileResult"),
        (plot_box, "DistributionProfileResult"),
    ],
)
def test_new_plots_validate_results_before_loading_dependencies(monkeypatch, plotter, match):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        assert not name.startswith(("matplotlib", "seaborn"))
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    with pytest.raises(ValidationError, match=match):
        plotter(None)


def test_new_plots_preserve_results_and_global_style(distribution):
    import matplotlib
    import matplotlib.pyplot as plt

    before_result = distribution.to_dict()
    before_style = matplotlib.rcParams.copy()
    plot_histogram(distribution)
    plot_ecdf(distribution)
    plot_qq(distribution)
    plot_box(distribution)
    try:
        assert distribution.to_dict() == before_result
        assert dict(matplotlib.rcParams) == dict(before_style)
    finally:
        plt.close("all")
