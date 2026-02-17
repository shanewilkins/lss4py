from lss4py import adapters, analytics, domain, observability, reporting, workflows
from lss4py.errors import AdapterError, LSS4PyError, ValidationError, WorkflowError

__all__ = [
    "AdapterError",
    "LSS4PyError",
    "ValidationError",
    "WorkflowError",
    "adapters",
    "analytics",
    "domain",
    "main",
    "observability",
    "reporting",
    "workflows",
]


def main() -> None:
    print("lss4py scaffold ready")
