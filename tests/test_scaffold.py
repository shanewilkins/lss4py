from lss4py import EventLog, map_process, validate_event_log
from lss4py.errors import LSS4PyError


def test_stable_yellow_belt_surface_is_importable() -> None:
    assert EventLog is not None
    assert map_process is not None
    assert validate_event_log is not None


def test_error_base_type() -> None:
    assert issubclass(LSS4PyError, Exception)
