"""Independent cross-package identity, semantics and persisted-evidence contracts."""

import hashlib
import json
from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import lss4py
from lss4py import ValidationError, describe, lead_time
from lss4py.integration import EvidenceManifest, MetricAnnotation, ProcessProjection, SourceEvidence

ROOT = Path(__file__).parent / "fixtures" / "ecosystem"
MAPPING = {"I": "intake", "R": "review", "A": "approval", "C": "close"}


@pytest.fixture
def projection():
    """Use a frozen public export from genuine FLO 0.4.2, without importing FLO."""
    return ProcessProjection.from_flo_export(
        json.loads((ROOT / "legacy-0.4.2/process-export.json").read_text()),
        source="intake-system",
        model_revision="intake-v1",
        step_mapping=MAPPING,
        flo_version="0.4.2",
    )


@pytest.fixture
def manifest(projection):
    """Capture simple independently known timing and step-level evidence."""
    frame = pl.DataFrame({"start": ["2026-09-01T08:00:00"], "end": ["2026-09-01T10:00:00"]})
    timing = lead_time(frame, start_column="start", end_column="end")
    timing.keys = np.array(["001"])
    summary = describe(
        pl.DataFrame({"step_id": ["review"], "hours": [2.0]}),
        column="hours",
        group_by="step_id",
        unit="hours",
    )[0]
    return EvidenceManifest.create(
        process=projection,
        sources=[SourceEvidence("observations.csv", hashlib.sha256(b"original").hexdigest())],
        cohort="Completed September cases",
        included_case_ids=["001"],
        exclusions=[{"case_id": "002", "reason": "Missing completion"}],
        timezone_policy="Naive source timestamps; no timezone inferred",
        observation_order="First occurrence in source CSV",
        software_versions={"flo-lang": "0.4.2", "lss4py": lss4py.__version__},
        results={"lead": timing, "review": summary},
        annotations=[MetricAnnotation("review", "review")],
    )


def rehash(envelope):
    """Update checksum deliberately so tests exercise semantic validation, not just hashes."""
    canonical = json.dumps(envelope["evidence"], sort_keys=True, separators=(",", ":"))
    envelope["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return json.dumps(envelope)


def test_projection_preserves_identity_topology_and_modeled_values(projection):
    """Known source identities and parallel/rework edges survive the projection."""
    model = projection.to_process_model()
    assert projection.resolve_activity("R") == "review"
    assert [step.id for step in model.steps] == [
        "start",
        "intake",
        "split",
        "review",
        "approval",
        "join",
        "close",
        "end",
    ]
    assert model.steps[1].metadata["flo"]["metadata"]["cycle_time"] == {"value": 20, "unit": "min"}
    assert model.metadata["model_revision"] == "intake-v1"
    assert model.metadata["projection_sha256"] == projection.digest


def test_projection_preserves_parallel_rework_and_handoff(projection):
    """Parallelism, rework and handoff remain explicit and independently inspectable."""
    model = projection.to_process_model()
    assert [edge.kind for edge in model.edges].count("parallel_split") == 2
    assert [edge.kind for edge in model.edges].count("parallel_join") == 2
    rework = next(edge for edge in model.edges if edge.kind == "rework")
    assert rework.source_step_id == rework.target_step_id == "review"
    assert rework.condition == "revise"
    assert rework.metadata["flo"]["handoff"] is True


def test_names_and_node_order_do_not_determine_mapping(projection):
    """Renaming/reordering display nodes preserves explicit source-to-step identity."""
    body = projection.to_dict()
    body["export"]["nodes"].reverse()
    for node in body["export"]["nodes"]:
        node["name"] = "Identical renamed labels"
    changed = ProcessProjection(json.dumps(body))
    assert changed.resolve_activity("R") == "review"
    assert changed.resolve_activity("A") == "approval"
    assert changed.digest != projection.digest


@pytest.mark.parametrize(
    "failure",
    [
        "schema",
        "version",
        "duplicate-node",
        "unknown-edge",
        "unknown-mapping",
        "ambiguous-mapping",
        "unsupported-node",
        "subprocess",
        "route",
        "edge-type",
        "empty-revision",
    ],
)
def test_projection_rejects_unsupported_or_ambiguous_semantics(projection, failure):
    """Never guess identity or flatten an unsupported topology into a successful result."""
    body = projection.to_dict()
    mutations = {
        "schema": lambda: body.update(schema_version="99"),
        "version": lambda: body.update(flo_version="0.5.0"),
        "duplicate-node": lambda: body["export"]["nodes"].append(body["export"]["nodes"][0]),
        "unknown-edge": lambda: body["export"]["edges"][0].update(target="unknown"),
        "unknown-mapping": lambda: body["step_mapping"].update(R="unknown"),
        "ambiguous-mapping": lambda: body["step_mapping"].update(A="review"),
        "unsupported-node": lambda: body["export"]["nodes"][0].update(kind="branch"),
        "subprocess": lambda: body["export"]["nodes"][1].update(subprocess_parent="parent"),
        "route": lambda: body["export"]["edges"][0].update(route="dispatch"),
        "edge-type": lambda: body["export"]["edges"][0].update(edge_type="unknown"),
        "empty-revision": lambda: body.update(model_revision=""),
    }
    mutations[failure]()
    with pytest.raises(ValidationError):
        ProcessProjection(json.dumps(body))


def test_unmapped_observation_is_an_error(projection):
    """Display labels cannot substitute for an absent source mapping."""
    with pytest.raises(ValidationError, match="Unmapped source activity"):
        projection.resolve_activity("Review")


def test_manifest_roundtrip_preserves_full_results_and_meaning(manifest, tmp_path):
    """Saved/reloaded evidence retains methods, keys, units, exclusions and annotation identity."""
    destination = tmp_path / "evidence.json"
    destination.write_text(manifest.to_json())
    restored = EvidenceManifest.from_json(destination.read_text())
    process = manifest.to_dict()["evidence"]["process"]
    assert ProcessProjection.from_json(json.dumps(process)).to_dict() == process
    assert restored.to_dict() == manifest.to_dict()
    timing = restored.restore_timing("lead")
    assert timing.to_dict() == restored.to_dict()["evidence"]["results"]["lead"]
    assert timing.values.tolist() == [2]
    assert timing.keys is not None
    assert timing.keys.tolist() == ["001"]
    (annotation,) = restored.observed_annotations()
    assert (
        annotation["step_id"],
        annotation["origin"],
        annotation["value"],
        annotation["unit"],
    ) == ("review", "observed", 2, "hours")
    assert restored.to_dict()["evidence"]["exclusions"] == [
        {"case_id": "002", "reason": "Missing completion"}
    ]


def test_mutable_copies_cannot_change_saved_evidence(projection, manifest):
    """Caller mutation of returned models or dicts cannot invalidate fingerprints."""
    baseline = projection.to_json(), manifest.to_json()
    projection.to_dict()["step_mapping"]["R"] = "approval"
    projection.to_process_model().steps[0].name = "Changed"
    manifest.to_dict()["evidence"]["results"]["lead"]["values"][0] = 999
    manifest.restore_timing("lead").values[0] = 999
    assert (projection.to_json(), manifest.to_json()) == baseline
    with pytest.raises(FrozenInstanceError):
        manifest._json = "{}"


def test_changed_evidence_fails_fingerprint(manifest):
    """Accidental edits cannot silently retain the original evidence identity."""
    envelope = manifest.to_dict()
    envelope["evidence"]["results"]["lead"]["values"][0] = 999
    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        EvidenceManifest(json.dumps(envelope))


def test_source_snapshots_must_match_saved_fingerprints(manifest):
    """Successful reload does not excuse changed or unavailable underlying observations."""
    manifest.verify_sources({"observations.csv": b"original"})
    with pytest.raises(ValidationError, match="Source fingerprint mismatch"):
        manifest.verify_sources({"observations.csv": b"changed"})
    with pytest.raises(ValidationError, match="Missing source snapshot"):
        manifest.verify_sources({})


def test_case_reordering_and_unit_conversion_remain_explicit(
    projection, frame_factory, interval_records
):
    """Backend index labels cannot change case identity or implicitly convert hours to minutes."""
    frame = frame_factory(interval_records)
    model = projection.to_process_model()
    hours = lead_time(frame, process_model=model, unit="hours")
    minutes = lead_time(frame, process_model=model, unit="minutes")
    assert hours.keys is not None
    assert hours.keys.tolist() == ["C2", "C1"]
    assert hours.values.tolist() == [3, 2]
    assert minutes.values.tolist() == [180, 120]
    assert hours.unit == "hours"
    assert minutes.provenance.parameters["unit"] == "minutes"


@pytest.mark.parametrize(
    "failure",
    [
        "schema",
        "wrong-step",
        "unknown-result",
        "invented-field",
        "invented-origin",
        "wrong-keys",
        "duplicate-keys",
        "wrong-unit",
        "relabeled-unit",
        "nonfinite",
        "package-version",
        "flo-version",
        "bad-source-hash",
        "included-and-excluded",
        "empty-cohort",
        "extra-field",
    ],
)
def test_semantic_corruption_is_rejected_even_with_new_hash(manifest, failure):
    """Hashes supplement validation; they cannot make incompatible evidence valid."""
    envelope = manifest.to_dict()
    body = envelope["evidence"]
    mutations = {
        "schema": lambda: body.update(schema_version="99"),
        "wrong-step": lambda: body["annotations"][0].update(step_id="approval"),
        "unknown-result": lambda: body["annotations"][0].update(result_id="missing"),
        "invented-field": lambda: body["annotations"][0].update(field="median"),
        "invented-origin": lambda: body["annotations"][0].update(origin="modeled"),
        "wrong-keys": lambda: body["results"]["lead"].update(keys=["002"]),
        "duplicate-keys": lambda: body["results"]["lead"].update(
            keys=["001", "001"], values=[2, 2]
        ),
        "wrong-unit": lambda: body["results"]["lead"].update(unit="fortnights"),
        "relabeled-unit": lambda: body["results"]["lead"].update(unit="minutes"),
        "nonfinite": lambda: body["results"]["lead"].update(values=[float("inf")]),
        "package-version": lambda: body["results"]["lead"]["provenance"].update(
            package_version="99"
        ),
        "flo-version": lambda: body["software_versions"].update({"flo-lang": "99"}),
        "bad-source-hash": lambda: body["sources"][0].update(sha256="g" * 64),
        "included-and-excluded": lambda: body["exclusions"][0].update(case_id="001"),
        "empty-cohort": lambda: body.update(cohort=""),
        "extra-field": lambda: body.update(automatic_method="guess"),
    }
    mutations[failure]()
    with pytest.raises(ValidationError):
        EvidenceManifest(rehash(envelope))


def test_missing_annotation_is_unavailable_not_invented(manifest):
    """A nullable analytical estimate remains nullable through annotation export."""
    envelope = manifest.to_dict()
    envelope["evidence"]["results"]["review"]["mean"] = None
    restored = EvidenceManifest(rehash(envelope))
    assert restored.observed_annotations()[0]["value"] is None


def test_rendering_saved_evidence_does_not_compute(manifest, monkeypatch, tmp_path):
    """Disable analyses and Seaborn estimation before rendering saved results on supplied axes."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    from lss4py.reporting.visualization import plot_timing

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Rendering attempted analysis or estimation")

    for name in ("lead_time", "describe", "capability_indices"):
        monkeypatch.setattr(lss4py, name, forbidden)
    monkeypatch.setattr(sns, "lineplot", forbidden)
    monkeypatch.setattr(sns, "regplot", forbidden)
    saved = EvidenceManifest(manifest.to_json())
    result = saved.restore_timing("lead")
    snapshot = deepcopy(result.to_dict())
    fig, ax = plt.subplots(layout="constrained")
    try:
        assert plot_timing(result, ax=ax) is ax
        assert np.asarray(ax.lines[0].get_ydata()).tolist() == [2]
        assert [tick.get_text() for tick in ax.get_xticklabels()] == ["001"]
        assert ax.get_ylabel() == "Observed duration (hours)"
        assert result.to_dict() == snapshot
        fig.savefig(tmp_path / "observed.svg")
        assert "Observed duration (hours)" in (tmp_path / "observed.svg").read_text()
    finally:
        plt.close(fig)


def test_bridge_does_not_import_flo_or_rendering_packages():
    """Enforce package independence in a fresh interpreter, independent of test import order."""
    import subprocess
    import sys

    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import lss4py; import lss4py.integration; "
                "forbidden = {'flo','matplotlib','seaborn'}; "
                "assert not any(m.split('.')[0] in forbidden for m in sys.modules)"
            ),
        ],
        check=True,
    )
