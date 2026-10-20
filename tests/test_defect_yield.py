"""Defect/rework counting contract and genuine R parity on all eager backends."""

import json

import pandas as pd
import pytest

from lss4py import ValidationError, process_yield
from tests.reference_catalog import load_catalog

pytestmark = pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
REFERENCE = next(e for e in load_catalog() if e["metadata"]["id"] == "r-sixsigma-baseline")
CASES = [case for case in REFERENCE["expected"] if case["method"] == "ss.ca.yield"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_genuine_r_counting_reference(frame_factory, case):
    """Map legacy R DPU to a count and retain all four numerical estimates."""
    args = case["parameters"]
    counts = {k: v if isinstance(v, list) else [v] for k, v in args.items()}
    result = process_yield(
        frame_factory({"d": counts["defects"], "r": counts["rework"]}),
        defects_column="d",
        rework_column="r",
        opportunities=args["opportunities"],
    )
    expected = case["expected"]["value"][0]
    mapped = {
        "Yield": result.yield_fraction,
        "FTY": result.first_time_yield,
        "RTY": result.rolled_throughput_yield,
        "DPU": result.defect_count,
        "DPMO": result.dpmo,
    }
    assert mapped == pytest.approx(
        expected, rel=case["tolerance"]["relative"], abs=case["tolerance"]["absolute"]
    )
    assert result.defects_per_unit is None
    assert result.opportunities == args["opportunities"]
    assert result.provenance.parameters["formula_source"] == "SixSigma 0.11.1 ss.ca.yield"


def test_denominators_and_independent_arithmetic(frame_factory):
    """Preserve bucket positions, source data, strict JSON and independent unit rates."""
    records = {"defects": [2, 1, 0], "rework": [1, 0, 2]}
    frame = frame_factory(records)
    result = process_yield(frame, rework_column="rework", opportunities=20, units=5)
    assert (result.defect_count, result.rework_count, result.opportunities, result.units) == (
        3,
        3,
        20,
        5,
    )
    assert result.yield_fraction == 17 / 20
    assert result.first_time_yield == 14 / 20
    assert result.bucket_first_time_yields == (17 / 20, 19 / 20, 18 / 20)
    assert result.rolled_throughput_yield == pytest.approx(17 * 19 * 18 / 20**3)
    assert result.dpmo == 150000
    assert result.defects_per_unit == 0.6


def test_backend_payload_and_source_preservation(frame_factory, neutral_payload, assert_equivalent):
    """Keep complete payloads equivalent and never change source count tables."""
    records = {"defects": [2, 1, 0], "rework": [1, 0, 2]}
    frame = frame_factory(records)
    before = str(frame)
    result = process_yield(frame, rework_column="rework", opportunities=20, units=5)
    assert result.bucket_defects == (2, 1, 0)
    assert result.bucket_rework == (1, 0, 2)
    assert str(frame) == before
    expected = process_yield(
        pd.DataFrame(records), rework_column="rework", opportunities=20, units=5
    )
    assert_equivalent(neutral_payload(result), neutral_payload(expected))
    payload = json.loads(json.dumps(result.to_dict(), allow_nan=False))
    assert payload == json.loads(result.to_json())
    assert payload["schema_version"] == "1.0"
    assert payload["bucket_defects"] == [2, 1, 0]


def test_optional_rework_and_exhausted_opportunities(frame_factory):
    """Omitted rework is zero, while complete loss returns finite zero yields."""
    result = process_yield(frame_factory({"defects": [10]}), opportunities=10)
    assert result.bucket_rework == (0,)
    assert result.yield_fraction == result.first_time_yield == result.rolled_throughput_yield == 0
    assert result.dpmo == 1_000_000
    assert result.units is None
    assert result.defects_per_unit is None


@pytest.mark.parametrize("column", ["defects", "rework"])
@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), -1, 0.5, True, "2"])
def test_invalid_counts_rejected_without_coercion(frame_factory, column, bad):
    """Reject missing, infinite, negative, fractional, text and boolean count domains."""
    records = {"defects": [1], "rework": [0]}
    records[column] = [bad]
    with pytest.raises(ValidationError, match="counts"):
        process_yield(frame_factory(records), opportunities=10, rework_column="rework")


@pytest.mark.parametrize("parameter", ["opportunities", "units"])
@pytest.mark.parametrize("bad", [0, -1, True, "10", 1.5, float("nan"), float("inf")])
def test_invalid_denominators(frame_factory, parameter, bad):
    """Neither opportunity nor unit denominators may be implicit or nonpositive."""
    options = {
        "opportunities": bad if parameter == "opportunities" else 10,
        "units": bad if parameter == "units" else None,
    }
    with pytest.raises(ValidationError):
        process_yield(
            frame_factory({"defects": [1]}),
            opportunities=options["opportunities"],
            units=options["units"],
        )


def test_empty_missing_and_impossible_counts(frame_factory):
    """Reject empty evidence, missing bindings and double-counted loss populations."""
    with pytest.raises(ValidationError, match="bucket"):
        process_yield(frame_factory({"defects": []}), opportunities=10)
    with pytest.raises(ValidationError, match="Missing required columns"):
        process_yield(frame_factory({"x": [1]}), opportunities=10)
    with pytest.raises(ValidationError, match="Missing required columns"):
        process_yield(frame_factory({"defects": [1]}), opportunities=10, rework_column="r")
    with pytest.raises(ValidationError, match="cannot exceed"):
        process_yield(
            frame_factory({"defects": [6, 3], "rework": [0, 2]}),
            rework_column="rework",
            opportunities=10,
        )


def test_exact_integer_reduction(frame_factory):
    """Do not round large integer counts through float64 or overflow int64 sums."""
    count = 2**53 + 1
    result = process_yield(frame_factory({"defects": [count, count]}), opportunities=2 * count)
    assert result.defect_count == 2 * count
    assert result.yield_fraction == 0
    assert result.first_time_yield == 0
    assert result.rolled_throughput_yield == 0.25


def test_r_invalid_denominator_difference(frame_factory):
    """R returns nonfinite output for zero opportunities; Python rejects it explicitly."""
    case = next(c for c in REFERENCE["invalid"] if c["id"] == "yield-zero-opportunities")
    assert case["expected"]["status"] == "returned"
    args = case["parameters"]
    with pytest.raises(ValidationError, match="positive"):
        process_yield(
            frame_factory({"defects": args["defects"], "rework": args["rework"]}),
            rework_column="rework",
            opportunities=0,
        )


def test_r_excess_loss_difference(frame_factory):
    """Reject R's negative FTY rather than report impossible opportunity fractions."""
    case = next(c for c in REFERENCE["invalid"] if c["id"] == "yield-excess-loss")
    assert case["expected"]["value"][0]["FTY"] < 0
    args = case["parameters"]
    with pytest.raises(ValidationError, match="cannot exceed"):
        process_yield(
            frame_factory({"defects": args["defects"], "rework": args["rework"]}),
            rework_column="rework",
            opportunities=args["opportunities"],
        )


def test_integral_float_counts(frame_factory):
    """Accept exact integral numeric counts without coercing invalid numeric domains."""
    result = process_yield(frame_factory({"defects": [1.0, 2.0]}), opportunities=10)
    assert result.defect_count == 3
    with pytest.raises(ValidationError, match="exact integer"):
        process_yield(frame_factory({"defects": [float(2**54)]}), opportunities=2**55)


def test_r_recycling_is_unrepresentable(frame_factory):
    """A single eager frame structurally prevents mismatched R vector lengths."""
    case = next(c for c in REFERENCE["invalid"] if c["id"] == "yield-length-mismatch")
    args = case["parameters"]
    assert case["expected"]["warnings"]
    # Padding unequal source vectors exposes missing counts instead of recycling.
    with pytest.raises(ValidationError, match="counts"):
        process_yield(
            frame_factory({"defects": args["defects"], "rework": [0, 1, None]}),
            rework_column="rework",
            opportunities=args["opportunities"],
        )


@pytest.mark.parametrize(
    ("defects_column", "rework_column"),
    [(None, None), ("", None), ("defects", "defects"), (1, None), ("defects", False)],
)
def test_invalid_column_roles(frame_factory, defects_column, rework_column):
    """Reject ambiguous roles before selecting columns or calculating losses."""
    with pytest.raises(ValidationError, match="names"):
        process_yield(
            frame_factory({"defects": [1]}),
            opportunities=10,
            defects_column=defects_column,
            rework_column=rework_column,
        )
