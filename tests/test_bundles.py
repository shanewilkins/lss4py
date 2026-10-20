"""Audited bundle round trips, legacy context upgrades and independent validation."""

import json
import subprocess
import sys
from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import lss4py
from lss4py import (
    AnalysisBundle,
    InputReference,
    Specification,
    ValidationError,
    capability_indices,
    created_to_booked_yield,
    describe,
    lead_time,
    process_yield,
)
from lss4py._bundle_schema import bundle_fingerprint
from lss4py.domain import AnalyticalResult, TimingResult

RAW = (
    b"x,hours,created,booked,start,end,defects,rework\n"
    b"1,1,1,1,2026-10-01T08:00:00,2026-10-01T09:00:00,1,0\n"
    b"2,2,1,1,2026-10-01T08:00:00,2026-10-01T09:00:00,0,1\n"
    b"3,3,1,0,2026-10-01T08:00:00,2026-10-01T09:00:00,1,0\n"
)


def software():
    """Record actual local software context for these original synthetic calculations."""
    versions = {}
    for name in ("lss4py", "numpy", "scipy", "narwhals", "pandas", "polars", "pyarrow"):
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            pass
    return versions


def results(frame_factory):
    """Compute every current analytical result family from explicit fixture inputs."""
    spec = Specification("X", "mm", "lower", lsl=0, usl=6)
    data = frame_factory(
        {
            "x": [1.0, 2.0, 3.0],
            "hours": [1.0, 2.0, 3.0],
            "created": [1, 1, 1],
            "booked": [1, 1, 0],
            "start": ["2026-10-01T08:00:00"] * 3,
            "end": ["2026-10-01T09:00:00"] * 3,
            "defects": [1, 0, 1],
            "rework": [0, 1, 0],
        }
    )
    return {
        "timing": lead_time(data, start_column="start", end_column="end", unit="hours"),
        "funnel": created_to_booked_yield(data, created_column="created", booked_column="booked"),
        "defects": process_yield(data, rework_column="rework", opportunities=20, units=5),
        "summary": describe(data, column="x", unit="mm"),
        "capability": capability_indices(data, column="x", specification=spec, ci=True),
    }, spec


def capture(items, spec=None):
    """Bind independently supplied source evidence and specification context explicitly."""
    return AnalysisBundle.capture(
        "Synthetic analysis",
        results=items,
        inputs={
            "observations": InputReference.from_bytes(
                "observations.csv",
                RAW,
                selection="all three original synthetic observations",
                media_type="text/csv",
            )
        },
        result_inputs={name: ["observations"] for name in items},
        cohort_definition="Original synthetic fixture cohort",
        software_versions=software(),
        specifications={} if spec is None else {"ctq": spec},
        result_specifications={} if spec is None else {"capability": ["ctq"]},
        context={
            "observation_order": "source row order",
            "timezone_policy": "naive wall time",
            "exclusions": [],
        },
    )


@pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
def test_all_result_families_roundtrip(frame_factory, monkeypatch):
    """Restore concrete models and full payloads after disabling every source calculation."""
    items, spec = results(frame_factory)
    bundle = capture(items, spec)
    saved = bundle.to_json()

    def fail(*_args, **_kwargs):
        raise AssertionError("Bundle restoration executed an analytical kernel")

    for name in (
        "lead_time",
        "describe",
        "capability_indices",
        "process_yield",
        "created_to_booked_yield",
    ):
        monkeypatch.setattr(lss4py, name, fail)
    restored = AnalysisBundle.from_json(saved)
    assert restored.to_json() == saved
    assert restored.audited
    restored.verify_inputs({"observations": RAW})
    for name, original in items.items():
        result = restored.get_result(name)
        assert type(result) is type(original)
        assert result.to_dict() == original.to_dict()
        assert AnalyticalResult.from_dict(original.to_dict()).to_dict() == original.to_dict()


@pytest.fixture
def audited_payload():
    """Use an original three-row summary as one complete portable audit snapshot."""
    return capture(
        {"summary": describe(pl.DataFrame({"x": [1.0, 2.0, 3.0]}), column="x")}
    ).to_dict()


def rehash(payload):
    """Allow semantic-corruption tests to get beyond the accidental-change checksum."""
    payload["sha256"] = bundle_fingerprint({k: v for k, v in payload.items() if k != "sha256"})
    return payload


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b.update(bundle_version="9.0"),
        lambda b: b.update(unexpected=True),
        lambda b: b["results"]["summary"].update(schema_version="9.0"),
        lambda b: b["results"]["summary"].update(input_ids=["missing"]),
        lambda b: b["results"]["summary"].update(input_ids=[]),
        lambda b: b["results"]["summary"].update(input_ids=["observations", "observations"]),
        lambda b: b["results"]["summary"].update(specification_ids=["missing"]),
        lambda b: b["results"]["summary"]["result"].update(result_type="InventedResult"),
        lambda b: b["results"]["summary"]["result"].update(count=99),
        lambda b: b["results"]["summary"]["result"]["provenance"].update(package_version="9"),
        lambda b: b["results"]["summary"]["result"]["provenance"].update(method="lead_time"),
        lambda b: b["software_versions"].update(numpy="other"),
        lambda b: b["inputs"]["observations"].update(sha256="bad"),
        lambda b: b["inputs"]["observations"].update(selection=""),
        lambda b: b.update(cohort_definition=None),
        lambda b: b["results"]["summary"]["result"].update(unexpected=1),
    ],
)
def test_semantic_corruption_rejected_even_when_rehashed(audited_payload, change):
    """A new checksum cannot make an incompatible or contradictory typed snapshot valid."""
    change(audited_payload)
    with pytest.raises(ValidationError):
        AnalysisBundle.from_dict(rehash(audited_payload))


def test_snapshot_hash_and_source_hashes(audited_payload):
    """Detect edits to saved data and independently verify the input bytes without I/O."""
    changed = deepcopy(audited_payload)
    changed["results"]["summary"]["result"]["mean"] = 99
    with pytest.raises(ValidationError, match="fingerprint"):
        AnalysisBundle.from_dict(changed)
    bundle = AnalysisBundle.from_dict(audited_payload)
    with pytest.raises(ValidationError, match="Missing input"):
        bundle.verify_inputs({})
    with pytest.raises(ValidationError, match="fingerprint"):
        bundle.verify_inputs({"observations": RAW + b"4\n"})
    with pytest.raises(ValidationError, match="Unknown result"):
        bundle.get_result("missing")


def test_capture_and_exports_are_detached():
    """Caller edits cannot alter already captured results, context, or source declarations."""
    original = describe(pl.DataFrame({"x": [1.0, 2.0, 3.0]}), column="x")
    bundle = capture({"summary": original})
    saved = bundle.to_json()
    original.mean = 99
    original.provenance.parameters["column"] = "other"
    exported = bundle.to_dict()
    exported["context"]["exclusions"].append("edit")
    restored = bundle.get_result("summary")
    restored.mean = 123
    assert bundle.to_json() == saved


def test_legacy_results_restore_and_upgrade_explicitly():
    """Legacy v1 loads its actual results; migration cannot invent missing source identity."""
    original = describe(pl.DataFrame({"x": [1.0, 2.0, 3.0]}), column="x")
    legacy = AnalysisBundle("Legacy", [original], specification_metadata={"note": "legacy CTQ"})
    restored = AnalysisBundle.from_json(legacy.to_json())
    assert restored.results[0].to_dict() == original.to_dict()
    assert restored.bundle_version == "1.0" and not restored.audited
    with pytest.raises(ValidationError, match="Legacy"):
        restored.verify_inputs({})
    upgraded = restored.with_audit_context(
        inputs={"raw": InputReference.from_bytes("raw.csv", RAW, selection="all rows")},
        result_inputs={"result-0": ["raw"]},
        cohort_definition="Explicit recovered cohort",
        software_versions=software(),
        context={"legacy_specification_metadata": restored.specification_metadata},
    )
    assert upgraded.audited
    assert upgraded.metadata["migrated_from_bundle_version"] == "1.0"
    upgraded.verify_inputs({"raw": RAW})
    with pytest.raises(ValidationError, match="already"):
        upgraded.with_audit_context()


def test_mixed_key_identity_and_intervals_restore():
    """Arrays retain finite scalar key types; intervals and bucket outputs regain tuples."""
    _, spec = results(pl.DataFrame)
    items, _ = results(pl.DataFrame)
    items["timing"].keys = np.array(["1", 2, True], dtype=object)
    bundle = capture(items, spec)
    timing = bundle.get_result("timing")
    assert timing.keys.tolist() == ["1", 2, True]
    assert [type(k) for k in timing.keys] == [str, int, bool]
    assert isinstance(bundle.get_result("capability").cp_confidence_interval, tuple)
    assert isinstance(bundle.get_result("defects").bucket_defects, tuple)
    with pytest.raises(ValidationError, match="differs"):
        TimingResult.from_dict(items["summary"].to_dict())


def test_standalone_validator_has_no_analytical_runtime(audited_payload, tmp_path):
    """Execute the packaged validator with site-packages disabled in a fresh process."""
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(audited_payload))
    script = Path(lss4py.__file__).with_name("_bundle_schema.py")
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(script), str(bundle)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == {
        "valid": True,
        "bundle_version": "2.0",
        "audited": True,
        "results": 1,
    }
    bundle.write_text('{"bundle_version": "9.0"}')
    failed = subprocess.run(
        [sys.executable, "-I", "-S", str(script), str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 1
    assert "Unsupported bundle" in failed.stderr


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), object()])
def test_nonportable_context_is_rejected(audited_payload, bad):
    """Reject nonstandard JSON numbers and arbitrary runtime objects before snapshotting."""
    audited_payload["context"]["bad"] = bad
    with pytest.raises(ValidationError):
        AnalysisBundle.from_dict(audited_payload)


def test_duplicate_json_members_are_rejected(audited_payload):
    """Never silently keep the last of conflicting schema or result fields."""
    text = json.dumps(audited_payload)
    text = text.replace(
        '"bundle_version": "2.0"', '"bundle_version": "2.0", "bundle_version": "1.0"'
    )
    with pytest.raises(ValidationError, match="Duplicate JSON"):
        AnalysisBundle.from_json(text)


def test_checked_in_legacy_fixture():
    """Read a fixed original v1 wire artifact rather than deriving it from the new exporter."""
    path = Path(__file__).parent / "fixtures" / "bundles" / "legacy-v1.json"
    payload = json.loads(path.read_text())
    restored = AnalysisBundle.from_dict(payload)
    assert restored.to_dict() == payload
    assert isinstance(restored.results[0], TimingResult)
    assert restored.results[0].values.tolist() == [1, 2, 3]
    assert restored.results[0].keys is not None
    assert restored.results[0].keys.tolist() == ["a", "b", "c"]
    assert restored.package_version == "0.2.0"
    assert not restored.audited


def test_public_validator_uses_domain_errors(audited_payload):
    """The package API wraps the standalone validator's portable errors consistently."""
    assert lss4py.validate_bundle(audited_payload) == audited_payload
    audited_payload["bundle_version"] = "other"
    with pytest.raises(ValidationError, match="Unsupported"):
        lss4py.validate_bundle(audited_payload)


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(values=[[1, 2]]),
        lambda r: r.update(keys=["only-one"]),
        lambda r: r.update(keys=["a", "a", "b"]),
        lambda r: r.update(unit="unknown"),
        lambda r: r["provenance"].pop("warnings"),
        lambda r: r["provenance"].update(created_at="invalid"),
    ],
)
def test_timing_schema_corruption(change):
    """Reject broken timing shapes, identifiers, units and provenance on reconstruction."""
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "bundles" / "legacy-v1.json").read_text()
    )
    change(payload["results"][0])
    with pytest.raises(ValidationError):
        AnalysisBundle.from_dict(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("dpmo", 99),
        ("first_time_yield", 2),
        ("defect_count", 100),
        ("bucket_rework", []),
        ("units", 0),
        ("defects_per_unit", None),
        ("schema_version", "2.0"),
    ],
)
def test_defect_count_semantic_corruption(field, value):
    """Rehashed result estimates must still agree with their own explicit count evidence."""
    items, spec = results(pl.DataFrame)
    payload = capture(items, spec).to_dict()
    payload["results"]["defects"]["result"][field] = value
    with pytest.raises(ValidationError):
        AnalysisBundle.from_dict(rehash(payload))


@pytest.mark.parametrize(
    "field,value",
    [
        ("cp_confidence_interval", [2, 1]),
        ("confidence_level", 2),
        ("unit", "cm"),
        ("lsl", -1),
        ("missing", 100),
    ],
)
def test_capability_context_corruption(field, value):
    """Capability intervals, sample counts, units and limits remain linked to the CTQ."""
    items, spec = results(pl.DataFrame)
    payload = capture(items, spec).to_dict()
    payload["results"]["capability"]["result"][field] = value
    with pytest.raises(ValidationError):
        AnalysisBundle.from_dict(rehash(payload))
