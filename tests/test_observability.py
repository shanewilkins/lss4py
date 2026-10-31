"""Exercise diagnostics while containing logging and telemetry process state."""

import io
import json
import logging

import pytest
import structlog
from click.testing import CliRunner

from lss4py.cli import main
from lss4py.observability import configure_logging, get_logger, telemetry


@pytest.fixture
def isolated_logging():
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    configured = structlog.is_configured()
    config = structlog.get_config().copy()
    context = structlog.contextvars.get_contextvars()
    structlog.contextvars.clear_contextvars()
    try:
        yield
    finally:
        root.handlers, root.level = handlers, level
        if configured:
            structlog.configure(**config)
        else:
            structlog.reset_defaults()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**context)


@pytest.mark.parametrize("debug", [False, True])
@pytest.mark.usefixtures("isolated_logging")
def test_json_logging_filters_debug_and_retains_context(debug, capsys):
    configure_logging(debug=debug)
    structlog.contextvars.bind_contextvars(order_id="WNF-003")
    logger = get_logger("measurement")
    logger.debug("detail", rows=330)
    logger.info("complete", orders=39)
    try:
        raise ValueError("invalid endpoint")
    except ValueError:
        logger.exception("rejected")
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [row["event"] for row in records] == (
        ["detail", "complete", "rejected"] if debug else ["complete", "rejected"]
    )
    assert all(row["order_id"] == "WNF-003" for row in records)
    assert all(row["timestamp"] and row["level"] for row in records)
    assert records[-2]["orders"] == 39
    assert "ValueError: invalid endpoint" in records[-1]["exception"]
    assert get_logger() is not None


@pytest.mark.parametrize("debug", [False, True])
def test_doctor_reports_success_with_requested_logging(debug, monkeypatch):
    calls = []
    monkeypatch.setattr("lss4py.cli.configure_logging", lambda **kw: calls.append(kw))
    result = CliRunner().invoke(main, [*(["--debug"] if debug else []), "doctor"])
    assert result.exit_code == 0, result.output
    assert "lss4py" in result.output and "ready" in result.output
    assert calls == [{"debug": debug}]


def test_cli_help_and_invalid_command_are_actionable(monkeypatch):
    calls = []
    monkeypatch.setattr("lss4py.cli.configure_logging", lambda **kw: calls.append(kw))
    help_result = CliRunner().invoke(main, ["--help"])
    assert help_result.exit_code == 0
    assert "doctor" in help_result.output and "--debug" in help_result.output
    invalid = CliRunner().invoke(main, ["missing"])
    assert invalid.exit_code == 2
    assert "No such command" in invalid.output
    assert calls == []


@pytest.mark.parametrize("service_name", [None, "book-measurement"])
def test_telemetry_exports_real_spans_without_installing_a_global_provider(
    service_name, monkeypatch
):
    original = telemetry.trace.get_tracer_provider()
    providers = []
    stream = io.StringIO()
    exporter = telemetry.ConsoleSpanExporter(out=stream)
    monkeypatch.setattr(telemetry, "ConsoleSpanExporter", lambda: exporter)
    monkeypatch.setattr(telemetry.trace, "set_tracer_provider", providers.append)
    if service_name is None:
        telemetry.configure_telemetry()
    else:
        telemetry.configure_telemetry(service_name)
    (provider,) = providers
    try:
        monkeypatch.setattr(telemetry.trace, "get_tracer", provider.get_tracer)
        tracer = telemetry.get_tracer()
        with tracer.start_as_current_span("reconstruct") as parent:
            with telemetry.get_tracer("book.workflow").start_as_current_span("measure") as child:
                child.set_attribute("orders", 39)
        assert provider.force_flush(timeout_millis=5000)
        # Console export is a sequence of indented JSON objects.
        decoder = json.JSONDecoder()
        remaining, spans = stream.getvalue().strip(), []
        while remaining:
            span, end = decoder.raw_decode(remaining)
            spans.append(span)
            remaining = remaining[end:].lstrip()
        by_name = {span["name"]: span for span in spans}
        assert set(by_name) == {"reconstruct", "measure"}
        assert by_name["measure"]["attributes"]["orders"] == 39
        assert by_name["measure"]["parent_id"] == by_name["reconstruct"]["context"]["span_id"]
        assert child.get_span_context().trace_id == parent.get_span_context().trace_id
        assert all(
            span["resource"]["attributes"]["service.name"] == (service_name or "lss4py")
            for span in spans
        )
    finally:
        provider.shutdown()
    assert telemetry.trace.get_tracer_provider() is original
