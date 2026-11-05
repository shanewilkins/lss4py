"""Shared Polars extraction primitives for analytical kernels."""

from __future__ import annotations

from collections.abc import Callable
from math import isfinite, isnan
from typing import Any

import numpy as np
import polars as pl

from lss4py.errors import ValidationError


def require_columns(frame: pl.DataFrame, *columns: str) -> None:
    """Require named columns without backend-specific lookup failures."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValidationError(f"Missing required columns: {', '.join(missing)}")


def missing_mask(series: pl.Series) -> np.ndarray:
    """Return one boolean per null or floating NaN observation."""
    if series.dtype == pl.Object:
        return np.fromiter(
            (_missing(value) for value in series.to_list()),
            dtype=np.bool_,
            count=len(series),
        )
    missing = series.is_null()
    if series.dtype.is_float():
        missing = missing | series.is_nan()
    return np.asarray(missing.to_numpy(), dtype=np.bool_)


def measurement_values(frame: pl.DataFrame, column: str) -> np.ndarray:
    """Extract nullable numeric measurements as float without coercing domains."""
    require_columns(frame, column)
    series = frame[column]
    if series.dtype == pl.Null or series.null_count() == len(series):
        return np.full(len(series), np.nan)
    if not series.dtype.is_numeric():
        raise ValidationError(f"Column '{column}' must contain numeric measurements.")
    values = np.asarray(series.cast(pl.Float64).to_numpy(), dtype=float)
    if np.isinf(values).any():
        raise ValidationError(f"Column '{column}' contains infinity; correct it before analysis.")
    return values


def nonnegative_measurements(frame: pl.DataFrame, column: str) -> np.ndarray:
    """Require complete finite nonnegative measurements."""
    values = measurement_values(frame, column)
    if not np.isfinite(values).all() or np.any(values < 0):
        raise ValidationError(f"Column '{column}' requires finite nonnegative measurements.")
    return values


def binary_stage_values(frame: pl.DataFrame, column: str) -> np.ndarray:
    """Extract complete exact boolean or numeric 0/1 stage observations."""
    require_columns(frame, column)
    series = frame[column]
    if series.dtype == pl.Boolean:
        if series.null_count():
            raise ValidationError(f"Column '{column}' contains missing stage values.")
        return np.asarray(series.cast(pl.Int64).to_numpy(), dtype=np.int64)
    values = measurement_values(frame, column)
    if not np.all(np.isin(values, [0, 1])):
        raise ValidationError(f"Column '{column}' contains non-binary values; expected 0 or 1.")
    return values.astype(np.int64)


def source_positions(
    frame: pl.DataFrame,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    """Return zero-based source positions, optionally retaining a boolean selection."""
    positions = np.arange(frame.height, dtype=np.int64)
    if mask is None:
        return positions
    selected = np.asarray(mask)
    if selected.dtype != np.bool_ or selected.ndim != 1 or len(selected) != frame.height:
        raise ValidationError("Source-position masks must be one-dimensional boolean arrays.")
    return positions[selected]


def portable_key_values(
    frame: pl.DataFrame,
    key_column: str | None,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    """Preserve unique portable scalar keys or explicit source positions."""
    metadata = {
        "row_positions": source_positions(frame).tolist(),
        "key_column": key_column,
    }
    if key_column is None:
        return None, metadata
    require_columns(frame, key_column)
    values = frame[key_column].to_list()
    for value in values:
        _portable_key(value)
    identities = [(type(value).__name__, value) for value in values]
    if len(set(identities)) != len(identities):
        raise ValidationError("Explicit row keys must be unique; duplicate keys were supplied.")
    return np.asarray(values, dtype=object), metadata


def first_observed_groups(
    frame: pl.DataFrame,
    columns: tuple[str, ...],
    normalize: Callable[[Any], Any],
) -> list[tuple[dict[str, Any], tuple[int, ...]]]:
    """Partition rows by normalized keys in stable first-observed order."""
    require_columns(frame, *columns)
    groups: dict[tuple[Any, ...], list[int]] = {}
    masks = {column: missing_mask(frame[column]) for column in columns}
    for row in range(frame.height):
        key = tuple(
            normalize(None if masks[column][row] else frame[column][row]) for column in columns
        )
        groups.setdefault(key, []).append(row)
    return [(dict(zip(columns, key, strict=True)), tuple(rows)) for key, rows in groups.items()]


def _missing(value: Any) -> bool:
    return value is None or isinstance(value, float) and isnan(value)


def _portable_key(value: Any) -> None:
    if isinstance(value, str) and value.strip():
        return
    if isinstance(value, (bool, int)):
        return
    if isinstance(value, float) and isfinite(value):
        return
    raise ValidationError("Explicit row keys must be nonblank strings or finite scalar numbers.")
