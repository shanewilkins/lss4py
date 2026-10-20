"""Installed CSV-to-audited-bundle-to-explicit-rerun journey."""

import json
import subprocess
import sys
from importlib.metadata import version
from io import BytesIO
from pathlib import Path

import polars as pl
import pytest

import lss4py
from lss4py import (
    AnalysisBundle,
    CapabilityResult,
    InputReference,
    Specification,
    ValidationError,
    capability_indices,
    describe,
    validate_bundle,
)


def test_audited_bundle_journey(backend, fixtures, tmp_path):
    """Save typed study evidence, independently validate it, then rerun on verified bytes."""
    source = (fixtures / "measurements.csv").read_bytes()
    if backend == "pandas":
        import pandas as pd

        data = pd.read_csv(BytesIO(source))
    else:
        data = pl.read_csv(BytesIO(source))
    spec = Specification.from_json((fixtures / "specification.json").read_text())
    summary = describe(data, column="diameter", unit="mm")
    capability = capability_indices(data, column="diameter", specification=spec, ci=True)
    bundle = AnalysisBundle.capture(
        "Diameter inspection",
        results={"summary": summary, "capability": capability},
        inputs={
            "measurements": InputReference.from_bytes(
                "measurements.csv",
                source,
                selection="all source rows; missing diameter omitted by methods",
                media_type="text/csv",
            )
        },
        result_inputs={"summary": ["measurements"], "capability": ["measurements"]},
        cohort_definition="September inspection sample, source row order",
        software_versions={
            name: version(name) for name in ("lss4py", "numpy", "scipy", "narwhals", backend)
        },
        specifications={"diameter": spec},
        result_specifications={"capability": ["diameter"]},
        context={
            "observation_order": "source row order",
            "exclusions": [],
            "missing_policy": "per-method omit; counts and warnings retained",
        },
    )
    output = tmp_path / "inspection.bundle.json"
    output.write_text(bundle.to_json())
    assert validate_bundle(output.read_text())["bundle_version"] == "2.0"
    script = Path(lss4py.__file__).with_name("_bundle_schema.py")
    validation = subprocess.run(
        [sys.executable, "-I", "-S", str(script), str(output)],
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(validation.stdout)["audited"]
    saved = AnalysisBundle.from_json(output.read_text())
    saved.verify_inputs({"measurements": source})
    restored = saved.get_result("capability")
    assert isinstance(restored, CapabilityResult)
    assert restored.to_dict() == capability.to_dict()
    # The caller chooses and executes the method; loading a bundle never does so.
    parameters = restored.provenance.parameters
    replayed = pl.read_csv(BytesIO(source))
    rerun = capability_indices(
        replayed,
        column=parameters["column"],
        specification=saved.specifications["diameter"],
        missing=parameters["missing"],
        ci=parameters["ci"],
        confidence_level=parameters["confidence_level"],
        sigma_shift=parameters["sigma_shift"],
    )
    assert rerun.cp == restored.cp
    assert rerun.cpk_confidence_interval == restored.cpk_confidence_interval
    with pytest.raises(ValidationError, match="fingerprint"):
        saved.verify_inputs({"measurements": source + b"changed"})
