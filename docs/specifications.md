# CTQs and specifications

`Specification` defines a critical-to-quality (CTQ) measurement and what good
performance means. It is an immutable, backend-neutral domain model supporting
UR-018 / TR-021. It declares analytical intent; it does not classify defects,
calculate capability, filter observations, convert units, or execute analyses.

```python
from datetime import UTC, datetime

import polars as pl
from lss4py import AnalysisWindow, Specification, describe

spec = Specification(
    name="Order completion time",
    unit="hours",
    direction="lower",
    target=4,
    usl=8,
    defect_definition="An order taking more than 8 hours to complete.",
    opportunity_definition="One completed order.",
    opportunities_per_unit=1,
    group_by=("team",),
    cohort="Orders completed in January 2026",
    time_window=AnalysisWindow(
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 2, 1, tzinfo=UTC),
    ),
    decision_context="Assess whether completion times meet the customer promise.",
)

# The caller prepares the declared cohort/window explicitly before analysis.
observations = pl.DataFrame({"team": ["A", "A", "B"], "hours": [2, 8, 4]})
summaries = describe(
    observations,
    column="hours",
    unit=spec.unit,
    group_by=spec.group_by,
)
assert [result.mean for result in summaries] == [5.0, 4.0]
assert [result.unit for result in summaries] == ["hours", "hours"]

# Pair the reusable contract with results without inserting a dataframe object.
review_payload = {
    "specification": spec.to_dict(),
    "results": [result.to_dict() for result in summaries],
}
restored = Specification.from_json(spec.to_json())
assert restored == spec
```

The review payload above is a plain dictionary, not a new governed analysis-bundle
schema. Automatic specification integration with analyses is later work.

## Fields and validation

| Field | Meaning and rules |
| --- | --- |
| `name`, `unit` | Required nonblank CTQ name and measurement unit. Use a label such as `ratio` or `count` for dimensionless/count data. |
| `direction` | `lower`, `higher`, or `target`. The `target` direction requires a nominal target. Direction does not infer specification limits. |
| `target` | Optional finite nominal value, inside any declared limits; may equal a boundary. |
| `lsl`, `usl` | Optional inclusive lower/upper specification limits in the declared unit. When both exist, `lsl < usl`. |
| `defect_definition` | Optional nonblank operational definition of a defect. Recorded as text, not parsed or executed. |
| `opportunity_definition` | Optional nonblank description of what counts as a defect opportunity. |
| `opportunities_per_unit` | Optional positive integer, requiring an opportunity definition. Omit for variable denominators; no denominator of one is inferred. |
| `group_by` | Unique, nonblank grouping-column names. Lists are copied into an immutable tuple; a bare string is rejected. |
| `cohort` | Optional nonblank population/cohort description. |
| `time_window` | Optional immutable `AnalysisWindow`; no timestamp-column binding or filtering is inferred. |
| `decision_context` | Optional nonblank explanation of the decision the analysis informs. |
| `schema_version` | Currently `1.0`; unsupported versions fail validation. |

For targetless one-sided specifications, declare only `lsl` or `usl`, with direction
`higher` or `lower` as appropriate. Targetless two-sided specifications are also
supported with either direction. A CTQ can be defined before any limits or target
are known; such a declaration is not sufficient for a later capability study.
Lower/higher direction can coexist with either bound (for example, a minimum
safety constraint alongside a desire to reduce a measurement).

Numbers are normalized to finite Python floats. Booleans, numeric strings, NaN,
and infinity are rejected. Exact decimal and arbitrary-precision arithmetic are
not supported. Units are labels: the model cannot check dimensional equivalence
or reconcile a free-text defect definition with numeric limits.

Specification limits describe acceptance requirements. **Control limits describe
observed statistical process behavior and do not belong in this model.** There
are no `lcl`/`ucl` fields, and deserialization rejects them rather than silently
discarding them.

## Observation windows

`AnalysisWindow(start=..., end=...)` declares a half-open interval `[start, end)`.
Either endpoint may be omitted, but not both. If both exist, start must precede
end. Both must be datetimes with compatible timezone awareness; timezone-aware
endpoints are compared by instant. Naive timestamps are permitted without any
implied timezone. ISO serialization preserves each declared offset.

This is distinct from the earlier mutable `ProcessWindow` type; existing callers
are unchanged. The specification requires the validated `AnalysisWindow` type.

## Serialization and reuse

Use `to_dict()` / `from_dict()` or `to_json()` / `from_json()`. The exported object
includes `schema_version`, grouping lists, and ISO timestamps, with no dataframe,
plotting, or reporting objects. Constructor validation also runs on restored
objects. Unknown fields and unsupported schema versions are rejected. For direct
dictionary construction, omitting `schema_version` uses the current `1.0` default.
Serialized data never becomes executable filtering or analysis instructions.

Both models are frozen. Modifying input grouping lists or exported dictionaries
does not alter an existing specification; use `dataclasses.replace` to construct
and validate an intentional revision.

Reuse the declared unit/grouping explicitly when calling
[`describe`](descriptive-statistics.md). Retain the serialized specification with
results for review. Other methods do not yet accept `specification=` or perform
automatic conformance checks. Tests in `tests/test_specification.py` cover bounds,
opportunities, immutable copies, timezone windows, versioning, and round trips.
