"""Execute supplied book assets against the installed public package without sibling data."""

import json
from pathlib import Path

import pytest


def test_supplied_preview_script_and_notebook(monkeypatch, capsys):
    """Execute both notebook cells and compare their output with the rendered example."""
    example = Path(__file__).parent / "fixtures" / "white_belt"
    if not example.exists():
        example = Path(__file__).resolve().parents[1] / "examples" / "white_belt"
    notebook = json.loads((example / "preview.ipynb").read_text())
    monkeypatch.chdir(example)
    namespace = {}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), "<book-preview>", "exec"), namespace)
    text = capsys.readouterr().out
    for value in ("662.6 min", "676.2 min", "6/21 (28.6%)", "13.7%"):
        assert value in text
    saved = "".join(notebook["cells"][-1]["outputs"][0]["text"])
    assert text == saved
    assert namespace["validation"].valid
    assert namespace["pce"].metadata["observation_count"] == 39
    assert namespace["pce"].metadata["aggregation"] == "ratio_of_sums"
    assert namespace["promise"].metadata["ineligible_count"] == 18
    assert namespace["p90"].provenance.parameters["percentile_method"] == "nearest_rank"


def test_supplied_activity_reconstruction_with_installed_package():
    """Reproduce complete orders without the book checkout or editable package."""
    import runpy

    example = Path(__file__).parent / "fixtures" / "white_belt"
    if not example.exists():
        example = Path(__file__).resolve().parents[1] / "examples" / "white_belt"
    namespace = runpy.run_path(str(example / "reconstruct.py"))
    result = namespace["reconstruct"](example / "event_log.csv")
    orders = result.to_polars()
    assert orders.height == 39
    assert orders["lead_time"].sum() == pytest.approx(25840.5)
    assert orders["value_add"].sum() == pytest.approx(3535.3)
    assert result.metadata["correction_occurrences"] == 5
