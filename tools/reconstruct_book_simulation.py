"""Run the full pinned activity-to-order route and save audited evidence offline."""

import json
import runpy
from importlib.metadata import version
from pathlib import Path
from typing import Any

import polars as pl

from lss4py import (
    AnalysisBundle,
    InputReference,
    deadline_performance,
    describe,
    process_cycle_efficiency,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/white_belt"


def main() -> None:
    """Reconstruct every order and capture the four book readouts with source links."""
    namespace = runpy.run_path(str(EXAMPLE / "reconstruct.py"))
    result = namespace["reconstruct"](EXAMPLE / "event_log.csv")
    policy = namespace["POLICY"]
    orders = result.to_polars()
    context: dict[str, Any] = {
        "unit": result.metadata["unit"],
        "clock": result.metadata["clock"],
        "boundary": result.metadata["boundary"],
        "cohort": policy.cohort,
    }
    mean = describe(orders, column="lead_time", missing="raise", **context)
    eligible_context: dict[str, Any] = {**context, "cohort": "Orders arriving <= minute 120"}
    p90 = describe(
        orders.filter(pl.col("arrival") <= 120),
        column="lead_time",
        missing="raise",
        percentile_method="nearest_rank",
        **eligible_context,
    )
    promise = deadline_performance(
        orders,
        case_id_column="Order ID",
        arrival_column="arrival",
        readiness_column="readiness",
        eligibility_cutoff=120,
        deadline=600,
        **context,
    )
    pce = process_cycle_efficiency(
        orders,
        case_id_column="Order ID",
        lead_time_column="lead_time",
        value_add_time_column="value_add",
        aggregation="cohort",
        value_add_convention=policy.value_add_convention,
        **context,
    )
    results = {"reconstruction": result, "mean": mean, "p90": p90, "promise": promise, "pce": pce}
    bundle = AnalysisBundle.capture(
        "White Belt activity-to-order reconstruction",
        results=results,
        inputs={
            "events": InputReference.from_bytes(
                "event_log.csv",
                (EXAMPLE / "event_log.csv").read_bytes(),
                selection="All 330 activity records, no exclusions",
                media_type="text/csv",
            )
        },
        result_inputs=dict.fromkeys(results, ("events",)),
        cohort_definition=policy.cohort,
        software_versions={
            name: version(name) for name in ("lss4py", "numpy", "narwhals", "polars", "scipy")
        },
        context={
            "dependency": "Readouts consume the reconstructed orders table",
            "policy": policy.to_dict(),
        },
    )
    (EXAMPLE / "reconstruction-bundle.json").write_text(bundle.to_json() + "\n")
    readout = {
        "orders": orders.height,
        "activity_records": result.to_polars("activity_records").height,
        "corrections": result.metadata["correction_occurrences"],
        "affected_orders": result.metadata["affected_orders"],
        "mean_lead": round(mean.mean, 1),
        "eligible_p90": round(p90.percentiles["p90"], 1),
        "promise_misses": promise.numerator,
        "eligible_orders": promise.denominator,
        "pce_percent": round(float(pce.values[0]), 1),
    }
    print(json.dumps(readout, indent=2))


if __name__ == "__main__":
    main()
