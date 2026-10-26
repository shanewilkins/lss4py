"""Installed FLO/LSS4PY journey using only public operations and independent fixtures."""

import hashlib
import json
import os
import sys
from importlib import import_module, metadata
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import polars as pl
import pytest

import lss4py
from lss4py import ValidationError, describe, lead_time, load_event_log
from lss4py.domain import AssumptionNote
from lss4py.integration import EvidenceManifest, MetricAnnotation, ProcessProjection, SourceEvidence

ROOT = Path(__file__).parent / "fixtures"
MAPPING = {"I": "intake", "R": "review", "A": "approval", "C": "close"}


def public_process(source):
    """Obtain validated IR and its portable export through supported FLO facade operations."""
    flo = import_module("flo")
    assert flo.__file__ is not None
    assert Path(flo.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    exported = flo.export(source)
    validated = flo.validate(source)
    assert exported.ok, exported.diagnostics
    assert validated.ok, validated.diagnostics
    assert metadata.version("flo-lang") == "0.4.2"
    return validated.value, json.loads(exported.value)


def study(source_path, *, payload=None):
    """Prepare a declared complete-case cohort and capture the resulting evidence."""
    source = (ROOT / "baseline.flo").read_text()
    ir, export = public_process(source)
    projection = ProcessProjection.from_flo_export(
        export if payload is None else payload,
        source="intake-system",
        model_revision="intake-v1",
        step_mapping=MAPPING,
    )
    events = load_event_log(
        source_path,
        case_id_column="case",
        step_id_column="activity",
        started_at_column="start",
        completed_at_column="end",
    ).to_polars()
    # Resolve every observation before cohort selection: invalid excluded rows cannot disappear.
    steps = [projection.resolve_activity(value) for value in events["step_id"].to_list()]
    events = events.with_columns(pl.Series("step_id", steps))
    selected, included, exclusions = select_cohort(events)
    lead = lead_time(selected, process_model=projection.to_process_model(), unit="hours")
    lead.provenance.warnings.append(
        AssumptionNote(
            "INCOMPLETE_CASES_EXCLUDED",
            "Excluded 003: missing declared close observation",
            "warning",
        )
    )
    lead.provenance.parameters["cohort_selection"] = "Require intake and close observations"
    durations = selected.with_columns(
        (
            (pl.col("completed_at") - pl.col("started_at")).dt.total_microseconds() / 3_600_000_000
        ).alias("activity_hours")
    )
    summaries = describe(durations, column="activity_hours", group_by="step_id", unit="hours")
    results = {
        "lead": lead,
        "summary": describe(pl.DataFrame({"hours": lead.values}), column="hours", unit="hours"),
    }
    annotations = []
    for summary in summaries:
        step = summary.group_keys["step_id"]
        results[f"step:{step}"] = summary
        annotations.append(MetricAnnotation(f"step:{step}", step))
    versions = {
        name: metadata.version(name)
        for name in (
            "flo-lang",
            "lss4py",
            "numpy",
            "scipy",
            "polars",
            "narwhals",
            "matplotlib",
            "seaborn",
        )
    }
    manifest = EvidenceManifest.create(
        process=projection,
        sources=[
            SourceEvidence(
                "observations.csv", hashlib.sha256(source_path.read_bytes()).hexdigest()
            ),
            SourceEvidence(
                "baseline.flo", hashlib.sha256((ROOT / "baseline.flo").read_bytes()).hexdigest()
            ),
        ],
        cohort="September cases with observed intake and close; first source occurrence order",
        included_case_ids=included,
        exclusions=exclusions,
        timezone_policy="Naive source timestamps; no timezone inferred",
        observation_order=(
            "First case occurrence; elapsed boundaries use earliest start/latest completion"
        ),
        software_versions=versions,
        results=results,
        annotations=annotations,
    )
    return ir, manifest


def select_cohort(events):
    """Explicit analyst selection; retain a reason for every omitted case."""
    included, exclusions = [], []
    for case in events["case_id"].unique(maintain_order=True).to_list():
        steps = set(events.filter(pl.col("case_id") == case)["step_id"].to_list())
        if {"intake", "close"}.issubset(steps):
            included.append(case)
        else:
            exclusions.append({"case_id": case, "reason": "Missing declared close observation"})
    return events.filter(pl.col("case_id").is_in(included)), included, exclusions


def test_public_export_matches_contract_fixture():
    """The released producer must still emit the frozen supported projection."""
    _, payload = public_process((ROOT / "baseline.flo").read_text())
    assert payload == json.loads((ROOT / "process-export.json").read_text())


def test_installed_baseline_to_evidence_and_artifacts(tmp_path, monkeypatch):
    """Real files cross both installed packages and produce faithful, legible artifacts."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib.testing.compare import compare_images

    from lss4py.reporting.visualization import plot_timing

    expected = json.loads((ROOT / "expected.json").read_text())
    ir, manifest = study(ROOT / "observations.csv")
    output = Path(os.environ.get("LSS4PY_E2E_ARTIFACTS", str(tmp_path)))
    output.mkdir(parents=True, exist_ok=True)
    (output / "observations.csv").write_bytes((ROOT / "observations.csv").read_bytes())
    (output / "baseline.flo").write_bytes((ROOT / "baseline.flo").read_bytes())
    saved = output / "evidence.json"
    saved.write_text(manifest.to_json())
    restored = EvidenceManifest.from_json(saved.read_text())
    restored.verify_sources(
        {name: (output / name).read_bytes() for name in ("observations.csv", "baseline.flo")}
    )
    assert restored.to_dict() == manifest.to_dict()
    evidence = restored.to_dict()["evidence"]
    assert evidence["included_case_ids"] == expected["case_ids"]
    assert evidence["exclusions"] == expected["excluded"]
    assert evidence["results"]["lead"]["values"] == expected["lead_hours"]
    assert evidence["results"]["summary"]["mean"] == expected["mean_lead_hours"]
    for annotation in restored.observed_annotations():
        assert annotation["value"] == pytest.approx(
            expected["mean_activity_hours"][annotation["step_id"]]
        )
        assert annotation["unit"] == "hours"
        assert annotation["origin"] == expected["annotation_origin"]
    (output / "observed-annotations.json").write_text(
        json.dumps(restored.observed_annotations(), indent=2)
    )
    # FLO retains modeled annotations. Observed evidence is a separate artifact, not an overlay.
    renderer = import_module("flo.render")
    artifact = renderer.render_artifact(ir, options={"diagram": "value_stream"})
    assert (
        artifact.content
        == renderer.render_artifact(ir, options={"diagram": "value_stream"}).content
    )
    (output / "modeled-value-stream.svg").write_text(artifact.content)
    assert "CT 20 min" in artifact.content
    assert 'data-flow-kind="information"' in artifact.content
    assert 'data-flow-kind="material"' in artifact.content
    assert artifact.metadata["partial"] is False
    svg = ET.fromstring(artifact.content)
    assert svg.attrib["data-flo-diagram"] == "value_stream"
    assert "Observed duration" not in artifact.content

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Persisted-evidence rendering attempted analysis")

    for name in ("lead_time", "describe", "capability_indices"):
        monkeypatch.setattr(lss4py, name, forbidden)
    monkeypatch.setattr(sns, "lineplot", forbidden)
    monkeypatch.setattr(sns, "regplot", forbidden)
    with matplotlib.rc_context({"font.family": "DejaVu Sans", "svg.fonttype": "none"}):
        fig, ax = plt.subplots(figsize=(6.4, 4.8), layout="constrained")
        try:
            timing = restored.restore_timing("lead")
            before = timing.to_dict()
            assert plot_timing(timing, ax=ax) is ax
            assert np.asarray(ax.lines[0].get_ydata()).tolist() == expected["lead_hours"]
            assert [label.get_text() for label in ax.get_xticklabels()] == expected["case_ids"]
            assert timing.to_dict() == before
            fig.canvas.draw()
            assert_labels_visible(fig, ax)
            # Freeze Agg's measured layout so SVG/PNG export cannot move text between backends.
            fig.set_layout_engine(None)
            fig.savefig(output / "observed-lead-time.svg")
            fig.savefig(output / "observed-lead-time.png", dpi=100)
            assert (
                "Excluded 003: missing declared close observation"
                in (output / "observed-lead-time.svg").read_text()
            )
            assert (
                compare_images(
                    str(ROOT / "observed-lead-time.png"),
                    str(output / "observed-lead-time.png"),
                    tol=0.5,
                )
                is None
            )
        finally:
            plt.close(fig)


def assert_labels_visible(fig, ax):
    """Use actual text bounds to catch clipped labels and missing-data notices."""
    bounds = fig.bbox
    for text in [ax.title, ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *ax.texts]:
        extent = text.get_window_extent(fig.canvas.get_renderer())
        assert extent.x0 >= bounds.x0 and extent.y0 >= bounds.y0
        assert extent.x1 <= bounds.x1 and extent.y1 <= bounds.y1


@pytest.mark.parametrize("failure", ["unmapped-excluded-case", "unknown-edge", "negative-duration"])
def test_invalid_evidence_cannot_emit_a_successful_study(tmp_path, failure):
    """Corrupt evidence fails before persistence or rendering can imply success."""
    contents = (ROOT / "observations.csv").read_text()
    payload = json.loads((ROOT / "process-export.json").read_text())
    if failure == "unmapped-excluded-case":
        contents = contents.replace("003,I", "003,UNKNOWN")
    elif failure == "negative-duration":
        contents = contents.replace("2026-09-02T11:00:00", "2026-09-02T09:00:00")
    else:
        payload["edges"][0]["target"] = "unknown"
    source = tmp_path / "invalid.csv"
    source.write_text(contents)
    from lss4py import AdapterError

    with pytest.raises((ValidationError, AdapterError)):
        study(source, payload=payload)
    assert not (tmp_path / "success.json").exists()
