"""Execute the standalone actual-book example against installed distributions."""

import json
import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import polars as pl
import pytest

from lss4py import (
    AnalysisBundle,
    DescriptiveResult,
    OrderReconstructionResult,
    TimingResult,
    ValidationError,
    YieldResult,
)
from lss4py.integration import ProcessProjection

ROOT = Path(__file__).parent / "fixtures/book-model"
WHITE_BELT = Path(__file__).parents[1] / "fixtures/white_belt"


def _command(model, source, output):
    return [
        sys.executable,
        "-I",
        str(WHITE_BELT / "flo_measure.py"),
        "--model-dir",
        str(model),
        "--source",
        str(source),
        "--output",
        str(output),
    ]


def test_installed_actual_model_and_csv_produce_restorable_evidence(tmp_path):
    """Compare every reconstructed order with the independently prepared book table."""
    output = Path(os.environ.get("LSS4PY_E2E_ARTIFACTS", str(tmp_path))) / "book"
    completed = subprocess.run(
        _command(ROOT, WHITE_BELT / "event_log.csv", output),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Cohort PCE: 13.7%" in completed.stdout
    bundle = AnalysisBundle.from_json((output / "evidence.json").read_text())
    bundle.verify_inputs({name: (output / name).read_bytes() for name in bundle.inputs})
    reconstruction = bundle.get_result("reconstruction")
    assert isinstance(reconstruction, OrderReconstructionResult)
    orders = reconstruction.to_polars().sort("Order ID")
    expected = pl.read_csv(WHITE_BELT / "order_summary.csv").sort("Order ID")
    assert orders.height == 39
    assert orders["Order ID"].to_list() == expected["Order ID"].to_list()
    for actual, reference in {
        "arrival": "Arrival (elapsed min)",
        "readiness": "Ready and notified (elapsed min)",
        "lead_time": "Operating L/T (min)",
        "processing": "Total P/T (min)",
        "waiting": "Total W/T (min)",
        "setup": "Total S/T (min)",
        "value_add": "VA time (min)",
        "correction_occurrences": "Correction occurrences",
    }.items():
        assert orders[actual].to_list() == pytest.approx(expected[reference].to_list(), abs=1e-8)
    assert orders["value_add"].sum() == pytest.approx(3535.3)
    assert orders["lead_time"].sum() == pytest.approx(25840.5)
    mean_lead = bundle.get_result("mean_lead")
    eligible_lead = bundle.get_result("eligible_lead")
    assert isinstance(mean_lead, DescriptiveResult)
    assert isinstance(eligible_lead, DescriptiveResult)
    assert mean_lead.mean == pytest.approx(662.6, abs=0.05)
    assert eligible_lead.percentiles is not None
    assert eligible_lead.percentiles["p90"] == pytest.approx(676.2)
    promise = bundle.get_result("promise")
    assert isinstance(promise, YieldResult)
    assert (promise.numerator, promise.denominator) == (6, 21)
    pce = bundle.get_result("pce")
    assert isinstance(pce, TimingResult)
    assert pce.values[0] == pytest.approx(13.7, abs=0.05)
    assert reconstruction.metadata["correction_occurrences"] == 5
    assert reconstruction.metadata["affected_orders"] == 5
    special = orders.filter(pl.col("Order ID") == "WNF-003")
    assert special["value_add"][0] == pytest.approx(82.7)
    activities = reconstruction.to_polars("activities").filter(pl.col("Order ID") == "WNF-003")
    for activity in ("Wash", "Dry"):
        assert len(activities.filter(pl.col("activity") == activity)["load_ids"][0]) == 2
    assert reconstruction.to_polars("source_records").height == 330
    projection = ProcessProjection.from_json((output / "projection.json").read_text())
    assert projection.to_dict() == bundle.context["process_projection"]
    policy = json.loads((output / "policy-derivation.json").read_text())
    assert policy == bundle.context["policy_derivation"]
    assert policy == reconstruction.metadata["policy_derivation"]
    assert policy["projection_sha256"] == projection.digest
    assert len(policy["classifications"]) == 8
    assert policy["analyst_conventions"]["parallel_activities"] == ["Wash", "Dry"]
    assert bundle.context["numeric_contract"]["unit"] == "minutes"
    assert bundle.software_versions["flo-lang"] == "0.5.0"
    assert bundle.context["producer_report"]["error_count"] == 0
    assert bundle.context["producer_report"]["warning_count"] > 0
    assert all(c["source_field"] == "value_class" for c in policy["classifications"].values())
    assert bundle.to_json() == AnalysisBundle.from_json(bundle.to_json()).to_json()
    svg = ET.fromstring((output / "modeled-value-stream.svg").read_text())
    assert svg.attrib["data-flo-diagram"] == "value_stream"
    assert list(svg.iter("{http://www.w3.org/2000/svg}text"))
    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        bundle.verify_inputs(dict.fromkeys(bundle.inputs, b"modified"))


@pytest.mark.parametrize("changed", ["washnfold.flo", "activity-mapping.json", "event_log.csv"])
def test_changed_pinned_sources_cannot_emit_success(tmp_path, changed):
    """The pinned demonstration rejects changed inputs before publishing evidence."""
    import shutil

    model = tmp_path / "model"
    shutil.copytree(ROOT, model)
    source = tmp_path / "event_log.csv"
    source.write_bytes((WHITE_BELT / "event_log.csv").read_bytes())
    target = source if changed == "event_log.csv" else model / changed
    target.write_bytes(target.read_bytes() + b"\n")
    output = tmp_path / "output"
    completed = subprocess.run(
        _command(model, source, output), check=False, capture_output=True, text=True
    )
    assert completed.returncode != 0
    assert not (output / "evidence.json").exists()
    assert not (output / "modeled-value-stream.svg").exists()
