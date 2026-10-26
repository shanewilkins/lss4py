"""Portable evidence and observed annotations, independent of source and rendering packages."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from lss4py.domain import TimingResult
from lss4py.errors import ValidationError

from .process import CONTRACT_VERSION, ProcessProjection, fingerprint, nonblank, strict_json


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """Reference and content hash identifying the supplied observed data."""

    reference: str
    sha256: str

    def __post_init__(self) -> None:
        """Require a resolvable reference and a hexadecimal SHA-256 digest."""
        nonblank(self.reference, "source reference")
        if not isinstance(self.sha256, str) or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None:
            raise ValidationError("Source sha256 must contain 64 hexadecimal characters.")

    def verify(self, content: bytes) -> None:
        """Verify supplied source bytes without implicit path resolution or data loading."""
        import hashlib

        if hashlib.sha256(content).hexdigest() != self.sha256:
            raise ValidationError(f"Source fingerprint mismatch: {self.reference}")


@dataclass(frozen=True, slots=True)
class MetricAnnotation:
    """An observed scalar already computed for one explicit declared step."""

    result_id: str
    step_id: str
    field: str = "mean"

    def __post_init__(self) -> None:
        """Keep the initial annotation contract deliberately limited to grouped means."""
        nonblank(self.result_id, "result id")
        nonblank(self.step_id, "step id")
        if self.field != "mean":
            raise ValidationError(
                "Unsupported annotation field; only observed means are supported."
            )


def _validate_result(identifier: str, result: dict) -> None:
    """Require portable typed evidence and executable reconstruction for timing results."""
    nonblank(identifier, "result id")
    if not isinstance(result, dict) or result.get("result_type") not in {
        "TimingResult",
        "DescriptiveResult",
    }:
        raise ValidationError("Unsupported analytical result contract.")
    nonblank(result.get("name"), "result name")
    provenance = _validate_provenance(result.get("provenance"))
    if result.get("unit") != provenance["parameters"].get("unit"):
        raise ValidationError("Result unit differs from declared analytical parameters.")
    if result["result_type"] == "TimingResult":
        _validate_timing(result)


def _validate_provenance(provenance: Any) -> dict:
    """Require reproducible method and software context in serialized results."""
    if not isinstance(provenance, dict):
        raise ValidationError("Result requires provenance.")
    required = {
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
    if set(provenance) != required:
        raise ValidationError("Unsupported provenance fields.")
    for name in ("method", "method_version", "package_version", "created_at", "backend"):
        nonblank(provenance.get(name), f"provenance {name}")
    try:
        datetime.fromisoformat(provenance["created_at"])
    except ValueError as exc:
        raise ValidationError("Invalid provenance timestamp.") from exc
    if not isinstance(provenance.get("parameters"), dict):
        raise ValidationError("Result requires explicit parameters.")
    _validate_notes(provenance)
    return provenance


def _validate_notes(provenance: dict) -> None:
    """Validate structured warnings and assumptions without changing them."""
    for name in ("assumptions", "warnings"):
        if not isinstance(provenance.get(name), list):
            raise ValidationError(f"Result requires {name}.")
        for note in provenance[name]:
            if not isinstance(note, dict) or set(note) != {"code", "message", "severity"}:
                raise ValidationError("Invalid diagnostic note.")
            for field in ("code", "message", "severity"):
                nonblank(note[field], f"diagnostic {field}")


def _validate_timing(result: dict) -> None:
    """Preserve explicit case identity, numeric durations and declared units."""
    required = {
        "result_type",
        "name",
        "provenance",
        "interpretation_context",
        "metadata",
        "values",
        "unit",
        "keys",
        "percentiles",
    }
    if set(result) != required:
        raise ValidationError("Unsupported timing result fields.")
    values, keys = result["values"], result["keys"]
    if not isinstance(values, list) or not values:
        raise ValidationError("Timing evidence requires values.")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        raise ValidationError("Timing evidence requires numeric values.")
    _validate_timing_keys(keys, values)
    if result.get("unit") not in {"seconds", "minutes", "hours", "days", "percentage", "ratio"}:
        raise ValidationError("Unsupported timing unit.")


def _validate_timing_keys(keys: Any, values: list) -> None:
    """Require aligned unique keys when timing evidence is keyed by case."""
    if keys is not None:
        if not isinstance(keys, list) or len(keys) != len(values):
            raise ValidationError("Timing key/value lengths differ.")
        for key in keys:
            nonblank(key, "timing key")
        if len(set(keys)) != len(keys):
            raise ValidationError("Duplicate timing keys.")


def _validate_context(body: dict) -> None:
    """Record explicit selection, exclusions and ordering without applying them implicitly."""
    for field in ("cohort", "timezone_policy", "observation_order"):
        nonblank(body[field], field)
    _validate_cohort(body["included_case_ids"], body["exclusions"])
    _validate_versions(body["software_versions"])
    _validate_sources(body["sources"])


def _validate_cohort(cases: Any, exclusions: Any) -> None:
    """Reject ambiguous selection or contradictory included/excluded identities."""
    if not isinstance(cases, list) or not cases or not isinstance(exclusions, list):
        raise ValidationError("Evidence requires included cases and explicit exclusions.")
    for case in cases:
        nonblank(case, "case id")
    excluded = _excluded_cases(exclusions)
    if len(set(cases)) != len(cases) or len(set(excluded)) != len(excluded):
        raise ValidationError("Duplicate cohort case identity.")
    if set(cases) & set(excluded):
        raise ValidationError("A case cannot be included and excluded.")


def _excluded_cases(exclusions: list) -> list[str]:
    """Validate explicit reasons and preserve excluded source identities."""
    excluded = []
    for entry in exclusions:
        if not isinstance(entry, dict) or set(entry) != {"case_id", "reason"}:
            raise ValidationError("Exclusions require case_id and reason.")
        excluded.append(nonblank(entry["case_id"], "excluded case id"))
        nonblank(entry["reason"], "exclusion reason")
    return excluded


def _validate_versions(versions: Any) -> None:
    """Require explicit version labels for all declared software dependencies."""
    if not isinstance(versions, dict) or not versions:
        raise ValidationError("Software versions are required.")
    for package, version in versions.items():
        nonblank(package, "package name")
        nonblank(version, "package version")


def _validate_sources(sources: Any) -> None:
    """Require actual referenced, fingerprinted source evidence."""
    if not isinstance(sources, list) or not sources:
        raise ValidationError("Source evidence is required.")
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"reference", "sha256"}:
            raise ValidationError("Invalid source evidence fields.")
        SourceEvidence(**source)
    references = [source["reference"] for source in sources]
    if len(set(references)) != len(references):
        raise ValidationError("Duplicate source references.")


def _validate_annotations(body: dict, projection: ProcessProjection) -> None:
    """Reject wrong-step associations and invented units or values."""
    annotations = body["annotations"]
    if not isinstance(annotations, list):
        raise ValidationError("Annotations must be a list.")
    steps = {node["id"] for node in projection.to_dict()["export"]["nodes"]}
    seen = set()
    for item in annotations:
        annotation = _validate_annotation(item, body["results"], steps)
        if annotation.result_id in seen:
            raise ValidationError("Duplicate result annotation.")
        seen.add(annotation.result_id)


def _validate_annotation(item: Any, results: dict, steps: set[str]) -> MetricAnnotation:
    """Validate one existing scalar result's exact step association."""
    if not isinstance(item, dict) or set(item) != {"result_id", "step_id", "field"}:
        raise ValidationError("Invalid annotation fields.")
    annotation = MetricAnnotation(**item)
    if annotation.step_id not in steps or annotation.result_id not in results:
        raise ValidationError("Annotation references unknown step or result.")
    result = results[annotation.result_id]
    _validate_annotation_value(result, annotation)
    return annotation


def _validate_annotation_value(result: dict, annotation: MetricAnnotation) -> None:
    """Check grouped-result identity and preserve nullable scalar units/values."""
    if result.get("result_type") != "DescriptiveResult" or result.get("group_keys") != {
        "step_id": annotation.step_id
    }:
        raise ValidationError("Annotation group identity differs from target step.")
    nonblank(result.get("unit"), "annotation unit")
    value = result.get(annotation.field)
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
        raise ValidationError("Annotation must reference a scalar result.")


@dataclass(frozen=True, slots=True)
class EvidenceManifest:
    """Immutable, versioned study snapshot with validated round-trip and fingerprints."""

    _json: str

    def __post_init__(self) -> None:
        """Validate portable evidence and its accidental-change fingerprint."""
        try:
            envelope = json.loads(self._json)
        except (ValueError, TypeError) as exc:
            raise ValidationError("Invalid evidence JSON.") from exc
        if not isinstance(envelope, dict) or set(envelope) != {"evidence", "sha256"}:
            raise ValidationError("Invalid evidence envelope.")
        body = envelope["evidence"]
        if not isinstance(body, dict) or set(body) != {
            "schema_version",
            "process",
            "sources",
            "cohort",
            "included_case_ids",
            "exclusions",
            "timezone_policy",
            "observation_order",
            "software_versions",
            "results",
            "annotations",
        }:
            raise ValidationError("Invalid evidence fields.")
        if body["schema_version"] != CONTRACT_VERSION:
            raise ValidationError("Unsupported evidence schema.")
        if fingerprint(body) != envelope["sha256"]:
            raise ValidationError("Evidence fingerprint mismatch.")
        projection = ProcessProjection(strict_json(body["process"]))
        _validate_context(body)
        self._validate_results(body)
        _validate_annotations(body, projection)
        object.__setattr__(self, "_json", strict_json(envelope))

    @staticmethod
    def _validate_results(body: dict) -> None:
        """Check provenance versions and case keys against the declared study context."""
        if not isinstance(body["results"], dict) or not body["results"]:
            raise ValidationError("Evidence requires analytical results.")
        for identifier, result in body["results"].items():
            _validate_result(identifier, result)
            if result["provenance"]["package_version"] != body["software_versions"].get("lss4py"):
                raise ValidationError("Analytical package version differs from manifest.")
            if (
                result["result_type"] == "TimingResult"
                and result.get("keys") is not None
                and result["keys"] != body["included_case_ids"]
            ):
                raise ValidationError("Timing case identity/order differs from cohort.")
        if body["software_versions"].get("flo-lang") != body["process"]["flo_version"]:
            raise ValidationError("FLO version differs from process projection.")

    @classmethod
    def create(
        cls,
        *,
        process: ProcessProjection,
        sources: list[SourceEvidence],
        cohort: str,
        included_case_ids: list[str],
        exclusions: list[dict[str, str]],
        timezone_policy: str,
        observation_order: str,
        software_versions: dict[str, str],
        results: dict[str, Any],
        annotations: list[MetricAnnotation] | None = None,
    ) -> EvidenceManifest:
        """Capture computed results; never select data, calculate metrics or render."""
        body = {
            "schema_version": CONTRACT_VERSION,
            "process": process.to_dict(),
            "sources": [{"reference": item.reference, "sha256": item.sha256} for item in sources],
            "cohort": cohort,
            "included_case_ids": included_case_ids,
            "exclusions": exclusions,
            "timezone_policy": timezone_policy,
            "observation_order": observation_order,
            "software_versions": software_versions,
            "results": {key: result.to_dict() for key, result in results.items()},
            "annotations": [
                {"result_id": item.result_id, "step_id": item.step_id, "field": item.field}
                for item in annotations or []
            ],
        }
        return cls(strict_json({"evidence": body, "sha256": fingerprint(body)}))

    def to_json(self) -> str:
        """Serialize the exact saved evidence without recomputation."""
        return self._json

    @classmethod
    def from_json(cls, value: str) -> EvidenceManifest:
        """Restore and validate saved evidence without exposing snapshot internals."""
        return cls(value)

    def to_dict(self) -> dict:
        """Return a detached copy of the envelope."""
        return json.loads(self._json)

    def verify_sources(self, contents: dict[str, bytes]) -> None:
        """Check every referenced source against explicit caller-supplied snapshots."""
        for source in self.to_dict()["evidence"]["sources"]:
            if source["reference"] not in contents:
                raise ValidationError(f"Missing source snapshot: {source['reference']}")
            SourceEvidence(**source).verify(contents[source["reference"]])

    def observed_annotations(self) -> list[dict]:
        """Expose explicit observed values without overwriting FLO's modeled metadata."""
        body = self.to_dict()["evidence"]
        return [
            dict(
                item,
                origin="observed",
                value=body["results"][item["result_id"]][item["field"]],
                unit=body["results"][item["result_id"]]["unit"],
                provenance=body["results"][item["result_id"]]["provenance"],
            )
            for item in body["annotations"]
        ]

    def restore_timing(self, result_id: str) -> TimingResult:
        """Restore the supported timing result from saved evidence without executing a kernel."""
        result = self.to_dict()["evidence"]["results"].get(result_id)
        if not result or result["result_type"] != "TimingResult":
            raise ValidationError("Requested result is not timing evidence.")
        return TimingResult.from_dict(result)
