"""Optional Matplotlib plots of completed analytical results, with Seaborn styling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lss4py.domain import TimingResult
from lss4py.errors import ValidationError

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def plot_timing(result: TimingResult, *, ax: Axes | None = None) -> Axes:
    """Draw observed durations in preserved order and return composable native axes.

    The caller controls display and export. Seaborn supplies a local style context;
    no Seaborn estimator, sorting, interval or smoothing operation is invoked.
    """
    if not isinstance(result, TimingResult):
        raise ValidationError("plot_timing requires a TimingResult.")
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ModuleNotFoundError as exc:
        raise ImportError("Install lss4py[visualization] to render statistical plots.") from exc

    with sns.axes_style("whitegrid"):
        if ax is None:
            _, ax = plt.subplots(layout="constrained")
        positions = list(range(len(result.values)))
        ax.plot(positions, result.values, marker="o", label="Observed")
        _label_timing(ax, result, positions)
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
