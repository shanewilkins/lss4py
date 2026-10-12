# 0017: Format adapter registry for multi-standard event log support

- Status: Accepted
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: UR-028, UR-029, TR-040

## Context

LSS4PY v0.2 supports pandas DataFrames with explicit column mappings. Future versions
must support OCEL 2.0 (green belt) and XES (black belt) event log formats without
requiring kernel functions to know about format-specific parsing.

Adding format support directly to each kernel function (e.g., `lead_time(data, format='ocel2')`)
couples analytical logic to data format concerns. Adding separate functions
(`lead_time_from_ocel2()`, `lead_time_from_xes()`) creates API explosion and maintenance burden.

The system must:
- Accept multiple input formats transparently
- Route format-specific parsing to dedicated adapters
- Keep kernels working with a stable, format-agnostic internal representation
- Enable new format support without modifying kernel code
- Allow users to provide custom adapters for proprietary formats

## Decision

Implement a **pluggable format adapter registry** that:

1. **Adapters convert input formats to an internal canonical representation.**
   Structure:
   ```
   lss4py/
     _adapters/
       __init__.py          # AdapterRegistry class
       _pandas.py           # Pandas → canonical
       _ocel2.py            # OCEL 2.0 → canonical (v0.3)
       _xes.py              # XES → canonical (v0.4+)
     _kernels/
       timing.py            # All functions use canonical representation
   ```

2. **Registry provides format detection and routing:**
   ```python
   class AdapterRegistry:
       @classmethod
       def detect_format(data) -> str:  # 'pandas', 'ocel2', 'xes', 'unknown'
       
       @classmethod
       def adapt(data, format_name=None) -> CanonicalEventLog:
       
       @classmethod
       def register(format_name: str, adapter_fn: Callable):
   ```

3. **Kernel functions delegate format handling to adapters:**
   ```python
   def lead_time(data, *, lead_time_column=None, process_model=None, ...):
       canonical_data = AdapterRegistry.adapt(data)
       if process_model and process_model.has_event_log_bindings():
           return _compute_from_event_log(canonical_data, process_model)
       elif lead_time_column:
           return _compute_from_column(canonical_data, lead_time_column)
   ```

4. **Format auto-detection is optional; explicit format specification is allowed:**
   ```python
   lead_time(ocel2_log)  # System detects OCEL 2.0 automatically
   lead_time(ocel2_log, format="ocel2")  # Explicit specification for ambiguous data
   ```

5. **Canonical representation is minimal and format-agnostic:**
   - Event ID, case ID, activity, timestamp, duration columns
   - Optionally: resource, cost, attributes (as dict)
   - Backed by Narwhals for pandas/Polars/PyArrow neutrality
   - Private to `_adapters/` and `_kernels/`; not part of public API

## Alternatives considered

- **Format-specific kernel functions.** `lead_time_pandas()`, `lead_time_ocel2()`, etc.
  Rejected: API explosion; maintenance burden; users confused by choice; hard to compose.

- **Universal format parameter in each function.** `lead_time(data, format='ocel2')`.
  Rejected: couples analytical code to format parsing; kernel functions grow complex;
  hard to test independently.

- **Separate `EventLogAdapter` base class; users inherit.** Rejected: users shouldn't
  extend adapters; better to register factory functions (lower ceremony).

- **Single adapter function that tries all formats.** Rejected: slow; ambiguous errors;
  no way to disambiguate when multiple formats could parse the same input.

## Consequences

- **Positive:**
  - Kernels remain format-agnostic; focused on analytical logic
  - New format support requires only a new adapter (typically 200–400 lines per format)
  - Users can register custom adapters for proprietary formats (advanced use case)
  - Clean separation of concerns: format problem vs. analysis problem
  - Extensible without modifying core kernel code

- **Negative:**
  - Introduces canonical representation concept (learning curve; needs documentation)
  - Adapter latency for large logs (typically <5% overhead; acceptable for analytics)
  - Requires clear error messages when auto-detection fails (implementation detail)

- **Follow-up:**
  - v0.3 ships OCEL 2.0 adapter; release notes document format auto-detection
  - v0.4+ ships XES adapter; versioned in release notes
  - Document canonical representation contract in `docs/architecture.md`
  - Add type hints for custom adapters; provide template in CONTRIBUTING.md
  - Consider caching adapters for repeated use (lazy optimization)

## Versioning & Rollout

- **v0.2.x:** Pandas adapter only; auto-detection works for DataFrame
- **v0.3.x:** Add OCEL 2.0 adapter (green belt); auto-detect OCEL 2.0 vs. Pandas
- **v0.4.x:** Add XES adapter (black belt); extend auto-detection
- **v0.5+:** Custom adapter registration becomes stable public API (if demand exists)
