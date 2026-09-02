# LSS4PY Architecture: Approved Layers & Import Directions

**Document Status:** Approved  
**Last Updated:** 2026-09-02  
**Audience:** Maintainers, Contributors, Auditors  

This document defines the approved layered architecture and enforces import restrictions
to maintain boundaries. Use this as an audit checklist during code review and refactoring.

---

## Layer Stack (Top to Bottom)

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER CODE                                │
│            (notebooks, scripts, downstream packages)            │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────▼───────────────┐
        │   PUBLIC API LAYER         │         Import: from lss4py import ...
        │  lss4py/__init__.py        │
        │ (analytical functions)     │
        └────────────┬───────────────┘
                     │
        ┌────────────▼──────────────────────────────────┐
        │     DOMAIN MODEL LAYER                        │   Import: from lss4py.domain import ...
        │  - domain/models.py (ProcessModelIR, etc.)    │
        │  - domain/results.py (AnalyticalResult, etc.) │
        │  - domain/validation.py (ValidationError)     │
        └────────────┬──────────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────────┐
        │     ADAPTER LAYER (Private)                   │   Import: (internal use only)
        │  lss4py/_adapters/                            │
        │  - __init__.py (AdapterRegistry)              │
        │  - _pandas.py (pandas adapter)                │
        │  - _ocel2.py (OCEL 2.0 adapter, v0.3+)        │
        │  - _xes.py (XES adapter, v0.4+)               │
        └────────────┬──────────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────────┐
        │     KERNEL LAYER (Private)                    │   Import: (internal use only)
        │  lss4py/_kernels/                             │
        │  - timing.py (lead_time, wait_time, ...)      │
        │  - yield_.py (stage yield, rolled yield, ...) │
        │  - capability.py (Cp, Cpk, future)            │
        │  - spc.py (control charts, future)            │
        │  - descriptive.py (percentiles, future)       │
        │  - inference.py (hypothesis tests, future)    │
        │  - _helpers.py (shared utilities)             │
        └────────────┬──────────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────────┐
        │     INTERNAL HELPERS (Private)                │   Import: (internal use only)
        │  lss4py/_event_log.py                         │
        │  (pandas-based event-log utilities, v0.3)     │
        └────────────┬──────────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────────┐
        │     EXTERNAL DEPENDENCIES                     │
        │  - narwhals (dataframe abstraction)           │
        │  - pandas / polars (optional backends)        │
        │  - numpy, scipy, statsmodels (computation)    │
        └──────────────────────────────────────────────┘
```

---

## Import Rules

### ✅ PUBLIC API (Stable; external users depend on this)

**Location:** `lss4py/__init__.py`

**Exports:**
- All analytical functions: `lead_time`, `wait_time`, `process_cycle_efficiency`, `takt_time`,
  `created_to_booked_yield`, `booked_to_completed_yield`, `rolled_yield`
- Domain models: Import from `lss4py.domain` (public contract)

**Users write:**
```python
from lss4py import lead_time, wait_time
from lss4py.domain import ProcessModelIR, TimingResult

result = lead_time(df, columns={...})
```

**Internal code writes:**
```python
from lss4py import lead_time  # Use public surface
```

**Never:**
```python
from lss4py.yellow_belt import lead_time  # ❌ DELETED
from lss4py._kernels.timing import lead_time  # ❌ Private
from lss4py.kernels.timing import lead_time  # ❌ Doesn't exist
```

---

### ✅ DOMAIN MODELS (Stable; part of public API)

**Location:** `lss4py/domain/`

**Exports:**
- `ProcessModelIR` — process topology with optional event-log bindings
- `AnalyticalResult` — base class for all analyses (provides provenance, assumptions, serialization)
- `TimingResult`, `YieldResult` — typed subclasses
- `ValidationError` — domain validation exception
- `TimeUnit`, `ProcessStep`, etc.

**Users write:**
```python
from lss4py.domain import ProcessModelIR, TimingResult, ValidationError
```

**Internal code writes:**
```python
from lss4py.domain import ProcessModelIR  # Use public domain models
```

**Never:**
```python
from lss4py.domain.models import SomePrivateHelper  # ❌ Check naming; if private, don't import
```

---

### ❌ KERNEL LAYER (Private; refactor-safe)

**Location:** `lss4py/_kernels/`

**Intent:** Implementation detail. Functions are exposed via public API only.

**Internal code writes:**
```python
# Inside kernel functions or adapters:
from lss4py._kernels import timing
from lss4py._kernels._helpers import detect_backend, build_provenance

result = timing._compute_lead_time_from_event_log(canonical_data, process_model)
```

**Users write:** ❌ NEVER
```python
from lss4py._kernels.timing import lead_time  # Don't dig into internals
from lss4py.kernels.timing import lead_time  # Directory doesn't exist
```

**Refactoring safety:** Kernel organization can change in any v0.x release
without breaking downstream code (users don't import internals).

---

### ❌ ADAPTER LAYER (Private; extensible)

**Location:** `lss4py/_adapters/`

**Intent:** Format-specific parsing. Internal use; accessed via `AdapterRegistry` only.

**Internal code writes:**
```python
# Inside kernel functions:
from lss4py._adapters import AdapterRegistry
canonical_data = AdapterRegistry.adapt(user_input)
```

**Users write:** ❌ NEVER
```python
from lss4py._adapters._pandas import adapt_pandas  # Don't use directly
```

**Future extension:** Advanced users *may* register custom adapters
(documented in v0.5+ if feature stabilizes):
```python
# Hypothetical v0.5+ API:
from lss4py._adapters import AdapterRegistry
AdapterRegistry.register('custom_format', my_adapter_fn)
```

---

### ❌ EVENT-LOG HELPERS (Private; v0.3 refactor candidate)

**Location:** `lss4py/_event_log.py`

**Intent:** Pandas-based event-log utilities (scheduled for Narwhals refactor in v0.3).

**Internal code writes:**
```python
# Inside timing.py or adapters:
from lss4py._event_log import event_log_lead_time_series
```

**Users write:** ❌ NEVER
```python
from lss4py._event_log import event_log_lead_time_series  # Private
```

---

## Cross-Layer Import Matrix

| From → To   | PUBLIC | DOMAIN | KERNEL | ADAPTER | EVENT_LOG |
|-------------|--------|--------|--------|---------|-----------|
| **PUBLIC**  | ✅ (re-export) | ✅ (import & re-export) | ❌ (forbidden) | ❌ (forbidden) | ❌ (forbidden) |
| **DOMAIN**  | ✅ (depend on public) | ✅ (intra-layer OK) | ❌ (forbidden) | ❌ (forbidden) | ❌ (forbidden) |
| **KERNEL**  | ❌ (would create cycle) | ✅ (use domain models) | ✅ (intra-layer OK) | ✅ (call adapters) | ✅ (call helpers) |
| **ADAPTER** | ❌ (would create cycle) | ✅ (use domain models) | ❌ (forbidden) | ✅ (intra-layer OK) | ✅ (call helpers) |
| **EVENT_LOG** | ❌ (would create cycle) | ✅ (use domain models) | ✅ (called by kernels) | ✅ (called by adapters) | ✅ (intra-layer OK) |

---

## Audit Checklist

Use this checklist during code review:

- [ ] **No imports from `_kernels/` outside of other kernel modules or adapters**
- [ ] **No imports from `_adapters/` outside of kernel or adapter modules**
- [ ] **No imports from `_event_log.py` outside of kernel or adapter modules**
- [ ] **All public functions are re-exported in `lss4py/__init__.py`**
- [ ] **Domain models are imported from `lss4py.domain`, not `lss4py.domain.models`**
- [ ] **Test files use public imports: `from lss4py import lead_time`, not internal paths**
- [ ] **No circular imports between layers**
- [ ] **New analytical functions are added to appropriate `_kernels/module.py`, then re-exported in `__init__.py`**
- [ ] **New formats are added as `_adapters/format_name.py` + registered in `AdapterRegistry`**

---

## Version Roadmap & Layer Evolution

| Version | Changes | Layer Impact |
|---------|---------|--------------|
| v0.2 | Timing & yield kernels stable | Kernel organization fixed; pandas adapter only |
| v0.3 | Add capability, SPC kernels; OCEL 2.0 adapter | Kernel & adapter layers expand |
| v0.4 | Add inference, visualization kernels; XES adapter | Kernel & adapter layers expand; visualizations in separate package |
| v0.5+ | Custom adapter registration (if demanded); optional workflow APIs | Adapter registry becomes optional public API |
| v1.0 | All layers stable; versioning guarantees apply | No breaking changes to public API or domain models |

---

## Related Documents

- **ADR-0016:** Private kernel architecture and capability-based organization
- **ADR-0017:** Format adapter registry for multi-standard event log support
- **ADR-0002:** Keep the core package focused on analytics (ecosystem boundary)
- **TR-018:** Kernel organization technical requirement
- **TR-033:** Analysis bundle and result export contract
