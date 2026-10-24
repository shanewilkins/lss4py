"""Audit inherited v0.1/v0.2 requirement status and reproduce timing release gaps.

This read-only assessment does not execute release commands or waive requirements.
Report JSON encodes nonfinite observations as text so it remains portable.
"""

import argparse
import csv
import hashlib
import inspect
import json
import math
import re
import subprocess
import tomllib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from lss4py import ValidationError, process_cycle_efficiency, takt_time, wait_time

ROOT = Path(__file__).resolve().parents[1]


def catalogs() -> tuple[list[dict], dict]:
    """Validate permanent IDs and traceability without weakening acceptance criteria."""
    records = []
    for name in ("user-requirements", "technical-requirements"):
        with (ROOT / f"docs/requirements/{name}.csv").open(newline="") as stream:
            records.extend(csv.DictReader(stream))
    indexed = {r["id"]: r for r in records}
    if len(indexed) != len(records):
        raise ValueError("Duplicate requirement IDs")
    with (ROOT / "docs/requirements/traceability.csv").open(newline="") as stream:
        links = list(csv.reader(stream))[1:]
    linked_users = set()
    for user, technical in links:
        if user not in indexed or technical not in indexed:
            raise ValueError(f"Unknown traceability endpoint: {user}, {technical}")
        linked_users.add(user)
    if missing := {r["id"] for r in records if r["id"].startswith("UR-")} - linked_users:
        raise ValueError(f"Users without traceability: {sorted(missing)}")
    return records, {"valid": True, "requirements": len(records), "traceability_links": len(links)}


def owned_requirements(records: list[dict]) -> list[dict]:
    """Read exact release ownership from the roadmap, including inherited obligations."""
    roadmap = (ROOT / "docs/roadmap.md").read_text()
    ownership = roadmap.split("## Primary release ownership", 1)[1].split("### Ingestion", 1)[0]
    targets = {}
    for milestone, body in re.findall(r"^- \*\*(v0\.[12]):\*\* (.+)$", ownership, re.MULTILINE):
        targets.update(dict.fromkeys(re.findall(r"(?:UR|TR)-\d{3}", body), milestone))
    rows = []
    for record in records:
        if record["id"] in targets:
            rows.append(
                {
                    **record,
                    "owner": targets[record["id"]],
                    "release_blocker": record["priority"] == "Must"
                    and record["status"] != "Satisfied",
                }
            )
    return rows


def observe(name: str, calculation) -> dict:
    """Capture actual public behavior without turning invalid inputs into passing tests."""
    try:
        result = calculation()
        return {"probe": name, "outcome": "returned", "value": finite_json(result), "passed": False}
    except Exception as exc:  # Diagnostic evidence records the concrete exception type.
        return {
            "probe": name,
            "outcome": "raised",
            "exception": type(exc).__name__,
            "message": str(exc),
            "passed": isinstance(exc, ValidationError),
        }


def finite_json(value):
    """Represent invalid numeric returns explicitly without writing NaN/Infinity JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, list):
        return [finite_json(item) for item in value]
    return value


def timing_findings() -> list[dict]:
    """Reproduce the existing default numeric paths independently of the book route."""

    def waiting(lead, cycle):
        result = wait_time(
            pl.DataFrame({"lead": [lead], "cycle": [cycle]}),
            lead_time_column="lead",
            cycle_time_column="cycle",
        )
        return result.values.tolist()

    return [
        {
            "probe": "wait_time_unit_contract",
            "passed": _wait_unit_supported(),
            "unit_parameter": "unit" in inspect.signature(wait_time).parameters,
            "observed_output_unit": wait_time(
                pl.DataFrame({"lead": [10.0], "cycle": [4.0]}),
                lead_time_column="lead",
                cycle_time_column="cycle",
            ).unit,
            "expected": "Caller can declare the common input/output unit.",
        },
        observe("negative_wait_inputs_lead_minus1_cycle_minus2", lambda: waiting(-1.0, -2.0)),
        observe("nan_wait_input", lambda: waiting(float("nan"), 1.0)),
        observe(
            "infinite_per_row_pce_denominator",
            lambda: process_cycle_efficiency(
                pl.DataFrame({"lead": [float("inf")], "va": [2.0]}),
                lead_time_column="lead",
                value_add_time_column="va",
            ).values.tolist(),
        ),
        observe(
            "infinite_takt_available_time",
            lambda: takt_time(available_time=float("inf"), customer_demand=2),
        ),
    ]


def _wait_unit_supported() -> bool:
    """Verify a unit declaration preserves both numeric values and their label."""
    if "unit" not in inspect.signature(wait_time).parameters:
        return False
    parameters: dict[str, Any] = {
        "lead_time_column": "lead",
        "cycle_time_column": "cycle",
        "unit": "minutes",
    }
    result = wait_time(pl.DataFrame({"lead": [10.0], "cycle": [4.0]}), **parameters)
    return result.unit == "minutes" and result.values.tolist() == [6.0]


def gate_snapshot() -> dict:
    """Check recorded local gate outcomes against the exact reviewed source fingerprints."""
    path = ROOT / "docs/assessments/v02-release-gates.json"
    if not path.exists():
        return {"current": False, "passed": False, "reason": "No local gate snapshot"}
    snapshot = json.loads(path.read_text())
    current = all(
        (ROOT / name).exists() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
        for name, digest in snapshot["source_sha256"].items()
    )
    required = {
        "pre_push",
        "required_arrow",
        "ruff",
        "ty",
        "bandit",
        "import_boundaries",
        "wheel_base",
        "wheel_pandas",
        "wheel_storage",
        "wheel_ecosystem",
        "build",
        "twine",
        "distribution_identity",
        "dependency_audit",
        "migration_example",
        "book_examples",
    }
    passed = required <= {item["name"] for item in snapshot["checks"]} and all(
        item["status"] == "passed" for item in snapshot["checks"]
    )
    return {
        "current": current,
        "passed": passed,
        "reference": "docs/assessments/v02-release-gates.json",
    }


def main() -> None:
    """Save a dated source-fingerprinted audit and list unsatisfied Must requirements."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records, integrity = catalogs()
    rows = owned_requirements(records)
    blockers = [r["id"] for r in rows if r["release_blocker"]]
    probes = timing_findings()
    gates = gate_snapshot()
    local_blockers = [key for key in blockers if key != "TR-038"]
    paths = [
        "docs/roadmap.md",
        "docs/requirements/user-requirements.csv",
        "docs/requirements/technical-requirements.csv",
        "docs/requirements/traceability.csv",
        "src/lss4py/_kernels/timing.py",
        "tools/audit_v02_readiness.py",
        "pyproject.toml",
        "uv.lock",
    ]
    report = {
        "audit_version": "1.1",
        "created_at": datetime.now(UTC).isoformat(),
        "target": "v0.2",
        "package_version": tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
            "version"
        ],
        "checkout_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_state": "Uncommitted working tree; not a release tag.",
        "ready": not blockers and all(probe["passed"] for probe in probes),
        "prepublication_ready": not local_blockers
        and all(probe["passed"] for probe in probes)
        and gates["current"]
        and gates["passed"],
        "prepublication_blockers": local_blockers,
        "postpublication_pending": [key for key in blockers if key == "TR-038"],
        "local_gate_snapshot": gates,
        "decision_basis": "No unsatisfied Must requirement is silently waived or retargeted.",
        "counts": dict(Counter(r["status"] for r in rows)),
        "catalog_integrity": integrity,
        "unsatisfied_must_requirements": blockers,
        "requirements": rows,
        "timing_probes": probes,
        "sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths},
        "gate_evidence": "docs/assessments/v02-release-readiness.md",
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "ready",
                    "prepublication_ready",
                    "counts",
                    "unsatisfied_must_requirements",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
