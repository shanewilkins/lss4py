"""Shared helpers for private analytical kernels.

Internal utilities for column resolution, data validation, and provenance building.
Not part of the public API; subject to change between v0.2 releases.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any, Literal, cast

from lss4py._frames import CanonicalFrame
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
    frame: CanonicalFrame,
    parameters: dict[str, Any],
    assumptions: list | None = None,
    warnings: list | None = None,
) -> Provenance:
    """Build provenance metadata for an analytical kernel."""
    return Provenance(
        method=method_name,
        method_version="1.1",  # Explicit input domains and per-result audit context
        package_version=__version__,
        backend=frame.source_backend,
        parameters=input_context(frame, parameters),
        input_schema_fingerprint=schema_fingerprint(frame),
        cohort_definition=parameters.get("cohort")
        or (f"All {frame.source_row_count} supplied source rows; no implicit cohort filter"),
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


def event_log_bindings_available(
    columns: Collection[str],
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

    frame_columns = set(columns)
    return all(cast(str, column) in frame_columns for column in required_columns)
