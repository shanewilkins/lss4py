"""Compare isolated base installation footprint before and after Pandera adoption."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

from capture_base_install import capture as capture_base_install
from compare_canonicalization_cost import BASELINE_REVISION


def _extract_revision(root: Path, revision: str, destination: Path) -> None:
    archive = subprocess.run(
        ["git", "archive", revision],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(destination, filter="data")


def capture(root: Path, repeats: int) -> dict:
    """Build isolated baseline/current wheels and compare their base installations."""
    with tempfile.TemporaryDirectory(prefix="lss4py-phase1-package-") as directory:
        baseline_root = Path(directory)
        _extract_revision(root, BASELINE_REVISION, baseline_root)
        before = capture_base_install(baseline_root, repeats)
    after = capture_base_install(root, repeats)
    before_packages = set(before["installed_packages"])
    after_packages = set(after["installed_packages"])
    return {
        "schema_version": "1.0",
        "method": "base_install_cost_comparison",
        "baseline_revision": BASELINE_REVISION,
        "before": before,
        "after": after,
        "differences": {
            "wheel_size_bytes": after["wheel"]["size_bytes"] - before["wheel"]["size_bytes"],
            "installed_package_count": (
                after["installed_package_count"] - before["installed_package_count"]
            ),
            "added_packages": sorted(after_packages - before_packages),
            "removed_packages": sorted(before_packages - after_packages),
            "import_median_seconds": (
                after["import_time"]["median_seconds"] - before["import_time"]["median_seconds"]
            ),
            "import_median_ratio": (
                after["import_time"]["median_seconds"] / before["import_time"]["median_seconds"]
            ),
        },
    }


def main() -> None:
    """Capture and optionally retain the before/after packaging comparison."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    evidence = capture(root, args.repeats)
    payload = json.dumps(evidence, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
