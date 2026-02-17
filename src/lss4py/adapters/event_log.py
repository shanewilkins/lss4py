from pathlib import Path

from lss4py.domain.models import EventLog


def load_event_log(path: str | Path) -> EventLog:
    _ = path
    raise NotImplementedError("Event-log adapter is not implemented yet.")
