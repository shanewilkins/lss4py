# Capability studies

`capability_study` composes normal capability indices, distribution diagnostics,
and observed nonconformance for an explicitly declared short-term sample and an
optional separately declared long-term sample.

```python
import polars as pl

from lss4py import Specification, capability_study

specification = Specification(
    "Fill volume",
    "ml",
    "target",
    target=10,
    lsl=8,
    usl=12,
)

study = capability_study(
    pl.DataFrame({"value": [9.0, 10.0, 11.0, 10.0, 9.5, 10.5]}),
    column="value",
    specification=specification,
    long_term_data=pl.DataFrame({"value": [7.0, 9.0, 10.0, 11.0, 13.0, 10.0]}),
)

assert study.short_term_capability is not None
assert study.long_term_capability is not None
assert study.long_term_nonconformance["nonconforming"] == 2
```

The result retains four complete child results when both samples are supplied:

- short-term `CapabilityResult`;
- short-term `DistributionProfileResult`;
- long-term `CapabilityResult`;
- long-term `DistributionProfileResult`.

It also stores observed counts below the LSL and above the USL, their combined
count, and the observed nonconforming rate for each sample. Specification
boundaries are inclusive: only values strictly below the LSL or above the USL
are counted as nonconforming.

## Explicit sample roles

The argument names are declarations, not statistical inference. LSS4PY does not
infer subgroup structure, collection duration, process stability, independence,
or whether either sample represents its stated horizon. The caller must select
samples whose collection designs justify those roles.

Each child capability calculation currently uses sample standard deviation with
`ddof=1` over its declared sample. Therefore:

- the short-term result is the overall standard deviation of the explicitly
  supplied short-term sample;
- it is not a pooled within-subgroup estimate;
- the optional long-term result is calculated independently from its supplied
  sample;
- no sigma shift is used to manufacture a long-term estimate.

The existing normality, small-sample, constant-variation, and missingness
diagnostics remain attached to the child results. Normality evidence does not
establish independence or stability.

## Input and missingness policy

Both samples use the same selected column and `Specification`. Eager pandas,
Polars, and PyArrow inputs are accepted independently, so the two samples need
not originate from the same dataframe backend. Inputs are never mutated.

Missing values are rejected by default. Set `missing="omit"` only when exclusion
is an explicit reviewed policy; each child result records supplied, retained, and
missing counts. At least two retained finite numeric observations are required
per supplied sample.

`ci=True` is the default for the composed study. Confidence level and normality
alpha are explicit shared parameters. Audited analysis bundles recursively
validate and restore every nested result without rerunning calculations.

## Portable validation boundary

Calculation passes the declared missing policy, confidence settings, and
normality alpha to the applicable children. Each child's provenance retains
its settings; its backend and schema describe its own supplied sample. Different
sample backends are expected, not inconsistent evidence.

Portable restoration checks child types and supported schemas, retained-count
agreement, specification limits/target/units, complete optional long-term evidence,
and observed nonconformance against the retained values. Audited bundles also
check source/specification links and software context. Valid JSON or a matching
snapshot fingerprint alone does not establish those semantic checks.

Restoration does not recompute capability estimates, confidence intervals, or
diagnostics, or certify agreement of every parent/child provenance parameter.
To verify an edited study's numerical derivation and shared settings, inspect the
recorded parameters and explicitly rerun the study from verified source bytes.
Loading a bundle is evidence restoration, not independent analytical replication
or source authentication.

## R SixSigma relationship and current boundary

SixSigma 0.11.1 `ss.study.ca` accepts separate `xST` and optional `xLT` vectors,
specification limits, a target, alpha, and presentation options. It renders a
study figure and returns `NULL`; there is no structured numerical R result to
round-trip.

LSS4PY follows the explicit two-sample concept but returns reusable evidence
before presentation. This is currently partial compatibility. The following
remain open:

- a composed result-only capability-study figure comparable in purpose to the R
  plot;
- pooled within-subgroup or other governed short-term variation estimators;
- transformations and non-normal capability methods;
- an independent stability decision;
- visual-reference acceptance for the complete study artifact.
