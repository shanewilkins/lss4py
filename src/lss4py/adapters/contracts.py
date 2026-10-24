"""
Adapter contracts for LSS4PY data ingestion.

All adapters (internal and external) must conform to these contracts.
This module is part of LSS4PY's public API and is stable across releases.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from lss4py.domain.data_quality import DataValidationReport


@dataclass(slots=True)
class AdapterSchema:
    """
    Schema information about data loaded by an adapter.

    Used to document what an adapter produces and validate before
    analytics are run.
    """

    column_names: frozenset[str]
    """All column names in the loaded data."""

    column_types: dict[str, str]
    """Mapping of column name to type (e.g., {"case_id": "string", "amount": "float64"})."""

    row_count: int
    """Number of rows loaded."""

    key_columns: list[str] = field(default_factory=list)
    """Columns that uniquely identify a row (e.g., ["case_id", "timestamp"])."""

    timestamp_columns: list[str] | None = None
    """Columns that represent timestamps (e.g., ["started_at", "completed_at"])."""

    source_format: str | None = None
    """Source format read by the adapter (for example, ``csv``)."""

    backend: str = "polars"
    """Native dataframe backend returned by the adapter."""

    transformations: tuple[str, ...] = ()
    """Ordered, user-visible normalization steps applied while loading."""

    source_reference: str | None = None
    source_sha256: str | None = None
    units: dict[str, str] = field(default_factory=dict)
    clock: str | None = None
    bindings: dict[str, str] = field(default_factory=dict)
    validation: DataValidationReport | None = None

    def validate_required_fields(self, required: list[str]) -> list[str]:
        """
        Check which required fields are missing.

        Returns:
            List of field names that are missing from the schema.
        """
        return [f for f in required if f not in self.column_names]


class TabularAdapter(ABC):
    """
    Base class for adapters that produce tabular (DataFrame) data.

    External adapter implementations should inherit from this class.
    See docs/EXTENDING.md for examples.
    """

    def __init__(self, source_reference: str):
        """
        Args:
            source_reference: Path, URI, connection string, or identifier
                identifying the data source.
        """
        self.source_reference = source_reference

    @abstractmethod
    def schema(self) -> AdapterSchema:
        """
        Inspect and return the normalized source schema.

        Implementations may scan or materialize the source when exact row counts
        or post-normalization types cannot otherwise be determined.

        Returns:
            AdapterSchema describing the data structure.

        Raises:
            AdapterError: if the source is unreachable or schema cannot be inferred.
        """

    @abstractmethod
    def load(
        self,
        backend: Literal["polars"] = "polars",
    ) -> tuple[Any, AdapterSchema]:
        """
        Load data from source and normalize to eager DataFrame.

        Args:
            backend: Requested dataframe backend. Core adapters materialize Polars.

        Returns:
            (DataFrame, AdapterSchema) where DataFrame is native to the backend.

        Raises:
            AdapterError: if data cannot be loaded.
            ValueError: if backend is not supported.
        """


class EventLogAdapter(ABC):
    """
    Base class for adapters that produce event-log data.

    Calendar interval logs use case_id, step_id, started_at, and completed_at.
    Numeric event adapters declare their own activity/lifecycle bindings and
    return the distinct NumericEventLog under ADR-0026.
    External adapter implementations should inherit from this class.
    """

    def __init__(self, source_reference: str):
        """
        Args:
            source_reference: Path, URI, connection string, or identifier
                identifying the data source.
        """
        self.source_reference = source_reference

    @abstractmethod
    def schema(self) -> AdapterSchema:
        """
        Inspect and return the normalized event-log schema.

        Returns:
            AdapterSchema describing the canonical interval-event fields.

        Raises:
            AdapterError: if the source is unreachable.
        """

    @abstractmethod
    def load(self, backend: Literal["polars"] = "polars") -> tuple[Any, AdapterSchema]:
        """
        Load events into the adapter's declared domain observation contract.

        Args:
            backend: Requested dataframe backend. Core adapters materialize Polars.

        Returns:
            A declared event-log value backed by Polars and its AdapterSchema.

        Raises:
            AdapterError: if data cannot be loaded or is invalid.
        """
