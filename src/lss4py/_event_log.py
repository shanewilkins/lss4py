"""Internal event-log helper functions (v0.3 refactor pending).

This module contains pandas-based event-log processing utilities.
Will be refactored to use Narwhals in v0.3 for full backend neutrality.

Not part of the public API; subject to change.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

import narwhals as nw
import pandas as pd

from lss4py.domain import ProcessModelIR
from lss4py.errors import ValidationError
from lss4py.kernels._helpers import TimeUnit, to_unit

__all__ = []  # Not exported


def event_log_bindings_available(
    frame: nw.DataFrame,
    process_model: ProcessModelIR | None,
) -> bool:
    """Check if event-log bindings are present in frame and model."""
    if process_model is None:
        return False

    bindings = process_model.bindings.event_log
    required_columns = [
        bindings.case_id_column,
        bindings.step_id_column,
        bindings.started_at_column,
        bindings.completed_at_column,
    ]

    if any(column is None for column in required_columns):
        return False

    frame_columns = set(frame.columns)
    return all(cast(str, column) in frame_columns for column in required_columns)


def merge_intervals(
    intervals: Iterable[tuple[Any, Any]],
) -> list[tuple[Any, Any]]:  # pragma: no cover
    """Merge overlapping time intervals."""
    ordered_intervals = sorted(intervals, key=lambda interval: interval[0])
    if not ordered_intervals:
        return []

    merged_intervals = [ordered_intervals[0]]
    for start, end in ordered_intervals[1:]:
        current_start, current_end = merged_intervals[-1]
        if start <= current_end:
            merged_intervals[-1] = (current_start, max(current_end, end))
            continue

        merged_intervals.append((start, end))

    return merged_intervals


def sum_interval_seconds(intervals: Iterable[tuple[Any, Any]]) -> float:  # pragma: no cover
    """Sum durations of datetime intervals."""
    return sum((end - start).total_seconds() for start, end in intervals)


def step_lookup(process_model: ProcessModelIR) -> dict[str, object]:
    """Build a lookup table of process steps by ID."""
    return {step.id: step for step in process_model.steps}


def validate_known_event_log_step_ids(
    frame: nw.DataFrame,
    *,
    process_model: ProcessModelIR,
    step_id_column: str,
) -> None:  # pragma: no cover
    """Validate that observed step IDs are in process model."""
    known_step_ids = set(step_lookup(process_model))
    observed_step_ids = set(frame[step_id_column].cast(nw.String).unique().to_native().to_list())
    unknown_step_ids = sorted(observed_step_ids - known_step_ids)
    if unknown_step_ids:
        raise ValidationError(
            "Observed step ids are missing from process model "
            f"'{process_model.name}': {', '.join(unknown_step_ids)}"
        )


def validate_event_log_durations(
    frame: nw.DataFrame,
    *,
    started_at_column: str,
    completed_at_column: str,
) -> tuple[nw.Series, nw.Series]:  # pragma: no cover
    """Validate and extract start/end datetime columns."""
    started_at = frame[started_at_column].cast(nw.Datetime)
    completed_at = frame[completed_at_column].cast(nw.Datetime)

    # Check for negative durations
    durations = completed_at - started_at
    # Check if any duration is negative
    neg_count = (durations < nw.lit(0)).sum()
    if neg_count > 0:
        raise ValidationError("Event-log rows cannot have negative durations.")

    return started_at, completed_at


def case_repeated_steps(case_rows: pd.DataFrame) -> list[str]:
    """Identify steps that repeat in a case."""
    step_counts = case_rows.groupby("__step_id").size().to_dict()
    return sorted(str(step_id) for step_id, count in step_counts.items() if count > 1)


def validate_event_log_case_rework(
    case_rows: pd.DataFrame,
    *,
    process_model: ProcessModelIR,
    rework_targets: set[str],
) -> None:
    """Validate that repeated steps have explicit rework edges in process model."""
    for repeated_step in case_repeated_steps(case_rows):
        if repeated_step not in rework_targets:
            raise ValidationError(
                "Step "
                f"'{repeated_step}' repeats in observed data but process model "
                f"'{process_model.name}' does not define a rework edge to it."
            )


def validate_event_log_case_overlaps(
    case_rows: pd.DataFrame,
    *,
    parallel_edges_present: bool,
) -> None:
    """Validate that overlapping steps have explicit parallel edges in process model."""
    ordered_rows = case_rows.sort_values("__started_at")
    previous_end: pd.Timestamp | None = None
    ordered_intervals = zip(
        ordered_rows["__started_at"],
        ordered_rows["__completed_at"],
        strict=False,
    )
    for started_at_value, completed_at_value in ordered_intervals:
        if (
            previous_end is not None
            and started_at_value < previous_end
            and not parallel_edges_present
        ):
            raise ValidationError(
                "Observed overlapping step intervals require explicit parallel "
                "edges in the process model."
            )
        previous_end = (
            max(previous_end, completed_at_value)
            if previous_end is not None
            else completed_at_value
        )


def validate_event_log_rows(data: pd.DataFrame, process_model: ProcessModelIR) -> None:
    """Validate event-log rows against process model topology."""
    bindings = process_model.bindings.event_log
    case_id_column = cast(str, bindings.case_id_column)
    step_id_column = cast(str, bindings.step_id_column)
    started_at_column = cast(str, bindings.started_at_column)
    completed_at_column = cast(str, bindings.completed_at_column)

    required_columns = [case_id_column, step_id_column, started_at_column, completed_at_column]
    missing = [col for col in required_columns if col not in data.columns]
    if missing:
        raise ValidationError(f"Missing required event-log columns: {', '.join(missing)}")

    # Use Narwhals for validation
    frame = nw.from_native(data, eager_only=True)
    validate_known_event_log_step_ids(
        frame,
        process_model=process_model,
        step_id_column=step_id_column,
    )
    validate_event_log_durations(
        frame,
        started_at_column=started_at_column,
        completed_at_column=completed_at_column,
    )

    rework_targets = {edge.target_step_id for edge in process_model.edges if edge.kind == "rework"}
    parallel_edges_present = any(
        edge.kind in {"parallel_split", "parallel_join"} for edge in process_model.edges
    )

    typed_data = data.assign(
        __case_id=data[case_id_column].astype(str),
        __step_id=data[step_id_column].astype(str),
        __started_at=data[started_at_column],
        __completed_at=data[completed_at_column],
    )

    for _, case_rows in typed_data.groupby("__case_id", sort=False):
        validate_event_log_case_rework(
            case_rows,
            process_model=process_model,
            rework_targets=rework_targets,
        )
        validate_event_log_case_overlaps(
            case_rows,
            parallel_edges_present=parallel_edges_present,
        )


def event_log_case_series(
    data: pd.DataFrame,
    *,
    process_model: ProcessModelIR,
    include_step_ids: set[str] | None = None,
    unit: TimeUnit,
) -> pd.Series:
    """Aggregate event-log case durations using process model semantics."""
    bindings = process_model.bindings.event_log
    case_id_column = cast(str, bindings.case_id_column)
    step_id_column = cast(str, bindings.step_id_column)
    started_at_column = cast(str, bindings.started_at_column)
    completed_at_column = cast(str, bindings.completed_at_column)

    typed_data = data.assign(
        __case_id=data[case_id_column].astype(str),
        __step_id=data[step_id_column].astype(str),
        __started_at=pd.to_datetime(data[started_at_column], errors="raise"),
        __completed_at=pd.to_datetime(data[completed_at_column], errors="raise"),
    )

    metric_values: dict[str, float] = {}
    for case_id, case_rows in typed_data.groupby("__case_id", sort=False):
        relevant_rows = case_rows
        if include_step_ids is not None:
            relevant_rows = case_rows[case_rows["__step_id"].isin(list(include_step_ids))]

        intervals = list(
            zip(
                relevant_rows["__started_at"],
                relevant_rows["__completed_at"],
                strict=False,
            )
        )
        if not intervals:
            metric_values[str(case_id)] = 0.0
            continue

        if process_model.metric_semantics.parallel_timing == "sum_all_branches":
            total_seconds = sum_interval_seconds(intervals)
        else:
            merged_intervals = merge_intervals(intervals)
            total_seconds = sum_interval_seconds(merged_intervals)

        metric_values[str(case_id)] = to_unit(total_seconds, unit)

    return pd.Series(metric_values, name="event_log_metric", dtype=float)


def event_log_lead_time_series(
    data: pd.DataFrame,
    *,
    process_model: ProcessModelIR,
    unit: TimeUnit,
) -> pd.Series:
    """Calculate lead time (min start to max end) for each case in event log."""
    bindings = process_model.bindings.event_log
    case_id_column = cast(str, bindings.case_id_column)
    started_at_column = cast(str, bindings.started_at_column)
    completed_at_column = cast(str, bindings.completed_at_column)

    typed_data = data.assign(
        __case_id=data[case_id_column].astype(str),
        __started_at=pd.to_datetime(data[started_at_column], errors="raise"),
        __completed_at=pd.to_datetime(data[completed_at_column], errors="raise"),
    )

    metric_values: dict[str, float] = {}
    for case_id, case_rows in typed_data.groupby("__case_id", sort=False):
        total_seconds = (
            case_rows["__completed_at"].max() - case_rows["__started_at"].min()
        ).total_seconds()
        metric_values[str(case_id)] = to_unit(total_seconds, unit)

    return pd.Series(metric_values, name="lead_time", dtype=float)


def event_log_value_add_step_ids(process_model: ProcessModelIR) -> set[str]:
    """Extract step IDs marked as value-add in process model."""
    return {step.id for step in process_model.steps if step.value_classification == "value_add"}
