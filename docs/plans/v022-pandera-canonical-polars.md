# v0.2.2 Pandera and canonical Polars plan

- Status: Approved for implementation
- Approved: 2026-11-05
- Release: 0.2.2
- Scope: Dataframe execution and validation architecture
- Follow-up: Resume the v0.3 moving-range control-chart slice after 0.2.2

## Objective

LSS4PY 0.2.2 adopts Pandera for private tabular validation and establishes a
middle-road dataframe architecture:

- public analytical APIs continue accepting eager Polars DataFrames, pandas
  DataFrames and PyArrow Tables;
- supported inputs are canonicalized internally to Polars;
- Pandera validates the canonical Polars representation;
- analytical kernels execute against Polars instead of three native dataframe
  engines;
- source backend, schema, order and identity remain visible in provenance; and
- public results and accepted-input behavior remain compatible with 0.2.1.

This is an infrastructure release. Moving-range control-chart implementation
resumes only after 0.2.2 is accepted and published.

## Non-goals

0.2.2 does not:

- implement a moving-range or other control chart;
- add a new statistical method;
- make Pandera schemas part of the public API;
- expose Pandera exception classes or message text;
- use Pandera decorators on public analytical functions;
- enable coercion or automatic invalid-row deletion;
- change analytical formulas;
- make pandas or PyArrow base dependencies;
- replace Pydantic exchange validation;
- replace the standard-library bundle validator; or
- modify the book repository.

## Architecture target

The public and internal boundaries deliberately differ:

| Boundary | Contract |
| --- | --- |
| Public analytical input | Eager Polars, pandas or PyArrow |
| Input recognition and conversion | Private Narwhals boundary |
| Canonical analytical representation | Polars |
| Tabular structural validation | Private Pandera Polars schemas |
| Analytical semantics | LSS4PY kernels and domain contracts |
| Public errors | LSS4PY exception and issue models |
| Provenance backend | Original caller backend plus canonical execution evidence |

Narwhals remains useful for recognizing supported eager inputs, inspecting their
source schema and converting required columns. It no longer serves as the
expression-execution abstraction inside analytical kernels.

## Phase 1: freeze the 0.2.1 baseline

**Status:** Complete. See the
[canonicalization baseline assessment](../assessments/v022-canonicalization-baseline.md).

Preserve evidence before changing the dataframe boundary.

1. Record the current commit and locked dependency state.
2. Run and retain the complete locked source gates, numerical fixtures, R
   verification and installed-wheel journeys.
3. Add missing characterization cases for:
   - pandas nullable integer, float, boolean and string dtypes;
   - pandas categoricals and duplicate indexes;
   - timezone-aware timestamps;
   - PyArrow chunked and dictionary arrays;
   - null versus NaN;
   - non-string column names;
   - row ordering;
   - lazy and unsupported inputs; and
   - source immutability.
4. Capture neutral result payloads for differential comparison.

**Gate:** the existing complete matrix must be green and reproducible before the
canonicalization refactor begins.

## Phase 2: dependency and installation contract

Add Pandera as a bounded direct dependency with Polars support. The intended
constraint is:

```toml
"pandera[polars]>=0.35,<0.36"
```

Confirm the exact floor against Python 3.14 and the locked Polars version before
finalizing the lock.

Do not install or activate Pandera's pandas, PyArrow or Narwhals validation
backends. Pandera receives only canonical Polars frames.

Verify that:

- the base installation contains Polars, Narwhals and Pandera;
- the base installation does not contain pandas or PyArrow;
- the pandas extra installs pandas without activating Pandera's pandas backend;
- the storage extra installs PyArrow without activating Pandera's PyArrow backend;
- importing LSS4PY does not change Pandera global configuration; and
- no `PANDERA_USE_NARWHALS_BACKEND` setting is required.

## Phase 3: canonical analytical input boundary

Introduce a private canonical-input model carrying:

- the canonical Polars frame;
- original source backend;
- original logical schema;
- original row count; and
- selected canonical columns.

The canonicalization operation must:

1. reject lazy and unsupported inputs;
2. detect and retain the original backend;
3. validate string and unique column identity;
4. capture the original logical schema and row count;
5. select only columns required by the method when safe;
6. materialize a detached Polars frame;
7. preserve exact source-row order;
8. retain zero-based source positions where row identity matters;
9. ignore pandas indexes as analytical identity; and
10. never mutate the caller's object.

Prefer required-column materialization over unconditional whole-frame conversion.
Inspect the complete source schema separately when provenance requires it.

Preserve the current provenance backend as the caller's source backend. Add
consistent evidence for the Polars execution backend and selected-column
canonicalization. Any provenance-model change must be wired through result
serialization, bundles and the standalone bundle validator.

## Phase 4: private Pandera validation

Create one private integration module rather than importing Pandera throughout
kernels.

All schemas use:

- `coerce=False`;
- `drop_invalid_rows=False`;
- extra columns permitted unless a contract deliberately closes the schema;
- lazy validation where aggregated findings are useful; and
- no process-global Pandera configuration changes.

Translate Pandera failures into LSS4PY-owned diagnostics:

- stable `DataIssue` codes;
- severity;
- governed messages;
- affected columns; and
- zero-based source-row positions.

Do not expose raw measurements unnecessarily, Pandera exception classes,
documentation URLs, backend stack traces or unstable third-party wording.

Compile existing `DataContract` declarations into Pandera Polars schemas for:

- required columns;
- numeric, integer, string, boolean and timestamp roles;
- nullability;
- finite bounds;
- key uniqueness; and
- supported row-wise checks.

Keep custom LSS4PY validation for timestamp ordering, units, duplicate policy,
portable key identity, cross-column business rules and analytical cohort
semantics.

## Phase 5: incremental migration

Do not convert every path in one patch.

### 5.1 Data-quality path

Migrate `validate_data`, `DataContract`, `ColumnRule` and
`DataValidationReport` first. Preserve public serialization.

`normalize_data` retains its documented output-backend behavior. A canonical
validation copy does not make public normalization Polars-only.

### 5.2 Shared extraction

Replace repeated Narwhals analytical extraction with shared Polars helpers for:

- numeric measurements;
- missing masks;
- finite checks;
- exact binary columns;
- portable keys;
- source positions; and
- first-observed group ordering.

### 5.3 Analytical families

Migrate in bounded batches:

1. descriptive statistics, mean inference and distribution profiles;
2. capability indices and defect/rework yield;
3. timing, efficiency, deadline and stage-yield methods;
4. process-map and event-log paths accepting generic frames; and
5. provenance, bundle and export helpers affected by the new boundary.

After each batch, run focused tests, compare neutral payloads against the baseline,
exercise all supported source backends and verify source immutability.

### 5.4 Boundary enforcement

At completion:

- Narwhals remains only in private input recognition and canonicalization;
- analytical kernels execute no Narwhals expressions;
- kernels contain no pandas- or PyArrow-specific branches; and
- import-linter enforces the new dependency direction.

## Phase 6: differential and performance evidence

Compare the old and new implementations over the governed corpus:

- result values;
- missing counts;
- warning codes;
- source positions;
- key and group ordering;
- schema fingerprints;
- provenance;
- serialized bundles;
- exception types; and
- invalid-input acceptance and rejection.

Differences require explicit review and documentation.

Benchmark native Polars, pandas and PyArrow inputs using narrow and wide frames.
Record conversion time, validation time, total analysis time and peak memory.
The native Polars path should avoid unnecessary full-frame copying. Document the
materialization cost for pandas and PyArrow.

Record dependency and packaging effects:

- base wheel size;
- installed package count;
- import time;
- dependency audit;
- exact Pandera, Polars and Narwhals versions; and
- confirmation that pandas and PyArrow do not leak into the base installation.

## Phase 7: ADR and governance

After implementation satisfies the differential and performance gates, add an
accepted ADR titled approximately:

> Canonicalize supported eager analytical inputs to Polars

The ADR partially supersedes the analytical-execution language in ADR-0018 and
records:

- broad public inputs and narrow internal execution;
- Polars as the canonical analytical representation;
- Narwhals as the compatibility and conversion boundary;
- Pandera as private Polars validation machinery;
- source versus execution backend provenance;
- materialization and allocation policy;
- no pandas-index identity;
- no implicit lazy collection;
- no coercion or row dropping; and
- LSS4PY ownership of public errors and analytical semantics.

Reconcile:

- UR-015, which remains satisfied;
- TR-002, which remains neutral at the public input boundary;
- TR-014, which changes from Narwhals execution to Narwhals-assisted
  canonicalization;
- TR-017, which verifies equivalent results after canonicalization;
- TR-022, which gains Pandera-backed validation evidence; and
- TR-010, which records the dependency and optional-backend boundaries.

Update the architecture, backend contract, data-quality guide, extension guide,
README, migration guide, roadmap/progress material and release notes.

## Phase 8: release preparation

Update package and runtime identity to 0.2.2 only after the implementation gates
pass.

Required release checks:

1. locked pre-push source gates;
2. Pylance diagnostics;
3. Pandera differential tests;
4. complete supported-input matrix;
5. governed numerical fixtures;
6. R reference verification;
7. dependency vulnerability audit;
8. wheel and source build;
9. Twine metadata validation;
10. exact-wheel base journey;
11. exact-wheel pandas journey;
12. exact-wheel storage/PyArrow journey;
13. exact-wheel visualization/FLO ecosystem journey; and
14. official-index verification after publication.

0.2.2 is accepted only when:

- existing numerical outputs remain compatible;
- pandas, Polars and PyArrow inputs remain accepted;
- analytical kernels execute against canonical Polars;
- Pandera does not mutate, coerce or delete data;
- original backend provenance remains visible;
- pandas and PyArrow remain absent from the base installation;
- bundle restoration retains standalone validation; and
- every exact-wheel journey passes.

## Commit sequence

Use cohesive, independently testable commits:

1. `test: freeze dataframe canonicalization behavior`
2. `build: add bounded pandera dependency`
3. `refactor: add canonical polars input boundary`
4. `refactor: validate data contracts with pandera`
5. `refactor: move analytical kernels to canonical polars`
6. `docs: record canonical analytical dataframe boundary`
7. `release: prepare v0.2.2`

Run the complete gates before the release commit.

## Post-0.2.2 continuation

Resume the v0.3 moving-range control-chart slice on the finalized boundary:

1. define `ControlChartResult`;
2. implement Phase I moving-range limits;
3. apply frozen Phase II baselines;
4. preserve adjacent source-pair identity and signals;
5. add genuine `SixSigma::ss.cc` fixtures;
6. render prepared chart evidence through Matplotlib; and
7. add bundles, guidance, documentation and installed-wheel coverage.
