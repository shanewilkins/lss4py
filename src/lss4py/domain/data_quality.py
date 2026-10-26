"""Immutable, backend-neutral contracts for data-quality checks and preparation."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from numbers import Integral, Real
from typing import Any, Literal

import polars as pl

from lss4py.errors import ValidationError


@dataclass(frozen=True, slots=True)
class ColumnRule:
    """Explicit column meaning, nullable policy, numeric domain and expected unit."""

    name: str
    kind: Literal["numeric", "integer", "string", "boolean", "timestamp"] = "numeric"
    nullable: bool = False
    minimum: float | None = None
    maximum: float | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        """Reject ambiguous rules before inspecting any data."""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Column names must be nonblank strings.")
        if self.kind not in ("numeric", "integer", "string", "boolean", "timestamp"):
            raise ValidationError("Unsupported column kind.")
        if not isinstance(self.nullable, bool):
            raise ValidationError("nullable must be boolean.")
        _domain(self)
        _normalize_bounds(self)
        if self.unit is not None and (not isinstance(self.unit, str) or not self.unit.strip()):
            raise ValidationError("unit must be nonblank text or None.")


def _normalize_bounds(rule: ColumnRule) -> None:
    """Detach numerical scalar bounds from backend-specific scalar wrappers."""
    for name in ("minimum", "maximum"):
        value = getattr(rule, name)
        if value is not None:
            object.__setattr__(
                rule, name, int(value) if isinstance(value, Integral) else float(value)
            )


def _bound(value: Any) -> None:
    """Require a finite real bound without coercing strings or booleans."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError("Bounds must be finite numeric values.")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValidationError("Bounds must be finite numeric values.")


def _domain(rule: ColumnRule) -> None:
    """Validate bounds and their declared numerical role."""
    for value in (rule.minimum, rule.maximum):
        if value is not None:
            _bound(value)
            if rule.kind not in ("numeric", "integer"):
                raise ValidationError("Bounds require a numeric kind.")
    if rule.minimum is not None and rule.maximum is not None and rule.minimum > rule.maximum:
        raise ValidationError("minimum cannot exceed maximum.")


def _sequence(value: Any) -> tuple:
    """Copy declared sequences while rejecting strings and mappings."""
    if not isinstance(value, (tuple, list)):
        raise ValidationError("Contract columns, keys and time pairs must be sequences.")
    return tuple(value)


def _keys(keys: tuple[str, ...], names: list[str]) -> None:
    """Require unique keys that reference declared columns."""
    if any(not isinstance(k, str) or k not in names for k in keys):
        raise ValidationError("Keys must reference declared column names.")
    if len(set(keys)) != len(keys):
        raise ValidationError("Key columns must be unique.")


def _time_pairs(pairs: tuple, columns: tuple[ColumnRule, ...]) -> None:
    """Require distinct timestamp roles for each ordered pair."""
    timestamps = {c.name for c in columns if c.kind == "timestamp"}
    for pair in pairs:
        if len(pair) != 2:
            raise ValidationError("Time-order pairs require two timestamp columns.")
        if any(not isinstance(k, str) or k not in timestamps for k in pair):
            raise ValidationError("Time-order pairs must reference timestamp columns.")
        if pair[0] == pair[1]:
            raise ValidationError("Time-order columns must be distinct.")


@dataclass(frozen=True, slots=True)
class DataContract:
    """Rules for one eager table; keys and time-order pairs are always explicit."""

    columns: tuple[ColumnRule, ...]
    key_columns: tuple[str, ...] = ()
    timestamp_order: tuple[tuple[str, str], ...] = ()
    duplicates: Literal["error", "warn", "allow"] = "warn"
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        """Freeze caller sequences and reject incompatible or incomplete policies."""
        object.__setattr__(self, "columns", _sequence(self.columns))
        object.__setattr__(self, "key_columns", _sequence(self.key_columns))
        object.__setattr__(
            self, "timestamp_order", tuple(_sequence(p) for p in _sequence(self.timestamp_order))
        )
        if not self.columns or not all(isinstance(c, ColumnRule) for c in self.columns):
            raise ValidationError("columns must contain ColumnRule instances.")
        names = [c.name for c in self.columns]
        if len(names) != len(set(names)):
            raise ValidationError("Contract column names must be unique.")
        if self.duplicates not in ("error", "warn", "allow") or self.schema_version != "1.0":
            raise ValidationError("Unsupported duplicate policy or contract version.")
        _keys(self.key_columns, names)
        _time_pairs(self.timestamp_order, self.columns)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the exact policy for reruns, with no backend-specific objects."""
        return {
            "schema_version": self.schema_version,
            "columns": [asdict(c) for c in self.columns],
            "key_columns": list(self.key_columns),
            "timestamp_order": [list(p) for p in self.timestamp_order],
            "duplicates": self.duplicates,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataContract:
        """Restore a declared contract and validate fields and supported versions."""
        try:
            allowed = {"columns", "key_columns", "timestamp_order", "duplicates", "schema_version"}
            if set(data) - allowed:
                raise ValidationError("Unknown data contract fields.")
            return cls(
                columns=tuple(ColumnRule(**c) for c in data["columns"]),
                key_columns=data.get("key_columns", ()),
                timestamp_order=data.get("timestamp_order", ()),
                duplicates=data.get("duplicates", "warn"),
                schema_version=data.get("schema_version", "1.0"),
            )
        except (TypeError, KeyError, AttributeError) as exc:
            raise ValidationError("Invalid serialized data contract.") from exc


@dataclass(frozen=True, slots=True)
class DataIssue:
    """A stable check code and its source-row positions, independent of index labels."""

    code: str
    severity: Literal["error", "warning"]
    message: str
    columns: tuple[str, ...] = ()
    rows: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    """Observed logical schema and counts; unique excludes missing/invalid values."""

    name: str
    observed_kind: str
    missing_count: int
    unique_count: int
    invalid_count: int
    expected_unit: str | None
    source_unit: str | None


@dataclass(frozen=True, slots=True)
class DataValidationReport:
    """Versioned inspection evidence; validity concerns only the declared checks."""

    contract: DataContract
    row_count: int
    column_names: tuple[str, ...]
    profiles: tuple[ColumnProfile, ...]
    issues: tuple[DataIssue, ...]
    backend: str
    schema_version: str = "1.0"
    method_version: str = "1.0"

    @property
    def errors(self) -> tuple[DataIssue, ...]:
        """Return blocking findings without changing or filtering the source."""
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[DataIssue, ...]:
        """Return nonblocking findings requiring caller interpretation."""
        return tuple(i for i in self.issues if i.severity == "warning")

    @property
    def valid(self) -> bool:
        """Whether the declared checks found no blocking issues."""
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize strict JSON-compatible schema, policy, counts and row evidence."""
        return {
            "result_type": "DataValidationReport",
            "method_version": self.method_version,
            "schema_version": self.schema_version,
            "contract": self.contract.to_dict(),
            "row_count": self.row_count,
            "column_names": list(self.column_names),
            "backend": self.backend,
            "valid": self.valid,
            "profiles": [asdict(p) for p in self.profiles],
            "issues": [
                {**asdict(i), "columns": list(i.columns), "rows": list(i.rows)} for i in self.issues
            ],
        }

    def to_json(self) -> str:
        """Export finite JSON without backend encoders or nonstandard numeric tokens."""
        return json.dumps(self.to_dict(), allow_nan=False, indent=2)


@dataclass(frozen=True, slots=True)
class NormalizedData:
    """Canonical prepared columns with source positions and before/after evidence.

    The frame contains only declared columns. Use to_polars for a copy; source
    positions refer to the original eager table, never its pandas index labels.
    """

    _frame: pl.DataFrame
    source_rows: tuple[int, ...]
    before: DataValidationReport
    after: DataValidationReport
    transformations: tuple[str, ...]

    def to_polars(self) -> pl.DataFrame:
        """Return an independently mutable canonical frame."""
        return self._frame.clone()

    def to_dict(self) -> dict[str, Any]:
        """Serialize preparation evidence separately from the actual data frame."""
        return {
            "result_type": "NormalizedData",
            "schema_version": "1.0",
            "source_rows": list(self.source_rows),
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "transformations": list(self.transformations),
        }

    def to_json(self) -> str:
        """Export preparation evidence without serializing backend frame internals."""
        return json.dumps(self.to_dict(), allow_nan=False, indent=2)
