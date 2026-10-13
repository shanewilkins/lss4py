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

FLO_VERSION = "0.4.2"
CONTRACT_VERSION = "1.0"
NODE_KINDS = {"start", "end", "task", "queue", "decision", "parallel_split", "parallel_join"}


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


def _nodes(payload: dict) -> dict[str, dict]:
    """Reject topology whose meaning the first projection cannot represent."""
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValidationError("FLO export requires nonempty nodes.")
    indexed = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise ValidationError("FLO nodes must be objects.")
        identifier = nonblank(node.get("id"), "node id")
        if identifier in indexed:
            raise ValidationError(f"Duplicate FLO node id: {identifier}")
        if (
            node.get("kind") not in NODE_KINDS
            or node.get("subprocess_parent") is not None
            or node.get("branch") is not None
        ):
            raise ValidationError(f"Unsupported FLO node semantics: {identifier}")
        indexed[identifier] = node
    return indexed


def _edges(payload: dict, nodes: dict[str, dict]) -> list[dict]:
    """Validate references and reject unsupported routing rather than flatten it."""
    edges = payload.get("edges")
    if not isinstance(edges, list):
        raise ValidationError("FLO export requires edges.")
    for edge in edges:
        _validate_edge(edge, nodes)
    return edges


def _validate_edge(edge: Any, nodes: dict[str, dict]) -> None:
    """Check one edge's references and supported selection semantics."""
    if not isinstance(edge, dict):
        raise ValidationError("FLO edges must be objects.")
    if edge.get("source") not in nodes or edge.get("target") not in nodes:
        raise ValidationError("FLO edge references an unknown step.")
    if edge.get("route") is not None:
        raise ValidationError("Unsupported FLO route semantics.")
    if edge.get("edge_type") not in (None, "sequence", "rework", "handoff"):
        raise ValidationError("Unsupported FLO edge type.")
    _edge_flags(edge)


def _edge_flags(edge: dict) -> None:
    """Require explicit boolean flags and textual branch outcomes."""
    for name in ("rework", "handoff"):
        if name in edge and not isinstance(edge[name], bool):
            raise ValidationError(f"FLO {name} must be boolean.")
    if edge.get("outcome") is not None:
        nonblank(edge["outcome"], "edge outcome")


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
        if not isinstance(body, dict) or set(body) != {
            "schema_version",
            "flo_version",
            "source",
            "model_revision",
            "export",
            "step_mapping",
        }:
            raise ValidationError("Invalid process projection fields.")
        if body["schema_version"] != CONTRACT_VERSION or body["flo_version"] != FLO_VERSION:
            raise ValidationError("Unsupported process schema or FLO version.")
        nonblank(body["source"], "source namespace")
        nonblank(body["model_revision"], "model revision")
        payload = body["export"]
        if not isinstance(payload, dict) or not isinstance(payload.get("process"), dict):
            raise ValidationError("Invalid FLO process export.")
        nonblank(payload["process"].get("id"), "process id")
        nonblank(payload["process"].get("name"), "process name")
        nodes = _nodes(payload)
        _edges(payload, nodes)
        self._validate_mapping(body["step_mapping"], nodes)
        object.__setattr__(self, "_json", strict_json(body))

    @staticmethod
    def _validate_mapping(mapping: Any, nodes: dict[str, dict]) -> None:
        """Require unambiguous source activity to declared-step associations."""
        if not isinstance(mapping, dict) or not mapping:
            raise ValidationError("An explicit nonempty step mapping is required.")
        for source, target in mapping.items():
            nonblank(source, "source activity id")
            nonblank(target, "target step id")
            if target not in nodes:
                raise ValidationError(f"Mapping references an unknown step: {target}")
        if len(set(mapping.values())) != len(mapping):
            raise ValidationError("Ambiguous many-to-one step mapping is unsupported.")

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
