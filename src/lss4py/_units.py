"""Explicit duration conversion at an eager-table preparation boundary."""

from __future__ import annotations

import json
from collections.abc import Sequence
from functools import lru_cache
from importlib.metadata import version
from math import isfinite
from numbers import Integral, Real
from typing import TYPE_CHECKING, Any

import narwhals as nw

from lss4py._frames import detect_backend, eager_frame
from lss4py.domain.units import DurationConversion
from lss4py.errors import ValidationError

if TYPE_CHECKING:
    from pint import UnitRegistry

_ALIASES = {
    "s": "second",
    "sec": "second",
    "second": "second",
    "seconds": "second",
    "min": "minute",
    "minute": "minute",
    "minutes": "minute",
    "h": "hour",
    "hr": "hour",
    "hour": "hour",
    "hours": "hour",
}


@lru_cache(maxsize=1)
def _registry() -> UnitRegistry:
    """Lazily own a registry without touching Pint's application registry."""
    from pint import UnitRegistry

    return UnitRegistry()


def _unit(label: str) -> str:
    """Accept only unambiguous duration aliases in the declared pilot scope."""
    if not isinstance(label, str) or label not in _ALIASES:
        raise ValidationError("Unsupported duration unit; use seconds, minutes or hours.")
    return _ALIASES[label]


def _columns(columns: Sequence[str], names: list[str]) -> tuple[str, ...]:
    """Require explicit, unique column identities without selecting or dropping rows."""
    if isinstance(columns, str) or not isinstance(columns, (tuple, list)) or not columns:
        raise ValidationError("columns must be a nonempty list or tuple of duration column names.")
    if any(not isinstance(name, str) or name not in names for name in columns):
        raise ValidationError("Duration columns must reference existing column names.")
    if len(set(columns)) != len(columns):
        raise ValidationError("Duration column names must be unique.")
    return tuple(columns)


def _converted(values: list[Any], factor: float, column: str) -> list[float]:
    """Reject missing, nonnumeric and nonrepresentable durations before materialization."""
    result = []
    for row, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValidationError(
                f"{column}, row {row}: duration must be a finite nonnegative number."
            )
        try:
            magnitude = float(value)
            converted = magnitude * factor
        except (OverflowError, ValueError) as exc:
            raise ValidationError(f"{column}, row {row}: duration is not representable.") from exc
        if isinstance(value, Integral) and int(magnitude) != value:
            raise ValidationError(f"{column}, row {row}: duration loses integer precision.")
        if not isfinite(magnitude) or magnitude < 0 or not isfinite(converted):
            raise ValidationError(f"{column}, row {row}: duration must be finite and nonnegative.")
        if magnitude > 0 and converted == 0:
            raise ValidationError(f"{column}, row {row}: conversion underflows to zero.")
        result.append(converted)
    return result


def convert_duration_columns(
    data: Any,
    *,
    columns: Sequence[str],
    source_unit: str,
    target_unit: str,
    clock: str,
) -> DurationConversion:
    """Convert selected finite duration columns explicitly, preserving backend and rows.

    Args:
        data: Eager pandas/Polars frame or PyArrow Table; lazy inputs are not collected.
        columns: Nonempty list or tuple of distinct duration columns sharing the source unit.
        source_unit: Seconds, minutes or hours, including documented short aliases.
        target_unit: Explicit output duration unit in the same supported set.
        clock: Nonblank declaration of the unchanged measurement clock; never inferred.

    Returns:
        DurationConversion with native data and portable conversion/source-position evidence.

    Raises:
        ValidationError: Unsupported units, invalid columns or incomplete/nonfinite durations.
    """
    source, target = _unit(source_unit), _unit(target_unit)
    if not isinstance(clock, str) or not clock.strip():
        raise ValidationError("clock must explicitly declare the unchanged measurement clock.")
    frame = eager_frame(data)
    selected = _columns(columns, frame.columns)
    if not len(frame):
        raise ValidationError("Duration conversion requires at least one observation.")
    factor = float(_registry().Quantity(1.0, source).to(target).magnitude)
    replacements = [
        nw.new_series(
            name, _converted(frame[name].to_list(), factor, name), backend=frame.implementation
        )
        for name in selected
    ]
    result = frame.with_columns(*replacements)
    evidence = {
        "result_type": "DurationConversion",
        "schema_version": "1.0",
        "method_version": "1.0",
        "columns": list(selected),
        "source_unit": source_unit,
        "target_unit": target_unit,
        "canonical_source_unit": source,
        "canonical_target_unit": target,
        "factor": factor,
        "clock": clock,
        "calendar_conversion": "none",
        "row_count": len(frame),
        "source_rows": list(range(len(frame))),
        "backend": detect_backend(frame),
        "registry": "lss4py.private.duration.v1",
        "software_versions": {"pint": version("pint")},
    }
    return DurationConversion(result.to_native(), json.dumps(evidence, allow_nan=False, indent=2))
