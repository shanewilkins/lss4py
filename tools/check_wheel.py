"""Exercise a supplied or newly built wheel in an isolated installation."""

import argparse
import hashlib
import json
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


def _select_wheel(supplied: Path | None, workspace: Path, root: Path) -> Path:
    """Use the exact supplied artifact, building only when none was provided."""
    if supplied is not None:
        return supplied
    run("uv", "build", "--wheel", "--out-dir", str(workspace / "dist"), cwd=root)
    (wheel,) = (workspace / "dist").glob("*.whl")
    return wheel


def _study_matrix(
    test: tuple[str, ...],
    install: tuple[str, ...],
    wheel: Path,
    workspace: Path,
    args: argparse.Namespace,
) -> None:
    """Run base and optional installs, retaining a distinct report for each pass."""
    stages: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
        ("base", (), ()),
        ("pandas", ("pandas",), ("--with-pandas",)),
    ]
    if args.storage or args.ecosystem:
        stages.append(("storage", ("pandas", "storage"), ("--with-pandas", "--with-storage")))
    if args.ecosystem:
        stages.append(
            (
                "ecosystem",
                ("pandas", "storage", "integration", "visualization"),
                ("--with-pandas", "--with-storage", "--ecosystem"),
            )
        )
    for name, extras, options in stages:
        requirement = f"{wheel}[{','.join(extras)}]" if extras else str(wheel)
        run(*install, requirement, "pytest", cwd=workspace)
        report = (
            (f"--junitxml={args.artifacts_dir / 'tests' / f'{name}.xml'}",)
            if args.artifacts_dir
            else ()
        )
        run(*test, *options, *report, cwd=workspace)


def main() -> None:
    """Test base and pandas-extra installs outside the checkout using locked dependencies."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, help="Test this exact wheel without rebuilding it")
    parser.add_argument(
        "--ecosystem", action="store_true", help="Also test released FLO and plotting extras"
    )
    parser.add_argument(
        "--storage", action="store_true", help="Also exercise installed Arrow/storage contracts"
    )
    parser.add_argument("--artifacts-dir", type=Path, help="Retain ecosystem evidence and graphics")
    args = parser.parse_args()
    if args.wheel:
        args.wheel = args.wheel.resolve()
        if not args.wheel.is_file() or args.wheel.suffix != ".whl":
            parser.error("--wheel must name an existing .whl file")
    if args.artifacts_dir:
        args.artifacts_dir = args.artifacts_dir.resolve()
        args.artifacts_dir.mkdir(parents=True, exist_ok=True)
        os.environ["LSS4PY_E2E_ARTIFACTS"] = str(args.artifacts_dir)
    with TemporaryDirectory(prefix="lss4py-wheel-") as directory:
        workspace = Path(directory)
        wheel = _select_wheel(args.wheel, workspace, root)
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        if args.artifacts_dir:
            (args.artifacts_dir / "wheel.json").write_text(
                json.dumps({"wheel": wheel.name, "sha256": digest}, indent=2) + "\n"
            )
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
        environment = workspace / "venv"
        run("uv", "venv", "--python", sys.executable, str(environment), cwd=workspace)
        executable_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        python = str(executable_dir / ("python.exe" if os.name == "nt" else "python"))
        suite = workspace / "e2e"
        shutil.copytree(root / "e2e", suite)
        shutil.copytree(root / "examples" / "white_belt", suite / "fixtures" / "white_belt")
        shutil.copytree(root / "tests" / "fixtures" / "ecosystem", suite / "ecosystem" / "fixtures")
        install = ("uv", "pip", "install", "--python", python, "--constraint", str(constraints))
        test = (
            python,
            "-I",
            "-m",
            "pytest",
            "-q",
            "--strict-config",
            "--strict-markers",
            "-o",
            "xfail_strict=true",
            str(suite),
        )
        _study_matrix(test, install, wheel, workspace, args)
        if hashlib.sha256(wheel.read_bytes()).hexdigest() != digest:
            raise ValueError("The tested wheel changed during verification")


if __name__ == "__main__":
    main()
