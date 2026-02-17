from lss4py.domain.models import AssumptionReport, EventLog


def spc_report(event_log: EventLog) -> AssumptionReport:
    _ = event_log
    raise NotImplementedError("SPC reporting is not implemented yet.")
