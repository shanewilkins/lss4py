from lss4py._kernels.capability import capability_indices
from lss4py._kernels.capability_study import capability_study
from lss4py._kernels.control_chart import control_chart
from lss4py._kernels.data_quality import normalize_data, validate_data
from lss4py._kernels.defect_yield import process_yield
from lss4py._kernels.descriptive import describe
from lss4py._kernels.distribution import distribution_profile
from lss4py._kernels.inference import mean_confidence_interval
from lss4py._kernels.orders import deadline_performance, validate_order_summary
from lss4py._kernels.quality_loss import quality_loss, quality_loss_analysis
from lss4py._kernels.reconstruction import reconstruct_orders
from lss4py._kernels.timing import (
    lead_time,
    process_cycle_efficiency,
    takt_time,
    wait_time,
)
from lss4py._kernels.yield_ import (
    booked_to_completed_yield,
    created_to_booked_yield,
    rolled_yield,
)
from lss4py._units import convert_duration_columns
from lss4py._version import __version__
from lss4py.adapters import AdapterSchema, EventLogCSVAdapter, load_event_log
from lss4py.adapters.numeric_log import NumericEventLogCSVAdapter, load_numeric_event_log
from lss4py.adapters.tabular import CSVTabularAdapter, load_csv
from lss4py.domain import (
    AnalysisBundle,
    AnalysisWindow,
    CapabilityResult,
    CapabilityStudyResult,
    ColumnProfile,
    ColumnRule,
    ControlChartResult,
    DataContract,
    DataIssue,
    DataValidationReport,
    DefectYieldResult,
    DescriptiveResult,
    DistributionProfileResult,
    EventLog,
    EventLogBindingsIR,
    EventStream,
    InputReference,
    IntervalEventLog,
    LeadTimeBindingIR,
    MeanCIResult,
    MetricBindingsIR,
    MetricSemanticsIR,
    NormalizedData,
    NumericEventLog,
    NumericLogContract,
    OrderSummaryContract,
    ProcessEdgeIR,
    ProcessModelIR,
    ProcessStepIR,
    QualityLossResult,
    Specification,
    StageBindingsIR,
    TimingResult,
    YieldResult,
    validate_bundle,
    validate_event_log,
)
from lss4py.domain.reconstruction import OrderReconstructionPolicy
from lss4py.domain.results import OrderReconstructionResult, ProcessMapResult
from lss4py.domain.units import DurationConversion
from lss4py.errors import (
    AdapterError,
    LSS4PyError,
    UnsupportedInputError,
    ValidationError,
    WorkflowError,
)
from lss4py.guidance import (
    AnalysisSelection,
    AnalysisSuitability,
    get_analysis,
    get_candidates,
    select_analysis,
)
from lss4py.workflows import map_process

__all__ = [
    "DurationConversion",
    "convert_duration_columns",
    "UnsupportedInputError",
    "ProcessMapResult",
    "AnalysisSelection",
    "select_analysis",
    "reconstruct_orders",
    "OrderReconstructionPolicy",
    "OrderReconstructionResult",
    "CSVTabularAdapter",
    "load_csv",
    "NumericEventLog",
    "NumericLogContract",
    "NumericEventLogCSVAdapter",
    "load_numeric_event_log",
    "OrderSummaryContract",
    "YieldResult",
    "TimingResult",
    "deadline_performance",
    "validate_order_summary",
    "AnalysisBundle",
    "InputReference",
    "validate_bundle",
    "ColumnRule",
    "ColumnProfile",
    "DataContract",
    "DataIssue",
    "DataValidationReport",
    "NormalizedData",
    "normalize_data",
    "validate_data",
    "__version__",
    "AdapterError",
    "AdapterSchema",
    "AnalysisWindow",
    "AnalysisSuitability",
    "get_analysis",
    "get_candidates",
    "CapabilityResult",
    "CapabilityStudyResult",
    "QualityLossResult",
    "capability_indices",
    "capability_study",
    "quality_loss",
    "quality_loss_analysis",
    "ControlChartResult",
    "control_chart",
    "DescriptiveResult",
    "DistributionProfileResult",
    "MeanCIResult",
    "DefectYieldResult",
    "describe",
    "distribution_profile",
    "mean_confidence_interval",
    "EventLogBindingsIR",
    "EventLog",
    "EventLogCSVAdapter",
    "EventStream",
    "IntervalEventLog",
    "LSS4PyError",
    "ValidationError",
    "WorkflowError",
    "booked_to_completed_yield",
    "created_to_booked_yield",
    "lead_time",
    "load_event_log",
    "LeadTimeBindingIR",
    "main",
    "map_process",
    "MetricBindingsIR",
    "MetricSemanticsIR",
    "ProcessEdgeIR",
    "ProcessModelIR",
    "ProcessStepIR",
    "process_cycle_efficiency",
    "rolled_yield",
    "process_yield",
    "StageBindingsIR",
    "Specification",
    "takt_time",
    "validate_event_log",
    "wait_time",
]


def main() -> None:
    """Print the package's lightweight readiness message."""
    print("lss4py scaffold ready")
