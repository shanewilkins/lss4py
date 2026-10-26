from lss4py.domain import EventStream


def bottleneck_report(event_log: EventStream) -> dict[str, object]:
    """Reject bottleneck analysis until the workflow is implemented."""
    _ = event_log
    raise NotImplementedError("Bottleneck workflow is not implemented yet.")
