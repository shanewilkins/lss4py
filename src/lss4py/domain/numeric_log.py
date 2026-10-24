"""Distinct contracts for numeric-clock lifecycle events and four-endpoint activity records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import polars as pl

from lss4py.domain.data_quality import ColumnRule, DataContract, DataValidationReport
from lss4py.errors import ValidationError


def _names(values: tuple) -> None:
    """Validate declared role names without inferring a source schema or process identity."""
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValidationError("Numeric log bindings and context must be nonblank strings.")


@dataclass(frozen=True, slots=True)
class NumericLogContract:
    """Declare grain, identities and a shared numeric clock before reading observations.

    One time field describes a lifecycle event and requires a lifecycle binding.
    Four ordered fields describe queue/setup/work-start/work-end activity records.
    Case and scope IDs are strings; child load IDs may be absent (null) only when
    explicitly bound. A pass/occurrence number is required to retain repetitions.
    """

    case_id_column: str
    activity_column: str
    pass_column: str
    time_columns: tuple[str, ...]
    unit: str
    clock: str
    boundary: str
    load_id_column: str | None = None
    lifecycle_column: str | None = None
    scope_columns: tuple[str, ...] = ()
    additional_columns: tuple[ColumnRule, ...] = ()

    def __post_init__(self) -> None:
        """Freeze bindings and reject ambiguous roles or incompatible event shapes."""
        for name in ("time_columns", "scope_columns", "additional_columns"):
            value = getattr(self, name)
            if not isinstance(value, (list, tuple)):
                raise ValidationError(f"{name} must be a sequence.")
            object.__setattr__(self, name, tuple(value))
        _names(
            (self.case_id_column, self.activity_column, self.pass_column, self.clock, self.boundary)
        )
        _names(self.time_columns + self.scope_columns)
        self._shape()
        names = self.identity_columns + self.time_columns
        if len(set(names)) != len(names):
            raise ValidationError("Numeric log roles must use distinct columns.")
        self.data_contract()  # Also validates any declared additional columns.

    def _shape(self) -> None:
        """Keep lifecycle instants separate from activity intervals and calendar datetimes."""
        if len(self.time_columns) not in (1, 4):
            raise ValidationError(
                "Numeric logs require one lifecycle time or four activity endpoints."
            )
        if self.unit not in ("seconds", "minutes", "hours", "days"):
            raise ValidationError("Numeric log unit must be seconds, minutes, hours, or days.")
        if len(self.time_columns) == 1 and self.lifecycle_column is None:
            raise ValidationError("Single-time numeric events require a lifecycle_column.")
        if len(self.time_columns) == 4 and self.lifecycle_column is not None:
            raise ValidationError("Four-endpoint activities do not have a lifecycle_column.")
        _names(tuple(v for v in (self.load_id_column, self.lifecycle_column) if v is not None))

    @property
    def identity_columns(self) -> tuple[str, ...]:
        """Return the full explicit event identity, including null-child identity where bound."""
        return (
            self.scope_columns
            + (self.case_id_column, self.activity_column, self.pass_column)
            + tuple(v for v in (self.load_id_column, self.lifecycle_column) if v is not None)
        )

    def data_contract(self) -> DataContract:
        """Build the schema; composite uniqueness uses explicit null-child semantics."""
        strings = self.scope_columns + (self.case_id_column, self.activity_column)
        columns = tuple(ColumnRule(n, kind="string") for n in strings)
        columns += (ColumnRule(self.pass_column, kind="integer", minimum=1),)
        columns += tuple(ColumnRule(n, minimum=0, unit=self.unit) for n in self.time_columns)
        if self.load_id_column is not None:
            columns += (ColumnRule(self.load_id_column, kind="string", nullable=True),)
        if self.lifecycle_column is not None:
            columns += (ColumnRule(self.lifecycle_column, kind="string"),)
        return DataContract(columns=columns + self.additional_columns, duplicates="allow")

    def to_dict(self) -> dict:
        """Expose source roles, units, clock, boundary and schema for audit and rerun."""
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> NumericLogContract:
        """Restore explicit bindings without executing a loader or repairing source data."""
        try:
            value = dict(value)
            value["additional_columns"] = tuple(
                ColumnRule(**v) for v in value.get("additional_columns", ())
            )
            return cls(**value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Invalid numeric log contract: {exc}") from exc


@dataclass(frozen=True, slots=True)
class NumericEventLog:
    """Validated eager numeric observations, retaining original columns and source order.

    This is not a calendar IntervalEventLog and is not an order reconstruction.
    Lifecycle pairing, parallel-load collapse and VA classification are separate
    analytical choices. Invalid or incomplete rows block construction.
    """

    frame: pl.DataFrame
    contract: NumericLogContract
    metadata: dict[str, Any] = field(default_factory=dict)
    validation: DataValidationReport = field(init=False)

    def __post_init__(self) -> None:
        """Enforce numeric schemas, complete endpoints and full composite event identity."""
        from lss4py._numeric_log import validate_numeric_log

        if not isinstance(self.frame, pl.DataFrame) or not isinstance(
            self.contract, NumericLogContract
        ):
            raise ValidationError("NumericEventLog requires eager Polars and a NumericLogContract.")
        report = validate_numeric_log(self.frame, self.contract)
        if not report.valid:
            raise ValidationError(report.to_json())
        object.__setattr__(self, "validation", report)

    @property
    def height(self) -> int:
        """Return source observation count without flattening loads or repeated passes."""
        return self.frame.height

    def to_polars(self, *, copy: bool = True) -> pl.DataFrame:
        """Expose the validated observations, cloning by default."""
        return self.frame.clone() if copy else self.frame
