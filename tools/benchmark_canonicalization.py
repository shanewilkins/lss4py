"""Benchmark canonical conversion, validation, and analysis across eager backends."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import resource
import statistics
import subprocess
import sys
import time
import tracemalloc
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import polars as pl
import pyarrow as pa

from lss4py import ColumnRule, DataContract, describe
from lss4py._frames import canonical_frame
from lss4py._pandera_validation import validate_frame

DEFAULT_ROWS = 20_000
DEFAULT_WIDE_COLUMNS = 128
DEFAULT_REPEATS = 5
TIME_BUDGET_SECONDS = 2.0
PEAK_MEMORY_BUDGET_MIB = 256.0


def _records(rows: int, columns: int) -> dict[str, np.ndarray]:
    """Build deterministic numeric columns with one selected measurement."""
    records = {"value": np.linspace(0.0, 1.0, rows, dtype=np.float64)}
    for index in range(1, columns):
        records[f"unused_{index:03d}"] = np.arange(rows, dtype=np.float64) + index
    return records


def _source(backend: str, records: dict[str, np.ndarray]) -> Any:
    """Materialize one supported eager backend without sharing writable arrays."""
    copied = {name: values.copy() for name, values in records.items()}
    if backend == "polars":
        return pl.DataFrame(copied)
    if backend == "pandas":
        return pd.DataFrame(copied)
    if backend == "pyarrow":
        return pa.table(copied)
    raise ValueError(f"Unknown backend: {backend}")


def _rss_mib() -> float:
    """Return process maximum resident memory in MiB on macOS and Linux."""
    peak = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return peak / 1024**2 if sys.platform == "darwin" else peak / 1024


def _measure(operation: Callable[[], Any], repeats: int) -> dict[str, float]:
    """Record median wall time and maximum traced Python allocation."""
    operation()
    timings = []
    peaks = []
    for _ in range(repeats):
        gc.collect()
        tracemalloc.start()
        started = time.perf_counter()
        operation()
        timings.append(time.perf_counter() - started)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peaks.append(peak / 1024**2)
    return {
        "median_seconds": statistics.median(timings),
        "python_peak_mib": max(peaks),
    }


def benchmark_scenario(
    backend: str,
    *,
    rows: int,
    columns: int,
    repeats: int,
) -> dict[str, Any]:
    """Benchmark one backend/shape while enforcing selected-column materialization."""
    source = _source(backend, _records(rows, columns))
    contract = DataContract((ColumnRule("value"),))
    baseline_rss = _rss_mib()

    canonical = canonical_frame(source, ("value",), retain_source_positions=True)
    if canonical.to_polars(copy=False).columns != ["value"]:
        raise AssertionError("Canonicalization materialized undeclared columns.")
    if canonical.source_row_count != rows or len(canonical.source_schema) != columns:
        raise AssertionError("Canonical source evidence does not describe the complete input.")

    conversion = _measure(
        lambda: canonical_frame(source, ("value",), retain_source_positions=True),
        repeats,
    )
    canonical_polars = canonical.to_polars(copy=False)
    validation = _measure(
        lambda: validate_frame(
            canonical_polars,
            contract,
            source_positions=canonical.source_positions,
        ),
        repeats,
    )
    analysis = _measure(lambda: describe(source, column="value"), repeats)
    return {
        "backend": backend,
        "shape": "narrow" if columns == 1 else "wide",
        "rows": rows,
        "source_columns": columns,
        "selected_columns": 1,
        "conversion": conversion,
        "validation": validation,
        "total_analysis": analysis,
        "process_peak_rss_delta_mib": max(0.0, _rss_mib() - baseline_rss),
    }


def _budgets(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate broad regression budgets without asserting backend speed rankings."""
    failures = []
    for scenario in scenarios:
        identity = f"{scenario['backend']}/{scenario['shape']}"
        for operation in ("conversion", "validation", "total_analysis"):
            observed = scenario[operation]["median_seconds"]
            if observed > TIME_BUDGET_SECONDS:
                failures.append(
                    f"{identity} {operation} {observed:.6f}s exceeds {TIME_BUDGET_SECONDS:.1f}s"
                )
        observed_memory = scenario["process_peak_rss_delta_mib"]
        if observed_memory > PEAK_MEMORY_BUDGET_MIB:
            failures.append(
                f"{identity} peak RSS delta {observed_memory:.3f} MiB "
                f"exceeds {PEAK_MEMORY_BUDGET_MIB:.1f} MiB"
            )
    return {
        "time_per_operation_seconds": TIME_BUDGET_SECONDS,
        "process_peak_rss_delta_mib": PEAK_MEMORY_BUDGET_MIB,
        "status": "pass" if not failures else "fail",
        "failures": failures,
    }


def _scenario_subprocess(
    backend: str,
    *,
    rows: int,
    columns: int,
    repeats: int,
) -> dict[str, Any]:
    """Run one scenario in an isolated process for a meaningful RSS high-water mark."""
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--scenario-backend",
            backend,
            "--rows",
            str(rows),
            "--scenario-columns",
            str(columns),
            "--repeats",
            str(repeats),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def capture(rows: int, wide_columns: int, repeats: int) -> dict[str, Any]:
    """Capture all governed backend/shape scenarios and their acceptance budgets."""
    scenarios = [
        _scenario_subprocess(backend, rows=rows, columns=columns, repeats=repeats)
        for backend in ("polars", "pandas", "pyarrow")
        for columns in (1, wide_columns)
    ]
    return {
        "schema_version": "1.0",
        "method": "canonicalization_performance",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": version("numpy"),
            "pandas": version("pandas"),
            "polars": version("polars"),
            "pyarrow": version("pyarrow"),
            "pandera": version("pandera"),
            "narwhals": version("narwhals"),
        },
        "configuration": {
            "rows": rows,
            "wide_columns": wide_columns,
            "repeats": repeats,
            "timing": "median perf_counter after one warmup",
            "python_memory": "maximum tracemalloc peak across repeats",
            "process_memory": "scenario peak RSS minus post-source baseline",
        },
        "scenarios": scenarios,
        "budgets": _budgets(scenarios),
    }


def main() -> None:
    """Run the benchmark and optionally retain its JSON evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--wide-columns", type=int, default=DEFAULT_WIDE_COLUMNS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scenario-backend", choices=("polars", "pandas", "pyarrow"))
    parser.add_argument("--scenario-columns", type=int)
    args = parser.parse_args()
    if args.rows < 1 or args.wide_columns < 2 or args.repeats < 1:
        parser.error("rows and repeats must be positive; wide-columns must be at least 2")
    if args.scenario_backend:
        if args.scenario_columns is None or args.scenario_columns < 1:
            parser.error("scenario-columns must be positive for a scenario worker")
        print(
            json.dumps(
                benchmark_scenario(
                    args.scenario_backend,
                    rows=args.rows,
                    columns=args.scenario_columns,
                    repeats=args.repeats,
                )
            )
        )
        return
    evidence = capture(args.rows, args.wide_columns, args.repeats)
    payload = json.dumps(evidence, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if evidence["budgets"]["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
