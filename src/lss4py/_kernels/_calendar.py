"""Backend-independent ISO/native calendar instants at declared microsecond precision."""

from datetime import UTC, datetime

import narwhals as nw
import numpy as np

from lss4py.errors import ValidationError


def calendar_seconds(frame: nw.DataFrame, start_column: str, end_column: str) -> np.ndarray:
    """Calculate elapsed seconds on explicit ISO/native datetime pairs without guessing formats."""
    start = _instants(frame, start_column)
    end = _instants(frame, end_column)
    try:
        return np.asarray([(e - s).total_seconds() for s, e in zip(start, end, strict=True)])
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValidationError("Calendar endpoints require consistent timezone awareness.") from exc


def _instants(frame: nw.DataFrame, column: str) -> list[datetime]:
    """Reject numeric/missing endpoints and normalize aware instants to UTC."""
    series = frame[column]
    if series.dtype != nw.String and not isinstance(series.dtype, nw.Datetime):
        raise ValidationError(
            f"Column '{column}' contains invalid timestamps; numeric clocks need numeric contracts."
        )
    try:
        values = [_instant(value) for value in series.to_list()]
        _uniform_awareness(values)
        return values
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValidationError(f"Column '{column}' contains invalid timestamps.") from exc


def _instant(value) -> datetime:
    """Parse ISO/native instants at microsecond precision without timezone inference."""
    if isinstance(value, str):
        value = _parse_iso(value)
    if not isinstance(value, datetime):
        raise ValueError("Complete datetime endpoints are required")
    result = datetime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        tzinfo=value.tzinfo,
        fold=value.fold,
    )
    return result.astimezone(UTC) if result.tzinfo is not None else result


def _parse_iso(value: str) -> datetime:
    """Require both ISO date and time rather than interpreting a date as midnight."""
    if "T" not in value and " " not in value:
        raise ValueError("Both date and time are required")
    return datetime.fromisoformat(value)


def _uniform_awareness(values: list[datetime]) -> None:
    """Reject mixed naive/aware observations even if individual row pairs align."""
    if len({value.tzinfo is None for value in values}) > 1:
        raise ValueError("Mixed timezone awareness")
