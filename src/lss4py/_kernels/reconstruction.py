"""Reconstruct complete serial orders with explicit parallel activity accounting."""

import json
from collections import defaultdict
from math import fsum, isclose

from lss4py._frames import eager_frame
from lss4py._kernels._helpers import build_provenance
from lss4py.domain.numeric_log import NumericEventLog
from lss4py.domain.reconstruction import OrderReconstructionPolicy
from lss4py.domain.results import OrderReconstructionResult
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis


@register_analysis(
    AnalysisSuitability(
        name="reconstruct_orders",
        outcome_types=("numeric_activity_endpoint",),
        predictor_types=("none",),
        sampling_requirements=(
            "Caller declares a comparable population; no random sampling is inferred.",
        ),
        family="timing",
        question_tags=("reconstruct_orders",),
        required_fields=(("numeric_activity_log", "policy"),),
        data_types=("numeric_activity_log",),
        design_types=("observational",),
        belt_level="white",
        prerequisites=("Four complete ordered numeric endpoints per activity occurrence.",),
        assumptions=("The declared activity envelopes partition each serial order path.",),
        alternatives=("describe",),
        limits=("No lifecycle pairing, arbitrary branch inference, or calendar conversion.",),
    )
)
def reconstruct_orders(
    log: NumericEventLog, *, policy: OrderReconstructionPolicy
) -> OrderReconstructionResult:
    """Reconstruct every supplied order or fail with case and source-row evidence.

    Boundaries are first arrival queue entry and final readiness work end.
    Repeated passes remain distinct. Parallel activity/pass groups collapse to
    min(queue), min(setup), max(start), max(end). Other groups remain singular.
    Adjacent envelopes must meet without gaps or overlaps; no rows are excluded.
    Output retains full floating precision; round only for presentation.
    """
    _check_input(log, policy)
    contract = log.contract
    case_columns = (*contract.scope_columns, contract.case_id_column)
    cases: dict[tuple, list] = defaultdict(list)
    for position, row in enumerate(log.frame.to_dicts()):
        cases[tuple(row[c] for c in case_columns)].append((position, row))
    orders, activities = [], []
    for key, records in cases.items():
        identity = dict(zip(case_columns, key, strict=True))
        collapsed = _collapse_case(records, log, policy, identity)
        orders.append(_summarize(collapsed, records, identity, log, policy))
        activities.extend(collapsed)
    parameters = {"contract": contract.to_dict(), "policy": policy.to_dict()}
    provenance = build_provenance("reconstruct_orders", eager_frame(log.frame), parameters)
    provenance.cohort_definition = policy.cohort
    activity_records = _source_timings(log, policy)
    return OrderReconstructionResult(
        name="Reconstructed complete orders",
        provenance=provenance,
        interpretation_context="Declared serial path and parallel envelope accounting.",
        metadata={
            "orders": orders,
            "activities": activities,
            "activity_records": activity_records,
            "source_records": log.frame.to_dicts(),
            "source": json.loads(json.dumps(log.metadata)),
            "table_columns": {
                "orders": list(orders[0]),
                "activities": list(activities[0]),
                "activity_records": list(activity_records[0]),
                "source_records": log.frame.columns,
            },
            "exclusions": [],
            "unit": contract.unit,
            "clock": contract.clock,
            "boundary": contract.boundary,
            "correction_occurrences": sum(o["correction_occurrences"] for o in orders),
            "affected_orders": sum(o["correction_occurrences"] > 0 for o in orders),
        },
    )


def _check_input(log: NumericEventLog, policy: OrderReconstructionPolicy) -> None:
    """Revalidate mutable frame contents and the supported endpoint contract."""
    if not isinstance(log, NumericEventLog) or not isinstance(policy, OrderReconstructionPolicy):
        raise ValidationError("NumericEventLog and OrderReconstructionPolicy are required.")
    NumericEventLog(log.frame, log.contract)
    if len(log.contract.time_columns) != 4 or not log.height:
        raise ValidationError("Reconstruction requires nonempty four-endpoint activity records.")
    if policy.rework_column not in log.frame.columns:
        raise ValidationError(f"Missing rework column: {policy.rework_column}")
    _check_columns(log, policy)
    flags = log.frame[policy.rework_column].to_list()
    if any(v not in (policy.rework_value, policy.non_rework_value) for v in flags):
        raise ValidationError("Unrecognized or missing rework flag; declare both accepted values.")


def _collapse_case(records: list, log, policy, identity: dict) -> list[dict]:
    """Preserve activity/pass identity and its original source positions."""
    c = log.contract
    groups: dict[tuple, list] = defaultdict(list)
    for position, row in records:
        groups[(row[c.activity_column], row[c.pass_column])].append((position, row))
    required = {*policy.required_activities, policy.arrival_activity, policy.readiness_activity}
    if missing := required - {k[0] for k in groups}:
        raise ValidationError(f"Incomplete order {identity}: missing activities {sorted(missing)}")
    return [_collapse_group(key, rows, log, policy, identity) for key, rows in groups.items()]


def _collapse_group(key: tuple, records: list, log, policy, identity: dict) -> dict:
    """Compute one elapsed envelope while keeping machine effort out of elapsed totals."""
    activity, occurrence = key
    c = log.contract
    positions, rows = zip(*records, strict=True)
    _check_group(activity, rows, positions, log, policy)
    q, setup, start, end = _envelope(rows, c.time_columns)
    right_first_time = all(row[policy.rework_column] == policy.non_rework_value for row in rows)
    classification = _classification(activity, right_first_time, policy)
    return {
        **identity,
        "activity": activity,
        "pass": occurrence,
        "queue": q,
        "setup_start": setup,
        "work_start": start,
        "work_end": end,
        "processing": end - start,
        "waiting": setup - q,
        "setup": start - setup,
        "value_add": end - start if classification == "VA" else 0,
        "processing_class": classification,
        "right_first_time": right_first_time,
        "source_positions": list(positions),
        "load_ids": [row[c.load_id_column] for row in rows] if c.load_id_column else [],
    }


def _summarize(activities: list, records: list, identity: dict, log, policy) -> dict:
    """Verify complete boundary coverage before totaling one case's elapsed components."""
    arrival = min(a["queue"] for a in activities if a["activity"] == policy.arrival_activity)
    ready = max(a["work_end"] for a in activities if a["activity"] == policy.readiness_activity)
    path = sorted(activities, key=lambda a: (a["queue"], a["work_end"]))
    _check_path(path, arrival, ready, identity, policy.tolerance)
    totals = _totals(activities)
    corrections = _correction_count(activities, policy.correction_activity)
    return {
        **identity,
        "arrival": arrival,
        "readiness": ready,
        "lead_time": ready - arrival,
        **totals,
        "activity_records": len(records),
        "correction_occurrences": corrections,
    }


def _check_path(path: list, arrival: float, ready: float, identity: dict, tolerance: float) -> None:
    """Reject gaps, overlaps, and records beyond declared boundaries with source evidence."""
    cursor = arrival
    for activity in path:
        if not isclose(activity["queue"], cursor, rel_tol=0, abs_tol=tolerance):
            raise ValidationError(
                f"Gap/overlap in order {identity}; rows={activity['source_positions']}; "
                f"expected queue={cursor}, observed={activity['queue']}"
            )
        cursor = activity["work_end"]
    if not isclose(cursor, ready, rel_tol=0, abs_tol=tolerance):
        raise ValidationError(f"Records outside readiness boundary for order {identity}.")


def _totals(activities: list) -> dict:
    """Sum elapsed components of validated serial envelopes at full precision."""
    return {
        name: fsum(a[name] for a in activities)
        for name in ("processing", "waiting", "setup", "value_add")
    }


def _envelope(rows: tuple, columns: tuple) -> tuple:
    """Apply the declared min/min/max/max accounting convention."""
    reducers = (min, min, max, max)
    times = tuple(op(row[col] for row in rows) for op, col in zip(reducers, columns, strict=True))
    q, setup, start, end = times
    if not q <= setup <= start <= end:
        raise ValidationError("Invalid collapsed endpoint ordering.")
    return times


def _check_columns(log, policy) -> None:
    """Protect fixed output names and optional expected load-count bindings."""
    reserved = {
        "arrival",
        "readiness",
        "lead_time",
        "processing",
        "waiting",
        "setup",
        "value_add",
        "activity_records",
        "correction_occurrences",
        "activity",
        "pass",
        "queue",
        "setup_start",
        "work_start",
        "work_end",
        "right_first_time",
        "source_positions",
        "load_ids",
        "processing_class",
    }
    keys = {*log.contract.scope_columns, log.contract.case_id_column}
    if keys & reserved:
        raise ValidationError("Case/scope columns collide with reserved reconstruction fields.")
    column = policy.parallel_load_count_column
    if column is not None and column not in log.frame.columns:
        raise ValidationError(f"Missing expected load count column: {column}")


def _check_group(activity: str, rows: tuple, positions: tuple, log, policy) -> None:
    """Reject ambiguous multiplicity and incomplete parallel groups."""
    if activity not in policy.parallel_activities:
        if len(rows) != 1:
            raise ValidationError(f"Ambiguous nonparallel activity {activity}; rows={positions}")
        return
    column = log.contract.load_id_column
    if column is None or any(row[column] is None for row in rows):
        raise ValidationError(
            f"Parallel activity requires explicit load identities; rows={positions}"
        )
    _check_load_count(rows, policy.parallel_load_count_column, positions)


def _check_load_count(rows: tuple, column: str | None, positions: tuple) -> None:
    """Check declared expected parallel cardinality without inferring it from observed rows."""
    if column is None:
        return
    counts = [row[column] for row in rows]
    if any(type(v) is not int or v < 1 for v in counts):
        raise ValidationError(f"Expected load count must be a positive integer; rows={positions}")
    if set(counts) != {len(rows)}:
        raise ValidationError(
            f"Incomplete parallel load group; rows={positions}; expected={counts}"
        )


def _correction_count(activities: list, correction_activity: str) -> int:
    """Count distinct singular correction passes independently of trigger flags."""
    return sum(a["activity"] == correction_activity for a in activities)


def _classification(activity: str, right_first_time: bool, policy) -> str:
    """Classify processing only; failed attempts and all other activities are NVA."""
    if not right_first_time:
        return "NVA"
    if activity in policy.value_add_activities:
        return "VA"
    if activity in policy.required_non_value_add_activities:
        return "RNVA"
    return "NVA"


def _source_timings(log, policy) -> list[dict]:
    """Retain each source record's own durations before any parallel collapse."""
    c = log.contract
    keys = (*c.scope_columns, c.case_id_column, c.activity_column, c.pass_column)
    return [
        _source_timing(position, row, keys, c, policy)
        for position, row in enumerate(log.frame.to_dicts())
    ]


def _source_timing(position: int, row: dict, keys: tuple, contract, policy) -> dict:
    """Compute one activity observation on its declared numeric operating clock."""
    q, setup, start, end = (row[col] for col in contract.time_columns)
    result = {key: row[key] for key in keys}
    if contract.load_id_column:
        result[contract.load_id_column] = row[contract.load_id_column]
    return {
        **result,
        "source_position": position,
        "processing": end - start,
        "waiting": setup - q,
        "setup": start - setup,
        "processing_class": _classification(
            row[contract.activity_column],
            row[policy.rework_column] == policy.non_rework_value,
            policy,
        ),
    }
