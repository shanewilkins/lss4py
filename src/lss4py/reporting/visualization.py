"""Optional Matplotlib plots of completed analytical results, with Seaborn styling."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from lss4py.domain import (
    ControlChartResult,
    DistributionProfileResult,
    MeanCIResult,
    QualityLossResult,
    TimingResult,
)
from lss4py.errors import ValidationError

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def _plotting():
    """Load optional plotting dependencies only after result validation."""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ModuleNotFoundError as exc:
        raise ImportError("Install lss4py[visualization] to render statistical plots.") from exc
    return plt, sns


def _profile(result: DistributionProfileResult) -> None:
    """Require completed distribution evidence before loading plotting dependencies."""
    if not isinstance(result, DistributionProfileResult):
        raise ValidationError("Distribution plotting requires a DistributionProfileResult.")


def plot_timing(result: TimingResult, *, ax: Axes | None = None) -> Axes:
    """Draw observed durations in preserved order and return composable native axes.

    The caller controls display and export. Seaborn supplies a local style context;
    no Seaborn estimator, sorting, interval or smoothing operation is invoked.
    """
    if not isinstance(result, TimingResult):
        raise ValidationError("plot_timing requires a TimingResult.")
    plt, sns = _plotting()

    with sns.axes_style("whitegrid"):
        if ax is None:
            _, ax = plt.subplots(layout="constrained")
        positions = list(range(len(result.values)))
        ax.plot(positions, result.values, marker="o", label="Observed")
        _label_timing(ax, result, positions)
    return ax


def plot_mean_interval(result: MeanCIResult, *, ax: Axes | None = None) -> Axes:
    """Draw one completed mean estimate and confidence interval."""
    if not isinstance(result, MeanCIResult):
        raise ValidationError("plot_mean_interval requires a MeanCIResult.")
    plt, sns = _plotting()
    lower, upper = result.confidence_interval
    with sns.axes_style("whitegrid"):
        if ax is None:
            _, ax = plt.subplots(layout="constrained")
        ax.errorbar(
            [result.mean],
            [0],
            xerr=[[result.mean - lower], [upper - result.mean]],
            fmt="o",
            capsize=5,
            label=f"{result.confidence_level:g} confidence interval",
        )
        ax.set_yticks([])
        ax.set_xlabel(f"Mean ({result.unit})" if result.unit else "Mean")
        ax.set_title(result.name)
        ax.legend()
    return ax


def plot_control_chart(result: ControlChartResult, *, ax: Axes | None = None) -> Axes:
    """Draw stored moving ranges, limits, and signals without recalculation."""
    if not isinstance(result, ControlChartResult):
        raise ValidationError("plot_control_chart requires a ControlChartResult.")
    plt, sns = _plotting()
    positions = result.pair_end_positions
    labels = (
        list(map(str, positions))
        if result.pair_end_keys is None
        else list(map(str, result.pair_end_keys))
    )
    with sns.axes_style("whitegrid"):
        if ax is None:
            _, ax = plt.subplots(layout="constrained")
        ax.plot(positions, result.moving_ranges, marker="o", label="Moving range")
        if len(result.signal_indices):
            ax.scatter(
                result.signal_source_positions,
                result.moving_ranges[result.signal_indices],
                color="red",
                label="Signal",
                zorder=3,
            )
        ax.axhline(result.lcl, color="black", label="LCL")
        ax.axhline(result.center_line, color="black", linestyle="--", label="Center line")
        ax.axhline(result.ucl, color="black", label="UCL")
        ax.set_xticks(positions, labels)
        ax.set_xlabel("Ending key" if result.pair_end_keys is not None else "Ending observation")
        ax.set_ylabel(f"Moving range ({result.unit})" if result.unit else "Moving range")
        ax.set_title(f"{result.name} — Phase {result.phase}")
        ax.legend()
    return ax


def plot_quality_loss(result: QualityLossResult, *, ax: Axes | None = None) -> Axes:
    """Plot stored observation/loss pairs and calibration without evaluating a new curve."""
    if not isinstance(result, QualityLossResult):
        raise ValidationError("plot_quality_loss requires a QualityLossResult.")
    plt, sns = _plotting()
    with sns.axes_style("whitegrid"):
        if ax is None:
            _, ax = plt.subplots(layout="constrained")
        ax.scatter(result.values, result.losses, label="Modeled observation loss")
        ax.axhline(result.average_loss, linestyle="--", label="Average loss")
        ax.axhline(result.loss_at_tolerance, linestyle=":", label="Calibration loss")
        if result.target is not None:
            ax.axvline(result.target, color="black", linestyle=":", label="Target")
        ax.set_xlabel(f"Measurement ({result.unit})" if result.unit else "Measurement")
        ax.set_ylabel(f"Modeled loss ({result.loss_unit} per unit)")
        ax.set_title(
            f"Quality loss — {result.convention}-the-better"
            if result.convention != "nominal"
            else "Quality loss — nominal-the-best"
        )
        ax.legend()
    return ax


def plot_histogram(
    result: DistributionProfileResult,
    *,
    density: bool = False,
    show_kde: bool = False,
    ax: Axes | None = None,
) -> Axes:
    """Draw prepared histogram bins and optional precomputed KDE evidence."""
    _profile(result)
    if not isinstance(density, bool) or not isinstance(show_kde, bool):
        raise ValidationError("density and show_kde must be booleans.")
    if show_kde and not density:
        raise ValidationError("show_kde requires density=True so the vertical scales agree.")
    if show_kde and result.density_method is None:
        raise ValidationError("The distribution profile does not contain density evidence.")
    plt, sns = _plotting()
    heights = result.histogram_density if density else result.histogram_counts
    with sns.axes_style("whitegrid"):
        if ax is None:
            _, ax = plt.subplots(layout="constrained")
        left = result.histogram_edges[:-1]
        widths = np.diff(result.histogram_edges)
        ax.bar(left, heights, width=widths, align="edge", label="Observed")
        if show_kde:
            ax.plot(result.density_x, result.density_y, label="Gaussian KDE")
        ax.set_xlabel(f"Value ({result.unit})" if result.unit else "Value")
        ax.set_ylabel("Density" if density else "Count")
        ax.set_title(result.name)
        if show_kde:
            ax.legend()
    return ax


def plot_ecdf(result: DistributionProfileResult, *, ax: Axes | None = None) -> Axes:
    """Draw the prepared empirical cumulative distribution."""
    _profile(result)
    plt, sns = _plotting()
    with sns.axes_style("whitegrid"):
        if ax is None:
            _, ax = plt.subplots(layout="constrained")
        ax.step(result.ecdf_values, result.ecdf_probabilities, where="post")
        ax.set_xlabel(f"Value ({result.unit})" if result.unit else "Value")
        ax.set_ylabel("Empirical cumulative probability")
        ax.set_ylim(0, 1.02)
        ax.set_title(result.name)
    return ax


def plot_qq(result: DistributionProfileResult, *, ax: Axes | None = None) -> Axes:
    """Draw prepared normal Q-Q coordinates and their stored reference line."""
    _profile(result)
    plt, sns = _plotting()
    with sns.axes_style("whitegrid"):
        if ax is None:
            _, ax = plt.subplots(layout="constrained")
        ax.scatter(result.qq_theoretical, result.qq_observed, label="Observed quantiles")
        ax.plot(result.qq_line_x, result.qq_line_y, label="Fitted reference")
        ax.set_xlabel("Theoretical normal quantiles")
        ax.set_ylabel(
            f"Observed quantiles ({result.unit})" if result.unit else "Observed quantiles"
        )
        ax.set_title(f"{result.name} — normal Q-Q")
        ax.legend()
    return ax


def plot_box(result: DistributionProfileResult, *, ax: Axes | None = None) -> Axes:
    """Draw a horizontal box plot from stored quartiles, whiskers and outlier evidence."""
    _profile(result)
    plt, sns = _plotting()
    try:
        from matplotlib.patches import Rectangle
    except ModuleNotFoundError as exc:
        raise ImportError("Install lss4py[visualization] to render statistical plots.") from exc
    with sns.axes_style("whitegrid"):
        if ax is None:
            _, ax = plt.subplots(layout="constrained")
        ax.add_patch(Rectangle((result.q1, 0.75), result.iqr, 0.5, fill=False))
        ax.vlines(result.median, 0.75, 1.25)
        ax.hlines(1, result.lower_whisker, result.q1)
        ax.hlines(1, result.q3, result.upper_whisker)
        ax.vlines([result.lower_whisker, result.upper_whisker], 0.88, 1.12)
        if len(result.outlier_values):
            ax.scatter(result.outlier_values, np.ones(len(result.outlier_values)), label="Flagged")
            ax.legend()
        ax.set_yticks([])
        ax.set_ylim(0.5, 1.5)
        ax.set_xlabel(f"Value ({result.unit})" if result.unit else "Value")
        ax.set_title(result.name)
    return ax


def _label_timing(ax: Axes, result: TimingResult, positions: list[int]) -> None:
    """Preserve explicit identity, units and diagnostics in the presentation."""
    labels = result.keys.tolist() if result.keys is not None else list(map(str, positions))
    ax.set_xticks(positions, labels)
    ax.set_xlabel("Case" if result.keys is not None else "Observation")
    ax.set_ylabel(f"Observed duration ({result.unit})")
    ax.set_title(result.name)
    ax.legend()
    notes = [note.message for note in result.provenance.warnings]
    if notes:
        ax.text(0, -0.22, ", ".join(notes), transform=ax.transAxes, wrap=True)
