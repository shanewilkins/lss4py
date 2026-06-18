from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


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


ValueClassification = Literal["value_add", "non_value_add", "required_non_value_add"]
EdgeKind = Literal["sequence", "parallel_split", "parallel_join", "rework"]
ParallelTiming = Literal["critical_path", "sum_all_branches"]
ObservedDataShape = Literal["event_log_rows"]


@dataclass(slots=True)
class LeadTimeBindingIR:
    start_column: str | None = None
    end_column: str | None = None
    unit: Literal["seconds", "minutes", "hours", "days"] = "hours"


@dataclass(slots=True)
class StageBindingsIR:
    created: str | None = None
    booked: str | None = None
    completed: str | None = None


@dataclass(slots=True)
class EventLogBindingsIR:
    case_id_column: str | None = None
    step_id_column: str | None = None
    started_at_column: str | None = None
    completed_at_column: str | None = None


@dataclass(slots=True)
class MetricBindingsIR:
    lead_time: LeadTimeBindingIR = field(default_factory=LeadTimeBindingIR)
    stages: StageBindingsIR = field(default_factory=StageBindingsIR)
    event_log: EventLogBindingsIR = field(default_factory=EventLogBindingsIR)


@dataclass(slots=True)
class MetricSemanticsIR:
    parallel_timing: ParallelTiming = "critical_path"
    observed_data_shape: ObservedDataShape = "event_log_rows"


@dataclass(slots=True)
class ProcessStepIR:
    id: str
    name: str
    cycle_time_column: str | None = None
    value_classification: ValueClassification = "value_add"
    role_label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProcessEdgeIR:
    source_step_id: str
    target_step_id: str
    kind: EdgeKind = "sequence"
    condition: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProcessModelIR:
    name: str
    schema_version: str = "1.0"
    steps: list[ProcessStepIR] = field(default_factory=list)
    edges: list[ProcessEdgeIR] = field(default_factory=list)
    bindings: MetricBindingsIR = field(default_factory=MetricBindingsIR)
    metric_semantics: MetricSemanticsIR = field(default_factory=MetricSemanticsIR)
    metadata: dict[str, Any] = field(default_factory=dict)


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
