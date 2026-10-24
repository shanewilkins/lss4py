"""Declared CSV loading and numeric-clock observation contracts without hidden reconstruction."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest

from lss4py import (
    AdapterError,
    ColumnRule,
    CSVTabularAdapter,
    DataContract,
    NumericEventLog,
    NumericLogContract,
    ValidationError,
    load_csv,
    load_numeric_event_log,
)
from lss4py.adapters.tabular import load_tabular_records

ACTIVITY = NumericLogContract(
    case_id_column="case",
    activity_column="activity",
    pass_column="pass",
    load_id_column="load",
    time_columns=("queue", "setup", "start", "end"),
    unit="minutes",
    clock="operating minutes from 07:00",
    boundary="drop-off through readiness notification",
)
TABLE = DataContract(
    columns=(ColumnRule("id", kind="string"), ColumnRule("value", minimum=0)),
    key_columns=("id",),
    duplicates="error",
)
ROOT = Path(__file__).parent / "fixtures/reference/washnfold-friday91"


def write(tmp_path, text):
    """Provide an independent small source under each test's temporary directory."""
    path = tmp_path / "source.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_csv_declared_types_preserve_identity_extras_and_source_evidence(tmp_path):
    path = write(tmp_path, "id,value,note\n001,1.2,NA\nNA,2.5,free text\n")
    frame, schema = CSVTabularAdapter(path, contract=TABLE).load()
    assert frame.to_dicts() == [
        {"id": "001", "value": 1.2, "note": "NA"},
        {"id": "NA", "value": 2.5, "note": "free text"},
    ]
    assert schema.source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert schema.validation is not None
    assert schema.validation.valid and schema.row_count == 2
    assert schema.column_types["id"] == "String"


def test_convenience_loaders_and_explicit_source_mapping(tmp_path):
    path = write(tmp_path, "external_id,amount,note\n001,2,keep\n")
    frame = load_csv(path, contract=TABLE, bindings={"id": "external_id", "value": "amount"})
    assert frame.columns == ["id", "value", "note"]
    assert frame.row(0) == ("001", 2.0, "keep")
    plain = write(tmp_path, "id,value\n001,2\n")
    assert load_tabular_records(plain, contract=TABLE) == [{"id": "001", "value": 2.0}]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "id,id\nA,B\n",
        ",value\nA,2\n",
        "id,value\nA\n",
        "id,value\nA,2,extra\n",
        "id,value\nA,not-a-number\n",
        "id,value\nA,1\nA,2\n",
        "id,value\n,1\n",
        "id,value\nA,-1\n",
        "id,value\nA,inf\n",
        "id,value\nA,NaN\n",
        "id,value\nA,1\n\n",
        'id,value\nA,"unterminated\n',
        "id,value\n",
    ],
)
def test_csv_rejects_invalid_or_ambiguous_sources(tmp_path, text):
    with pytest.raises(AdapterError):
        load_csv(write(tmp_path, text), contract=TABLE)


def test_source_errors_and_checksum_mismatch_are_explicit(tmp_path):
    with pytest.raises(AdapterError, match="Could not read"):
        load_csv(tmp_path / "missing.csv", contract=TABLE)
    path = write(tmp_path, "id,value\nA,2\n")
    with pytest.raises(AdapterError, match="checksum mismatch"):
        load_csv(path, contract=TABLE, expected_sha256="0" * 64)
    path.write_bytes(b"id,value\n\xff,2\n")
    with pytest.raises(AdapterError, match="Could not parse"):
        load_csv(path, contract=TABLE)


def test_invalid_schema_mapping_fails_without_renaming_over_existing_columns(tmp_path):
    path = write(tmp_path, "id,other,value\nA,B,2\n")
    with pytest.raises(AdapterError, match="collide"):
        load_csv(path, contract=TABLE, bindings={"id": "other"})
    with pytest.raises(ValidationError, match="distinct"):
        CSVTabularAdapter(path, contract=TABLE, bindings={"id": "id", "value": "id"})
    with pytest.raises(ValidationError, match="target"):
        CSVTabularAdapter(path, contract=TABLE, bindings={"unknown": "id"})


def test_csv_reports_invalid_source_row_positions(tmp_path):
    path = write(tmp_path, "id,value\nA,1\nB,-2\n")
    with pytest.raises(AdapterError, match="OUT_OF_RANGE") as error:
        load_csv(path, contract=TABLE)
    assert '"rows": [' in str(error.value)
    assert "\n        1\n" in str(error.value)


def test_calendar_types_are_parsed_only_when_declared(tmp_path):
    contract = DataContract(
        columns=(ColumnRule("when", kind="timestamp"), ColumnRule("flag", kind="boolean"))
    )
    frame = load_csv(write(tmp_path, "when,flag\n2026-10-23T08:00:00,True\n"), contract=contract)
    assert isinstance(frame.schema["when"], pl.Datetime)
    assert frame["flag"].to_list() == [True]


def activity_csv():
    """Keep parallel children and a later pass distinct under one numeric clock."""
    return (
        "case,load,activity,pass,queue,setup,start,end,note\n"
        "A,L1,Wash,1,12.1,13.1,14.1,40.1,first\n"
        "A,L2,Wash,1,12.1,13.1,14.1,40.1,parallel\n"
        "A,,Fold,1,40.1,40.1,40.1,50.1,order level\n"
        "A,,Fold,2,50.1,50.1,50.1,55.1,repeat\n"
    )


def test_numeric_log_preserves_children_null_loads_passes_and_operating_clock(tmp_path):
    log = load_numeric_event_log(write(tmp_path, activity_csv()), contract=ACTIVITY)
    assert log.height == 4
    assert log.frame["load"].to_list() == ["L1", "L2", None, None]
    assert log.frame["pass"].to_list() == [1, 1, 1, 2]
    assert log.frame["queue"].to_list()[0] == 12.1
    assert log.to_polars() is not log.frame
    assert NumericLogContract.from_dict(ACTIVITY.to_dict()) == ACTIVITY


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("13.1,14.1", "15.1,14.1"),
        ("14.1,40.1", "14.1,"),
        ("12.1,13.1", "-1,13.1"),
        ("12.1,13.1", "2026-10-23,13.1"),
        ("L2,Wash,1", "L1,Wash,1"),
        ("Fold,2", "Fold,1"),
        ("Wash,1", "Wash,0"),
    ],
)
def test_numeric_log_rejects_invalid_ordering_missing_or_duplicate_records(tmp_path, old, new):
    with pytest.raises(AdapterError):
        load_numeric_event_log(write(tmp_path, activity_csv().replace(old, new)), contract=ACTIVITY)


def test_null_child_identity_does_not_collide_with_literal_text(tmp_path):
    text = (
        "case,load,activity,pass,queue,setup,start,end\nA,,Fold,1,0,0,0,1\nA,None,Fold,1,0,0,0,1\n"
    )
    assert load_numeric_event_log(write(tmp_path, text), contract=ACTIVITY).height == 2


def test_scoped_lifecycle_events_preserve_occurrences_and_source_order(tmp_path):
    contract = replace(
        ACTIVITY, time_columns=("time",), lifecycle_column="lifecycle", scope_columns=("run",)
    )
    text = (
        "run,case,load,activity,pass,lifecycle,time\n"
        "1,A,,Order,1,arrival,9.1\n1,A,,Order,1,ready,174.3\n"
        "2,A,,Order,1,arrival,10.2\n"
    )
    log = load_numeric_event_log(write(tmp_path, text), contract=contract)
    assert log.frame["time"].to_list() == [9.1, 174.3, 10.2]
    assert log.frame["run"].to_list() == ["1", "1", "2"]
    assert log.metadata["exclusions"] == []


@pytest.mark.parametrize(
    "fields",
    [
        {"time_columns": ("time",)},
        {"time_columns": ("a", "b")},
        {"unit": "calendar"},
        {"clock": ""},
        {"pass_column": "case"},
        {"time_columns": "time"},
    ],
)
def test_numeric_contract_rejects_ambiguous_declarations(fields):
    with pytest.raises(ValidationError):
        replace(ACTIVITY, **fields)


def test_programmatic_numeric_log_cannot_bypass_validation():
    with pytest.raises(ValidationError):
        NumericEventLog(pl.DataFrame({"case": ["A"]}), ACTIVITY)


def test_pinned_book_activity_source_is_ingested_with_declared_full_precision_roles():
    configuration = json.loads(
        (ROOT.parents[3] / "examples/white_belt/simulation_sources.json").read_text()
    )
    profile = configuration["profiles"][0]
    log = load_numeric_event_log(
        ROOT / "event_log.csv",
        contract=NumericLogContract.from_dict(profile["contract"]),
        expected_sha256=profile["expected_sha256"],
    )
    assert log.height == 330
    assert log.frame["Load ID"].null_count() == 200
    assert log.frame["Work End (elapsed min)"].dtype == pl.Float64
    assert log.frame["Notes"].null_count() > 0
