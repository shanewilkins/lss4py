"""Validate prepared order observations and evaluate a declared fixed deadline."""

from dataclasses import replace
from math import isfinite
from typing import Any

import numpy as np

from lss4py._frames import eager_frame
from lss4py._kernels._helpers import build_provenance, measurement_values
from lss4py._kernels.data_quality import validate_data
from lss4py.domain import ColumnRule, DataContract, DataIssue, DataValidationReport, YieldResult
from lss4py.domain.order_summary import OrderSummaryContract
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis


def case_measurements(data: Any, case_id_column: str, columns: tuple[str, ...], unit: str):
    """Inspect finite nonnegative numeric observations and unique explicit string keys."""
    contract = DataContract(
        columns=(ColumnRule(case_id_column, kind="string"),)
        + tuple(ColumnRule(name, minimum=0, unit=unit) for name in columns),
        key_columns=(case_id_column,),
        duplicates="error",
    )
    return validate_data(data, contract=contract)


def require_valid(report: DataValidationReport) -> None:
    """Fail with source-row findings rather than silently excluding invalid observations."""
    if not report.valid:
        details = "; ".join(f"{i.code}: {i.message}; rows={list(i.rows)}" for i in report.errors)
        raise ValidationError(details)


def validate_order_summary(data: Any, *, contract: OrderSummaryContract) -> DataValidationReport:
    """Inspect prepared numeric orders without changing inputs or reconstructing events.

    Checks unique cases, complete finite nonnegative observations, readiness >=
    arrival, lead = readiness - arrival, VA <= lead, and optional P/T+W/T+S/T =
    lead. No records are excluded. The report's numeric schema is complemented by
    the supplied OrderSummaryContract, which must be retained with the analysis.
    """
    if not isinstance(contract, OrderSummaryContract):
        raise ValidationError("contract must be an OrderSummaryContract.")
    report = case_measurements(data, contract.case_id_column, contract.time_columns, contract.unit)
    if report.row_count == 0:
        issue = DataIssue("EMPTY_COHORT", "error", "No order observations were supplied.")
        return replace(report, issues=(*report.issues, issue))
    if not report.valid:
        return report
    frame = eager_frame(data)
    values = {name: measurement_values(frame, name) for name in contract.time_columns}
    conditions = _order_checks(contract, values)
    return _order_report(report, conditions)


def _order_checks(contract: OrderSummaryContract, values: dict) -> list:
    """Build numeric endpoint, VA and optional component comparisons."""
    arrival, ready = values[contract.arrival_column], values[contract.readiness_column]
    lead, va = values[contract.lead_time_column], values[contract.value_add_time_column]
    conditions: list[tuple[str, np.ndarray, tuple[str, ...], str]] = [
        (
            "ORDERING",
            ready < arrival,
            (contract.arrival_column, contract.readiness_column),
            "Readiness precedes arrival.",
        ),
        (
            "LEAD_TIME_MISMATCH",
            ~np.isclose(ready - arrival, lead, atol=contract.tolerance, rtol=0),
            (contract.arrival_column, contract.readiness_column, contract.lead_time_column),
            "Prepared lead time differs from readiness minus arrival.",
        ),
        (
            "VA_EXCEEDS_LEAD",
            va > lead,
            (contract.value_add_time_column, contract.lead_time_column),
            "Value-added time exceeds lead time.",
        ),
    ]
    if contract.processing_time_column is not None:
        conditions.append(_partition_check(contract, values))
    return conditions


def _partition_check(contract: OrderSummaryContract, values: dict) -> tuple:
    """Compare the declared complete processing/wait/setup partition with lead time."""
    names = contract.time_columns[4:]
    components = sum(values[name] for name in names)
    return (
        "TIMING_PARTITION_MISMATCH",
        ~np.isclose(components, values[contract.lead_time_column], atol=contract.tolerance, rtol=0),
        (*names, contract.lead_time_column),
        "Processing plus waiting plus setup differs from lead time.",
    )


def _order_report(report: DataValidationReport, conditions: list) -> DataValidationReport:
    """Attach source positions to relational findings without excluding observations."""
    issues = list(report.issues)
    for code, mask, columns, message in conditions:
        positions = tuple(int(i) for i in np.flatnonzero(mask))
        if positions:
            issues.append(DataIssue(code, "error", message, columns, positions))
    return replace(report, issues=tuple(issues))


def semantic_context(
    unit: str | None, clock: str | None, boundary: str | None, cohort: str | None
) -> dict:
    """Validate and expose the shared measurement context without inferring meaning."""
    if unit not in ("seconds", "minutes", "hours", "days"):
        raise ValidationError("unit must be seconds, minutes, hours, or days.")
    context = {"clock": clock, "boundary": boundary, "cohort": cohort, "input_unit": unit}
    if any(not isinstance(v, str) or not v.strip() for v in context.values()):
        raise ValidationError("Clock, boundary, and cohort must be explicit nonblank declarations.")
    return context


@register_analysis(
    AnalysisSuitability(
        name="deadline_performance",
        outcome_types=("numeric_operating_endpoint",),
        predictor_types=("none",),
        sampling_requirements=(
            "Caller declares a comparable population; no random sampling is inferred.",
        ),
        family="timing",
        question_tags=("fixed_deadline",),
        required_fields=(("case_id_column", "arrival_column", "readiness_column"),),
        data_types=("numeric",),
        design_types=("observational",),
        belt_level="white",
        prerequisites=(
            "Unique cases and complete numeric arrivals/readiness on one declared clock.",
        ),
        assumptions=(
            "The declared eligibility cutoff and fixed deadline represent the customer promise.",
        ),
        alternatives=("describe",),
        limits=(
            "A fixed readiness deadline differs from a lead-time allowance; no causal inference.",
        ),
    )
)
def deadline_performance(
    data: Any,
    *,
    case_id_column: str,
    arrival_column: str,
    readiness_column: str,
    eligibility_cutoff: float,
    deadline: float,
    unit: str,
    clock: str,
    boundary: str,
    cohort: str,
) -> YieldResult:
    """Return fixed-deadline miss fraction, counts, and distinct case populations.

    Eligibility is arrival <= cutoff; a miss is eligible readiness > deadline.
    Deadline equality is on time. Invalid/incomplete cases and an empty eligible
    denominator raise ValidationError; no observations are silently dropped.
    Numeric endpoints are never parsed as calendar timestamps.
    """
    context = semantic_context(unit, clock, boundary, cohort)
    for value in (eligibility_cutoff, deadline):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValidationError("Cutoff and deadline must be finite numeric values.")
        if value < 0:
            raise ValidationError("Cutoff and deadline must be nonnegative.")
    report = case_measurements(data, case_id_column, (arrival_column, readiness_column), unit)
    require_valid(report)
    frame = eager_frame(data)
    arrival, ready = (measurement_values(frame, col) for col in (arrival_column, readiness_column))
    if np.any(ready < arrival):
        raise ValidationError("Readiness precedes arrival.")
    eligible = arrival <= eligibility_cutoff
    missed = eligible & (ready > deadline)
    denominator = int(eligible.sum())
    if not denominator:
        raise ValidationError("No eligible orders; deadline miss rate is undefined.")
    ids = frame[case_id_column].to_list()

    def selected(mask):
        """Preserve explicit case identity in source order, independent of a dataframe index."""
        return [key for key, keep in zip(ids, mask, strict=True) if keep]

    metadata = {
        **context,
        "observation_count": len(ids),
        "eligible_count": denominator,
        "miss_count": int(missed.sum()),
        "ineligible_count": int((~eligible).sum()),
        "eligible_cases": selected(eligible),
        "missed_cases": selected(missed),
        "on_time_cases": selected(eligible & ~missed),
        "ineligible_cases": selected(~eligible),
        "exclusions": [],
        "eligibility_comparison": "arrival <= cutoff",
        "miss_comparison": "eligible readiness > deadline",
    }
    parameters = {
        **context,
        "case_id_column": case_id_column,
        "arrival_column": arrival_column,
        "readiness_column": readiness_column,
        "eligibility_cutoff": eligibility_cutoff,
        "deadline": deadline,
        "missing": "raise",
    }
    provenance = build_provenance("deadline_performance", frame, parameters)
    provenance.cohort_definition = cohort
    return YieldResult(
        name="Fixed deadline miss rate",
        provenance=provenance,
        value=int(missed.sum()) / denominator,
        unit="fraction",
        numerator=int(missed.sum()),
        denominator=denominator,
        method="fixed_deadline",
        metadata=metadata,
        interpretation_context=(
            "Observed miss rate among eligible cases; "
            "ineligible cases are distinct from on-time cases."
        ),
    )
