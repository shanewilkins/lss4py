# White Belt prepared-data preview

The [rendered preview](../examples/white_belt/preview.html) reproduces the adopted
Wash n' Fold baseline using public lss4py calculations:

| Measure | Result |
| --- | --- |
| Mean operating lead time, all 39 orders | 662.6 min |
| Nearest-rank P90, 21 eligible orders | 676.2 min |
| Fixed-deadline promise misses | 6/21 (28.6%) |
| Cohort PCE, all 39 orders | 13.7% |

The source is **prepared order summaries**, pinned as `washnfold-friday91` v1.0.0.
The supplied CSV and source license are beside the example. Its hash is checked
before analysis. No sibling repository, simulation, OCEL conversion, or calendar
timestamp conversion is needed. These are synthetic teaching observations.

The supplied preparation now uses `CSVTabularAdapter` with explicit string/numeric
column declarations and the pinned source hash, followed by order consistency
validation. Its ingestion transformations are retained in the audited bundle.
The broader [simulation ingestion guide](simulation-ingestion.md) covers the
raw activity/lifecycle and aggregate sources separately.

Run the [complete example](../examples/white_belt/preview.py) in the locked environment:

```bash
uv run --locked python examples/white_belt/preview.py
```

The [executed notebook](../examples/white_belt/preview.ipynb) supplies and validates
the data in its preparation cell and shows the short calculation cell. The
[Quarto excerpt](../examples/white_belt/preview.qmd) provides the corresponding
chapter-ready content. The book build executes the supplied preparation; learners
do not need to write setup code. Bindings and conventions remain inspectable.

`tools/render_book_preview.py` executes the actual public-API example and regenerates
the HTML, notebook, excerpt and [audited bundle](../examples/white_belt/preview-bundle.json).
The bundle links every result to the prepared CSV and records its hash, selections,
software versions, contract, validation findings, clock, boundary, and VA policy.
Descriptive summaries retain their own all-order or eligible cohort definitions.

## Prepared-order contract

`OrderSummaryContract` declares case, arrival, readiness, lead-time and VA columns,
unit, clock, boundary, cohort and VA convention. Processing/wait/setup bindings are
optional, but must be declared together. `validate_order_summary` returns the
existing structured `DataValidationReport`; callers retain the semantic contract
with it. Validation does not alter or exclude rows.

Checks cover unique nonmissing string case IDs; finite nonnegative numeric times;
readiness >= arrival; lead = readiness - arrival; VA <= lead; and, when supplied,
processing + waiting + setup = lead. Equality comparisons use an explicit absolute
tolerance (default 1e-8 input units) with no relative tolerance. Empty cohorts and
invalid observations produce blocking findings with source-row positions.

Every time column must already use the declared unit and operating clock. Numeric
times are never parsed as dates. Calendar `lead_time` now rejects numeric endpoints
instead of silently interpreting them as tiny calendar offsets. Numeric event-log
reconstruction remains v0.3 work. The existing `wait_time` residual calculation is
not used as the book's activity waiting formula.

## Summary, promise and efficiency contracts

`describe(..., percentile_method="nearest_rank")` selects ascending one-based
`max(1, ceil(p*n))`, where p is the percentile fraction. P0 selects the minimum.
The default remains linear interpolation. The independent `median` field always
averages the middle two for even samples, even if nearest-rank P50 selects the
lower one. `measurement_sum` is the sum of retained measurements; `total` retains
its existing meaning of original observation count. Empty or overflowed sums are
unavailable, with diagnostics. Saved descriptive results without the new sum
field still restore with `measurement_sum=None` rather than a fabricated value.
Optional `cohort`, `clock` and `boundary` declarations must be supplied together.

`deadline_performance` accepts explicit case/arrival/readiness bindings, numeric
cutoff/deadline and shared semantic context. It returns a `YieldResult` whose
numerator is misses, denominator is eligible orders, and value is the miss
fraction. Eligibility is arrival <= cutoff; a miss is eligible readiness >
deadline. Equality with the deadline is on time. Metadata retains eligible,
missed, on-time and ineligible case identities separately. Missing/invalid cases
and an empty eligible denominator fail explicitly; no success-shaped zero is
returned for an undefined rate.

`process_cycle_efficiency(..., aggregation="cohort")` uses the same validated
case population for both sums. Explicit case/lead/VA bindings, unit, clock,
boundary, cohort and VA convention are required. Its `TimingResult` contains one
aggregate value, the observation count, full source case IDs, both time sums,
ratio-of-sums convention and no silent exclusions. Individual zero-lead/zero-VA
cases can contribute to a positive cohort denominator; a zero total denominator
is undefined. The default per-row API remains available.

For this fixture, VA is right-first-time Wash, Dry, Fold and package, and readiness
notification processing. Staging is RNVA; failed packaging attempts and corrections
are NVA. Setup and waiting are outside VA. PCE is 100 * 3535.3 / 25840.5 = 13.7%
when displayed to one decimal, rather than the unweighted mean of row percentages.

## Delivery boundary and verification

The standalone preview, chapter excerpt, notebook and rendered output are supplied
here. The sibling book uses the official lss4py release selected by its lockfile;
its published Chapter 9 has not been changed to require these unreleased API
additions. Publication integration requires releasing the package and updating
that book dependency through its ordinary release process. No local source
override is introduced into the book environment.

The public prepared-data slice has backend, cutoff/deadline equality, nearest-rank
counterexample, missing/invalid input, ratio-of-sums, serialization and pinned
fixture tests. Installed-wheel workflows execute both notebook cells with the
supplied data and compare saved output. The separate [activity-to-order reconstruction](order-reconstruction.md) now
reproduces every pinned order and retains load/pass/classification and correction
evidence. Book publication requirements remain Partial until the official release
and book dependency update.

Current 0.2.0 candidate verification passes 1,750 tests with five deferred
branch-metric expected failures and 95.22% coverage, with Arrow required.
Installed base/pandas/storage/ecosystem journeys verify the standalone notebook
and full route. See the [source-fingerprinted acceptance snapshot](assessments/v02-release-gates.json)
for current exact gate results.
