"""Independent book fixture, parallel accounting, completeness and evidence regressions."""

import importlib.util
import json
from dataclasses import replace
from importlib.metadata import version
from pathlib import Path

import polars as pl
import pytest

from lss4py import (
    NumericEventLog,
    OrderReconstructionResult,
    ValidationError,
    reconstruct_orders,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/reference/washnfold-friday91"
SPEC = importlib.util.spec_from_file_location(
    "reconstruction_example", ROOT / "examples/white_belt/reconstruct.py"
)
assert SPEC is not None and SPEC.loader is not None
EXAMPLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXAMPLE)


@pytest.fixture
def log():
    profile = json.loads((EXAMPLE.HERE / "simulation_sources.json").read_text())["profiles"][0]
    from lss4py import NumericLogContract, load_numeric_event_log

    return load_numeric_event_log(
        FIXTURE / "event_log.csv", contract=NumericLogContract.from_dict(profile["contract"])
    )


@pytest.fixture
def result(log):
    return reconstruct_orders(log, policy=EXAMPLE.POLICY)


@pytest.mark.parametrize(
    ("actual", "expected"),
    [
        ("arrival", "Arrival (elapsed min)"),
        ("readiness", "Ready and notified (elapsed min)"),
        ("lead_time", "Operating L/T (min)"),
        ("processing", "Total P/T (min)"),
        ("waiting", "Total W/T (min)"),
        ("setup", "Total S/T (min)"),
        ("value_add", "VA time (min)"),
        ("correction_occurrences", "Correction occurrences"),
    ],
)
def test_all_39_orders_match_independent_prepared_fixture(result, actual, expected):
    prepared = pl.read_csv(FIXTURE / "order_summary.csv").sort("Order ID")
    orders = result.to_polars().sort("Order ID")
    assert orders.height == 39
    assert orders["Order ID"].to_list() == prepared["Order ID"].to_list()
    assert orders[actual].to_list() == pytest.approx(prepared[expected].to_list(), abs=1e-8)


def test_wnf003_parallel_envelopes_and_corrections(result):
    order = result.to_polars().filter(pl.col("Order ID") == "WNF-003").row(0, named=True)
    activities = result.to_polars("activities").filter(pl.col("Order ID") == "WNF-003")
    wash = activities.filter(pl.col("activity") == "Wash").row(0, named=True)
    assert wash["processing"] == pytest.approx(30)
    assert len(wash["load_ids"]) == 2
    assert order["value_add"] == pytest.approx(82.7)
    assert order["correction_occurrences"] == 1
    assert order["activity_records"] == 10


def test_correction_flags_do_not_double_count_and_sources_remain(result, log):
    assert result.metadata["correction_occurrences"] == 5
    assert result.metadata["affected_orders"] == 5
    assert result.to_polars("source_records").equals(log.frame)
    positions = [p for row in result.metadata["activities"] for p in row["source_positions"]]
    assert sorted(positions) == list(range(330))
    assert result.metadata["exclusions"] == []


def test_result_round_trip_retains_evidence(result):
    restored = OrderReconstructionResult.from_dict(json.loads(result.to_json()))
    assert restored.to_polars().equals(result.to_polars())
    assert restored.metadata == result.metadata
    assert restored.provenance.parameters["policy"]["parallel_activities"] == ["Wash", "Dry"]


def test_source_order_does_not_determine_order_path(log, result):
    reversed_log = NumericEventLog(log.frame.reverse(), log.contract)
    actual = reconstruct_orders(reversed_log, policy=EXAMPLE.POLICY)
    assert actual.to_polars().sort("Order ID").equals(result.to_polars().sort("Order ID"))


@pytest.mark.parametrize("activity", ["Drop-off and ticket", "Dry", "Send readiness notification"])
def test_incomplete_orders_fail_without_exclusions(log, activity):
    frame = log.frame.filter(
        ~((pl.col("Order ID") == "WNF-003") & (pl.col("Activity Name") == activity))
    )
    with pytest.raises(ValidationError, match=r"Incomplete order.*WNF-003"):
        reconstruct_orders(NumericEventLog(frame, log.contract), policy=EXAMPLE.POLICY)


def test_gaps_and_overlaps_are_not_zero_filled(log):
    q = log.contract.time_columns[0]
    frame = log.frame.with_columns(
        pl.when((pl.col("Order ID") == "WNF-003") & (pl.col("Activity Name") == "Sort and tag"))
        .then(pl.col(q) - 0.1)
        .otherwise(pl.col(q))
        .alias(q)
    )
    with pytest.raises(ValidationError, match=r"Gap/overlap.*WNF-003.*rows="):
        reconstruct_orders(NumericEventLog(frame, log.contract), policy=EXAMPLE.POLICY)


def test_scope_prevents_merging_same_order_between_runs(log):
    frame = pl.concat([log.frame.with_columns(pl.lit(v).alias("run")) for v in ("01", "02")])
    contract = replace(log.contract, scope_columns=("run",))
    result = reconstruct_orders(NumericEventLog(frame, contract), policy=EXAMPLE.POLICY)
    assert result.to_polars().height == 78
    assert result.metadata["correction_occurrences"] == 10


def test_unrecognized_flags_fail(log):
    frame = log.frame.with_columns(pl.lit("?").alias("Rework Y/N"))
    with pytest.raises(ValidationError, match="rework flag"):
        reconstruct_orders(NumericEventLog(frame, log.contract), policy=EXAMPLE.POLICY)


def test_raw_activity_durations_and_classes_are_separate_from_envelopes(result):
    raw = result.to_polars("activity_records").filter(pl.col("Order ID") == "WNF-003")
    wash = raw.filter(pl.col("Activity Name") == "Wash")
    staging = raw.filter(pl.col("Activity Name") == "Stage for collection")
    assert wash["processing"].sum() == pytest.approx(60)
    assert staging["processing_class"].to_list() == ["RNVA"]
    assert raw.filter(pl.col("processing_class") == "NVA").height == 2


def test_missing_one_parallel_load_is_detected(log):
    frame = log.frame.filter(
        ~(
            (pl.col("Order ID") == "WNF-003")
            & (pl.col("Activity Name") == "Wash")
            & (pl.col("Load ID") == "L1")
        ).fill_null(False)
    )
    with pytest.raises(ValidationError, match="Incomplete parallel load group"):
        reconstruct_orders(NumericEventLog(frame, log.contract), policy=EXAMPLE.POLICY)


def test_audited_bundle_restores_reconstruction(result):
    from lss4py import AnalysisBundle, InputReference

    bundle = AnalysisBundle.capture(
        "Reconstruction",
        results={"orders": result},
        inputs={
            "events": InputReference.from_bytes(
                "event_log.csv",
                (FIXTURE / "event_log.csv").read_bytes(),
                selection="All 330 records",
            )
        },
        result_inputs={"orders": ("events",)},
        cohort_definition=EXAMPLE.POLICY.cohort,
        software_versions={
            name: version(name) for name in ("lss4py", "numpy", "scipy", "narwhals", "polars")
        },
    )
    restored = AnalysisBundle.from_json(bundle.to_json())
    restored_result = restored.results[0]
    assert isinstance(restored_result, OrderReconstructionResult)
    assert restored_result.to_polars().equals(result.to_polars())


def test_repeated_passes_remain_distinct(log):
    base = log.frame.filter(pl.col("Order ID") == "WNF-001")
    last = base.filter(pl.col("Activity Name") == "Send readiness notification")
    end = last[log.contract.time_columns[-1]][0]
    extra = last.with_columns(
        pl.lit(2, dtype=pl.Int64).alias("Pass"),
        *[pl.lit(end).alias(c) for c in log.contract.time_columns],
    )
    result = reconstruct_orders(
        NumericEventLog(pl.concat([base, extra]), log.contract), policy=EXAMPLE.POLICY
    )
    notifications = result.to_polars("activities").filter(
        pl.col("activity") == "Send readiness notification"
    )
    assert notifications["pass"].to_list() == [1, 2]
    assert result.to_polars()["readiness"][0] == end


@pytest.mark.parametrize(
    "changes",
    [
        {"rework_value": "N"},
        {"arrival_activity": "Send readiness notification"},
        {"tolerance": float("nan")},
        {"tolerance": -1},
        {"cohort": ""},
        {"parallel_activities": "Wash"},
        {"required_activities": ("Wash", "Wash")},
        {"correction_activity": "Wash"},
        {"non_rework_value": None},
        {"tolerance": "1"},
        {"value_add_activities": ("Stage for collection",)},
        {"value_add_activities": ("Fold correction",)},
    ],
)
def test_ambiguous_policy_declarations_fail(changes):
    with pytest.raises(ValidationError):
        replace(EXAMPLE.POLICY, **changes)
