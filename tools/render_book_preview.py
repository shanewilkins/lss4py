"""Execute the checked-in public-API example and render its HTML, notebook and audit bundle."""

import io
import json
import platform
import re
import runpy
from contextlib import redirect_stdout
from html import escape
from pathlib import Path

import narwhals
import numpy
import polars
import scipy

from lss4py import AnalysisBundle, InputReference, __version__


def main() -> None:
    """Render actual execution output while keeping prepared-input declarations inspectable."""
    root = Path(__file__).resolve().parents[1]
    example = root / "examples/white_belt/preview.py"
    output = root / "examples/white_belt"
    stream = io.StringIO()
    with redirect_stdout(stream):
        executed = runpy.run_path(str(example))
    text = stream.getvalue()
    results = {name: executed[name] for name in ("mean_lead", "p90", "promise", "pce")}
    reference = InputReference.from_bytes(
        "washnfold-friday91/1.0.0/order_summary.csv",
        executed["source"].read_bytes(),
        selection="All 39 prepared order summaries",
        media_type="text/csv",
    )
    if reference.sha256 != executed["source_sha256"]:
        raise ValueError("Prepared input changed after ingestion.")
    ingestion = executed["ingestion"]
    bundle = AnalysisBundle.capture(
        "White Belt prepared-data preview",
        results=results,
        inputs={"orders": reference},
        result_inputs={name: ["orders"] for name in results},
        cohort_definition=executed["contract"].cohort,
        software_versions={
            "lss4py": __version__,
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "polars": polars.__version__,
            "narwhals": narwhals.__version__,
            "scipy": scipy.__version__,
        },
        context={
            "order_summary_contract": executed["contract"].to_dict(),
            "validation_report": executed["validation"].to_dict(),
            "ingestion": {
                "source_sha256": ingestion.source_sha256,
                "bindings": ingestion.bindings,
                "clock": ingestion.clock,
                "transformations": ingestion.transformations,
            },
            "input_preparation": "Supplied order summaries; event reconstruction not performed",
            "eligible_selection": "arrival <= operating minute 120",
            "exclusions": [],
        },
    )
    (output / "preview-bundle.json").write_text(bundle.to_json() + "\n")
    source = example.read_text()
    setup, cell = source.split("# Preview cell:", 1)
    cell = cell.split("\n", 1)[1]
    rows = [re.split(r"\s{2,}", line.strip(), maxsplit=1) for line in text.strip().splitlines()[1:]]
    table = "".join(
        f"<tr><th>{escape(name.strip())}</th><td>{escape(value.strip())}</td></tr>"
        for name, value in rows
    )
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>White Belt · Wash n’ Fold baseline</title>
<style>body{{font:17px/1.6 system-ui;margin:48px auto;padding:0 24px;
max-width:1000px;color:#193038;background:#f7faf9}}
h1{{line-height:1.2}}table{{width:100%;border-collapse:collapse;background:white;margin:28px 0}}
th,td{{padding:16px;text-align:left;border-bottom:1px solid #d9e5e0}}
td{{font-weight:650;color:#12634f}}
pre{{overflow:auto;background:#132c32;color:#e2f4ec;padding:24px;font-size:13px;border-radius:8px}}
small{{color:#4d6468}}summary{{cursor:pointer}}a{{color:#12634f}}</style>
<h1>Wash n’ Fold baseline</h1><p>Four familiar measures from simulated representative Friday 91.</p>
<p><strong>Prepared inputs:</strong> washnfold-friday91 v1.0.0, 39 supplied order summaries.
Activity-to-order reconstruction is outside this preview. All times use cumulative operating minutes
from 07:00 with closed hours excluded.</p>
<table><caption>Drop-off queue entry through final readiness notification</caption>{table}</table>
<p><small>PCE uses 3,535.3 VA / 25,840.5 lead-time minutes across the same 39 orders.
VA includes right-first-time Wash, Dry, Fold and package, and notification. Staging is RNVA;
failed packaging and corrections are NVA.</small></p>
<h2>Runnable preview cell</h2>
<p>The book supplies the data and declarations below; learners need no setup cell.</p>
<pre>{escape(cell)}</pre><details><summary>Inspect supplied data bindings and validation</summary>
<pre>{escape(setup)}</pre></details>
<p><a href="preview-bundle.json">Inspect analytical evidence</a> ·
<a href="preview.ipynb">Executed notebook</a> · <a href="preview.py">Full runnable source</a> ·
<a href="order_summary.csv">Prepared observations</a></p>
<p><small>Data: Shane M. Wilkins, <em>Modern Process Improvement with Python</em>,
<a href="https://github.com/shanewilkins/modern-process-improvement">source</a>,
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. CSV unchanged;
LSS4PY analysis and formatting added.
<a href="SOURCE_LICENSE.md">Source notice</a>.</small></p></html>"""
    (output / "preview.html").write_text(html)
    # The notebook is self-contained beside its supplied CSV; the setup executes automatically.
    notebook_setup = setup.replace(
        'source = Path(__file__).with_name("order_summary.csv")',
        'source = Path("order_summary.csv")',
    )
    excerpt = (
        "## Reproduce the baseline with Python\n\n"
        "The book supplies the prepared order summaries and their measurement declarations. "
        "This cell reproduces the four baseline measures using lss4py. "
        "The activity-to-order preparation is separate; the customer boundary and "
        "operating clock are the same ones used in the worked calculations.\n\n"
        "```{python}\n#| echo: false\n" + notebook_setup + "\n```\n\n"
        "```{python}\n" + cell + "\n```\n"
    )
    (output / "preview.qmd").write_text(excerpt)
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}
        },
        "cells": [
            {
                "cell_type": "markdown",
                "id": "prepared-input-notice",
                "metadata": {},
                "source": [
                    "# Wash n’ Fold baseline\n",
                    "Prepared washnfold-friday91 v1.0.0 order summaries.\n",
                    "Data: Shane M. Wilkins, Modern Process Improvement with Python, CC BY 4.0.\n",
                    "See SOURCE_LICENSE.md.\n",
                    "The book build executes the supplied preparation cell.\n",
                    "The visible cell uses public lss4py calculations.\n",
                ],
            },
            {
                "cell_type": "code",
                "id": "supplied-preparation",
                "metadata": {"tags": ["hide-input"]},
                "source": ("#| echo: false\n" + notebook_setup).splitlines(keepends=True),
                "execution_count": 1,
                "outputs": [],
            },
            {
                "cell_type": "code",
                "id": "visible-preview",
                "metadata": {},
                "source": cell.splitlines(keepends=True),
                "execution_count": 2,
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": text.splitlines(keepends=True),
                    }
                ],
            },
        ],
    }
    (output / "preview.ipynb").write_text(json.dumps(notebook, indent=2) + "\n")
    print(text, end="")
    print(f"Rendered {output / 'preview.html'}")


if __name__ == "__main__":
    main()
