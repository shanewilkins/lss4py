# 0010: Unified diagnostic model

- Status: Proposed
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: UR-005, UR-017, TR-020, TR-022

## Context

LSS4PY analyses produce assumptions, warnings, and diagnostics (e.g., normality
test results, outlier flags, sample-size warnings), but these are currently exposed
inconsistently:

- Some analyses return `AssumptionReport`; others don't
- Warnings are scattered or missing
- Diagnostic details (p-values, counts) are not structured for querying
- Bundles (TR-033) cannot reliably capture reasoning

Users need to see assumptions and diagnostics to understand result reliability
(UR-005, UR-017) without requiring external knowledge or plotting.

## Decision

Introduce a unified `DiagnosticNote` class and centralized `DiagnosticRegistry` in
`src/lss4py/domain/diagnostics.py`.

`DiagnosticNote` is:

```python
@dataclass(slots=True)
class DiagnosticNote:
    code: str  # e.g., "normality_fail_shapiro"
    message: str
    severity: Severity = Severity.INFO  # INFO, WARNING, CRITICAL
    details: dict[str, Any] = field(default_factory=dict)  # e.g., {"p_value": 0.03}
```

`DiagnosticRegistry` centralizes definitions:

```python
DiagnosticRegistry.create("normality_fail_shapiro", {"p_value": 0.03})
```

All `AnalyticalResult` (ADR-0005) include:

- `assumptions: list[DiagnosticNote]` – what must be true for validity
- `warnings: list[DiagnosticNote]` – violations or concerns (severity ≥ WARNING)
- `diagnostics: dict[str, DiagnosticNote]` – checks run, results captured

Example:

```python
result = capability_study(data, lsl=10, usl=20)
result.assumptions == [
    DiagnosticNote("normality", "Data should be normally distributed"),
]
result.warnings == [
    DiagnosticNote(
        "normality_fail_shapiro",
        "Shapiro-Wilk test suggests non-normality.",
        severity=Severity.WARNING,
        details={"p_value": 0.03},
    ),
]
result.diagnostics == {
    "shapiro_wilk": DiagnosticNote(
        "normality_fail_shapiro",
        ...,
    ),
}
```

## Alternatives considered

- **Separate assumption/warning/diagnostic classes.** More specific but verbose.
  Rejected: unified severity/details handling is more queryable.
- **Callable/function diagnostics.** Lazy evaluation. Rejected: results are
  incomplete; users might miss critical checks.

## Consequences

- Every analysis populates `assumptions`, `warnings`, and `diagnostics` in the
  result.
- Diagnostics are JSON-serializable (via DiagnosticNote → dict → JSON).
- Pre-1.0, diagnostic codes and severity levels may evolve; breaking changes
  trigger deprecation (ADR-0014).
- Bundles (TR-033) include diagnostics, so reasoning is preserved across
  serialization.
