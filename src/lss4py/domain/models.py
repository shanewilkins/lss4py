from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class AssumptionNote:
    code: str
    message: str
    severity: str = "info"


@dataclass(slots=True)
class AssumptionReport:
    assumptions: list[AssumptionNote] = field(default_factory=list)
    warnings: list[AssumptionNote] = field(default_factory=list)


@dataclass(slots=True)
class ProcessWindow:
    name: str
    start: datetime | None = None
    end: datetime | None = None


@dataclass(slots=True)
class EventLog:
    events: list[dict[str, Any]]
    required_fields: tuple[str, ...] = ("case_id", "activity", "timestamp")
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ComparisonSlice:
    before: EventLog
    after: EventLog
    label: str = "before_after"


@dataclass(slots=True)
class MetricResult:
    name: str
    value: float | None
    unit: str | None = None
    notes: list[AssumptionNote] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PercentileProfile:
    p50: float | None
    p90: float | None
    p95: float | None
    p99: float | None
    count: int
