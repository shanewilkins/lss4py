# Descriptive statistics

`describe` summarizes a numeric column from an eager Polars or pandas dataframe.
Provisional PyArrow cases are covered by the [shared backend suite](backend-contracts.md).
It returns a backend-neutral `DescriptiveResult`; no pandas dependency is needed
when using Polars. This is the descriptive slice of the v0.2 contract foundation,
not a claim that the full milestone or R SixSigma parity is complete.

```python
import polars as pl
from lss4py import describe

observations = pl.DataFrame(
    {
        "team": ["A", "A", "B", "B", "B"],
        "hours": [1.0, 2.0, 2.0, 4.0, None],
    }
)

summary = describe(observations, column="hours", unit="hours")
assert summary.mean == 2.25
assert summary.count == 4
assert summary.missing == 1
assert summary.modes == [2.0]
assert summary.percentiles["p50"] == 2.0

by_team = describe(observations, column="hours", group_by="team", unit="hours")
assert [result.group_keys for result in by_team] == [{"team": "A"}, {"team": "B"}]
assert [result.mean for result in by_team] == [1.5, 3.0]
payload = summary.to_dict()  # Also available as summary.to_json().
```

## Included statistics

- Measurement sum, mean, median, all tied repeated-value modes and their frequency.
- Minimum, maximum, range, variance, and standard deviation.
- Bias-corrected skewness and kurtosis.
- Coefficient of variation (CV), expressed as a ratio, not a percentage.
- Quartiles, interquartile range (IQR), and unscaled median absolute deviation (MAD).
- Configurable percentiles; p90, p95, and p99 are included by default.
- Total count, valid count (`count`), missing count, and unique valid-value count.

## Conventions and options

Measurements are materialized as NumPy float64 values; exact large-integer and
arbitrary-precision decimal arithmetic are not supported. The source is not mutated.
Only selected measurements and grouping keys are materialized.

`ddof=1` selects sample standard deviation and variance. Use `ddof=0` for population
spread. Variance has squared measurement units; CV, skewness, and kurtosis are
dimensionless. The `unit` label is recorded, not converted or inferred.

Skewness requires at least three valid observations and kurtosis at least four.
Shape estimates use bias corrections. `excess_kurtosis=True` uses a normal-distribution
reference of zero; `False` selects Pearson kurtosis with a reference of three.
Constant or numerically near-constant data have unavailable shape estimates.

Quartiles are always included as `p25`, `p50`, and `p75`. Supply additional levels
with `percentiles=[5, 90, 99]`; levels must be finite and between 0 and 100.
The default quantile method is linear interpolation. Explicit
`percentile_method="nearest_rank"` sorts ascending and selects one-based
`max(1, ceil(p*n))`; P0 selects the minimum. The ordinary median field still averages
the middle two for even samples. `measurement_sum` sums valid measurements;
`total` remains the original observation count. Empty/overflowed sums are
unavailable with diagnostics. MAD is the median of absolute deviations
from the median, without normal-consistency scaling.

`measurement_scale="ratio"` declares a meaningful zero, such as elapsed time.
Use `"interval"` for measurements such as Celsius temperatures, for which CV is
unavailable. CV is also unavailable when the mean is nonpositive or no greater
than `1e-12 * max(abs(valid_measurements))`. Multiply an available CV by 100 for
percentage presentation. The function cannot infer a suitable measurement scale.

When every valid value occurs once, `modes=[]` and `mode_frequency=1`, with a
diagnostic explaining that no repeated-value mode exists. No binning or density
estimation is performed for continuous measurements.

`missing="omit"` excludes nulls and NaNs, records their count, and adds a warning.
`missing="raise"` rejects them. Infinite measurements, text, and booleans are rejected
rather than silently coerced or excluded. Empty/all-missing samples return an
unavailable summary. Insufficient data and numerical failures produce `None` with
structured warnings; numerically unavailable percentile entries are omitted.

## Grouping and provenance

Without grouping the return value is one `DescriptiveResult`. With `group_by="team"`
or `group_by=["team", "shift"]`, it is a list of results in first-observed group
order, each with `group_keys`. Null/NaN identifiers form a retained missing-key
group. Scalar and date/datetime keys are supported; dates serialize as ISO strings.
Nested or infinite group identifiers are rejected. Empty grouped input returns
an empty list; an empty grouping-column selection is invalid.

Each result records backend identity, statistical options, exclusions, unit,
group keys, method/package versions, creation time, and NumPy/SciPy versions.
The summary describes observed data: it does not establish normality, stability,
capability, causality, or statistical independence. Confidence intervals and
inferential tests remain separate work.

Contract tests in `tests/test_descriptive.py` cover pandas/Polars equivalence,
hand-calculated moment references, grouping, invalid inputs, serialization,
small samples, missingness, and numerical failures. R-specific fixtures are still
future work.
