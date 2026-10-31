# Explicit duration conversion

`convert_duration_columns` prepares selected duration columns before analysis.
It accepts eager pandas/Polars frames and PyArrow tables and returns a
`DurationConversion` containing the same native backend and portable evidence.
Existing validation, normalization and numerical functions do not start
converting units implicitly.

```python
import polars as pl
from lss4py import convert_duration_columns, describe

source = pl.DataFrame({"case": ["001", "002"], "duration": [1.5, 2.0]})
converted = convert_duration_columns(
    source,
    columns=["duration"],
    source_unit="min",
    target_unit="seconds",
    clock="cumulative operating time; closed hours excluded",
)
prepared = converted.to_native()  # duration is now [90.0, 120.0]; source is unchanged
summary = describe(prepared, column="duration", unit="seconds")
summary.metadata["duration_conversion"] = converted.to_dict()
```

All selected columns share the declared source and target units. Their new
magnitudes are float64 values; every row and non-selected column remains in
place. Pandas index labels are preserved in the native frame, but the evidence
identifies rows by zero-based positions in the supplied table. Positions do not
refer to an earlier table that a caller might already have filtered.

`to_native()` returns an independently mutable pandas/Polars frame; Arrow tables
are immutable. Evidence returned by `to_dict()` is detached. `to_json()` exports
only that evidence, not the table, a Pint quantity, or a unit registry. Source
file hashing and linking conversion evidence into a study remain caller choices.

## Supported units and clock meaning

| Duration | Accepted spellings |
| --- | --- |
| Seconds | `s`, `sec`, `second`, `seconds` |
| Minutes | `min`, `minute`, `minutes` |
| Hours | `h`, `hr`, `hour`, `hours` |

Aliases are explicit and case-sensitive; labels are not stripped or guessed.
The authored source/target spellings and canonical Pint names are both retained.
Ambiguous `m`, incompatible dimensions, quantities embedded in text, compound
units, percent/ratio units, custom units and unknown spellings are rejected.

The clock declaration is mandatory, nonblank text and is preserved verbatim.
The operation never parses it into a calendar or changes operating time into
elapsed calendar time. It scales durations on the caller's existing clock.
Days and operating days are outside this slice, even though Pint can convert
physical days. An operating-day conversion requires an explicit work-calendar
policy; none is inferred here. Calendar timestamps are not duration magnitudes.
Existing analytical APIs retain their existing unit choices, including calendar
`days` where already supported.

Column names are preserved, including names that contain an old unit label.
Rename such columns explicitly before presenting or exporting them, and pass
the target unit to subsequent numerical APIs. Those APIs do not infer units from
this preparation result or from a column's name.

## Validation and numerical limits

Conversion requires a nonempty table and an explicit nonempty list/tuple of
distinct existing column names. Selected values must be complete, finite,
nonnegative real numbers. Booleans, text, nulls, NaNs, infinities and timestamps
fail with `lss4py.errors.ValidationError` identifying the column and row.
No rows are dropped or filled, and zero remains measured zero.

The output follows float64 arithmetic. Integers that cannot first be represented
exactly as a float, conversion overflow and positive values that underflow to
zero are rejected. Other floating rounding follows normal float64 behavior;
round-trip comparisons should use an appropriate numerical tolerance.
All selected columns are checked before producing a result, and errors do not
partially modify the supplied table. Unsupported/lazy inputs retain the existing
`UnsupportedInputError`; lazy plans are not collected.

## Registry ownership and provenance

Pint is a direct core dependency (`>=0.25,<1`), locked to 0.26.2 for this slice.
The private lazy registry is initialized only when conversion is requested.
It supplies the conversion factor; LSS4PY does not duplicate a duration factor
table. Only the explicit aliases above are exposed by this API.

The operation neither sets nor reads Pint's application registry. A caller's
custom unit definitions therefore do not change this boundary, and initializing
it does not replace the caller's registry. No private FLO registry is imported.

The evidence includes schema/method version, selected columns, authored and
canonical units, multiplicative factor, unchanged clock declaration,
`calendar_conversion="none"`, source positions/count, native backend, Pint
version and the registry-policy identifier `lss4py.private.duration.v1`.
It can be attached as ordinary finite JSON in analytical result metadata and
saved/restored through existing result and bundle APIs. It is preparation
evidence rather than a new analytical result type in the standalone bundle schema.

## Verification

The 2026-10-27 source gates pass **1,901 tests**, with five explicitly deferred
expected failures and **93.53% full-package statement coverage**. Ninety new
source cases cover physical conversion factors, all native backends, hostile
pandas indexes, row/column preservation, aliases, missing/invalid values,
overflow/underflow, integer precision, immutable evidence and registry isolation.

The installed-wheel matrix passes 27 base, 37 pandas, 39 storage and 46 ecosystem
tests (**149 total**). It converts the actual 39-order prepared book durations
from minutes to hours and back, preserves the independent sums, and retains
13.7% PCE. Existing reconstruction and numeric-unit contract tests also pass.
Ruff, formatting, Vulture, lock consistency, typing and all eight import-boundary
contracts pass. Python 3.14 uses the locked Pint 0.26.2 release.
