"""Shared eager-frame identity without analytical or adapter dependencies."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

import narwhals as nw
import polars as pl
from narwhals.exceptions import DuplicateError

from lss4py.errors import UnsupportedInputError, ValidationError

Backend = Literal["pandas", "polars", "pyarrow", "unknown"]
LogicalSchema = tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class CanonicalFrame:
    """Selected Polars columns plus immutable source-boundary evidence."""

    _frame: pl.DataFrame
    source_backend: Backend
    source_schema: LogicalSchema
    source_row_count: int
    selected_columns: tuple[str, ...]
    source_positions: tuple[int, ...] | None
    execution_backend: Literal["polars"] = "polars"

    def to_polars(self, *, copy: bool = True) -> pl.DataFrame:
        """Return the canonical frame, copying by default for mutation isolation."""
        return self._frame.clone() if copy else self._frame


def detect_backend(frame: nw.DataFrame) -> Backend:
    """Identify supported native eager frame implementations without converting them."""
    native = type(frame.to_native())
    backends: dict[tuple[str, str], Backend] = {
        ("pandas", "DataFrame"): "pandas",
        ("polars", "DataFrame"): "polars",
        ("pyarrow", "Table"): "pyarrow",
    }
    for base in native.__mro__:
        if backend := backends.get((base.__module__.split(".")[0], base.__name__)):
            return backend
    return "unknown"


def eager_frame(data: Any) -> nw.DataFrame:
    """Reject unsupported/lazy inputs without collecting them or leaking backend exceptions."""
    try:
        frame = nw.from_native(data, eager_only=True)
    except DuplicateError as exc:
        raise ValidationError("Observed column names must be unique.") from exc
    except TypeError as exc:
        raise UnsupportedInputError(
            "Supply an eager pandas/Polars frame or PyArrow Table; lazy plans are not collected."
        ) from exc
    if detect_backend(frame) == "unknown":
        raise UnsupportedInputError("Supported eager backends are pandas, Polars and PyArrow.")
    if any(not isinstance(name, str) for name in frame.columns):
        raise ValidationError("Observed column names must be strings.")
    return frame


def canonical_frame(
    data: Any,
    columns: Iterable[str],
    *,
    retain_source_positions: bool = False,
) -> CanonicalFrame:
    """Materialize required eager columns as Polars while retaining source evidence."""
    frame = eager_frame(data)
    if isinstance(columns, str):
        raise ValidationError("Selected columns must be an iterable of column names.")
    if not isinstance(retain_source_positions, bool):
        raise ValidationError("retain_source_positions must be boolean.")
    requested = tuple(columns)
    if not requested:
        raise ValidationError("Canonicalization requires at least one selected column.")
    if any(not isinstance(name, str) for name in requested):
        raise ValidationError("Selected column names must be strings.")
    selected = tuple(dict.fromkeys(requested))
    missing = [name for name in selected if name not in frame.columns]
    if missing:
        raise ValidationError(f"Missing required columns: {', '.join(missing)}")
    source_backend = detect_backend(frame)
    canonical = _materialize_polars(frame.select(*selected), source_backend)
    row_count = len(frame)
    return CanonicalFrame(
        canonical,
        source_backend,
        tuple((name, str(dtype)) for name, dtype in frame.schema.items()),
        row_count,
        selected,
        tuple(range(row_count)) if retain_source_positions else None,
    )


def _materialize_polars(frame: nw.DataFrame, backend: Backend) -> pl.DataFrame:
    """Detach mutable pandas buffers before producing the selected Polars frame."""
    if backend == "pandas":
        native: Any = frame.to_native()
        frame = nw.from_native(native.copy(deep=True), eager_only=True)
    return frame.to_polars().clone()
