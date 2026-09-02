"""
LSS4PY Adapter Layer

Adapters normalize data from any source (files, databases, APIs, streams)
into LSS4PY's canonical contracts (DataFrames or EventLogs).

Public API (stable across releases):
  - TabularAdapter: Base class for tabular data adapters
  - EventLogAdapter: Base class for event-log adapters
  - AdapterSchema: Schema contract describing what was loaded

External adapters should inherit from TabularAdapter or EventLogAdapter
and conform to these contracts. See docs/EXTENDING.md.

Forbidden imports for external adapters:
  - lss4py.analytics (calculations)
  - lss4py.kernels (numerical code)
  - lss4py.workflows (end-to-end workflows)
  - lss4py.reporting (visualization)
"""

from lss4py.adapters.contracts import AdapterSchema, EventLogAdapter, TabularAdapter
from lss4py.adapters.event_log import load_event_log
from lss4py.adapters.tabular import load_tabular_records

__all__ = [
    # Public adapter API
    "TabularAdapter",
    "EventLogAdapter",
    "AdapterSchema",
    # Convenience loaders (deprecated; use adapter classes directly)
    "load_event_log",
    "load_tabular_records",
]
