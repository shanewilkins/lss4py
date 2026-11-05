# Mean confidence interval

`mean_confidence_interval` estimates a population mean from one governed numeric
measurement column. It returns a typed `MeanCIResult`; calculation does not create
plots or mutate the source frame.

```python
import polars as pl

from lss4py import mean_confidence_interval

sample = pl.DataFrame({"cycle_minutes": [8, 9, 10, 11, 12]})
result = mean_confidence_interval(
    sample,
    column="cycle_minutes",
    unit="minutes",
    cohort="Five independently sampled completed cycles",
)

print(result.mean)
print(result.confidence_interval)
print(result.shapiro_p_value)
```

The default 95% interval is approximately `(8.0368, 11.9632)`.

## Interval policy

With unknown population variance, the method uses the sample standard deviation,
standard error \(s/\sqrt{n}\), and a Student's t critical value with \(n-1\)
degrees of freedom. Sample size alone never silently changes that policy.

Supplying `population_variance` uses its square root as the known population
standard deviation and a normal critical value. `approximate_z=True` instead uses
sample spread with a normal critical value. This approximation is explicit and
adds an `APPROXIMATE_Z` warning.

`confidence_level` must be finite and strictly between zero and one. At least two
valid measurements are required. Nulls and NaNs are omitted by default and counted
in the result; `missing="raise"` rejects them. Text, booleans, infinities and
nonfinite interval arithmetic fail validation.

## Normality diagnostic

Shapiro-Wilk is reported for nonconstant samples containing 3 through 5,000 valid
measurements. The result retains its statistic, p-value and declared
`normality_alpha`. A p-value below that threshold adds `NON_NORMAL_SAMPLE`; it
does not delete data, change the interval method, or make an automatic analytical
decision.

For unsupported sample sizes or constant measurements, Shapiro-Wilk remains
unavailable and `NORMALITY_UNAVAILABLE` explains why. Samples below 30 also carry
`SMALL_SAMPLE` to prompt review of normality and sampling assumptions.

Shapiro-Wilk addresses marginal distribution shape only. It does not establish
independence, representative sampling, process stability, practical importance,
or capability. Those assumptions remain visible in provenance and require
practitioner judgment.

## R `SixSigma` evidence

Three genuine R `SixSigma` 0.11.1 `ss.ci` cases cover unknown variance, known
population variance and the explicit z approximation. LSS4PY matches their
confidence bounds across pandas, duplicate-index pandas, Polars and PyArrow.

Unlike `ss.ci`, LSS4PY separates numerical inference from distribution evidence
and rendering. `plot_mean_interval` renders the completed estimate, while
`distribution_profile` prepares histogram, ECDF, Q-Q, box and optional density
evidence for the same governed measurement cohort. SciPy supplies the
Shapiro-Wilk diagnostic, so exact R test-statistic parity is not claimed.
