"""Shared non-analytical checks for explicit numeric observation contracts."""

from dataclasses import replace

import polars as pl

from lss4py._data_quality import validate_data
from lss4py.domain.data_quality import DataIssue, DataValidationReport
from lss4py.domain.numeric_log import NumericLogContract


def validate_numeric_log(frame: pl.DataFrame, contract: NumericLogContract) -> DataValidationReport:
    """Inspect mechanical log consistency without pairing, aggregating or excluding events."""
    report = validate_data(frame, contract=contract.data_contract())
    if not report.valid:
        return report
    issues = (*report.issues, *_duplicate_events(frame, contract), *_time_order(frame, contract))
    return replace(report, issues=issues)


def _duplicate_events(frame: pl.DataFrame, contract: NumericLogContract) -> list[DataIssue]:
    """Keep repeated case/load/activity/pass identity distinct from legitimate parallel rows."""
    issues = []
    duplicate = frame.select(contract.identity_columns).is_duplicated().to_list()
    positions = tuple(i for i, flag in enumerate(duplicate) if flag)
    if positions:
        issues.append(
            DataIssue(
                "DUPLICATE_EVENT",
                "error",
                "Duplicate declared event identity.",
                contract.identity_columns,
                positions,
            )
        )
    return issues


def _time_order(frame: pl.DataFrame, contract: NumericLogContract) -> list[DataIssue]:
    """Check only declared endpoint ordering, without reconstructing event intervals."""
    issues = []
    for start, end in zip(contract.time_columns, contract.time_columns[1:], strict=False):
        mask = (frame[start] > frame[end]).to_list()
        positions = tuple(i for i, flag in enumerate(mask) if flag)
        if positions:
            issues.append(
                DataIssue(
                    "INVALID_TIME_ORDER",
                    "error",
                    "Numeric endpoints are out of order.",
                    (start, end),
                    positions,
                )
            )
    return issues
