"""Normal capability indices with explicit sample-variation and specification policy."""

from __future__ import annotations

from numbers import Real
from typing import Any, Literal

import narwhals as nw
import numpy as np
import scipy
from scipy import stats

from lss4py._kernels._helpers import build_provenance, measurement_values
from lss4py.domain import AssumptionNote, CapabilityResult, Specification
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis


def _specification(specification: Specification) -> None:
    """Require an executable specification without implicit selection policy."""
    if not isinstance(specification, Specification):
        raise ValidationError("specification must be a Specification.")
    if specification.lsl is None and specification.usl is None:
        raise ValidationError("Capability requires at least one specification limit.")
    if specification.group_by or specification.time_window is not None:
        raise ValidationError(
            "Select groups and time windows explicitly before capability analysis."
        )


def _options(missing: str, ci: bool, level: float) -> None:
    """Validate exclusion and confidence-interval options."""
    if missing not in ("omit", "raise"):
        raise ValidationError("missing must be 'omit' or 'raise'.")
    if not isinstance(ci, bool):
        raise ValidationError("ci must be a boolean.")
    _confidence_level(level)


def _confidence_level(level: float) -> None:
    """Require a finite confidence level in the open unit interval."""
    if isinstance(level, bool) or not isinstance(level, Real) or not 0 < level < 1:
        raise ValidationError("confidence_level must be a finite number strictly between 0 and 1.")


def _warn(result: CapabilityResult, code: str, message: str) -> None:
    """Attach an auditable interpretation or numerical warning."""
    result.provenance.warnings.append(AssumptionNote(code, message, severity="warning"))


def _estimates(result: CapabilityResult, values: np.ndarray) -> None:
    """Calculate finite indices, preserving negative capability outside specifications."""
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        mean = float(np.mean(values))
        sigma = float(np.std(values, ddof=1))
    if not np.isfinite(mean) or not np.isfinite(sigma):
        _warn(result, "NUMERICAL_UNAVAILABLE", "Mean or variation overflowed; indices unavailable.")
        return
    result.mean, result.sigma = mean, sigma
    if sigma == 0:
        constant = bool(np.all(values == values[0]))
        _warn(
            result,
            "ZERO_VARIATION" if constant else "NUMERICAL_UNAVAILABLE",
            "Sample variation is zero or underflowed; capability indices are unavailable.",
        )
        return
    _components(result, mean, sigma)


def _components(result: CapabilityResult, mean: float, sigma: float) -> None:
    """Calculate signed components and guard nonfinite limit arithmetic."""
    result.cpl = (mean - result.lsl) / 3 / sigma if result.lsl is not None else None
    result.cpu = (result.usl - mean) / 3 / sigma if result.usl is not None else None
    components = [v for v in (result.cpl, result.cpu) if v is not None]
    result.cpk = min(components)
    result.cp = (
        (result.usl - result.lsl) / 6 / sigma
        if result.lsl is not None and result.usl is not None
        else result.cpk
    )
    if not all(np.isfinite(v) for v in [*components, result.cp, result.cpk]):
        result.cp = result.cpk = result.cpl = result.cpu = None
        _warn(
            result,
            "NUMERICAL_UNAVAILABLE",
            "Capability arithmetic overflowed; indices unavailable.",
        )
    elif result.cpk < 0:
        _warn(
            result, "MEAN_OUTSIDE_SPEC", "Mean is outside a specification limit; Cpk is negative."
        )


def _intervals(result: CapabilityResult) -> None:
    """Use chi-square Cp and approximate normal Cpk intervals with retained sample size."""
    if result.cp is None or result.cpk is None or result.count is None:
        return
    n = result.count
    tail = (1 - result.confidence_level) / 2
    multipliers = np.sqrt(stats.chi2.ppf([tail, 1 - tail], n - 1) / (n - 1))
    with np.errstate(over="ignore", invalid="ignore"):
        cp_bounds = sorted(float(result.cp * factor) for factor in multipliers)
    # Additive form remains defined at Cpk=0 and ordered for negative Cpk.
    with np.errstate(over="ignore", invalid="ignore"):
        error = float(
            stats.norm.isf(tail) * np.hypot(1 / np.sqrt(9 * n), result.cpk / np.sqrt(2 * (n - 1)))
        )
    cpk_bounds = (result.cpk - error, result.cpk + error)
    if not all(np.isfinite(v) for v in [*cp_bounds, *cpk_bounds]):
        _warn(
            result, "NUMERICAL_INTERVAL_UNAVAILABLE", "Confidence interval arithmetic overflowed."
        )
        return
    result.cp_confidence_interval = (cp_bounds[0], cp_bounds[1])
    result.cpk_confidence_interval = cpk_bounds
    result.confidence_interval = cpk_bounds


def _result(
    frame: nw.DataFrame,
    specification: Specification,
    parameters: dict[str, Any],
    total: int,
    count: int,
) -> CapabilityResult:
    """Build the typed contract and provenance before numerical estimation."""
    result = CapabilityResult(
        name=f"Capability indices: {specification.name}",
        provenance=build_provenance(
            "capability_indices",
            frame,
            parameters,
            assumptions=[
                {
                    "code": "NORMAL_STABLE_INDEPENDENT",
                    "message": "Normality, stability, and independence are assumed, not tested.",
                }
            ],
        ),
        interpretation_context="Overall sample variation; short-term capability is unverified.",
        metadata={"numpy_version": np.__version__, "scipy_version": scipy.__version__},
        target=specification.target,
        lsl=specification.lsl,
        usl=specification.usl,
        count=count,
        total=total,
        missing=total - count,
        unit=specification.unit,
        confidence_level=parameters["confidence_level"],
    )
    result.provenance.cohort_definition = specification.cohort
    return result


@register_analysis(
    AnalysisSuitability(
        name="capability_indices",
        family="capability",
        question_tags=("process_capability",),
        required_fields=(("column", "specification"),),
        data_types=("numeric",),
        prerequisites=("At least two finite measurements and one explicit specification limit.",),
        assumptions=(
            "Stable, independent, approximately normal observations in a defined cohort.",
        ),
        alternatives=("describe",),
        limits=(
            "Does not test normality or stability or estimate within-subgroup variation.",
            "Z scores, subgroup estimates, and non-normal capability are unavailable.",
        ),
        belt_level="yellow",
        design_types=("observational",),
    )
)
def capability_indices(
    data: Any,
    *,
    column: str,
    specification: Specification,
    missing: Literal["omit", "raise"] = "omit",
    ci: bool = False,
    confidence_level: float = 0.95,
) -> CapabilityResult:
    """Calculate normal Cp/Cpk and lower/upper components from an eager numeric column.

    Yellow Belt: suitable for a declared stable, approximately normal process with
    independent measurements and explicit acceptance limits. These assumptions are
    recorded, never inferred or verified. Uses overall sample standard deviation
    (ddof=1), not a within-subgroup or short-term estimator. One-sided Cp follows
    SixSigma's available component convention; two-sided Cp is width/(6s).

    Null/NaN measurements are omitted or rejected explicitly. Text, booleans,
    infinity, absent limits, and implicit grouping/window selection are rejected.
    Undefined estimates are None with diagnostics; negative indices are retained.
    ci=True returns chi-square Cp and approximate normal Cpk intervals, using the
    retained count. No unit conversion, cohort filtering, Z score, plotting, or
    automatic distribution/stability decision is performed.
    """
    _specification(specification)
    _options(missing, ci, confidence_level)
    frame = nw.from_native(data, eager_only=True)
    values = measurement_values(frame, column)
    valid = values[~np.isnan(values)]
    if missing == "raise" and len(valid) != len(values):
        raise ValidationError(f"Column '{column}' contains missing measurements.")
    parameters = {
        "column": column,
        "specification": specification.to_dict(),
        "missing": missing,
        "ci": ci,
        "confidence_level": float(confidence_level),
        "ddof": 1,
        "variation_estimator": "overall_sample_std",
        "cp_interval_method": "chi_square",
        "cpk_interval_method": "normal_approximation",
    }
    result = _result(frame, specification, parameters, len(values), len(valid))
    if result.missing:
        _warn(result, "MISSING_OMITTED", f"Excluded {result.missing} null/NaN measurements.")
    if len(valid) < 2:
        _warn(
            result,
            "INSUFFICIENT_DATA",
            "Sample variation requires at least two valid measurements.",
        )
        return result
    if len(valid) < 50:
        _warn(
            result,
            "SMALL_SAMPLE",
            "Capability estimates and intervals are uncertain with fewer than 50 observations.",
        )
    _estimates(result, valid)
    if ci:
        _intervals(result)
    return result
