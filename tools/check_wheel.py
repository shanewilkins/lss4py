"""Build a wheel and exercise customer workflows in an isolated installation."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run(*command: str, cwd: Path) -> None:
    """Run a required check, keeping its output and failing on any error."""
    print(f"\nRunning: {' '.join(command)}", flush=True)
    environment = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        environment.pop(key, None)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["MPLCONFIGDIR"] = str(cwd / ".matplotlib")
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def main() -> None:
    """Test base and pandas-extra installs outside the checkout using locked dependencies."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ecosystem", action="store_true", help="Also test released FLO and plotting extras"
    )
    parser.add_argument(
        "--storage", action="store_true", help="Also exercise installed Arrow/storage contracts"
    )
    parser.add_argument("--artifacts-dir", type=Path, help="Retain ecosystem evidence and graphics")
    args = parser.parse_args()
    if args.artifacts_dir:
        os.environ["LSS4PY_E2E_ARTIFACTS"] = str(args.artifacts_dir.resolve())
    with TemporaryDirectory(prefix="lss4py-wheel-") as directory:
        workspace = Path(directory)
        run("uv", "build", "--wheel", "--out-dir", str(workspace / "dist"), cwd=root)
        constraints = workspace / "constraints.txt"
        run(
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
        (wheel,) = (workspace / "dist").glob("*.whl")
        environment = workspace / "venv"
        run("uv", "venv", "--python", sys.executable, str(environment), cwd=workspace)
        executable_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        python = str(executable_dir / ("python.exe" if os.name == "nt" else "python"))
        suite = workspace / "e2e"
        shutil.copytree(root / "e2e", suite)
        shutil.copytree(root / "examples" / "white_belt", suite / "fixtures" / "white_belt")
        shutil.copytree(root / "tests" / "fixtures" / "ecosystem", suite / "ecosystem" / "fixtures")
        install = ("uv", "pip", "install", "--python", python, "--constraint", str(constraints))
        run(*install, str(wheel), "pytest", cwd=workspace)
        test = (python, "-I", "-m", "pytest", "-q", "--strict-markers", str(suite))
        run(*test, cwd=workspace)
        run(*install, f"{wheel}[pandas]", cwd=workspace)
        run(*test, "--with-pandas", cwd=workspace)
        if args.storage or args.ecosystem:
            run(*install, f"{wheel}[pandas,storage]", cwd=workspace)
            run(*test, "--with-pandas", "--with-storage", cwd=workspace)
        if args.ecosystem:
            run(*install, f"{wheel}[integration,visualization]", cwd=workspace)
            run(*test, "--with-pandas", "--with-storage", "--ecosystem", cwd=workspace)


if __name__ == "__main__":
    main()
