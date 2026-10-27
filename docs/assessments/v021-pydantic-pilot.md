# v0.2.1 S2: Pydantic process-payload pilot

Implemented 2026-10-26. Portable process projections now use private strict
Pydantic schemas for their structure. FLO still validates native documents
through its public facade; the bridge imports no FLO source or render models.
Internal dataclasses, numerical kernels, dataframe validation and the standalone
standard-library bundle validator are unchanged.

## Scope and dependency decision

`integration/_process_schema.py` describes the bridge envelope, producer process
identity, nodes, edges and mapping. Existing graph-reference, duplicate-node and
one-to-one mapping rules remain explicit in `integration/process.py`.

Pydantic is a direct core dependency, constrained to `>=2.12,<3`. The bridge was
already usable without FLO installed, including for saved/external JSON. Moving
its validator behind the FLO integration extra would break that installation
contract; maintaining a separate fallback would retain duplicate validation.
Pydantic is imported with the integration bridge, not by numerical kernels.

The lock already contained Pydantic 2.14.1 for optional FLO. This change does not
resolve a second Pydantic version or add packages to the lock graph, but it does
install Pydantic and its dependencies in base installations. That is an explicit
dependency cost. FLO and rendering packages remain optional, and their absence
is still enforced by the isolated base-installation tests.

## Compatibility policy

| Contract | Implementation |
| --- | --- |
| Strict consumed fields | Strings, object/list shapes, supported literal values and boolean flags are validated without coercion. Nonblank text is checked without stripping or rewriting it. |
| Closed envelope | All six bridge fields are required; unknown outer fields are rejected. |
| Extensible producer data | Unknown fields on the export, process, nodes and edges remain accepted. Previously unvalidated annotations retain their original JSON types. |
| Original serialization | Typed models are validation views only. Canonical JSON is still generated from the original parsed object, preserving unknown data, omitted fields, explicit nulls, false flags and numeric scalar representations. |
| Supported producer versions | 0.4.2 and 0.4.3 retain their original version tags, snapshots and fingerprints. New captures still default to 0.4.3. |
| Public errors | Shape errors are translated to `lss4py.errors.ValidationError` with field locations. Messages omit input payloads, Pydantic documentation URLs and exception chains. |
| Analytical semantics | Native FLO documents, work calendars, classification policy and numerical reconstruction are outside this pilot. |

For example, a string used as a rework flag now reports:

```text
Invalid process projection. export.edges.0.rework: Input should be a valid boolean
```

An unknown reference still reports the existing semantic failure, now with its
location:

```text
export.edges.0.target: FLO edge references an unknown step.
```

These are diagnostic examples rather than a promise of exact third-party message
wording. The public exception class and identifiable field location are tested.
Malformed reference types that previously leaked hashing/type errors now fail
through that same public validation error.

## Size and usefulness

The process module shrank from 247 to 181 lines. The explicit schemas and error
adapter add 82 lines, so the combined implementation is **263 lines**, 16 more
than before. It is not a net line-count reduction.

Across the old module versus both new modules, AST counts of `if`, `for`, `while`,
conditional expressions and `try` constructs fell from **28 to 18**. Declarative
field policies replace handwritten traversal/type/flag checks; cross-reference
rules remain visible. This and improved nested error locations justify retaining
the bounded pilot, not converting all domain dataclasses to Pydantic.

## Verification

Forty new source cases cover malformed nested fields, missing/extra envelope
fields, strict boolean rejection, whitespace-only keys, optional nulls,
extensible producer metadata, omitted defaults and nonfinite annotations.
Existing book/version tests retain their pinned fingerprints for both producer
profiles. The focused payload/book/integration run passes 98 tests.

A local differential probe compared the previous validator with the new one over
325 payload variants. All acceptance/rejection decisions agreed; all 65 accepted
variants retained byte-identical canonical snapshots and fingerprints. This is
bounded compatibility evidence, not an exhaustive proof or a claim of identical
error strings. Existing domain-error behavior is retained, while malformed
shapes receive clearer governed failures.

Installed-wheel tests exercise projection restoration and strict field errors in
the base, pandas, storage and ecosystem environments. They check that Pydantic is
declared directly rather than arriving accidentally through FLO. The standalone
bundle validation journey still runs with site-packages disabled.

Final local gates pass: **1,811 source tests**, five explicitly deferred expected
failures, and **93.39% full-package statement coverage**. The private schema module
has 100% statement coverage and the process module 98%. Installed-wheel stages
pass 26 base, 35 pandas, 37 storage and 44 ecosystem tests (**142 total**). Ruff,
formatting, Vulture, lockfile consistency, typing and all eight import boundaries
pass.

Reproduce the source and installed gates with:

```sh
uv run --locked pre-commit run --all-files --hook-stage pre-push
uv run --locked python tools/check_wheel.py --ecosystem --artifacts-dir artifacts/ecosystem
```

S2a (Pint and explicit unit handling) is the next slice. S3 still owns deriving
measurement policy from model classifications; this pilot does not implement it.
