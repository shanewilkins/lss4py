"""Timing kernels: lead time, cycle time, efficiency, and takt time.

Core Yellow Belt timing calculations with full provenance and typed results.
"""

from __future__ import annotations

from typing import Any

import narwhals as nw
import numpy as np

from lss4py.domain import ProcessModelIR, TimingResult
from lss4py.errors import ValidationError
from lss4py.kernels._helpers import (
    TimeUnit,
    build_provenance,
    event_log_bindings_available,
    require_columns,
    resolve_cycle_time_series,
    resolve_lead_time_columns,
    resolve_lead_time_series,
    resolve_value_add_time_series,
)

_SECONDS_PER_UNIT: dict[TimeUnit, float] = {
    "seconds": 1.0,
    "minutes": 60.0,
    "hours": 3600.0,
    "days": 86400.0,
}


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
    frame = nw.from_native(data, eager_only=True)

    if (
        start_column is None
        and end_column is None
        and event_log_bindings_available(frame, process_model)
    ):
        assert process_model is not None
        # Event-log path (v0.3 migration in progress)
        raise NotImplementedError(
            "Event-log lead_time calculation is being refactored for v0.3. "
            "Use explicit start_column and end_column for now."
        )

    resolved_start_column, resolved_end_column = resolve_lead_time_columns(
        process_model=process_model,
        start_column=start_column,
        end_column=end_column,
    )
    require_columns(frame, resolved_start_column, resolved_end_column)

    start = frame[resolved_start_column].cast(nw.Datetime)
    end = frame[resolved_end_column].cast(nw.Datetime)

    # Calculate durations in seconds, convert to unit
    durations_native = (end - start).to_native()

    # Extract to NumPy
    if hasattr(durations_native, "dt"):
        # pandas Series
        durations_seconds = durations_native.dt.total_seconds().to_numpy()
    else:
        # Polars Series
        durations_seconds = durations_native.dt.total_seconds().to_numpy()

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
