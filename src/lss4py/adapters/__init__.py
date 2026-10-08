"""
LSS4PY Adapter Layer

Adapters normalize file data and future external sources into LSS4PY's canonical
Polars tabular contracts.

Public API (stable across releases):
  - TabularAdapter: Base class for tabular data adapters
  - EventLogAdapter: Base class for event-log adapters
  - AdapterSchema: Schema contract describing what was loaded
  - EventLogCSVAdapter: CSV interval-event implementation
  - load_event_log: convenient CSV-to-IntervalEventLog loader

External adapters should inherit from TabularAdapter or EventLogAdapter
and conform to these contracts. See docs/EXTENDING.md.

Forbidden imports for external adapters:
  - lss4py._kernels (private numerical code)
  - lss4py.workflows (end-to-end workflows)
  - lss4py.reporting (visualization)
"""

from lss4py.adapters.contracts import AdapterSchema, EventLogAdapter, TabularAdapter
from lss4py.adapters.event_log import EventLogCSVAdapter, load_event_log
from lss4py.adapters.tabular import load_tabular_records

__all__ = [
    # Public adapter API
    "TabularAdapter",
    "EventLogAdapter",
    "EventLogCSVAdapter",
    "AdapterSchema",
    # Convenience loaders
    "load_event_log",
    "load_tabular_records",
]
