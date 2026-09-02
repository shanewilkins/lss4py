"""Tests for Sprint 1: Result Models & Provenance.

Tests verify:
- AnalyticalResult base class and subclasses
- Provenance metadata capture and serialization
- yellow_belt.py functions returning typed results
- Result construction, serialization, and provenance snapshots
"""

import json

import numpy as np
import pandas as pd
import pytest

from lss4py import lead_time
from lss4py.domain import (
    AnalysisBundle,
    AssumptionNote,
    Provenance,
    TimingResult,
    YieldResult,
)


class TestProvenance:
    """Test Provenance model and serialization."""

    def test_provenance_creation(self) -> None:
        """Test creating a provenance record."""
        prov = Provenance(
            method="lead_time",
            method_version="1.0",
            package_version="0.2.0",
            backend="pandas",
            parameters={"start_column": "created_at", "end_column": "completed_at"},
        )

        assert prov.method == "lead_time"
        assert prov.package_version == "0.2.0"
        assert prov.backend == "pandas"

    def test_provenance_with_assumptions_and_warnings(self) -> None:
        """Test provenance with assumptions and warnings."""
        assumptions = [
            AssumptionNote(
                code="TIMESTAMP_ORDERING",
                message="Assumes end >= start",
            ),
        ]
        warnings = [
            AssumptionNote(
                code="SMALL_SAMPLE",
                message="Sample size < 30",
                severity="warning",
            ),
        ]

        prov = Provenance(
            method="lead_time",
            method_version="1.0",
            package_version="0.2.0",
            backend="polars",
            parameters={"unit": "hours"},
            assumptions=assumptions,
            warnings=warnings,
        )

        assert len(prov.assumptions) == 1
        assert len(prov.warnings) == 1
        assert prov.assumptions[0].code == "TIMESTAMP_ORDERING"
        assert prov.warnings[0].severity == "warning"

    def test_provenance_serialization(self) -> None:
        """Test provenance to_dict and to_json."""
        prov = Provenance(
            method="lead_time",
            method_version="1.0",
            package_version="0.2.0",
            backend="pandas",
        )

        prov_dict = prov.to_dict()
        assert prov_dict["method"] == "lead_time"
        assert prov_dict["backend"] == "pandas"
        assert "created_at" in prov_dict

        prov_json = prov.to_json()
        parsed = json.loads(prov_json)
        assert parsed["method"] == "lead_time"


class TestAnalyticalResult:
    """Test AnalyticalResult base class."""

    def test_timing_result_creation(self) -> None:
        """Test creating a TimingResult."""
        prov = Provenance(
            method="lead_time",
            method_version="1.0",
            package_version="0.2.0",
            backend="pandas",
        )

        values = np.array([3.0, 4.5, 2.1])
        result = TimingResult(
            name="Lead Time",
            provenance=prov,
            values=values,
            unit="hours",
        )

        assert result.name == "Lead Time"
        assert result.unit == "hours"
        assert len(result.values) == 3
        assert result.values[0] == 3.0

    def test_yield_result_creation(self) -> None:
        """Test creating a YieldResult."""
        prov = Provenance(
            method="rolled_yield",
            method_version="1.0",
            package_version="0.2.0",
            backend="pandas",
        )

        result = YieldResult(
            name="Rolled Throughput Yield",
            provenance=prov,
            value=0.88,
            unit="fraction",
            numerator=88,
            denominator=100,
        )

        assert result.name == "Rolled Throughput Yield"
        assert result.value == 0.88
        assert result.numerator == 88

    def test_result_serialization(self) -> None:
        """Test result to_dict and to_json."""
        prov = Provenance(
            method="lead_time",
            method_version="1.0",
            package_version="0.2.0",
            backend="pandas",
        )

        result = TimingResult(
            name="Lead Time",
            provenance=prov,
            values=np.array([3.0, 4.5]),
            unit="hours",
            interpretation_context="Total time from start to end.",
        )

        result_dict = result.to_dict()
        assert result_dict["result_type"] == "TimingResult"
        assert result_dict["name"] == "Lead Time"
        assert result_dict["provenance"]["method"] == "lead_time"

        result_json = result.to_json()
        parsed = json.loads(result_json)
        assert parsed["result_type"] == "TimingResult"

    def test_timing_result_to_numpy(self) -> None:
        """Test extracting NumPy array from TimingResult."""
        prov = Provenance(
            method="lead_time",
            method_version="1.0",
            package_version="0.2.0",
            backend="pandas",
        )

        values = np.array([3.0, 4.5, 2.1])
        result = TimingResult(
            name="Lead Time",
            provenance=prov,
            values=values,
            unit="hours",
        )

        extracted = result.to_numpy()
        np.testing.assert_array_equal(extracted, values)
        # Verify it's a copy, not a reference
        assert extracted is not result.values


class TestYellowBeltRefactor:
    """Test yellow_belt.py functions returning typed results."""

    def test_lead_time_returns_typed_result(self) -> None:
        """Test that lead_time returns a TimingResult."""
        data = pd.DataFrame(
            {
                "created_at": ["2026-01-01T08:00:00", "2026-01-02T09:00:00"],
                "completed_at": ["2026-01-01T11:00:00", "2026-01-02T10:30:00"],
            }
        )

        result = lead_time(data, start_column="created_at", end_column="completed_at", unit="hours")

        # Verify result type
        assert isinstance(result, TimingResult)
        assert result.name == "Lead Time"
        assert result.unit == "hours"

    def test_lead_time_provenance_captured(self) -> None:
        """Test that lead_time captures provenance."""
        data = pd.DataFrame(
            {
                "created_at": ["2026-01-01T08:00:00"],
                "completed_at": ["2026-01-01T11:00:00"],
            }
        )

        result = lead_time(data, start_column="created_at", end_column="completed_at")

        # Verify provenance
        assert result.provenance.method == "lead_time"
        assert result.provenance.backend == "pandas"
        assert result.provenance.parameters["start_column"] == "created_at"
        assert result.provenance.parameters["unit"] == "hours"

    def test_lead_time_assumptions_captured(self) -> None:
        """Test that lead_time captures assumptions."""
        data = pd.DataFrame(
            {
                "created_at": ["2026-01-01T08:00:00"],
                "completed_at": ["2026-01-01T11:00:00"],
            }
        )

        result = lead_time(data, start_column="created_at", end_column="completed_at")

        # Verify assumptions
        assert len(result.provenance.assumptions) > 0
        assumption_codes = [a.code for a in result.provenance.assumptions]
        assert "TIMESTAMP_ORDERING" in assumption_codes

    def test_lead_time_interpretation_context(self) -> None:
        """Test that lead_time includes interpretation context."""
        data = pd.DataFrame(
            {
                "created_at": ["2026-01-01T08:00:00"],
                "completed_at": ["2026-01-01T11:00:00"],
            }
        )

        result = lead_time(data, start_column="created_at", end_column="completed_at")

        assert result.interpretation_context is not None
        assert "Lead time" in result.interpretation_context
        assert "improve" in result.interpretation_context.lower()

    def test_lead_time_values_correct(self) -> None:
        """Test that lead_time values are calculated correctly."""
        data = pd.DataFrame(
            {
                "created_at": ["2026-01-01T08:00:00", "2026-01-02T09:15:00"],
                "completed_at": ["2026-01-01T11:00:00", "2026-01-02T10:45:00"],
            }
        )

        result = lead_time(data, start_column="created_at", end_column="completed_at", unit="hours")

        assert len(result.values) == 2
        assert np.isclose(result.values[0], 3.0)
        assert np.isclose(result.values[1], 1.5)


class TestAnalysisBundle:
    """Test AnalysisBundle versioned container."""

    def test_bundle_creation(self) -> None:
        """Test creating an analysis bundle."""
        prov = Provenance(
            method="lead_time",
            method_version="1.0",
            package_version="0.2.0",
            backend="pandas",
        )

        result = TimingResult(
            name="Lead Time",
            provenance=prov,
            values=np.array([3.0, 4.5]),
            unit="hours",
        )

        bundle = AnalysisBundle(
            name="Q3 Intake Process Baseline",
            results=[result],
            cohort_definition="All intake cases in Q3 2026",
        )

        assert bundle.name == "Q3 Intake Process Baseline"
        assert len(bundle.results) == 1
        assert bundle.bundle_version == "1.0"

    def test_bundle_serialization(self) -> None:
        """Test bundle serialization."""
        prov = Provenance(
            method="lead_time",
            method_version="1.0",
            package_version="0.2.0",
            backend="pandas",
        )

        result = TimingResult(
            name="Lead Time",
            provenance=prov,
            values=np.array([3.0]),
            unit="hours",
        )

        bundle = AnalysisBundle(
            name="Test Bundle",
            results=[result],
        )

        bundle_dict = bundle.to_dict()
        assert bundle_dict["bundle_type"] == "AnalysisBundle"
        assert bundle_dict["name"] == "Test Bundle"
        assert len(bundle_dict["results"]) == 1

        bundle_json = bundle.to_json()
        parsed = json.loads(bundle_json)
        assert parsed["bundle_type"] == "AnalysisBundle"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
