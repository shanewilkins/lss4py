"""Reproduce the governed book baseline using released FLO and installed LSS4PY."""

import argparse
import json
from importlib import import_module, metadata
from pathlib import Path
from typing import Any

import polars as pl

from lss4py import (
    AnalysisBundle,
    InputReference,
    NumericLogContract,
    TimingResult,
    ValidationError,
    deadline_performance,
    describe,
    load_numeric_event_log,
    process_cycle_efficiency,
    reconstruct_orders,
)
from lss4py.integration import (
    ProcessProjection,
    ReconstructionConventions,
    derive_reconstruction_policy,
)

HERE = Path(__file__).parent


def _model(model_dir):
    """Verify frozen model artifacts before invoking the public producer facade."""
    manifest = json.loads((model_dir / "manifest.json").read_text())
    for name, digest in manifest["artifacts_sha256"].items():
        InputReference(name, digest, "Complete governed model artifact").verify(
            (model_dir / name).read_bytes()
        )
    flo = import_module("flo")
    if metadata.version("flo-lang") != manifest["producer"]["version"]:
        raise ValidationError("The governed example requires FLO 0.5.0.")
    source = (model_dir / "washnfold.flo").read_text()
    validated, exported = flo.validate(source), flo.export(source)
    if not validated.ok or not exported.ok or exported.value is None:
        raise ValidationError(
            f"FLO rejected the model: {validated.diagnostics} {exported.diagnostics}"
        )
    payload = json.loads(exported.value)
    if payload != json.loads((model_dir / "process-export.json").read_text()):
        raise ValidationError("Public FLO export differs from the governed snapshot.")
    projection = ProcessProjection.from_flo_export(
        payload,
        source=manifest["observations"]["dataset_id"],
        model_revision=manifest["source"]["revision"],
        step_mapping=json.loads((model_dir / "activity-mapping.json").read_text()),
        flo_version=metadata.version("flo-lang"),
    )
    if projection.digest != manifest["bridge"]["projection_sha256"]:
        raise ValidationError("Projection differs from the governed book profile.")
    return manifest, validated.value, projection, exported.report.as_dict()


def _conventions():
    """Declare accounting rules while leaving all baseline classes in FLO."""
    return ReconstructionConventions(
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
        rework_column="Rework Y/N",
        rework_value="Y",
        non_rework_value="N",
        correction_activity="Fold correction",
        cohort="All 39 orders in washnfold-friday91 v1.0.0",
        value_add_convention="Model baseline classes; failed attempts NVA; setup/wait excluded.",
        parallel_load_count_column="Compatible Loads",
    )


def _measure(log, projection):
    """Compute observed metrics using existing reconstruction and measurement APIs."""
    bound = derive_reconstruction_policy(
        projection,
        observed_activities=tuple(log.frame[log.contract.activity_column].unique()),
        conventions=_conventions(),
    )
    reconstruction = reconstruct_orders(log, policy=bound.policy)
    reconstruction.metadata["policy_derivation"] = bound.to_dict()
    orders = reconstruction.to_polars()
    context: dict[str, Any] = {
        "unit": log.contract.unit,
        "clock": log.contract.clock,
        "boundary": log.contract.boundary,
        "cohort": bound.policy.cohort,
    }
    eligible_context: dict[str, Any] = {
        **context,
        "cohort": "21 orders arriving at or before operating minute 120",
    }
    eligible = orders.filter(pl.col("arrival") <= 120)
    results = {
        "reconstruction": reconstruction,
        "mean_lead": describe(orders, column="lead_time", missing="raise", **context),
        "eligible_lead": describe(
            eligible,
            column="lead_time",
            missing="raise",
            percentile_method="nearest_rank",
            **eligible_context,
        ),
        "promise": deadline_performance(
            orders,
            case_id_column="Order ID",
            arrival_column="arrival",
            readiness_column="readiness",
            eligibility_cutoff=120,
            deadline=600,
            **context,
        ),
        "pce": process_cycle_efficiency(
            orders,
            case_id_column="Order ID",
            lead_time_column="lead_time",
            value_add_time_column="value_add",
            aggregation="cohort",
            value_add_convention=bound.policy.value_add_convention,
            **context,
        ),
    }
    return results, bound


def run(model_dir: Path, source: Path, output: Path):
    """Save a verifiable audit bundle, source snapshots and a modeled FLO rendering."""
    manifest, ir, projection, producer_report = _model(model_dir)
    profile_bytes = (HERE / "simulation_sources.json").read_bytes()
    profile = json.loads(profile_bytes)["profiles"][0]
    digest = manifest["observations"]["artifacts_sha256"]["event_log.csv"]
    if profile["expected_sha256"] != digest:
        raise ValidationError("Numeric ingestion profile disagrees with the governed source hash.")
    log = load_numeric_event_log(
        source, contract=NumericLogContract.from_dict(profile["contract"]), expected_sha256=digest
    )
    results, bound = _measure(log, projection)
    snapshots = {
        "event_log.csv": source.read_bytes(),
        "simulation_sources.json": profile_bytes,
        "observation-SOURCE_LICENSE.md": (HERE / "SOURCE_LICENSE.md").read_bytes(),
        **{
            name: (model_dir / name).read_bytes()
            for name in (
                "washnfold.flo",
                "activity-mapping.json",
                "process-export.json",
                "manifest.json",
                "SOURCE_LICENSE.md",
            )
        },
    }
    inputs = {
        name: InputReference.from_bytes(name, content, selection="Complete source artifact")
        for name, content in snapshots.items()
    }
    bundle = AnalysisBundle.capture(
        "FLO-backed White Belt book baseline",
        results=results,
        inputs=inputs,
        result_inputs={name: tuple(inputs) for name in results},
        cohort_definition=bound.policy.cohort,
        software_versions={
            name: metadata.version(name)
            for name in (
                "lss4py",
                "flo-lang",
                "polars",
                "narwhals",
                "numpy",
                "scipy",
                "pydantic",
            )
        },
        context={
            "process_projection": projection.to_dict(),
            "producer_report": producer_report,
            "policy_derivation": bound.to_dict(),
            "source_manifest": manifest,
            "numeric_contract": log.contract.to_dict(),
            "modeled_durations": "Displayed model facts only; excluded from observed arithmetic",
            "rendering": "FLO modeled value stream; no measured overlay",
        },
    )
    artifact = import_module("flo.render").render_artifact(ir, options={"diagram": "value_stream"})
    restored = AnalysisBundle.from_json(bundle.to_json())
    restored.verify_inputs(snapshots)
    output.mkdir(parents=True, exist_ok=True)
    for name, content in snapshots.items():
        (output / name).write_bytes(content)
    (output / "modeled-value-stream.svg").write_text(artifact.content)
    (output / "projection.json").write_text(projection.to_json())
    (output / "policy-derivation.json").write_text(bound.to_json())
    (output / "evidence.json").write_text(bundle.to_json())
    return restored


def main():
    """Run the frozen book profile with explicit model and destination directories."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--source", type=Path, default=HERE / "event_log.csv")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    bundle = run(args.model_dir, args.source, args.output)
    pce = bundle.get_result("pce")
    assert isinstance(pce, TimingResult)
    print(f"Cohort PCE: {pce.values[0]:.1f}%")
    print(f"Evidence: {args.output / 'evidence.json'}")


if __name__ == "__main__":
    main()
