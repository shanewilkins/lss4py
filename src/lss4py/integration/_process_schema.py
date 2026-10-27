"""Strict shapes for portable process projections, independent of FLO internals."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from pydantic import ValidationError as SchemaError

from lss4py.errors import ValidationError


def _nonblank(value: str) -> str:
    """Reject whitespace-only identifiers without normalizing authored text."""
    if not value.strip():
        raise ValueError("must be nonblank text")
    return value


NonBlank = Annotated[str, AfterValidator(_nonblank)]


class ProducerObject(BaseModel):
    """Validate consumed fields while permitting unknown producer annotations."""

    model_config = ConfigDict(strict=True, extra="allow")


class ProcessIdentity(ProducerObject):
    id: NonBlank
    name: NonBlank


class ProcessNode(ProducerObject):
    id: NonBlank
    kind: Literal["start", "end", "task", "queue", "decision", "parallel_split", "parallel_join"]
    subprocess_parent: None = None
    branch: None = None


class ProcessEdge(ProducerObject):
    source: NonBlank
    target: NonBlank
    route: None = None
    edge_type: Literal["sequence", "rework", "handoff"] | None = None
    rework: bool = False
    handoff: bool = False
    outcome: NonBlank | None = None


class ProcessExport(ProducerObject):
    process: ProcessIdentity
    nodes: Annotated[list[ProcessNode], Field(min_length=1)]
    edges: list[ProcessEdge]


class ProjectionEnvelope(BaseModel):
    """Require the exact bridge envelope without closing extensible producer data."""

    model_config = ConfigDict(strict=True, extra="forbid")

    schema_version: Literal["1.0"]
    flo_version: Literal["0.4.2", "0.4.3"]
    source: NonBlank
    model_revision: NonBlank
    export: ProcessExport
    step_mapping: Annotated[dict[NonBlank, NonBlank], Field(min_length=1)]


def validate_projection(body: object) -> ProjectionEnvelope:
    """Return a validated view or a public error with precise field locations."""
    try:
        return ProjectionEnvelope.model_validate(body)
    except SchemaError as exc:
        errors = exc.errors(include_url=False, include_context=False, include_input=False)
        prefix = (
            "Unsupported process schema or FLO version."
            if any(error["loc"] in (("schema_version",), ("flo_version",)) for error in errors)
            else "Invalid process projection."
        )
        details = "; ".join(
            f"{'.'.join(map(str, error['loc'])) or '$'}: {error['msg']}" for error in errors
        )
        raise ValidationError(f"{prefix} {details}") from None
