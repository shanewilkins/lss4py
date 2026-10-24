"""Shared eager-frame identity without analytical or adapter dependencies."""

from typing import Literal

import narwhals as nw
from narwhals.exceptions import DuplicateError

from lss4py.errors import UnsupportedInputError, ValidationError

Backend = Literal["pandas", "polars", "pyarrow", "unknown"]


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


def eager_frame(data) -> nw.DataFrame:
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
