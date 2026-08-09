from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, cast

import pandas as pd

from lss4py.domain import ProcessModelIR
from lss4py.errors import ValidationError

TimeUnit = Literal["seconds", "minutes", "hours", "days"]

_SECONDS_PER_UNIT: dict[TimeUnit, float] = {
    "seconds": 1.0,
    "minutes": 60.0,
    "hours": 3600.0,
    "days": 86400.0,
}


def _to_unit(total_seconds: float, unit: TimeUnit) -> float:
    return total_seconds / _SECONDS_PER_UNIT[unit]


def _event_log_bindings_available(data: pd.DataFrame, process_model: ProcessModelIR | None) -> bool:
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

    return all(cast(str, column) in data.columns for column in required_columns)


def _merge_intervals(
    intervals: Iterable[tuple[pd.Timestamp, pd.Timestamp]],
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
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


def _sum_interval_seconds(intervals: Iterable[tuple[pd.Timestamp, pd.Timestamp]]) -> float:
    return sum((end - start).total_seconds() for start, end in intervals)


def _step_lookup(process_model: ProcessModelIR) -> dict[str, object]:
    return {step.id: step for step in process_model.steps}


def _validate_known_event_log_step_ids(
    data: pd.DataFrame,
    *,
    process_model: ProcessModelIR,
    step_id_column: str,
) -> None:
    known_step_ids = set(_step_lookup(process_model))
    observed_step_ids = set(data[step_id_column].astype(str).unique().tolist())
    unknown_step_ids = sorted(observed_step_ids - known_step_ids)
    if unknown_step_ids:
        raise ValidationError(
            "Observed step ids are missing from process model "
            f"'{process_model.name}': {', '.join(unknown_step_ids)}"
        )


def _validate_event_log_durations(
    data: pd.DataFrame,
    *,
    started_at_column: str,
    completed_at_column: str,
) -> tuple[pd.Series, pd.Series]:
    started_at = pd.to_datetime(data[started_at_column], errors="raise")
    completed_at = pd.to_datetime(data[completed_at_column], errors="raise")
    if (completed_at < started_at).any():
        raise ValidationError("Event-log rows cannot have negative durations.")

    return started_at, completed_at


def _case_repeated_steps(case_rows: pd.DataFrame) -> list[str]:
    step_counts = case_rows.groupby("__step_id").size().to_dict()
    return sorted(str(step_id) for step_id, count in step_counts.items() if count > 1)


def _validate_event_log_case_rework(
    case_rows: pd.DataFrame,
    *,
    process_model: ProcessModelIR,
    rework_targets: set[str],
) -> None:
    for repeated_step in _case_repeated_steps(case_rows):
        if repeated_step not in rework_targets:
            raise ValidationError(
                "Step "
                f"'{repeated_step}' repeats in observed data but process model "
                f"'{process_model.name}' does not define a rework edge to it."
            )


def _validate_event_log_case_overlaps(
    case_rows: pd.DataFrame,
    *,
    parallel_edges_present: bool,
) -> None:
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


def _validate_event_log_rows(data: pd.DataFrame, process_model: ProcessModelIR) -> None:
    bindings = process_model.bindings.event_log
    case_id_column = cast(str, bindings.case_id_column)
    step_id_column = cast(str, bindings.step_id_column)
    started_at_column = cast(str, bindings.started_at_column)
    completed_at_column = cast(str, bindings.completed_at_column)
    _require_columns(data, case_id_column, step_id_column, started_at_column, completed_at_column)

    _validate_known_event_log_step_ids(
        data,
        process_model=process_model,
        step_id_column=step_id_column,
    )
    started_at, completed_at = _validate_event_log_durations(
        data,
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
        __started_at=started_at,
        __completed_at=completed_at,
    )

    for _, case_rows in typed_data.groupby("__case_id", sort=False):
        _validate_event_log_case_rework(
            case_rows,
            process_model=process_model,
            rework_targets=rework_targets,
        )
        _validate_event_log_case_overlaps(
            case_rows,
            parallel_edges_present=parallel_edges_present,
        )


def _event_log_case_series(
    data: pd.DataFrame,
    *,
    process_model: ProcessModelIR,
    include_step_ids: set[str] | None = None,
    unit: TimeUnit,
) -> pd.Series:
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
            total_seconds = _sum_interval_seconds(intervals)
        else:
            merged_intervals = _merge_intervals(intervals)
            total_seconds = _sum_interval_seconds(merged_intervals)

        metric_values[str(case_id)] = _to_unit(total_seconds, unit)

    return pd.Series(metric_values, name="event_log_metric", dtype=float)


def _event_log_lead_time_series(
    data: pd.DataFrame,
    *,
    process_model: ProcessModelIR,
    unit: TimeUnit,
) -> pd.Series:
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
        metric_values[str(case_id)] = _to_unit(total_seconds, unit)

    return pd.Series(metric_values, name="lead_time", dtype=float)


def _event_log_value_add_step_ids(process_model: ProcessModelIR) -> set[str]:
    return {step.id for step in process_model.steps if step.value_classification == "value_add"}


def _resolve_lead_time_columns(
    *,
    process_model: ProcessModelIR | None,
    start_column: str | None,
    end_column: str | None,
) -> tuple[str, str]:
    resolved_start_column = start_column
    resolved_end_column = end_column

    if process_model is not None:
        resolved_start_column = (
            resolved_start_column or process_model.bindings.lead_time.start_column
        )
        resolved_end_column = resolved_end_column or process_model.bindings.lead_time.end_column

    if resolved_start_column is None or resolved_end_column is None:
        raise ValidationError(
            "Lead time requires explicit start/end columns or a process model with "
            "lead_time_start_column and lead_time_end_column."
        )

    return resolved_start_column, resolved_end_column


def _sum_process_step_columns(
    data: pd.DataFrame,
    *,
    process_model: ProcessModelIR,
    value_classifications: set[str] | None = None,
) -> pd.Series:
    cycle_time_columns: list[str] = []

    for step in process_model.steps:
        if step.cycle_time_column is None:
            continue

        if (
            value_classifications is not None
            and step.value_classification not in value_classifications
        ):
            continue

        cycle_time_columns.append(step.cycle_time_column)

    if not cycle_time_columns:
        raise ValidationError(
            f"Process model '{process_model.name}' does not define the required cycle-time columns."
        )

    total = pd.Series(0.0, index=data.index)
    for column in cycle_time_columns:
        total = total + _numeric_series(data, column)

    return total


def _resolve_stage_column(
    *,
    process_model: ProcessModelIR | None,
    explicit_column: str | None,
    stage_name: str,
) -> str:
    resolved_column = explicit_column
    if process_model is not None:
        stage_bindings = process_model.bindings.stages
        resolved_column = resolved_column or getattr(stage_bindings, stage_name)

    if resolved_column is None:
        raise ValidationError(
            f"Stage '{stage_name}' requires an explicit column or a matching process model mapping."
        )

    return resolved_column


def _resolve_lead_time_series(
    data: pd.DataFrame,
    *,
    process_model: ProcessModelIR | None,
    lead_time_column: str | None,
) -> pd.Series:
    if lead_time_column is not None:
        return _numeric_series(data, lead_time_column)

    if _event_log_bindings_available(data, process_model):
        assert process_model is not None
        unit = process_model.bindings.lead_time.unit
        return _event_log_lead_time_series(data, process_model=process_model, unit=unit)

    return lead_time(data, process_model=process_model)


def _resolve_cycle_time_series(
    data: pd.DataFrame,
    *,
    process_model: ProcessModelIR | None,
    cycle_time_column: str | None,
) -> pd.Series:
    if cycle_time_column is not None:
        return _numeric_series(data, cycle_time_column)

    if _event_log_bindings_available(data, process_model):
        assert process_model is not None
        unit = process_model.bindings.lead_time.unit
        return _event_log_case_series(data, process_model=process_model, unit=unit)

    if process_model is None:
        raise ValidationError(
            "Wait time requires an explicit cycle-time column or a process model "
            "with step cycle-time columns."
        )

    return _sum_process_step_columns(data, process_model=process_model)


def _resolve_value_add_time_series(
    data: pd.DataFrame,
    *,
    process_model: ProcessModelIR | None,
    value_add_time_column: str | None,
) -> pd.Series:
    if value_add_time_column is not None:
        return _numeric_series(data, value_add_time_column)

    if _event_log_bindings_available(data, process_model):
        assert process_model is not None
        unit = process_model.bindings.lead_time.unit
        value_add_step_ids = _event_log_value_add_step_ids(process_model)
        if not value_add_step_ids:
            raise ValidationError(
                f"Process model '{process_model.name}' does not define any value-add steps."
            )
        return _event_log_case_series(
            data,
            process_model=process_model,
            include_step_ids=value_add_step_ids,
            unit=unit,
        )

    if process_model is None:
        raise ValidationError(
            "Process cycle efficiency requires an explicit value-add time column "
            "or a process model "
            "with value-add step cycle-time columns."
        )

    return _sum_process_step_columns(
        data,
        process_model=process_model,
        value_classifications={"value_add"},
    )


def _require_columns(data: pd.DataFrame, *columns: str) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValidationError(f"Missing required columns: {', '.join(missing)}")


def _numeric_series(data: pd.DataFrame, column: str) -> pd.Series:
    _require_columns(data, column)

    try:
        numeric_values = pd.to_numeric(data[column], errors="raise")
        return cast(pd.Series, numeric_values)
    except Exception as exc:  # pragma: no cover - pandas error detail is environment-specific
        raise ValidationError(f"Column '{column}' must contain numeric values.") from exc


def _binary_stage_series(data: pd.DataFrame, column: str) -> pd.Series:
    series = _numeric_series(data, column)
    non_null_values = set(series.dropna().tolist())
    allowed_values = {0, 1}

    if not non_null_values.issubset(allowed_values):
        raise ValidationError(f"Column '{column}' must contain only binary stage values (0/1).")

    return series.astype(int)


def _stage_yield(
    data: pd.DataFrame,
    *,
    from_column: str | None,
    to_column: str | None,
    from_stage_name: str,
    to_stage_name: str,
    process_model: ProcessModelIR | None,
    as_percentage: bool,
) -> float:
    resolved_from_column = _resolve_stage_column(
        process_model=process_model,
        explicit_column=from_column,
        stage_name=from_stage_name,
    )
    resolved_to_column = _resolve_stage_column(
        process_model=process_model,
        explicit_column=to_column,
        stage_name=to_stage_name,
    )

    from_stage = _binary_stage_series(data, resolved_from_column)
    to_stage = _binary_stage_series(data, resolved_to_column)

    if (to_stage > from_stage).any():
        raise ValidationError(
            "Column "
            f"'{resolved_to_column}' cannot exceed column '{resolved_from_column}' "
            "for stage yield calculations."
        )

    opportunities = int(from_stage.sum())
    if opportunities <= 0:
        raise ValidationError(
            f"Column '{resolved_from_column}' must contain at least one stage opportunity."
        )

    conversions = int(to_stage.sum())
    result = conversions / opportunities
    if as_percentage:
        result *= 100.0

    return result


def lead_time(
    data: pd.DataFrame,
    *,
    start_column: str | None = None,
    end_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    unit: TimeUnit = "hours",
) -> pd.Series:
    if (
        start_column is None
        and end_column is None
        and _event_log_bindings_available(data, process_model)
    ):
        assert process_model is not None
        _validate_event_log_rows(data, process_model)
        return _event_log_lead_time_series(
            data,
            process_model=process_model,
            unit=process_model.bindings.lead_time.unit,
        )

    resolved_start_column, resolved_end_column = _resolve_lead_time_columns(
        process_model=process_model,
        start_column=start_column,
        end_column=end_column,
    )
    _require_columns(data, resolved_start_column, resolved_end_column)

    try:
        start = pd.to_datetime(data[resolved_start_column], errors="raise")
        end = pd.to_datetime(data[resolved_end_column], errors="raise")
    except Exception as exc:  # pragma: no cover - pandas error detail is environment-specific
        raise ValidationError("Lead time requires parseable start and end timestamps.") from exc

    durations = (end - start).dt.total_seconds() / _SECONDS_PER_UNIT[unit]
    if (durations < 0).any():
        raise ValidationError("Lead time cannot be negative.")

    return durations.rename("lead_time")


def wait_time(
    data: pd.DataFrame,
    *,
    lead_time_column: str | None = None,
    cycle_time_column: str | None = None,
    process_model: ProcessModelIR | None = None,
) -> pd.Series:
    if (
        lead_time_column is None
        and cycle_time_column is None
        and _event_log_bindings_available(data, process_model)
    ):
        assert process_model is not None
        _validate_event_log_rows(data, process_model)

    lead = _resolve_lead_time_series(
        data,
        process_model=process_model,
        lead_time_column=lead_time_column,
    )
    cycle = _resolve_cycle_time_series(
        data,
        process_model=process_model,
        cycle_time_column=cycle_time_column,
    )

    waits = lead - cycle
    if (waits < 0).any():
        raise ValidationError("Wait time cannot be negative. Check lead and cycle time inputs.")

    return waits.rename("wait_time")


def process_cycle_efficiency(
    data: pd.DataFrame,
    *,
    lead_time_column: str | None = None,
    value_add_time_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    as_percentage: bool = True,
) -> pd.Series:
    if (
        lead_time_column is None
        and value_add_time_column is None
        and _event_log_bindings_available(data, process_model)
    ):
        assert process_model is not None
        _validate_event_log_rows(data, process_model)

    lead = _resolve_lead_time_series(
        data,
        process_model=process_model,
        lead_time_column=lead_time_column,
    )
    value_add = _resolve_value_add_time_series(
        data,
        process_model=process_model,
        value_add_time_column=value_add_time_column,
    )

    if (lead <= 0).any():
        raise ValidationError("Lead time must be greater than zero for process cycle efficiency.")

    if (value_add < 0).any() or (value_add > lead).any():
        raise ValidationError("Value-add time must be between zero and lead time.")

    efficiency = value_add / lead
    if as_percentage:
        efficiency = efficiency * 100.0

    return efficiency.rename("process_cycle_efficiency")


def takt_time(*, available_time: float, customer_demand: float) -> float:
    if available_time <= 0:
        raise ValidationError("Available time must be greater than zero.")

    if customer_demand <= 0:
        raise ValidationError("Customer demand must be greater than zero.")

    return available_time / customer_demand


def created_to_booked_yield(
    data: pd.DataFrame,
    *,
    created_column: str | None = None,
    booked_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    as_percentage: bool = True,
) -> float:
    return _stage_yield(
        data,
        from_column=created_column,
        to_column=booked_column,
        from_stage_name="created",
        to_stage_name="booked",
        process_model=process_model,
        as_percentage=as_percentage,
    )


def booked_to_completed_yield(
    data: pd.DataFrame,
    *,
    booked_column: str | None = None,
    completed_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    as_percentage: bool = True,
) -> float:
    return _stage_yield(
        data,
        from_column=booked_column,
        to_column=completed_column,
        from_stage_name="booked",
        to_stage_name="completed",
        process_model=process_model,
        as_percentage=as_percentage,
    )


def rolled_yield(
    data: pd.DataFrame,
    *,
    created_column: str | None = None,
    booked_column: str | None = None,
    completed_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    as_percentage: bool = True,
) -> float:
    created_to_booked = created_to_booked_yield(
        data,
        created_column=created_column,
        booked_column=booked_column,
        process_model=process_model,
        as_percentage=False,
    )
    booked_to_completed = booked_to_completed_yield(
        data,
        booked_column=booked_column,
        completed_column=completed_column,
        process_model=process_model,
        as_percentage=False,
    )

    result = created_to_booked * booked_to_completed
    if as_percentage:
        result *= 100.0

    return result
