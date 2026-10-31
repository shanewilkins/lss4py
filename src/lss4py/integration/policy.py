"""Derive numeric reconstruction policy from FLO classes and analyst conventions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from lss4py.domain import OrderReconstructionPolicy
from lss4py.errors import ValidationError

from .process import ProcessProjection, strict_json


@dataclass(frozen=True, slots=True)
class ReconstructionConventions:
    """Declare measurement rules without duplicating model-owned value classes.

    These rules retain the existing serial-path, parallel-envelope and
    right-first-time reconstruction semantics; topology does not infer them.
    """

    arrival_activity: str
    readiness_activity: str
    required_activities: tuple[str, ...]
    parallel_activities: tuple[str, ...]
    rework_column: str
    rework_value: str
    non_rework_value: str
    correction_activity: str
    cohort: str
    value_add_convention: str
    parallel_load_count_column: str | None = None
    tolerance: float = 1e-8

    def __post_init__(self) -> None:
        """Reuse domain validation and freeze caller-owned activity sequences."""
        checked = OrderReconstructionPolicy(**asdict(self), value_add_activities=())
        for name in ("required_activities", "parallel_activities"):
            object.__setattr__(self, name, getattr(checked, name))


@dataclass(frozen=True, slots=True)
class DerivedReconstructionPolicy:
    """Carry the existing domain policy alongside detached portable attribution."""

    policy: OrderReconstructionPolicy
    _json: str

    def to_dict(self) -> dict:
        """Return detached evidence suitable for analytical result metadata."""
        return json.loads(self._json)

    def to_json(self) -> str:
        """Serialize declarations and attribution without upstream objects."""
        return self._json


def derive_reconstruction_policy(
    projection: ProcessProjection,
    *,
    observed_activities: tuple[str, ...],
    conventions: ReconstructionConventions,
) -> DerivedReconstructionPolicy:
    """Classify every mapped measured task, rejecting omissions and conflicts.

    Mapping keys are observation identities, never FLO display labels. Unmapped
    routing nodes need no class. Modeled durations are never read. Supply the
    distinct activity vocabulary of the observations that will be reconstructed.
    """
    if not isinstance(projection, ProcessProjection) or not isinstance(
        conventions, ReconstructionConventions
    ):
        raise ValidationError("ProcessProjection and ReconstructionConventions are required.")
    body = projection.to_dict()
    _check_observed_activities(observed_activities, body["step_mapping"])
    nodes = {node["id"]: node for node in body["export"]["nodes"]}
    classes = {
        activity: _classification(activity, nodes[step_id], modern=body["flo_version"] == "0.5.0")
        for activity, step_id in body["step_mapping"].items()
    }
    _check_declarations(classes, conventions)
    policy = OrderReconstructionPolicy(
        **asdict(conventions),
        value_add_activities=tuple(a for a in sorted(classes) if classes[a] == "VA"),
        required_non_value_add_activities=tuple(a for a in sorted(classes) if classes[a] == "RNVA"),
    )
    return DerivedReconstructionPolicy(
        policy,
        strict_json(
            {
                "schema_version": "1.0",
                "method": "derive_reconstruction_policy",
                "method_version": "1.0",
                "projection_sha256": projection.digest,
                "source": body["source"],
                "model_revision": body["model_revision"],
                "flo_version": body["flo_version"],
                "observed_activities": sorted(observed_activities),
                "classifications": {
                    activity: {
                        "step_id": body["step_mapping"][activity],
                        "value_class": value,
                        "source_field": (
                            "value_class"
                            if body["flo_version"] == "0.5.0"
                            else "metadata.value_class"
                        ),
                    }
                    for activity, value in classes.items()
                },
                "analyst_conventions": asdict(conventions),
                "policy": policy.to_dict(),
            }
        ),
    )


def _classification(activity: str, node: dict, *, modern: bool = False) -> str:
    """Require explicit supported task metadata without defaulting absent values."""
    label = f"Activity {activity!r}, FLO step {node['id']!r}"
    if node["kind"] != "task":
        raise ValidationError(f"{label}: measured activities must map to task nodes.")
    metadata = node if modern else node.get("metadata")
    field = "value_class" if modern else "metadata.value_class"
    value = metadata.get("value_class") if isinstance(metadata, dict) else None
    if not isinstance(value, str) or value not in {"VA", "RNVA", "NVA"}:
        raise ValidationError(f"{label}: {field} must be VA, RNVA, or NVA.")
    return value


def _check_declarations(classes: dict[str, str], conventions: ReconstructionConventions) -> None:
    """Require mapped policy identities and an explicitly non-value-added correction."""
    referenced = {
        conventions.arrival_activity,
        conventions.readiness_activity,
        conventions.correction_activity,
        *conventions.required_activities,
        *conventions.parallel_activities,
    }
    if missing := referenced - classes.keys():
        raise ValidationError(f"Unmapped analyst activities: {sorted(missing)}")
    if classes[conventions.correction_activity] != "NVA":
        raise ValidationError("Correction activity must have FLO value_class NVA.")


def _check_observed_activities(activities: tuple[str, ...], mapping: dict) -> None:
    """Reject incomplete bindings before unrecognized records can fall back to NVA."""
    if not isinstance(activities, (tuple, list)) or not activities:
        raise ValidationError("observed_activities must be a nonempty sequence of distinct names.")
    if any(not isinstance(a, str) or not a.strip() for a in activities):
        raise ValidationError("observed_activities must contain nonblank strings.")
    if len(set(activities)) != len(activities):
        raise ValidationError("observed_activities must contain distinct names.")
    if missing := set(activities) - mapping.keys():
        raise ValidationError(f"Unmapped observed activities: {sorted(missing)}")
