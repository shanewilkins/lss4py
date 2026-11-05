"""Capture isolated base-wheel size, dependency, import, and optional-leakage evidence."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

CORE_PACKAGES = ("pandera", "polars", "narwhals")


def _run(*command: str, cwd: Path, capture: bool = False) -> str:
    """Run one required isolated command with ambient Python overrides removed."""
    environment = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=True,
        text=True,
        capture_output=capture,
    )
    return completed.stdout if capture else ""


def _import_times(python: Path, cwd: Path, repeats: int) -> list[float]:
    """Measure package import inside fresh isolated interpreter processes."""
    code = "import time;s=time.perf_counter();import lss4py;print(time.perf_counter()-s)"
    return [
        float(_run(str(python), "-I", "-c", code, cwd=cwd, capture=True).strip())
        for _ in range(repeats)
    ]


def capture(root: Path, repeats: int) -> dict:
    """Build and inspect one isolated base installation."""
    with TemporaryDirectory(prefix="lss4py-base-evidence-") as directory:
        workspace = Path(directory)
        dist = workspace / "dist"
        _run("uv", "build", "--wheel", "--out-dir", str(dist), cwd=root)
        (wheel,) = dist.glob("*.whl")
        environment = workspace / "venv"
        _run("uv", "venv", "--python", sys.executable, str(environment), cwd=workspace)
        executable_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        python = executable_dir / ("python.exe" if os.name == "nt" else "python")
        constraints = workspace / "constraints.txt"
        _run(
            "uv",
            "export",
            "--locked",
            "--group",
            "dev",
            "--extra",
            "pandas",
            "--extra",
            "integration",
            "--extra",
            "visualization",
            "--extra",
            "storage",
            "--no-emit-project",
            "--no-hashes",
            "--quiet",
            "--output-file",
            str(constraints),
            cwd=root,
        )
        _run(
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--constraint",
            str(constraints),
            str(wheel),
            cwd=workspace,
        )
        probe = (
            "import importlib.metadata as m,importlib.util,json;"
            "a={x.metadata['Name'].lower():x.version for x in m.distributions() "
            "if x.metadata['Name']};d=sorted(x.metadata['Name'] for x in m.distributions() "
            "if x.metadata['Name']);"
            "print(json.dumps({'packages':d,'versions':{n:a.get(n) for n in "
            f"{CORE_PACKAGES!r}"
            "},'pandas_present':importlib.util.find_spec('pandas') is not None,"
            "'pyarrow_present':importlib.util.find_spec('pyarrow') is not None}))"
        )
        installed = json.loads(_run(str(python), "-I", "-c", probe, cwd=workspace, capture=True))
        timings = _import_times(python, workspace, repeats)
        uv_version = _run("uv", "--version", cwd=root, capture=True).strip()
        return {
            "schema_version": "1.0",
            "method": "base_install_evidence",
            "environment": {
                "python": platform.python_version(),
                "builder_uv": uv_version,
                "dependency_source": "uv.lock constraints",
            },
            "wheel": {
                "filename": wheel.name,
                "size_bytes": wheel.stat().st_size,
            },
            "installed_package_count": len(installed["packages"]),
            "installed_packages": installed["packages"],
            "core_versions": installed["versions"],
            "pandas_present": installed["pandas_present"],
            "pyarrow_present": installed["pyarrow_present"],
            "import_time": {
                "repeats": repeats,
                "median_seconds": statistics.median(timings),
                "observations_seconds": timings,
            },
        }


def main() -> None:
    """Capture base-install evidence and optionally retain it as JSON."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    evidence = capture(root, args.repeats)
    if evidence["pandas_present"] or evidence["pyarrow_present"]:
        raise SystemExit("Base installation leaked an optional dataframe backend.")
    payload = json.dumps(evidence, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
