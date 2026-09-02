"""
Adapter contracts for LSS4PY data ingestion.

All adapters (internal and external) must conform to these contracts.
This module is part of LSS4PY's public API and is stable across releases.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


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
        Inspect and return schema without loading full data.

        This method should peek at the source (e.g., read column headers,
        count rows) without materializing all data in memory.

        Returns:
            AdapterSchema describing the data structure.

        Raises:
            AdapterError: if the source is unreachable or schema cannot be inferred.
        """

    @abstractmethod
    def load(
        self,
        backend: Literal["pandas", "polars"] = "pandas",
    ) -> tuple[Any, AdapterSchema]:
        """
        Load data from source and normalize to eager DataFrame.

        Args:
            backend: Requested dataframe backend ("pandas" or "polars").

        Returns:
            (DataFrame, AdapterSchema) where DataFrame is native to the backend.

        Raises:
            AdapterError: if data cannot be loaded.
            ValueError: if backend is not supported.
        """


class EventLogAdapter(ABC):
    """
    Base class for adapters that produce event-log data.

    Event logs have required fields: case_id, activity, timestamp.
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
        Inspect event-log schema without loading all events.

        Returns:
            AdapterSchema with required_fields including case_id, activity, timestamp.

        Raises:
            AdapterError: if the source is unreachable.
        """

    @abstractmethod
    def load(self, backend: str = "pandas") -> tuple[Any, AdapterSchema]:
        """
        Load events from source and normalize to EventLog domain model.

        Args:
            backend: Unused for now (event logs are normalized to EventLog,
                not raw DataFrames). Kept for API compatibility.

        Returns:
            (EventLog, AdapterSchema) where EventLog is lss4py.domain.models.EventLog.

        Raises:
            AdapterError: if data cannot be loaded or is invalid.
        """
