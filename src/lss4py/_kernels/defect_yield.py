"""Small count reductions and ratios matching the retained SixSigma yield convention.

Source formulas: SixSigma 0.11.1 ss.ca.yield; no numerical dependency is needed
beyond Python sum, product, and division (ADR-0020).
"""

from __future__ import annotations

from math import isfinite, prod
from numbers import Integral, Real
from typing import Any

import narwhals as nw

from lss4py._frames import eager_frame
from lss4py._kernels._helpers import build_provenance, require_columns
from lss4py.domain import DefectYieldResult
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis


def _count(value: Any, label: str) -> int:
    """Validate exact nonnegative counts without coercing text, booleans, or nulls."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(f"{label} must contain nonnegative integer counts.")
    if isinstance(value, Integral) or isfinite(value) and value == int(value) and value <= 2**53:
        count = int(value)
    else:
        raise ValidationError(f"{label} must contain finite, exact integer counts.")
    if count < 0:
        raise ValidationError(f"{label} must contain nonnegative integer counts.")
    return count


def _counts(frame: nw.DataFrame, column: str) -> tuple[int, ...]:
    """Preserve positional alignment and integer precision across eager backends."""
    require_columns(frame, column)
    return tuple(_count(value, column) for value in frame[column].to_list())


def _columns(defects: str, rework: str | None) -> None:
    """Require unambiguous, distinct source column roles."""
    for name in (defects, rework):
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValidationError("Count columns must be nonempty names.")
    if defects is None or defects == rework:
        raise ValidationError("Defect and rework columns must be distinct nonempty names.")


def _positive_count(value: Any, label: str) -> int:
    """Require a positive explicit denominator."""
    count = _count(value, label)
    if count == 0:
        raise ValidationError(f"{label} must be positive.")
    return count


@register_analysis(
    AnalysisSuitability(
        name="process_yield",
        outcome_types=("aggregate_nonnegative_integer_count",),
        predictor_types=("none",),
        sampling_requirements=(
            "Caller declares a comparable population; no random sampling is inferred.",
        ),
        family="yield",
        question_tags=("defect_rework_performance",),
        required_fields=(("defects_column", "opportunities"),),
        data_types=("aggregate_counts",),
        prerequisites=(
            "Aligned count buckets share one explicit opportunity denominator.",
            "Defect and rework losses are disjoint and their sum cannot exceed opportunities.",
        ),
        assumptions=(
            "Counts describe comparable opportunities in one declared population.",
            "The rolled estimate multiplies bucket complements using a shared denominator.",
        ),
        alternatives=("rolled_yield",),
        limits=(
            "Opportunity fractions do not identify defective units or observed end-to-end success.",
            "Rework counts excluded from defect counts must not be counted twice.",
        ),
        belt_level="yellow",
        design_types=("observational",),
    )
)
def process_yield(
    data: Any,
    *,
    defects_column: str = "defects",
    rework_column: str | None = None,
    opportunities: int,
    units: int | None = None,
) -> DefectYieldResult:
    """Calculate opportunity-based Yield, FTY, RTY, and DPMO from count buckets.

    Rows are aligned aggregate counting buckets, not individual units or inferred
    sequential stages. All buckets use the same total opportunity denominator.
    Omitted rework means zero; missing counts are rejected. Optional units supplies
    only the defects-per-unit denominator and does not alter the R yield formulas.
    See docs/defect-yield.md for formulas and interpretation limits.

    Returns:
        Versioned DefectYieldResult with fractions, counts, denominators and provenance.
    """
    frame = eager_frame(data)
    _columns(defects_column, rework_column)
    denominator = _positive_count(opportunities, "opportunities")
    unit_count = None if units is None else _positive_count(units, "units")
    defects = _counts(frame, defects_column)
    rework = (0,) * len(defects) if rework_column is None else _counts(frame, rework_column)
    if not defects:
        raise ValidationError("At least one count bucket is required.")
    if sum(defects) + sum(rework) > denominator:
        raise ValidationError("Combined defect and rework counts cannot exceed opportunities.")
    return _result(frame, defects, rework, denominator, unit_count, defects_column, rework_column)


def _result(
    frame: nw.DataFrame,
    defects: tuple[int, ...],
    rework: tuple[int, ...],
    denominator: int,
    units: int | None,
    defects_column: str,
    rework_column: str | None,
) -> DefectYieldResult:
    """Reduce exact counts and retain enough input evidence to audit each ratio."""
    defect_count, rework_count = sum(defects), sum(rework)
    first_pass = tuple(
        (denominator - d - r) / denominator for d, r in zip(defects, rework, strict=True)
    )
    try:
        dpu = None if units is None else defect_count / units
    except OverflowError as exc:
        raise ValidationError("Defects per unit exceeds the finite numerical range.") from exc
    provenance = build_provenance(
        "process_yield",
        frame,
        parameters={
            "defects_column": defects_column,
            "rework_column": rework_column,
            "opportunities": denominator,
            "units": units,
            "missing": "raise",
            "counting_method": "shared_opportunity_buckets",
            "formula_source": "SixSigma 0.11.1 ss.ca.yield",
        },
        assumptions=[
            {
                "code": "SHARED_OPPORTUNITY_BUCKETS",
                "message": (
                    "Aligned disjoint defect/rework losses share one opportunity population."
                ),
            }
        ],
        warnings=[
            {
                "code": "OPPORTUNITY_YIELD_INTERPRETATION",
                "message": "Bucket-product RTY is a counting estimate, not observed unit success.",
            }
        ],
    )
    return DefectYieldResult(
        name="Defect and Rework Yield",
        provenance=provenance,
        interpretation_context=(
            "Opportunity-based counting estimates; no defective-unit count or causal effect "
            "is inferred. RTY multiplies bucket FTYs under the retained R convention."
        ),
        yield_fraction=(denominator - defect_count) / denominator,
        first_time_yield=(denominator - defect_count - rework_count) / denominator,
        rolled_throughput_yield=prod(first_pass),
        dpmo=(defect_count / denominator) * 1_000_000,
        defect_count=defect_count,
        rework_count=rework_count,
        opportunities=denominator,
        units=units,
        defects_per_unit=dpu,
        bucket_defects=defects,
        bucket_rework=rework,
        bucket_first_time_yields=first_pass,
    )
