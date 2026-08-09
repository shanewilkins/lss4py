from lss4py import EventLog, map_process, validate_event_log
from lss4py import main as package_main
from lss4py.errors import LSS4PyError


def test_stable_yellow_belt_surface_is_importable() -> None:
    assert EventLog is not None
    assert map_process is not None
    assert validate_event_log is not None


def test_error_base_type() -> None:
    assert issubclass(LSS4PyError, Exception)


def test_package_main_prints_ready_message(capsys) -> None:
    package_main()

    captured = capsys.readouterr()

    assert captured.out == "lss4py scaffold ready\n"


def test_validate_event_log_warns_on_empty_log() -> None:
    report = validate_event_log(EventLog(events=[]))

    assert [note.code for note in report.warnings] == ["empty_event_log"]


def test_validate_event_log_warns_on_missing_required_fields() -> None:
    report = validate_event_log(EventLog(events=[{"case_id": "C1", "activity": "A"}]))

    assert [note.code for note in report.warnings] == ["missing_required_fields"]
    assert "timestamp" in report.warnings[0].message


def test_validate_event_log_accepts_required_fields() -> None:
    report = validate_event_log(
        EventLog(events=[{"case_id": "C1", "activity": "A", "timestamp": "2020-01-01T00:00:00"}])
    )

    assert report.warnings == []
