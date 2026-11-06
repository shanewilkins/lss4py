"""Calibrated Taguchi loss over explicit observations, separate from rendering."""

from __future__ import annotations

from math import fsum, isfinite
from numbers import Integral, Real
from sys import float_info
from typing import Any, Literal

import numpy as np
import polars as pl

from lss4py._frames import canonical_frame
from lss4py._kernels._helpers import build_provenance
from lss4py._polars_extract import measurement_values, portable_key_values
from lss4py.domain import QualityLossResult
from lss4py.errors import ValidationError
from lss4py.guidance import AnalysisSuitability, register_analysis

Convention = Literal["nominal", "smaller", "larger"]


def _number(value: Any, name: str) -> float:
    """Require a finite real scalar without boolean or text coercion."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(f"{name} must be a finite real number.")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValidationError(f"{name} must be a finite real number.") from exc
    if not isfinite(number):
        raise ValidationError(f"{name} must be a finite real number.")
    return number


def _calibration(convention: str, target: Any, tolerance: Any, cost: Any) -> tuple:
    """Normalize the explicit convention and calibrate loss at the reference boundary."""
    if convention not in ("nominal", "smaller", "larger"):
        raise ValidationError("convention must be 'nominal', 'smaller', or 'larger'.")
    tolerance = _number(tolerance, "tolerance")
    cost = _number(cost, "loss_at_tolerance")
    if tolerance <= 0 or cost < 0:
        raise ValidationError("tolerance must be positive and loss_at_tolerance nonnegative.")
    if convention == "nominal":
        target = _number(target, "target")
    elif convention == "smaller":
        if target is not None and _number(target, "target") != 0:
            raise ValidationError("The smaller convention requires a zero or omitted target.")
        target = 0.0
    elif target is not None:
        raise ValidationError(
            "Omit target for the larger convention; no infinite JSON target is used."
        )
    coefficient = (
        cost * tolerance * tolerance if convention == "larger" else cost / tolerance / tolerance
    )
    if not isfinite(coefficient) or (cost > 0 and coefficient < float_info.min):
        raise ValidationError("Quality-loss coefficient overflowed or underflowed.")
    return target, tolerance, cost, coefficient


def _context(unit: Any, loss_unit: Any, production_size: Any, missing: str) -> int | None:
    """Validate labels, exclusion policy, and an optional explicit production count."""
    for name, value in (("unit", unit), ("loss_unit", loss_unit)):
        if value is None and name == "unit":
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{name} must be nonblank text.")
    if missing not in ("raise", "omit"):
        raise ValidationError("missing must be 'raise' or 'omit'.")
    if production_size is None:
        return None
    if isinstance(production_size, bool) or not isinstance(production_size, Integral):
        raise ValidationError("production_size must be a nonnegative integer or None.")
    if production_size < 0:
        raise ValidationError("production_size must be a nonnegative integer or None.")
    return int(production_size)


def _estimates(values: np.ndarray, convention: str, target: Any, coefficient: float) -> tuple:
    """Compute finite empirical squared-basis and loss summaries without a normality model."""
    if convention == "smaller" and np.any(values < 0):
        raise ValidationError("Smaller-the-better measurements must be nonnegative.")
    if convention == "larger" and np.any(values <= 0):
        raise ValidationError("Larger-the-better measurements must be strictly positive.")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
        basis = 1 / values if convention == "larger" else values - target
        squares = np.square(basis)
        losses = coefficient * squares
    if (
        not np.isfinite(squares).all()
        or not np.isfinite(losses).all()
        or np.any((basis != 0) & (squares < float_info.min))
        or (coefficient > 0 and np.any((squares > 0) & (losses < float_info.min)))
    ):
        raise ValidationError("Quality-loss arithmetic overflowed or underflowed.")
    try:
        msd = fsum(float(value) / len(values) for value in squares)
        average = fsum(float(value) / len(values) for value in losses)
        sample_loss = fsum(map(float, losses))
    except OverflowError as exc:
        raise ValidationError("Quality-loss aggregation overflowed.") from exc
    if any(0 < value < float_info.min for value in (msd, average, sample_loss)):
        raise ValidationError("Quality-loss aggregation underflowed.")
    return losses, msd, average, sample_loss


def _suitability(name: str, fields: tuple[str, ...]) -> AnalysisSuitability:
    """Describe calibrated economic modeling without selecting a convention for the caller."""
    return AnalysisSuitability(
        name=name,
        family="quality_loss",
        question_tags=("quality_loss", "economic_impact"),
        required_fields=(fields,),
        data_types=("numeric",),
        belt_level="yellow",
        design_types=("observational",),
        prerequisites=("Explicit loss convention, tolerance and cost calibration.",),
        assumptions=(
            "The caller's loss calibration represents the declared economic consequence.",
        ),
        alternatives=("describe", "capability_indices"),
        limits=("Modeled loss is not measured expenditure, causal evidence, or a defect count.",),
    )


@register_analysis(
    _suitability("quality_loss_analysis", ("column", "tolerance", "loss_at_tolerance"))
)
def quality_loss_analysis(
    data: Any,
    *,
    column: str,
    tolerance: float,
    loss_at_tolerance: float,
    convention: Convention = "nominal",
    target: float | None = None,
    production_size: int | None = None,
    unit: str | None = None,
    loss_unit: str = "currency",
    missing: Literal["raise", "omit"] = "raise",
    key_column: str | None = None,
) -> QualityLossResult:
    """Return calibrated per-observation and aggregate Taguchi loss for eager frames.

    Nominal loss is cost*((x-target)/tolerance)**2; smaller loss is
    cost*(x/tolerance)**2; larger loss is cost*(tolerance/x)**2.
    The larger convention uses squared reciprocal measurements as its MSD basis,
    not differences from an infinite target. Missingness is explicit; one retained
    measurement suffices. Production loss extrapolates average loss to an explicit
    count and does not silently substitute the retained sample size.
    """
    target, tolerance, cost, coefficient = _calibration(
        convention, target, tolerance, loss_at_tolerance
    )
    size = _context(unit, loss_unit, production_size, missing)
    columns = (column,) if key_column is None else tuple(dict.fromkeys((column, key_column)))
    canonical = canonical_frame(data, columns)
    frame = canonical.to_polars(copy=False)
    supplied = measurement_values(frame, column)
    keys, identity = portable_key_values(frame, key_column)
    retained = ~np.isnan(supplied)
    if missing == "raise" and not retained.all():
        raise ValidationError(f"Column '{column}' contains missing measurements.")
    values = supplied[retained].copy()
    if not len(values):
        raise ValidationError("Quality-loss analysis requires at least one retained measurement.")
    losses, msd, average, sample_loss = _estimates(values, convention, target, coefficient)
    try:
        total_loss = None if size is None else average * size
    except OverflowError as exc:
        raise ValidationError("Production-loss arithmetic overflowed.") from exc
    if total_loss is not None and not isfinite(total_loss):
        raise ValidationError("Production-loss arithmetic overflowed.")
    parameters = {
        "column": column,
        "convention": convention,
        "target": target,
        "tolerance": tolerance,
        "loss_at_tolerance": cost,
        "production_size": size,
        "unit": unit,
        "loss_unit": loss_unit,
        "missing": missing,
        "key_column": key_column,
        "calibration": "loss_equals_declared_cost_at_tolerance_boundary",
    }
    provenance = build_provenance(
        "quality_loss_analysis",
        canonical,
        parameters,
        assumptions=[
            {
                "code": "DECLARED_ECONOMIC_MODEL",
                "message": "Loss is modeled using caller-declared calibration, not observed cost.",
            }
        ],
        warnings=(
            [
                {
                    "code": "MISSING_OMITTED",
                    "message": f"Excluded {int((~retained).sum())} missing measurements.",
                }
            ]
            if not retained.all()
            else []
        ),
    )
    provenance.method_version = "1.0"
    return QualityLossResult(
        name=f"Quality-loss analysis: {column}",
        provenance=provenance,
        interpretation_context="Modeled economic loss; no causal or realized-savings claim.",
        metadata=identity,
        convention=convention,
        target=target,
        tolerance=tolerance,
        loss_at_tolerance=cost,
        coefficient=coefficient,
        values=values,
        losses=losses,
        source_positions=np.flatnonzero(retained),
        keys=None if keys is None else keys[retained].copy(),
        count=len(values),
        total=len(supplied),
        missing=int((~retained).sum()),
        mean_squared_deviation=msd,
        average_loss=average,
        sample_loss=sample_loss,
        production_size=size,
        total_loss=total_loss,
        unit=unit,
        loss_unit=loss_unit,
    )


@register_analysis(_suitability("quality_loss", ("value", "tolerance", "loss_at_tolerance")))
def quality_loss(
    value: Any,
    *,
    tolerance: float,
    loss_at_tolerance: float,
    convention: Convention = "nominal",
    target: float | None = None,
    production_size: int | None = None,
    unit: str | None = None,
    loss_unit: str = "currency",
) -> QualityLossResult:
    """Evaluate a real scalar or one-dimensional numeric sequence with typed loss evidence.

    Uses the same calibrated formulas as quality_loss_analysis. Missing values,
    booleans, strings and nested arrays are rejected; use the tabular API for an
    explicit omission policy or source keys. Scalar results retain a one-row array.
    """
    try:
        observations = np.asarray(value, dtype=object)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "value must be a numeric scalar or one-dimensional sequence."
        ) from exc
    scalar = observations.ndim == 0
    if observations.ndim > 1:
        raise ValidationError("value must be a numeric scalar or one-dimensional sequence.")
    values = [_number(item, "value") for item in observations.reshape(-1)]
    result = quality_loss_analysis(
        pl.DataFrame({"value": values}),
        column="value",
        tolerance=tolerance,
        loss_at_tolerance=loss_at_tolerance,
        convention=convention,
        target=target,
        production_size=production_size,
        unit=unit,
        loss_unit=loss_unit,
    )
    result.provenance.method = "quality_loss"
    result.provenance.backend = "unknown"
    result.provenance.parameters.pop("backend_version")
    result.provenance.parameters.update(
        input_kind="scalar" if scalar else "sequence",
        materialization="Detached numeric sequence; synthetic numeric schema; no source mutation",
    )
    return result
