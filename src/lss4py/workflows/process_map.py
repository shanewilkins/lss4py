from collections import defaultdict
from datetime import datetime
from typing import Any, TypedDict

from lss4py.domain import EventStream


class ProcessMapResult(TypedDict):
    nodes: list[str]
    edges: dict[str, dict[str, int]]


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        return datetime.fromisoformat(value)

    raise TypeError("Event timestamps must be datetime objects or ISO-8601 strings.")


def map_process(event_log: EventStream) -> ProcessMapResult:
    """Discover activity nodes and direct-follow transitions from an event stream."""
    grouped_events: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for event in event_log.events:
        case_id = str(event["case_id"])
        grouped_events[case_id].append(event)

    nodes: set[str] = set()
    edges: dict[str, dict[str, int]] = {}

    for case_events in grouped_events.values():
        ordered_events = sorted(case_events, key=lambda event: _parse_timestamp(event["timestamp"]))

        for event in ordered_events:
            nodes.add(str(event["activity"]))

        for current_event, next_event in zip(ordered_events, ordered_events[1:], strict=False):
            current_activity = str(current_event["activity"])
            next_activity = str(next_event["activity"])
            edges.setdefault(current_activity, {})
            transition_count = edges[current_activity].get(next_activity, 0) + 1
            edges[current_activity][next_activity] = transition_count

    return {
        "nodes": sorted(nodes),
        "edges": edges,
    }
