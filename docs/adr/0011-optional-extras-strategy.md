# 0011: Optional extras strategy

- Status: Proposed
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: UR-012, TR-010

## Context

LSS4PY has optional dependencies for visualization (seaborn, matplotlib),
simulation (simpy), optimization (pulp, pyomo), and process mining (PM4Py).
Core analytics must remain usable without these extras (UR-012).

Currently, there is no gating strategy; if a user installs `lss4py` without
extras and tries to use visualization, they get cryptic import errors.

## Decision

Use centralized import gating with helpful error messages in `src/lss4py/_extras.py`.

**Strategy:**

1. Define extras in `pyproject.toml`:

```toml
[project.optional-dependencies]
visualization = ["matplotlib>=3.10.0", "seaborn>=0.13.0"]
simulation = ["simpy>=4.1.0"]
optimization = ["pulp>=2.9.0", "pyomo>=6.8.0"]
process-mining = ["pm4py>=2.7.0"]
storage = ["duckdb>=1.2.0", "pyarrow>=19.0.0"]
```

2. Gate imports at module boundaries:

```python
# src/lss4py/reporting/visualization.py
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    _HAS_VISUALIZATION = True
except ImportError:
    _HAS_VISUALIZATION = False

def plot_capability_study(...) -> "matplotlib.figure.Figure":
    if not _HAS_VISUALIZATION:
        raise ImportError(
            "Visualization requires matplotlib and seaborn. "
            "Install with: uv pip install lss4py[visualization]"
        )
    ...
```

3. Document in docstrings and type hints:

```python
def plot_capability_study(...) -> "matplotlib.figure.Figure":
    """
    Plot capability study results.
    
    Requires: lss4py[visualization]
    
    Raises:
        ImportError: if matplotlib or seaborn are not installed.
    """
```

4. CI validates base install works without extras:

```bash
uv pip install lss4py --no-cache-dir
uv run python -c "from lss4py import lead_time"  # Should work
uv run python -c "from lss4py.reporting.visualization import plot_capability_study"  # Should fail gracefully
```

## Alternatives considered

- **Lazy proxies (importlib).** Errors only on function call. Rejected: delayed
  errors confuse debugging.
- **Separate entry points.** No coupling. Rejected: users don't know features
  exist; discovery is hard.

## Consequences

- Base `lss4py` install remains lightweight; optional dependencies are user choice.
- Errors are immediate and actionable.
- Optional extras can evolve independently (version bumps don't affect core).
- Each extra can be developed and tested in isolation (future: separate packages).
