"""Shared contract validation and normalization for adapters and public analytical entry points."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
from math import isnan
from numbers import Integral, Real
from typing import Any

import polars as pl

from lss4py._frames import CanonicalFrame, canonical_frame, eager_frame
from lss4py.domain.data_quality import (
    ColumnProfile,
    ColumnRule,
    DataContract,
    DataIssue,
    DataValidationReport,
    NormalizedData,
)
from lss4py.errors import ValidationError


def _canonical(data: Any, contract: DataContract) -> CanonicalFrame:
    """Select declared source columns while retaining missing-column evidence."""
    if not isinstance(contract, DataContract):
        raise ValidationError("contract must be a DataContract.")
    source = eager_frame(data)
    selected = tuple(rule.name for rule in contract.columns if rule.name in source.columns)
    return canonical_frame(data, selected, retain_source_positions=True)


def _validate_structural(
    frame: pl.DataFrame,
    contract: DataContract,
    *,
    source_positions: tuple[int, ...] | None,
) -> tuple[DataIssue, ...]:
    """Load Pandera only when a public data-quality operation executes."""
    from lss4py._pandera_validation import validate_frame

    return validate_frame(frame, contract, source_positions=source_positions)


def _missing(value: Any) -> bool:
    """Treat native nulls and floating NaNs as one portable missing category."""
    return value is None or isinstance(value, float) and isnan(value)


def _kind(value: Any) -> str:
    """Describe logical scalar kinds without exposing backend-specific dtype names."""
    if _missing(value):
        return "missing"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, Real):
        return "numeric"
    if isinstance(value, datetime):
        return "timestamp"
    if isinstance(value, str):
        return "string"
    return "unsupported"


def _timestamp(value: Any) -> datetime:
    """Use microsecond datetime identity and normalize aware times to UTC."""
    if isinstance(value, str):
        if "T" not in value and " " not in value:
            raise ValueError("A timestamp requires both date and time.")
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        raise ValueError("Expected a native or ISO datetime.")
    value = value if value.utcoffset() is None else value.astimezone(UTC)
    # Rebuild a native datetime so subclasses cannot retain hidden nanoseconds.
    # Inspection, duplicate selection and materialization must share one identity.
    return datetime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        tzinfo=value.tzinfo,
        fold=value.fold,
    )


def _time_value(value: Any) -> tuple[Any, str | None]:
    """Translate parser failures into a portable timestamp diagnostic."""
    try:
        return _timestamp(value), None
    except ValueError, OverflowError, TypeError:
        return None, "INVALID_TIMESTAMP"


def _collect(
    values: list[Any],
    nulls: list[bool],
    rule: ColumnRule,
    structural_issues: tuple[DataIssue, ...],
) -> tuple:
    """Normalize structurally valid values and retain LSS4PY-owned findings."""
    findings: dict[str, list[int]] = defaultdict(list)
    clean: list[Any] = []
    kinds: set[str] = set()
    missing_rows = []
    structurally_invalid = {
        row for issue in structural_issues if issue.code != "MISSING_VALUES" for row in issue.rows
    }
    for row, (value, null) in enumerate(zip(values, nulls, strict=True)):
        if null or _missing(value):
            missing_rows.append(row)
            clean.append(None)
            continue
        kinds.add(_kind(value))
        if row in structurally_invalid:
            clean.append(None)
            continue
        if rule.kind == "timestamp":
            normalized, code = _time_value(value)
        elif rule.kind == "string" and not value.strip():
            normalized, code = None, "BLANK_VALUE"
        else:
            normalized = int(value) if rule.kind == "integer" else value
            code = None
        if code is not None:
            findings[code].append(row)
        clean.append(None if code else normalized)
    return findings, clean, kinds, tuple(missing_rows)


def _column(
    values: list[Any],
    nulls: list[bool],
    rule: ColumnRule,
    unit: str | None,
    structural_issues: tuple[DataIssue, ...],
) -> tuple[ColumnProfile, list[DataIssue], list[Any]]:
    """Inspect one column and retain canonical scalars for cross-column checks."""
    findings, clean, kinds, missing_rows = _collect(
        values,
        nulls,
        rule,
        structural_issues,
    )
    issues = [*structural_issues, *_semantic_issues(findings, rule)]
    issues.sort(key=lambda issue: min(issue.rows))
    issues.extend(_units(rule, unit))
    issues.extend(_timezone_issues(clean, rule.name))
    profile = _profile(
        rule,
        unit,
        kinds,
        structural_issues,
        findings,
        clean,
        missing_rows,
    )
    return profile, issues, clean


def _timezone_issues(clean: list[Any], name: str) -> list[DataIssue]:
    """Flag mixed timezone awareness without inferring a timezone for naive values."""
    issues = []
    awareness = {v.utcoffset() is not None for v in clean if isinstance(v, datetime)}
    if len(awareness) > 1:
        issues.append(
            DataIssue("MIXED_TIMEZONES", "error", "Mixed naive and aware timestamps.", (name,))
        )
    return issues


def _profile(
    rule: ColumnRule,
    unit: str | None,
    kinds: set[str],
    structural_issues: tuple[DataIssue, ...],
    findings: dict,
    clean: list,
    missing_rows: tuple[int, ...],
) -> ColumnProfile:
    """Count portable missingness, distinct valid values and invalid scalar observations."""
    invalid_count = sum(
        len(issue.rows) for issue in structural_issues if issue.code != "MISSING_VALUES"
    ) + sum(len(rows) for rows in findings.values())
    profile = ColumnProfile(
        rule.name,
        "|".join(sorted(kinds)) or "missing",
        len(missing_rows),
        len({v for v in clean if v is not None}),
        invalid_count,
        rule.unit,
        unit,
    )
    return profile


def _semantic_issues(
    findings: dict[str, list[int]],
    rule: ColumnRule,
) -> list[DataIssue]:
    """Return findings deliberately retained outside Pandera."""
    issues = []
    for code, rows in findings.items():
        if not rows:
            continue
        issues.append(
            DataIssue(
                code,
                "error",
                f"{rule.name}: {code.lower().replace('_', ' ')}.",
                (rule.name,),
                tuple(rows),
            )
        )
    return issues


def _units(rule: ColumnRule, source: str | None) -> list[DataIssue]:
    """Compare explicit declarations; never infer units or convert quantities."""
    if rule.unit is None:
        return []
    if source is None:
        return [
            DataIssue("UNIT_UNVERIFIED", "warning", "Source unit was not declared.", (rule.name,))
        ]
    if source != rule.unit:
        return [
            DataIssue("UNIT_MISMATCH", "error", "Source and expected units differ.", (rule.name,))
        ]
    return []


def _duplicate_rows(
    values: dict[str, list[Any]],
    columns: tuple[str, ...],
    excluded: frozenset[int] = frozenset(),
) -> tuple[int, ...]:
    """Find later duplicate positions with exact typed key identity and stable ordering."""
    seen: set[tuple] = set()
    duplicates = []
    for row, items in enumerate(zip(*(values[c] for c in columns), strict=True)):
        if row in excluded:
            continue
        key = tuple((_kind(value), value) for value in items)
        if key in seen:
            duplicates.append(row)
        seen.add(key)
    return tuple(duplicates)


def _duplicate_issues(
    values: dict[str, list[Any]],
    contract: DataContract,
    excluded: frozenset[int],
) -> list[DataIssue]:
    """Apply the declared duplicate policy independently of temporal checks."""
    issues = []
    columns = contract.key_columns or tuple(c.name for c in contract.columns)
    if all(c in values for c in columns) and contract.duplicates != "allow":
        duplicates = _duplicate_rows(values, columns, excluded)
        if duplicates:
            severity = "error" if contract.duplicates == "error" else "warning"
            issues.append(
                DataIssue(
                    "DUPLICATE_ROWS",
                    severity,
                    "Later duplicate key/row positions.",
                    columns,
                    duplicates,
                )
            )
    return issues


def _invalid_rows(issues: list[DataIssue]) -> frozenset[int]:
    """Exclude blocking scalar observations from duplicate identity comparisons."""
    return frozenset(row for issue in issues if issue.severity == "error" for row in issue.rows)


def _time_order(starts: list[Any], ends: list[Any], columns: tuple[str, str]) -> list[DataIssue]:
    """Distinguish reversed intervals from incompatible timezone awareness."""
    findings: dict[str, list[int]] = defaultdict(list)
    for row, (start, end) in enumerate(zip(starts, ends, strict=True)):
        if start is None or end is None:
            continue
        if (start.utcoffset() is None) != (end.utcoffset() is None):
            findings["MIXED_TIMEZONES"].append(row)
        elif end < start:
            findings["REVERSED_TIME"].append(row)
    return [
        DataIssue(code, "error", "Invalid timestamp pair.", columns, tuple(rows))
        for code, rows in findings.items()
    ]


def _source_units(source_units: Mapping[str, str] | None) -> dict[str, str]:
    """Copy declared source units and reject ambiguous mappings."""
    if source_units is None:
        return {}
    if not isinstance(source_units, Mapping):
        raise ValidationError("source_units must be a mapping of column names to units.")
    result = dict(source_units)
    if any(not isinstance(v, str) or not v.strip() for item in result.items() for v in item):
        raise ValidationError("source_units must contain nonblank column names and units.")
    return result


def validate_data(
    data: Any,
    *,
    contract: DataContract,
    source_units: Mapping[str, str] | None = None,
) -> DataValidationReport:
    """Inspect an eager table and return all declared blocking and nonblocking findings.

    Validation never mutates, coerces, excludes rows or executes an analysis.
    Positions are zero-based source rows. Native nulls and NaNs are one missing
    category; nullable columns warn, while missing keys always block. Extra columns
    are reported by name but are outside the declared checks.
    """
    frame = _canonical(data, contract)
    report, _ = _inspect(frame, contract, _source_units(source_units))
    return report


def _inspect(
    canonical: CanonicalFrame,
    contract: DataContract,
    units: dict[str, str],
) -> tuple[DataValidationReport, dict[str, list[Any]]]:
    """Share inspection between reporting and explicit preparation."""
    frame = canonical.to_polars(copy=False)
    source_columns = tuple(name for name, _ in canonical.source_schema)
    if set(units) - set(source_columns):
        raise ValidationError("source_units references absent columns.")
    source_positions = (
        canonical.source_positions if frame.height == canonical.source_row_count else None
    )
    structural = _validate_structural(
        frame,
        contract,
        source_positions=source_positions,
    )
    profiles, issues, clean = [], [], {}
    if canonical.source_row_count == 0:
        issues.append(DataIssue("EMPTY_DATA", "error", "No rows were supplied."))
    for rule in contract.columns:
        column_issues = tuple(
            issue
            for issue in structural
            if issue.columns == (rule.name,) and issue.code != "DUPLICATE_ROWS"
        )
        if rule.name not in frame.columns:
            issues.extend(column_issues)
            continue
        series = frame[rule.name]
        profile, notes, values = _column(
            series.to_list(),
            series.is_null().to_list(),
            rule,
            units.get(rule.name),
            column_issues,
        )
        profiles.append(profile)
        issues.extend(notes)
        clean[rule.name] = values
    issues.extend(_duplicate_issues(clean, contract, _invalid_rows(issues)))
    for start, end in contract.timestamp_order:
        if start in clean and end in clean:
            issues.extend(_time_order(clean[start], clean[end], (start, end)))
    return DataValidationReport(
        contract,
        canonical.source_row_count,
        source_columns,
        tuple(profiles),
        tuple(issues),
        canonical.source_backend,
    ), clean


def normalize_data(
    data: Any,
    *,
    contract: DataContract,
    source_units: Mapping[str, str] | None = None,
    drop_missing: bool = False,
    drop_duplicates: bool = False,
) -> NormalizedData:
    """Materialize declared columns as Polars with explicitly selected row exclusions.

    ISO timestamps are parsed to microsecond native timestamps; aware values use
    UTC and naive values remain naive. Null/NaN values become null. No numeric text,
    boolean or unit coercion occurs. Other blocking defects cause ValidationError.
    Both reports, transformations and original row positions remain inspectable.
    """
    frame = _canonical(data, contract)
    if not isinstance(drop_missing, bool) or not isinstance(drop_duplicates, bool):
        raise ValidationError("Row exclusion options must be boolean.")
    units = _source_units(source_units)
    before, clean = _inspect(frame, contract, units)
    _blocking(before, drop_missing, drop_duplicates)
    retained = _retained_rows(clean, contract, drop_missing, drop_duplicates)
    transformations = _transformations(contract, drop_missing, drop_duplicates)
    result = _materialize(clean, retained)
    return _prepared(result, retained, before, transformations, units)


def _prepared(
    result: pl.DataFrame,
    retained: tuple[int, ...],
    before: DataValidationReport,
    transformations: tuple[str, ...],
    units: dict[str, str],
) -> NormalizedData:
    """Revalidate materialized output before returning its source-linked evidence."""
    after = validate_data(
        result,
        contract=before.contract,
        source_units={k: v for k, v in units.items() if k in result.columns},
    )
    if not after.valid:
        raise ValidationError(
            "Normalization leaves invalid data: " + ", ".join(i.code for i in after.errors)
        )
    return NormalizedData(result, retained, before, after, transformations)


def _blocking(before: DataValidationReport, drop_missing: bool, drop_duplicates: bool) -> None:
    """Allow only specifically authorized exclusion defects during normalization."""
    removable = {"MISSING_VALUES"} if drop_missing else set()
    if drop_duplicates:
        removable.add("DUPLICATE_ROWS")
    blocking = [i for i in before.errors if i.code not in removable]
    if blocking:
        raise ValidationError("Cannot normalize data: " + ", ".join(i.code for i in blocking))


def _transformations(
    contract: DataContract, drop_missing: bool, drop_duplicates: bool
) -> tuple[str, ...]:
    """Record the complete, deterministic preparation policy."""
    transformations = ("select_declared_columns", "canonical_polars_copy", "null_nan_to_null")
    if drop_missing:
        transformations += ("drop_missing_rows",)
    if drop_duplicates:
        transformations += ("keep_first_duplicate",)
    if any(c.kind == "timestamp" for c in contract.columns):
        transformations += ("parse_iso_timestamps_microseconds_aware_to_utc",)
    return transformations


def _materialize(clean: dict[str, list[Any]], retained: tuple[int, ...]) -> pl.DataFrame:
    """Copy declared scalar values into canonical Polars without wrapping source memory."""
    try:
        columns = {c: _storage_values([v[r] for r in retained]) for c, v in clean.items()}
        return pl.DataFrame(columns, strict=True)
    except (TypeError, ValueError, OverflowError, pl.exceptions.PolarsError) as exc:
        raise ValidationError(
            "Declared values cannot be materialized as canonical Polars."
        ) from exc


def _storage_values(values: list[Any]) -> list[Any]:
    """Promote mixed numeric scalars consistently, without rounding exact integers."""
    integer_kinds = {isinstance(v, Integral) for v in values if isinstance(v, Real)}
    if integer_kinds != {False, True}:
        return values
    return [_float_storage(v) for v in values]


def _float_storage(value: Any) -> float | None:
    """Represent one mixed numeric scalar as a float only when integer identity survives."""
    if value is None:
        return None
    if isinstance(value, Integral) and int(value) != float(value):
        raise ValueError("Mixed numeric storage would lose integer precision.")
    return float(value)


def _retained_rows(
    clean: dict[str, list[Any]],
    contract: DataContract,
    missing: bool,
    duplicates: bool,
) -> tuple[int, ...]:
    """Exclude missing rows before calculating duplicate positions on surviving data."""
    count = len(next(iter(clean.values())))
    rows = list(range(count))
    if missing:
        rows = _complete_rows(clean, rows)
    if duplicates:
        rows = _keep_first(clean, rows, contract.key_columns or tuple(clean))
    return tuple(rows)


def _keep_first(
    clean: dict[str, list[Any]], rows: list[int], columns: tuple[str, ...]
) -> list[int]:
    """Deduplicate only surviving rows using the declared key or complete-row identity."""
    selected = {c: [v[r] for r in rows] for c, v in clean.items()}
    excluded = set(_duplicate_rows(selected, columns))
    return [r for i, r in enumerate(rows) if i not in excluded]


def _complete_rows(clean: dict[str, list[Any]], rows: list[int]) -> list[int]:
    """Identify complete declared observations before deduplicating survivors."""
    return [r for r in rows if all(v[r] is not None for v in clean.values())]
