class LSS4PyError(Exception):
    """Base exception for lss4py."""


class ValidationError(LSS4PyError):
    """Raised when input data fails validation checks."""


class AdapterError(LSS4PyError):
    """Raised when adapter-level IO or parsing fails."""


class WorkflowError(LSS4PyError):
    """Raised when workflow orchestration fails."""
