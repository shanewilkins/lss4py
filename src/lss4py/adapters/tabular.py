"""Strict, declared-schema CSV loading without statistical calculations or row exclusions."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from typing import Any, Literal

import polars as pl

from lss4py._data_quality import normalize_data, validate_data
from lss4py.adapters.contracts import AdapterSchema, TabularAdapter
from lss4py.domain.data_quality import ColumnRule, DataContract
from lss4py.errors import AdapterError, ValidationError


def _source_bytes(source: str, expected_sha256: str | None) -> bytes:
    """Capture and fingerprint one source snapshot before any parsing or normalization."""
    try:
        contents = Path(source).read_bytes()
    except OSError as exc:
        raise AdapterError(f"Could not read CSV '{source}': {exc}") from exc
    if expected_sha256 is not None and hashlib.sha256(contents).hexdigest() != expected_sha256:
        raise AdapterError(f"CSV source checksum mismatch: {source}")
    return contents


def _header(rows: list[list[str]]) -> list[str]:
    """Reject missing, duplicate or blank source field identity before typing columns."""
    if not rows or not rows[0]:
        raise AdapterError("CSV requires a nonblank header.")
    header = rows[0]
    if any(not name.strip() for name in header):
        raise AdapterError("CSV requires a nonblank header.")
    if len(header) != len(set(header)):
        raise AdapterError("CSV contains duplicate column names.")
    return header


def _read_rows(
    source: str, expected_sha256: str | None
) -> tuple[bytes, list[str], list[list[str]]]:
    """Parse CSV structure without silently truncating ragged or blank observations."""
    contents = _source_bytes(source, expected_sha256)
    try:
        rows = list(csv.reader(io.StringIO(contents.decode("utf-8-sig"), newline=""), strict=True))
    except (UnicodeError, csv.Error) as exc:
        raise AdapterError(f"Could not parse CSV '{source}': {exc}") from exc
    header = _header(rows)
    for index, row in enumerate(rows[1:]):
        if len(row) != len(header):
            raise AdapterError(
                f"CSV data row {index} has {len(row)} fields; expected {len(header)}."
            )
    return contents, header, rows[1:]


def _parse_value(value: str, rule: ColumnRule, null_values: tuple[str, ...]) -> Any:
    """Parse only explicitly declared types; NA and leading-zero identities remain strings."""
    if value in null_values:
        return None
    if rule.kind == "numeric":
        return float(value)
    if rule.kind == "integer":
        return int(value)
    if rule.kind == "boolean":
        if value not in ("true", "false", "True", "False"):
            raise ValueError("Boolean fields require true/false or True/False.")
        return value in ("true", "True")
    return value


def _column(values: list[str], rule: ColumnRule, null_values: tuple[str, ...]) -> pl.Series:
    """Translate parsing and storage errors with field and zero-based source-row context."""
    parsed = []
    for index, value in enumerate(values):
        try:
            parsed.append(_parse_value(value, rule, null_values))
        except (TypeError, ValueError, OverflowError) as exc:
            raise AdapterError(
                f"Invalid {rule.kind} in column '{rule.name}', data row {index}: {value!r}"
            ) from exc
    dtypes = {
        "numeric": pl.Float64,
        "integer": pl.Int64,
        "boolean": pl.Boolean,
        "string": pl.String,
        "timestamp": pl.String,
    }
    try:
        return pl.Series(rule.name, parsed, dtype=dtypes[rule.kind], strict=True)
    except (TypeError, OverflowError, pl.exceptions.PolarsError) as exc:
        raise AdapterError(f"Could not store declared column '{rule.name}': {exc}") from exc


def _bindings(contract: DataContract, bindings: dict[str, str] | None) -> dict[str, str]:
    """Require an unambiguous target-to-source mapping without implicit schema discovery."""
    names = [rule.name for rule in contract.columns]
    configured = dict(bindings or {})
    if set(configured) - set(names):
        raise ValidationError("CSV bindings must name declared target columns.")
    result = {name: configured.get(name, name) for name in names}
    if any(not isinstance(value, str) or not value.strip() for value in result.values()):
        raise ValidationError("CSV source bindings must be nonblank strings.")
    if len(set(result.values())) != len(result):
        raise ValidationError("CSV source bindings must be distinct.")
    return result


class CSVTabularAdapter(TabularAdapter):
    """Load a local UTF-8 CSV into eager Polars under an explicit DataContract.

    All declared types are parsed explicitly. Undeclared columns remain strings,
    in original order; extras and source rows are never dropped. The default null
    token is the empty CSV field only. Whitespace and NA-like strings are not
    silently normalized. Target-to-source bindings may rename declared fields.
    """

    def __init__(
        self,
        source_reference: str | Path,
        *,
        contract: DataContract,
        bindings: dict[str, str] | None = None,
        null_values: tuple[str, ...] = ("",),
        expected_sha256: str | None = None,
        clock: str | None = None,
    ) -> None:
        """Validate loading declarations before accessing a source."""
        super().__init__(str(source_reference))
        if not isinstance(contract, DataContract):
            raise ValidationError("CSV ingestion requires a DataContract.")
        if not isinstance(null_values, tuple) or any(not isinstance(v, str) for v in null_values):
            raise ValidationError("null_values must be an explicit tuple of strings.")
        self.contract = contract
        self.bindings = _bindings(contract, bindings)
        self.null_values = null_values
        self.expected_sha256 = expected_sha256
        self.clock = clock

    def schema(self) -> AdapterSchema:
        """Inspect the fully parsed and validated source rather than guess its row count."""
        return self.load()[1]

    def load(self, backend: Literal["polars"] = "polars") -> tuple[pl.DataFrame, AdapterSchema]:
        """Parse one source snapshot, preserve extras and report exact transformations."""
        if backend != "polars":
            raise ValueError("Core CSV adapters materialize the 'polars' backend only.")
        contents, header, rows = _read_rows(self.source_reference, self.expected_sha256)
        frame = self._frame(header, rows)
        report = validate_data(frame, contract=self.contract)
        if not report.valid:
            raise AdapterError(f"Invalid CSV {self.source_reference!r}: {report.to_json()}")
        try:
            normalized = normalize_data(frame, contract=self.contract)
        except ValidationError as exc:
            raise AdapterError(f"Invalid CSV '{self.source_reference}': {exc}") from exc
        frame = frame.with_columns(normalized.to_polars().get_columns())
        return frame, self._schema(frame, contents, normalized)

    def _frame(self, header: list[str], rows: list[list[str]]) -> pl.DataFrame:
        """Retain source column order while mapping declared fields and preserving extra strings."""
        missing = set(self.bindings.values()) - set(header)
        if missing:
            raise AdapterError(f"Missing required CSV columns: {sorted(missing)}")
        inverse = {source: target for target, source in self.bindings.items()}
        names = [inverse.get(name, name) for name in header]
        if len(names) != len(set(names)):
            raise AdapterError("CSV bindings collide with existing source columns.")
        rules = {rule.name: rule for rule in self.contract.columns}
        columns = []
        for index, name in enumerate(names):
            rule = rules.get(name, ColumnRule(name, kind="string", nullable=True))
            columns.append(_column([row[index] for row in rows], rule, self.null_values))
        return pl.DataFrame(columns)

    def _schema(self, frame: pl.DataFrame, contents: bytes, normalized: Any) -> AdapterSchema:
        """Attach provenance and validation evidence to the actual materialized schema."""
        return AdapterSchema(
            column_names=frozenset(frame.columns),
            column_types={c: str(t) for c, t in frame.schema.items()},
            row_count=frame.height,
            key_columns=list(self.contract.key_columns),
            timestamp_columns=[r.name for r in self.contract.columns if r.kind == "timestamp"],
            source_format="csv",
            backend="polars",
            transformations=(
                "decode_utf8_csv",
                "parse_explicit_column_types",
                "apply_declared_bindings",
                *normalized.transformations,
                "restore_extra_columns_and_source_order",
            ),
            source_reference=self.source_reference,
            source_sha256=hashlib.sha256(contents).hexdigest(),
            units={r.name: r.unit for r in self.contract.columns if r.unit is not None},
            clock=self.clock,
            bindings=dict(self.bindings),
            validation=validate_data(frame, contract=self.contract),
        )


def load_csv(
    path: str | Path,
    *,
    contract: DataContract,
    bindings: dict[str, str] | None = None,
    expected_sha256: str | None = None,
) -> pl.DataFrame:
    """Convenient declared CSV loading; use CSVTabularAdapter.load for full source evidence."""
    return CSVTabularAdapter(
        path, contract=contract, bindings=bindings, expected_sha256=expected_sha256
    ).load()[0]


def load_tabular_records(path: str | Path, *, contract: DataContract) -> list[dict[str, Any]]:
    """Load declared local CSV records without backend-specific scalar or index semantics."""
    return load_csv(path, contract=contract).to_dicts()
