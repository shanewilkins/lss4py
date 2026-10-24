# Auditable analysis bundles

The prepared-data preview adds `deadline_performance` results using `YieldResult`
and cohort PCE using `TimingResult`, preserving eligibility populations and sum
derivations in metadata. `DescriptiveResult.measurement_sum` is an additive field:
older saved descriptive results without it restore with an unavailable sum.
See the [preview evidence](../examples/white_belt/preview-bundle.json).

`AnalysisBundle.capture(...)` exports the seven current analytical result families
with explicit source references, selections, software versions and specification
links. `AnalysisBundle.from_json()` reconstructs their real domain models; loading
never executes an analysis, resolves a path, imports a named method, or fetches data.

## Capture an analysis

This original synthetic example stores a mean with its input identity. The source
bytes define the three observations; the cohort and selection are explicit.

```python
from importlib.metadata import version
from io import BytesIO
import polars as pl
from lss4py import AnalysisBundle, InputReference, describe

source = b"hours\n1\n2\n3\n"
data = pl.read_csv(BytesIO(source))
summary = describe(data, column="hours", unit="hours")
bundle = AnalysisBundle.capture(
    "Synthetic baseline",
    results={"summary": summary},
    inputs={
        "measurements": InputReference.from_bytes(
            "measurements.csv",
            source,
            selection="all three source rows",
            media_type="text/csv",
        )
    },
    result_inputs={"summary": ["measurements"]},
    cohort_definition="Original three-observation synthetic example",
    software_versions={
        name: version(name) for name in ("lss4py", "numpy", "scipy", "narwhals", "polars")
    },
    context={"observation_order": "source row order", "exclusions": []},
)
saved_json = bundle.to_json()
restored = AnalysisBundle.from_json(saved_json)
restored.verify_inputs({"measurements": source})
assert restored.get_result("summary").mean == 2
```

`results` maps stable caller-supplied ids to computed results. `result_inputs` must
link every result to one or more declared input ids. `InputReference` records a
reference, SHA-256 of exact bytes, selection description and media type. References
are opaque identifiers: bundle methods do not read or write them. Callers retain
the original artifacts and explicitly supply bytes when verifying them.

For capability results, pass typed `specifications={"ctq": specification}` and
`result_specifications={"capability": ["ctq"]}`. The saved specification must
match the declaration in the result's parameters, including unit, target and
acceptance limits. Specification objects and observation windows restore as their
validated domain types. Grouped summaries can use a separate id for each group.

Software context must include `lss4py`, NumPy, Narwhals, and every result's recorded
input backend. NumPy/SciPy/Narwhals versions present in result metadata must agree
with the bundle context. Record other relevant dependencies, the environment or
lockfile reference, process model artifacts, cohort rules, timezone policy and
exclusion reasons as applicable. `context` accepts finite JSON, including the
preparation evidence returned by `NormalizedData.to_dict()`; its application-specific
contents are preserved rather than interpreted as executable instructions.

Capture takes detached copies. Changing the caller's original result or exported
dictionary cannot alter the captured bundle. The bundle object itself remains
editable like existing result models; each export creates a newly validated snapshot.
Use a new export/revision when editing saved evidence.

## Versioned wire format

Audited bundles use `bundle_version="2.0"`. Each named result entry has its own
`schema_version="1.0"`, complete typed payload, input ids and specification ids.
The payload preserves estimates, units, arrays and keys, bucket counts, confidence
intervals, missingness counts, group identities, parameters, provenance timestamps,
method/package versions, assumptions and warnings. Result reconstruction supports
`TimingResult`, `YieldResult`, `DefectYieldResult`, `DescriptiveResult`, and
`CapabilityResult`. Their inherited `from_dict()` method also restores standalone
result payloads; an incompatible requested subclass is rejected.

Exports use finite, deterministic JSON with sorted object keys; result identifiers
provide identity, while observation arrays retain their original order and scalar
key types. A SHA-256 over the canonical body excluding `sha256` detects accidental
snapshot changes. `verify_inputs` separately detects changed or missing source bytes.
Hashes do not establish authorship or prove a numerical conclusion.

Validation rejects unknown schema versions, unknown/missing fields, duplicate JSON
object members, nonfinite/nonportable values, missing software context, dangling or
duplicate artifact links, wrong result/method combinations, inconsistent sample
counts, unaligned timing keys, reversed confidence intervals, contradictory defect
count ratios and specification mismatches. It does not recompute statistical
estimates or establish that a supplied artifact contains the declared population.

## Validate without analytical dependencies

The package API `validate_bundle(saved_json_or_dict)` returns detached validated
JSON data and raises `ValidationError` on invalid evidence. The same validator is
packaged as one self-contained standard-library script:

```bash
python -I -S src/lss4py/_bundle_schema.py study.bundle.json
```

A reviewer can copy that script next to the bundle and run it with Python 3.14
without installing LSS4PY, NumPy, pandas, Polars, plotting or document libraries.
It prints the format version, result count and whether the bundle is audited;
invalid files exit with code 1. Its standalone error type is `BundleValidationError`,
a `ValueError` subclass. The installed-wheel journey runs this script with site
packages disabled, so no analytical runtime participates in validation.

## Legacy format and migration

Direct `AnalysisBundle(name, results, ...)` construction retains the original v1
format for compatibility. Version 1.0 now restores actual typed results instead
of silently returning an empty list. It preserves legacy metadata, timestamps and
original package-version labels, including historical labels that differed from
the results. It has no source hash or required audit context and `audited` is false.

`legacy.with_audit_context(inputs=..., result_inputs=..., cohort_definition=...,
software_versions=..., ...)` explicitly upgrades it to v2. Results receive ids
`result-0`, `result-1`, etc. Original bundle creation/version/cohort/specification
metadata is retained in `context["legacy_bundle_context"]`, and migration origin
is recorded in metadata. The caller supplies the missing source artifacts and
selection/software evidence; the loader never invents those. Unknown future
versions are rejected until a reviewed migration is implemented.

## Explicit rerun

First load and validate the bundle, then verify caller-supplied source snapshots.
The caller deliberately loads those artifacts, reconstructs any preparation or
process-model context, and calls a chosen public method using saved parameters
and linked specifications. Compare numerical outputs while accounting for the
new computation timestamp and possibly different input backend.

The installed-wheel example reads `e2e/fixtures/measurements.csv`, captures a summary
and capability indices, validates the saved bundle in a standard-library-only
process, restores the typed results, verifies source bytes and explicitly reruns
the capability calculation. Existing FLO `EvidenceManifest` retains its own
process/annotation envelope and reuses the shared timing-result restoration path.

`OrderReconstructionResult` also supports portable restoration and audited capture.
It retains ordered source, per-record timing, collapsed activity/pass and complete
order tables, along with the explicit accounting policy and ingestion provenance.
See [order reconstruction](order-reconstruction.md).

`ProcessMapResult` preserves typed direct-follow counts and source evidence, with
legacy nodes/edges lookup and an explicit `.to_mapping()` export. Current results
also record runtime and backend versions in provenance; audited capture rejects
conflicting supplied software context. Historical payloads lacking that additive
context remain readable without inventing it.
