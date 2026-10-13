# Cp, Cpk, and specification Z distance

`capability_indices` calculates normal capability indices from an eager pandas,
Polars, or provisional Arrow frame and an explicit `Specification`. It returns
`CapabilityResult`, with the specification, estimator, exclusions, assumptions,
software versions, and backend recorded in provenance.

```python
import polars as pl
from lss4py import Specification, capability_indices

spec = Specification("Length", "mm", "target", target=10, lsl=7, usl=14)
result = capability_indices(
    pl.DataFrame({"length": [8, 9, 10, 11, 12]}),
    column="length", specification=spec, ci=True,
)
assert round(result.cpk, 6) == 0.632456
print(result.cp, result.cpk, result.cpl, result.cpu)
print(result.cp_confidence_interval, result.cpk_confidence_interval)
```

## Numerical conventions

The estimator is **overall sample standard deviation**, `s`, with denominator
`n-1`, after exclusions. No subgroup or short-term variation is inferred.
Given the observed mean `m`, the components are `(m-LSL)/(3s)` and `(USL-m)/(3s)`.
Two-sided Cp is `(USL-LSL)/(6s)` and Cpk is the smaller available component.
With a single limit, both Cp and Cpk equal that component, following SixSigma's
one-sided convention. A missing component is `None`. Targets are retained as
context and do not alter these formulas. Negative Cpk is retained when the mean
lies outside a limit; it is accompanied by a diagnostic.

`ci=True` enables intervals at `confidence_level=0.95` by default. For tail
probability `a=(1-confidence_level)/2`, the Cp endpoints multiply Cp by
`sqrt(chi2_quantile(a, n-1)/(n-1))` and its upper-tail counterpart. The approximate
Cpk interval is `Cpk ± z(1-a)*sqrt(1/(9n) + Cpk²/(2(n-1)))`.
The legacy `confidence_interval` field aliases the Cpk interval.

`z_score` is the signed distance to the governing specification limit, using the
same overall sample variation: `3*Cpk - sigma_shift`. The default
`sigma_shift=0.0` applies no adjustment. `sigma_shift=1.5` matches SixSigma's
`LT=True` convention; any requested shift must be finite and nonnegative and
produces a `SIGMA_SHIFT_ASSUMED` diagnostic. It does not establish measured
long-term performance. Provenance records the shift and method; metadata's
`z_to_spec` retains the unshifted distance. Z stays unavailable when Cpk is
unavailable or Z arithmetic overflows. No observation-standardization API or Z
confidence interval is implied.

These formulas and assumptions are described in the
[NIST capability handbook](https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc16.htm).
Capability interpretation needs a stable, independent, approximately normal
process and a defensible cohort. This function records these assumptions without
testing them. Fewer than 50 retained observations produce a small-sample warning;
that threshold is a diagnostic policy, not an automatic adequacy decision.

## Input and undefined-result policy

Nulls and NaNs use `missing="omit"` by default; `missing="raise"` rejects them.
`total`, `count`, and `missing` retain the exclusion accounting. Text, booleans,
infinite measurements, absent columns, missing specification limits, and invalid
confidence levels fail with `ValidationError`. The immutable specification model
already rejects contradictory or nonfinite limits.

Fewer than two retained observations, zero variation, and numerical overflow
produce unavailable indices/intervals (`None`) with structured warnings, never
infinite capability values. Numerical outputs serialize as strict JSON.

Units must already agree with the specification; no conversion is inferred.
Select cohorts before calling the function. Specifications containing grouping or
time-window instructions are rejected to avoid silently ignoring selection rules.
The cohort label is recorded but does not filter rows. Within-subgroup
variation, non-normal methods, distribution/stability tests, plots, and full
capability studies remain future work.

## R evidence and intentional differences

`tests/test_capability.py` uses the checksummed SixSigma 0.11.1 baseline for
two-sided and upper-only Cp, offset Cpk, and both confidence intervals across all
four backend variants. It also tests lower-only formulas, signed/zero Cpk,
exclusions, unit transformations, confidence widths, invalid domains, provenance,
and input preservation. Ordinary Python tests consume JSON and do not require R.

The R baseline remains reference-only as a whole because its defect/rework yield cases have
no corresponding Python implementation. `tests/test_capability_z.py` validates
eight genuine R Z cases, including lower-only, upper-only, negative distances,
and their shifted counterparts. The reference snapshot is now version 1.1.0. Cp/Cpk compatibility is partial, with
explicit differences: Python uses retained `n` in both intervals (R Cp uses the
original vector length even after omitting missing values); Python orders signed
intervals and has a finite Cpk interval at zero; R's multiplicative Cpk expression
can reverse negative endpoints or return NaN at zero. Python returns governed
unavailable values for degenerate data and typed errors for invalid domains.
The original MIT Python formulas do not copy the GPL R implementation.
