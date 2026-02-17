from lss4py.domain.models import EventLog, PercentileProfile


def summarize_cycle_time(
    event_log: EventLog, percentiles: tuple[int, ...] = (50, 90, 95, 99)
) -> PercentileProfile:
    _ = (event_log, percentiles)
    raise NotImplementedError("Cycle-time percentile summarization is not implemented yet.")
