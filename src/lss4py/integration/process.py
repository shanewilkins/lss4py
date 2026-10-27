"""Translate the supported FLO JSON export without importing its implementation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from lss4py.domain import (
    EventLogBindingsIR,
    MetricBindingsIR,
    ProcessEdgeIR,
    ProcessModelIR,
    ProcessStepIR,
)
from lss4py.errors import ValidationError

from ._process_schema import ProjectionEnvelope, validate_projection

FLO_VERSION = "0.4.3"
CONTRACT_VERSION = "1.0"


def strict_json(value: Any) -> str:
    """Snapshot portable data and reject nonfinite or non-JSON values."""
    try:
        return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))
    except (ValueError, TypeError) as exc:
        raise ValidationError("Exchange data must be finite JSON.") from exc


def fingerprint(value: Any) -> str:
    """Fingerprint canonical JSON for accidental-change detection, not authentication."""
    return hashlib.sha256(strict_json(value).encode()).hexdigest()


def nonblank(value: Any, name: str) -> str:
    """Require an explicit identifier, revision or semantic declaration."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be nonblank text.")
    return value


def _validate_references(projection: ProjectionEnvelope) -> None:
    """Keep graph and observation identity rules separate from payload shapes."""
    nodes = set()
    for index, node in enumerate(projection.export.nodes):
        if node.id in nodes:
            raise ValidationError(f"export.nodes.{index}.id: Duplicate FLO node id: {node.id}")
        nodes.add(node.id)
    for index, edge in enumerate(projection.export.edges):
        for field, identifier in (("source", edge.source), ("target", edge.target)):
            if identifier not in nodes:
                raise ValidationError(
                    f"export.edges.{index}.{field}: FLO edge references an unknown step."
                )
    for source, target in projection.step_mapping.items():
        if target not in nodes:
            raise ValidationError(
                f"step_mapping.{source}: Mapping references an unknown step: {target}"
            )
    if len(set(projection.step_mapping.values())) != len(projection.step_mapping):
        raise ValidationError("step_mapping: Ambiguous many-to-one step mapping is unsupported.")


@dataclass(frozen=True, slots=True)
class ProcessProjection:
    """Immutable snapshot of a supported export and explicit source-step mapping."""

    _json: str

    def __post_init__(self) -> None:
        """Validate even direct construction and isolate mutable caller objects."""
        try:
            body = json.loads(self._json)
        except (ValueError, TypeError) as exc:
            raise ValidationError("Invalid process projection JSON.") from exc
        projection = validate_projection(body)
        _validate_references(projection)
        # The typed view is for validation only: retain omissions and all producer data.
        object.__setattr__(self, "_json", strict_json(body))

    @classmethod
    def from_flo_export(
        cls,
        payload: dict,
        *,
        source: str,
        model_revision: str,
        step_mapping: dict[str, str],
        flo_version: str = FLO_VERSION,
    ) -> ProcessProjection:
        """Capture FLO's public JSON export with version and identity declarations."""
        return cls(
            strict_json(
                {
                    "schema_version": CONTRACT_VERSION,
                    "flo_version": flo_version,
                    "source": source,
                    "model_revision": model_revision,
                    "export": payload,
                    "step_mapping": step_mapping,
                }
            )
        )

    def to_dict(self) -> dict:
        """Return a detached portable snapshot without upstream objects."""
        return json.loads(self._json)

    def to_json(self) -> str:
        """Export the versioned exchange contract."""
        return self._json

    @classmethod
    def from_json(cls, value: str) -> ProcessProjection:
        """Restore a portable projection with schema, version and semantic validation."""
        return cls(value)

    @property
    def digest(self) -> str:
        """Identify the exact model revision, mapping and export snapshot."""
        return hashlib.sha256(self._json.encode()).hexdigest()

    def resolve_activity(self, source_id: str) -> str:
        """Resolve an explicit source identity, never a display label or row index."""
        mapping = self.to_dict()["step_mapping"]
        if source_id not in mapping:
            raise ValidationError(f"Unmapped source activity: {source_id}")
        return mapping[source_id]

    def to_process_model(self) -> ProcessModelIR:
        """Project every supported node/edge while retaining source semantics in metadata."""
        body = self.to_dict()
        payload = body["export"]
        nodes = {node["id"]: node for node in payload["nodes"]}
        edges = [self._project_edge(edge, nodes) for edge in payload["edges"]]
        return ProcessModelIR(
            name=payload["process"]["name"],
            steps=[
                ProcessStepIR(
                    id=node["id"], name=node.get("name", node["id"]), metadata={"flo": node}
                )
                for node in payload["nodes"]
            ],
            edges=edges,
            bindings=MetricBindingsIR(
                event_log=EventLogBindingsIR(
                    case_id_column="case_id",
                    step_id_column="step_id",
                    started_at_column="started_at",
                    completed_at_column="completed_at",
                )
            ),
            metadata={
                "process_id": payload["process"]["id"],
                "model_revision": body["model_revision"],
                "projection_sha256": self.digest,
                "source": body["source"],
                "flo_version": body["flo_version"],
            },
        )

    @staticmethod
    def _project_edge(edge: dict, nodes: dict[str, dict]) -> ProcessEdgeIR:
        """Retain rework priority and explicit split/join endpoint meaning."""
        kind = "sequence"
        if edge.get("rework") or edge.get("edge_type") == "rework":
            kind = "rework"
        elif nodes[edge["source"]]["kind"] == "parallel_split":
            kind = "parallel_split"
        elif nodes[edge["target"]]["kind"] == "parallel_join":
            kind = "parallel_join"
        return ProcessEdgeIR(
            source_step_id=edge["source"],
            target_step_id=edge["target"],
            kind=kind,
            condition=edge.get("outcome"),
            metadata={"flo": edge},
        )
