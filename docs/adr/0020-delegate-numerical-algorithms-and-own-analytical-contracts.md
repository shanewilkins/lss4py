# 0020: Delegate numerical algorithms while owning analytical contracts

- Status: Accepted
- Date: 2026-10-12
- Deciders: Maintainers
- Related requirements: UR-005, UR-006, UR-017, UR-023, UR-024, UR-033,
  TR-007, TR-008, TR-009, TR-010, TR-018, TR-019, TR-020, TR-023, TR-033
- Supersedes: [ADR-0003](0003-own-analytical-workflows-and-delegate-primitives.md)
  and [ADR-0006](0006-numerical-kernel-delegation.md)
- Complements: [ADR-0013](0013-backend-parity-testing.md),
  [ADR-0016](0016-private-kernel-architecture.md), and
  [ADR-0019](0019-reconcile-package-boundaries-and-event-log-contracts.md)

## Context

The Cp/Cpk implementation raised a recurring boundary question: which calculations
belong in LSS4PY, and which should use an established scientific library?
Feature parity with R SixSigma requires governed analytical outcomes, but does
not require matching its function layout or implementing a second statistics stack.

ADR-0003 proposed owning workflows and delegating primitives. ADR-0006 additionally
proposed a separate raw kernel result, version registry, and workflow wrapper for
every analysis. That mandatory decomposition conflicts with the simpler accepted
private-kernel architecture and current calculations returning typed results
directly. The boundary needs to describe responsibilities without requiring extra
layers for a small calculation.

## Decision

1. **LSS4PY owns analytical contracts.** A supported analysis connects a declared
   practitioner question to reproducible results. LSS4PY owns specification and
   opportunity semantics, cohort and exclusion policies, estimator selection,
   domain validation, suitability guidance, assumptions, diagnostics,
   interpretation limits, typed results, and provenance. Guidance lists candidates;
   callers explicitly select their question, cohort, and analysis. Observed data
   must not silently select and execute a statistical method.

2. **Delegate established numerical algorithms.** Use NumPy, SciPy, statsmodels,
   or another justified dependency for numerical primitives, distribution
   functions, statistical tests, fitting, and optimization when its behavior
   satisfies the analytical contract. Assess estimator definitions, numerical
   behavior, maintenance, licensing, dependency cost, and reproducibility.
   Adapt dependency results into LSS4PY contracts; upstream implementation objects
   are not the supported study-result interface.

3. **Small domain formulas may be implemented directly.** Transparent arithmetic
   such as specification distance, capability components, or declared yield
   ratios can live in private kernels. Reuse existing estimates and upstream
   primitives. Document the mathematical basis and verify it independently.
   A short formula does not justify a new dependency; an R discrepancy does not
   by itself justify duplicating a mature algorithm. Document intentional
   differences or justify a focused adaptation with reference evidence.

4. **Separate calculation, study, and presentation responsibilities.** Calculations
   validate formula inputs and return typed results. Studies orchestrate public
   calculations and diagnostics for a declared design and cohort. Presentation
   consumes results and remains optional; it must not silently recompute estimates
   or change their policies. An index calculation does not establish the normality,
   stability, or independence needed for its interpretation. A workflow is needed
   when orchestration has a distinct responsibility, not for every calculation.

5. **Preserve accepted package boundaries.** Calculations remain implemented in
   capability-oriented private `_kernels` and exported deliberately at the package
   root. Domain contracts remain independent; adapters own source I/O; Narwhals
   normalizes supported eager analytical inputs; Polars remains the canonical
   ingestion engine. Workflows orchestrate public APIs. This decision requires
   neither a new analytical layer nor raw kernel-result/version registries.

6. **R parity is a behavioral contract.** Map each retained R feature to the
   question answered, input roles and units, defaults and policies, estimators,
   result meanings, and invalid-domain behavior. One R function may map to several
   Python operations, and multiple R functions may share one result. Validate
   claimed behavior against checksummed, versioned SixSigma 0.11.1 fixtures with
   explicit tolerances. Record semantic differences and partial coverage in the
   compatibility matrix. Do not claim compatibility solely because an upstream
   dependency offers a similarly named function or a fixture has been generated.

7. **Keep evidence and runtime separate.** R is optional reference-development
   tooling with its own environment and CI. Python runtime and ordinary tests
   consume checked-in evidence without invoking R. Results record the selected
   method, estimator, parameters, exclusions, and relevant software versions;
   changing a numerical dependency must preserve the contract or document and
   validate its change.

## Applying the boundary

| Feature | Delegated machinery | LSS4PY responsibility |
| --- | --- | --- |
| Cp/Cpk | Array statistics and distribution quantiles | Specification policy, components, estimator declaration, intervals, diagnostics, provenance |
| Capability Z distance | Existing capability estimates | Distance to the governing limit; any conventional shift is explicit and does not establish measured long-term performance |
| Generic observation standardization | Scientific-library standardization | No separate public API is required solely for upstream function coverage |
| Defect/rework yield | Array reductions and arithmetic | Unit/opportunity denominators, counting and rework semantics, result names, invalid domains |
| Capability study | Fitting and statistical diagnostics | Study design, orchestration, interpretation, and auditable combined results |

## Alternatives considered

- **Reimplement the R algorithms and mirror its API.** Expands correctness and
  maintenance obligations and can preserve ambiguous names or invalid-domain
  quirks without serving the practitioner contract.
- **Expose only upstream wrappers or result objects.** Leaves domain decisions,
  exclusions, and interpretation fragmented and couples callers to dependencies.
- **Require raw kernel results and wrapper workflows everywhere.** Adds mandatory
  indirection without a separate responsibility for simple calculations. Private
  helpers remain appropriate where their reuse or complexity justifies them.

## Consequences

- Numerical reuse and explicit domain policy are both required design concerns.
- Each new feature needs a contract, dependency/formula rationale, reference and
  invalid-domain evidence, and backend tests where tabular input is supported.
- Simple calculations may return typed results directly; full studies still need
  deliberate orchestration and documented assumption checks.
- Dependency upgrades need targeted numerical regression checks. Replacing a
  dependency is an internal change only while the supported contract is preserved.
- This ADR establishes architecture; it adds no analytical implementation,
  compatibility promotion, release completion, or new release targeting.
