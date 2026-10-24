"""Standard-library-only bundle validation; also runnable as a standalone JSON validator.

Run ``python _bundle_schema.py saved-bundle.json`` without installing LSS4PY or
any analytical/dataframe dependencies. Validation never imports or executes methods.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class BundleValidationError(ValueError):
    """A portable bundle is malformed, incompatible, or internally inconsistent."""


def _require(condition: bool, message: str) -> None:
    """Raise one portable schema error without dependency-specific exceptions."""
    if not condition:
        raise BundleValidationError(message)


def _text(value: Any) -> bool:
    """Recognize a nonblank JSON string."""
    return isinstance(value, str) and bool(value.strip())


def _number(value: Any) -> bool:
    """Recognize finite JSON numbers while keeping booleans out of numerical fields."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _integer(value: Any) -> bool:
    """Recognize nonnegative count/position integers without floating coercion."""
    return type(value) is int and value >= 0


def _object(value: Any, fields: set[str], label: str) -> None:
    """Reject missing and unknown schema fields explicitly."""
    _require(isinstance(value, dict), f"{label} must be an object.")
    _require(set(value) == fields, f"Unsupported {label} fields.")


def _json_tree(value: Any) -> None:
    """Reject nonportable keys, nonfinite values and arbitrary Python objects."""
    if isinstance(value, dict):
        _require(all(isinstance(k, str) for k in value), "JSON keys must be strings.")
        for item in value.values():
            _json_tree(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _json_tree(item)
    else:
        _require(
            value is None or isinstance(value, (str, bool)) or _number(value),
            "Bundle data must be finite JSON.",
        )


def canonical_json(value: Any) -> str:
    """Encode portable data deterministically for snapshotting and integrity hashes."""
    try:
        _json_tree(value)
    except RecursionError as exc:
        raise BundleValidationError("Cyclic or deeply nested bundle data.") from exc
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


def bundle_fingerprint(value: Any) -> str:
    """Hash canonical JSON for accidental-change detection, not authentication."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _datetime(value: Any, label: str) -> None:
    """Require an explicit valid ISO datetime."""
    _require(_text(value), f"{label} requires a timestamp.")
    _require("T" in value or " " in value, f"{label} requires date and time.")
    try:
        datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise BundleValidationError(f"Invalid {label} timestamp.") from exc


def _notes(value: Any) -> None:
    """Validate analytical assumptions and warnings without replacing their content."""
    _require(isinstance(value, list), "Diagnostics must be a list.")
    for note in value:
        _object(note, {"code", "message", "severity"}, "diagnostic")
        _require(all(_text(v) for v in note.values()), "Diagnostics require nonblank fields.")
        _require(
            note["severity"] in ("info", "warning", "error", "critical"),
            "Unsupported diagnostic severity.",
        )


PROVENANCE_FIELDS = {
    "method",
    "method_version",
    "package_version",
    "backend",
    "parameters",
    "created_at",
    "assumptions",
    "warnings",
    "input_schema_fingerprint",
    "cohort_definition",
}
BASE_FIELDS = {"result_type", "name", "provenance", "interpretation_context", "metadata"}
RESULT_FIELDS = {
    "ProcessMapResult": set(),
    "OrderReconstructionResult": set(),
    "TimingResult": {"values", "unit", "keys", "percentiles"},
    "YieldResult": {"value", "unit", "numerator", "denominator", "method"},
    "DefectYieldResult": {
        "schema_version",
        "yield_fraction",
        "first_time_yield",
        "rolled_throughput_yield",
        "dpmo",
        "defect_count",
        "rework_count",
        "opportunities",
        "units",
        "defects_per_unit",
        "bucket_defects",
        "bucket_rework",
        "bucket_first_time_yields",
    },
    "DescriptiveResult": {
        "mean",
        "median",
        "std",
        "variance",
        "skew",
        "kurtosis",
        "min_value",
        "max_value",
        "percentiles",
        "count",
        "missing",
        "total",
        "modes",
        "mode_frequency",
        "unique_count",
        "range",
        "iqr",
        "mad",
        "coefficient_of_variation",
        "unit",
        "group_keys",
    },
    "CapabilityResult": {
        "cp",
        "cpk",
        "z_score",
        "target",
        "lsl",
        "usl",
        "mean",
        "sigma",
        "count",
        "confidence_level",
        "confidence_interval",
        "method",
        "cpl",
        "cpu",
        "cp_confidence_interval",
        "cpk_confidence_interval",
        "total",
        "missing",
        "unit",
        "variation_estimator",
    },
}
METHODS = {
    "ProcessMapResult": {"map_process"},
    "OrderReconstructionResult": {"reconstruct_orders"},
    "TimingResult": {"lead_time", "wait_time", "process_cycle_efficiency", "takt_time"},
    "YieldResult": {
        "deadline_performance",
        "created_to_booked_yield",
        "booked_to_completed_yield",
        "rolled_yield",
    },
    "DefectYieldResult": {"process_yield"},
    "DescriptiveResult": {"describe"},
    "CapabilityResult": {"capability_indices"},
}


def _provenance(value: Any) -> None:
    """Validate full method, parameter and diagnostic context."""
    _object(value, PROVENANCE_FIELDS, "provenance")
    for name in ("method", "method_version", "package_version"):
        _require(_text(value[name]), f"Provenance requires {name}.")
    _require(value["backend"] in ("pandas", "polars", "pyarrow", "unknown"), "Unknown backend.")
    _require(isinstance(value["parameters"], dict), "Provenance parameters must be an object.")
    _datetime(value["created_at"], "provenance")
    _notes(value["assumptions"])
    _notes(value["warnings"])
    for name in ("input_schema_fingerprint", "cohort_definition"):
        _require(value[name] is None or _text(value[name]), f"Invalid provenance {name}.")


def _numeric_fields(result: dict, names: tuple[str, ...]) -> None:
    """Validate nullable numerical estimates without imposing statistical assumptions."""
    for name in names:
        _require(result[name] is None or _number(result[name]), f"Invalid numeric field: {name}.")


def _percentiles(value: Any) -> None:
    """Validate named percentile estimates when present."""
    if value is not None:
        _require(isinstance(value, dict), "Percentiles must be an object or null.")
        _require(all(_text(k) and _number(v) for k, v in value.items()), "Invalid percentiles.")


def _count_fields(result: dict, names: tuple[str, ...]) -> None:
    """Require exact nonnegative counts."""
    for name in names:
        _require(_integer(result[name]), f"Invalid count: {name}.")


def _sample_counts(result: dict) -> None:
    """Reject inconsistent retained, missing and original sample sizes."""
    _count_fields(result, ("total", "missing"))
    count = result["count"]
    _require(count is None or _integer(count), "Invalid retained count.")
    if count is not None:
        _require(count + result["missing"] == result["total"], "Sample counts disagree.")


def _timing(result: dict) -> None:
    """Keep timing keys aligned and preserve JSON scalar identity without dtype coercion."""
    values, keys = result["values"], result["keys"]
    _require(isinstance(values, list) and all(_number(v) for v in values), "Invalid timing values.")
    _require(
        result["unit"] in ("seconds", "minutes", "hours", "days", "percentage", "ratio"),
        "Unsupported timing unit.",
    )
    if keys is not None:
        _require(isinstance(keys, list) and len(keys) == len(values), "Timing key lengths differ.")
        _require(
            all(isinstance(k, (str, bool)) or _number(k) for k in keys), "Invalid timing keys."
        )
        identities = [canonical_json(k) for k in keys]
        _require(len(set(identities)) == len(identities), "Duplicate timing keys.")
    _percentiles(result["percentiles"])


def _yield(result: dict) -> None:
    """Validate finite scalar yield contracts without inventing funnel denominator semantics."""
    _require(_number(result["value"]), "Yield requires a finite value.")
    _require(result["unit"] in ("fraction", "percentage", "ppm"), "Unsupported yield unit.")
    limits = {"fraction": 1, "percentage": 100, "ppm": 1_000_000}
    _require(0 <= result["value"] <= limits[result["unit"]], "Yield value outside its unit range.")
    for name in ("numerator", "denominator"):
        _require(result[name] is None or _integer(result[name]), f"Invalid yield {name}.")
    if result["denominator"] is not None:
        _require(result["denominator"] > 0, "Yield denominator must be positive.")
    _require(result["method"] is None or _text(result["method"]), "Invalid yield method.")


def _close(actual: Any, expected: float, label: str) -> None:
    """Check internally derived quantities with a documented float64 tolerance."""
    _require(_number(actual), f"Invalid derived field: {label}.")
    _require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), f"Inconsistent {label}.")


def _defect_counts(result: dict) -> None:
    """Validate aligned count buckets and the explicit opportunity denominator."""
    _require(result["schema_version"] == "1.0", "Unsupported defect-yield schema.")
    _count_fields(result, ("defect_count", "rework_count", "opportunities"))
    defects, rework = result["bucket_defects"], result["bucket_rework"]
    _require(
        isinstance(defects, list) and bool(defects) and isinstance(rework, list),
        "Defect yield requires count buckets.",
    )
    _require(len(defects) == len(rework), "Defect/rework bucket lengths differ.")
    _require(all(_integer(v) for v in defects + rework), "Invalid bucket counts.")
    _require(
        sum(defects) == result["defect_count"] and sum(rework) == result["rework_count"],
        "Bucket totals disagree.",
    )
    _require(result["opportunities"] > 0, "Opportunities must be positive.")
    _require(sum(defects) + sum(rework) <= result["opportunities"], "Loss exceeds opportunities.")


def _defect_yield(result: dict) -> None:
    """Verify opportunity estimates and optional actual DPU against retained counts."""
    _defect_counts(result)
    n, d, r = result["opportunities"], result["defect_count"], result["rework_count"]
    factors = [
        (n - a - b) / n
        for a, b in zip(result["bucket_defects"], result["bucket_rework"], strict=True)
    ]
    actual = result["bucket_first_time_yields"]
    _require(isinstance(actual, list) and len(actual) == len(factors), "Invalid bucket yields.")
    for left, right in zip(actual, factors, strict=True):
        _close(left, right, "bucket FTY")
    expected = {
        "yield_fraction": (n - d) / n,
        "first_time_yield": (n - d - r) / n,
        "rolled_throughput_yield": math.prod(factors),
        "dpmo": d / n * 1_000_000,
    }
    for key, value in expected.items():
        _close(result[key], value, key)
    _defect_units(result)


def _defect_units(result: dict) -> None:
    """An actual DPU rate requires a positive explicit unit denominator."""
    units = result["units"]
    if units is None:
        _require(result["defects_per_unit"] is None, "DPU requires units.")
    else:
        _require(_integer(units) and units > 0, "Units must be positive.")
        _close(result["defects_per_unit"], result["defect_count"] / units, "DPU")


def _descriptive(result: dict) -> None:
    """Validate estimates and counts while retaining unavailable values and group identities."""
    _numeric_fields(
        result,
        (
            "mean",
            "median",
            "std",
            "variance",
            "skew",
            "kurtosis",
            "min_value",
            "max_value",
            "range",
            "iqr",
            "mad",
            "coefficient_of_variation",
        ),
    )
    if "measurement_sum" in result:
        _numeric_fields(result, ("measurement_sum",))
    _sample_counts(result)
    _count_fields(result, ("mode_frequency", "unique_count"))
    _require(
        isinstance(result["modes"], list) and all(_number(v) for v in result["modes"]),
        "Invalid modes.",
    )
    _require(isinstance(result["group_keys"], dict), "Group keys must be an object.")
    _require(result["unit"] is None or _text(result["unit"]), "Invalid descriptive unit.")
    _percentiles(result["percentiles"])


def _interval(value: Any) -> None:
    """Require ordered finite interval endpoints or an unavailable interval."""
    if value is not None:
        _require(isinstance(value, list) and len(value) == 2, "Invalid confidence interval.")
        _require(all(_number(v) for v in value), "Invalid confidence interval endpoints.")
        _require(value[0] <= value[1], "Confidence interval endpoints are reversed.")


def _capability(result: dict) -> None:
    """Validate capability output contracts, retaining signed indices and unavailable estimates."""
    _numeric_fields(
        result, ("cp", "cpk", "z_score", "target", "lsl", "usl", "mean", "sigma", "cpl", "cpu")
    )
    _sample_counts(result)
    _require(
        _number(result["confidence_level"]) and 0 < result["confidence_level"] < 1,
        "Invalid confidence level.",
    )
    for name in ("confidence_interval", "cp_confidence_interval", "cpk_confidence_interval"):
        _interval(result[name])
    _require(result["unit"] is None or _text(result["unit"]), "Invalid capability unit.")
    for name in ("method", "variation_estimator"):
        _require(_text(result[name]), f"Invalid capability {name}.")


def _reconstruction(result: dict) -> None:
    """Require inspectable finite reconstruction tables in portable snapshots."""
    metadata = result["metadata"]
    for name in ("orders", "activities", "activity_records", "source_records"):
        table = metadata.get(name)
        _require(isinstance(table, list) and bool(table), f"Missing reconstruction {name}.")
        _require(all(isinstance(row, dict) and row for row in table), "Invalid evidence rows.")
    _require(metadata.get("exclusions") == [], "Reconstruction cannot silently exclude rows.")
    for name in ("unit", "clock", "boundary"):
        _require(_text(metadata.get(name)), f"Missing reconstruction {name}.")
    columns = metadata.get("table_columns")
    _require(isinstance(columns, dict), "Reconstruction table column order is required.")
    for name in ("orders", "activities", "activity_records", "source_records"):
        names = columns.get(name)
        _require(isinstance(names, list) and all(_text(v) for v in names), "Invalid table columns.")
        _require(len(set(names)) == len(names), "Duplicate table columns.")
        _require(all(set(row) == set(names) for row in metadata[name]), "Evidence schema mismatch.")
    _json_tree(metadata)


def _process_map(result: dict) -> None:
    """Validate typed observed nodes and exact direct-follow counts without rediscovery."""
    metadata = result["metadata"]
    nodes, edges = metadata.get("nodes"), metadata.get("edges")
    _require(isinstance(nodes, list) and all(_text(n) for n in nodes), "Invalid discovered nodes.")
    _require(len(set(nodes)) == len(nodes), "Duplicate discovered nodes.")
    _require(isinstance(edges, dict), "Invalid discovered edges.")
    for source, targets in edges.items():
        _require(source in nodes and isinstance(targets, dict), "Unknown discovery source.")
        _require(
            all(
                target in nodes and _integer(count) and count > 0
                for target, count in targets.items()
            ),
            "Invalid discovery transition counts.",
        )
    _json_tree(metadata)


RESULT_CHECKS = {
    "ProcessMapResult": _process_map,
    "OrderReconstructionResult": _reconstruction,
    "TimingResult": _timing,
    "YieldResult": _yield,
    "DefectYieldResult": _defect_yield,
    "DescriptiveResult": _descriptive,
    "CapabilityResult": _capability,
}


def validate_result(result: Any) -> None:
    """Validate a complete current typed analytical payload without importing its runtime."""
    _require(isinstance(result, dict), "Result must be an object.")
    kind = result.get("result_type")
    _require(isinstance(kind, str) and kind in RESULT_FIELDS, "Unsupported result type.")
    fields = BASE_FIELDS | RESULT_FIELDS[kind]
    # Additive describe 1.1 field; older saved results restore with an unavailable sum.
    if kind == "DescriptiveResult" and "measurement_sum" in result:
        fields = fields | {"measurement_sum"}
    _object(result, fields, "result")
    _require(_text(result["name"]), "Result name is required.")
    _require(isinstance(result["metadata"], dict), "Result metadata must be an object.")
    _require(
        result["interpretation_context"] is None or _text(result["interpretation_context"]),
        "Invalid result interpretation context.",
    )
    _provenance(result["provenance"])
    _require(result["provenance"]["method"] in METHODS[kind], "Result/method mismatch.")
    RESULT_CHECKS[kind](result)


LEGACY_FIELDS = {
    "bundle_type",
    "bundle_version",
    "name",
    "package_version",
    "created_at",
    "cohort_definition",
    "specification_metadata",
    "interpretation_notes",
    "metadata",
    "results",
}
AUDIT_FIELDS = (LEGACY_FIELDS - {"specification_metadata"}) | {
    "inputs",
    "specifications",
    "software_versions",
    "context",
    "sha256",
}
SPEC_FIELDS = {
    "name",
    "unit",
    "direction",
    "target",
    "lsl",
    "usl",
    "defect_definition",
    "opportunity_definition",
    "opportunities_per_unit",
    "group_by",
    "cohort",
    "time_window",
    "decision_context",
    "schema_version",
}


def _bundle_header(body: dict) -> None:
    """Validate shared bundle metadata for legacy and audited formats."""
    for name in ("name", "package_version"):
        _require(_text(body[name]), f"Bundle requires {name}.")
    _datetime(body["created_at"], "bundle")
    _require(isinstance(body["metadata"], dict), "Bundle metadata must be an object.")
    for name in ("cohort_definition", "interpretation_notes"):
        _require(body[name] is None or _text(body[name]), f"Invalid {name}.")


def _inputs(inputs: Any) -> None:
    """Require explicitly selected, fingerprinted input artifacts with unique identifiers."""
    _require(isinstance(inputs, dict) and bool(inputs), "Audited bundles require inputs.")
    for identifier, item in inputs.items():
        _require(_text(identifier), "Input ids must be nonblank.")
        _object(item, {"reference", "sha256", "selection", "media_type"}, "input reference")
        for field in ("reference", "selection", "media_type"):
            _require(_text(item[field]), f"Input requires {field}.")
        _require(
            isinstance(item["sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None,
            "Input SHA-256 must contain 64 lowercase hexadecimal characters.",
        )


def _specification(spec: Any) -> None:
    """Validate the supported CTQ declaration with no dataframe or analytical runtime."""
    _object(spec, SPEC_FIELDS, "specification")
    _require(spec["schema_version"] == "1.0", "Unsupported specification schema.")
    _require(_text(spec["name"]) and _text(spec["unit"]), "Specification requires name and unit.")
    _require(spec["direction"] in ("lower", "higher", "target"), "Invalid specification direction.")
    _numeric_fields(spec, ("target", "lsl", "usl"))
    _spec_limits(spec)
    _spec_context(spec)


def _spec_limits(spec: dict) -> None:
    """Require ordered limits and a target inside the declared specification."""
    lo, hi, target = spec["lsl"], spec["usl"], spec["target"]
    if lo is not None and hi is not None:
        _require(lo < hi, "Specification limits are reversed.")
    if spec["direction"] == "target":
        _require(target is not None, "Target direction requires a target.")
    if target is not None:
        _require(lo is None or target >= lo, "Target is below specification.")
        _require(hi is None or target <= hi, "Target is above specification.")


def _spec_context(spec: dict) -> None:
    """Check opportunity and observation-window declarations without applying them."""
    for name in ("defect_definition", "opportunity_definition", "cohort", "decision_context"):
        _require(spec[name] is None or _text(spec[name]), f"Invalid specification {name}.")
    count = spec["opportunities_per_unit"]
    if count is not None:
        _require(
            _integer(count) and count > 0 and _text(spec["opportunity_definition"]),
            "Invalid specification opportunities.",
        )
    groups = spec["group_by"]
    _require(isinstance(groups, list) and all(_text(v) for v in groups), "Invalid group columns.")
    _require(len(set(groups)) == len(groups), "Duplicate group columns.")
    if spec["time_window"] is not None:
        _window(spec["time_window"])


def _window(window: Any) -> None:
    """Validate ISO window endpoints and compatible awareness."""
    _object(window, {"start", "end"}, "window")
    _require(any(v is not None for v in window.values()), "Window requires an endpoint.")
    for value in window.values():
        if value is not None:
            _datetime(value, "window")
    if all(v is not None for v in window.values()):
        start, end = (datetime.fromisoformat(window[k]) for k in ("start", "end"))
        _require(
            (start.utcoffset() is None) == (end.utcoffset() is None), "Mixed window awareness."
        )
        _require(start < end, "Window endpoints are reversed.")


def _references(value: Any, available: dict, label: str, *, required: bool = False) -> None:
    """Reject dangling and duplicate relationships between results and declared artifacts."""
    _require(
        isinstance(value, list) and all(_text(v) for v in value), f"Invalid {label} references."
    )
    _require(len(set(value)) == len(value), f"Duplicate {label} references.")
    _require(set(value) <= set(available), f"Unknown {label} reference.")
    if required:
        _require(bool(value), f"Result requires {label} references.")


def _versions(versions: Any, package_version: str) -> None:
    """Record explicit software versions including the analytical package identity."""
    _require(isinstance(versions, dict) and bool(versions), "Software versions are required.")
    _require(all(_text(k) and _text(v) for k, v in versions.items()), "Invalid software versions.")
    _require(
        {"lss4py", "numpy", "narwhals"} <= set(versions), "Missing analytical software versions."
    )
    _require(
        versions.get("lss4py") == package_version,
        "Bundle package version differs from software context.",
    )


def _result_context(entry: dict, body: dict) -> None:
    """Check saved versions and specifications against the recorded context."""
    result = entry["result"]
    _require(
        result["provenance"]["package_version"] == body["package_version"],
        "Result package version differs from bundle.",
    )
    backend = result["provenance"]["backend"]
    if backend != "unknown":
        _require(backend in body["software_versions"], "Missing input backend software version.")
    for package in ("numpy", "scipy", "narwhals"):
        version = result["metadata"].get(f"{package}_version")
        if version is not None:
            _require(
                body["software_versions"].get(package) == version,
                f"Missing or conflicting software version: {package}.",
            )
    parameters = result["provenance"]["parameters"]
    for package, recorded in parameters.get("runtime_versions", {}).items():
        _require(
            body["software_versions"].get(package) == recorded,
            f"Missing or conflicting software version: {package}.",
        )
    if "backend_version" in parameters:
        _require(
            body["software_versions"].get(backend) == parameters["backend_version"],
            "Conflicting backend software version.",
        )
    _parameter_context(result)
    declared = result["provenance"]["parameters"].get("specification")
    if declared is not None:
        linked = [body["specifications"][k] for k in entry["specification_ids"]]
        _require(declared in linked, "Result specification is not preserved by its links.")
        _spec_result_context(result, declared)


def _parameter_context(result: dict) -> None:
    """Keep output units and defect denominators consistent with saved method arguments."""
    parameters = result["provenance"]["parameters"]
    if "unit" in parameters and "unit" in result:
        _require(result["unit"] == parameters["unit"], "Result unit differs from parameters.")
    if result["result_type"] == "DefectYieldResult":
        for name in ("opportunities", "units"):
            if name in parameters:
                _require(
                    result[name] == parameters[name], f"Result {name} differs from parameters."
                )


def _spec_result_context(result: dict, declared: dict) -> None:
    """Preserve capability units and acceptance limits without recomputing estimates."""
    if result["result_type"] == "CapabilityResult":
        for name in ("unit", "target", "lsl", "usl"):
            _require(result[name] == declared[name], f"Result specification {name} differs.")


def _audited(body: dict) -> None:
    """Validate artifact relationships, versioned typed results and the snapshot hash."""
    _require(_text(body["cohort_definition"]), "Audited bundles require a cohort definition.")
    _inputs(body["inputs"])
    _versions(body["software_versions"], body["package_version"])
    _require(isinstance(body["context"], dict), "Bundle context must be an object.")
    _require(isinstance(body["specifications"], dict), "Specifications must be an object.")
    for identifier, spec in body["specifications"].items():
        _require(_text(identifier), "Specification ids must be nonblank.")
        _specification(spec)
    _entries(body)
    expected = bundle_fingerprint({k: v for k, v in body.items() if k != "sha256"})
    _require(body["sha256"] == expected, "Bundle fingerprint mismatch.")


def _entries(body: dict) -> None:
    """Validate every current result and its explicit input/specification associations."""
    results = body["results"]
    _require(isinstance(results, dict) and bool(results), "Bundle requires named results.")
    for identifier, entry in results.items():
        _require(_text(identifier), "Result ids must be nonblank.")
        _object(
            entry, {"schema_version", "result", "input_ids", "specification_ids"}, "result entry"
        )
        _require(entry["schema_version"] == "1.0", "Unsupported result schema version.")
        validate_result(entry["result"])
        _references(entry["input_ids"], body["inputs"], "input", required=True)
        _references(entry["specification_ids"], body["specifications"], "specification")
        _result_context(entry, body)


def validate_bundle(value: Any) -> dict:
    """Return detached validated finite JSON data; never load sources or execute methods.

    Version 1.0 is legacy storage without complete audit context. Version 2.0
    requires inputs, selections, software versions and typed result relationships.
    Unknown versions and fields are rejected rather than silently migrated.
    """
    try:
        if isinstance(value, str):
            value = json.loads(value, object_pairs_hook=_unique_object)
        body = json.loads(canonical_json(value))
    except (TypeError, ValueError, RecursionError) as exc:
        raise BundleValidationError(f"Invalid bundle JSON: {exc}") from exc
    _require(isinstance(body, dict), "Bundle must be an object.")
    version = body.get("bundle_version")
    _require(version in ("1.0", "2.0"), "Unsupported bundle schema version.")
    _object(body, LEGACY_FIELDS if version == "1.0" else AUDIT_FIELDS, "bundle")
    _require(body["bundle_type"] == "AnalysisBundle", "Invalid bundle type.")
    _bundle_header(body)
    if version == "1.0":
        _legacy(body)
    else:
        _audited(body)
    return body


def _unique_object(items: list[tuple[str, Any]]) -> dict:
    """Reject duplicate JSON object members instead of silently keeping the last value."""
    result = {}
    for key, value in items:
        _require(key not in result, f"Duplicate JSON field: {key}.")
        result[key] = value
    return result


def _legacy(body: dict) -> None:
    """Restore the original skeleton's complete results without inventing missing audit data."""
    results = body["results"]
    _require(isinstance(results, list) and bool(results), "Legacy bundle requires results.")
    for result in results:
        validate_result(result)
    _require(
        body["specification_metadata"] is None or isinstance(body["specification_metadata"], dict),
        "Legacy specification metadata must be an object or null.",
    )


def main() -> None:
    """Validate one saved bundle using only the Python standard library."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        body = validate_bundle(args.bundle.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, BundleValidationError) as exc:
        parser.exit(1, f"Invalid bundle: {exc}\n")
    print(
        json.dumps(
            {
                "valid": True,
                "bundle_version": body["bundle_version"],
                "audited": body["bundle_version"] == "2.0",
                "results": len(body["results"]),
            }
        )
    )


if __name__ == "__main__":
    main()
