"""Catalog-integrity regressions for provenance, licensing, paths, and tolerances."""

import hashlib
import json
from shutil import copytree

import pytest

from tests.reference_catalog import ROOT, load_catalog


@pytest.fixture
def copied_catalog(tmp_path):
    """Isolate intentional corruption tests from the checked-in evidence."""
    root = tmp_path / "catalog"
    copytree(ROOT, root)
    return root


def _write_manifest(root, manifest):
    """Save a modified manifest for a negative governance test."""
    (root / "manifest.json").write_text(json.dumps(manifest))


def _manifest(root):
    """Read the isolated manifest without applying validation."""
    return json.loads((root / "manifest.json").read_text())


def test_catalog_has_certified_and_independent_cases_for_supported_methods():
    entries = load_catalog()
    assert {entry["metadata"]["source"]["kind"] for entry in entries} == {
        "published_certified",
        "independently_derived",
        "r_sixsigma",
    }
    supported = [
        entry for entry in entries if entry["metadata"].get("validation_status") != "reference_only"
    ]
    assert {method for entry in supported for method in entry["metadata"]["intended_analyses"]} == {
        "describe",
        "lead_time",
        "wait_time",
        "process_cycle_efficiency",
        "takt_time",
        "created_to_booked_yield",
        "booked_to_completed_yield",
        "rolled_yield",
    }
    assert all(entry["metadata"]["purpose"] == "test_fixture" for entry in entries)
    nist = next(entry for entry in entries if entry["metadata"]["id"] == "nist-numacc1")
    assert nist["inputs"]["columns"]["y"] == [10000001, 10000003, 10000002]
    assert nist["expected"][0]["tolerance"] == {"absolute": 0.0, "relative": 0.0}


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("version", "invalid", "Dataset version"),
        ("purpose", "production_evidence", "Unknown dataset purpose"),
        ("intended_analyses", ["unimplemented"], "Intended analyses mismatch"),
        ("semantic_differences", "none", "Semantic differences"),
    ],
)
def test_catalog_rejects_invalid_metadata(copied_catalog, field, value, message):
    manifest = _manifest(copied_catalog)
    manifest["datasets"][0][field] = value
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match=message):
        load_catalog(copied_catalog)


@pytest.mark.parametrize("field", ["author", "citation", "version", "accessed_on", "derivation"])
def test_catalog_requires_source_provenance(copied_catalog, field):
    manifest = _manifest(copied_catalog)
    manifest["datasets"][0]["source"][field] = ""
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match="Missing source"):
        load_catalog(copied_catalog)


@pytest.mark.parametrize("field", ["identifier", "attribution", "redistribution", "notice"])
def test_catalog_requires_redistribution_evidence(copied_catalog, field):
    manifest = _manifest(copied_catalog)
    manifest["datasets"][0]["license"][field] = ""
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match="Missing license"):
        load_catalog(copied_catalog)


def test_catalog_rejects_unapproved_redistribution(copied_catalog):
    manifest = _manifest(copied_catalog)
    manifest["datasets"][0]["license"]["redistribution"] = "unknown"
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match="Redistribution is not permitted"):
        load_catalog(copied_catalog)


@pytest.mark.parametrize("artifact", ["inputs", "expected", "invalid"])
def test_catalog_detects_tampered_artifacts(copied_catalog, artifact):
    entry = _manifest(copied_catalog)["datasets"][0]
    path = copied_catalog / entry["artifacts"][artifact]["path"]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_catalog(copied_catalog)


def test_catalog_rejects_escaping_paths(copied_catalog):
    manifest = _manifest(copied_catalog)
    manifest["datasets"][0]["artifacts"]["inputs"]["path"] = "../external.json"
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match="escapes the catalog"):
        load_catalog(copied_catalog)


def test_catalog_rejects_duplicate_ids(copied_catalog):
    manifest = _manifest(copied_catalog)
    manifest["datasets"][1]["id"] = manifest["datasets"][0]["id"]
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match="unique"):
        load_catalog(copied_catalog)


def test_catalog_rejects_unknown_schema_version(copied_catalog):
    manifest = _manifest(copied_catalog)
    manifest["schema_version"] = "99.0"
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match="Unsupported catalog schema"):
        load_catalog(copied_catalog)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"tolerance": {"absolute": -1, "relative": 0}}, "Invalid tolerance"),
        ({"tolerance": {"absolute": True, "relative": 0}}, "Invalid tolerance"),
        ({"tolerance": {"absolute": float("inf"), "relative": 0}}, "Invalid tolerance"),
        ({"expected": {"mean": float("nan")}}, "Nonfinite expected"),
        ({"basis": ""}, "independent basis"),
        ({"tolerance_reason": ""}, "Tolerance justification"),
        ({"input_kind": "scalar"}, "Input kind does not match"),
    ],
)
def test_catalog_rejects_invalid_expectations_even_with_new_checksum(
    copied_catalog, change, message
):
    manifest = _manifest(copied_catalog)
    artifact = manifest["datasets"][0]["artifacts"]["expected"]
    path = copied_catalog / artifact["path"]
    cases = json.loads(path.read_text())
    cases[0].update(change)
    path.write_text(json.dumps(cases))
    artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match=message):
        load_catalog(copied_catalog)


def test_catalog_checks_data_schema_even_with_new_checksum(copied_catalog):
    manifest = _manifest(copied_catalog)
    artifact = manifest["datasets"][0]["artifacts"]["inputs"]
    path = copied_catalog / artifact["path"]
    path.write_text(json.dumps({"columns": {"y": [True, 2, 3]}}))
    artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match="Invalid input value"):
        load_catalog(copied_catalog)


@pytest.mark.parametrize("version", [None, "0.11.0", "future"])
def test_sixsigma_claim_requires_the_governed_package_version(copied_catalog, version):
    manifest = _manifest(copied_catalog)
    source = manifest["datasets"][0]["source"]
    source.update(kind="r_sixsigma", package="SixSigma", package_version=version)
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match=r"SixSigma 0\.11\.1"):
        load_catalog(copied_catalog)


def test_sixsigma_claim_requires_generation_evidence(copied_catalog):
    manifest = _manifest(copied_catalog)
    source = manifest["datasets"][0]["source"]
    source.update(kind="r_sixsigma", package="SixSigma", package_version="0.11.1")
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match="Missing R generation evidence"):
        load_catalog(copied_catalog)


def test_catalog_accounts_for_every_json_artifact():
    entries = load_catalog()
    paths = {
        ROOT / artifact["path"]
        for entry in entries
        for artifact in entry["metadata"]["artifacts"].values()
        if artifact["path"].endswith(".json")
    }
    assert paths == set(ROOT.rglob("*.json")) - {ROOT / "manifest.json"}


def test_catalog_requires_all_artifact_roles(copied_catalog):
    manifest = _manifest(copied_catalog)
    manifest["datasets"][0]["artifacts"].pop("invalid")
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match="Missing fixture artifacts"):
        load_catalog(copied_catalog)


@pytest.mark.parametrize("missing", ["generator", "invalid-input"])
def test_sixsigma_requires_generator_and_error_evidence(copied_catalog, missing):
    manifest = _manifest(copied_catalog)
    entry = manifest["datasets"][0]
    entry["source"].update(
        kind="r_sixsigma",
        package="SixSigma",
        package_version="0.11.1",
        r_version="4.4.0",
        generated_at="2026-10-09T00:00:00Z",
        command="Rscript generate.R",
    )
    if missing == "generator":
        expected = "checksummed generator"
    else:
        # The payload is never accepted or executed; source validation fails first.
        entry["artifacts"]["generator"] = entry["artifacts"]["inputs"].copy()
        expected = "invalid-input cases"
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match=expected):
        load_catalog(copied_catalog)


def test_r_snapshot_is_reference_only_and_preserves_observed_semantics():
    entry = next(
        item for item in load_catalog() if item["metadata"]["source"]["kind"] == "r_sixsigma"
    )
    assert entry["metadata"]["validation_status"] == "reference_only"
    assert entry["metadata"]["source"]["package_version"] == "0.11.1"
    assert {case["method"] for case in entry["expected"]} == {
        "ss.ca.cp",
        "ss.ca.cpk",
        "ss.ca.z",
        "ss.ca.yield",
    }
    assert len(entry["expected"]) == 17 and len(entry["invalid"]) == 6


def test_r_invalid_inputs_preserve_observed_semantics():
    entry = next(
        item for item in load_catalog() if item["metadata"]["source"]["kind"] == "r_sixsigma"
    )
    cases = {case["id"]: case["expected"] for case in entry["invalid"]}
    assert cases["cp-no-limits"]["status"] == "error"
    assert cases["yield-zero-opportunities"]["status"] == "returned"
    assert cases["yield-zero-opportunities"]["value"][0]["DPMO"] == "Inf"
    assert cases["yield-length-mismatch"]["warnings"] == [
        "longer object length is not a multiple of shorter object length",
    ]


@pytest.mark.parametrize("mutation", ["runtime", "status"])
def test_r_runtime_evidence_cannot_be_mislabeled(copied_catalog, mutation):
    manifest = _manifest(copied_catalog)
    entry = next(e for e in manifest["datasets"] if e["id"] == "r-sixsigma-baseline")
    if mutation == "runtime":
        artifact = entry["artifacts"]["provenance"]
        path = copied_catalog / artifact["path"]
        provenance = json.loads(path.read_text())
        provenance["package_version"] = "0.11.0"
        path.write_text(json.dumps(provenance))
        artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        message = "R provenance mismatch"
    else:
        entry["validation_status"] = "python_parity_passed"
        message = "reference_only"
    _write_manifest(copied_catalog, manifest)
    with pytest.raises(ValueError, match=message):
        load_catalog(copied_catalog)
