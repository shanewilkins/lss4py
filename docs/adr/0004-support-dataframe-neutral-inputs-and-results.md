# 0004: Support dataframe-neutral inputs and results

- Status: Proposed
- Date: 2026-08-09
- Deciders: Maintainers
- Related requirements: UR-012, UR-014, UR-015, TR-002, TR-014, TR-015, TR-016, TR-017

## Context

The current stable calculations accept pandas objects and return pandas `Series`.
That makes pandas semantics—especially its index and missing-value behavior—part of
the public contract. The intended users may instead work with Polars, PyArrow, or
other tabular engines.

The Python dataframe interchange protocol is not a suitable operational abstraction
for new LSS4PY code. Pandas recommends Arrow's C/PyCapsule interfaces instead for
new interchange work, and Polars has deprecated its `__dataframe__` support:

- https://pandas.pydata.org/docs/reference/api/pandas.api.interchange.from_dataframe.html
- https://docs.pola.rs/api/python/dev/reference/dataframe/api/polars.DataFrame.__dataframe__.html

Narwhals is designed for library authors that need dataframe-agnostic operations,
supports pandas, Polars, and PyArrow eager frames, and does not install those
backends itself:

- https://narwhals-dev.github.io/narwhals/
- https://narwhals-dev.github.io/narwhals/installation/

## Decision

LSS4PY will make its public analytical contract independent of pandas and Polars.

- Eager tabular inputs will use Narwhals' `IntoFrame` compatibility boundary.
- Pandas and Polars will be first-class tested backends; PyArrow will be a supported
  interchange/table backend where the required operations are available.
- Lazy inputs will be rejected initially with an actionable error. Full-sample
  statistical analyses must not trigger an implicit collection; a future lazy API
  requires a separate decision.
- Row identity will use explicit key columns or positional identifiers, not a pandas
  index contract.
- Statistical kernels may extract validated numeric arrays for NumPy/SciPy or
  statsmodels. Conversion, copying, null policy, and materialization must be
  explicit and tested.
- Scalar and multi-value analyses will return typed LSS4PY result models. Row-level
  results will use a backend-neutral keyed metric result with explicit conversion
  helpers, rather than returning a pandas `Series` unconditionally.
- Narwhals will be a base runtime dependency. Concrete dataframe engines will be
  development dependencies and user-selectable extras; after migration, pandas
  will no longer be mandatory for the base installation.

## Alternatives considered

- **Keep pandas as the canonical internal and public frame.** This is simplest but
  forces conversions and pandas semantics on every other backend.
- **Use Polars as the canonical frame.** This changes the favored backend rather
  than removing backend coupling.
- **Use `__dataframe__` directly.** Official pandas and Polars guidance makes this
  a poor forward-looking foundation.
- **Use Arrow tables as the only public input.** Arrow is a strong interchange
  format, but requiring users to convert before every analysis weakens the
  Python-native experience and does not provide a dataframe operations facade.
- **Maintain a custom dataframe protocol.** This would duplicate compatibility work
  and create a large backend test burden.

## Consequences

- The current pandas-returning APIs require a staged pre-1.0 migration.
- Backend equivalence tests become mandatory for public tabular calculations.
- Backend-specific behavior must be treated as a documented exception, not the
  default contract.
- Some operations may require an intentional copy into a numeric kernel; zero-copy
  behavior is desirable but not promised when correctness requires conversion.
- Supporting lazy/distributed frames remains separate future scope.

