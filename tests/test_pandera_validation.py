"""Private Pandera structural validation and error translation."""

from copy import deepcopy
from typing import Any

import pandera.config as pandera_config
import polars as pl
import pytest

from lss4py._pandera_validation import compile_schema, validate_frame
from lss4py.domain.data_quality import ColumnRule, DataContract
from lss4py.errors import ValidationError


def test_schema_is_noncoercing_open_and_nonmutating():
    """Compile only private structural policy without changing Pandera globals."""
    contract = DataContract((ColumnRule("value", minimum=0),))
    before = deepcopy(pandera_config.CONFIG)
    schema = compile_schema(contract)
    frame = pl.DataFrame({"value": [1.0], "extra": ["retained"]})
    original = frame.clone()
    assert validate_frame(frame, contract) == ()
    assert frame.equals(original)
    assert schema.coerce is False
    assert schema.strict is False
    assert schema.drop_invalid_rows is False
    assert schema.columns["value"].coerce is False
    assert schema.columns["value"].drop_invalid_rows is False
    assert pandera_config.CONFIG == before
    assert pandera_config.CONFIG.use_narwhals_backend is False


@pytest.mark.parametrize(
    ("rule", "values"),
    [
        (ColumnRule("value", "numeric"), [1.0, 2.5]),
        (ColumnRule("value", "integer"), [1.0, 2.0]),
        (ColumnRule("value", "string"), ["a", "b"]),
        (ColumnRule("value", "boolean"), [True, False]),
        (ColumnRule("value", "timestamp"), ["2026-01-01T08:00:00"]),
    ],
)
def test_supported_logical_kinds_pass_without_coercion(rule, values):
    """Accept the broad logical domains retained by existing contracts."""
    frame = pl.DataFrame({"value": values})
    schema = frame.schema
    assert validate_frame(frame, DataContract((rule,))) == ()
    assert frame.schema == schema
    assert frame["value"].to_list() == values


def test_numeric_failures_are_aggregated_with_stable_codes_and_rows():
    """Map named Pandera checks without exposing failure values or wording."""
    contract = DataContract((ColumnRule("value", minimum=0, maximum=10),))
    frame = pl.DataFrame({"value": [1.0, float("inf"), -1.0, float("nan"), 11.0]})
    issues = validate_frame(frame, contract)
    assert [(issue.code, issue.rows) for issue in issues] == [
        ("NONFINITE", (1,)),
        ("OUT_OF_RANGE", (2, 4)),
        ("MISSING_VALUES", (3,)),
    ]


def test_integer_and_type_failures_use_existing_diagnostics():
    """Separate exact-integer failures from incompatible physical dtypes."""
    integer = validate_frame(
        pl.DataFrame({"value": [1.0, 1.5, 2.0]}),
        DataContract((ColumnRule("value", "integer"),)),
    )
    wrong_type = validate_frame(
        pl.DataFrame({"value": ["secret-a", None]}),
        DataContract((ColumnRule("value", "boolean", nullable=True),)),
    )
    timestamp = validate_frame(
        pl.DataFrame({"value": [1, 2]}),
        DataContract((ColumnRule("value", "timestamp"),)),
    )
    assert [(issue.code, issue.rows) for issue in integer] == [("INVALID_INTEGER", (1,))]
    assert [(issue.code, issue.severity, issue.rows) for issue in wrong_type] == [
        ("INVALID_TYPE", "error", (0,)),
        ("MISSING_VALUES", "warning", (1,)),
    ]
    assert [(issue.code, issue.rows) for issue in timestamp] == [("INVALID_TIMESTAMP", (0, 1))]
    assert "secret" not in repr(wrong_type)


def test_invalid_integer_does_not_also_report_a_bound_failure():
    """Apply bounds only after satisfying the declared integer domain."""
    issues = validate_frame(
        pl.DataFrame({"value": [1.5]}),
        DataContract((ColumnRule("value", "integer", minimum=2),)),
    )
    assert [(issue.code, issue.rows) for issue in issues] == [("INVALID_INTEGER", (0,))]


def test_missing_columns_and_nullable_source_positions_are_stable():
    """Retain governed missingness severity and caller source positions."""
    contract = DataContract(
        (
            ColumnRule("optional", nullable=True),
            ColumnRule("required"),
            ColumnRule("absent"),
        )
    )
    frame = pl.DataFrame({"optional": [1.0, None], "required": [None, 2.0]})
    issues = validate_frame(frame, contract, source_positions=(10, 20))
    assert [(issue.code, issue.severity, issue.columns, issue.rows) for issue in issues] == [
        ("MISSING_VALUES", "warning", ("optional",), (20,)),
        ("MISSING_VALUES", "error", ("required",), (10,)),
        ("MISSING_COLUMN", "error", ("absent",), ()),
    ]


@pytest.mark.parametrize("policy", ["warn", "error"])
def test_key_uniqueness_keeps_later_valid_occurrences(policy):
    """Translate Pandera uniqueness to existing later-duplicate identity."""
    contract = DataContract(
        (ColumnRule("key", "integer", nullable=True),),
        key_columns=("key",),
        duplicates=policy,
    )
    frame = pl.DataFrame({"key": [1, 1, None, None, 2, 2]})
    issues = validate_frame(frame, contract)
    assert [(issue.code, issue.severity, issue.rows) for issue in issues] == [
        ("MISSING_VALUES", "error", (2, 3)),
        ("DUPLICATE_ROWS", policy.replace("warn", "warning"), (1, 5)),
    ]


def test_allowed_key_duplicates_do_not_compile_a_uniqueness_check():
    """Respect explicit duplicate allowance rather than reporting hidden policy."""
    contract = DataContract(
        (ColumnRule("key", "integer"),),
        key_columns=("key",),
        duplicates="allow",
    )
    assert validate_frame(pl.DataFrame({"key": [1, 1]}), contract) == ()
    assert compile_schema(contract).unique is None


def test_analytical_semantics_remain_outside_pandera():
    """Leave parsing, blank text, full-row duplicates, and time order to LSS4PY."""
    contract = DataContract(
        (
            ColumnRule("label", "string"),
            ColumnRule("started", "timestamp"),
            ColumnRule("completed", "timestamp"),
        ),
        timestamp_order=(("started", "completed"),),
        duplicates="error",
    )
    frame = pl.DataFrame(
        {
            "label": [" ", " "],
            "started": ["not-a-time", "not-a-time"],
            "completed": ["also-invalid", "also-invalid"],
        }
    )
    assert validate_frame(frame, contract) == ()


def test_invalid_rows_do_not_establish_duplicate_identity():
    """Match existing policy by excluding blocking rows before key comparison."""
    contract = DataContract(
        (ColumnRule("measurement"), ColumnRule("key", "integer")),
        key_columns=("key",),
    )
    issues = validate_frame(
        pl.DataFrame({"measurement": [float("inf"), 1.0], "key": [1, 1]}),
        contract,
    )
    assert [(issue.code, issue.rows) for issue in issues] == [("NONFINITE", (0,))]


@pytest.mark.parametrize(
    "positions",
    [
        (0,),
        (-1, 0),
        (0, 0),
        (False, 1),
    ],
)
def test_source_positions_must_be_complete_unique_and_nonnegative(positions):
    """Reject invalid identity mappings before translating diagnostics."""
    with pytest.raises(ValidationError, match="Source positions"):
        validate_frame(
            pl.DataFrame({"value": [1.0, None]}),
            DataContract((ColumnRule("value", nullable=True),)),
            source_positions=positions,
        )


def test_validation_requires_canonical_polars():
    """Keep Pandera behind the canonical Polars boundary."""
    invalid_frame: Any = {"value": [1]}
    with pytest.raises(TypeError, match="canonical Polars"):
        validate_frame(invalid_frame, DataContract((ColumnRule("value"),)))
