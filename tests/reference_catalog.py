"""Validate offline numerical-reference manifests; this is private test support."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).parent / "fixtures" / "reference"
R_APIS = {"ss.ca.cp", "ss.ca.cpk", "ss.ca.z", "ss.ca.yield"}
METHODS = {
    "describe",
    "lead_time",
    "wait_time",
    "process_cycle_efficiency",
    "takt_time",
    "created_to_booked_yield",
    "booked_to_completed_yield",
    "rolled_yield",
}


def _require(condition: bool, message: str) -> None:
    """Reject incomplete or inconsistent catalog evidence."""
    if not condition:
        raise ValueError(message)


def _text(value: object) -> bool:
    """Recognize meaningful human-readable metadata."""
    return isinstance(value, str) and bool(value.strip())


def _finite(value: object) -> bool:
    """Accept JSON numbers without treating booleans as estimates."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _artifact(root: Path, artifact: dict) -> bytes:
    """Check local paths and byte checksums before parsing trusted fixture artifacts."""
    _require(set(artifact) == {"path", "sha256"}, "Artifact needs path and sha256")
    _require(_text(artifact["path"]), "Artifact path is required")
    path = (root / artifact["path"]).resolve()
    _require(path.is_relative_to(root.resolve()), "Artifact path escapes the catalog")
    _require(not Path(artifact["path"]).is_absolute(), "Artifact path must be relative")
    contents = path.read_bytes()
    _require(
        hashlib.sha256(contents).hexdigest() == artifact["sha256"], "Artifact checksum mismatch"
    )
    return contents


def _schema(inputs: dict, schema: dict) -> None:
    """Validate row count, names, primitive types, and nullability of test data."""
    _require(set(inputs) == {"columns"}, "Input artifact needs columns")
    columns = inputs["columns"]
    _require(
        isinstance(columns, dict) and bool(columns), "Input columns must be a nonempty mapping"
    )
    _require(set(schema) == {"rows", "fields"}, "Schema needs rows and fields")
    _require(type(schema["rows"]) is int and schema["rows"] >= 0, "Invalid schema row count")
    _require(set(columns) == set(schema["fields"]), "Schema columns mismatch")
    validators = {"number": _finite, "integer": lambda x: type(x) is int, "string": _text}
    for name, values in columns.items():
        field = schema["fields"][name]
        _require(set(field) == {"type", "nullable"}, "Field needs type and nullable")
        _require(
            field["type"] in validators and type(field["nullable"]) is bool, "Invalid field type"
        )
        _require(
            isinstance(values, list) and len(values) == schema["rows"], "Schema row count mismatch"
        )
        for value in values:
            valid = field["nullable"] if value is None else validators[field["type"]](value)
            _require(valid, f"Invalid input value in column '{name}'")


def _source(entry: dict) -> None:
    """Require attribution and distinguish certified, independently derived, and R evidence."""
    source = entry["source"]
    _require(
        source["kind"] in {"published_certified", "independently_derived", "r_sixsigma"},
        "Unknown reference source kind",
    )
    for name in ("author", "citation", "version", "accessed_on", "derivation"):
        _require(_text(source.get(name)), f"Missing source {name}")
    license_info = entry["license"]
    for name in ("identifier", "attribution", "redistribution", "notice"):
        _require(_text(license_info.get(name)), f"Missing license {name}")
    _require(license_info["redistribution"] == "permitted", "Redistribution is not permitted")
    _require(type(entry["semantic_differences"]) is list, "Semantic differences must be explicit")
    _require(
        all(_text(value) for value in entry["semantic_differences"]),
        "Semantic differences must be nonblank text",
    )
    if source["kind"] == "r_sixsigma":
        _r_generation(entry)


def _r_generation(entry: dict) -> None:
    """Require the pinned package, generation context, and executable source artifact."""
    source = entry["source"]
    _require(
        source.get("package") == "SixSigma" and source.get("package_version") == "0.11.1",
        "R parity requires SixSigma 0.11.1",
    )
    for name in ("r_version", "generated_at", "command"):
        _require(_text(source.get(name)), f"Missing R generation evidence: {name}")
    _require("generator" in entry["artifacts"], "R parity needs a checksummed generator artifact")
    _require(bool(entry["invalid_cases_required"]), "R parity needs invalid-input cases")


def _r_cases(cases: list, entry: dict) -> None:
    """Validate captured R responses without claiming a Python implementation."""
    _require(bool(cases), "R reference cases must be nonempty")
    names = [case["id"] for case in cases]
    _require(len(names) == len(set(names)), "Duplicate R case IDs")
    _require(
        {case["method"] for case in cases} == set(entry["intended_analyses"]),
        "R analysis catalog mismatch",
    )
    for case in cases:
        _require(
            case["method"] in R_APIS and case["input_kind"] == "r_arguments",
            "Unsupported R reference API",
        )
        _require(isinstance(case["parameters"], dict), "R arguments must be a mapping")
        _require(_text(case["basis"]), "R case basis required")
        response = case["expected"]
        _require(response["status"] in {"returned", "error"}, "Unknown R response status")
        key = "value" if response["status"] == "returned" else "message"
        _require(key in response, "Incomplete R response")
        _tolerance(case)
        _finite_tree(response)


def _r_provenance(entry: dict, contents: dict) -> None:
    """Match the manifest to captured runtime evidence, without executing R."""
    _require(
        entry.get("validation_status") == "reference_only",
        "R snapshots must be labeled reference_only",
    )
    _require("provenance" in contents, "R runtime provenance artifact required")
    provenance = json.loads(contents["provenance"])
    for name in ("package", "package_version", "r_version", "generated_at", "command"):
        _require(provenance.get(name) == entry["source"].get(name), "R provenance mismatch")
    _require(bool(provenance.get("session_info")), "R session evidence required")
    _require(_text(provenance.get("nonfinite_encoding")), "R nonfinite encoding required")


def _cases(cases: list, entry: dict) -> None:
    """Validate target methods and explicit, finite numerical tolerances."""
    if entry.get("validation_status") == "reference_only":
        _r_cases(cases, entry)
        return
    _require(isinstance(cases, list) and bool(cases), "Expected cases must be nonempty")
    names = [case["id"] for case in cases]
    _require(
        all(_text(name) for name in names) and len(names) == len(set(names)), "Duplicate case IDs"
    )
    _require(
        set(entry["intended_analyses"]) == {case["method"] for case in cases},
        "Intended analyses mismatch expected cases",
    )
    for case in cases:
        _require(case["method"] in METHODS, "Unknown supported analysis")
        _require(case["input_kind"] in {"frame", "scalar"}, "Unknown input kind")
        _require(
            (case["method"] == "takt_time") == (case["input_kind"] == "scalar"),
            "Input kind does not match the method",
        )
        _require(isinstance(case["parameters"], dict), "Case parameters must be a mapping")
        _require(
            isinstance(case["expected"], dict) and bool(case["expected"]),
            "Expected fields required",
        )
        _require(_text(case["basis"]), "Expected values need an independent basis")
        _tolerance(case)
        _finite_tree(case["expected"])


def _tolerance(case: dict) -> None:
    """Require justified, finite absolute and relative numerical tolerances."""
    tolerance = case["tolerance"]
    _require(
        set(tolerance) == {"absolute", "relative"}, "Explicit absolute/relative tolerances required"
    )
    _require(all(_finite(x) and x >= 0 for x in tolerance.values()), "Invalid tolerance")
    _require(_text(case["tolerance_reason"]), "Tolerance justification required")


def _finite_tree(value: object) -> None:
    """Reject nonstandard JSON NaN/Infinity anywhere in expected outputs."""
    if isinstance(value, dict):
        for child in value.values():
            _finite_tree(child)
    elif isinstance(value, list):
        for child in value:
            _finite_tree(child)
    elif type(value) in (int, float):
        _require(_finite(value), "Nonfinite expected output")


def _invalid_cases(cases: list, entry: dict) -> None:
    """Require deterministic error evidence without executable fixture expressions."""
    if entry.get("validation_status") == "reference_only":
        _r_cases(cases, entry)
        return
    _require(isinstance(cases, list), "Invalid cases must be a list")
    _require(bool(cases) or not entry["invalid_cases_required"], "Invalid-input evidence required")
    names = [case["id"] for case in cases]
    _require(
        all(_text(name) for name in names) and len(names) == len(set(names)),
        "Duplicate or blank invalid case IDs",
    )
    for case in cases:
        _require(case["method"] in entry["intended_analyses"], "Invalid case analysis mismatch")
        _require(isinstance(case["columns_override"], dict), "Invalid case needs data overrides")
        _require(isinstance(case["parameters"], dict), "Invalid case parameters must be a mapping")
        _require(
            case["error_type"] == "ValidationError" and _text(case["message"]),
            "Invalid case needs a governed error and message",
        )


def load_catalog(root: Path = ROOT) -> list[dict]:
    """Load a versioned manifest, checking governance and artifact integrity offline."""
    manifest = json.loads((root / "manifest.json").read_text())
    _require(manifest.get("schema_version") == "1.0", "Unsupported catalog schema version")
    entries = manifest["datasets"]
    ids = [entry["id"] for entry in entries]
    _require(
        bool(ids) and len(ids) == len(set(ids)) and all(_text(x) for x in ids),
        "Dataset IDs must be nonempty and unique",
    )
    loaded = []
    for entry in entries:
        _require(
            re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", entry["version"]) is not None,
            "Dataset version must use major.minor.patch",
        )
        _require(
            entry["purpose"] in {"test_fixture", "teaching_dataset"}, "Unknown dataset purpose"
        )
        _source(entry)
        artifacts = entry["artifacts"]
        _require({"inputs", "expected", "invalid"} <= set(artifacts), "Missing fixture artifacts")
        contents = {name: _artifact(root, artifact) for name, artifact in artifacts.items()}
        data = {name: json.loads(contents[name]) for name in ("inputs", "expected", "invalid")}
        if entry["source"]["kind"] == "r_sixsigma":
            _r_provenance(entry, contents)
        _schema(data["inputs"], entry["schema"])
        _cases(data["expected"], entry)
        _invalid_cases(data["invalid"], entry)
        loaded.append({"metadata": entry, **data})
    return loaded
