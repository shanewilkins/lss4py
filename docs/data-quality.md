# Validate and prepare analytical data

`validate_data(data, *, contract, source_units=None)` inspects an eager pandas,
Polars, or provisional PyArrow table and returns an immutable, versioned
`DataValidationReport`. It never changes source values, removes rows, chooses an
analysis, or changes an existing calculation's validation policy.

## Declare the checks

A `DataContract` contains `ColumnRule` objects, explicit key columns, optional
ordered timestamp pairs, and a duplicate policy (`warn`, `error`, or `allow`).
Contracts serialize with `to_dict()` and restore with `DataContract.from_dict()`;
unknown fields and unsupported versions fail explicitly.

Each column rule declares a kind (`numeric`, `integer`, `string`, `boolean`, or
`timestamp`), nullable policy, optional numeric bounds, and optional expected unit.
Extra source columns appear in the report's column names but are not checked.
Observed column names must be unique strings. Unsupported and lazy inputs raise
`TypeError` before inspection; invalid contracts raise `ValidationError`.

The report contains logical schema profiles, total/missing/distinct/invalid
counts, the complete contract, backend identity, version, and structured issues.
`report.valid` means no blocking issues were found by the **declared checks**.
It does not establish statistical assumptions or suitability for a particular
analysis. `report.errors` and `report.warnings` expose issues separately.
Issue codes, affected columns, and zero-based source row positions are reusable;
pandas index labels never define identity. `to_json()` emits strict JSON.

| Check | Policy |
| --- | --- |
| Missing columns / empty tables | Blocking findings |
| Native nulls, NaNs, and NaT | One portable missing category; never stringified |
| Missing values | Blocking by default; `nullable=True` warns; missing keys always block |
| Numeric values | Real numbers only; no text or boolean coercion; infinity blocks |
| Integer values | Exact integers; integral floats accepted within ±2**53 |
| Numeric bounds | Inclusive minimum/maximum; invalid domains block |
| Strings | Nonblank strings; no trimming or stringification |
| Timestamps | Native datetime or ISO date-and-time string; invalid values block |
| Timezones | Aware values compare in UTC; mixed naive/aware values block |
| Ordered time pairs | Completion before start blocks; equal times are allowed |
| Duplicates | Later occurrences of declared composite keys; without keys, all declared columns define identity |
| Units | Compare explicit source and expected labels; unknown units warn and mismatches block |

Missingness combines nulls and NaNs because pandas may represent both as NaN.
Logical schemas avoid accidental dependence on backend dtype names. Numeric keys
compare numerically, so integer/float promotion does not change duplicate identity.
Distinct counts exclude invalid and missing scalars. Rows with blocking scalar
findings are excluded from duplicate comparisons, so failed parsing cannot create
phantom duplicate keys. A row can contribute to
multiple column findings; issue counts must not be added to infer unique bad rows.
Nested/object values outside the declared scalar kinds produce type findings.
Timestamp inspection uses microsecond precision, matching normalization, including
for distinct counts, duplicate identity and ordered time comparisons.

## Opt-in normalization

`normalize_data(data, *, contract, source_units=None, drop_missing=False,
drop_duplicates=False)` uses the same inspection engine and returns `NormalizedData`.
It copies **only declared columns** to eager canonical Polars, converts missing
values to nulls, materializes integral columns as integers, and parses declared
timestamps at microsecond precision. Aware timestamps become UTC; naive values
retain their wall time. Sub-microsecond precision is not preserved. Numeric text
and units are never converted. Mixed integer/real numeric columns use common float
storage only when the integers can be represented exactly; otherwise normalization
raises `ValidationError` rather than silently rounding them.

Rows remain in original order. Missing-row exclusion occurs first, and optional
deduplication keeps the first surviving occurrence. These options apply to all
declared columns and declared key/row identity respectively. No other error is
repaired by exclusion; invalid domains, incompatible units, mixed timezones, and
reversed intervals block preparation even if a different field on that row is
missing. Dropping every row also fails. Very large exact integers may inspect
successfully but fail canonical Polars storage with an explicit `ValidationError`.

The result retains the before/after reports, deterministic transformation policy,
and original `source_rows`. Use `to_polars()` for an independently mutable copy;
`to_dict()` / `to_json()` export evidence separately from the frame. Normalization
materializes Python scalar columns and a new Polars frame; no zero-copy promise
is made. Ordinary calculation APIs still accept their existing native backends.

## Reproducible example

Original synthetic inspection records contain one missing duration and a repeated
identifier. This example explicitly chooses to exclude the missing observation
and retain the first complete observation for each identifier.

```python
import polars as pl
from lss4py import ColumnRule, DataContract, describe, normalize_data, validate_data

observations = pl.DataFrame({
    "id": ["a", "b", "a", "c"],
    "hours": [1.0, None, 2.0, 3.0],
})
contract = DataContract(
    (ColumnRule("id", "string"), ColumnRule("hours", nullable=True, minimum=0, unit="hours")),
    key_columns=("id",),
)
report = validate_data(observations, contract=contract, source_units={"hours": "hours"})
assert report.valid
assert {issue.code for issue in report.warnings} == {"MISSING_VALUES", "DUPLICATE_ROWS"}
prepared = normalize_data(
    observations, contract=contract, source_units={"hours": "hours"},
    drop_missing=True, drop_duplicates=True,
)
assert prepared.source_rows == (0, 3)
summary = describe(prepared.to_polars(), column="hours", unit="hours")
assert summary.count == 2 and summary.mean == 2
```

The cross-backend suite executes these policies, while the installed-wheel journey
reads original `e2e/fixtures/quality.csv`, checks ordered timestamps, prepares the
selected rows, runs `describe`, and exports strict JSON. Existing interval-log
validation and analytical formulas remain independent contracts. Distribution
suitability tests, normality diagnostics, automated unit conversion, and general
study-bundle reconstruction remain future work.
