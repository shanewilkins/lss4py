# 0016: Private kernel architecture and capability-based organization

- Status: Accepted
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: TR-018, TR-033

## Context

The package initially exposed analytical functions through multiple re-export layers:
`yellow_belt.py` (user-facing re-export) → `kernels/__init__.py` (kernel re-exports) →
`kernels/timing.py`, `kernels/yield_.py` (implementation).

This created unnecessary indirection and exposed implementation details. Additionally,
the distinction between `kernels/` and `analytics/` was unclear; both contained analytical
functions organized differently (kernels by type, analytics by intent).

Users needed to understand package internals to know whether to import from `lss4py`,
`lss4py.kernels`, or `lss4py.yellow_belt`. Code organization did not reflect actual
user workflows.

The project targets both library users (like scikit-learn) and ecosystem partners,
requiring a clear, stable public API with internal infrastructure treated as private.

## Decision

1. **Kernels are private infrastructure.** Rename `lss4py/kernels/` to `lss4py/_kernels/`.
   Internal modules use `_` prefix consistently (e.g., `_helpers.py`, `_event_log.py`).

2. **All analytical functions are exposed at package level.** `lss4py/__init__.py`
   is the only public entry point for calculations:
   ```python
   from lss4py import lead_time, wait_time, created_to_booked_yield, ...
   ```
   Users never write `from lss4py._kernels.timing import lead_time`.

3. **Organize kernels by analytical capability, not by belt level.** Structure:
   - `_kernels/timing.py` — lead time, cycle time, efficiency, takt time
   - `_kernels/yield_.py` — stage yield, rolled-throughput yield
   - `_kernels/capability.py` — Cp, Cpk, Pp, Ppk (future)
   - `_kernels/spc.py` — control charts, run tests (future)
   - `_kernels/descriptive.py` — percentiles, distribution shapes (future)
   - `_kernels/inference.py` — hypothesis tests, confidence intervals (future)
   - `_kernels/_helpers.py` — shared utilities (backend detection, provenance, validation)

4. **Document belt-level guidance separately.** "Yellow Belt covers timing and yield"
   is a *usage pattern*, not a code structure. Belt level lives in documentation
   (`docs/roadmap.md`, `docs/analysis-journey.md`), not file structure.

## Alternatives considered

- **Keep kernels public; make users opt-in to internals.** This requires clear
  documentation and risky: as kernels evolve, users depending on internal APIs
  experience breakage outside normal semver cycles.

- **Merge all functions into a single `analytics.py` module.** Avoids private
  namespacing but creates a single large file; discourages future modularity.

- **Use separate package for internals (`lss4py._core`).** Adds distribution
  complexity; tight coupling between core and main package makes this unnecessary.

## Consequences

- **Positive:**
  - Clear API boundary: users never import internals
  - Safe to refactor kernel organization in v0.3+ without breaking downstream code
  - Consistent with scikit-learn, statsmodels, NumPy patterns
  - Simpler mental model: "use `lss4py`, not its guts"

- **Negative:**
  - Advanced users cannot directly use internal functions (acceptable; they should
    request public APIs instead)
  - Requires one-time test and documentation audit to fix imports

- **Follow-up:**
  - ADR-0017 defines adapter registry; adapters sit in `_adapters/` alongside kernels
  - Update CONTRIBUTING.md to document public vs. internal conventions
  - Add import lint rule: if code outside `_kernels/` imports from `_kernels/`,
    audit for missing public API
