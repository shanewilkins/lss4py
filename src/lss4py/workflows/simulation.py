from lss4py.domain import EventStream


def redesign_simulation(event_log: EventStream) -> dict[str, object]:
    """Reject redesign simulation until the workflow is implemented."""
    _ = event_log
    raise NotImplementedError("Simulation workflow is not implemented yet.")
