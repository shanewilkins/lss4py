"""Validated, immutable CTQ contracts independent of dataframe libraries."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from numbers import Real
from typing import Any, Literal, Self

from lss4py.errors import ValidationError


def _text(name: str, value: Any, *, optional: bool = False) -> None:
    """Require nonblank text without altering caller-supplied labels."""
    if value is None and optional:
        return
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be nonblank text.")


def _number(name: str, value: Any) -> float | None:
    """Normalize optional finite real measurements, rejecting booleans and strings."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(f"{name} must be a finite real number.")
    try:
        normalized = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValidationError(f"{name} must be a finite real number.") from exc
    if not math.isfinite(normalized):
        raise ValidationError(f"{name} must be a finite real number.")
    return normalized


def _payload(data: Any, model: type[AnalysisWindow] | type[Specification]) -> dict[str, Any]:
    """Reject unknown schema fields, including accidental control-limit fields."""
    if not isinstance(data, Mapping):
        raise ValidationError("Serialized model must be an object.")
    unknown = set(data) - {item.name for item in fields(model)}
    if unknown:
        raise ValidationError(f"Unknown fields: {', '.join(sorted(map(str, unknown)))}")
    return dict(data)


def _json_object(value: str) -> dict[str, Any]:
    """Parse JSON with consistent domain errors instead of parser exceptions."""
    try:
        result = json.loads(value)
    except (ValueError, TypeError) as exc:
        raise ValidationError("Invalid JSON model.") from exc
    if not isinstance(result, dict):
        raise ValidationError("Serialized model must be an object.")
    return result


@dataclass(frozen=True, slots=True)
class AnalysisWindow:
    """Declared half-open observation window [start, end), allowing an open endpoint.

    At least one endpoint is required. Both endpoints must be datetimes with
    compatible timezone awareness. Naive datetimes are allowed but carry no implied
    timezone. This model never filters observations or infers a timestamp column.
    """

    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(self) -> None:
        """Validate datetime types, awareness, and temporal ordering."""
        if self.start is None and self.end is None:
            raise ValidationError("An analysis window requires start or end.")
        for name in ("start", "end"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, datetime):
                raise ValidationError(f"Window {name} must be a datetime.")
        self._validate_order()

    def _validate_order(self) -> None:
        """Compare endpoints only after verifying compatible timezone awareness."""
        if self.start is None or self.end is None:
            return
        if (self.start.utcoffset() is None) != (self.end.utcoffset() is None):
            raise ValidationError("Window endpoints must have compatible timezone awareness.")
        if self.start >= self.end:
            raise ValidationError("Window start must be earlier than end.")

    def to_dict(self) -> dict[str, str | None]:
        """Serialize endpoints as ISO 8601 strings, preserving timezone offsets."""
        return {
            "start": self.start.isoformat() if self.start is not None else None,
            "end": self.end.isoformat() if self.end is not None else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a declared window from ISO endpoints and validate it."""
        payload = _payload(data, cls)
        try:
            endpoints = {
                name: datetime.fromisoformat(value) if value is not None else None
                for name, value in payload.items()
            }
        except (ValueError, TypeError) as exc:
            raise ValidationError("Window endpoints must be ISO datetime strings.") from exc
        return cls(**endpoints)


@dataclass(frozen=True, slots=True)
class Specification:
    """Reusable CTQ definition and acceptance specifications (UR-018 / TR-021).

    Limits are inclusive specification boundaries, never statistical control
    limits. All numeric values share the declared unit; no conversion is inferred.
    Targetless and limitless definitions are allowed for higher/lower directions.
    The target direction requires an explicit target. Definitions, grouping,
    cohort, and time window capture intent without executing analytical policy.
    """

    name: str
    unit: str
    direction: Literal["lower", "higher", "target"]
    target: float | None = None
    lsl: float | None = None
    usl: float | None = None
    defect_definition: str | None = None
    opportunity_definition: str | None = None
    opportunities_per_unit: int | None = None
    group_by: tuple[str, ...] = ()
    cohort: str | None = None
    time_window: AnalysisWindow | None = None
    decision_context: str | None = None
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        """Validate and normalize the complete declaration on construction."""
        _text("name", self.name)
        _text("unit", self.unit)
        for name in ("defect_definition", "opportunity_definition", "cohort", "decision_context"):
            _text(name, getattr(self, name), optional=True)
        for name in ("target", "lsl", "usl"):
            object.__setattr__(self, name, _number(name, getattr(self, name)))
        self._validate_limits()
        self._validate_opportunities()
        self._normalize_groups()
        self._validate_context()

    def _validate_limits(self) -> None:
        """Reject contradictory acceptance bounds and out-of-bounds targets."""
        if self.direction not in ("lower", "higher", "target"):
            raise ValidationError("direction must be 'lower', 'higher', or 'target'.")
        if self.direction == "target" and self.target is None:
            raise ValidationError("The target direction requires a target value.")
        if self.lsl is not None and self.usl is not None and self.lsl >= self.usl:
            raise ValidationError("lsl must be strictly less than usl.")
        self._validate_target()

    def _validate_target(self) -> None:
        """Keep an optional nominal target inside declared specification boundaries."""
        if self.target is None:
            return
        if self.lsl is not None and self.target < self.lsl:
            raise ValidationError("target must not be below lsl.")
        if self.usl is not None and self.target > self.usl:
            raise ValidationError("target must not be above usl.")

    def _validate_opportunities(self) -> None:
        """Require an explicit opportunity definition for a fixed per-unit count."""
        count = self.opportunities_per_unit
        if count is None:
            return
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValidationError("opportunities_per_unit must be a positive integer.")
        if self.opportunity_definition is None:
            raise ValidationError("opportunities_per_unit requires an opportunity_definition.")

    def _normalize_groups(self) -> None:
        """Copy grouping labels into an immutable tuple, rejecting duplicate columns."""
        if not isinstance(self.group_by, (tuple, list)):
            raise ValidationError("group_by must be a tuple or list of column names.")
        for column in self.group_by:
            _text("group_by column", column)
        if len(set(self.group_by)) != len(self.group_by):
            raise ValidationError("group_by columns must be unique.")
        object.__setattr__(self, "group_by", tuple(self.group_by))

    def _validate_context(self) -> None:
        """Validate the schema version and optional typed observation window."""
        if self.schema_version != "1.0":
            raise ValidationError(
                f"Unsupported specification schema version: {self.schema_version}"
            )
        if self.time_window is not None and not isinstance(self.time_window, AnalysisWindow):
            raise ValidationError("time_window must be an AnalysisWindow.")

    def to_dict(self) -> dict[str, Any]:
        """Export a versioned, JSON-compatible specification without backend objects."""
        payload = asdict(self)
        payload["group_by"] = list(self.group_by)
        payload["time_window"] = self.time_window.to_dict() if self.time_window else None
        return payload

    def to_json(self) -> str:
        """Export strict JSON, disallowing nonfinite numeric values."""
        return json.dumps(self.to_dict(), allow_nan=False, indent=2)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore and revalidate a specification; never silently accept unknown fields."""
        payload = _payload(data, cls)
        if payload.get("time_window") is not None:
            payload["time_window"] = AnalysisWindow.from_dict(payload["time_window"])
        try:
            return cls(**payload)
        except TypeError as exc:
            raise ValidationError("Specification requires name, unit, and direction.") from exc

    @classmethod
    def from_json(cls, value: str) -> Self:
        """Restore a specification from a versioned JSON object."""
        return cls.from_dict(_json_object(value))
