"""Verify an official release in a fresh environment using only the public PyPI index."""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    """Install the exact published version with bounded propagation retries and no source access."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    args = parser.parse_args()
    version = args.version.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Expected a stable three-component package version")
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PIP_", "UV_", "PYTHONPATH", "PYTHONHOME"))
    }
    with TemporaryDirectory(prefix="lss4py-published-") as temporary:
        directory = Path(temporary)
        subprocess.run(
            ["uv", "venv", "--python", sys.executable, str(directory / "venv")],
            check=True,
            env=environment,
        )
        python = directory / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        command = [
            "uv",
            "--no-config",
            "--no-cache",
            "pip",
            "install",
            "--python",
            str(python),
            "--index-url",
            "https://pypi.org/simple",
            f"lss4py=={version}",
        ]
        for attempt in range(6):
            installed = subprocess.run(command, cwd=directory, env=environment, check=False)
            if installed.returncode == 0:
                break
            if attempt == 5:
                installed.check_returncode()
            time.sleep(10)
        check = (
            "import sys, pathlib, importlib.metadata as m, lss4py; "
            "assert m.version('lss4py') == sys.argv[1] == lss4py.__version__; "
            "assert pathlib.Path(lss4py.__file__).resolve().is_relative_to("
            "pathlib.Path(sys.prefix).resolve()); "
            "assert all(callable(getattr(lss4py, name, None)) for name in "
            "('reconstruct_orders', 'select_analysis', 'deadline_performance')); "
            "print('Official PyPI package verified:', lss4py.__version__)"
        )
        subprocess.run(
            [str(python), "-I", "-c", check, version], cwd=directory, env=environment, check=True
        )


if __name__ == "__main__":
    main()
