# LSS4PY Release Quality Gate

Act as an independent technical consultancy reviewing this repository.

The question is whether LSS4PY is a credible, correct, maintainable, and usable
Lean Six Sigma analytics library at its **currently declared version and stable
surface**. Separately assess its readiness to advance to the **next roadmap gate**.
Do not judge the repository as though every pre-1.0 roadmap feature is already
promised today.

Assess only the current working tree and checked-in evidence. Do not infer completed
work from roadmaps, ADRs, requirement status, type signatures, placeholders, issue
references, or comments. Distinguish implemented behavior, automated validation,
documented intent, contradictions, and unknowns throughout the report.

## Review basis

Read at least these sources before reaching conclusions:

- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `LICENSE.md`;
- `pyproject.toml` and `uv.lock`;
- `docs/README.md`, `docs/analysis-journey.md`, and `docs/roadmap.md`;
- all ADRs under `docs/adr/`;
- the user requirements, technical requirements, and traceability CSVs under
  `docs/requirements/`;
- `docs/sixsigma-compatibility.md`;
- the public package exports, implementation code, and tests under `src/` and
  `tests/`;
- `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, and `.importlinter`; and
- the current Git status and diff, noting which evidence is uncommitted.

Infer the version under review from `pyproject.toml`. Infer the current stable API
only from consistent public documentation, exports, implementation, and tests. If
those sources disagree, report the disagreement instead of choosing the most
favorable interpretation.

## Product and quality objectives

Use these objectives when evaluating the current release:

1. A practitioner can identify the supported analytical surface and use it without
   accidentally relying on a stub, experimental API, or roadmap promise.
2. Stable process-time, efficiency, takt, and yield calculations use explicit
   units, populations, denominators, and missing-data behavior and produce correct
   results over valid boundary cases.
3. Invalid data, impossible process structures, ambiguous overlap, unmodeled
   rework, zero denominators, and unsupported study conditions fail or warn
   explicitly rather than producing plausible but misleading results.
4. Process-model and event-log behavior is deterministic: bindings, precedence,
   row/case identity, sequence, parallel paths, and rework semantics are documented
   and tested.
5. Public contracts are Pythonic and can evolve toward the governed
   dataframe-neutral architecture without silently embedding pandas index, null,
   ordering, or coercion semantics.
6. Analytical results preserve assumptions, warnings, method context, units, and
   provenance appropriate to the claim, while calculation remains separable from
   optional rendering and delivery layers.
7. R `SixSigma` compatibility is claimed only where versioned numerical fixtures,
   tolerances, edge cases, and intentional differences provide evidence.
8. A contributor or user can reproduce, test, build, install, and smoke-test the
   supported package from the locked repository, with architecture and dependency
   boundaries enforced.
9. Requirements, traceability, compatibility status, documentation, and the
   versioned roadmap accurately describe the same product state.

For next-gate readiness, use the belt scope and release gates in
`docs/roadmap.md`. Belt labels describe supported practitioner workflows, not
certification or professional-competence claims.

## Consultant panel

Evaluate through these distinct lenses. Do not use clean code or passing tests as
a substitute for evidence of statistical validity or practitioner usefulness.

| Consultant | Primary remit |
| --- | --- |
| Lean Six Sigma product owner and Yellow Belt practitioner | End-to-end DMAIC usefulness, current scope, workflow gaps, and whether the API helps complete real improvement work. |
| Master Black Belt or quality-engineering SME | Fidelity to Lean Six Sigma concepts, belt-level scope, CTQs, specifications, control limits, measurement systems, and interpretation boundaries. |
| Applied statistician | Estimands, assumptions, uncertainty, study design, diagnostic behavior, small samples, multiplicity, and avoidance of unsupported causal claims. |
| Scientific/numerical software engineer | Formula correctness, numerical stability, units, missing values, degeneracy, reference oracles, tolerances, and reproducibility. |
| Python library and dataframe interoperability architect | Public API design, typing, result contracts, serialization, pandas/Polars neutrality, materialization, optional dependencies, and migration risk. |
| Software architect and maintainer | Module boundaries, error model, complexity, maintainability, dead code, dependency direction, and consistency with accepted or proposed ADRs. |
| Test, release, and supply-chain engineer | Test strength, coverage meaning, CI parity, locked builds, wheel installation, CLI smoke tests, dependency exposure, and release safety. |
| Documentation and practitioner-education specialist | Discoverability, examples, terminology, explanation of assumptions, learning usability, and prevention of analytical misuse. |

After using the panel, state whether these are the right perspectives for the next
roadmap gate. Recommend an additional specialist only for a concrete decision or
evidence gap—for example, a metrologist for advanced MSA, a reliability engineer
for time-to-event methods, or a domain practitioner for external validation.

## Fixed scoring rubric

Score every category from 0 to 4 using these exact definitions:

| Score | Meaning |
| --- | --- |
| 0 | Absent, contradicted by the repository, or creates an unacceptable correctness, data-integrity, security, or release risk. |
| 1 | Intent is documented, but implementation or validation is materially incomplete for the current claim. |
| 2 | Partially implemented; important gaps, unvalidated assumptions, or unreliable paths remain. |
| 3 | Implemented and supported by relevant evidence; only bounded, non-blocking gaps remain. |
| 4 | Implemented, independently well-validated for the current scope, and protected against foreseeable failure and change. |

Do not average scores mechanically. A score of 0 or 1 in statistical correctness,
input/data integrity, stable API truthfulness, or build/install reliability is a
release blocker regardless of other scores.

Score these categories:

1. Current-scope truthfulness and practitioner journey
2. Statistical and Lean Six Sigma correctness
3. Input validation, units, and failure safety
4. Process-model and event-log semantics
5. API, result-model, and dataframe portability
6. Numerical reference evidence and R `SixSigma` parity
7. Architecture, dependencies, and maintainability
8. Automated tests, static analysis, and change detection
9. Documentation, examples, and misuse resistance
10. Packaging, security, reproducibility, and release operations
11. Requirements, traceability, and roadmap integrity

## Evidence rules

For every score, finding, and recommendation:

- cite repository paths and the most relevant symbols, tests, configuration, CSV
  requirement IDs, or documented contracts;
- label evidence as `Implemented`, `Validated`, `Documented intent`,
  `Contradiction`, or `Unknown`;
- state the affected objective number(s), user consequence, and release
  implication;
- name what a test proves; an import test proves importability, not numerical
  correctness or practitioner usability;
- do not count `NotImplementedError`, empty scaffolds, typed signatures, roadmap
  entries, or proposed ADRs as implemented capability;
- do not treat the configured 95% coverage threshold as whole-package coverage
  without examining the exclusions in `pyproject.toml`;
- distinguish example-based tests, property/boundary tests, independent published
  references, upstream-library comparisons, and R parity fixtures;
- inspect missing values, non-finite values, time zones, ordering, duplicate keys,
  zero denominators, tiny samples, degenerate variation, one-sided specifications,
  parallel work, and rework where relevant;
- do not penalize deliberately deferred features unless the README claims them,
  they are required by the version under review, or their absence makes a current
  workflow unsafe or unusable;
- audit every `Satisfied` requirement against implementation and validation rather
  than trusting its status cell;
- flag undocumented differences among the README, `lss4py.__all__`, tests,
  requirement catalogs, roadmap, and compatibility matrix; and
- mark claims requiring user research, external subject-matter review, independent
  numerical replication, other dataframe engines, or production package-index
  evidence as `Unknown`, with a concrete validation step.

## Repository checks

Run the following from the repository root when the environment permits. Record
the exact commands, result, and any deviation from CI:

```bash
uv lock --check
uv run --locked ruff check .
uv run --locked lint-imports
uv run --locked vulture src tests --min-confidence 80
uv run --locked xenon --max-absolute C --max-modules A --max-average A src/lss4py tests
uv run --locked pyright
uv run --locked pytest --cov=src/lss4py --cov-report=term-missing
uv build
```

Also inspect the CI wheel smoke test and, when practical, install the built wheel
into a clean environment outside the source tree and exercise both `import lss4py`
and `lss4py doctor`. A failed command is evidence to analyze, not permission to
change the repository during the review.

## Required report format

Save the report as `notes/quality_gate_YYYY_MM_DD.md`, replacing the date with the
review date. Do not modify product code while performing the review.

Use this structure exactly:

1. `# LSS4PY Quality Gate: v<version>`
2. **Review scope and evidence limits**: version, commit and working-tree state,
   sources examined, commands run, and unavailable evidence.
3. **Executive decisions**: one current-release decision—`Ready to release`,
   `Ready with conditions`, `Not ready to release`, or `Insufficient evidence`—and
   one next-roadmap-gate assessment—`On track`, `At risk`, `Blocked`, or
   `Insufficient evidence`.
4. **Declared-surface audit**: public claim or API, implementation status,
   validation strength, strongest evidence, contradiction or gap, and release
   implication.
5. **Objective coverage table**: one row per objective with implementation status,
   validation status, strongest evidence, gap or risk, and decision implication.
6. **Scorecard**: one row per fixed category with score, evidence, strengths,
   weaknesses, affected objectives, and blocker status.
7. **Consultant findings**: the most consequential findings under every consultant
   lens, including questions the repository cannot answer.
8. **Strengths to preserve**: no more than five evidence-backed strengths.
9. **Risks and weaknesses**: rank each `Critical`, `High`, `Medium`, or `Low` and
   include evidence, consequence, affected objectives, and whether it blocks the
   current release or next gate.
10. **Requirements and compatibility audit**: unsupported `Satisfied` statuses,
    untraced requirements, stale evidence, R parity overclaims, and roadmap drift.
11. **Prioritized improvement plan**: no more than ten actions, each with owner
    role, priority, expected user outcome, acceptance criteria, smallest credible
    validation, dependencies, and target release.
12. **Team adequacy**: sufficient current perspectives, missing expertise needed
    now, and expertise that can wait.
13. **Open questions and evidence plan**: unresolved questions and the cheapest
    credible way to answer each.

## Consistency check before finalizing

Before saving the report, verify that:

- all nine product and quality objectives appear exactly once in the objective
  coverage table;
- all eleven scoring categories have exactly one score and evidence statement;
- current-release blockers are separated from risks to the next roadmap gate;
- every `Critical` or `High` risk has a prioritized action or an explicit reason it
  cannot yet be addressed;
- every recommendation has an acceptance criterion and validation method;
- every compatibility claim is consistent with the compatibility matrix and its
  available fixture evidence;
- requirement status is treated as a claim to audit, not proof;
- the final decisions follow from the evidence and fixed rubric; and
- repository facts are clearly separated from practitioner research, independent
  statistical review, package-index behavior, and future-roadmap assumptions.
