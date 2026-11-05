"""Capture governed invalid-input acceptance and exception contracts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import polars as pl

from lss4py import (
    Specification,
    booked_to_completed_yield,
    capability_indices,
    deadline_performance,
    describe,
    distribution_profile,
    lead_time,
    mean_confidence_interval,
    process_cycle_efficiency,
    process_yield,
    wait_time,
)


def _cases() -> dict[str, Callable[[], Any]]:
    """Return bounded invalid domains spanning every migrated analytical family."""
    return {
        "capability_missing_limits": lambda: capability_indices(
            pl.DataFrame({"value": [1.0, 2.0]}),
            column="value",
            specification=Specification("X", "mm", "lower"),
        ),
        "deadline_empty_eligible_population": lambda: deadline_performance(
            pl.DataFrame({"case": ["A"], "arrival": [2.0], "ready": [3.0]}),
            case_id_column="case",
            arrival_column="arrival",
            readiness_column="ready",
            eligibility_cutoff=1.0,
            deadline=4.0,
            unit="hours",
            clock="operating",
            boundary="arrival through readiness",
            cohort="declared probe cohort",
        ),
        "descriptive_infinite_measurement": lambda: describe(
            pl.DataFrame({"value": [1.0, float("inf")]}),
            column="value",
        ),
        "descriptive_missing_column": lambda: describe(
            pl.DataFrame({"value": [1.0]}),
            column="absent",
        ),
        "distribution_duplicate_key": lambda: distribution_profile(
            pl.DataFrame({"value": [1.0, 2.0], "key": ["A", "A"]}),
            column="value",
            key_column="key",
        ),
        "lazy_input": lambda: describe(
            pl.DataFrame({"value": [1.0]}).lazy(),
            column="value",
        ),
        "lead_time_negative": lambda: lead_time(
            pl.DataFrame(
                {
                    "start": ["2026-01-01T10:00:00"],
                    "end": ["2026-01-01T09:00:00"],
                }
            ),
            start_column="start",
            end_column="end",
        ),
        "mean_interval_missing_raise": lambda: mean_confidence_interval(
            pl.DataFrame({"value": [1.0, None]}),
            column="value",
            missing="raise",
        ),
        "process_cycle_efficiency_zero_lead": lambda: process_cycle_efficiency(
            pl.DataFrame({"lead": [0.0], "value_add": [0.0]}),
            lead_time_column="lead",
            value_add_time_column="value_add",
        ),
        "process_yield_fractional_count": lambda: process_yield(
            pl.DataFrame({"defects": [0.5]}),
            opportunities=10,
        ),
        "stage_yield_nonbinary": lambda: booked_to_completed_yield(
            pl.DataFrame({"booked": [1], "completed": [0.5]}),
            booked_column="booked",
            completed_column="completed",
        ),
        "unsupported_mapping_input": lambda: describe({"value": [1.0]}, column="value"),
        "wait_time_cycle_exceeds_lead": lambda: wait_time(
            pl.DataFrame({"lead": [1.0], "cycle": [2.0]}),
            lead_time_column="lead",
            cycle_time_column="cycle",
        ),
    }


def capture_invalid_contract() -> dict[str, dict[str, str]]:
    """Execute every probe and retain exact acceptance or exception identity."""
    outcomes = {}
    for name, operation in _cases().items():
        try:
            result = operation()
        except Exception as exc:
            outcomes[name] = {
                "status": "error",
                "exception": f"{type(exc).__module__}.{type(exc).__name__}",
                "message": str(exc),
            }
        else:
            outcomes[name] = {
                "status": "returned",
                "result_type": type(result).__name__,
            }
    return outcomes


def main() -> None:
    """Capture the invalid-input contract and optionally retain it as JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(capture_invalid_contract(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
