"""Validated reconstruction of existing result types; no method execution or I/O."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import numpy as np

from lss4py._bundle_schema import (
    BundleValidationError,
    canonical_json,
    validate_result,
)
from lss4py.errors import ValidationError


def restore_result(value: Any) -> Any:
    """Validate a neutral snapshot and reconstruct its concrete supported result class."""
    from . import results as models

    try:
        payload = json.loads(canonical_json(value))
        validate_result(payload)
    except (BundleValidationError, TypeError, ValueError) as exc:
        raise ValidationError(f"Invalid analytical result: {exc}") from exc
    kind = payload.pop("result_type")
    payload["provenance"] = restore_provenance(payload["provenance"])
    _restore_arrays(payload, kind)
    return getattr(models, kind)(**payload)


def _restore_arrays(payload: dict, kind: str) -> None:
    """Restore arrays and interval/bucket tuples while preserving scalar key identity."""
    if kind == "TimingResult":
        payload["values"] = np.array(payload["values"])
        keys = payload["keys"]
        payload["keys"] = None if keys is None else np.array(keys, dtype=object)
    if kind == "DefectYieldResult":
        for name in ("bucket_defects", "bucket_rework", "bucket_first_time_yields"):
            payload[name] = tuple(payload[name])
    if kind == "CapabilityResult":
        for name in ("confidence_interval", "cp_confidence_interval", "cpk_confidence_interval"):
            if payload[name] is not None:
                payload[name] = tuple(payload[name])
    if kind == "MeanCIResult":
        payload["confidence_interval"] = tuple(payload["confidence_interval"])
    if kind == "DistributionProfileResult":
        _restore_distribution_arrays(payload)


def _restore_distribution_arrays(payload: dict) -> None:
    """Restore distribution arrays with explicit identity and count dtypes."""
    integer_arrays = {
        "source_positions",
        "histogram_counts",
        "outlier_source_positions",
    }
    for name in (
        "values",
        "source_positions",
        "histogram_edges",
        "histogram_counts",
        "histogram_density",
        "ecdf_values",
        "ecdf_probabilities",
        "qq_theoretical",
        "qq_observed",
        "qq_line_x",
        "qq_line_y",
        "outlier_values",
        "outlier_source_positions",
        "density_x",
        "density_y",
    ):
        payload[name] = np.array(
            payload[name],
            dtype=int if name in integer_arrays else float,
        )
    for name in ("keys", "outlier_keys"):
        payload[name] = None if payload[name] is None else np.array(payload[name], dtype=object)


def restore_provenance(payload: dict) -> Any:
    """Restore the full original timestamp, backend, parameters and diagnostic notes."""
    from .models import AssumptionNote
    from .results import Provenance

    payload = dict(payload)
    payload["created_at"] = datetime.fromisoformat(payload["created_at"])
    for name in ("assumptions", "warnings"):
        payload[name] = [AssumptionNote(**note) for note in payload[name]]
    return Provenance(**payload)
