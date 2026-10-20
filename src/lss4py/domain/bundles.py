"""Versioned general bundles with explicit audit context and real typed restoration."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from lss4py._bundle_schema import (
    BundleValidationError,
    bundle_fingerprint,
    canonical_json,
)
from lss4py._bundle_schema import (
    validate_bundle as _validate_bundle,
)
from lss4py.errors import ValidationError

from ._result_io import restore_result
from .specification import Specification

if TYPE_CHECKING:
    from .results import AnalyticalResult


def validate_bundle(value: Any) -> dict:
    """Validate portable saved evidence using the package's standard error hierarchy."""
    try:
        return _validate_bundle(value)
    except BundleValidationError as exc:
        raise ValidationError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class InputReference:
    """An input artifact's exact byte identity and explicitly declared selection."""

    reference: str
    sha256: str
    selection: str
    media_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        """Validate identifiers and the SHA-256 digest without reading any source."""
        import re

        for name in ("reference", "selection", "media_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"Input {name} must be nonblank text.")
        if not isinstance(self.sha256, str) or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None:
            raise ValidationError("Input sha256 requires 64 lowercase hexadecimal characters.")

    @classmethod
    def from_bytes(
        cls,
        reference: str,
        content: bytes,
        *,
        selection: str,
        media_type: str = "application/octet-stream",
    ) -> InputReference:
        """Fingerprint caller-supplied bytes; never resolve paths or fetch remote resources."""
        if not isinstance(content, bytes):
            raise ValidationError("Source snapshots must be bytes.")
        return cls(reference, hashlib.sha256(content).hexdigest(), selection, media_type)

    def verify(self, content: bytes) -> None:
        """Reject missing/wrong source bytes before the caller explicitly reruns an analysis."""
        if not isinstance(content, bytes) or hashlib.sha256(content).hexdigest() != self.sha256:
            raise ValidationError(f"Input fingerprint mismatch: {self.reference}")


@dataclass(slots=True)
class AnalysisBundle:
    """Container for typed results; capture creates a detached audited v2 snapshot.

    Direct construction retains the legacy v1 format for compatibility. Audited
    capture requires explicit source, cohort, software and result-link context.
    Exports are validated and detached; edits to the object create a new snapshot.
    """

    name: str
    results: list[AnalyticalResult]
    bundle_version: str = "1.0"
    package_version: str = "0.1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    cohort_definition: str | None = None
    specification_metadata: dict[str, Any] | None = None
    interpretation_notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, InputReference] = field(default_factory=dict)
    result_ids: tuple[str, ...] = ()
    result_inputs: dict[str, tuple[str, ...]] = field(default_factory=dict)
    software_versions: dict[str, str] = field(default_factory=dict)
    specifications: dict[str, Specification] = field(default_factory=dict)
    result_specifications: dict[str, tuple[str, ...]] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def capture(
        cls,
        name: str,
        *,
        results: Mapping[str, AnalyticalResult],
        inputs: Mapping[str, InputReference],
        result_inputs: Mapping[str, list[str] | tuple[str, ...]],
        cohort_definition: str,
        software_versions: Mapping[str, str],
        specifications: Mapping[str, Specification] | None = None,
        result_specifications: Mapping[str, list[str] | tuple[str, ...]] | None = None,
        context: dict[str, Any] | None = None,
        interpretation_notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AnalysisBundle:
        """Capture computed results with explicit artifact links, never recompute or select data."""
        if not isinstance(results, Mapping) or not isinstance(inputs, Mapping):
            raise ValidationError("Named results and inputs must be mappings.")
        versions = dict(software_versions)
        bundle = cls(
            name=name,
            results=list(results.values()),
            bundle_version="2.0",
            package_version=versions.get("lss4py", ""),
            cohort_definition=cohort_definition,
            inputs=dict(inputs),
            result_ids=tuple(results),
            result_inputs=_links(result_inputs),
            software_versions=versions,
            specifications=dict(specifications or {}),
            result_specifications=_links(result_specifications or {}),
            context=context or {},
            interpretation_notes=interpretation_notes,
            metadata=metadata or {},
        )
        return cls.from_dict(bundle.to_dict())

    @property
    def audited(self) -> bool:
        """Whether this object exports the complete v2 audit contract."""
        return self.bundle_version == "2.0"

    def to_dict(self) -> dict[str, Any]:
        """Create a finite, validated, detached snapshot and hash the audited format."""
        try:
            body = _body(self)
            if self.audited:
                body["sha256"] = bundle_fingerprint(body)
            return _validate_bundle(body)
        except (BundleValidationError, TypeError, AttributeError, ValueError) as exc:
            raise ValidationError(f"Invalid analysis bundle: {exc}") from exc

    def to_json(self) -> str:
        """Export deterministic strict JSON including the v2 accidental-change hash."""
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisBundle:
        """Restore every typed result and its original provenance, preserving schema version."""
        try:
            body = _validate_bundle(data)
        except BundleValidationError as exc:
            raise ValidationError(str(exc)) from exc
        return _restore(cls, body)

    @classmethod
    def from_json(cls, value: str) -> AnalysisBundle:
        """Validate strict saved JSON before reconstructing supported result models."""
        try:
            body = _validate_bundle(value)
        except BundleValidationError as exc:
            raise ValidationError(str(exc)) from exc
        return _restore(cls, body)

    def get_result(self, identifier: str) -> AnalyticalResult:
        """Restore a detached named result without executing any analytical method."""
        body = self.to_dict()
        if not self.audited:
            raise ValidationError("Named results require an audited v2 bundle.")
        if identifier not in body["results"]:
            raise ValidationError(f"Unknown result id: {identifier}")
        return restore_result(body["results"][identifier]["result"])

    def verify_inputs(self, contents: Mapping[str, bytes]) -> None:
        """Verify all input ids against caller-supplied bytes without any implicit I/O."""
        if not self.audited:
            raise ValidationError("Legacy bundles have no verifiable source context.")
        for identifier, item in self.to_dict()["inputs"].items():
            if identifier not in contents:
                raise ValidationError(f"Missing input snapshot: {identifier}")
            InputReference(**item).verify(contents[identifier])

    def with_audit_context(self, **context: Any) -> AnalysisBundle:
        """Explicitly upgrade legacy results after the caller supplies missing audit evidence."""
        if self.audited:
            raise ValidationError("This bundle already has v2 audit context.")
        audit = dict(context)
        metadata = {
            **self.metadata,
            **audit.pop("metadata", {}),
            "migrated_from_bundle_version": "1.0",
        }
        original = {
            "created_at": self.created_at.isoformat(),
            "package_version": self.package_version,
            "cohort_definition": self.cohort_definition,
            "specification_metadata": self.specification_metadata,
        }
        audit["context"] = {**audit.get("context", {}), "legacy_bundle_context": original}
        return self.capture(
            self.name,
            results={f"result-{i}": r for i, r in enumerate(self.results)},
            metadata=metadata,
            interpretation_notes=self.interpretation_notes,
            **audit,
        )


def _links(value: Mapping) -> dict[str, tuple[str, ...]]:
    """Copy explicit associations without treating strings as identifier sequences."""
    if not isinstance(value, Mapping):
        raise ValidationError("Result links must be mappings.")
    result = {}
    for key, items in value.items():
        if not isinstance(items, (list, tuple)):
            raise ValidationError("Result links must contain lists or tuples of ids.")
        result[key] = tuple(items)
    return result


def _body(bundle: AnalysisBundle) -> dict:
    """Build the supported wire format without discarding unknown audit fields."""
    body = {
        "bundle_type": "AnalysisBundle",
        "bundle_version": bundle.bundle_version,
        "name": bundle.name,
        "package_version": bundle.package_version,
        "created_at": bundle.created_at.isoformat(),
        "cohort_definition": bundle.cohort_definition,
        "interpretation_notes": bundle.interpretation_notes,
        "metadata": bundle.metadata,
    }
    if bundle.audited:
        body.update(_audit_body(bundle))
    else:
        if any(
            (
                bundle.inputs,
                bundle.result_ids,
                bundle.result_inputs,
                bundle.software_versions,
                bundle.specifications,
                bundle.result_specifications,
                bundle.context,
            )
        ):
            raise ValidationError("Audit context requires bundle version 2.0.")
        body.update(
            specification_metadata=bundle.specification_metadata,
            results=[r.to_dict() for r in bundle.results],
        )
    return body


def _audit_body(bundle: AnalysisBundle) -> dict:
    """Require complete result ids and explicit source links for every captured result."""
    ids = bundle.result_ids
    if len(ids) != len(bundle.results) or len(set(ids)) != len(ids):
        raise ValidationError("Result ids must be unique and aligned with results.")
    if set(bundle.result_inputs) != set(ids) or set(bundle.result_specifications) - set(ids):
        raise ValidationError("Result links must reference exactly the captured results.")
    if bundle.specification_metadata is not None:
        raise ValidationError("Use typed specifications for audited bundles.")
    return {
        "inputs": {key: asdict(item) for key, item in bundle.inputs.items()},
        "software_versions": bundle.software_versions,
        "specifications": {key: item.to_dict() for key, item in bundle.specifications.items()},
        "context": bundle.context,
        "results": {
            key: {
                "schema_version": "1.0",
                "result": result.to_dict(),
                "input_ids": list(bundle.result_inputs[key]),
                "specification_ids": list(bundle.result_specifications.get(key, ())),
            }
            for key, result in zip(ids, bundle.results, strict=True)
        },
    }


def _restore(cls: type[AnalysisBundle], body: dict) -> AnalysisBundle:
    """Rebuild legacy or audited objects from already validated portable snapshots."""
    version = body["bundle_version"]
    common = {
        key: body[key]
        for key in (
            "name",
            "bundle_version",
            "package_version",
            "cohort_definition",
            "interpretation_notes",
            "metadata",
        )
    }
    common["created_at"] = datetime.fromisoformat(body["created_at"])
    if version == "1.0":
        return cls(
            **common,
            results=[restore_result(r) for r in body["results"]],
            specification_metadata=body["specification_metadata"],
        )
    return cls(
        **common,
        results=[restore_result(e["result"]) for e in body["results"].values()],
        inputs={key: InputReference(**item) for key, item in body["inputs"].items()},
        result_ids=tuple(body["results"]),
        result_inputs={key: tuple(e["input_ids"]) for key, e in body["results"].items()},
        software_versions=body["software_versions"],
        specifications={
            key: Specification.from_dict(item) for key, item in body["specifications"].items()
        },
        result_specifications={
            key: tuple(e["specification_ids"]) for key, e in body["results"].items()
        },
        context=body["context"],
    )
