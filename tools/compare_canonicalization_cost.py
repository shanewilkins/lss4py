"""Compare public dataframe performance before and after canonical Polars execution."""

from __future__ import annotations

import argparse
import gc
import io
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import polars as pl
import pyarrow as pa

BASELINE_REVISION = "0c217cd9869b3ec162f1e8ff755655cbca76781c"
DEFAULT_ROWS = 20_000
DEFAULT_WIDE_COLUMNS = 128
DEFAULT_REPEATS = 5


def _records(rows: int, columns: int) -> dict[str, np.ndarray]:
    records = {"value": np.linspace(0.0, 1.0, rows, dtype=np.float64)}
    for index in range(1, columns):
        records[f"unused_{index:03d}"] = np.arange(rows, dtype=np.float64) + index
    return records


def _source(backend: str, records: dict[str, np.ndarray]) -> Any:
    copied = {name: values.copy() for name, values in records.items()}
    if backend == "polars":
        return pl.DataFrame(copied)
    if backend == "pandas":
        return pd.DataFrame(copied)
    if backend == "pyarrow":
        return pa.table(copied)
    raise ValueError(f"Unknown backend: {backend}")


def _rss_mib() -> float:
    peak = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return peak / 1024**2 if sys.platform == "darwin" else peak / 1024


def _measure(operation, repeats: int) -> dict[str, float]:
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
    """Measure only public operations available before and after migration."""
    from lss4py import ColumnRule, DataContract, describe, validate_data

    source = _source(backend, _records(rows, columns))
    contract = DataContract((ColumnRule("value"),))
    baseline_rss = _rss_mib()
    validation = _measure(lambda: validate_data(source, contract=contract), repeats)
    analysis = _measure(lambda: describe(source, column="value"), repeats)
    return {
        "backend": backend,
        "shape": "narrow" if columns == 1 else "wide",
        "rows": rows,
        "source_columns": columns,
        "validation": validation,
        "analysis": analysis,
        "process_peak_rss_delta_mib": max(0.0, _rss_mib() - baseline_rss),
    }


def _extract_revision(root: Path, revision: str, destination: Path) -> None:
    archive = subprocess.run(
        ["git", "archive", revision],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(destination, filter="data")


def _worker(
    script: Path,
    *,
    backend: str,
    rows: int,
    columns: int,
    repeats: int,
    source_root: Path,
) -> dict[str, Any]:
    environment = os.environ.copy()
    prior = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(source_root / "src"), *([prior] if prior else [])]
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--worker-backend",
            backend,
            "--rows",
            str(rows),
            "--worker-columns",
            str(columns),
            "--repeats",
            str(repeats),
        ],
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def _capture(
    label: str,
    source_root: Path,
    *,
    rows: int,
    wide_columns: int,
    repeats: int,
) -> dict[str, Any]:
    script = Path(__file__).resolve()
    scenarios = [
        _worker(
            script,
            backend=backend,
            rows=rows,
            columns=columns,
            repeats=repeats,
            source_root=source_root,
        )
        for backend in ("polars", "pandas", "pyarrow")
        for columns in (1, wide_columns)
    ]
    return {"label": label, "source_root": str(source_root), "scenarios": scenarios}


def _deltas(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    comparisons = []
    for old, new in zip(before["scenarios"], after["scenarios"], strict=True):
        comparison = {"backend": new["backend"], "shape": new["shape"]}
        for operation in ("validation", "analysis"):
            old_time = old[operation]["median_seconds"]
            new_time = new[operation]["median_seconds"]
            old_memory = old[operation]["python_peak_mib"]
            new_memory = new[operation]["python_peak_mib"]
            comparison[operation] = {
                "before_seconds": old_time,
                "after_seconds": new_time,
                "seconds_delta": new_time - old_time,
                "time_ratio": new_time / old_time,
                "before_python_peak_mib": old_memory,
                "after_python_peak_mib": new_memory,
                "python_peak_mib_delta": new_memory - old_memory,
            }
        comparison["process_peak_rss_delta_mib_change"] = (
            new["process_peak_rss_delta_mib"] - old["process_peak_rss_delta_mib"]
        )
        comparisons.append(comparison)
    return comparisons


def capture(root: Path, rows: int, wide_columns: int, repeats: int) -> dict[str, Any]:
    """Compare the Phase 1 baseline source with the current working tree."""
    with tempfile.TemporaryDirectory(prefix="lss4py-phase1-source-") as directory:
        baseline_root = Path(directory)
        _extract_revision(root, BASELINE_REVISION, baseline_root)
        before = _capture(
            BASELINE_REVISION,
            baseline_root,
            rows=rows,
            wide_columns=wide_columns,
            repeats=repeats,
        )
        after = _capture(
            "working-tree",
            root,
            rows=rows,
            wide_columns=wide_columns,
            repeats=repeats,
        )
    return {
        "schema_version": "1.0",
        "method": "canonicalization_cost_comparison",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "configuration": {
            "rows": rows,
            "wide_columns": wide_columns,
            "repeats": repeats,
            "timing": "median perf_counter after one warmup",
            "python_memory": "maximum tracemalloc peak across repeats",
            "process_memory": "scenario peak RSS minus post-source baseline",
        },
        "before": before,
        "after": after,
        "comparisons": _deltas(before, after),
    }


def main() -> None:
    """Run the comparison or one isolated worker scenario."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--wide-columns", type=int, default=DEFAULT_WIDE_COLUMNS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker-backend", choices=("polars", "pandas", "pyarrow"))
    parser.add_argument("--worker-columns", type=int)
    args = parser.parse_args()
    if args.rows < 1 or args.wide_columns < 2 or args.repeats < 1:
        parser.error("rows and repeats must be positive; wide-columns must be at least 2")
    if args.worker_backend:
        if args.worker_columns is None or args.worker_columns < 1:
            parser.error("worker-columns must be positive for a worker")
        print(
            json.dumps(
                benchmark_scenario(
                    args.worker_backend,
                    rows=args.rows,
                    columns=args.worker_columns,
                    repeats=args.repeats,
                )
            )
        )
        return
    evidence = capture(root, args.rows, args.wide_columns, args.repeats)
    payload = json.dumps(evidence, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
