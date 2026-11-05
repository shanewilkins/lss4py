# Distribution profile and diagnostic plots

`distribution_profile` prepares reusable evidence for reviewing one governed
numeric measurement column. It returns a typed `DistributionProfileResult`;
calculation does not create plots or mutate the source frame.

```python
import polars as pl

from lss4py import distribution_profile
from lss4py.reporting import plot_ecdf, plot_histogram, plot_qq

sample = pl.DataFrame(
    {
        "case_id": ["A", "B", "C", "D", "E", "F"],
        "cycle_minutes": [8, 9, 10, 11, 12, 30],
    }
)
profile = distribution_profile(
    sample,
    column="cycle_minutes",
    key_column="case_id",
    histogram_bins="sturges",
    density=True,
    unit="minutes",
    cohort="Six completed cycles",
)

plot_histogram(profile, density=True, show_kde=True)
plot_ecdf(profile)
plot_qq(profile)
```

The result retains exact valid observations, zero-based source positions and,
when requested, validated unique keys. Nulls and NaNs are omitted and counted by
default; `missing="raise"` rejects them. Text, booleans, infinities and samples
with fewer than two valid measurements fail validation.

## Prepared evidence

The profile owns all statistical preparation needed by its renderers:

- explicit histogram edges, counts and density heights;
- ordered ECDF values and rank probabilities;
- normal Q-Q coordinates and a fitted reference line;
- linear quartiles, IQR fences, whiskers and flagged observation identity;
- bias-corrected skewness and excess kurtosis when defined;
- bounded Shapiro-Wilk evidence; and
- an optional Gaussian KDE grid with its resolved bandwidth.

`histogram_bins` accepts a positive integer or `auto`, `fd`, `doane`, `scott`,
`rice`, `sturges` or `sqrt`. The stored histogram density is
`count / (valid_count * bin_width)`.

The default anomaly policy is Tukey's IQR rule with multiplier `1.5`.
`outlier_method="none"` disables fences and flags. Flags are prompts for
investigation; they do not exclude observations from any profile evidence.

Shapiro-Wilk is advisory for nonconstant samples containing 3 through 5,000
valid measurements. It does not choose a method or establish independence,
stability, capability or representative sampling. Constant data retain the
evidence that remains meaningful while shape, Shapiro-Wilk and KDE add explicit
unavailability warnings.

## Rendering contract

The optional visualization extra provides:

- `plot_histogram(profile, density=False, show_kde=False)`
- `plot_ecdf(profile)`
- `plot_qq(profile)`
- `plot_box(profile)`
- `plot_mean_interval(mean_result)`

Each function returns a native Matplotlib `Axes` and accepts a caller-owned
`ax`. Matplotlib is the public object contract; Seaborn supplies local styling
only. Renderers use stored arrays and do not select bins, sort observations,
estimate density, fit Q-Q lines, calculate intervals, test normality or detect
outliers. Requesting a KDE overlay without prepared KDE evidence fails
explicitly.

Install rendering dependencies with:

```bash
uv pip install "lss4py[visualization]"
```

## Evidence sensitivity

Serialized `values`, ECDF coordinates and Q-Q observed coordinates reproduce the
valid source measurements. Keys and source positions can identify their source
rows. Treat saved profiles and analysis bundles according to the same access,
retention and disclosure policy as the underlying measurements.
