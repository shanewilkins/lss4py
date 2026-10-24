"""Numeric operating-clock CSV ingestion, distinct from calendar interval loading."""

from pathlib import Path
from typing import Literal

from lss4py.adapters.contracts import AdapterSchema, EventLogAdapter
from lss4py.adapters.tabular import CSVTabularAdapter
from lss4py.domain.numeric_log import NumericEventLog, NumericLogContract
from lss4py.errors import AdapterError, ValidationError


class NumericEventLogCSVAdapter(EventLogAdapter):
    """Load numeric activity intervals or lifecycle events under explicit source bindings."""

    def __init__(
        self,
        source_reference: str | Path,
        *,
        contract: NumericLogContract,
        expected_sha256: str | None = None,
    ) -> None:
        """Require a declared numeric shape and clock rather than inferring calendar semantics."""
        super().__init__(str(source_reference))
        if not isinstance(contract, NumericLogContract):
            raise ValidationError("contract must be a NumericLogContract.")
        self.contract = contract
        self.expected_sha256 = expected_sha256

    def schema(self) -> AdapterSchema:
        """Inspect the validated numeric source and its actual normalized types."""
        return self.load()[1]

    def load(self, backend: Literal["polars"] = "polars") -> tuple[NumericEventLog, AdapterSchema]:
        """Read one source snapshot and reject incomplete/ambiguous event records explicitly."""
        frame, schema = CSVTabularAdapter(
            self.source_reference,
            contract=self.contract.data_contract(),
            expected_sha256=self.expected_sha256,
            clock=self.contract.clock,
        ).load(backend)
        try:
            result = NumericEventLog(
                frame,
                self.contract,
                metadata={
                    "source_reference": schema.source_reference,
                    "source_sha256": schema.source_sha256,
                    "contract": self.contract.to_dict(),
                    "transformations": schema.transformations,
                    "exclusions": [],
                },
            )
        except ValidationError as exc:
            raise AdapterError(f"Invalid numeric log '{self.source_reference}': {exc}") from exc
        schema.key_columns = list(self.contract.identity_columns)
        schema.validation = result.validation
        return result, schema


def load_numeric_event_log(
    path: str | Path, *, contract: NumericLogContract, expected_sha256: str | None = None
) -> NumericEventLog:
    """Load explicit numeric observations without calendar conversion or hidden reconstruction."""
    return NumericEventLogCSVAdapter(
        path, contract=contract, expected_sha256=expected_sha256
    ).load()[0]
