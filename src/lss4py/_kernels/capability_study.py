"""Capability-study orchestration over explicit short- and long-term samples."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import scipy

from lss4py._frames import canonical_frame
from lss4py._kernels._helpers import build_provenance
from lss4py._kernels.capability import capability_indices
from lss4py._kernels.distribution import distribution_profile
from lss4py.domain import AssumptionNote, CapabilityStudyResult, Specification
from lss4py.guidance import AnalysisSuitability, register_analysis


def _nonconformance(values: np.ndarray, specification: Specification) -> dict[str, int | float]:
    """Count observed values outside inclusive specification boundaries."""
    below = 0 if specification.lsl is None else int(np.count_nonzero(values < specification.lsl))
    above = 0 if specification.usl is None else int(np.count_nonzero(values > specification.usl))
    count = below + above
    return {
        "total": len(values),
        "below_lsl": below,
        "above_usl": above,
        "nonconforming": count,
        "nonconforming_rate": count / len(values),
    }


@register_analysis(
    AnalysisSuitability(
        name="capability_study",
        family="capability",
        question_tags=("capability_study", "process_capability"),
        required_fields=(("column", "specification", "short_term_data"),),
        data_types=("numeric",),
        prerequisites=("Explicit short-term observations and at least one specification limit.",),
        assumptions=(
            "The caller declares short- and long-term sample roles and a stable process.",
            "Normal capability indices require approximately normal independent observations.",
        ),
        alternatives=("capability_indices", "distribution_profile"),
        limits=(
            "Sample roles are declarations; the study does not infer subgroup structure.",
            "No transformation, stability test, or causal conclusion is performed.",
        ),
        belt_level="yellow",
        design_types=("observational",),
        sampling_requirements=(
            "Short- and optional long-term samples represent explicitly declared populations.",
        ),
    )
)
def capability_study(
    short_term_data: Any,
    *,
    column: str,
    specification: Specification,
    long_term_data: Any | None = None,
    missing: Literal["omit", "raise"] = "raise",
    ci: bool = True,
    confidence_level: float = 0.95,
    normality_alpha: float = 0.05,
) -> CapabilityStudyResult:
    """Compose capability, distribution, and observed-risk evidence for declared samples.

    The short-term and optional long-term roles are explicit caller declarations.
    Each sample retains its own capability and distribution result; no subgroup
    structure, stability, transformation, or relationship between samples is
    inferred. Observed nonconformance uses inclusive specification boundaries.
    """
    short_frame = canonical_frame(short_term_data, (column,))
    short_capability = capability_indices(
        short_term_data,
        column=column,
        specification=specification,
        missing=missing,
        ci=ci,
        confidence_level=confidence_level,
    )
    short_distribution = distribution_profile(
        short_term_data,
        column=column,
        normality_alpha=normality_alpha,
        missing=missing,
        unit=specification.unit,
        cohort="Explicit short-term sample",
    )
    long_capability = None
    long_distribution = None
    long_nonconformance = None
    if long_term_data is not None:
        long_capability = capability_indices(
            long_term_data,
            column=column,
            specification=specification,
            missing=missing,
            ci=ci,
            confidence_level=confidence_level,
        )
        long_distribution = distribution_profile(
            long_term_data,
            column=column,
            normality_alpha=normality_alpha,
            missing=missing,
            unit=specification.unit,
            cohort="Explicit long-term sample",
        )
        long_nonconformance = _nonconformance(long_distribution.values, specification)

    parameters = {
        "column": column,
        "specification": specification.to_dict(),
        "long_term_supplied": long_term_data is not None,
        "missing": missing,
        "ci": ci,
        "confidence_level": confidence_level,
        "normality_alpha": normality_alpha,
        "sample_role_policy": "explicit_short_term_and_optional_long_term",
    }
    provenance = build_provenance(
        "capability_study",
        short_frame,
        parameters,
        assumptions=[
            {
                "code": "EXPLICIT_SAMPLE_ROLES",
                "message": "Short- and long-term roles are caller declarations.",
            },
            {
                "code": "STABILITY_NOT_ESTABLISHED",
                "message": "This study does not establish process stability.",
                "severity": "warning",
            },
        ],
    )
    provenance.method_version = "1.0"
    if long_capability is not None:
        provenance.assumptions.append(
            AssumptionNote(
                "SEPARATE_LONG_TERM_SAMPLE",
                "Long-term evidence comes from the separately supplied sample.",
            )
        )
    return CapabilityStudyResult(
        name=f"Capability study: {specification.name}",
        provenance=provenance,
        interpretation_context=(
            "Capability indices require a stable process and appropriate distribution model; "
            "normality and observed nonconformance evidence do not establish either."
        ),
        metadata={
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "short_term_backend": short_capability.provenance.backend,
            "long_term_backend": (
                None if long_capability is None else long_capability.provenance.backend
            ),
            "short_term_schema_fingerprint": (short_capability.provenance.input_schema_fingerprint),
            "long_term_schema_fingerprint": (
                None
                if long_capability is None
                else long_capability.provenance.input_schema_fingerprint
            ),
        },
        specification=specification.to_dict(),
        short_term_capability=short_capability,
        short_term_distribution=short_distribution,
        short_term_nonconformance=_nonconformance(short_distribution.values, specification),
        long_term_capability=long_capability,
        long_term_distribution=long_distribution,
        long_term_nonconformance=long_nonconformance,
    )
