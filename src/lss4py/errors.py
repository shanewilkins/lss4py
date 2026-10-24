"""LSS4PY exception hierarchy.

All exceptions raised by lss4py inherit from LSS4PyError.
Specific error types indicate the layer where the failure occurred.
"""


class LSS4PyError(Exception):
    """Base exception for lss4py."""


class ValidationError(LSS4PyError):
    """Raised when input data fails validation checks."""


class AdapterError(LSS4PyError):
    """Raised when adapter-level IO or parsing fails."""


class WorkflowError(LSS4PyError):
    """Raised when workflow orchestration fails."""


class UnsupportedInputError(ValidationError, TypeError):
    """Unsupported eager-frame input; retains TypeError compatibility and LSS4PY handling."""
