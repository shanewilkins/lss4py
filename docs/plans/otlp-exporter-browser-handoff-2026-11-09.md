# OTLP exporter dependency: marimo browser handoff

- Date: 2026-11-09
- From: MPI book/LMS integration work
- Status: Investigation finding and recommended packaging change; not implemented
- Scope: Remove an apparently unused mandatory exporter without changing analytical behavior

## Request

Please review removing `opentelemetry-exporter-otlp>=1.31.0` from core dependencies in `pyproject.toml`.
Keep `opentelemetry-api` and `opentelemetry-sdk`, which the current telemetry implementation uses.
If a real remote-export use case is introduced later, its exporter can be installed through an optional extra rather than required for every analytics or notebook user.
There is no need to add an unused extra solely to preserve the current dependency declaration.

## Evidence in this repository

- `pyproject.toml` lists API, SDK and OTLP exporter as direct core dependencies.
- `src/lss4py/observability/telemetry.py` imports `trace`, `Resource`, `TracerProvider`, `BatchSpanProcessor` and `ConsoleSpanExporter` from the API/SDK.
- `configure_telemetry()` configures console export; it does not instantiate an OTLP exporter.
- Repository searches found no imports from `opentelemetry.exporter`, `OTLPSpanExporter` or `OTLPMetricExporter` in Python source or tests.
- `tests/test_observability.py::test_telemetry_exports_real_spans_without_installing_a_global_provider` verifies console spans, parent/child relationships, service naming and provider-state isolation.

The API/SDK are used; the finding concerns the separate OTLP exporter distribution specifically.
The suggested change preserves existing console telemetry and does not remove observability wholesale.
Please confirm there are no supported external-consumer promises or release obligations requiring that exporter to be installed implicitly.

## Observed browser failure

The book team created a self-contained synthetic marimo workbook at `modern-process-improvement/templates/yellow_belt_browser_probe.py`.
Its native reference uses released lss4py 0.2.2, flo-lang 0.5.0, marimo 0.25.2 and Python 3.14.
The workbook executes numerical analysis, validation, provenance, real FLO export/rendering and downloadable evidence locally.
The owner accepts local marimo execution; browser compatibility is useful but does not block local delivery.

The actual marimo offline exporter runs dependency resolution in Pyodide 314.0.0 / Python 3.14.0.
After selecting the Polars WASM wheel available in that runtime, resolution fails with:

```text
ValueError: Can't find a pure Python 3 wheel for 'grpcio<2.0.0,>=1.75.1; python_version >= "3.14"'.
```

The relevant dependency path is:

```text
lss4py
  -> opentelemetry-exporter-otlp
     -> opentelemetry-exporter-otlp-proto-grpc
        -> grpcio
```

An earlier, separate failure selected native `polars-runtime-32==2.1.0`.
The workbook now requests Pyodide's Polars 1.33.1 only on `emscripten`, with the native constraint kept separate.
This addressed the observed Polars resolution mismatch; it did not bypass grpcio or establish complete browser compatibility.
The exporter stops at the grpcio failure, so subsequent package, import, threading and rendering behavior remains unverified.
No dependencies were silently dropped and no metadata was patched to claim success.

## Suggested implementation and acceptance

1. Remove the unused OTLP exporter from core requirements and synchronize `uv.lock`.
2. Run existing observability tests, the normal repository quality gates and an installed-wheel analytical journey.
3. Inspect the built wheel's `Requires-Dist` and resolve a fresh base installation to verify that this dependency path no longer brings in grpcio.
   Another independently requested integration may still require grpcio; the claim is about the base lss4py install.
4. Confirm console telemetry remains functional and does not add unwanted global-provider state changes.
5. Hand the book team an exact candidate wheel with its hash, or publish the change through the normal release process.
   Changing this checkout or its lockfile does not repair already-published lss4py 0.2.2 metadata.
6. Rerun the actual marimo/Pyodide resolution and workbook operations against that candidate.
   Removing this blocker is not, by itself, proof of browser execution or save/reopen compatibility.

The existing native mock and five independent numerical/integration tests provide a reusable reference.
The full book suite passed 372 tests; local editor response download, notebook-source export and edited-source reopening were verified.
The detailed consumer record is `modern-process-improvement/docs/specifications/yellow_belt_browser_probe.md`.

## Browser reproduction from the book repository

```console
uv run --locked marimo export html-wasm templates/yellow_belt_browser_probe.py --mode edit --offline -o /tmp/yb-browser-probe-offline
```

Use a fresh output destination and update the notebook's pinned lss4py requirement deliberately when testing a new release or candidate.
The current source pins released 0.2.2, so an unchanged run should reproduce the existing packaging failure rather than test a modified sibling checkout.
This note requests no deployment, hosted notebook service, telemetry activation or upstream change on the team's behalf.
