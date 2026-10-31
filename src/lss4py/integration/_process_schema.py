"""Strict shapes for portable process projections, independent of FLO internals."""

import math
import re
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator
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


class MeasurementResult(ProducerObject):
    method: NonBlank
    value: Any
    unit: NonBlank
    parameters: dict[str, Any] | None = None

    @model_validator(mode="after")
    def check_method(self):
        """Require core methods or explicitly namespaced extension methods."""
        core = {
            "count",
            "sum",
            "minimum",
            "maximum",
            "mean",
            "median",
            "mode",
            "percentile",
            "standard_deviation",
        }
        if self.method not in core and not re.fullmatch(
            r"[a-z][a-z0-9_.-]*:[a-z][a-z0-9_.-]*", self.method
        ):
            raise ValueError("method must be a core or namespaced method")
        if self.method == "percentile":
            percentile = (self.parameters or {}).get("percentile")
            if (
                isinstance(percentile, bool)
                or not isinstance(percentile, (int, float))
                or not 0 <= percentile <= 100
            ):
                raise ValueError("percentile requires parameters.percentile between 0 and 100")
        return self


class MeasurementProfile(ProducerObject):
    basis: Literal["observed", "simulated", "estimated", "planned", "target"]
    results: Annotated[dict[NonBlank, MeasurementResult], Field(min_length=1)]
    primary: NonBlank
    analysis_input: NonBlank | None = None
    observation_count: Annotated[int, Field(gt=0)] | None = None
    observation_unit: NonBlank | None = None
    cohort: NonBlank | None = None
    aggregation_level: NonBlank | None = None
    observation_window: NonBlank | None = None
    evidence_ref: NonBlank | None = None
    extensions: dict[str, Any] | None = None

    @model_validator(mode="after")
    def check_selections(self):
        """Validate selected durations without substituting a display selection."""
        if (self.observation_count is None) != (self.observation_unit is None):
            raise ValueError("observation_count and observation_unit must occur together")
        factors = {"s": 1, "m": 60, "min": 60, "hr": 3600, "d": 86400}
        for selector in (self.primary, self.analysis_input):
            if selector is None:
                continue
            if selector not in self.results:
                raise ValueError(f"unknown result selector: {selector}")
            result = self.results[selector]
            value = result.value
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value < 0
                or result.unit not in factors
            ):
                raise ValueError(f"selected result {selector} must be a nonnegative duration")
            try:
                finite = math.isfinite(value * factors[result.unit])
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError(f"selected result {selector} must convert to finite seconds")
        return self


class WaitingReference(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    ref: NonBlank


class ModernProcessIdentity(ProcessIdentity):
    lead_time: MeasurementProfile | None = None


class ModernProcessNode(ProcessNode):
    value_class: Literal["VA", "RNVA", "NVA", "unknown"] | None = None
    cycle_time: MeasurementProfile | None = None
    wait_time: MeasurementProfile | WaitingReference | None = None
    changeover_time: MeasurementProfile | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_retired_fields(cls, value):
        """Do not accept retired operational metadata as 0.5 evidence."""
        if isinstance(value, dict):
            retired = {
                "metadata",
                "workers",
                "wait_before",
                "crossover_time",
                "transfer_time",
                "lead_time",
                "sla_target_seconds",
                "attrs",
            } & value.keys()
            if retired:
                raise ValueError(f"retired FLO 0.5 fields: {', '.join(sorted(retired))}")
        return value

    @model_validator(mode="after")
    def check_applicability(self):
        """Keep work measurements and references on their declared node kinds."""
        if self.kind != "task" and any(
            v is not None for v in (self.value_class, self.cycle_time, self.changeover_time)
        ):
            raise ValueError("work classification and processing/setup profiles require task nodes")
        if self.wait_time is not None and self.kind not in {"task", "queue"}:
            raise ValueError("waiting profiles require task or queue nodes")
        if isinstance(self.wait_time, WaitingReference) and self.kind != "queue":
            raise ValueError("waiting references require queue nodes")
        return self


class Handoff(ProducerObject):
    type: (
        Literal["responsibility", "information", "material", "system", "location", "mixed"] | None
    ) = None
    extensions: dict[str, Any] | None = None


class ReworkFrequency(ProducerObject):
    basis: Literal["observed", "simulated", "estimated", "planned", "target"]
    numerator: Annotated[int | float, Field(ge=0)]
    denominator: Annotated[int, Field(gt=0)]
    observation_unit: NonBlank
    evidence_ref: NonBlank | None = None

    @model_validator(mode="after")
    def check_population(self):
        """Preserve measured zero and reject contradictory population counts."""
        if self.numerator > self.denominator:
            raise ValueError("numerator cannot exceed denominator")
        return self


class Rework(ProducerObject):
    reason: NonBlank | None = None
    frequency: ReworkFrequency | None = None
    note: NonBlank | None = None
    extensions: dict[str, Any] | None = None


class ModernProcessEdge(ProducerObject):
    source: NonBlank
    target: NonBlank
    route: None = None
    edge_type: None = None
    handoff: Handoff | None = None
    rework: Rework | None = None
    outcome: NonBlank | None = None

    @field_validator("edge_type", mode="before")
    @classmethod
    def reject_edge_type(cls, value):
        """Retain the precise location of a retired edge-type declaration."""
        raise ValueError("edge_type is retired in FLO 0.5; use structured relations")

    @model_validator(mode="before")
    @classmethod
    def reject_retired_fields(cls, value):
        """Reject legacy edge annotations even when their value is null."""
        if isinstance(value, dict) and {"metadata", "attrs"} & value.keys():
            raise ValueError("retired FLO 0.5 edge fields")
        return value


class ModernProcessExport(ProducerObject):
    process: ModernProcessIdentity
    nodes: Annotated[list[ModernProcessNode], Field(min_length=1)]
    edges: list[ModernProcessEdge]


class EnvelopeBase(BaseModel):
    """Require the exact bridge envelope without closing extensible producer data."""

    model_config = ConfigDict(strict=True, extra="forbid")

    schema_version: Literal["1.0"]
    source: NonBlank
    model_revision: NonBlank
    step_mapping: Annotated[dict[NonBlank, NonBlank], Field(min_length=1)]


class ProjectionEnvelope(EnvelopeBase):
    flo_version: Literal["0.4.2", "0.4.3"]
    export: ProcessExport


class ModernProjectionEnvelope(EnvelopeBase):
    flo_version: Literal["0.5.0"]
    export: ModernProcessExport


def validate_projection(body: object) -> ProjectionEnvelope | ModernProjectionEnvelope:
    """Return a validated view or a public error with precise field locations."""
    try:
        model = (
            ModernProjectionEnvelope
            if isinstance(body, dict) and body.get("flo_version") == "0.5.0"
            else ProjectionEnvelope
        )
        return model.model_validate(body)
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
