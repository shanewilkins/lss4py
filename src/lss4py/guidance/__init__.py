"""Discover analytical candidates from declared intent, without executing methods."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, TypeVar

from lss4py.errors import ValidationError


@dataclass(frozen=True)
class AnalysisSuitability:
    """Immutable method guidance; field groups represent alternative input paths.

    Each required_fields group is sufficient as a semantic input path. Names are
    roles resolved through explicit arguments or process bindings, not literal
    dataframe columns. Prerequisites and assumptions require caller judgment.
    """

    name: str
    family: str
    question_tags: tuple[str, ...]
    belt_level: str
    required_fields: tuple[tuple[str, ...], ...]
    data_types: tuple[str, ...]
    design_types: tuple[str, ...]
    prerequisites: tuple[str, ...]
    assumptions: tuple[str, ...]
    alternatives: tuple[str, ...]
    limits: tuple[str, ...]
    outcome_types: tuple[str, ...] = ("declared",)
    predictor_types: tuple[str, ...] = ("none",)
    sampling_requirements: tuple[str, ...] = (
        "Caller declares the observed population and design.",
    )

    def __post_init__(self) -> None:
        """Validate labels and defensively freeze all sequence metadata."""
        for field in ("name", "family", "belt_level"):
            _label(getattr(self, field))
        for field in (
            "question_tags",
            "data_types",
            "design_types",
            "prerequisites",
            "assumptions",
            "alternatives",
            "limits",
            "outcome_types",
            "predictor_types",
            "sampling_requirements",
        ):
            object.__setattr__(self, field, _labels(getattr(self, field)))
        groups = self.required_fields
        if isinstance(groups, str) or not groups:
            raise ValidationError("required_fields must contain semantic input paths.")
        object.__setattr__(self, "required_fields", tuple(_labels(group) for group in groups))

    def to_dict(self) -> dict[str, Any]:
        """Return independent machine-readable metadata without a callable or data."""
        return asdict(self)


def _label(value: str) -> None:
    """Reject missing or ambiguous metadata labels."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Guidance labels must be nonblank strings.")


def _labels(values: tuple[str, ...]) -> tuple[str, ...]:
    """Copy a nonempty sequence of unique labels into a tuple."""
    if isinstance(values, str) or not values:
        raise ValidationError("Guidance metadata must contain a sequence of labels.")
    for value in values:
        _label(value)
    if len(set(values)) != len(values):
        raise ValidationError("Guidance labels must be unique within each field.")
    return tuple(values)


_registry: dict[str, AnalysisSuitability] = {}
Function = TypeVar("Function", bound=Callable[..., Any])


def register_analysis(
    suitability: AnalysisSuitability,
) -> Callable[[Function], Function]:
    """Register metadata at definition time and preserve the original callable."""

    def decorate(function: Function) -> Function:
        """Associate one uniquely named analysis with its declared guidance."""
        if getattr(function, "__name__", None) != suitability.name:
            raise ValidationError("Guidance name must match the analysis function name.")
        if suitability.name in _registry:
            raise ValidationError(f"Analysis '{suitability.name}' is already registered.")
        _registry[suitability.name] = suitability
        return function

    return decorate


def get_analysis(name: str) -> AnalysisSuitability:
    """Return a registered method's guidance, rejecting unknown names."""
    _label(name)
    try:
        return _registry[name]
    except KeyError as exc:
        raise ValidationError(f"Unknown analysis '{name}'.") from exc


def get_candidates(
    question: str | None = None,
    *,
    data_type: str | None = None,
    design_type: str | None = None,
) -> tuple[AnalysisSuitability, ...]:
    """List candidates in name order using exact, caller-declared metadata tags.

    Omitted filters enumerate the catalog. Unknown tags return no candidates.
    Matches do not certify data validity or assumptions, rank methods, select a
    method, or execute analysis. No observed dataset is accepted or inspected.
    """
    filters = {"question_tags": question, "data_types": data_type, "design_types": design_type}
    for value in filters.values():
        if value is not None:
            _label(value)
    return tuple(
        entry
        for name, entry in sorted(_registry.items())
        if all(value is None or value in getattr(entry, field) for field, value in filters.items())
    )


@dataclass(frozen=True)
class AnalysisSelection:
    """An explicit practitioner decision; construction and recording never run an analysis."""

    suitability: AnalysisSuitability
    reason: str
    cohort: str
    design_type: str

    def __post_init__(self) -> None:
        """Require a reason, population and a design supported by the chosen method."""
        for value in (self.reason, self.cohort, self.design_type):
            _label(value)
        if self.design_type not in self.suitability.design_types:
            raise ValidationError("Selected design is not supported by this method.")

    def to_dict(self) -> dict:
        """Return detached machine-readable selection and reviewed method guidance."""
        return asdict(self)

    def record(self, result: Any) -> None:
        """Attach a caller-authorized decision to its matching already-computed result."""
        if not hasattr(result, "provenance"):
            raise ValidationError(
                "Recording requires an AnalyticalResult; retain scalar choices separately."
            )
        if result.provenance.method != self.suitability.name:
            raise ValidationError("Selection does not match the result method.")
        result.metadata["analysis_selection"] = self.to_dict()


def select_analysis(name: str, *, reason: str, cohort: str, design_type: str) -> AnalysisSelection:
    """Record the practitioner's declared choice without inspecting data or executing methods."""
    return AnalysisSelection(get_analysis(name), reason, cohort, design_type)
