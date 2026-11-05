"""Shared current analytical contracts for identity, schema and runtime evidence."""

from functools import lru_cache
from importlib.metadata import version

from lss4py._frames import CanonicalFrame
from lss4py.errors import ValidationError


@lru_cache(maxsize=1)
def runtime_versions() -> dict[str, str]:
    """Record the core numerical/compatibility stack used by governed kernels."""
    return {name: version(name) for name in ("numpy", "scipy", "narwhals")}


def schema_fingerprint(frame: CanonicalFrame) -> str:
    """Hash ordered names and semantic dtypes without depending on native dtype spelling."""
    return frame.source_schema_fingerprint


def input_context(frame: CanonicalFrame, parameters: dict) -> dict:
    """Retain source selection, missingness and allocation policy without silently preparing."""
    return {
        "missing": "raise",
        "source_order": "input row positions; pandas index ignored",
        "observation_count": frame.source_row_count,
        "materialization": "eager native input; new numeric arrays; no source mutation",
        "runtime_versions": dict(runtime_versions()),
        "backend_version": version(frame.source_backend),
        **parameters,
    }


def boolean_option(value, name: str) -> None:
    """Reject truthiness coercion for declared analytical boolean options."""
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be boolean.")
