"""Domain validation for LSS4PY models.

Utilities for validating process models, event logs, and analytical inputs.
"""

from .models import AssumptionNote, AssumptionReport, EventLog


def validate_event_log(event_log: EventLog) -> AssumptionReport:
    """Validate event log structure and contents.

    Args:
        event_log: EventLog to validate.

    Returns:
        AssumptionReport with validation warnings.
    """
    if not event_log.events:
        return AssumptionReport(
            warnings=[
                AssumptionNote(
                    code="empty_event_log",
                    message="Event log contains zero rows.",
                    severity="warning",
                )
            ]
        )

    sample_event = event_log.events[0]
    missing = [field for field in event_log.required_fields if field not in sample_event]

    if missing:
        return AssumptionReport(
            warnings=[
                AssumptionNote(
                    code="missing_required_fields",
                    message=f"Missing required fields: {', '.join(missing)}",
                    severity="warning",
                )
            ]
        )

    return AssumptionReport()
