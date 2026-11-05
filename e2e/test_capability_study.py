"""Installed composed study from source CSVs to a verified audited bundle."""

import json
from importlib.metadata import version

import pytest

from lss4py import (
    AnalysisBundle,
    CapabilityResult,
    CapabilityStudyResult,
    DistributionProfileResult,
    InputReference,
    Specification,
    __version__,
    capability_study,
)
from lss4py.domain import AnalyticalResult


def test_composed_capability_study(read_csv, backend, tmp_path):
    short_raw = b"value,record\n9,a\n10,b\n11,c\n,d\n10,e\n"
    long_raw = b"value\n7\n10\n13\n12\n"
    short_path = tmp_path / "short.csv"
    long_path = tmp_path / "long.csv"
    short_path.write_bytes(short_raw)
    long_path.write_bytes(long_raw)
    specification = Specification("Fill volume", "ml", "target", target=10, lsl=8, usl=12)
    study = capability_study(
        read_csv(short_path),
        column="value",
        specification=specification,
        long_term_data=read_csv(long_path),
        missing="omit",
        confidence_level=0.9,
        normality_alpha=0.1,
    )
    assert study.short_term_nonconformance["nonconforming"] == 0
    assert study.long_term_nonconformance is not None
    assert study.long_term_nonconformance["nonconforming"] == 2
    assert study.long_term_nonconformance["nonconforming_rate"] == 0.5
    assert study.short_term_capability is not None
    assert study.short_term_capability.mean == pytest.approx(10)
    assert study.short_term_capability.cp == pytest.approx(4 / (6 * (2 / 3) ** 0.5))
    assert study.short_term_capability.cpk == study.short_term_capability.cp
    assert study.short_term_capability.cp_confidence_interval is not None
    for role in ("short_term", "long_term"):
        capability = getattr(study, f"{role}_capability")
        distribution = getattr(study, f"{role}_distribution")
        assert isinstance(capability, CapabilityResult)
        assert isinstance(distribution, DistributionProfileResult)
        assert capability.count == distribution.count == 4
        assert capability.total == distribution.total == (5 if role == "short_term" else 4)
        assert capability.missing == distribution.missing == (1 if role == "short_term" else 0)
        assert capability.provenance.backend == distribution.provenance.backend == backend
        assert capability.confidence_level == 0.9
        assert distribution.normality_alpha == 0.1
        assert capability.unit == distribution.unit == "ml"
        assert capability.provenance.parameters["missing"] == "omit"
        assert distribution.provenance.parameters["missing"] == "omit"
    restored = AnalyticalResult.from_dict(json.loads(study.to_json()))
    assert isinstance(restored, CapabilityStudyResult)
    assert isinstance(restored.short_term_capability, CapabilityResult)
    assert isinstance(restored.long_term_distribution, DistributionProfileResult)
    assert restored.to_dict() == study.to_dict()
    bundle = AnalysisBundle.capture(
        "Explicit capability study",
        results={"study": study},
        inputs={
            "short": InputReference.from_bytes(
                "short.csv", short_raw, selection="Short-term sample"
            ),
            "long": InputReference.from_bytes("long.csv", long_raw, selection="Long-term sample"),
        },
        result_inputs={"study": ["short", "long"]},
        cohort_definition="Explicit short- and long-term samples",
        software_versions={
            "lss4py": __version__,
            **{name: version(name) for name in ("numpy", "scipy", "narwhals", backend)},
        },
        specifications={"ctq": specification},
        result_specifications={"study": ["ctq"]},
    )
    destination = tmp_path / "study-bundle.json"
    destination.write_text(bundle.to_json())
    loaded = AnalysisBundle.from_json(destination.read_text())
    loaded.verify_inputs({"short": short_raw, "long": long_raw})
    assert loaded.get_result("study").to_dict() == study.to_dict()
    assert loaded.result_inputs["study"] == ("short", "long")
    assert loaded.specifications["ctq"] == specification
