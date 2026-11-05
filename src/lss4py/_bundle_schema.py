"""Standard-library-only bundle validation; also runnable as a standalone JSON validator.

Run ``python _bundle_schema.py saved-bundle.json`` without installing LSS4PY or
any analytical/dataframe dependencies. Validation never imports or executes methods.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class BundleValidationError(ValueError):
    """A portable bundle is malformed, incompatible, or internally inconsistent."""


def _require(condition: bool, message: str) -> None:
    """Raise one portable schema error without dependency-specific exceptions."""
    if not condition:
        raise BundleValidationError(message)


def _text(value: Any) -> bool:
    """Recognize a nonblank JSON string."""
    return isinstance(value, str) and bool(value.strip())


def _number(value: Any) -> bool:
    """Recognize finite JSON numbers while keeping booleans out of numerical fields."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _integer(value: Any) -> bool:
    """Recognize nonnegative count/position integers without floating coercion."""
    return type(value) is int and value >= 0


def _object(value: Any, fields: set[str], label: str) -> None:
    """Reject missing and unknown schema fields explicitly."""
    _require(isinstance(value, dict), f"{label} must be an object.")
    _require(set(value) == fields, f"Unsupported {label} fields.")


def _json_tree(value: Any) -> None:
    """Reject nonportable keys, nonfinite values and arbitrary Python objects."""
    if isinstance(value, dict):
        _require(all(isinstance(k, str) for k in value), "JSON keys must be strings.")
        for item in value.values():
            _json_tree(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _json_tree(item)
    else:
        _require(
            value is None or isinstance(value, (str, bool)) or _number(value),
            "Bundle data must be finite JSON.",
        )


def canonical_json(value: Any) -> str:
    """Encode portable data deterministically for snapshotting and integrity hashes."""
    try:
        _json_tree(value)
    except RecursionError as exc:
        raise BundleValidationError("Cyclic or deeply nested bundle data.") from exc
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


def bundle_fingerprint(value: Any) -> str:
    """Hash canonical JSON for accidental-change detection, not authentication."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _datetime(value: Any, label: str) -> None:
    """Require an explicit valid ISO datetime."""
    _require(_text(value), f"{label} requires a timestamp.")
    _require("T" in value or " " in value, f"{label} requires date and time.")
    try:
        datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise BundleValidationError(f"Invalid {label} timestamp.") from exc


def _notes(value: Any) -> None:
    """Validate analytical assumptions and warnings without replacing their content."""
    _require(isinstance(value, list), "Diagnostics must be a list.")
    for note in value:
        _object(note, {"code", "message", "severity"}, "diagnostic")
        _require(all(_text(v) for v in note.values()), "Diagnostics require nonblank fields.")
        _require(
            note["severity"] in ("info", "warning", "error", "critical"),
            "Unsupported diagnostic severity.",
        )


PROVENANCE_FIELDS = {
    "method",
    "method_version",
    "package_version",
    "backend",
    "parameters",
    "created_at",
    "assumptions",
    "warnings",
    "input_schema_fingerprint",
    "cohort_definition",
}
BASE_FIELDS = {"result_type", "name", "provenance", "interpretation_context", "metadata"}
RESULT_FIELDS = {
    "ProcessMapResult": set(),
    "OrderReconstructionResult": set(),
    "TimingResult": {"values", "unit", "keys", "percentiles"},
    "YieldResult": {"value", "unit", "numerator", "denominator", "method"},
    "DefectYieldResult": {
        "schema_version",
        "yield_fraction",
        "first_time_yield",
        "rolled_throughput_yield",
        "dpmo",
        "defect_count",
        "rework_count",
        "opportunities",
        "units",
        "defects_per_unit",
        "bucket_defects",
        "bucket_rework",
        "bucket_first_time_yields",
    },
    "DescriptiveResult": {
        "mean",
        "median",
        "std",
        "variance",
        "skew",
        "kurtosis",
        "min_value",
        "max_value",
        "percentiles",
        "count",
        "missing",
        "total",
        "modes",
        "mode_frequency",
        "unique_count",
        "range",
        "iqr",
        "mad",
        "coefficient_of_variation",
        "unit",
        "group_keys",
    },
    "DistributionProfileResult": {
        "values",
        "keys",
        "source_positions",
        "unit",
        "count",
        "total",
        "missing",
        "mean",
        "median",
        "std",
        "skew",
        "kurtosis",
        "histogram_bin_method",
        "histogram_edges",
        "histogram_counts",
        "histogram_density",
        "ecdf_values",
        "ecdf_probabilities",
        "qq_distribution",
        "qq_theoretical",
        "qq_observed",
        "qq_line_x",
        "qq_line_y",
        "qq_slope",
        "qq_intercept",
        "qq_r",
        "q1",
        "q3",
        "iqr",
        "outlier_method",
        "outlier_multiplier",
        "lower_fence",
        "upper_fence",
        "lower_whisker",
        "upper_whisker",
        "outlier_values",
        "outlier_source_positions",
        "outlier_keys",
        "shapiro_statistic",
        "shapiro_p_value",
        "normality_alpha",
        "density_method",
        "density_bandwidth",
        "density_x",
        "density_y",
    },
    "MeanCIResult": {
        "mean",
        "standard_deviation",
        "standard_error",
        "count",
        "total",
        "missing",
        "confidence_level",
        "confidence_interval",
        "distribution",
        "critical_value",
        "degrees_of_freedom",
        "variance_source",
        "population_variance",
        "shapiro_statistic",
        "shapiro_p_value",
        "normality_alpha",
        "unit",
    },
    "CapabilityResult": {
        "cp",
        "cpk",
        "z_score",
        "target",
        "lsl",
        "usl",
        "mean",
        "sigma",
        "count",
        "confidence_level",
        "confidence_interval",
        "method",
        "cpl",
        "cpu",
        "cp_confidence_interval",
        "cpk_confidence_interval",
        "total",
        "missing",
        "unit",
        "variation_estimator",
    },
    "CapabilityStudyResult": {
        "schema_version",
        "specification",
        "short_term_capability",
        "short_term_distribution",
        "short_term_nonconformance",
        "long_term_capability",
        "long_term_distribution",
        "long_term_nonconformance",
    },
    "ControlChartResult": {
        "schema_version",
        "chart",
        "phase",
        "moving_ranges",
        "pair_start_positions",
        "pair_end_positions",
        "pair_start_keys",
        "pair_end_keys",
        "lcl",
        "center_line",
        "ucl",
        "signal_indices",
        "signal_source_positions",
        "observation_count",
        "baseline_observation_count",
        "nsigmas",
        "unit",
        "baseline_result_fingerprint",
    },
}
METHODS = {
    "ProcessMapResult": {"map_process"},
    "OrderReconstructionResult": {"reconstruct_orders"},
    "TimingResult": {"lead_time", "wait_time", "process_cycle_efficiency", "takt_time"},
    "YieldResult": {
        "deadline_performance",
        "created_to_booked_yield",
        "booked_to_completed_yield",
        "rolled_yield",
    },
    "DefectYieldResult": {"process_yield"},
    "DescriptiveResult": {"describe"},
    "DistributionProfileResult": {"distribution_profile"},
    "MeanCIResult": {"mean_confidence_interval"},
    "CapabilityResult": {"capability_indices"},
    "CapabilityStudyResult": {"capability_study"},
    "ControlChartResult": {"control_chart"},
}


def _provenance(value: Any) -> None:
    """Validate full method, parameter and diagnostic context."""
    _object(value, PROVENANCE_FIELDS, "provenance")
    for name in ("method", "method_version", "package_version"):
        _require(_text(value[name]), f"Provenance requires {name}.")
    _require(value["backend"] in ("pandas", "polars", "pyarrow", "unknown"), "Unknown backend.")
    _require(isinstance(value["parameters"], dict), "Provenance parameters must be an object.")
    _datetime(value["created_at"], "provenance")
    _notes(value["assumptions"])
    _notes(value["warnings"])
    for name in ("input_schema_fingerprint", "cohort_definition"):
        _require(value[name] is None or _text(value[name]), f"Invalid provenance {name}.")


def _numeric_fields(result: dict, names: tuple[str, ...]) -> None:
    """Validate nullable numerical estimates without imposing statistical assumptions."""
    for name in names:
        _require(result[name] is None or _number(result[name]), f"Invalid numeric field: {name}.")


def _percentiles(value: Any) -> None:
    """Validate named percentile estimates when present."""
    if value is not None:
        _require(isinstance(value, dict), "Percentiles must be an object or null.")
        _require(all(_text(k) and _number(v) for k, v in value.items()), "Invalid percentiles.")


def _count_fields(result: dict, names: tuple[str, ...]) -> None:
    """Require exact nonnegative counts."""
    for name in names:
        _require(_integer(result[name]), f"Invalid count: {name}.")


def _sample_counts(result: dict) -> None:
    """Reject inconsistent retained, missing and original sample sizes."""
    _count_fields(result, ("total", "missing"))
    count = result["count"]
    _require(count is None or _integer(count), "Invalid retained count.")
    if count is not None:
        _require(count + result["missing"] == result["total"], "Sample counts disagree.")


def _timing(result: dict) -> None:
    """Keep timing keys aligned and preserve JSON scalar identity without dtype coercion."""
    values, keys = result["values"], result["keys"]
    _require(isinstance(values, list) and all(_number(v) for v in values), "Invalid timing values.")
    _require(
        result["unit"] in ("seconds", "minutes", "hours", "days", "percentage", "ratio"),
        "Unsupported timing unit.",
    )
    if keys is not None:
        _require(isinstance(keys, list) and len(keys) == len(values), "Timing key lengths differ.")
        _require(
            all(isinstance(k, (str, bool)) or _number(k) for k in keys), "Invalid timing keys."
        )
        identities = [canonical_json(k) for k in keys]
        _require(len(set(identities)) == len(identities), "Duplicate timing keys.")
    _percentiles(result["percentiles"])


def _yield(result: dict) -> None:
    """Validate finite scalar yield contracts without inventing funnel denominator semantics."""
    _require(_number(result["value"]), "Yield requires a finite value.")
    _require(result["unit"] in ("fraction", "percentage", "ppm"), "Unsupported yield unit.")
    limits = {"fraction": 1, "percentage": 100, "ppm": 1_000_000}
    _require(0 <= result["value"] <= limits[result["unit"]], "Yield value outside its unit range.")
    for name in ("numerator", "denominator"):
        _require(result[name] is None or _integer(result[name]), f"Invalid yield {name}.")
    if result["denominator"] is not None:
        _require(result["denominator"] > 0, "Yield denominator must be positive.")
    _require(result["method"] is None or _text(result["method"]), "Invalid yield method.")


def _close(actual: Any, expected: float, label: str) -> None:
    """Check internally derived quantities with a documented float64 tolerance."""
    _require(_number(actual), f"Invalid derived field: {label}.")
    _require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), f"Inconsistent {label}.")


def _defect_counts(result: dict) -> None:
    """Validate aligned count buckets and the explicit opportunity denominator."""
    _require(result["schema_version"] == "1.0", "Unsupported defect-yield schema.")
    _count_fields(result, ("defect_count", "rework_count", "opportunities"))
    defects, rework = result["bucket_defects"], result["bucket_rework"]
    _require(
        isinstance(defects, list) and bool(defects) and isinstance(rework, list),
        "Defect yield requires count buckets.",
    )
    _require(len(defects) == len(rework), "Defect/rework bucket lengths differ.")
    _require(all(_integer(v) for v in defects + rework), "Invalid bucket counts.")
    _require(
        sum(defects) == result["defect_count"] and sum(rework) == result["rework_count"],
        "Bucket totals disagree.",
    )
    _require(result["opportunities"] > 0, "Opportunities must be positive.")
    _require(sum(defects) + sum(rework) <= result["opportunities"], "Loss exceeds opportunities.")


def _defect_yield(result: dict) -> None:
    """Verify opportunity estimates and optional actual DPU against retained counts."""
    _defect_counts(result)
    n, d, r = result["opportunities"], result["defect_count"], result["rework_count"]
    factors = [
        (n - a - b) / n
        for a, b in zip(result["bucket_defects"], result["bucket_rework"], strict=True)
    ]
    actual = result["bucket_first_time_yields"]
    _require(isinstance(actual, list) and len(actual) == len(factors), "Invalid bucket yields.")
    for left, right in zip(actual, factors, strict=True):
        _close(left, right, "bucket FTY")
    expected = {
        "yield_fraction": (n - d) / n,
        "first_time_yield": (n - d - r) / n,
        "rolled_throughput_yield": math.prod(factors),
        "dpmo": d / n * 1_000_000,
    }
    for key, value in expected.items():
        _close(result[key], value, key)
    _defect_units(result)


def _defect_units(result: dict) -> None:
    """An actual DPU rate requires a positive explicit unit denominator."""
    units = result["units"]
    if units is None:
        _require(result["defects_per_unit"] is None, "DPU requires units.")
    else:
        _require(_integer(units) and units > 0, "Units must be positive.")
        _close(result["defects_per_unit"], result["defect_count"] / units, "DPU")


def _descriptive(result: dict) -> None:
    """Validate estimates and counts while retaining unavailable values and group identities."""
    _numeric_fields(
        result,
        (
            "mean",
            "median",
            "std",
            "variance",
            "skew",
            "kurtosis",
            "min_value",
            "max_value",
            "range",
            "iqr",
            "mad",
            "coefficient_of_variation",
        ),
    )
    if "measurement_sum" in result:
        _numeric_fields(result, ("measurement_sum",))
    _sample_counts(result)
    _count_fields(result, ("mode_frequency", "unique_count"))
    _require(
        isinstance(result["modes"], list) and all(_number(v) for v in result["modes"]),
        "Invalid modes.",
    )
    _require(isinstance(result["group_keys"], dict), "Group keys must be an object.")
    _require(result["unit"] is None or _text(result["unit"]), "Invalid descriptive unit.")
    _percentiles(result["percentiles"])


def _interval(value: Any) -> None:
    """Require ordered finite interval endpoints or an unavailable interval."""
    if value is not None:
        _require(isinstance(value, list) and len(value) == 2, "Invalid confidence interval.")
        _require(all(_number(v) for v in value), "Invalid confidence interval endpoints.")
        _require(value[0] <= value[1], "Confidence interval endpoints are reversed.")


def _capability(result: dict) -> None:
    """Validate capability output contracts, retaining signed indices and unavailable estimates."""
    _numeric_fields(
        result, ("cp", "cpk", "z_score", "target", "lsl", "usl", "mean", "sigma", "cpl", "cpu")
    )
    _sample_counts(result)
    _require(
        _number(result["confidence_level"]) and 0 < result["confidence_level"] < 1,
        "Invalid confidence level.",
    )
    for name in ("confidence_interval", "cp_confidence_interval", "cpk_confidence_interval"):
        _interval(result[name])
    _require(result["unit"] is None or _text(result["unit"]), "Invalid capability unit.")
    for name in ("method", "variation_estimator"):
        _require(_text(result[name]), f"Invalid capability {name}.")


def _control_chart_keys(start_keys: Any, end_keys: Any, count: int) -> None:
    """Require overlapping pairs to reconstruct one unique portable source sequence."""
    _require(
        isinstance(start_keys, list)
        and isinstance(end_keys, list)
        and len(start_keys) == len(end_keys) == count,
        "Invalid control-chart pair keys.",
    )
    _require(
        all(_text(key) or isinstance(key, bool) or _number(key) for key in start_keys + end_keys),
        "Control-chart keys must be portable nonmissing scalars.",
    )
    start_identities = [(type(key).__name__, key) for key in start_keys]
    end_identities = [(type(key).__name__, key) for key in end_keys]
    _require(
        start_identities[1:] == end_identities[:-1],
        "Control-chart pair keys disagree on adjacent observations.",
    )
    identities = start_identities[:1] + end_identities
    _require(len(set(identities)) == count + 1, "Duplicate control-chart source keys.")


def _control_chart(result: dict) -> None:
    """Validate aligned MR pairs, limits, signals, and Phase I/II evidence."""
    _require(result["schema_version"] == "1.0", "Unsupported control-chart schema.")
    _require(result["chart"] == "moving_range", "Unsupported control-chart family.")
    _require(result["phase"] in ("I", "II"), "Invalid control-chart phase.")
    for name in ("moving_ranges", "pair_start_positions", "pair_end_positions"):
        _numeric_array(result[name], name)
    ranges = result["moving_ranges"]
    count = len(ranges)
    _require(all(value >= 0 for value in ranges), "Moving ranges must be nonnegative.")
    _require(
        result["observation_count"] == count + 1 and result["observation_count"] >= 2,
        "Control-chart observation count mismatch.",
    )
    _require(
        _integer(result["baseline_observation_count"])
        and result["baseline_observation_count"] >= 2,
        "Invalid baseline observation count.",
    )
    starts, ends = result["pair_start_positions"], result["pair_end_positions"]
    _require(
        all(_integer(value) for value in starts + ends)
        and starts == list(range(count))
        and ends == list(range(1, count + 1)),
        "Invalid adjacent source-pair positions.",
    )
    start_keys, end_keys = result["pair_start_keys"], result["pair_end_keys"]
    _require((start_keys is None) == (end_keys is None), "Incomplete control-chart pair keys.")
    if start_keys is not None:
        _control_chart_keys(start_keys, end_keys, count)
    for name in ("lcl", "center_line", "ucl", "nsigmas"):
        _require(_number(result[name]), f"Invalid control-chart field: {name}.")
    _require(
        0 <= result["lcl"] <= result["center_line"] <= result["ucl"],
        "Control-chart limits are not ordered.",
    )
    _require(result["nsigmas"] > 0, "Control-chart nsigmas must be positive.")
    indices = result["signal_indices"]
    positions = result["signal_source_positions"]
    _require(
        isinstance(indices, list)
        and all(_integer(value) and value < count for value in indices)
        and indices == sorted(set(indices)),
        "Invalid control-chart signal indices.",
    )
    expected_indices = [
        index
        for index, value in enumerate(ranges)
        if value < result["lcl"] or value > result["ucl"]
    ]
    _require(indices == expected_indices, "Control-chart signals disagree with limits.")
    _require(
        positions == [ends[index] for index in indices],
        "Control-chart signal source positions disagree.",
    )
    _require(result["unit"] is None or _text(result["unit"]), "Invalid control-chart unit.")
    fingerprint = result["baseline_result_fingerprint"]
    if result["phase"] == "I":
        _require(fingerprint is None, "Phase I cannot cite a baseline result.")
        _require(
            result["baseline_observation_count"] == result["observation_count"],
            "Phase I baseline count mismatch.",
        )
    else:
        _require(_text(fingerprint), "Phase II requires a baseline fingerprint.")


def _nonconformance(
    value: Any,
    observations: list,
    specification: dict,
    label: str,
) -> None:
    """Validate one observed specification-risk summary."""
    _object(
        value,
        {"total", "below_lsl", "above_usl", "nonconforming", "nonconforming_rate"},
        label,
    )
    for name in ("total", "below_lsl", "above_usl", "nonconforming"):
        _require(
            _integer(value[name]) and value[name] >= 0,
            f"Invalid {label} count: {name}.",
        )
    total = len(observations)
    _require(value["total"] == total, f"{label} total disagrees with observation count.")
    _require(
        value["nonconforming"] == value["below_lsl"] + value["above_usl"]
        and value["nonconforming"] <= total,
        f"Invalid {label} nonconforming counts.",
    )
    _require(
        _number(value["nonconforming_rate"])
        and 0 <= value["nonconforming_rate"] <= 1
        and math.isclose(
            value["nonconforming_rate"],
            value["nonconforming"] / total,
            rel_tol=0,
            abs_tol=1e-15,
        ),
        f"Invalid {label} nonconforming rate.",
    )
    lsl, usl = specification["lsl"], specification["usl"]
    expected_below = 0 if lsl is None else sum(item < lsl for item in observations)
    expected_above = 0 if usl is None else sum(item > usl for item in observations)
    _require(
        value["below_lsl"] == expected_below and value["above_usl"] == expected_above,
        f"{label} counts disagree with observations and specification.",
    )


def _capability_study(result: dict) -> None:
    """Validate nested short-/long-term evidence and observed risk."""
    _require(result["schema_version"] == "1.0", "Unsupported capability-study schema.")
    _specification(result["specification"])
    short_capability = result["short_term_capability"]
    short_distribution = result["short_term_distribution"]
    validate_result(short_capability)
    validate_result(short_distribution)
    _require(
        short_capability["result_type"] == "CapabilityResult"
        and short_distribution["result_type"] == "DistributionProfileResult",
        "Invalid short-term capability-study evidence.",
    )
    _require(
        short_capability["count"] == len(short_distribution["values"]),
        "Short-term study counts disagree.",
    )
    _require(
        short_capability["lsl"] == result["specification"]["lsl"]
        and short_capability["usl"] == result["specification"]["usl"]
        and short_capability["target"] == result["specification"]["target"]
        and short_capability["unit"] == result["specification"]["unit"]
        and short_distribution["unit"] == result["specification"]["unit"],
        "Short-term study specification disagrees.",
    )
    _nonconformance(
        result["short_term_nonconformance"],
        short_distribution["values"],
        result["specification"],
        "short-term nonconformance",
    )
    long_values = (
        result["long_term_capability"],
        result["long_term_distribution"],
        result["long_term_nonconformance"],
    )
    _require(
        all(value is None for value in long_values)
        or all(value is not None for value in long_values),
        "Incomplete long-term capability-study evidence.",
    )
    if long_values[0] is not None:
        long_capability, long_distribution, long_nonconformance = long_values
        validate_result(long_capability)
        validate_result(long_distribution)
        _require(
            long_capability["result_type"] == "CapabilityResult"
            and long_distribution["result_type"] == "DistributionProfileResult",
            "Invalid long-term capability-study evidence.",
        )
        _require(
            long_capability["count"] == len(long_distribution["values"]),
            "Long-term study counts disagree.",
        )
        _require(
            long_capability["lsl"] == result["specification"]["lsl"]
            and long_capability["usl"] == result["specification"]["usl"]
            and long_capability["target"] == result["specification"]["target"]
            and long_capability["unit"] == result["specification"]["unit"]
            and long_distribution["unit"] == result["specification"]["unit"],
            "Long-term study specification disagrees.",
        )
        _nonconformance(
            long_nonconformance,
            long_distribution["values"],
            result["specification"],
            "long-term nonconformance",
        )


def _mean_ci(result: dict) -> None:
    """Validate inferential estimates, interval policy and optional normality diagnostics."""
    _numeric_fields(
        result,
        (
            "mean",
            "standard_deviation",
            "standard_error",
            "critical_value",
            "population_variance",
            "shapiro_statistic",
            "shapiro_p_value",
        ),
    )
    _sample_counts(result)
    for name in ("confidence_level", "normality_alpha"):
        _require(_number(result[name]) and 0 < result[name] < 1, f"Invalid {name}.")
    _interval(result["confidence_interval"])
    _require(result["distribution"] in ("student_t", "normal"), "Invalid interval distribution.")
    _require(
        result["variance_source"] in ("sample", "known_population"),
        "Invalid variance source.",
    )
    degrees = result["degrees_of_freedom"]
    _require(degrees is None or _integer(degrees) and degrees > 0, "Invalid degrees of freedom.")
    if result["distribution"] == "student_t":
        _require(degrees == result["count"] - 1, "Student t degrees of freedom mismatch.")
    else:
        _require(degrees is None, "Normal intervals cannot have t degrees of freedom.")
    if result["variance_source"] == "known_population":
        _require(result["population_variance"] is not None, "Known variance is missing.")
    else:
        _require(result["population_variance"] is None, "Sample variance source is inconsistent.")
    for name in ("shapiro_statistic", "shapiro_p_value"):
        _require(
            (result[name] is None) == (result["shapiro_statistic"] is None),
            "Incomplete Shapiro-Wilk diagnostic.",
        )
    if result["shapiro_p_value"] is not None:
        _require(0 <= result["shapiro_p_value"] <= 1, "Invalid Shapiro-Wilk p-value.")
    _require(result["unit"] is None or _text(result["unit"]), "Invalid inference unit.")


def _numeric_array(value: Any, label: str, *, nonempty: bool = True) -> None:
    """Require a finite JSON numerical array."""
    _require(isinstance(value, list), f"Invalid {label}.")
    _require(not nonempty or bool(value), f"Invalid {label}.")
    _require(all(_number(item) for item in value), f"Invalid {label}.")


def _distribution_profile(result: dict) -> None:
    """Validate exact observations and internally aligned prepared diagnostic evidence."""
    _sample_counts(result)
    count = result["count"]
    for name in (
        "values",
        "source_positions",
        "histogram_edges",
        "histogram_counts",
        "histogram_density",
        "ecdf_values",
        "ecdf_probabilities",
        "qq_theoretical",
        "qq_observed",
        "qq_line_x",
        "qq_line_y",
    ):
        _numeric_array(result[name], name)
    for name in ("outlier_values", "outlier_source_positions", "density_x", "density_y"):
        _numeric_array(result[name], name, nonempty=False)
    _require(len(result["values"]) == count, "Distribution observation count mismatch.")
    _require(
        len(result["source_positions"]) == count
        and all(_integer(position) for position in result["source_positions"])
        and len(set(result["source_positions"])) == count,
        "Invalid distribution source positions.",
    )
    keys = result["keys"]
    _require(keys is None or isinstance(keys, list) and len(keys) == count, "Invalid profile keys.")
    if keys is not None:
        _json_tree(keys)
        _require(
            len({canonical_json(key) for key in keys}) == count,
            "Distribution profile keys must be unique.",
        )
    _numeric_fields(
        result,
        (
            "mean",
            "median",
            "std",
            "skew",
            "kurtosis",
            "qq_slope",
            "qq_intercept",
            "qq_r",
            "q1",
            "q3",
            "iqr",
            "lower_fence",
            "upper_fence",
            "lower_whisker",
            "upper_whisker",
            "shapiro_statistic",
            "shapiro_p_value",
            "density_bandwidth",
        ),
    )
    _require(result["std"] >= 0 and result["iqr"] >= 0, "Invalid distribution spread.")
    _require(
        result["q1"] <= result["median"] <= result["q3"],
        "Invalid distribution quartile order.",
    )
    _require(
        result["lower_whisker"] <= result["upper_whisker"],
        "Invalid distribution whiskers.",
    )
    edges = result["histogram_edges"]
    histogram_counts = result["histogram_counts"]
    _require(
        len(edges) == len(histogram_counts) + 1
        and all(left < right for left, right in zip(edges, edges[1:], strict=False)),
        "Invalid histogram edges.",
    )
    _require(
        all(_integer(value) for value in histogram_counts)
        and sum(histogram_counts) == count
        and len(result["histogram_density"]) == len(histogram_counts),
        "Invalid histogram evidence.",
    )
    for name in ("ecdf_values", "ecdf_probabilities", "qq_theoretical", "qq_observed"):
        _require(len(result[name]) == count, f"Invalid {name} length.")
    _require(
        result["ecdf_values"] == sorted(result["ecdf_values"]),
        "ECDF values must be ordered.",
    )
    _require(
        result["ecdf_values"] == sorted(result["values"]),
        "ECDF values differ from observations.",
    )
    _require(
        all(
            left < right
            for left, right in zip(
                result["ecdf_probabilities"],
                result["ecdf_probabilities"][1:],
                strict=False,
            )
        )
        and result["ecdf_probabilities"][-1] == 1,
        "Invalid ECDF probabilities.",
    )
    _require(
        result["qq_distribution"] == "normal"
        and len(result["qq_line_x"]) == len(result["qq_line_y"]) == 2,
        "Invalid Q-Q evidence.",
    )
    _require(
        result["outlier_method"] in ("iqr", "none")
        and _number(result["outlier_multiplier"])
        and result["outlier_multiplier"] > 0,
        "Invalid outlier policy.",
    )
    if result["outlier_method"] == "none":
        _require(
            result["lower_fence"] is None
            and result["upper_fence"] is None
            and result["outlier_values"] == [],
            "Disabled outlier policy retained flags.",
        )
    outlier_count = len(result["outlier_values"])
    _require(
        len(result["outlier_source_positions"]) == outlier_count
        and all(_integer(position) for position in result["outlier_source_positions"]),
        "Invalid outlier positions.",
    )
    outlier_keys = result["outlier_keys"]
    _require(
        outlier_keys is None
        or isinstance(outlier_keys, list)
        and len(outlier_keys) == outlier_count,
        "Invalid outlier keys.",
    )
    if outlier_keys is not None:
        _json_tree(outlier_keys)
    positions = dict(zip(result["source_positions"], result["values"], strict=True))
    _require(
        all(
            position in positions and positions[position] == value
            for position, value in zip(
                result["outlier_source_positions"], result["outlier_values"], strict=True
            )
        ),
        "Outlier evidence differs from observations.",
    )
    _require(
        _number(result["normality_alpha"]) and 0 < result["normality_alpha"] < 1,
        "Invalid profile normality alpha.",
    )
    _require(
        (result["shapiro_statistic"] is None) == (result["shapiro_p_value"] is None),
        "Incomplete profile Shapiro-Wilk diagnostic.",
    )
    if result["shapiro_p_value"] is not None:
        _require(0 <= result["shapiro_p_value"] <= 1, "Invalid profile Shapiro-Wilk p-value.")
    density_method = result["density_method"]
    if density_method is None:
        _require(
            result["density_bandwidth"] is None
            and result["density_x"] == []
            and result["density_y"] == [],
            "Unavailable density must not retain evidence.",
        )
    else:
        _require(
            density_method == "gaussian_kde"
            and _number(result["density_bandwidth"])
            and result["density_bandwidth"] > 0
            and len(result["density_x"]) == len(result["density_y"])
            and len(result["density_x"]) >= 32,
            "Invalid density evidence.",
        )
    _require(result["unit"] is None or _text(result["unit"]), "Invalid profile unit.")
    _require(_text(result["histogram_bin_method"]), "Invalid histogram method.")


def _reconstruction(result: dict) -> None:
    """Require inspectable finite reconstruction tables in portable snapshots."""
    metadata = result["metadata"]
    for name in ("orders", "activities", "activity_records", "source_records"):
        table = metadata.get(name)
        _require(isinstance(table, list) and bool(table), f"Missing reconstruction {name}.")
        _require(all(isinstance(row, dict) and row for row in table), "Invalid evidence rows.")
    _require(metadata.get("exclusions") == [], "Reconstruction cannot silently exclude rows.")
    for name in ("unit", "clock", "boundary"):
        _require(_text(metadata.get(name)), f"Missing reconstruction {name}.")
    columns = metadata.get("table_columns")
    _require(isinstance(columns, dict), "Reconstruction table column order is required.")
    for name in ("orders", "activities", "activity_records", "source_records"):
        names = columns.get(name)
        _require(isinstance(names, list) and all(_text(v) for v in names), "Invalid table columns.")
        _require(len(set(names)) == len(names), "Duplicate table columns.")
        _require(all(set(row) == set(names) for row in metadata[name]), "Evidence schema mismatch.")
    _json_tree(metadata)


def _process_map(result: dict) -> None:
    """Validate typed observed nodes and exact direct-follow counts without rediscovery."""
    metadata = result["metadata"]
    nodes, edges = metadata.get("nodes"), metadata.get("edges")
    _require(isinstance(nodes, list) and all(_text(n) for n in nodes), "Invalid discovered nodes.")
    _require(len(set(nodes)) == len(nodes), "Duplicate discovered nodes.")
    _require(isinstance(edges, dict), "Invalid discovered edges.")
    for source, targets in edges.items():
        _require(source in nodes and isinstance(targets, dict), "Unknown discovery source.")
        _require(
            all(
                target in nodes and _integer(count) and count > 0
                for target, count in targets.items()
            ),
            "Invalid discovery transition counts.",
        )
    _json_tree(metadata)


RESULT_CHECKS = {
    "ProcessMapResult": _process_map,
    "OrderReconstructionResult": _reconstruction,
    "TimingResult": _timing,
    "YieldResult": _yield,
    "DefectYieldResult": _defect_yield,
    "DescriptiveResult": _descriptive,
    "DistributionProfileResult": _distribution_profile,
    "MeanCIResult": _mean_ci,
    "CapabilityResult": _capability,
    "CapabilityStudyResult": _capability_study,
    "ControlChartResult": _control_chart,
}


def validate_result(result: Any) -> None:
    """Validate a complete current typed analytical payload without importing its runtime."""
    _require(isinstance(result, dict), "Result must be an object.")
    kind = result.get("result_type")
    _require(isinstance(kind, str) and kind in RESULT_FIELDS, "Unsupported result type.")
    fields = BASE_FIELDS | RESULT_FIELDS[kind]
    # Additive describe 1.1 field; older saved results restore with an unavailable sum.
    if kind == "DescriptiveResult" and "measurement_sum" in result:
        fields = fields | {"measurement_sum"}
    _object(result, fields, "result")
    _require(_text(result["name"]), "Result name is required.")
    _require(isinstance(result["metadata"], dict), "Result metadata must be an object.")
    _require(
        result["interpretation_context"] is None or _text(result["interpretation_context"]),
        "Invalid result interpretation context.",
    )
    _provenance(result["provenance"])
    _require(result["provenance"]["method"] in METHODS[kind], "Result/method mismatch.")
    RESULT_CHECKS[kind](result)


LEGACY_FIELDS = {
    "bundle_type",
    "bundle_version",
    "name",
    "package_version",
    "created_at",
    "cohort_definition",
    "specification_metadata",
    "interpretation_notes",
    "metadata",
    "results",
}
AUDIT_FIELDS = (LEGACY_FIELDS - {"specification_metadata"}) | {
    "inputs",
    "specifications",
    "software_versions",
    "context",
    "sha256",
}
SPEC_FIELDS = {
    "name",
    "unit",
    "direction",
    "target",
    "lsl",
    "usl",
    "defect_definition",
    "opportunity_definition",
    "opportunities_per_unit",
    "group_by",
    "cohort",
    "time_window",
    "decision_context",
    "schema_version",
}


def _bundle_header(body: dict) -> None:
    """Validate shared bundle metadata for legacy and audited formats."""
    for name in ("name", "package_version"):
        _require(_text(body[name]), f"Bundle requires {name}.")
    _datetime(body["created_at"], "bundle")
    _require(isinstance(body["metadata"], dict), "Bundle metadata must be an object.")
    for name in ("cohort_definition", "interpretation_notes"):
        _require(body[name] is None or _text(body[name]), f"Invalid {name}.")


def _inputs(inputs: Any) -> None:
    """Require explicitly selected, fingerprinted input artifacts with unique identifiers."""
    _require(isinstance(inputs, dict) and bool(inputs), "Audited bundles require inputs.")
    for identifier, item in inputs.items():
        _require(_text(identifier), "Input ids must be nonblank.")
        _object(item, {"reference", "sha256", "selection", "media_type"}, "input reference")
        for field in ("reference", "selection", "media_type"):
            _require(_text(item[field]), f"Input requires {field}.")
        _require(
            isinstance(item["sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None,
            "Input SHA-256 must contain 64 lowercase hexadecimal characters.",
        )


def _specification(spec: Any) -> None:
    """Validate the supported CTQ declaration with no dataframe or analytical runtime."""
    _object(spec, SPEC_FIELDS, "specification")
    _require(spec["schema_version"] == "1.0", "Unsupported specification schema.")
    _require(_text(spec["name"]) and _text(spec["unit"]), "Specification requires name and unit.")
    _require(spec["direction"] in ("lower", "higher", "target"), "Invalid specification direction.")
    _numeric_fields(spec, ("target", "lsl", "usl"))
    _spec_limits(spec)
    _spec_context(spec)


def _spec_limits(spec: dict) -> None:
    """Require ordered limits and a target inside the declared specification."""
    lo, hi, target = spec["lsl"], spec["usl"], spec["target"]
    if lo is not None and hi is not None:
        _require(lo < hi, "Specification limits are reversed.")
    if spec["direction"] == "target":
        _require(target is not None, "Target direction requires a target.")
    if target is not None:
        _require(lo is None or target >= lo, "Target is below specification.")
        _require(hi is None or target <= hi, "Target is above specification.")


def _spec_context(spec: dict) -> None:
    """Check opportunity and observation-window declarations without applying them."""
    for name in ("defect_definition", "opportunity_definition", "cohort", "decision_context"):
        _require(spec[name] is None or _text(spec[name]), f"Invalid specification {name}.")
    count = spec["opportunities_per_unit"]
    if count is not None:
        _require(
            _integer(count) and count > 0 and _text(spec["opportunity_definition"]),
            "Invalid specification opportunities.",
        )
    groups = spec["group_by"]
    _require(isinstance(groups, list) and all(_text(v) for v in groups), "Invalid group columns.")
    _require(len(set(groups)) == len(groups), "Duplicate group columns.")
    if spec["time_window"] is not None:
        _window(spec["time_window"])


def _window(window: Any) -> None:
    """Validate ISO window endpoints and compatible awareness."""
    _object(window, {"start", "end"}, "window")
    _require(any(v is not None for v in window.values()), "Window requires an endpoint.")
    for value in window.values():
        if value is not None:
            _datetime(value, "window")
    if all(v is not None for v in window.values()):
        start, end = (datetime.fromisoformat(window[k]) for k in ("start", "end"))
        _require(
            (start.utcoffset() is None) == (end.utcoffset() is None), "Mixed window awareness."
        )
        _require(start < end, "Window endpoints are reversed.")


def _references(value: Any, available: dict, label: str, *, required: bool = False) -> None:
    """Reject dangling and duplicate relationships between results and declared artifacts."""
    _require(
        isinstance(value, list) and all(_text(v) for v in value), f"Invalid {label} references."
    )
    _require(len(set(value)) == len(value), f"Duplicate {label} references.")
    _require(set(value) <= set(available), f"Unknown {label} reference.")
    if required:
        _require(bool(value), f"Result requires {label} references.")


def _versions(versions: Any, package_version: str) -> None:
    """Record explicit software versions including the analytical package identity."""
    _require(isinstance(versions, dict) and bool(versions), "Software versions are required.")
    _require(all(_text(k) and _text(v) for k, v in versions.items()), "Invalid software versions.")
    _require(
        {"lss4py", "numpy", "narwhals"} <= set(versions), "Missing analytical software versions."
    )
    _require(
        versions.get("lss4py") == package_version,
        "Bundle package version differs from software context.",
    )


def _result_context(entry: dict, body: dict) -> None:
    """Check saved versions and specifications against the recorded context."""
    result = entry["result"]
    _require(
        result["provenance"]["package_version"] == body["package_version"],
        "Result package version differs from bundle.",
    )
    backend = result["provenance"]["backend"]
    if backend != "unknown":
        _require(backend in body["software_versions"], "Missing input backend software version.")
    for package in ("numpy", "scipy", "narwhals"):
        version = result["metadata"].get(f"{package}_version")
        if version is not None:
            _require(
                body["software_versions"].get(package) == version,
                f"Missing or conflicting software version: {package}.",
            )
    parameters = result["provenance"]["parameters"]
    for package, recorded in parameters.get("runtime_versions", {}).items():
        _require(
            body["software_versions"].get(package) == recorded,
            f"Missing or conflicting software version: {package}.",
        )
    if "backend_version" in parameters:
        _require(
            body["software_versions"].get(backend) == parameters["backend_version"],
            "Conflicting backend software version.",
        )
    _parameter_context(result)
    declared = result["provenance"]["parameters"].get("specification")
    if declared is not None:
        linked = [body["specifications"][k] for k in entry["specification_ids"]]
        _require(declared in linked, "Result specification is not preserved by its links.")
        _spec_result_context(result, declared)
    if result["result_type"] == "CapabilityStudyResult":
        for name in (
            "short_term_capability",
            "short_term_distribution",
            "long_term_capability",
            "long_term_distribution",
        ):
            child = result[name]
            if child is not None:
                _result_context({**entry, "result": child}, body)


def _parameter_context(result: dict) -> None:
    """Keep output units and defect denominators consistent with saved method arguments."""
    parameters = result["provenance"]["parameters"]
    if "unit" in parameters and "unit" in result:
        _require(result["unit"] == parameters["unit"], "Result unit differs from parameters.")
    if result["result_type"] == "DefectYieldResult":
        for name in ("opportunities", "units"):
            if name in parameters:
                _require(
                    result[name] == parameters[name], f"Result {name} differs from parameters."
                )


def _spec_result_context(result: dict, declared: dict) -> None:
    """Preserve capability units and acceptance limits without recomputing estimates."""
    if result["result_type"] == "CapabilityResult":
        for name in ("unit", "target", "lsl", "usl"):
            _require(result[name] == declared[name], f"Result specification {name} differs.")


def _audited(body: dict) -> None:
    """Validate artifact relationships, versioned typed results and the snapshot hash."""
    _require(_text(body["cohort_definition"]), "Audited bundles require a cohort definition.")
    _inputs(body["inputs"])
    _versions(body["software_versions"], body["package_version"])
    _require(isinstance(body["context"], dict), "Bundle context must be an object.")
    _require(isinstance(body["specifications"], dict), "Specifications must be an object.")
    for identifier, spec in body["specifications"].items():
        _require(_text(identifier), "Specification ids must be nonblank.")
        _specification(spec)
    _entries(body)
    expected = bundle_fingerprint({k: v for k, v in body.items() if k != "sha256"})
    _require(body["sha256"] == expected, "Bundle fingerprint mismatch.")


def _entries(body: dict) -> None:
    """Validate every current result and its explicit input/specification associations."""
    results = body["results"]
    _require(isinstance(results, dict) and bool(results), "Bundle requires named results.")
    for identifier, entry in results.items():
        _require(_text(identifier), "Result ids must be nonblank.")
        _object(
            entry, {"schema_version", "result", "input_ids", "specification_ids"}, "result entry"
        )
        _require(entry["schema_version"] == "1.0", "Unsupported result schema version.")
        validate_result(entry["result"])
        _references(entry["input_ids"], body["inputs"], "input", required=True)
        _references(entry["specification_ids"], body["specifications"], "specification")
        _result_context(entry, body)


def validate_bundle(value: Any) -> dict:
    """Return detached validated finite JSON data; never load sources or execute methods.

    Version 1.0 is legacy storage without complete audit context. Version 2.0
    requires inputs, selections, software versions and typed result relationships.
    Unknown versions and fields are rejected rather than silently migrated.
    """
    try:
        if isinstance(value, str):
            value = json.loads(value, object_pairs_hook=_unique_object)
        body = json.loads(canonical_json(value))
    except (TypeError, ValueError, RecursionError) as exc:
        raise BundleValidationError(f"Invalid bundle JSON: {exc}") from exc
    _require(isinstance(body, dict), "Bundle must be an object.")
    version = body.get("bundle_version")
    _require(version in ("1.0", "2.0"), "Unsupported bundle schema version.")
    _object(body, LEGACY_FIELDS if version == "1.0" else AUDIT_FIELDS, "bundle")
    _require(body["bundle_type"] == "AnalysisBundle", "Invalid bundle type.")
    _bundle_header(body)
    if version == "1.0":
        _legacy(body)
    else:
        _audited(body)
    return body


def _unique_object(items: list[tuple[str, Any]]) -> dict:
    """Reject duplicate JSON object members instead of silently keeping the last value."""
    result = {}
    for key, value in items:
        _require(key not in result, f"Duplicate JSON field: {key}.")
        result[key] = value
    return result


def _legacy(body: dict) -> None:
    """Restore the original skeleton's complete results without inventing missing audit data."""
    results = body["results"]
    _require(isinstance(results, list) and bool(results), "Legacy bundle requires results.")
    for result in results:
        validate_result(result)
    _require(
        body["specification_metadata"] is None or isinstance(body["specification_metadata"], dict),
        "Legacy specification metadata must be an object or null.",
    )


def main() -> None:
    """Validate one saved bundle using only the Python standard library."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        body = validate_bundle(args.bundle.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, BundleValidationError) as exc:
        parser.exit(1, f"Invalid bundle: {exc}\n")
    print(
        json.dumps(
            {
                "valid": True,
                "bundle_version": body["bundle_version"],
                "audited": body["bundle_version"] == "2.0",
                "results": len(body["results"]),
            }
        )
    )


if __name__ == "__main__":
    main()
