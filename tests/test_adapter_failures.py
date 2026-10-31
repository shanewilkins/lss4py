"""Protect source failures on the numeric book ingestion path."""

import pytest

from lss4py import AdapterError, ColumnRule, CSVTabularAdapter, DataContract, ValidationError
from lss4py.adapters.numeric_log import NumericEventLogCSVAdapter


@pytest.mark.parametrize(
    ("contents", "column", "kind", "message"),
    [
        (b"flag\nmaybe\n", "flag", "boolean", r"Invalid boolean.*flag.*data row 0"),
        (
            b"count\n9223372036854775808\n",
            "count",
            "integer",
            "Could not store declared column 'count'",
        ),
        (b"amount\n1\nbad\n", "amount", "numeric", r"Invalid numeric.*amount.*data row 1"),
    ],
)
def test_csv_parse_and_storage_failures_retain_field_and_source_context(
    tmp_path, contents, column, kind, message
):
    source = tmp_path / "source.csv"
    source.write_bytes(contents)
    adapter = CSVTabularAdapter(
        source, contract=DataContract(columns=(ColumnRule(column, kind=kind),))
    )
    with pytest.raises(AdapterError, match=message):
        adapter.load()
    assert source.read_bytes() == contents


def test_numeric_adapter_requires_an_explicit_numeric_contract(tmp_path):
    with pytest.raises(ValidationError, match="must be a NumericLogContract"):
        NumericEventLogCSVAdapter(tmp_path / "missing.csv", contract=None)  # ty: ignore[invalid-argument-type]


def test_numeric_schema_reports_validated_source_identity():
    import hashlib
    import json
    from pathlib import Path

    from lss4py import NumericLogContract

    root = Path(__file__).resolve().parents[1]
    source = root / "examples/white_belt/event_log.csv"
    profile = json.loads((source.parent / "simulation_sources.json").read_text())["profiles"][0]
    contract = NumericLogContract.from_dict(profile["contract"])
    schema = NumericEventLogCSVAdapter(source, contract=contract).schema()
    assert schema.row_count == 330
    assert schema.key_columns == list(contract.identity_columns)
    assert schema.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert schema.validation is not None and schema.validation.valid
