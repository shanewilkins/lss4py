"""Reconstruct the pinned book orders using public numeric activity contracts."""

import json
from pathlib import Path

from lss4py import (
    NumericLogContract,
    OrderReconstructionPolicy,
    load_numeric_event_log,
    reconstruct_orders,
)

HERE = Path(__file__).parent
POLICY = OrderReconstructionPolicy(
    arrival_activity="Drop-off and ticket",
    readiness_activity="Send readiness notification",
    required_activities=(
        "Drop-off and ticket",
        "Sort and tag",
        "Wash",
        "Dry",
        "Fold and package",
        "Stage for collection",
        "Send readiness notification",
    ),
    parallel_activities=("Wash", "Dry"),
    value_add_activities=("Wash", "Dry", "Fold and package", "Send readiness notification"),
    rework_column="Rework Y/N",
    rework_value="Y",
    non_rework_value="N",
    correction_activity="Fold correction",
    cohort="All 39 orders in washnfold-friday91 v1.0.0",
    value_add_convention=(
        "Right-first-time Wash, Dry, Fold/package and readiness notification; staging RNVA."
    ),
    parallel_load_count_column="Compatible Loads",
    required_non_value_add_activities=(
        "Drop-off and ticket",
        "Sort and tag",
        "Stage for collection",
    ),
)


def reconstruct(source: Path):
    """Load all source records and retain auditable intermediate activity envelopes."""
    profile = json.loads((HERE / "simulation_sources.json").read_text())["profiles"][0]
    log = load_numeric_event_log(
        source,
        contract=NumericLogContract.from_dict(profile["contract"]),
        expected_sha256=profile["expected_sha256"],
    )
    return reconstruct_orders(log, policy=POLICY)


if __name__ == "__main__":
    result = reconstruct(HERE / "event_log.csv")
    print(result.to_polars())
    print(f"Corrections: {result.metadata['correction_occurrences']}")
