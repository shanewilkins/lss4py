"""Internal normalization and aggregation for interval event logs."""

from __future__ import annotations

from typing import Any, cast

import narwhals as nw
import numpy as np
import polars as pl

from lss4py.domain import EventLogBindingsIR, IntervalEventLog, ProcessModelIR
from lss4py.errors import ValidationError

CANONICAL_EVENT_LOG_COLUMNS = (
    "case_id",
    "step_id",
    "started_at",
    "completed_at",
)
CANONICAL_EVENT_LOG_BINDINGS = EventLogBindingsIR(
    case_id_column="case_id",
    step_id_column="step_id",
    started_at_column="started_at",
    completed_at_column="completed_at",
)

_CASE_ID = "__lss4py_case_id"
_STEP_ID = "__lss4py_step_id"
_STARTED_AT = "__lss4py_started_at"
_COMPLETED_AT = "__lss4py_completed_at"

__all__: list[str] = []


def _required_binding_columns(bindings: EventLogBindingsIR) -> tuple[str, str, str, str]:
    """Return complete interval-event bindings or fail with a clear message."""
    values = (
        bindings.case_id_column,
        bindings.step_id_column,
        bindings.started_at_column,
        bindings.completed_at_column,
    )
    if any(value is None for value in values):
        raise ValidationError(
            "Interval event logs require case_id, step_id, started_at, and completed_at bindings."
        )
    return cast(tuple[str, str, str, str], values)


def event_log_bindings_available(
    frame: nw.DataFrame,
    process_model: ProcessModelIR | None,
) -> bool:
    """Return whether a process model supplies complete bindings present in a frame."""
    if process_model is None:
        return False

    try:
        required = _required_binding_columns(process_model.bindings.event_log)
    except ValidationError:
        return False
    return all(column in frame.columns for column in required)


def _datetime_expression(frame: pl.DataFrame, column: str, alias: str) -> pl.Expr:
    """Build a strict datetime conversion expression for one source column."""
    dtype = frame.schema[column]
    expression = pl.col(column)
    if dtype == pl.String:
        expression = expression.str.to_datetime(strict=True)
    elif dtype == pl.Date:
        expression = expression.cast(pl.Datetime)
    elif not isinstance(dtype, pl.Datetime):
        expression = expression.cast(pl.Datetime, strict=True)
    return expression.alias(alias)


def _validate_required_values(frame: pl.DataFrame) -> None:
    """Reject missing or blank identifiers and missing timestamps."""
    missing_counts = frame.select(
        pl.col(_CASE_ID).is_null().sum().alias(_CASE_ID),
        pl.col(_STEP_ID).is_null().sum().alias(_STEP_ID),
        pl.col(_STARTED_AT).is_null().sum().alias(_STARTED_AT),
        pl.col(_COMPLETED_AT).is_null().sum().alias(_COMPLETED_AT),
    ).row(0, named=True)
    missing = [name for name, count in missing_counts.items() if count]
    if missing:
        raise ValidationError(
            "Interval event-log fields cannot contain null values: " + ", ".join(missing)
        )

    blank_identifiers = frame.select(
        (
            pl.col(_CASE_ID).str.strip_chars().eq("") | pl.col(_STEP_ID).str.strip_chars().eq("")
        ).any()
    ).item()
    if blank_identifiers:
        raise ValidationError("Event-log case and step identifiers cannot be blank.")


def _validate_known_steps(frame: pl.DataFrame, process_model: ProcessModelIR) -> None:
    """Reject observed step IDs not declared by a non-empty process model."""
    known = {step.id for step in process_model.steps}
    if not known:
        return
    observed = set(frame.get_column(_STEP_ID).unique().to_list())
    unknown = sorted(observed - known)
    if unknown:
        raise ValidationError(
            "Observed step ids are missing from process model "
            f"'{process_model.name}': {', '.join(unknown)}"
        )


def _validate_rework(frame: pl.DataFrame, process_model: ProcessModelIR) -> None:
    """Require an explicit rework edge for repeated steps within a case."""
    repeated = (
        frame.group_by(_CASE_ID, _STEP_ID)
        .len()
        .filter(pl.col("len") > 1)
        .get_column(_STEP_ID)
        .unique()
        .to_list()
    )
    rework_targets = {edge.target_step_id for edge in process_model.edges if edge.kind == "rework"}
    unmodeled = sorted(set(repeated) - rework_targets)
    if unmodeled:
        raise ValidationError(
            "Observed repeated steps require explicit rework edges in process model "
            f"'{process_model.name}': {', '.join(unmodeled)}"
        )


def _validate_overlaps(frame: pl.DataFrame, process_model: ProcessModelIR) -> None:
    """Require explicit parallel topology when intervals overlap within a case."""
    if any(edge.kind in {"parallel_split", "parallel_join"} for edge in process_model.edges):
        return

    ordered = frame.sort(_CASE_ID, _STARTED_AT, _COMPLETED_AT).with_columns(
        pl.col(_COMPLETED_AT).cum_max().shift(1).over(_CASE_ID).alias("__lss4py_previous_end")
    )
    overlap_exists = ordered.select(
        (pl.col(_STARTED_AT) < pl.col("__lss4py_previous_end")).fill_null(False).any()
    ).item()
    if overlap_exists:
        raise ValidationError(
            "Observed overlapping step intervals require explicit parallel edges "
            f"in process model '{process_model.name}'."
        )


def _to_polars(data: Any) -> pl.DataFrame:
    """Materialize a supported eager interval input as Polars."""
    try:
        native_input = data.to_polars(copy=False) if isinstance(data, IntervalEventLog) else data
        portable_frame = nw.from_native(native_input, eager_only=True)
        native_frame = portable_frame.to_native()
        if isinstance(native_frame, pl.DataFrame):
            return native_frame
        return pl.DataFrame(portable_frame.to_dict(as_series=False), strict=False)
    except Exception as exc:
        raise ValidationError(
            "Interval event-log data must be an eager pandas, Polars, or PyArrow frame."
        ) from exc


def normalize_interval_event_log(
    data: Any,
    *,
    bindings: EventLogBindingsIR,
    process_model: ProcessModelIR | None = None,
) -> pl.DataFrame:
    """Normalize eager dataframe input to a validated Polars interval-event frame."""
    frame = _to_polars(data)

    case_column, step_column, start_column, end_column = _required_binding_columns(bindings)
    required = (case_column, step_column, start_column, end_column)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValidationError("Missing required event-log columns: " + ", ".join(missing))
    if frame.is_empty():
        raise ValidationError("Interval event log contains zero rows.")

    try:
        normalized = frame.with_columns(
            pl.col(case_column).cast(pl.String, strict=True).alias(_CASE_ID),
            pl.col(step_column).cast(pl.String, strict=True).alias(_STEP_ID),
            _datetime_expression(frame, start_column, _STARTED_AT),
            _datetime_expression(frame, end_column, _COMPLETED_AT),
        )
    except pl.exceptions.PolarsError as exc:
        raise ValidationError(f"Could not normalize interval event-log values: {exc}") from exc

    _validate_required_values(normalized)
    negative_duration = normalized.select(
        (pl.col(_COMPLETED_AT) < pl.col(_STARTED_AT)).any()
    ).item()
    if negative_duration:
        raise ValidationError("Event-log rows cannot have negative durations.")

    if process_model is not None:
        _validate_known_steps(normalized, process_model)
        _validate_rework(normalized, process_model)
        _validate_overlaps(normalized, process_model)

    return normalized.with_columns(
        pl.col(_CASE_ID).alias(case_column),
        pl.col(_STEP_ID).alias(step_column),
        pl.col(_STARTED_AT).alias(start_column),
        pl.col(_COMPLETED_AT).alias(end_column),
    ).drop(_CASE_ID, _STEP_ID, _STARTED_AT, _COMPLETED_AT)


def event_log_lead_time(
    data: Any,
    *,
    process_model: ProcessModelIR,
    seconds_per_unit: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate per-case elapsed time and keys from an interval event log."""
    bindings = process_model.bindings.event_log
    case_column, _, start_column, end_column = _required_binding_columns(bindings)
    frame = normalize_interval_event_log(
        data,
        bindings=bindings,
        process_model=process_model,
    )
    summary = frame.group_by(case_column, maintain_order=True).agg(
        pl.col(start_column).min().alias("__lss4py_case_start"),
        pl.col(end_column).max().alias("__lss4py_case_end"),
    )
    values = (
        summary.select(
            (pl.col("__lss4py_case_end") - pl.col("__lss4py_case_start"))
            .dt.total_seconds()
            .cast(pl.Float64)
            / seconds_per_unit
        )
        .to_series()
        .to_numpy()
    )
    keys = summary.get_column(case_column).to_numpy()
    return keys, values
