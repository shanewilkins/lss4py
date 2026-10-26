"""Prepared-measurement contracts, fixed deadlines, and cohort evidence across backends."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from lss4py import (
    AnalysisBundle,
    DescriptiveResult,
    OrderSummaryContract,
    ValidationError,
    YieldResult,
    deadline_performance,
    describe,
    lead_time,
    process_cycle_efficiency,
    validate_order_summary,
)

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
FIXTURE = Path(__file__).parent / "fixtures/reference/washnfold-friday91"
CONTEXT: dict[str, Any] = {
    "unit": "minutes",
    "clock": "cumulative operating minutes; closed hours excluded",
    "boundary": "Drop-off through final readiness notification",
    "cohort": "all orders",
}
CONTRACT = OrderSummaryContract(
    case_id_column="id",
    arrival_column="arrival",
    readiness_column="ready",
    lead_time_column="lead",
    value_add_time_column="va",
    **CONTEXT,
    value_add_convention="right-first-time work",
    processing_time_column="pt",
    wait_time_column="wt",
    setup_time_column="st",
)


def observations():
    """Supply unequal leads and a case ready at the exact deadline."""
    return {
        "id": ["A", "B"],
        "arrival": [0.0, 120.0],
        "ready": [600.0, 700.0],
        "lead": [600.0, 580.0],
        "va": [60.0, 116.0],
        "pt": [90.0, 150.0],
        "wt": [500.0, 420.0],
        "st": [10.0, 10.0],
    }


def test_valid_prepared_contract_preserves_semantics_and_source(frame_factory):
    data = observations()
    report = validate_order_summary(frame_factory(data), contract=CONTRACT)
    assert report.valid and report.row_count == 2
    assert OrderSummaryContract.from_dict(CONTRACT.to_dict()) == CONTRACT
    assert data == observations()


@pytest.mark.parametrize(
    ("column", "values", "code"),
    [
        ("id", ["A", "A"], "DUPLICATE"),
        ("ready", [None, 700.0], "MISSING"),
        ("va", [float("inf"), 116.0], "NONFINITE"),
        ("arrival", [-1.0, 120.0], "OUT_OF_RANGE"),
        ("ready", [-1.0, 700.0], "OUT_OF_RANGE"),
        ("ready", [0.0, 100.0], "ORDERING"),
        ("lead", [599.0, 580.0], "LEAD_TIME_MISMATCH"),
        ("va", [601.0, 116.0], "VA_EXCEEDS_LEAD"),
        ("pt", [80.0, 150.0], "TIMING_PARTITION_MISMATCH"),
    ],
)
def test_prepared_contract_returns_row_findings(frame_factory, column, values, code):
    data = observations()
    data[column] = values
    report = validate_order_summary(frame_factory(data), contract=CONTRACT)
    assert not report.valid
    assert any(code in issue.code for issue in report.errors)
    assert any(issue.rows for issue in report.errors)


def test_nearest_rank_is_not_interpolation_or_even_sample_median(frame_factory):
    data = frame_factory({"x": [1.0, 2.0, 3.0, 4.0]})
    empirical = describe(
        data, column="x", percentile_method="nearest_rank", percentiles=[0, 90, 100]
    )
    assert empirical.measurement_sum == 10
    assert empirical.total == empirical.count == 4
    assert empirical.median == 2.5
    assert empirical.percentiles == {
        "p0": 1.0,
        "p25": 1.0,
        "p50": 2.0,
        "p75": 3.0,
        "p90": 4.0,
        "p100": 4.0,
    }
    linear = describe(data, column="x")
    assert linear.percentiles is not None
    assert linear.percentiles["p90"] == pytest.approx(3.7)


def test_descriptive_sum_roundtrip_and_legacy_result(frame_factory):
    data = frame_factory({"x": [1.0, 2.0, 3.0, 4.0]})
    empirical = describe(frame_factory({"x": [1.0, 2.0, 3.0, 4.0]}), column="x")
    assert DescriptiveResult.from_dict(empirical.to_dict()).to_dict() == empirical.to_dict()
    legacy = empirical.to_dict()
    legacy.pop("measurement_sum")
    assert DescriptiveResult.from_dict(legacy).measurement_sum is None
    missing = describe(frame_factory({"x": [None, None]}), column="x")
    assert missing.measurement_sum is None
    with pytest.raises(ValidationError, match="percentile_method"):
        describe(data, column="x", percentile_method="interpolated")  # ty: ignore[invalid-argument-type]


def test_fixed_deadline_equality_and_distinct_ineligible_cases(frame_factory):
    data = frame_factory(
        {
            "id": ["A", "B", "C", "D"],
            "arrival": [120.0, 120.0, 120.1, 0.0],
            "ready": [600.0, 600.1, 700.0, 601.0],
        }
    )
    result = deadline_performance(
        data,
        case_id_column="id",
        arrival_column="arrival",
        readiness_column="ready",
        eligibility_cutoff=120,
        deadline=600,
        **CONTEXT,
    )
    assert (result.numerator, result.denominator) == (2, 3)
    assert result.value == pytest.approx(2 / 3)
    assert result.metadata["on_time_cases"] == ["A"]
    assert result.metadata["ineligible_cases"] == ["C"]
    assert result.metadata["missed_cases"] == ["B", "D"]
    # D has only 601 minutes of lead; B only 480.1, yet both miss the fixed deadline.
    assert YieldResult.from_dict(result.to_dict()).to_dict() == result.to_dict()


@pytest.mark.parametrize("change", ["ineligible", "missing", "duplicate", "reverse"])
def test_deadline_invalid_or_undefined_populations_fail(frame_factory, change):
    data = observations()
    if change == "ineligible":
        cutoff = -1
    else:
        cutoff = 120
    if change == "missing":
        data["ready"][0] = None
    if change == "duplicate":
        data["id"] = ["A", "A"]
    if change == "reverse":
        data["ready"][1] = 119.0
    with pytest.raises(ValidationError):
        deadline_performance(
            frame_factory(data),
            case_id_column="id",
            arrival_column="arrival",
            readiness_column="ready",
            eligibility_cutoff=cutoff,
            deadline=600,
            **CONTEXT,
        )
    with pytest.raises(ValidationError, match="No eligible"):
        deadline_performance(
            frame_factory({"id": ["A"], "arrival": [121.0], "ready": [600.0]}),
            case_id_column="id",
            arrival_column="arrival",
            readiness_column="ready",
            eligibility_cutoff=120,
            deadline=600,
            **CONTEXT,
        )


def test_ratio_of_sums_retains_aligned_case_evidence(frame_factory):
    data = frame_factory({"id": ["A", "B"], "lead": [10.0, 90.0], "va": [5.0, 9.0]})
    result = process_cycle_efficiency(
        data,
        lead_time_column="lead",
        value_add_time_column="va",
        aggregation="cohort",
        case_id_column="id",
        **CONTEXT,
        value_add_convention="right-first-time work",
    )
    assert result.values.tolist() == pytest.approx([14.0])
    assert (
        np.mean(
            process_cycle_efficiency(
                data, lead_time_column="lead", value_add_time_column="va"
            ).values
        )
        == 30
    )
    assert result.metadata["observation_count"] == 2
    assert result.metadata["case_ids"] == ["A", "B"]
    assert result.metadata["lead_time_sum"] == 100
    assert result.metadata["value_add_time_sum"] == 14
    assert result.provenance.cohort_definition == "all orders"
    assert result.metadata["aggregation"] == "ratio_of_sums"


def test_cohort_result_bundle_roundtrip(frame_factory):
    result = process_cycle_efficiency(
        frame_factory({"id": ["A", "B"], "lead": [10.0, 90.0], "va": [5.0, 9.0]}),
        lead_time_column="lead",
        value_add_time_column="va",
        aggregation="cohort",
        case_id_column="id",
        **CONTEXT,
        value_add_convention="right-first-time work",
    )
    restored = AnalysisBundle.from_dict(
        AnalysisBundle(name="prepared preview", results=[result]).to_dict()
    )
    assert restored.results[0].to_dict() == result.to_dict()


@pytest.mark.parametrize("values", [[0.0, 0.0], [float("nan"), 1.0], [float("inf"), 1.0]])
def test_invalid_pce_denominators_fail(frame_factory, values):
    with pytest.raises(ValidationError):
        process_cycle_efficiency(
            frame_factory({"id": ["A", "B"], "lead": values, "va": [0.0, 0.0]}),
            aggregation="cohort",
            case_id_column="id",
            lead_time_column="lead",
            value_add_time_column="va",
            **CONTEXT,
            value_add_convention="VA",
        )


def test_numeric_boundaries_cannot_enter_calendar_timing(frame_factory):
    with pytest.raises(ValidationError, match="invalid timestamps"):
        lead_time(
            frame_factory({"start": [12.1], "end": [178.4]}),
            start_column="start",
            end_column="end",
            unit="minutes",
        )


@pytest.fixture
def pinned_results(frame_factory):
    """Execute real public methods on the pinned prepared cases and explicit selection."""
    columns = json.loads((FIXTURE / "inputs.json").read_text())["columns"]
    contract = replace(
        CONTRACT,
        case_id_column="Order ID",
        arrival_column="Arrival (elapsed min)",
        readiness_column="Ready and notified (elapsed min)",
        lead_time_column="Operating L/T (min)",
        value_add_time_column="VA time (min)",
        processing_time_column="Total P/T (min)",
        wait_time_column="Total W/T (min)",
        setup_time_column="Total S/T (min)",
    )
    data = frame_factory(columns)
    report = validate_order_summary(data, contract=contract)
    all_orders = describe(data, column=contract.lead_time_column, unit="minutes", missing="raise")
    selection = [i for i, a in enumerate(columns[contract.arrival_column]) if a <= 120]
    eligible = frame_factory({k: [v[i] for i in selection] for k, v in columns.items()})
    tail = describe(eligible, column=contract.lead_time_column, percentile_method="nearest_rank")
    promise = deadline_performance(
        data,
        case_id_column=contract.case_id_column,
        arrival_column=contract.arrival_column,
        readiness_column=contract.readiness_column,
        eligibility_cutoff=120,
        deadline=600,
        **CONTEXT,
    )
    pce = process_cycle_efficiency(
        data,
        case_id_column=contract.case_id_column,
        lead_time_column=contract.lead_time_column,
        value_add_time_column=contract.value_add_time_column,
        aggregation="cohort",
        **CONTEXT,
        value_add_convention=contract.value_add_convention,
    )
    return report, all_orders, tail, promise, pce


def test_pinned_fixture_summary_uses_actual_public_methods(pinned_results):
    report, all_orders, tail, _, _ = pinned_results
    assert report.valid
    assert f"{all_orders.mean:.1f}" == "662.6"
    assert all_orders.measurement_sum == pytest.approx(25840.5)
    assert tail.percentiles is not None
    assert tail.percentiles["p90"] == 676.2


def test_pinned_fixture_promise_and_pce_use_actual_public_methods(pinned_results):
    _, _, _, promise, pce = pinned_results
    assert (promise.numerator, promise.denominator) == (6, 21)
    assert f"{pce.values[0]:.1f}" == "13.7"


@pytest.mark.parametrize(
    "fields",
    [
        {"clock": " "},
        {"unit": "weeks"},
        {"readiness_column": "arrival"},
        {"processing_time_column": None},
        {"tolerance": float("nan")},
        {"tolerance": True},
        {"tolerance": -1},
        {"tolerance": 10**400},
    ],
)
def test_invalid_order_declarations_fail_before_inspection(frame_factory, fields):
    with pytest.raises(ValidationError):
        replace(CONTRACT, **fields)


def test_unknown_order_contract_fields_and_empty_population(frame_factory):
    with pytest.raises(ValidationError, match="fields"):
        OrderSummaryContract.from_dict({**CONTRACT.to_dict(), "hidden_policy": True})
    report = validate_order_summary(
        frame_factory({key: [] for key in observations()}), contract=CONTRACT
    )
    assert not report.valid
    assert any(i.code == "EMPTY_COHORT" for i in report.errors)


def test_nearest_rank_avoids_float_position_rounding(frame_factory):
    result = describe(
        frame_factory({"x": list(range(25))}),
        column="x",
        percentile_method="nearest_rank",
        percentiles=[28],
    )
    assert result.percentiles is not None
    # ceil(0.28*25)=7 mathematically, even when float multiplication exceeds 7 slightly.
    assert result.percentiles["p28"] == 6
