"""Public validation entry points over the shared non-analytical data-contract engine."""

from collections.abc import Mapping
from typing import Any

from lss4py._data_quality import normalize_data as _normalize_data
from lss4py._data_quality import validate_data as _validate_data
from lss4py.domain.data_quality import DataContract, DataValidationReport, NormalizedData


def validate_data(
    data: Any, *, contract: DataContract, source_units: Mapping[str, str] | None = None
) -> DataValidationReport:
    """Inspect declared schema, identities, domains, units and ordering without modifying input."""
    return _validate_data(data, contract=contract, source_units=source_units)


def normalize_data(
    data: Any,
    *,
    contract: DataContract,
    source_units: Mapping[str, str] | None = None,
    drop_missing: bool = False,
    drop_duplicates: bool = False,
) -> NormalizedData:
    """Normalize declared values with explicit optional exclusions and retained source positions."""
    return _normalize_data(
        data,
        contract=contract,
        source_units=source_units,
        drop_missing=drop_missing,
        drop_duplicates=drop_duplicates,
    )
