"""Shared current analytical contracts for identity, schema and runtime evidence."""

import hashlib
import json
from functools import lru_cache
from importlib.metadata import version
from math import isfinite

import narwhals as nw
import numpy as np

from lss4py._frames import detect_backend
from lss4py.errors import ValidationError


@lru_cache(maxsize=1)
def runtime_versions() -> dict[str, str]:
    """Record the core numerical/compatibility stack used by governed kernels."""
    return {name: version(name) for name in ("numpy", "scipy", "narwhals")}


def schema_fingerprint(frame: nw.DataFrame) -> str:
    """Hash ordered names and semantic dtypes without depending on native dtype spelling."""
    schema = [(name, _dtype_kind(dtype)) for name, dtype in frame.schema.items()]
    return hashlib.sha256(json.dumps(schema, separators=(",", ":")).encode()).hexdigest()


def _dtype_kind(dtype) -> str:
    """Normalize dtype families across eager backends while retaining semantic roles."""
    if dtype.is_numeric():
        return "numeric"
    if isinstance(dtype, nw.Datetime):
        return f"datetime:{dtype.time_zone}"
    return str(dtype)


def input_context(frame: nw.DataFrame, parameters: dict) -> dict:
    """Retain source selection, missingness and allocation policy without silently preparing."""
    return {
        "missing": "raise",
        "source_order": "input row positions; pandas index ignored",
        "observation_count": len(frame),
        "materialization": "eager native input; new numeric arrays; no source mutation",
        "runtime_versions": dict(runtime_versions()),
        "backend_version": version(detect_backend(frame)),
        **parameters,
    }


def row_identity(frame: nw.DataFrame, key_column: str | None) -> tuple:
    """Preserve unique explicit scalar identities or explicit source positions."""
    metadata = {"row_positions": list(range(len(frame))), "key_column": key_column}
    if key_column is None:
        return None, metadata
    if key_column not in frame.columns:
        raise ValidationError(f"Missing required columns: {key_column}")
    values = frame[key_column].to_list()
    for value in values:
        _key(value)
    identities = [json.dumps(v) for v in values]
    if len(set(identities)) != len(identities):
        raise ValidationError("Explicit row keys must be unique; duplicate keys were supplied.")
    return np.asarray(values, dtype=object), metadata


def _key(value) -> None:
    """Require portable scalar keys, keeping strings, booleans and numbers distinct."""
    if isinstance(value, str) and value.strip():
        return
    if isinstance(value, (bool, int)):
        return
    if isinstance(value, float) and isfinite(value):
        return
    raise ValidationError("Explicit row keys must be nonblank strings or finite scalar numbers.")


def boolean_option(value, name: str) -> None:
    """Reject truthiness coercion for declared analytical boolean options."""
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be boolean.")
