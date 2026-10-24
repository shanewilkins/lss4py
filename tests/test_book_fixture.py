"""Offline checks for adopted source bytes, conventions and independent baseline arithmetic."""

import csv
import hashlib
import json
import math
from decimal import Decimal

import pytest

from lss4py import process_cycle_efficiency
from tests.reference_catalog import ROOT, load_catalog

FIXTURE = ROOT / "washnfold-friday91"


def _rows(name):
    """Read the frozen CSV without depending on the sibling book checkout."""
    with (FIXTURE / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _json(name):
    """Read independent declared expectations or conventions."""
    return json.loads((FIXTURE / name).read_text())


def _times(rows, column):
    """Use exact displayed decimals for independent fixture arithmetic."""
    return [Decimal(row[column]) for row in rows]


@pytest.mark.parametrize(
    ("local", "source"), _json("conventions.json")["raw_artifact_source_paths"].items()
)
def test_source_bytes_match_adopted_snapshot(local, source):
    conventions = _json("conventions.json")
    assert (
        hashlib.sha256((FIXTURE / local).read_bytes()).hexdigest()
        == conventions["source_sha256"][source]
    )


def test_catalog_version_and_clock_match_conventions():
    entry = next(e for e in load_catalog() if e["metadata"]["id"] == "washnfold-friday91")
    conventions = _json("conventions.json")
    assert entry["metadata"]["version"] == conventions["version"] == "1.0.0"
    assert conventions["clock"]["kind"] == "cumulative_operating"
    assert conventions["va"]["staging"] == "RNVA"
    assert conventions["boundary"]["completion_activity"] == "Send readiness notification"


@pytest.mark.parametrize("name", _json("inputs.json")["columns"])
def test_normalization_preserves_source_measurements_and_strings(name):
    values = _json("inputs.json")["columns"][name]
    observed = [row[name] for row in _rows("order_summary.csv")]
    converted = [v if isinstance(v, str) else str(v) for v in values]
    assert observed == converted


def test_order_cases_are_unique():
    rows = _rows("order_summary.csv")
    assert len({row["Order ID"] for row in rows}) == len(rows) == 39


@pytest.mark.parametrize(
    ("column", "key"), [("Operating L/T (min)", "total_lead"), ("VA time (min)", "total_va")]
)
def test_decimal_cohort_sums(column, key):
    assert sum(_times(_rows("order_summary.csv"), column)) == Decimal(
        _json("baseline.json")["minutes"][key]
    )


@pytest.fixture
def eligible():
    """Select the actual promise cohort independently of prepared flags."""
    return [r for r in _rows("order_summary.csv") if Decimal(r["Arrival (elapsed min)"]) <= 120]


def test_eligible_counts_and_deadline(eligible):
    baseline = _json("baseline.json")
    assert len(eligible) == baseline["counts"]["eligible"] == 21
    assert 39 - len(eligible) == baseline["counts"]["ineligible"] == 18
    assert sum(Decimal(r["Ready and notified (elapsed min)"]) > 600 for r in eligible) == 6


def test_eligible_tail_and_median(eligible):
    baseline = _json("baseline.json")
    leads = sorted(_times(eligible, "Operating L/T (min)"))
    rank = math.ceil(Decimal("0.90") * len(leads))
    assert rank == baseline["nearest_rank_p90_position"] == 19
    assert leads[rank - 1] == Decimal(baseline["minutes"]["eligible_nearest_rank_p90"])
    assert leads[len(leads) // 2] == Decimal(baseline["minutes"]["eligible_median_lead"])
    assert sum(leads) == Decimal(baseline["minutes"]["eligible_total_lead"])


def test_pce_uses_decimal_ratio_of_sums():
    rows = _rows("order_summary.csv")
    total = sum(_times(rows, "Operating L/T (min)"))
    va = sum(_times(rows, "VA time (min)"))
    assert f"{100 * va / total:.1f}" == _json("baseline.json")["display"]["pce_percent"] == "13.7"


@pytest.mark.parametrize(
    ("component", "display"), [("P/T", "mean_pt"), ("W/T", "mean_wt"), ("S/T", "mean_st")]
)
def test_order_component_means(component, display):
    rows = _rows("order_summary.csv")
    value = sum(_times(rows, f"Total {component} (min)")) / len(rows)
    assert f"{value:.1f}" == _json("baseline.json")["display"][display]


def test_correction_occurrences_and_affected_orders():
    events = _rows("event_log.csv")
    corrections = [r for r in events if r["Activity Name"] == "Fold correction"]
    assert len(events) == _json("baseline.json")["counts"]["event_records"] == 330
    assert len(corrections) == 5
    assert len({r["Order ID"] for r in corrections}) == 5


def test_rework_flags_are_not_correction_occurrences():
    assert sum(r["Rework Y/N"] == "Y" for r in _rows("event_log.csv")) == 10


def _wnf003_rows():
    """Keep all original child-load and correction records in the hand check."""
    return [r for r in _rows("event_log.csv") if r["Order ID"] == "WNF-003"]


def _last_load_processing(activity):
    """Apply only the declared case-specific last-start/last-end processing span."""
    loads = [r for r in _wnf003_rows() if r["Activity Name"] == activity]
    return max(_times(loads, "Work End (elapsed min)")) - max(
        _times(loads, "Work Start (elapsed min)")
    )


@pytest.mark.parametrize(("activity", "expected"), [("Wash", "30.0"), ("Dry", "51.5")])
def test_wnf003_parallel_load_processing(activity, expected):
    loads = [r for r in _wnf003_rows() if r["Activity Name"] == activity]
    assert len(loads) == 2
    assert _last_load_processing(activity) == Decimal(expected)


def test_wnf003_failed_packaging_is_outside_va():
    packaging = next(r for r in _wnf003_rows() if r["Activity Name"] == "Fold and package")
    notification = next(
        r for r in _wnf003_rows() if r["Activity Name"] == "Send readiness notification"
    )
    va = (
        _last_load_processing("Wash")
        + _last_load_processing("Dry")
        + Decimal(notification["P/T (min)"])
    )
    assert packaging["Rework Y/N"] == "Y"
    assert va == Decimal(_json("baseline.json")["wnf003"]["va"]) == Decimal("82.7")


def test_wnf003_partition_and_prepared_va():
    expected = _json("baseline.json")["wnf003"]
    summary = next(r for r in _rows("order_summary.csv") if r["Order ID"] == "WNF-003")
    assert Decimal(summary["VA time (min)"]) == Decimal(expected["va"])
    assert Decimal(expected["pt"]) + Decimal(expected["wt"]) + Decimal(expected["st"]) == Decimal(
        expected["lead"]
    )


@pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
def test_existing_public_pce_on_pinned_explicit_totals(frame_factory):
    baseline = _json("baseline.json")
    lead = Decimal(baseline["minutes"]["total_lead"])
    va = Decimal(baseline["minutes"]["total_va"])
    result = process_cycle_efficiency(
        frame_factory({"lead": [float(lead)], "va": [float(va)]}),
        lead_time_column="lead",
        value_add_time_column="va",
    )
    assert result.values[0] == pytest.approx(float(100 * va / lead), abs=1e-12)
