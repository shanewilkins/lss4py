"""Private eager-input canonicalization boundary."""

from copy import deepcopy
from typing import Any

import pandas as pd
import polars as pl
import pytest

from lss4py._frames import canonical_frame
from lss4py.errors import ValidationError


def _snapshot(frame):
    if isinstance(frame, pd.DataFrame):
        return frame.copy(deep=True)
    if isinstance(frame, pl.DataFrame):
        return frame.clone()
    return deepcopy(frame.to_pylist()), frame.schema


def _assert_unchanged(frame, snapshot):
    if isinstance(frame, pd.DataFrame):
        pd.testing.assert_frame_equal(frame, snapshot)
    elif isinstance(frame, pl.DataFrame):
        assert frame.equals(snapshot)
    else:
        rows, schema = snapshot
        assert frame.to_pylist() == rows
        assert frame.schema == schema


@pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
def test_canonical_frame_selects_ordered_columns_and_retains_source_evidence(
    backend, frame_factory
):
    """Keep whole-source metadata while materializing only required columns."""
    frame = frame_factory(
        {
            "ignored": [9, 8, 7],
            "value": [2.0, None, 1.0],
            "label": ["b", "a", "c"],
        }
    )
    original = _snapshot(frame)
    canonical = canonical_frame(
        frame,
        ("label", "value"),
        retain_source_positions=True,
    )
    expected_backend = "pandas" if backend.startswith("pandas") else backend
    assert canonical.source_backend == expected_backend
    assert canonical.source_row_count == 3
    assert canonical.selected_columns == ("label", "value")
    assert canonical.execution_backend == "polars"
    assert [name for name, _ in canonical.source_schema] == ["ignored", "value", "label"]
    assert canonical.source_positions == (0, 1, 2)
    assert canonical.to_polars().to_dict(as_series=False) == {
        "label": ["b", "a", "c"],
        "value": [2.0, None, 1.0],
    }
    _assert_unchanged(frame, original)


@pytest.mark.parametrize(
    "backend", ["pandas", "pandas-indexed", "polars", "pyarrow"], indirect=True
)
def test_canonical_frame_is_detached_and_copy_safe(frame_factory):
    """Mutating returned Polars objects cannot change the source or stored frame."""
    frame = frame_factory({"value": [1, 2], "ignored": [3, 4]})
    original = _snapshot(frame)
    canonical = canonical_frame(frame, ("value",))
    first = canonical.to_polars()
    first.replace_column(0, pl.Series("value", [10, 20]))
    assert canonical.to_polars()["value"].to_list() == [1, 2]
    assert canonical.source_positions is None
    _assert_unchanged(frame, original)


@pytest.mark.parametrize("backend", ["pandas", "pandas-indexed", "polars"], indirect=True)
def test_canonical_frame_does_not_follow_mutable_source_changes(frame_factory):
    """Canonical values remain stable after caller-owned source replacement."""
    frame = frame_factory({"value": [1, 2]})
    canonical = canonical_frame(frame, ("value",))
    if isinstance(frame, pd.DataFrame):
        frame.loc[:, "value"] = [10, 20]
    else:
        frame.replace_column(0, pl.Series("value", [10, 20]))
    assert canonical.to_polars()["value"].to_list() == [1, 2]


def test_canonical_frame_deduplicates_selected_roles_in_first_seen_order():
    """One source column may satisfy multiple analytical roles without duplication."""
    canonical = canonical_frame(
        pl.DataFrame({"first": [1], "second": [2]}),
        ("second", "first", "second"),
    )
    assert canonical.selected_columns == ("second", "first")
    assert canonical.to_polars().columns == ["second", "first"]


def test_canonical_frame_preserves_categorical_values_and_source_schema():
    """Keep ordered labels while distinguishing source and execution dtypes."""
    frame = pd.DataFrame(
        {
            "label": pd.Series(
                ["b", "a", "b"],
                dtype=pd.CategoricalDtype(categories=["a", "b"], ordered=True),
            )
        }
    )
    canonical = canonical_frame(frame, ("label",))
    assert canonical.source_schema == (("label", "Enum(categories=['a', 'b'])"),)
    assert canonical.to_polars()["label"].to_list() == ["b", "a", "b"]


def test_canonical_frame_preserves_arrow_dictionary_and_chunked_values():
    """Materialize Arrow edge types without changing chunks or null positions."""
    pa = pytest.importorskip("pyarrow")
    labels = pa.chunked_array(
        [
            pa.array(["b", "a"]).dictionary_encode(),
            pa.array(["b"]).dictionary_encode(),
        ]
    )
    values = pa.chunked_array([[1.0, None], [3.0]])
    table = pa.table({"label": labels, "value": values})
    canonical = canonical_frame(table, ("label", "value"), retain_source_positions=True)
    assert canonical.to_polars().to_dict(as_series=False) == {
        "label": ["b", "a", "b"],
        "value": [1.0, None, 3.0],
    }
    assert canonical.source_positions == (0, 1, 2)
    assert table.column("label").num_chunks == 2
    assert table.column("value").num_chunks == 2


def test_canonical_frame_allows_empty_selection_with_source_metadata():
    """Support inspection when every declared contract column is absent."""
    canonical = canonical_frame(
        pl.DataFrame({"extra": [1, 2]}),
        (),
        retain_source_positions=True,
    )
    assert canonical.to_polars().shape == (0, 0)
    assert canonical.source_row_count == 2
    assert canonical.source_positions == (0, 1)


def test_canonical_frame_rejects_absent_selection():
    """Use a governed error for absent required-column selections."""
    with pytest.raises(ValidationError):
        canonical_frame(pl.DataFrame({"value": [1]}), ("missing",))


def test_canonical_frame_rejects_non_string_selected_names():
    """Internal callers cannot bypass the string column-identity contract."""
    invalid_columns: Any = ("value", 1)
    with pytest.raises(ValidationError, match="Selected column names must be strings"):
        canonical_frame(pl.DataFrame({"value": [1]}), invalid_columns)


@pytest.mark.parametrize(
    ("frame", "message"),
    [
        (pd.DataFrame([[1, 2]], columns=["value", "value"]), "must be unique"),
        (pd.DataFrame([[1]], columns=[1]), "must be strings"),
    ],
)
def test_canonical_frame_rejects_ambiguous_source_columns(frame, message):
    """Canonicalization enforces source identity before selecting columns."""
    with pytest.raises(ValidationError, match=message):
        canonical_frame(frame, ("value",))


def test_canonical_frame_rejects_ambiguous_options():
    """Reject string iteration and truthy position options from internal callers."""
    frame = pl.DataFrame({"value": [1]})
    invalid_position_option: Any = 1
    with pytest.raises(ValidationError, match="iterable of column names"):
        canonical_frame(frame, "value")
    with pytest.raises(ValidationError, match="must be boolean"):
        canonical_frame(
            frame,
            ("value",),
            retain_source_positions=invalid_position_option,
        )


@pytest.mark.parametrize(
    "values",
    [
        [1, 2.5],
        [True, 1],
        ["1", 1],
        [2**53 + 1, 2.5],
    ],
)
def test_canonical_frame_preserves_pandas_object_scalars(values):
    """Keep heterogeneous scalar identity for row-level structural validation."""
    source = pd.DataFrame({"value": pd.Series(values, dtype=object)})
    canonical = canonical_frame(source, ("value",))
    assert canonical.to_polars()["value"].dtype == pl.Object
    assert canonical.to_polars()["value"].to_list() == values


def test_canonical_frame_rejects_lazy_input_without_collecting(monkeypatch):
    """Canonicalization inherits eager-only rejection without executing a plan."""

    def fail(*_args, **_kwargs):
        pytest.fail("Lazy plan was executed")

    monkeypatch.setattr(pl.LazyFrame, "collect", fail)
    with pytest.raises(TypeError):
        canonical_frame(pl.DataFrame({"value": [1]}).lazy(), ("value",))
