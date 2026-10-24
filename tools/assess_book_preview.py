"""Assess local book fixtures; diagnostic tooling, not a supported book demo API.

Run: uv run --locked python tools/assess_book_preview.py --output <report.json>
The sibling checkout is read only. No simulation or fixture regeneration is run.
"""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import mean, median

import polars as pl

import lss4py as lss

D = Decimal
ARRIVAL = "Arrival (elapsed min)"
READY = "Ready and notified (elapsed min)"
LEAD = "Operating L/T (min)"
VA = "VA time (min)"
COMPONENTS = ("P/T (min)", "W/T (min)", "S/T (min)")
ENDPOINTS = (
    "Queue Entry (elapsed min)",
    "Setup Start (elapsed min)",
    "Work Start (elapsed min)",
    "Work End (elapsed min)",
)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def probe(operation):
    """Record actual behavior, including errors, without treating gaps as passes."""
    try:
        return {"returned": operation()}
    except Exception as exc:  # Diagnostic evidence must retain backend failures too.
        return {"error_type": type(exc).__name__, "message": str(exc)}


def reference_audit(events, summaries):
    """Independent Decimal audit of the current generator's declared convention.

    This checks supplied evidence only; it is not a general reconstruction API.
    """
    by_order = defaultdict(list)
    for row in events:
        by_order[row["Order ID"]].append(row)
    mismatches = []
    invalid = []
    partitions = []
    correction_mismatches = []
    spot = []
    for order in summaries:
        order_id = order["Order ID"]
        groups = defaultdict(list)
        rows = by_order[order_id]
        for row in rows:
            endpoints = [D(row[name]) for name in ENDPOINTS]
            if endpoints != sorted(endpoints):
                invalid.append([order_id, row["Activity Name"], "ordering"])
            p, w, s = (D(row[name]) for name in COMPONENTS)
            q, setup, start, end = endpoints
            if (p, w, s) != (end - start, setup - q, start - setup):
                invalid.append([order_id, row["Activity Name"], "activity formula"])
            groups[row["Activity Name"], row["Pass"]].append(row)
        timings = []
        for (activity, activity_pass), records in groups.items():
            if activity in {"Wash", "Dry"}:
                q, setup = (min(D(r[name]) for r in records) for name in ENDPOINTS[:2])
                start, end = (max(D(r[name]) for r in records) for name in ENDPOINTS[2:])
                p, w, s = end - start, setup - q, start - setup
            else:
                p, w, s = (sum(D(r[name]) for r in records) for name in COMPONENTS)
            right_first_time = all(r["Rework Y/N"] != "Y" for r in records)
            is_va = right_first_time and activity in {
                "Wash",
                "Dry",
                "Fold and package",
                "Send readiness notification",
            }
            timings.append(
                {
                    "activity": activity,
                    "pass": activity_pass,
                    "pt": p,
                    "wt": w,
                    "st": s,
                    "va": p if is_va else D(0),
                }
            )
        starts = [D(r[ENDPOINTS[0]]) for r in rows if r["Activity Name"] == "Drop-off and ticket"]
        ends = [
            D(r[ENDPOINTS[3]]) for r in rows if r["Activity Name"] == "Send readiness notification"
        ]
        if len(starts) != 1 or len(ends) != 1:
            invalid.append([order_id, "boundary endpoint multiplicity"])
            continue
        calculated = {
            ARRIVAL: starts[0],
            READY: ends[0],
            LEAD: ends[0] - starts[0],
            VA: sum(t["va"] for t in timings),
        }
        for component, key in zip(COMPONENTS, ["pt", "wt", "st"], strict=True):
            calculated["Total " + component] = sum(t[key] for t in timings)
        for name, value in calculated.items():
            if value != D(order[name]):
                mismatches.append([order_id, name, str(value), order[name]])
        if sum(calculated["Total " + name] for name in COMPONENTS) != calculated[LEAD]:
            partitions.append(order_id)
        corrections = sum(r["Activity Name"] == "Fold correction" for r in rows)
        if corrections != int(order["Correction occurrences"]):
            correction_mismatches.append(order_id)
        if order_id == "WNF-003":
            spot = timings
    return {
        "orders_audited": len(summaries),
        "invalid_activity_records": invalid,
        "prepared_summary_mismatches": mismatches,
        "order_partition_mismatches": partitions,
        "correction_count_mismatches": correction_mismatches,
        "wnf003_activity_spans": spot,
        "event_orders_without_summary": sorted(set(by_order) - {r["Order ID"] for r in summaries}),
    }


def public_probes(frame, eligible, data_dir):
    summary = lss.describe(frame, column=LEAD, missing="raise", unit="minutes")
    eligible_summary = lss.describe(eligible, column=LEAD, missing="raise", unit="minutes")
    counterexample = lss.describe(pl.DataFrame({"x": [1, 2, 3, 4]}), column="x")
    if eligible_summary.percentiles is None or counterexample.percentiles is None:
        raise ValueError("The complete assessment fixtures must have defined percentiles.")
    row_pce = lss.process_cycle_efficiency(frame, lead_time_column=LEAD, value_add_time_column=VA)
    totals = frame.select(pl.col(LEAD).sum(), pl.col(VA).sum())
    aggregate = lss.process_cycle_efficiency(
        totals, lead_time_column=LEAD, value_add_time_column=VA
    )
    contract = lss.DataContract(
        columns=(lss.ColumnRule("Order ID", kind="string"),)
        + tuple(
            lss.ColumnRule(name, minimum=0, unit="minutes") for name in (ARRIVAL, READY, LEAD, VA)
        ),
        key_columns=("Order ID",),
        duplicates="error",
    )
    validation = lss.validate_data(frame, contract=contract)
    duplicate_validation = lss.validate_data(pl.concat([frame, frame.head(1)]), contract=contract)
    return {
        "package_version": lss.__version__,
        "describe_all": {
            "count": summary.count,
            "mean": summary.mean,
            "median": summary.median,
            "has_sum_field": hasattr(summary, "measurement_sum"),
            "total_field": summary.total,
        },
        "describe_eligible": {
            "mean": eligible_summary.mean,
            "median": eligible_summary.median,
            "p90": eligible_summary.percentiles["p90"],
            "method": eligible_summary.provenance.parameters["percentile_method"],
        },
        "percentile_method_argument": probe(
            # Probe current availability; retain the original assessment snapshot separately.
            lambda: lss.describe(frame, column=LEAD, percentile_method="nearest_rank").to_dict()
        ),
        "nearest_rank_counterexample_linear": counterexample.percentiles["p90"],
        "mean_of_row_pce_percent": float(mean(row_pce.values)),
        "pce_on_explicit_totals_percent": float(aggregate.values[0]),
        "pce_totals_cohort_metadata": aggregate.provenance.cohort_definition,
        "numeric_lead_time": probe(
            lambda: lss.lead_time(
                frame.head(1), start_column=ARRIVAL, end_column=READY, unit="minutes"
            ).values.tolist()
        ),
        "numeric_interval_loader": probe(
            lambda: (
                lss.load_event_log(
                    data_dir / "washnfold_event_log.csv",
                    case_id_column="Order ID",
                    step_id_column="Activity Name",
                    started_at_column=ENDPOINTS[2],
                    completed_at_column=ENDPOINTS[3],
                ).height
            )
        ),
        "data_contract_valid": validation.valid,
        "data_contract_duplicate_rejected": not duplicate_validation.valid,
        "numeric_order_contract": probe(
            lambda: lss.DataContract(
                columns=(lss.ColumnRule(ARRIVAL), lss.ColumnRule(READY)),
                timestamp_order=((ARRIVAL, READY),),
            ).to_dict()
        ),
        "existing_wait_time_on_minutes": probe(
            lambda: {
                "first_value": float(
                    lss.wait_time(
                        frame, lead_time_column=LEAD, cycle_time_column="Total P/T (min)"
                    ).values[0]
                ),
                "unit": lss.wait_time(
                    frame, lead_time_column=LEAD, cycle_time_column="Total P/T (min)"
                ).unit,
            }
        ),
        "promise_public_export": any("promise" in name for name in lss.__all__),
    }


def main():
    """Capture source fingerprints, independent values, and real public API behavior."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--book-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "modern-process-improvement",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    book = args.book_root.resolve()
    data_dir = book / "data/washnfold"
    summaries = read_csv(data_dir / "washnfold_learner_order_summary.csv")
    events = read_csv(data_dir / "washnfold_event_log.csv")
    eligible = [r for r in summaries if D(r[ARRIVAL]) <= 120]
    leads = [D(r[LEAD]) for r in summaries]
    eligible_leads = sorted(D(r[LEAD]) for r in eligible)
    va = sum(D(r[VA]) for r in summaries)
    total_lead = sum(leads)
    misses = sum(D(r[READY]) > 600 for r in eligible)
    spot = next(r for r in summaries if r["Order ID"] == "WNF-003")
    paths = [
        data_dir / name
        for name in [
            "README.md",
            "washnfold_event_log.csv",
            "washnfold_learner_order_summary.csv",
            "washnfold_baseline_readout.csv",
            "washnfold_simulation.py",
            "washnfold_representative_run.csv",
        ]
    ] + [book / "book/content/white_belt/measuring_process.qmd", book / "LICENSE.md"]
    frame = pl.read_csv(data_dir / "washnfold_learner_order_summary.csv")
    original_va = D("3582.3")
    metrics = {
        "orders": len(summaries),
        "eligible_orders": len(eligible),
        "ineligible_orders": len(summaries) - len(eligible),
        "event_records": len(events),
        "activities": dict(Counter(r["Activity Name"] for r in events)),
        "all_mean_lead_min": mean(leads),
        "eligible_sum_lead_min": sum(eligible_leads),
        "eligible_mean_lead_min": mean(eligible_leads),
        "eligible_median_lead_min": median(eligible_leads),
        "eligible_p90_position": math.ceil(D(".9") * len(eligible)),
        "eligible_p90_min": eligible_leads[math.ceil(D(".9") * len(eligible)) - 1],
        "eligible_misses": misses,
        "eligible_miss_percent": D(100) * misses / len(eligible),
        "total_va_min": va,
        "total_lead_min": total_lead,
        "cohort_pce_percent": D(100) * va / total_lead,
        "mean_order_components_min": {
            c: mean(D(r["Total " + c]) for r in summaries) for c in COMPONENTS
        },
        "correction_occurrences": sum(int(r["Correction occurrences"]) for r in summaries),
        "distinct_corrected_orders": sum(int(r["Correction occurrences"]) > 0 for r in summaries),
        "rework_flagged_records": sum(r["Rework Y/N"] == "Y" for r in events),
        "duplicate_order_ids": [
            key for key, n in Counter(r["Order ID"] for r in summaries).items() if n > 1
        ],
        "promise_flag_mismatches": [
            r["Order ID"]
            for r in summaries
            if r["Promise eligible Y/N"] != ("Y" if D(r[ARRIVAL]) <= 120 else "N")
            or r["Promise missed Y/N/NA"]
            != ("NA" if D(r[ARRIVAL]) > 120 else ("Y" if D(r[READY]) > 600 else "N"))
        ],
        "wnf003": spot,
    }
    report = {
        "purpose": "Assessment evidence only; not a new public calculation or canonical fixture",
        "source_root": str(book),
        "sha256": {
            str(path.relative_to(book)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        },
        "lss4py_source_sha256": {
            name: hashlib.sha256(
                (Path(__file__).resolve().parents[1] / name).read_bytes()
            ).hexdigest()
            for name in (
                "src/lss4py/__init__.py",
                "src/lss4py/_kernels/timing.py",
                "src/lss4py/_kernels/descriptive.py",
                "src/lss4py/domain/data_quality.py",
                "src/lss4py/adapters/event_log.py",
            )
        },
        "independent_metrics": metrics,
        "original_requirement_drift": {
            "original_total_va_min": original_va,
            "current_minus_original_va_min": va - original_va,
            "original_pce_display": "13.9%",
            "current_pce_display": f"{100 * va / total_lead:.1f}%",
            "original_wnf003_va_min": "94.4",
            "current_wnf003_va_min": spot[VA],
            "original_final_activity": "Stage and notify",
            "current_final_activity": "Send readiness notification",
        },
        "reference_audit": reference_audit(events, summaries),
        "public_api_probes": public_probes(frame, frame.filter(pl.col(ARRIVAL) <= 120), data_dir),
    }
    payload = json.dumps(report, indent=2, default=str, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(payload)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
