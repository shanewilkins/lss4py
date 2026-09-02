# 0006: Numerical kernel delegation and registry

- Status: Proposed
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: TR-018, TR-023, TR-024, TR-025, TR-028, TR-029

## Context

LSS4PY calculations currently rely on NumPy, SciPy, and statsmodels, but there is
no explicit kernel abstraction. This makes it hard to:

- Track which upstream library version produced a result
- Swap implementations (e.g., testing alternative algorithms or backends)
- Validate R SixSigma parity independently from workflow logic
- Document provenance and formula sources for audits

Additionally, LSS4PY's promise to own workflows and delegate primitives (ADR-0003)
requires a clear boundary between orchestration (LSS4PY) and calculation (NumPy/SciPy).

## Decision

Create a `src/lss4py/kernels/` submodule that houses small, focused, testable
calculation functions organized by LSS domain:

- `kernels/capability.py` – Cp, Cpk, Z, confidence intervals, variation estimates
- `kernels/yield_.py` – Yield, FTY, RTY, DPMO calculations
- `kernels/spc.py` – Moving-range, I-chart, other control-chart families
- `kernels/msa.py` – Gage R&R ANOVA, variance components
- `kernels/inference.py` – Confidence intervals, hypothesis tests, effect estimates
- `kernels/quality_loss.py` – Taguchi loss calculations

Each kernel function:

1. Accepts validated NumPy arrays and domain parameters (e.g., LSL, USL, confidence
   level).
2. Returns a lightweight `KernelResult` dataclass with raw outputs, provenance
   (formula source, upstream library versions), and optional metadata.
3. Includes docstring citing formula source (AIAG, R package, textbook, etc.).
4. Is tested in isolation against reference fixtures (R SixSigma, published examples,
   textbook cases).

Workflow-level APIs (e.g., `capability_study()`) orchestrate data validation, array
extraction (via Narwhals), kernel invocation, and wrapping in typed `AnalyticalResult`.

## Alternatives considered

- **Thin wrappers without abstraction.** Calculation logic scattered across modules.
  Rejected: no parity tracking; hard to version independently.
- **Lazy kernel dispatch (callable registry).** Swap implementations at runtime.
  Rejected: over-engineered for MVP; adds complexity.

## Consequences

- New numerical analyses require both a kernel function and a workflow wrapper.
- Kernel results are internal; only `AnalyticalResult` is public.
- R parity fixtures are stored alongside kernels and tested automatically (ADR-0013).
- Each kernel version string is tracked and included in result provenance.
- Kernels do not depend on Narwhals, dataframe backends, or visualization; only
  NumPy/SciPy/statsmodels.
