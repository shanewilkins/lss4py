from lss4py import EventStream, map_process


def test_map_process_simple() -> None:
    events = [
        {"case_id": "C1", "activity": "A", "timestamp": "2020-01-01T00:00:00"},
        {"case_id": "C1", "activity": "B", "timestamp": "2020-01-01T01:00:00"},
        {"case_id": "C2", "activity": "A", "timestamp": "2020-01-02T00:00:00"},
        {"case_id": "C2", "activity": "B", "timestamp": "2020-01-02T01:00:00"},
        {"case_id": "C2", "activity": "C", "timestamp": "2020-01-02T02:00:00"},
    ]

    el = EventStream(events=events)
    pm = map_process(el)

    assert set(pm["nodes"]) == {"A", "B", "C"}
    assert pm["edges"] == {"A": {"B": 2}, "B": {"C": 1}}


def test_typed_discovery_result_restores_and_retains_legacy_lookup():
    from lss4py import ProcessMapResult

    source = EventStream(
        events=[
            {"case_id": "01", "activity": "A", "timestamp": "2026-01-01T01:00:00"},
            {"case_id": "01", "activity": "B", "timestamp": "2026-01-01T02:00:00"},
        ]
    )
    result = map_process(source)
    restored = ProcessMapResult.from_dict(result.to_dict())
    assert restored.to_mapping() == {"nodes": ["A", "B"], "edges": {"A": {"B": 1}}}
    assert restored.metadata["source_events"][0]["source_position"] == 0
    assert restored.provenance.cohort_definition == "All 1 observed cases in 2 events"


def test_discovery_lookup_is_detached():
    import pytest

    from lss4py import ValidationError

    result = map_process(EventStream(events=[]))
    result["nodes"].append("invented")
    assert result["nodes"] == []
    with pytest.raises(ValidationError):
        map_process(
            EventStream(
                events=[{"case_id": None, "activity": "A", "timestamp": "2026-01-01T01:00:00"}]
            )
        )


def test_discovery_orders_dst_fold_by_instant():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    zone = ZoneInfo("America/Chicago")
    result = map_process(
        EventStream(
            events=[
                {
                    "case_id": "01",
                    "activity": "B",
                    "timestamp": datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1),
                },
                {
                    "case_id": "01",
                    "activity": "A",
                    "timestamp": datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0),
                },
            ]
        )
    )
    assert result["edges"] == {"A": {"B": 1}}
    assert result.metadata["source_events"][0]["original_timestamp"].endswith("-06:00")
