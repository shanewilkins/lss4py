# 0012: Visualization contracts

- Status: Superseded by [ADR-0021](0021-reuse-flo-and-established-presentation-libraries.md)
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: UR-029, TR-032, ADR-0002

## Context

LSS4PY calculates analytical results; visualization is optional (ADR-0002).
Plotting functions should consume typed results without recalculation and return
native library objects (matplotlib, Plotly) that users already know.

Currently, there are no visualization functions; the boundary and contract are
undefined.

## Decision

Plot functions in `src/lss4py/reporting/visualization.py` (optional `visualization`
extra) will:

1. **Accept only typed results** (e.g., `CapabilityResult`, `ControlChartResult`),
   never raw data. This ensures:
   - No hidden recalculation
   - All assumptions and diagnostics are available in the result
   - Users can inspect data before plotting

2. **Return native library objects:**
   - matplotlib: `matplotlib.figure.Figure`
   - Plotly: `plotly.graph_objects.Figure`
   - User chooses via `style=` parameter

3. **Preserve metadata:** plots display units, limits, flagged observations, and
   assumptions from the result without mutation.

4. **Remain optional:** base analytics never import visualization module.

Example:

```python
def plot_capability_study(
    result: CapabilityResult,
    *,
    style: Literal["matplotlib", "plotly"] = "matplotlib",
) -> Any:
    """
    Plot capability study results.
    
    Args:
        result: CapabilityResult from capability_study().
        style: "matplotlib" or "plotly".
    
    Returns:
        matplotlib Figure or Plotly Figure object.
    
    Notes:
        - No recalculation; uses result.diagnostics directly.
        - All limits, units, assumptions preserved from result.
        - Requires: lss4py[visualization]
    """
    if not _HAS_VISUALIZATION:
        raise ImportError("...")
    
    if style == "matplotlib":
        return _plot_capability_matplotlib(result)
    elif style == "plotly":
        return _plot_capability_plotly(result)
```

## Alternatives considered

- **LSS4PY plot wrapper class.** Consistent but extra indirection. Rejected: users
  already know matplotlib/Plotly.
- **Data-only return (dict/JSON).** Backend-agnostic but users write plotting code.
  Rejected: violates "make good LSS the default."
- **Bundled plotting submodule.** Tightly coupled. Rejected: violates ADR-0002.

## Consequences

- Plotting is a thin layer consuming result objects.
- Visualization tests verify that plots consume result data correctly and include
  all relevant metadata (limits, diagnostics, units).
- Plot functions do not run statistical tests or transformations.
- Accessibility (alt text, colorblind-friendly palettes) is documented but not
  enforced pre-1.0.
- Plot return types are library-native; easy to integrate into notebooks and
  dashboards.
