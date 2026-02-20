from lss4py.domain.models import EventLog
from lss4py.workflows.process_map import map_process


def test_map_process_simple():
    events = [
        {"case_id": "C1", "activity": "A", "timestamp": "2020-01-01T00:00:00"},
        {"case_id": "C1", "activity": "B", "timestamp": "2020-01-01T01:00:00"},
        {"case_id": "C2", "activity": "A", "timestamp": "2020-01-02T00:00:00"},
        {"case_id": "C2", "activity": "B", "timestamp": "2020-01-02T01:00:00"},
        {"case_id": "C2", "activity": "C", "timestamp": "2020-01-02T02:00:00"},
    ]

    el = EventLog(events=events)
    pm = map_process(el)

    assert set(pm["nodes"]) == {"A", "B", "C"}
    assert pm["edges"] == {"A": {"B": 2}, "B": {"C": 1}}
