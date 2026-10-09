# Analysis guidance

`get_candidates` lists analytical methods matching caller-declared intent.
`get_analysis` explains a named method. Both return immutable
`AnalysisSuitability` metadata, never calculations or observed-data diagnostics.
The catalog covers the eight supported timing, yield, and descriptive functions.

```python
import polars as pl
from lss4py import describe, get_analysis, get_candidates

candidates = get_candidates(
    "summarize_measurements", data_type="numeric", design_type="observational",
)
assert [entry.name for entry in candidates] == ["describe"]
for entry in candidates:
    print(entry.prerequisites, entry.assumptions, entry.limits)

# The practitioner reviews the guidance and explicitly calls the chosen method.
result = describe(pl.DataFrame({"hours": [2, 4, 6]}), column="hours", unit="hours")
assert result.mean == 4
metadata = get_analysis("describe").to_dict()
assert metadata["belt_level"] == "white"
```

## Questions and filters

| Question tag | Candidates | Data type | Design type |
| --- | --- | --- | --- |
| `summarize_measurements` | `describe` | `numeric` | `observational` |
| `elapsed_time` | `lead_time` | `timestamps`, `interval_event_log` | `observational` |
| `waiting_time` | `wait_time` | `numeric_duration` | `observational` |
| `value_add_share` | `process_cycle_efficiency` | `numeric_duration` | `observational` |
| `demand_pace` | `takt_time` | `scalar` | `planning` |
| `stage_conversion` | `booked_to_completed_yield`, `created_to_booked_yield` | `binary_stage_outcome` | `observational` |
| `overall_conversion` | `rolled_yield` | `binary_stage_outcome` | `observational` |

All filters use exact tags. Omitted filters match any registered value;
`get_candidates()` enumerates the catalog in alphabetical method order. Unknown
tags return an empty tuple, while blank/non-string filters fail validation.
Unknown method names passed to `get_analysis` fail explicitly.

Metadata includes family, questions, belt level, semantic field requirements,
data types, design types, prerequisites, assumptions, alternatives, and limits.
Each tuple within `required_fields` represents an alternative sufficient input
path. These are semantic roles, not literal source column names. Lead time has
separate timestamp-pair and process-bound interval-log paths. Wait time and
process-cycle efficiency currently require explicit measurement columns; guidance
does not advertise branch-aware interval-log inference for those methods.
There are no predictor requirements for these eight calculations.

A match identifies a candidate for review. It does not validate source schema,
sampling design, units, sample size, or assumptions. Each analysis retains its
own validation and provenance. Guidance does not infer a question from data,
rank candidates, pick a method, filter a cohort, or record a selection on the
caller's behalf. Keep guidance metadata alongside the explicitly chosen method's
result if it helps your review; no new bundle schema is implied.

## Adding methods

Declare `AnalysisSuitability` with `@register_analysis` from `lss4py.guidance` on
an implementation function. The decorator registers metadata, checks matching
and unique method names, and returns the original function unchanged. Metadata
has no callable references. Public built-in calculations are imported by the
package root, which makes the catalog available before queries. There is no
plugin discovery, dynamic loading, or public registry mutation API.

These pre-1.0 tags may evolve as analytical workflows expand. Registry tests
cover completeness, declared questions, filters, immutable copies, invalid
metadata, duplicate registrations, and non-execution. Import-linter forbids the
guidance layer from importing calculations, adapters, workflows, or IO layers.
