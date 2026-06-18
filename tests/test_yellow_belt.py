from typing import Literal

import pandas as pd
import pytest

from lss4py import (
    EventLogBindingsIR,
    LeadTimeBindingIR,
    MetricBindingsIR,
    MetricSemanticsIR,
    ProcessEdgeIR,
    ProcessModelIR,
    ProcessStepIR,
    StageBindingsIR,
    booked_to_completed_yield,
    created_to_booked_yield,
    lead_time,
    process_cycle_efficiency,
    rolled_yield,
    takt_time,
    wait_time,
)
from lss4py.errors import ValidationError


def _sample_process_model_ir() -> ProcessModelIR:
    return ProcessModelIR(
        name="Client intake",
        edges=[
            ProcessEdgeIR(source_step_id="review", target_step_id="approve", kind="sequence"),
            ProcessEdgeIR(source_step_id="approve", target_step_id="review", kind="rework"),
        ],
        bindings=MetricBindingsIR(
            lead_time=LeadTimeBindingIR(
                start_column="created_at",
                end_column="completed_at",
            ),
            stages=StageBindingsIR(
                created="created",
                booked="booked",
                completed="completed",
            ),
        ),
        metric_semantics=MetricSemanticsIR(parallel_timing="critical_path"),
        steps=[
            ProcessStepIR(
                id="review",
                name="review",
                cycle_time_column="review_hours",
                value_classification="non_value_add",
            ),
            ProcessStepIR(
                id="approve",
                name="approval",
                cycle_time_column="approval_hours",
                value_classification="value_add",
            ),
        ],
    )


def _sample_event_log_process_model_ir(
    *,
    parallel_timing: Literal["critical_path", "sum_all_branches"] = "critical_path",
) -> ProcessModelIR:
    return ProcessModelIR(
        name="Parallel intake",
        edges=[
            ProcessEdgeIR(
                source_step_id="intake",
                target_step_id="review_a",
                kind="parallel_split",
            ),
            ProcessEdgeIR(
                source_step_id="intake",
                target_step_id="review_b",
                kind="parallel_split",
            ),
            ProcessEdgeIR(
                source_step_id="review_a",
                target_step_id="approve",
                kind="parallel_join",
            ),
            ProcessEdgeIR(
                source_step_id="review_b",
                target_step_id="approve",
                kind="parallel_join",
            ),
            ProcessEdgeIR(source_step_id="approve", target_step_id="review_a", kind="rework"),
        ],
        bindings=MetricBindingsIR(
            lead_time=LeadTimeBindingIR(unit="hours"),
            event_log=EventLogBindingsIR(
                case_id_column="case_id",
                step_id_column="step_id",
                started_at_column="started_at",
                completed_at_column="completed_at",
            ),
        ),
        metric_semantics=MetricSemanticsIR(parallel_timing=parallel_timing),
        steps=[
            ProcessStepIR(id="intake", name="Intake", value_classification="non_value_add"),
            ProcessStepIR(id="review_a", name="Review A", value_classification="value_add"),
            ProcessStepIR(id="review_b", name="Review B", value_classification="non_value_add"),
            ProcessStepIR(id="approve", name="Approve", value_classification="value_add"),
        ],
    )


def _sample_parallel_event_log() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": ["C1", "C1", "C1", "C1"],
            "step_id": ["intake", "review_a", "review_b", "approve"],
            "started_at": [
                "2026-01-01T08:00:00",
                "2026-01-01T10:00:00",
                "2026-01-01T10:00:00",
                "2026-01-01T13:00:00",
            ],
            "completed_at": [
                "2026-01-01T09:00:00",
                "2026-01-01T12:00:00",
                "2026-01-01T11:00:00",
                "2026-01-01T14:00:00",
            ],
        }
    )


def test_process_model_ir_supports_explicit_graph_edges_and_bindings() -> None:
    process_model = _sample_process_model_ir()

    assert process_model.schema_version == "1.0"
    assert process_model.metric_semantics.parallel_timing == "critical_path"
    assert process_model.bindings.lead_time.start_column == "created_at"
    assert process_model.edges[0].kind == "sequence"
    assert process_model.edges[1].kind == "rework"


def test_lead_time_computes_hours_from_timestamps() -> None:
    data = pd.DataFrame(
        {
            "created_at": ["2026-01-01T08:00:00", "2026-01-02T09:15:00"],
            "completed_at": ["2026-01-01T11:00:00", "2026-01-02T10:45:00"],
        }
    )

    result = lead_time(data, start_column="created_at", end_column="completed_at")

    assert result.tolist() == [3.0, 1.5]


def test_wait_time_and_process_cycle_efficiency_use_explicit_columns() -> None:
    data = pd.DataFrame(
        {
            "lead_time_hours": [10.0, 5.0],
            "cycle_time_hours": [4.0, 1.0],
            "value_add_hours": [3.0, 1.0],
        }
    )

    wait_result = wait_time(
        data,
        lead_time_column="lead_time_hours",
        cycle_time_column="cycle_time_hours",
    )
    pce_result = process_cycle_efficiency(
        data,
        lead_time_column="lead_time_hours",
        value_add_time_column="value_add_hours",
    )

    assert wait_result.tolist() == [6.0, 4.0]
    assert pce_result.tolist() == [30.0, 20.0]


def test_metrics_can_resolve_columns_from_process_model_ir() -> None:
    process_model = _sample_process_model_ir()
    data = pd.DataFrame(
        {
            "created_at": ["2026-01-01T08:00:00", "2026-01-02T09:00:00"],
            "completed_at": ["2026-01-01T18:00:00", "2026-01-02T15:00:00"],
            "review_hours": [2.0, 1.0],
            "approval_hours": [1.0, 2.0],
        }
    )

    lead_result = lead_time(data, process_model=process_model)
    wait_result = wait_time(data, process_model=process_model)
    pce_result = process_cycle_efficiency(data, process_model=process_model)

    assert lead_result.tolist() == [10.0, 6.0]
    assert wait_result.tolist() == [7.0, 3.0]
    assert pce_result.tolist() == [10.0, pytest.approx(33.33333333333333)]


def test_event_log_metrics_use_parallel_critical_path_semantics() -> None:
    process_model = _sample_event_log_process_model_ir(parallel_timing="critical_path")
    data = _sample_parallel_event_log()

    lead_result = lead_time(data, process_model=process_model)
    wait_result = wait_time(data, process_model=process_model)
    pce_result = process_cycle_efficiency(data, process_model=process_model)

    assert lead_result.to_dict() == {"C1": 6.0}
    assert wait_result.to_dict() == {"C1": 2.0}
    assert pce_result.to_dict() == {"C1": 50.0}


def test_event_log_metrics_can_sum_parallel_branch_work() -> None:
    process_model = _sample_event_log_process_model_ir(parallel_timing="sum_all_branches")
    data = _sample_parallel_event_log()

    wait_result = wait_time(data, process_model=process_model)
    pce_result = process_cycle_efficiency(data, process_model=process_model)

    assert wait_result.to_dict() == {"C1": 1.0}
    assert pce_result.to_dict() == {"C1": 50.0}


def test_event_log_metrics_allow_rework_when_rework_edge_is_defined() -> None:
    process_model = _sample_event_log_process_model_ir(parallel_timing="critical_path")
    data = pd.DataFrame(
        {
            "case_id": ["C2", "C2", "C2", "C2"],
            "step_id": ["intake", "review_a", "approve", "review_a"],
            "started_at": [
                "2026-01-01T08:00:00",
                "2026-01-01T09:00:00",
                "2026-01-01T10:00:00",
                "2026-01-01T11:00:00",
            ],
            "completed_at": [
                "2026-01-01T09:00:00",
                "2026-01-01T10:00:00",
                "2026-01-01T11:00:00",
                "2026-01-01T12:00:00",
            ],
        }
    )

    lead_result = lead_time(data, process_model=process_model)
    wait_result = wait_time(data, process_model=process_model)

    assert lead_result.to_dict() == {"C2": 4.0}
    assert wait_result.to_dict() == {"C2": 0.0}


def test_event_log_metrics_reject_overlap_without_parallel_edges() -> None:
    process_model = ProcessModelIR(
        name="Sequential only",
        bindings=MetricBindingsIR(
            lead_time=LeadTimeBindingIR(unit="hours"),
            event_log=EventLogBindingsIR(
                case_id_column="case_id",
                step_id_column="step_id",
                started_at_column="started_at",
                completed_at_column="completed_at",
            ),
        ),
        steps=[
            ProcessStepIR(id="review_a", name="Review A", value_classification="value_add"),
            ProcessStepIR(id="review_b", name="Review B", value_classification="value_add"),
        ],
    )
    data = pd.DataFrame(
        {
            "case_id": ["C3", "C3"],
            "step_id": ["review_a", "review_b"],
            "started_at": ["2026-01-01T09:00:00", "2026-01-01T09:30:00"],
            "completed_at": ["2026-01-01T10:00:00", "2026-01-01T10:30:00"],
        }
    )

    with pytest.raises(ValidationError, match="explicit parallel edges"):
        wait_time(data, process_model=process_model)


def test_event_log_metrics_reject_repeat_without_rework_edge() -> None:
    process_model = ProcessModelIR(
        name="No rework",
        bindings=MetricBindingsIR(
            lead_time=LeadTimeBindingIR(unit="hours"),
            event_log=EventLogBindingsIR(
                case_id_column="case_id",
                step_id_column="step_id",
                started_at_column="started_at",
                completed_at_column="completed_at",
            ),
        ),
        steps=[
            ProcessStepIR(id="review_a", name="Review A", value_classification="value_add"),
        ],
    )
    data = pd.DataFrame(
        {
            "case_id": ["C4", "C4"],
            "step_id": ["review_a", "review_a"],
            "started_at": ["2026-01-01T09:00:00", "2026-01-01T10:00:00"],
            "completed_at": ["2026-01-01T10:00:00", "2026-01-01T11:00:00"],
        }
    )

    with pytest.raises(ValidationError, match="does not define a rework edge"):
        lead_time(data, process_model=process_model)


def test_takt_time_divides_available_time_by_customer_demand() -> None:
    assert takt_time(available_time=420.0, customer_demand=84.0) == 5.0


def test_lead_time_rejects_negative_durations() -> None:
    data = pd.DataFrame(
        {
            "created_at": ["2026-01-01T11:00:00"],
            "completed_at": ["2026-01-01T08:00:00"],
        }
    )

    with pytest.raises(ValidationError, match="Lead time cannot be negative"):
        lead_time(data, start_column="created_at", end_column="completed_at")


def test_wait_time_rejects_cycle_time_longer_than_lead_time() -> None:
    data = pd.DataFrame({"lead_time_hours": [2.0], "cycle_time_hours": [3.0]})

    with pytest.raises(ValidationError, match="Wait time cannot be negative"):
        wait_time(data, lead_time_column="lead_time_hours", cycle_time_column="cycle_time_hours")


def test_takt_time_requires_positive_customer_demand() -> None:
    with pytest.raises(ValidationError, match="Customer demand must be greater than zero"):
        takt_time(available_time=420.0, customer_demand=0.0)


def test_yield_helpers_compute_stage_and_rolled_yields() -> None:
    data = pd.DataFrame(
        {
            "created": [1, 1, 1, 1, 1],
            "booked": [1, 1, 0, 1, 0],
            "completed": [1, 0, 0, 1, 0],
        }
    )

    created_booked = created_to_booked_yield(
        data,
        created_column="created",
        booked_column="booked",
    )
    booked_completed = booked_to_completed_yield(
        data,
        booked_column="booked",
        completed_column="completed",
    )
    rolled = rolled_yield(
        data,
        created_column="created",
        booked_column="booked",
        completed_column="completed",
    )

    assert created_booked == 60.0
    assert booked_completed == pytest.approx(66.66666666666666)
    assert rolled == 40.0


def test_yield_helpers_can_resolve_stage_columns_from_process_model_ir() -> None:
    process_model = _sample_process_model_ir()
    data = pd.DataFrame(
        {
            "created": [1, 1, 1, 1, 1],
            "booked": [1, 1, 0, 1, 0],
            "completed": [1, 0, 0, 1, 0],
        }
    )

    created_booked = created_to_booked_yield(data, process_model=process_model)
    booked_completed = booked_to_completed_yield(data, process_model=process_model)
    rolled = rolled_yield(data, process_model=process_model)

    assert created_booked == 60.0
    assert booked_completed == pytest.approx(66.66666666666666)
    assert rolled == 40.0


def test_yield_helpers_reject_non_binary_stage_values() -> None:
    data = pd.DataFrame({"created": [1, 1], "booked": [1, 2]})

    with pytest.raises(ValidationError, match="binary stage values"):
        created_to_booked_yield(data, created_column="created", booked_column="booked")


def test_yield_helpers_reject_stage_progression_that_exceeds_prior_stage() -> None:
    data = pd.DataFrame(
        {
            "booked": [1, 0],
            "completed": [1, 1],
        }
    )

    with pytest.raises(ValidationError, match="cannot exceed column 'booked'"):
        booked_to_completed_yield(
            data,
            booked_column="booked",
            completed_column="completed",
        )


def test_yield_helpers_require_at_least_one_stage_opportunity() -> None:
    data = pd.DataFrame({"created": [0, 0], "booked": [0, 0]})

    with pytest.raises(ValidationError, match="must contain at least one stage opportunity"):
        created_to_booked_yield(data, created_column="created", booked_column="booked")


def test_process_model_ir_must_define_required_mappings_for_derived_metrics() -> None:
    process_model = ProcessModelIR(name="Incomplete model")
    data = pd.DataFrame(
        {
            "created_at": ["2026-01-01T08:00:00"],
            "completed_at": ["2026-01-01T09:00:00"],
        }
    )

    with pytest.raises(ValidationError, match="Lead time requires explicit start/end columns"):
        lead_time(data, process_model=process_model)
