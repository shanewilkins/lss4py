# Moving-range control charts

`control_chart` provides the first governed statistical-process-control slice:
an MR(2) chart over adjacent observations. It separates Phase I limit estimation
from Phase II monitoring, retains the identity of every adjacent source pair,
and returns calculation evidence without rendering.

```python
import polars as pl

from lss4py import control_chart

phase_i = control_chart(
    pl.DataFrame(
        {
            "sample": ["a", "b", "c", "d", "e"],
            "minutes": [10.0, 11.0, 12.0, 13.0, 30.0],
        }
    ),
    column="minutes",
    key_column="sample",
    unit="minutes",
)

assert phase_i.phase == "I"
assert phase_i.moving_ranges.tolist() == [1.0, 1.0, 1.0, 17.0]
assert phase_i.signal_source_positions.tolist() == [4]
print(phase_i.to_frame())
```

The moving range at index `i` is `abs(x[i + 1] - x[i])`. Its source pair is
retained through zero-based start/end positions and, when `key_column` is
provided, detached start/end keys. Signal indexes address moving ranges rather
than source rows; `signal_source_positions` identifies the ending observation of
each signaled pair.

## Phase I limits

The chart span is fixed at two. LSS4PY uses the closed-form constants
`d2(2) = 2 / sqrt(pi)` and `d3(2) = sqrt(2 * (1 - 2 / pi))`.
For the mean moving range `MR_bar` and declared `nsigmas`:

- center line = `MR_bar`
- lower control limit = `max(0, MR_bar * (1 - nsigmas * d3 / d2))`
- upper control limit = `MR_bar * (1 + nsigmas * d3 / d2)`

Values strictly below the lower limit or above the upper limit are signals.
The default is three sigma. These are control limits estimated from observed
variation, not specification limits.

Phase I estimates are descriptive evidence about the supplied baseline. The
caller remains responsible for confirming meaningful sequence order, comparable
observations, and a baseline suitable for monitoring.

## Frozen Phase II monitoring

Pass the intact Phase I result as `baseline` to monitor later observations:

```python
phase_ii = control_chart(
    pl.DataFrame({"sample": ["f", "g", "h"], "minutes": [30.0, 45.0, 46.0]}),
    column="minutes",
    key_column="sample",
    baseline=phase_i,
    unit="minutes",
)

assert phase_ii.phase == "II"
assert phase_ii.ucl == phase_i.ucl
assert phase_ii.baseline_result_fingerprint is not None
```

Phase II copies the Phase I limits and records a fingerprint of that exact
baseline result. It never recalculates limits from monitoring data. The baseline
must be a schema-valid Phase I moving-range result with matching `nsigmas`;
edited limits and chained Phase II baselines are rejected.

An omitted Phase II `unit` inherits the baseline unit. An explicitly supplied
unit must match the baseline exactly, including whether a unit was declared;
convert measurements explicitly before monitoring. Limits are never converted
or relabeled implicitly.

## Worked example: convert, monitor, investigate

Run the complete [monitoring example](../examples/yellow_belt/monitoring.py):

```sh
uv run --locked python examples/yellow_belt/monitoring.py
```

The example estimates a baseline from six sequential durations in minutes,
`[10, 11, 9, 10, 14, 13]`, with keys `a` through `f`. Its mean moving range is
1.8 minutes and its three-sigma UCL is approximately 5.8798 minutes. This small
synthetic sample demonstrates the API; it does not establish stability or a
recommended baseline size. Assess collection design and baseline suitability
before using limits to make operational decisions.

Later observations `g`, `h`, and `i` arrive as `[780, 1380, 1320]` seconds. The
example retains those raw values and explicitly derives a minutes column:

```python
converted = recorded.with_columns((pl.col("duration_seconds") / 60).alias("duration_minutes"))
monitored = control_chart(
    converted,
    column="duration_minutes",
    key_column="sample",
    baseline=baseline,
)
```

Omitting `unit` inherits `minutes` from the baseline. The converted observations
are `[13, 23, 22]`, so their moving ranges are `[10, 1]` minutes. Limits remain
frozen, and the first pair signals. `signal_indices == [0]` refers to the first
moving range; `signal_source_positions == [1]` refers to its ending observation,
`h`. The pair-level table preserves both `g` and `h` for investigation. No pair
is formed across the boundary between the baseline and the monitoring batch.

Check the recorded measurements, collection conditions, and relevant process
changes around `g → h`. The signal identifies a change outside the declared
limits; it does not identify a cause, prove nonconformance to specifications,
or authorize dropping observations or recalibrating the baseline. The absence
of a signal on `h → i` does not establish overall process stability.

## Optional plotting

The visualization extra renders the completed pair-level evidence without
recalculating ranges, limits, or signals:

```python
from lss4py.reporting import plot_control_chart

ax = plot_control_chart(phase_i)
ax.figure.savefig("moving-range.png")
```

`plot_control_chart` returns a native Matplotlib `Axes` and accepts a caller-owned
`ax`. The horizontal axis uses each pair's ending source position, labeled with
the ending key when keys are available. The chart preserves the declared unit,
Phase I/II label, LCL, center line, UCL, and flagged points. The caller controls
display and export.

## Input and result contract

- Eager pandas, Polars, and PyArrow frames are accepted and are not mutated.
- At least two finite numeric observations are required.
- Missing values are rejected. Omitting a missing row would invent adjacency
  between observations that were not neighbors in the source.
- Source row order is the monitoring order; pandas indexes are not identities.
- Optional keys must be unique portable scalar values.
- `ControlChartResult.to_dict()` is strict portable evidence.
- `ControlChartResult.to_frame()` returns detached pair-level evidence as
  Polars by default, or pandas/PyArrow when explicitly requested.
- Audited analysis bundles restore the typed result without recalculation.

This slice does not include an individuals chart, rational subgroups, attribute
charts, run/trend/zone rules, automatic recalibration, or persistent control
plans. In particular, it does not expose general control-chart constant lookups.
Those remain separate future contracts rather than implied behavior.

## R SixSigma evidence

Checked-in fixtures execute SixSigma 0.11.1 `ss.cc(type="mr")` for Phase I,
Phase II, and insufficient-data behavior. The Python limits and signals reproduce
the retained R cases within the declared `2e-11` tolerance. The small tolerance
accounts for R's numerical integration of constants versus the closed forms
above. Python uses zero-based moving-range indexes; R reports them one-based.

LSS4PY intentionally requires a validated Phase I result for Phase II instead of
asking for raw baseline observations. This makes the reused limits and baseline
identity explicit and prevents implicit recalibration.

SixSigma 0.11.1 `ss.cc` itself supports only `type="mr"`; broader chart families
are LSS4PY roadmap gaps, not missing parity with that R function. Its ggplot
layout is not reproduced exactly. LSS4PY provides a composable Matplotlib chart
with equivalent moving-range, limit, phase, and signal evidence.
