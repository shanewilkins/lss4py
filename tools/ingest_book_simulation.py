"""Ingest declared current White Belt simulation sources without running or reconstructing them."""

import argparse
import json
from pathlib import Path

from lss4py import CSVTabularAdapter, DataContract, NumericEventLogCSVAdapter, NumericLogContract


def ingest(source: Path, profile: dict) -> dict:
    """Load one declared observation family and retain its evidence."""
    path = source / profile["filename"]
    if profile["category"].startswith("numeric_"):
        value, schema = NumericEventLogCSVAdapter(
            path,
            contract=NumericLogContract.from_dict(profile["contract"]),
            expected_sha256=profile.get("expected_sha256"),
        ).load()
        frame = value.to_polars()
        context = value.contract.to_dict()
    else:
        frame, schema = CSVTabularAdapter(
            path,
            contract=DataContract.from_dict(profile["contract"]),
            expected_sha256=profile.get("expected_sha256"),
            clock=profile.get("clock"),
        ).load()
        context = profile["contract"]
    if schema.validation is None:
        raise ValueError("Ingestion did not supply validation evidence.")
    return {
        "source": profile["filename"],
        "category": profile["category"],
        "rows": frame.height,
        "columns": frame.columns,
        "dtypes": {n: str(t) for n, t in frame.schema.items()},
        "source_sha256": schema.source_sha256,
        "transformations": schema.transformations,
        "clock": schema.clock,
        "contract": context,
        "validation": schema.validation.to_dict(),
        "exclusions": [],
    }


def main() -> None:
    """Exercise every selected source and write an inspectable ingestion manifest."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=root.parent / "modern-process-improvement/data/washnfold"
    )
    parser.add_argument(
        "--profiles", type=Path, default=root / "examples/white_belt/simulation_sources.json"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    configuration = json.loads(args.profiles.read_text())
    entries = [ingest(args.source, profile) for profile in configuration["profiles"]]
    payload = {
        "profile_version": configuration["profile_version"],
        "source_directory": str(args.source.resolve()),
        "purpose": (
            "Ingestion evidence only; no lifecycle pairing, order reconstruction, "
            "simulation or causal analysis"
        ),
        "sources": entries,
    }
    if args.output:
        args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    for entry in entries:
        print(f"{entry['source']}: {entry['rows']} rows ({entry['category']})")


if __name__ == "__main__":
    main()
