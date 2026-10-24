"""Shared helpers for private analytical kernels.

Internal utilities for column resolution, data validation, and provenance building.
Not part of the public API; subject to change between v0.2 releases.
"""

from __future__ import annotations

from typing import Any, Literal, cast

import narwhals as nw
import numpy as np

from lss4py._frames import detect_backend as detect_backend
from lss4py._kernels._contracts import input_context, schema_fingerprint
from lss4py._version import __version__
from lss4py.domain import AssumptionNote, ProcessModelIR, Provenance
from lss4py.errors import ValidationError

TimeUnit = Literal["seconds", "minutes", "hours", "days"]

_SECONDS_PER_UNIT: dict[TimeUnit, float] = {
    "seconds": 1.0,
    "minutes": 60.0,
    "hours": 3600.0,
    "days": 86400.0,
}


def build_provenance(
    method_name: str,
    frame: nw.DataFrame,
    parameters: dict[str, Any],
    assumptions: list | None = None,
    warnings: list | None = None,
) -> Provenance:
    """Build provenance metadata for an analytical kernel."""
    return Provenance(
        method=method_name,
        method_version="1.1",  # Explicit input domains and per-result audit context
        package_version=__version__,
        backend=detect_backend(frame),
        parameters=input_context(frame, parameters),
        input_schema_fingerprint=schema_fingerprint(frame),
        cohort_definition=parameters.get("cohort")
        or f"All {len(frame)} supplied source rows; no implicit cohort filter",
        assumptions=[
            AssumptionNote(
                code=a["code"],
                message=a["message"],
                severity=a.get("severity", "info"),
            )
            for a in (assumptions or [])
        ],
        warnings=[
            AssumptionNote(
                code=w["code"],
                message=w["message"],
                severity=w.get("severity", "warning"),
            )
            for w in (warnings or [])
        ],
    )


def to_unit(total_seconds: float, unit: TimeUnit) -> float:
    """Convert seconds to requested time unit."""
    return total_seconds / _SECONDS_PER_UNIT[unit]


def require_columns(frame: nw.DataFrame, *columns: str) -> None:
    """Validate that required columns exist in frame."""
    frame_columns = set(frame.columns)
    missing = [column for column in columns if column not in frame_columns]
    if missing:
        raise ValidationError(f"Missing required columns: {', '.join(missing)}")


def numeric_series(frame: nw.DataFrame, column: str) -> np.ndarray:
    """Extract numeric column as NumPy array."""
    values = measurement_values(frame, column)
    if not np.isfinite(values).all() or np.any(values < 0):
        raise ValidationError(f"Column '{column}' requires finite nonnegative measurements.")
    return values


def binary_stage_series(frame: nw.DataFrame, column: str) -> np.ndarray:
    """Validate exact binary measurements before integer conversion; never truncate."""
    require_columns(frame, column)
    series = frame[column]
    if series.dtype == nw.Boolean:
        if series.null_count():
            raise ValidationError(f"Column '{column}' contains missing stage values.")
        return np.asarray(series.to_numpy(), dtype=np.int64)
    values = measurement_values(frame, column)
    if not np.all(np.isin(values, [0, 1])):
        raise ValidationError(f"Column '{column}' contains non-binary values; expected 0 or 1.")
    return values.astype(np.int64)


def resolve_stage_column(
    *,
    process_model: ProcessModelIR | None,
    explicit_column: str | None,
    stage_name: str,
) -> str:
    """Resolve stage column from explicit argument or process model."""
    resolved_column = explicit_column
    if process_model is not None:
        stage_bindings = process_model.bindings.stages
        resolved_column = resolved_column or getattr(stage_bindings, stage_name)

    if resolved_column is None:
        raise ValidationError(
            f"Stage '{stage_name}' requires an explicit column or a matching process model mapping."
        )

    return resolved_column


def resolve_lead_time_columns(
    *,
    process_model: ProcessModelIR | None,
    start_column: str | None,
    end_column: str | None,
) -> tuple[str, str]:
    """Resolve lead-time start/end columns from explicit arguments or process model."""
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


def resolve_lead_time_series(
    frame: nw.DataFrame,
    *,
    process_model: ProcessModelIR | None,
    lead_time_column: str | None,
) -> np.ndarray:
    """Resolve lead-time series from explicit column (event-log deferred to v0.3)."""
    if lead_time_column is not None:
        return numeric_series(frame, lead_time_column)

    # Event-log path (v0.3)
    raise ValidationError(
        "Lead time requires an explicit lead_time_column. "
        "Event-log inference is being refactored for v0.3."
    )


def resolve_cycle_time_series(
    frame: nw.DataFrame,
    *,
    process_model: ProcessModelIR | None,
    cycle_time_column: str | None,
) -> np.ndarray:
    """Resolve cycle-time series from explicit column (event-log deferred to v0.3)."""
    if cycle_time_column is not None:
        return numeric_series(frame, cycle_time_column)

    # Event-log path (v0.3)
    raise ValidationError(
        "Cycle time requires an explicit cycle_time_column. "
        "Event-log inference is being refactored for v0.3."
    )


def resolve_value_add_time_series(
    frame: nw.DataFrame,
    *,
    process_model: ProcessModelIR | None,
    value_add_time_column: str | None,
) -> np.ndarray:
    """Resolve value-add time series from explicit column (event-log deferred to v0.3)."""
    if value_add_time_column is not None:
        return numeric_series(frame, value_add_time_column)

    # Event-log path (v0.3)
    raise ValidationError(
        "Value-add time requires an explicit value_add_time_column. "
        "Event-log inference is being refactored for v0.3."
    )


def stage_yield_components(
    frame: nw.DataFrame,
    *,
    from_column: str | None,
    to_column: str | None,
    from_stage_name: str,
    to_stage_name: str,
    process_model: ProcessModelIR | None,
) -> tuple[float, float, float]:
    """Calculate stage yield components: (yield_fraction, numerator, denominator).

    Returns yield as fraction (0-1), plus numerator (conversions) and denominator (opportunities).
    """
    resolved_from_column = resolve_stage_column(
        process_model=process_model,
        explicit_column=from_column,
        stage_name=from_stage_name,
    )
    resolved_to_column = resolve_stage_column(
        process_model=process_model,
        explicit_column=to_column,
        stage_name=to_stage_name,
    )

    from_stage = binary_stage_series(frame, resolved_from_column)
    to_stage = binary_stage_series(frame, resolved_to_column)

    if np.any(to_stage > from_stage):
        raise ValidationError(
            "Column "
            f"'{resolved_to_column}' cannot exceed column '{resolved_from_column}' "
            "for stage yield calculations."
        )

    opportunities = int(np.sum(from_stage))
    if opportunities <= 0:
        raise ValidationError(
            f"Column '{resolved_from_column}' must contain at least one stage opportunity."
        )

    conversions = int(np.sum(to_stage))
    yield_value = conversions / opportunities

    return yield_value, conversions, opportunities


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


def measurement_values(frame: nw.DataFrame, column: str) -> np.ndarray:
    """Extract only a numeric measurement column; never coerce text or booleans."""
    require_columns(frame, column)
    series = frame[column]
    if series.null_count() == len(series):
        return np.full(len(series), np.nan)
    if not series.dtype.is_numeric():
        raise ValidationError(f"Column '{column}' must contain numeric measurements.")
    values = np.asarray(series.cast(nw.Float64).to_numpy(), dtype=float)
    if np.isinf(values).any():
        raise ValidationError(f"Column '{column}' contains infinity; correct it before analysis.")
    return values
