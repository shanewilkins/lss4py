"""Private Pandera validation for canonical Polars frames."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

import pandera.polars as pa
import polars as pl
from pandera.errors import SchemaErrors

from lss4py.domain.data_quality import ColumnRule, DataContract, DataIssue
from lss4py.errors import ValidationError

_MISSING = "lss4py_missing"
_FINITE = "lss4py_finite"
_INTEGER = "lss4py_integer"
_MINIMUM = "lss4py_minimum"
_MAXIMUM = "lss4py_maximum"
_UNIQUE = "multiple_fields_uniqueness"


def compile_schema(contract: DataContract) -> pa.DataFrameSchema:
    """Compile structural contract rules without coercion or row deletion."""
    if not isinstance(contract, DataContract):
        raise ValidationError("contract must be a DataContract.")
    columns = {
        rule.name: pa.Column(
            None,
            checks=_checks(rule),
            nullable=True,
            required=True,
            coerce=False,
            drop_invalid_rows=False,
        )
        for rule in contract.columns
    }
    unique = (
        list(contract.key_columns)
        if contract.key_columns and contract.duplicates != "allow"
        else None
    )
    return pa.DataFrameSchema(
        columns,
        coerce=False,
        strict=False,
        unique=unique,
        drop_invalid_rows=False,
    )


def validate_frame(
    frame: pl.DataFrame,
    contract: DataContract,
    *,
    source_positions: tuple[int, ...] | None = None,
) -> tuple[DataIssue, ...]:
    """Return stable LSS4PY issues from lazy aggregated Pandera failures."""
    if not isinstance(frame, pl.DataFrame):
        raise TypeError("Pandera validation requires a canonical Polars DataFrame.")
    positions = _positions(frame.height, source_positions)
    try:
        compile_schema(contract).validate(frame, lazy=True)
    except SchemaErrors as exc:
        return _translate(exc.failure_cases, frame, contract, positions)
    return ()


def _checks(rule: ColumnRule) -> list[pa.Check]:
    """Build named checks so translation never depends on third-party wording."""
    checks = [
        pa.Check(_missing_check, name=_MISSING, ignore_na=False),
        pa.Check(_kind_check(rule.kind), name=f"lss4py_kind_{rule.kind}"),
    ]
    if rule.kind in ("numeric", "integer"):
        checks.append(pa.Check(_finite_check, name=_FINITE))
    if rule.kind == "integer":
        checks.append(pa.Check(_integer_check, name=_INTEGER))
    if rule.minimum is not None:
        checks.append(
            pa.Check(
                _bound_check(
                    rule.minimum,
                    minimum=True,
                    integer=rule.kind == "integer",
                ),
                name=_MINIMUM,
            )
        )
    if rule.maximum is not None:
        checks.append(
            pa.Check(
                _bound_check(
                    rule.maximum,
                    minimum=False,
                    integer=rule.kind == "integer",
                ),
                name=_MAXIMUM,
            )
        )
    return checks


def _dtype(data: Any) -> pl.DataType:
    """Read the selected column dtype from Pandera's Polars check object."""
    return data.lazyframe.collect_schema()[data.key]


def _missing_expression(name: str, dtype: pl.DataType) -> pl.Expr:
    """Treat null and floating NaN as the same missing category."""
    expression = pl.col(name).is_null()
    return expression | pl.col(name).is_nan() if dtype.is_float() else expression


def _missing_check(data: Any) -> pl.LazyFrame:
    dtype = _dtype(data)
    return data.lazyframe.select(~_missing_expression(data.key, dtype))


def _kind_check(kind: str) -> Callable[[Any], bool | pl.LazyFrame]:
    def check(data: Any) -> bool | pl.LazyFrame:
        dtype = _dtype(data)
        if dtype == pl.Null:
            return True
        base = dtype.base_type()
        if kind in ("numeric", "integer"):
            valid = _numeric_dtype(dtype)
        elif kind == "string":
            valid = base in (pl.String, pl.Categorical, pl.Enum)
        elif kind == "boolean":
            valid = base == pl.Boolean
        else:
            valid = base in (pl.String, pl.Datetime)
        if valid:
            return True
        return data.lazyframe.select(_missing_expression(data.key, dtype))

    return check


def _finite_check(data: Any) -> bool | pl.LazyFrame:
    dtype = _dtype(data)
    if not _numeric_dtype(dtype):
        return True
    missing = _missing_expression(data.key, dtype)
    return data.lazyframe.select(missing | pl.col(data.key).is_finite())


def _integer_check(data: Any) -> bool | pl.LazyFrame:
    dtype = _dtype(data)
    if dtype.is_integer():
        return True
    if not dtype.is_float():
        return True
    column = pl.col(data.key)
    missing = _missing_expression(data.key, dtype)
    nonfinite = ~column.is_finite()
    exact = (column == column.floor()) & column.is_between(-(2**53), 2**53)
    return data.lazyframe.select(missing | nonfinite | exact)


def _bound_check(
    bound: float,
    *,
    minimum: bool,
    integer: bool,
) -> Callable[[Any], bool | pl.LazyFrame]:
    def check(data: Any) -> bool | pl.LazyFrame:
        dtype = _dtype(data)
        if not _numeric_dtype(dtype):
            return True
        column = pl.col(data.key)
        missing = _missing_expression(data.key, dtype)
        nonfinite = ~column.is_finite()
        comparison = column >= bound if minimum else column <= bound
        if integer and dtype.is_float():
            invalid_integer = (column != column.floor()) | ~column.is_between(-(2**53), 2**53)
            comparison = invalid_integer | comparison
        return data.lazyframe.select(missing | nonfinite | comparison)

    return check


def _numeric_dtype(dtype: pl.DataType) -> bool:
    """Match the existing Python Real contract without accepting Decimal storage."""
    return dtype.is_integer() or dtype.is_float()


def _positions(count: int, positions: tuple[int, ...] | None) -> tuple[int, ...]:
    if positions is None:
        return tuple(range(count))
    if (
        len(positions) != count
        or any(
            not isinstance(position, int) or isinstance(position, bool) or position < 0
            for position in positions
        )
        or len(set(positions)) != count
    ):
        raise ValidationError("Source positions must be unique nonnegative row identifiers.")
    return positions


def _translate(
    failure_cases: pl.DataFrame,
    frame: pl.DataFrame,
    contract: DataContract,
    source_positions: tuple[int, ...],
) -> tuple[DataIssue, ...]:
    """Aggregate stable diagnostics while discarding Pandera failure values."""
    failures: dict[tuple[str | None, str], set[int]] = defaultdict(set)
    missing_columns: set[str] = set()
    duplicate_failed = False
    for failure in failure_cases.to_dicts():
        check = failure["check"]
        if check == "column_in_dataframe":
            missing_columns.add(failure["failure_case"])
            continue
        if check == _UNIQUE:
            duplicate_failed = True
            continue
        column = failure["column"]
        index = failure["index"]
        if column is not None and index is not None:
            failures[(column, check)].add(index)
        elif column is not None:
            failures[(column, check)].update(_present_rows(frame, column))

    issues: list[DataIssue] = []
    for rule in contract.columns:
        if rule.name in missing_columns:
            issues.append(
                DataIssue(
                    "MISSING_COLUMN",
                    "error",
                    "Required column is absent.",
                    (rule.name,),
                )
            )
            continue
        issues.extend(_column_issues(rule, contract, failures, source_positions))

    invalid_rows = {row for issue in issues if issue.severity == "error" for row in issue.rows}
    if duplicate_failed:
        excluded = {
            row for row, source_row in enumerate(source_positions) if source_row in invalid_rows
        }
        duplicate_rows = tuple(
            source_positions[row]
            for row in _later_duplicates(frame, contract.key_columns, excluded)
        )
        if duplicate_rows:
            issues.append(
                DataIssue(
                    "DUPLICATE_ROWS",
                    "error" if contract.duplicates == "error" else "warning",
                    "Later duplicate key/row positions.",
                    contract.key_columns,
                    duplicate_rows,
                )
            )
    return tuple(issues)


def _column_issues(
    rule: ColumnRule,
    contract: DataContract,
    failures: dict[tuple[str | None, str], set[int]],
    source_positions: tuple[int, ...],
) -> list[DataIssue]:
    checks = (
        (_MISSING, "MISSING_VALUES"),
        (f"lss4py_kind_{rule.kind}", _type_code(rule)),
        (_FINITE, "NONFINITE"),
        (_INTEGER, "INVALID_INTEGER"),
        (_MINIMUM, "OUT_OF_RANGE"),
        (_MAXIMUM, "OUT_OF_RANGE"),
    )
    rows_by_code: dict[str, set[int]] = defaultdict(set)
    for check, code in checks:
        rows_by_code[code].update(failures.get((rule.name, check), ()))
    issues = []
    ordered = sorted(
        ((code, rows) for code, rows in rows_by_code.items() if rows),
        key=lambda item: min(item[1]),
    )
    for code, local_rows in ordered:
        severity = (
            "warning"
            if code == "MISSING_VALUES" and rule.nullable and rule.name not in contract.key_columns
            else "error"
        )
        issues.append(
            DataIssue(
                code,
                severity,
                f"{rule.name}: {code.lower().replace('_', ' ')}.",
                (rule.name,),
                tuple(source_positions[row] for row in sorted(local_rows)),
            )
        )
    return issues


def _type_code(rule: ColumnRule) -> str:
    return "INVALID_TIMESTAMP" if rule.kind == "timestamp" else "INVALID_TYPE"


def _present_rows(frame: pl.DataFrame, column: str) -> set[int]:
    series = frame[column]
    missing = series.is_null()
    if series.dtype.is_float():
        missing = missing | series.is_nan()
    return {row for row, is_missing in enumerate(missing) if not is_missing}


def _later_duplicates(
    frame: pl.DataFrame,
    columns: tuple[str, ...],
    excluded: set[int],
) -> tuple[int, ...]:
    seen: set[tuple[Any, ...]] = set()
    duplicates = []
    for row, values in enumerate(frame.select(*columns).iter_rows()):
        if row in excluded:
            continue
        if values in seen:
            duplicates.append(row)
        seen.add(values)
    return tuple(duplicates)
