"""Timing kernels: lead time, cycle time, efficiency, and takt time.

Core Yellow Belt timing calculations with full provenance and typed results.
"""

from __future__ import annotations

from typing import Any

import narwhals as nw
import numpy as np

from lss4py._event_log import event_log_lead_time
from lss4py._kernels._helpers import (
    TimeUnit,
    build_provenance,
    event_log_bindings_available,
    require_columns,
    resolve_cycle_time_series,
    resolve_lead_time_columns,
    resolve_lead_time_series,
    resolve_value_add_time_series,
)
from lss4py.domain import IntervalEventLog, ProcessModelIR, TimingResult
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis

_SECONDS_PER_UNIT: dict[TimeUnit, float] = {
    "seconds": 1.0,
    "minutes": 60.0,
    "hours": 3600.0,
    "days": 86400.0,
}


def _timestamp_series(frame: nw.DataFrame, column: str) -> nw.Series:
    """Parse strings explicitly and preserve native datetime timezone semantics."""
    series = frame[column]
    try:
        if series.dtype == nw.String:
            return series.str.to_datetime()
        if isinstance(series.dtype, nw.Datetime):
            return series
        return series.cast(nw.Datetime)
    except Exception as exc:
        raise ValidationError(f"Column '{column}' contains invalid timestamps.") from exc


@register_analysis(
    AnalysisSuitability(
        name="lead_time",
        family="timing",
        question_tags=("elapsed_time",),
        required_fields=(
            ("start_timestamp", "end_timestamp"),
            ("case_id", "step_id", "started_at", "completed_at", "process_model"),
        ),
        data_types=("timestamps", "interval_event_log"),
        prerequisites=(
            "Consistent timestamp units and timezone awareness.",
            "Interval logs require explicit process bindings and declared parallel/rework edges.",
        ),
        assumptions=("Observed boundaries represent the intended process start and completion.",),
        alternatives=("wait_time",),
        limits=("Elapsed time includes both working and waiting; it does not separate them.",),
        belt_level="yellow",
        design_types=("observational",),
    )
)
def lead_time(
    data: Any,  # IntoFrame (pandas, Polars, PyArrow)
    *,
    start_column: str | None = None,
    end_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    unit: TimeUnit = "hours",
) -> TimingResult:
    """Calculate lead time per row.

    **Belt Level:** Yellow Belt (measure current state)

    **Suitable When:** You have timestamp columns marking process start and end,
    and you want to understand the time customers spend waiting plus working.

    **Not Suitable When:** You need to distinguish working time from wait time
    (use wait_time instead), or you need to account for parallel activities
    (use process model aware aggregations in v0.3).

    Args:
        data: DataFrame in pandas, Polars, or PyArrow format.
        start_column: Timestamp column for process start.
        end_column: Timestamp column for process end.
        process_model: Optional ProcessModelIR with lead-time bindings.
        unit: Time unit for results ("seconds", "minutes", "hours", "days").

    Returns:
        TimingResult with per-row lead times in requested unit, including full
        provenance, assumptions, and interpretation context.
    """
    native_data = data.to_polars(copy=False) if isinstance(data, IntervalEventLog) else data
    frame = nw.from_native(native_data, eager_only=True)

    if (
        start_column is None
        and end_column is None
        and event_log_bindings_available(frame, process_model)
    ):
        assert process_model is not None
        keys, result = event_log_lead_time(
            native_data,
            process_model=process_model,
            seconds_per_unit=_SECONDS_PER_UNIT[unit],
        )
        provenance = build_provenance(
            method_name="lead_time",
            frame=frame,
            parameters={
                "unit": unit,
                "process_model": True,
                "data_shape": "interval_event_log",
                "case_id_column": process_model.bindings.event_log.case_id_column,
                "step_id_column": process_model.bindings.event_log.step_id_column,
                "started_at_column": process_model.bindings.event_log.started_at_column,
                "completed_at_column": process_model.bindings.event_log.completed_at_column,
            },
            assumptions=[
                {
                    "code": "CASE_BOUNDARIES",
                    "message": (
                        "Per-case lead time uses the earliest activity start and latest "
                        "activity completion."
                    ),
                },
                {
                    "code": "INTERVAL_EVENT_LOG",
                    "message": (
                        "Each row represents one activity interval with explicit case and step IDs."
                    ),
                },
            ],
        )
        return TimingResult(
            name="Lead Time",
            provenance=provenance,
            values=result,
            keys=keys,
            unit=unit,
            interpretation_context=(
                "Lead time is the elapsed time from the first observed activity start to "
                "the last observed activity completion for each case."
            ),
        )

    resolved_start_column, resolved_end_column = resolve_lead_time_columns(
        process_model=process_model,
        start_column=start_column,
        end_column=end_column,
    )
    require_columns(frame, resolved_start_column, resolved_end_column)

    start = _timestamp_series(frame, resolved_start_column)
    end = _timestamp_series(frame, resolved_end_column)
    # Extract fractional seconds through the backend-neutral duration namespace.
    durations_seconds = (end - start).dt.total_microseconds().to_numpy() / 1_000_000

    result = durations_seconds / _SECONDS_PER_UNIT[unit]

    if np.any(result < 0):
        raise ValidationError("Lead time cannot be negative.")

    # Build and return typed result with provenance
    provenance = build_provenance(
        method_name="lead_time",
        frame=frame,
        parameters={
            "start_column": resolved_start_column,
            "end_column": resolved_end_column,
            "unit": unit,
            "process_model": process_model is not None,
        },
        assumptions=[
            {
                "code": "TIMESTAMP_ORDERING",
                "message": "Assumes end_column >= start_column (time flows forward)",
            }
        ],
    )

    return TimingResult(
        name="Lead Time",
        provenance=provenance,
        values=result,
        unit=unit,
        interpretation_context=(
            "Lead time is the total elapsed time from process start to completion. "
            "Includes both value-add and wait time. "
            "Use to establish baseline performance and identify improvement opportunities."
        ),
    )


@register_analysis(
    AnalysisSuitability(
        name="wait_time",
        family="timing",
        question_tags=("waiting_time",),
        required_fields=(("lead_time_column", "cycle_time_column"),),
        data_types=("numeric_duration",),
        prerequisites=("Explicit measured lead and cycle columns are required.",),
        assumptions=("Lead and cycle measurements use the same units and scope.",),
        alternatives=("lead_time", "process_cycle_efficiency"),
        limits=(
            "Branch-aware interval-event inference is unavailable.",
            "Lead minus cycle time does not identify the cause of waiting.",
        ),
        belt_level="yellow",
        design_types=("observational",),
    )
)
def wait_time(
    data: Any,  # IntoFrame
    *,
    lead_time_column: str | None = None,
    cycle_time_column: str | None = None,
    process_model: ProcessModelIR | None = None,
) -> TimingResult:
    """Calculate wait time per row (lead time - cycle time).

    **Belt Level:** Yellow Belt (measure current state)

    **Suitable When:** You have measured lead time and cycle time, and you want
    to quantify non-value-adding time (the opportunity to improve).

    **Not Suitable When:** You don't have both lead and cycle time measurements
    (lead_time() and process_cycle_efficiency() may be better choices).

    Args:
        data: DataFrame in pandas, Polars, or PyArrow format.
        lead_time_column: Explicit lead-time column.
        cycle_time_column: Explicit cycle-time column.
        process_model: Optional ProcessModelIR (v0.3).

    Returns:
        TimingResult with per-row wait times, including full provenance.
    """
    frame = nw.from_native(data, eager_only=True)

    lead = resolve_lead_time_series(
        frame,
        process_model=process_model,
        lead_time_column=lead_time_column,
    )
    cycle = resolve_cycle_time_series(
        frame,
        process_model=process_model,
        cycle_time_column=cycle_time_column,
    )

    waits = lead - cycle
    if np.any(waits < 0):
        raise ValidationError("Wait time cannot be negative. Check lead and cycle time inputs.")

    # Build and return typed result with provenance
    provenance = build_provenance(
        method_name="wait_time",
        frame=frame,
        parameters={
            "lead_time_column": lead_time_column,
            "cycle_time_column": cycle_time_column,
            "process_model": process_model is not None,
        },
        assumptions=[
            {
                "code": "LEAD_CYCLE_RELATIONSHIP",
                "message": (
                    "Wait time = lead time - cycle time (assumes both measured consistently)"
                ),
            }
        ],
    )

    return TimingResult(
        name="Wait Time",
        provenance=provenance,
        values=waits,
        unit="hours",
        interpretation_context=(
            "Wait time is the portion of lead time that is not productive work. "
            "This represents non-value-adding delay and rework. "
            "Focus on reducing wait time through process redesign and removal of bottlenecks."
        ),
    )


@register_analysis(
    AnalysisSuitability(
        name="process_cycle_efficiency",
        family="timing",
        question_tags=("value_add_share",),
        required_fields=(("lead_time_column", "value_add_time_column"),),
        data_types=("numeric_duration",),
        prerequisites=("Explicit lead and value-add columns; lead time must be positive.",),
        assumptions=(
            "Value-add classification is supplied by the practitioner.",
            "Measurements use the same units and process scope.",
        ),
        alternatives=("wait_time",),
        limits=(
            "Branch-aware interval-event inference is unavailable.",
            "The ratio does not establish an improvement effect.",
        ),
        belt_level="yellow",
        design_types=("observational",),
    )
)
def process_cycle_efficiency(
    data: Any,  # IntoFrame
    *,
    lead_time_column: str | None = None,
    value_add_time_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    as_percentage: bool = True,
) -> TimingResult:
    """Calculate process cycle efficiency per row (value-add time / lead time).

    **Belt Level:** Yellow Belt (measure current state)

    **Suitable When:** You have lead time and can identify value-adding time,
    and you want a ratio of productive work.

    **Not Suitable When:** You need to validate measurement system (use Gage R&R),
    or you need to test if efficiency differs before/after (use Green Belt methods).

    Args:
        data: DataFrame in pandas, Polars, or PyArrow format.
        lead_time_column: Explicit lead-time column.
        value_add_time_column: Explicit value-add time column.
        process_model: Optional ProcessModelIR (v0.3).
        as_percentage: Return as percentage (default) or ratio.

    Returns:
        TimingResult with per-row efficiency values (percentage or ratio), including provenance.
    """
    frame = nw.from_native(data, eager_only=True)

    lead = resolve_lead_time_series(
        frame,
        process_model=process_model,
        lead_time_column=lead_time_column,
    )
    value_add = resolve_value_add_time_series(
        frame,
        process_model=process_model,
        value_add_time_column=value_add_time_column,
    )

    if np.any(lead <= 0):
        raise ValidationError("Lead time must be greater than zero for process cycle efficiency.")

    if np.any(value_add < 0) or np.any(value_add > lead):
        raise ValidationError("Value-add time must be between zero and lead time.")

    efficiency = value_add / lead
    unit = "percentage" if as_percentage else "ratio"
    if as_percentage:
        efficiency = efficiency * 100.0

    # Build and return typed result with provenance
    provenance = build_provenance(
        method_name="process_cycle_efficiency",
        frame=frame,
        parameters={
            "lead_time_column": lead_time_column,
            "value_add_time_column": value_add_time_column,
            "as_percentage": as_percentage,
            "process_model": process_model is not None,
        },
        assumptions=[
            {
                "code": "VALUE_ADD_CLASSIFICATION",
                "message": (
                    "Assumes value-add time correctly classified "
                    "(e.g., via process model or expert review)"
                ),
            }
        ],
    )

    return TimingResult(
        name="Process Cycle Efficiency",
        provenance=provenance,
        values=efficiency,
        unit=unit,
        interpretation_context=(
            "Process cycle efficiency is the ratio of productive work time to total lead time. "
            "Higher is better. Use to identify waste and prioritize process improvements. "
            "Complement with wait-time analysis to identify bottlenecks."
        ),
    )


@register_analysis(
    AnalysisSuitability(
        name="takt_time",
        family="timing",
        question_tags=("demand_pace",),
        required_fields=(("available_time", "customer_demand"),),
        data_types=("scalar",),
        prerequisites=("Positive available time and demand for the same period.",),
        assumptions=("Available productive time and demand represent the planning period.",),
        alternatives=("lead_time",),
        limits=("Takt is a planning pace, not observed cycle time or a capacity guarantee.",),
        belt_level="yellow",
        design_types=("planning",),
    )
)
def takt_time(*, available_time: float, customer_demand: float) -> float:
    """Calculate takt time (available production time / customer demand).

    **Belt Level:** Yellow Belt (measure current state)

    **Suitable When:** You want to know the pace needed to meet customer demand,
    and you have steady, predictable demand and available production time.

    **Not Suitable When:** Demand is highly variable or unpredictable (use
    simulation for scenario analysis in Black Belt phase).

    Args:
        available_time: Production time available (in any unit).
        customer_demand: Customer demand per period (same unit).

    Returns:
        Takt time (production time per unit).

    Raises:
        ValidationError: if demand is zero or non-positive.
    """
    if available_time <= 0:
        raise ValidationError("Available time must be greater than zero.")

    if customer_demand <= 0:
        raise ValidationError("Customer demand must be greater than zero.")

    return available_time / customer_demand
