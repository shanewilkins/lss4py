"""Explicit direct-follow discovery from a single-time event stream."""

import hashlib
import platform
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from lss4py._version import __version__
from lss4py.domain import AssumptionNote, EventStream, Provenance
from lss4py.domain.results import ProcessMapResult
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis


def _parse_timestamp(value: Any) -> datetime:
    """Parse declared calendar instants without numeric/date-only coercion."""
    if isinstance(value, str) and ("T" in value or " " in value):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        raise ValidationError("Event timestamps must be datetime objects or ISO date/time strings.")
    return value.astimezone(UTC) if value.tzinfo is not None else value


@register_analysis(
    AnalysisSuitability(
        name="map_process",
        family="process_discovery",
        question_tags=("direct_follow_discovery",),
        required_fields=(("case_id", "activity", "timestamp"),),
        data_types=("event_stream",),
        design_types=("observational",),
        belt_level="white",
        prerequisites=("Explicit case, activity and single-time calendar observations.",),
        assumptions=("Timestamp order represents the observed direct-follow sequence.",),
        alternatives=("reconstruct_orders",),
        limits=("Direct-follow counts do not infer causal, parallel or rework topology.",),
        outcome_types=("categorical_activity_and_calendar_time",),
        predictor_types=("none",),
        sampling_requirements=(
            "Caller declares the event population; tie order remains source order.",
        ),
    )
)
def map_process(event_log: EventStream) -> ProcessMapResult:
    """Discover nodes and direct-follow counts with typed evidence and stable tie order."""
    grouped, evidence = _events(event_log)
    nodes: set[str] = set()
    edges: dict[str, dict[str, int]] = {}
    for events in grouped.values():
        try:
            ordered = sorted(events, key=lambda e: e[0])
        except TypeError as exc:
            raise ValidationError(
                "Event timestamps require consistent timezone awareness."
            ) from exc
        nodes.update(activity for _, activity in ordered)
        for current, following in zip(ordered, ordered[1:], strict=False):
            counts = edges.setdefault(current[1], {})
            counts[following[1]] = counts.get(following[1], 0) + 1
    return ProcessMapResult(
        name="Observed direct-follow process map",
        provenance=Provenance(
            method="map_process",
            method_version="1.1",
            package_version=__version__,
            backend="unknown",
            parameters={
                "missing": "raise",
                "order": "timestamp; source-order ties",
                "timestamp_policy": "aware instants normalized to UTC; naive instants retained",
                "python_version": platform.python_version(),
            },
            input_schema_fingerprint=hashlib.sha256(
                b"case_id:string,activity:string,timestamp:calendar"
            ).hexdigest(),
            cohort_definition=f"All {len(grouped)} observed cases in {len(evidence)} events",
            assumptions=[
                AssumptionNote("DIRECT_FOLLOW", "Observed sequence is not inferred topology.")
            ],
        ),
        interpretation_context="Observed transition counts, without causal or branch inference.",
        metadata={
            "nodes": sorted(nodes),
            "edges": edges,
            "source_events": evidence,
            "unit": "transition count",
            "observation_count": len(evidence),
            "case_count": len(grouped),
            "exclusions": [],
        },
    )


def _events(event_log: EventStream) -> tuple[dict, list]:
    """Retain portable original identities and source positions before grouping."""
    if not isinstance(event_log, EventStream):
        raise ValidationError("map_process requires an EventStream.")
    grouped = defaultdict(list)
    evidence = []
    for position, event in enumerate(event_log.events):
        case, activity, timestamp = _event(event, position)
        grouped[case].append((timestamp, activity))
        evidence.append(
            {
                "case_id": case,
                "activity": activity,
                "timestamp": timestamp.isoformat(),
                "original_timestamp": event["timestamp"]
                if isinstance(event["timestamp"], str)
                else event["timestamp"].isoformat(),
                "source_position": position,
            }
        )
    return grouped, evidence


def _event(event: dict, position: int) -> tuple:
    """Validate one discovery observation before constructing its portable evidence."""
    try:
        case, activity = event["case_id"], event["activity"]
        _identity(case)
        _identity(activity)
        timestamp = _parse_timestamp(event["timestamp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(f"Invalid discovery event at source row {position}.") from exc
    return case, activity, timestamp


def _identity(value) -> None:
    """Keep case/activity identifiers explicit rather than coercing numeric or missing values."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Nonblank string identities required")
