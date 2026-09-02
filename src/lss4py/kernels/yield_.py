"""Yield kernels: stage yield, rolled-throughput yield.

Core Yellow Belt yield calculations with full provenance and typed results.
"""

from __future__ import annotations

from typing import Any

import narwhals as nw

from lss4py.domain import ProcessModelIR, YieldResult
from lss4py.kernels._helpers import (
    build_provenance,
    stage_yield_components,
)


def created_to_booked_yield(
    data: Any,  # IntoFrame
    *,
    created_column: str | None = None,
    booked_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    as_percentage: bool = True,
) -> YieldResult:
    """Calculate created-to-booked stage yield.

    **Belt Level:** Yellow Belt (measure yield and defects)

    **Suitable When:** Items pass through distinct stages (created → booked),
    and you want to quantify the fraction that successfully complete each stage.

    **Not Suitable When:** You need to test if yield improvements are significant
    (use hypothesis tests in Green Belt phase).

    Returns:
        YieldResult with yield fraction/percentage, numerator, denominator, and provenance.
    """
    frame = nw.from_native(data, eager_only=True)
    yield_value, numerator, denominator = stage_yield_components(
        frame,
        from_column=created_column,
        to_column=booked_column,
        from_stage_name="created",
        to_stage_name="booked",
        process_model=process_model,
    )

    result_value = yield_value
    unit = "percentage" if as_percentage else "fraction"
    if as_percentage:
        result_value *= 100.0

    provenance = build_provenance(
        method_name="created_to_booked_yield",
        frame=frame,
        parameters={
            "created_column": created_column,
            "booked_column": booked_column,
            "as_percentage": as_percentage,
            "process_model": process_model is not None,
        },
        assumptions=[
            {
                "code": "BINARY_STAGE_OUTCOME",
                "message": (
                    "Assumes items are either present or absent "
                    "at each stage (binary classification)"
                ),
            }
        ],
    )

    return YieldResult(
        name="Created-to-Booked Yield",
        provenance=provenance,
        value=result_value,
        unit=unit,
        numerator=int(numerator),
        denominator=int(denominator),
        method="funnel_stages",
        interpretation_context=(
            "Stage yield is the fraction of items that successfully "
            "transition from one stage to the next. "
            "Created-to-Booked measures conversion from intake to booking. "
            "Use to identify where items are lost and prioritize stage-specific improvements."
        ),
    )


def booked_to_completed_yield(
    data: Any,  # IntoFrame
    *,
    booked_column: str | None = None,
    completed_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    as_percentage: bool = True,
) -> YieldResult:
    """Calculate booked-to-completed stage yield.

    **Belt Level:** Yellow Belt (measure yield and defects)

    **Suitable When:** You want to measure the fraction of booked items
    that complete the process.

    **Not Suitable When:** You need to test if yield improvements are significant
    (use hypothesis tests in Green Belt phase).

    Returns:
        YieldResult with yield fraction/percentage, numerator, denominator, and provenance.
    """
    frame = nw.from_native(data, eager_only=True)
    yield_value, numerator, denominator = stage_yield_components(
        frame,
        from_column=booked_column,
        to_column=completed_column,
        from_stage_name="booked",
        to_stage_name="completed",
        process_model=process_model,
    )

    result_value = yield_value
    unit = "percentage" if as_percentage else "fraction"
    if as_percentage:
        result_value *= 100.0

    provenance = build_provenance(
        method_name="booked_to_completed_yield",
        frame=frame,
        parameters={
            "booked_column": booked_column,
            "completed_column": completed_column,
            "as_percentage": as_percentage,
            "process_model": process_model is not None,
        },
        assumptions=[
            {
                "code": "BINARY_STAGE_OUTCOME",
                "message": (
                    "Assumes items are either present or absent "
                    "at each stage (binary classification)"
                ),
            }
        ],
    )

    return YieldResult(
        name="Booked-to-Completed Yield",
        provenance=provenance,
        value=result_value,
        unit=unit,
        numerator=int(numerator),
        denominator=int(denominator),
        method="funnel_stages",
        interpretation_context=(
            "Booked-to-Completed measures the fraction of booked items "
            "that successfully complete the process. "
            "Use to assess execution quality and identify rework/delay opportunities."
        ),
    )


def rolled_yield(
    data: Any,  # IntoFrame
    *,
    created_column: str | None = None,
    booked_column: str | None = None,
    completed_column: str | None = None,
    process_model: ProcessModelIR | None = None,
    as_percentage: bool = True,
) -> YieldResult:
    """Calculate rolled-throughput yield (product of stage yields).

    **Belt Level:** Yellow Belt (measure yield and defects)

    **Suitable When:** You want the overall probability that an item
    survives all stages without rework or defect.

    **Not Suitable When:** You need to understand which stage has the biggest
    opportunity (use Pareto analysis) or test improvements (use Green Belt methods).

    Returns:
        YieldResult with rolled-throughput yield (fraction/percentage) and provenance.
    """
    frame = nw.from_native(data, eager_only=True)

    # Get component yields
    created_to_booked_result = created_to_booked_yield(
        data,
        created_column=created_column,
        booked_column=booked_column,
        process_model=process_model,
        as_percentage=False,
    )
    booked_to_completed_result = booked_to_completed_yield(
        data,
        booked_column=booked_column,
        completed_column=completed_column,
        process_model=process_model,
        as_percentage=False,
    )

    # Compute rolled yield (product of yields as fractions)
    result = created_to_booked_result.value * booked_to_completed_result.value
    unit = "percentage" if as_percentage else "fraction"
    if as_percentage:
        result *= 100.0

    provenance = build_provenance(
        method_name="rolled_yield",
        frame=frame,
        parameters={
            "created_column": created_column,
            "booked_column": booked_column,
            "completed_column": completed_column,
            "as_percentage": as_percentage,
            "process_model": process_model is not None,
        },
        assumptions=[
            {
                "code": "INDEPENDENT_STAGE_YIELDS",
                "message": (
                    "Assumes stage yields are independent (defects "
                    "at one stage are not correlated with others)"
                ),
            }
        ],
    )

    return YieldResult(
        name="Rolled Throughput Yield",
        provenance=provenance,
        value=result,
        unit=unit,
        numerator=created_to_booked_result.numerator,
        denominator=created_to_booked_result.denominator,
        method="serial_yield",
        interpretation_context=(
            "Rolled-throughput yield is the probability that an item "
            "successfully completes all stages. "
            "It is the product of individual stage yields. "
            "Use to understand overall process effectiveness and "
            "prioritize multi-stage improvements."
        ),
    )
