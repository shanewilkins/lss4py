"""Shared distribution diagnostics for governed analytical kernels."""

from __future__ import annotations

import math

import numpy as np
from scipy import stats

from lss4py.domain import AssumptionNote


def shapiro_diagnostic(
    values: np.ndarray, alpha: float
) -> tuple[float | None, float | None, list[AssumptionNote]]:
    """Run Shapiro-Wilk only inside its supported, nonconstant sample domain."""
    warnings: list[AssumptionNote] = []
    if len(values) < 3:
        warnings.append(
            AssumptionNote(
                "NORMALITY_UNAVAILABLE",
                "Shapiro-Wilk requires at least three valid measurements.",
                severity="warning",
            )
        )
        return None, None, warnings
    if len(values) > 5000:
        warnings.append(
            AssumptionNote(
                "NORMALITY_UNAVAILABLE",
                "Shapiro-Wilk is limited to at most 5,000 valid measurements.",
                severity="warning",
            )
        )
        return None, None, warnings
    if np.all(values == values[0]):
        warnings.append(
            AssumptionNote(
                "NORMALITY_UNAVAILABLE",
                "Shapiro-Wilk is undefined for constant measurements.",
                severity="warning",
            )
        )
        return None, None, warnings
    statistic, p_value = stats.shapiro(values)
    statistic, p_value = float(statistic), float(p_value)
    if not math.isfinite(statistic) or not math.isfinite(p_value):
        warnings.append(
            AssumptionNote(
                "NORMALITY_UNAVAILABLE",
                "Shapiro-Wilk did not produce finite diagnostic values.",
                severity="warning",
            )
        )
        return None, None, warnings
    if p_value < alpha:
        warnings.append(
            AssumptionNote(
                "NON_NORMAL_SAMPLE",
                f"Shapiro-Wilk rejects normality at alpha={alpha:g}; review the data and method.",
                severity="warning",
            )
        )
    return statistic, p_value, warnings
