# Defect and rework yield

`process_yield(data, *, defects_column="defects", rework_column=None,
opportunities=..., units=None)` returns a versioned `DefectYieldResult` without
rendering. Eager pandas, Polars, and provisional PyArrow inputs share the same
counting contract. Binary funnel APIs keep their existing behavior.

## Counting contract

Each row is an aggregate counting bucket in one declared population. Defects and
rework align by row position, never by a pandas index. Counts must be finite,
nonnegative integers; integral floats up to 2**53 are accepted. Integer columns
retain exact counts beyond that range. Nulls, NaNs, text, booleans, fractional
counts, empty tables, absent columns, and ambiguous column roles are rejected.
Defect and rework column names must be distinct. Omitted rework means zero;
select a rework column explicitly to include it. No rows are silently excluded.

`opportunities` is the **total shared opportunity population**, not opportunities
per unit and not the number of rows. Supply it explicitly as a positive integer.
For example, 5 units with 4 opportunities each have 20 total opportunities. Each
failed opportunity is counted once; rework losses must exclude losses already
counted as defects. The combined defect/rework count cannot exceed opportunities.
The caller must establish that losses are disjoint; aggregates cannot verify it.
This contract does not accept arbitrary repeated defect incidents per opportunity.

`units`, when provided, is a positive explicit denominator for defects per unit.
It does not alter Yield, FTY, RTY, or DPMO. Multiple failed opportunities on one unit
are permitted; the result cannot infer the number of defective units. These
opportunity fractions are unit yields only when the caller's counting design
makes that interpretation valid.

## Formulas and R mapping

For opportunity total N, bucket defect counts d_i and rework counts r_i:

| Result | Formula | SixSigma field |
| --- | --- | --- |
| `yield_fraction` | (N - sum(d_i)) / N | Yield |
| `first_time_yield` | (N - sum(d_i) - sum(r_i)) / N | FTY |
| `bucket_first_time_yields[i]` | (N - d_i - r_i) / N | RTY factor |
| `rolled_throughput_yield` | product of bucket FTYs | RTY |
| `defect_count` | sum(d_i) | DPU (legacy count) |
| `dpmo` | sum(d_i) / N * 1,000,000 | DPMO |
| `defects_per_unit` | sum(d_i) / units, or unavailable | No equivalent |

The implementation uses Python integer reductions, division, and `math.prod`,
following the small domain formulas in
[SixSigma ss.ca.yield](https://emilopezcano.github.io/SixSigma/reference/ss.ca.yield.html)
and ADR-0020. No additional numerical dependency is needed.

The bucket-product RTY is the retained R counting estimate. It depends on bucket
partitioning and is not an observed probability that a unit survives sequential
stages. Actual stage-throughput analysis needs a declared cohort and stage design;
this API does not infer those from aggregate counts. A provenance warning records
this limit on every result. All yields are fractions, not percentages.

Intentional R differences: Python rejects zero opportunities, missing or invalid
counts, and combined loss above N instead of returning nonfinite or negative
fractions. A single frame enforces equal column lengths, so R vector recycling
cannot occur. R's `DPU` is mapped to `defect_count`, never silently treated as a
rate. Typed results include the optional actual rate and all denominators.

## Reproducible example

Original synthetic counts: 5 inspected units, each with 4 opportunities; buckets
represent three disjoint failure categories, with rework recorded separately.

```python
import json
import polars as pl
from lss4py import process_yield

counts = pl.DataFrame({"defects": [2, 1, 0], "rework": [1, 0, 2]})
result = process_yield(counts, rework_column="rework", opportunities=20, units=5)
assert result.yield_fraction == 0.85
assert result.first_time_yield == 0.70
assert round(result.rolled_throughput_yield, 5) == 0.72675
assert result.dpmo == 150000
assert result.defects_per_unit == 0.6
json.dumps(result.to_dict(), allow_nan=False)
```

Results retain aligned bucket counts, bucket FTYs, schema version, method version,
backend, column choices, missingness policy, assumptions, and interpretation.
`tests/test_defect_yield.py` executes this example across eager backends and checks
genuine R references. The installed-wheel study reads CSV counts and exports JSON
in isolated base and pandas-extra installations.
