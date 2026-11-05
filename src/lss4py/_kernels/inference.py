"""Backend-neutral confidence interval for a population mean."""

from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np
import scipy
from scipy import stats

from lss4py._frames import eager_frame
from lss4py._kernels._distribution import shapiro_diagnostic
from lss4py._kernels._helpers import build_provenance, measurement_values
from lss4py.domain import AssumptionNote, MeanCIResult
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis


def _probability(value: float, name: str) -> float:
    """Require a finite, non-boolean probability strictly inside the unit interval."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a finite number strictly between 0 and 1.")
    converted = float(value)
    if not math.isfinite(converted) or not 0 < converted < 1:
        raise ValidationError(f"{name} must be a finite number strictly between 0 and 1.")
    return converted


def _population_variance(value: float | None) -> float | None:
    """Validate an explicitly known population variance without treating booleans as numbers."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("population_variance must be a finite nonnegative number.")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0:
        raise ValidationError("population_variance must be a finite nonnegative number.")
    return converted


@register_analysis(
    AnalysisSuitability(
        name="mean_confidence_interval",
        outcome_types=("numeric_measurement",),
        predictor_types=("none",),
        sampling_requirements=(
            "The supplied cohort represents the population addressed by the interval.",
        ),
        family="inferential",
        question_tags=("estimate_mean",),
        required_fields=(("column",),),
        data_types=("numeric",),
        prerequisites=(
            "At least two valid numeric measurements.",
            "A known population variance must be declared explicitly; otherwise sample "
            "spread is used.",
        ),
        assumptions=(
            "Observations are independent and the sampling or cohort definition supports "
            "inference.",
            "Small-sample t inference requires an approximately normal population.",
        ),
        alternatives=("describe",),
        limits=(
            "A confidence interval does not establish process stability, normality, or capability.",
            "Shapiro-Wilk is a diagnostic rather than proof of normality or independence.",
        ),
        belt_level="yellow",
        design_types=("observational",),
    )
)
def mean_confidence_interval(
    data: Any,
    *,
    column: str,
    confidence_level: float = 0.95,
    population_variance: float | None = None,
    approximate_z: bool = False,
    normality_alpha: float = 0.05,
    missing: Literal["omit", "raise"] = "omit",
    unit: str | None = None,
    cohort: str | None = None,
) -> MeanCIResult:
    """Estimate a population mean with an explicit confidence interval and diagnostic.

    Unknown population variance uses the sample standard deviation and Student's t.
    A supplied population variance uses the normal distribution. ``approximate_z=True``
    explicitly uses the sample standard deviation with a normal critical value, matching
    the optional approximation in R SixSigma ``ss.ci``; it is never selected by sample
    size alone.

    Nulls and NaNs follow ``missing``. Text, booleans, and infinities are rejected.
    At least two valid measurements are required. Shapiro-Wilk is reported for
    nonconstant samples of 3 through 5,000 observations and otherwise remains
    unavailable with a structured warning. It diagnoses marginal normality only and
    does not establish independence, stability, representativeness, or capability.
    """
    level = _probability(confidence_level, "confidence_level")
    diagnostic_alpha = _probability(normality_alpha, "normality_alpha")
    variance = _population_variance(population_variance)
    if not isinstance(approximate_z, bool):
        raise ValidationError("approximate_z must be a boolean.")
    if missing not in ("omit", "raise"):
        raise ValidationError("missing must be 'omit' or 'raise'.")
    if unit is not None and (not isinstance(unit, str) or not unit.strip()):
        raise ValidationError("unit must be a nonblank string when supplied.")
    if cohort is not None and (not isinstance(cohort, str) or not cohort.strip()):
        raise ValidationError("cohort must be a nonblank string when supplied.")

    frame = eager_frame(data)
    supplied = measurement_values(frame, column)
    if missing == "raise" and np.isnan(supplied).any():
        raise ValidationError(f"Column '{column}' contains missing measurements.")
    values = supplied[~np.isnan(supplied)]
    if len(values) < 2:
        raise ValidationError("Mean confidence intervals require at least two valid measurements.")

    distribution = "normal" if variance is not None or approximate_z else "student_t"
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        standard_deviation = (
            math.sqrt(variance) if variance is not None else float(np.std(values, ddof=1))
        )
        standard_error = standard_deviation / math.sqrt(len(values))
        tail = (1 - level) / 2
        degrees_of_freedom = None if distribution == "normal" else len(values) - 1
        critical_value = (
            float(stats.norm.ppf(1 - tail))
            if distribution == "normal"
            else float(stats.t.ppf(1 - tail, degrees_of_freedom))
        )
        mean = float(np.mean(values))
        margin = critical_value * standard_error
        interval = (mean - margin, mean + margin)
    estimates = (mean, standard_deviation, standard_error, critical_value, *interval)
    if not all(math.isfinite(value) for value in estimates):
        raise ValidationError("Mean confidence interval arithmetic did not remain finite.")

    shapiro_statistic, shapiro_p_value, warnings = shapiro_diagnostic(values, diagnostic_alpha)
    if len(values) < 30:
        warnings.append(
            AssumptionNote(
                "SMALL_SAMPLE",
                "Fewer than 30 valid measurements; review normality and sampling assumptions.",
                severity="warning",
            )
        )
    if approximate_z and variance is None:
        warnings.append(
            AssumptionNote(
                "APPROXIMATE_Z",
                "The z approximation uses sample spread; Student's t is the default when "
                "variance is unknown.",
                severity="warning",
            )
        )
    parameters = {
        "column": column,
        "confidence_level": level,
        "population_variance": variance,
        "approximate_z": approximate_z,
        "normality_alpha": diagnostic_alpha,
        "missing": missing,
        "unit": unit,
        "cohort": cohort,
        "formula_source": "SixSigma 0.11.1 ss.ci",
    }
    provenance = build_provenance(
        "mean_confidence_interval",
        frame,
        parameters,
        assumptions=[
            {
                "code": "INDEPENDENT_OBSERVATIONS",
                "message": "The interval assumes independent observations.",
            },
            {
                "code": "REPRESENTATIVE_COHORT",
                "message": "Inference applies only to the declared sampling frame or cohort.",
            },
        ],
    )
    provenance.method_version = "1.0"
    provenance.warnings.extend(warnings)
    return MeanCIResult(
        name=f"Mean confidence interval: {column}",
        provenance=provenance,
        interpretation_context=(
            "Estimates the population mean under the declared sampling assumptions. "
            "The normality diagnostic is not an automatic accept/reject gate."
        ),
        metadata={"numpy_version": np.__version__, "scipy_version": scipy.__version__},
        mean=mean,
        standard_deviation=standard_deviation,
        standard_error=standard_error,
        count=len(values),
        total=len(supplied),
        missing=len(supplied) - len(values),
        confidence_level=level,
        confidence_interval=interval,
        distribution=distribution,
        critical_value=critical_value,
        degrees_of_freedom=degrees_of_freedom,
        variance_source="known_population" if variance is not None else "sample",
        population_variance=variance,
        shapiro_statistic=shapiro_statistic,
        shapiro_p_value=shapiro_p_value,
        normality_alpha=diagnostic_alpha,
        unit=unit,
    )
