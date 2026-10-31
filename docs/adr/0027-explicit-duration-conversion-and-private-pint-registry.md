# ADR-0027: Explicit duration conversion and a private Pint registry

- Status: Accepted
- Date: 2026-10-27
- Scope: v0.2.1 S2a

## Context

The book model uses `min`, while observations explicitly declare cumulative
operating minutes. LSS4PY's existing numerical and preparation APIs preserve
declared unit labels without inferring conversion. Pint can supply physical
duration factors, but its general registry cannot determine operating calendars
or analyst-specific counting and percentage semantics.

## Decision

Add Pint as a direct core dependency for a separate public preparation operation,
`convert_duration_columns`. It converts selected finite numeric columns on an
explicit unchanged clock, preserving backend and row identity and returning
portable evidence. Existing numerical functions and `normalize_data` keep their
current behavior.

Use a private, lazily initialized registry. Never set or consume the application
registry and never import private registry objects from FLO. Delegate physical
conversion factors to Pint and expose only a declared alias set for seconds,
minutes and hours. Reject days, custom/compound units and unrelated dimensions
until their analytical contracts are separately supported.

Store ordinary magnitudes and JSON declarations, not Pint quantities, registries
or Python pickles. Float64 limits and error behavior are explicit; no conversion
may silently reinterpret a numeric operating clock as calendar time.

## Alternatives and consequences

Implicit conversion in existing methods would change their declared-input
contract and hide which clock and unit the analyst supplied. A global application
registry would make results depend on mutable external definitions. A shared
private FLO registry would couple independent package implementations. A separate
optional extra would add installation branches for a core preparation operation.
These alternatives are not adopted.

Base installations gain Pint and its flexcache, flexparser and platformdirs
dependencies. Importing the numerical API does not initialize Pint. The narrow
alias contract deliberately exposes less
than Pint itself supports; expanding it requires tests and explicit clock/unit
semantics. Existing standard-library-only bundle validation remains independent
of this dependency.
