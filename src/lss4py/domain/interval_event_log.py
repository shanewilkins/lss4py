"""Canonical interval-event log contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import polars as pl

CANONICAL_INTERVAL_EVENT_COLUMNS = (
    "case_id",
    "step_id",
    "started_at",
    "completed_at",
)


@dataclass(frozen=True, slots=True)
class IntervalEventLog:
    """Validated interval-event observations backed by an eager Polars frame.

    Each row represents one observed activity interval. Core adapters construct
    this type after normalizing source-specific names and validating values.
    Analytical functions may also continue to accept supported eager native
    frames directly when a process model supplies the required bindings.
    """

    frame: pl.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Enforce the canonical eager Polars shape."""
        if not isinstance(self.frame, pl.DataFrame):
            raise TypeError("IntervalEventLog.frame must be an eager Polars DataFrame.")

        missing = [
            column
            for column in CANONICAL_INTERVAL_EVENT_COLUMNS
            if column not in self.frame.columns
        ]
        if missing:
            raise ValueError("IntervalEventLog is missing canonical columns: " + ", ".join(missing))

        for column in ("case_id", "step_id"):
            if self.frame.schema[column] != pl.String:
                raise TypeError(f"IntervalEventLog column '{column}' must use the String dtype.")
        for column in ("started_at", "completed_at"):
            if not isinstance(self.frame.schema[column], pl.Datetime):
                raise TypeError(f"IntervalEventLog column '{column}' must use a Datetime dtype.")

    @property
    def columns(self) -> list[str]:
        """Return the canonical frame's column names."""
        return self.frame.columns

    @property
    def height(self) -> int:
        """Return the number of event intervals."""
        return self.frame.height

    def to_polars(self, *, copy: bool = True) -> pl.DataFrame:
        """Return the underlying Polars frame, cloning it by default."""
        return self.frame.clone() if copy else self.frame
