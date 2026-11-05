"""Installed-wheel monitoring with portable baselines and explicit measurement units."""

import json

import pytest

from lss4py import ControlChartResult, ValidationError, control_chart
from lss4py.domain import AnalyticalResult


def test_portable_monitoring_baseline(read_csv, tmp_path):
    source = tmp_path / "baseline.csv"
    source.write_text("sample,x\na,0\nb,1e-15\nc,2e-15\n")
    baseline = control_chart(read_csv(source), column="x", key_column="sample", unit="seconds")
    restored = AnalyticalResult.from_dict(json.loads(baseline.to_json()))
    assert isinstance(restored, ControlChartResult)
    monitoring = tmp_path / "monitoring.csv"
    monitoring.write_text("x\n0\n1e-13\n")
    frame = read_csv(monitoring)
    result = control_chart(frame, column="x", baseline=restored)
    assert result.unit == "seconds"
    assert result.signal_indices.tolist() == [0]
    with pytest.raises(ValidationError, match="unit must match"):
        control_chart(frame, column="x", baseline=restored, unit="minutes")
    restored.ucl = 9e-13
    with pytest.raises(ValidationError, match="limits differ"):
        control_chart(frame, column="x", baseline=restored)
    payload = json.loads(baseline.to_json())
    payload["pair_end_keys"] = ["wrong", "wrong"]
    with pytest.raises(ValidationError, match="adjacent observations"):
        AnalyticalResult.from_dict(payload)
