# LSS4PY v0.2 Progress & Continuation Guide

**Last Updated:** 2026-09-02  
**Status:** In Progress — Architecture & Quality Gates Complete; Ready for Backend & Analysis Infrastructure  
**Version Target:** v0.2 (Contract Foundation)  
**Audience:** Developers returning to continue v0.2 work

---

## Quick Start for Continuation

When you return to this project, you can:

1. **Review this document** (2 min) for what's been completed and what remains
2. **Run the quality gates** (3 min) to confirm everything still passes:
   ```bash
   uv sync --locked --group dev
   uv run pre-commit run --all-files --hook-stage pre-push
   ```
3. **Pick the next task** from the "What's Next" section below
4. **Reference** [Architectural Decisions](#architectural-decisions) and [Known Deferrals](#known-deferrals-v03-work) as needed

---

## v0.2 Release Scope (Contract Foundation)

From `docs/roadmap.md`:

> Adopt backend-neutral input and result contracts, add reusable validation and normalization, 
> define CTQ/specification and provenance models, introduce analysis-guidance and parity-fixture 
> scaffolding, and preserve the working v0.1 slice while those contracts migrate.

**v0.2 is the foundation for all future releases.** It ensures:
- All inputs and outputs use backend-neutral Narwhals
- Result models include full provenance (who, what, when, why)
- Validation is reusable and composable
- Quality gates prevent AI-generated code from degrading standards

---

## What's Complete ✅

### 1. Architecture & Governance

| Item | Status | File(s) | Notes |
|------|--------|---------|-------|
| 5-layer architecture defined | ✅ | [docs/ARCHITECTURE.md](ARCHITECTURE.md) | Enforced via import-linter (7 contracts) |
| ADR-0016: Private kernels | ✅ | [docs/adr/0016-private-kernel-architecture.md](adr/0016-private-kernel-architecture.md) | Approved — kernels will be renamed `_kernels/` in v0.3+ |
| ADR-0017: Format adapters | ✅ | [docs/adr/0017-format-adapter-registry.md](adr/0017-format-adapter-registry.md) | Approved — registry pattern; pandas v0.2, OCEL 2.0 v0.3, XES v0.4 |
| Architecture audit checklist | ✅ | [docs/ARCHITECTURE.md#audit-checklist](ARCHITECTURE.md#audit-checklist) | Used during code review |

### 2. Result Models & Provenance (Sprint 1)

| Component | Status | Coverage | Notes |
|-----------|--------|----------|-------|
| Provenance dataclass | ✅ | 100% | method, method_version, package_version, backend, parameters, created_at, assumptions, warnings, input_schema_fingerprint |
| AnalyticalResult (ABC) | ✅ | 100% | Base class for all results; `to_dict()`, `to_json()`, `from_dict()` serialization |
| TimingResult | ✅ | 100% | lead_time, wait_time, cycle_time, takt_time; supports percentages and ratios for efficiency |
| YieldResult | ✅ | 100% | created_to_booked_yield, booked_to_completed_yield, rolled_yield |
| CapabilityResult, DescriptiveResult | ✅ | ~50% | Structure defined; methods deferred to v0.3+ |
| AnalysisBundle | ✅ | 100% | Aggregates multiple results with shared provenance |
| Tests (Sprint 1) | ✅ | 14/14 passing | Provenance, serialization, round-trips validated |

### 3. Refactored Kernel Functions

All return typed `AnalyticalResult` objects with full provenance:

| Function | Status | Module | Docstring | Type Hints | Tests |
|----------|--------|--------|-----------|-----------|-------|
| `lead_time()` | ✅ | kernels/timing.py | ✅ | ✅ | ✅ |
| `wait_time()` | ✅ | kernels/timing.py | ✅ | ✅ | ✅ |
| `process_cycle_efficiency()` | ✅ | kernels/timing.py | ✅ | ✅ | ✅ |
| `takt_time()` | ✅ | kernels/timing.py | ✅ | ✅ | ✅ |
| `created_to_booked_yield()` | ✅ | kernels/yield_.py | ✅ | ✅ | ✅ |
| `booked_to_completed_yield()` | ✅ | kernels/yield_.py | ✅ | ✅ | ✅ |
| `rolled_yield()` | ✅ | kernels/yield_.py | ✅ | ✅ | ✅ |

### 4. Quality Gates (Tier 1 & 2)

**Tier 1 (Pre-Push — Developer Responsibility):**

| Tool | Config | Status | Current |
|------|--------|--------|---------|
| ruff | E/F/I/UP/B, line-length 100 | ✅ | 0 errors |
| interrogate | 80% docstring coverage | ✅ | 81.9% |
| pydocstyle | Google format (D100/D101/D104 ignored) | ✅ | 0 style issues |
| coverage | 90% minimum | ✅ | 92.71% |
| import-linter | 7 contracts (architecture enforcement) | ✅ | 7/7 contracts passing |
| xenon | B/A/A complexity limits | ✅ | All modules pass |
| vulture | 80% confidence dead code | ✅ | 0 violations |
| ty (Astral) | Type checking (swapped from pyright) | ✅ | All checks passed |
| pytest | Functional tests | ✅ | 34 passed, 7 xfailed |

**Tier 2 (CI — Blocking):**

| Tool | Config | Status | Current |
|------|--------|--------|---------|
| bandit | Security scanning (skip B101 assert_used) | ✅ | 0 issues |
| pip-audit | Dependency vulnerabilities | ✅ | 0 vulnerabilities |

**Hooks:**
- ✅ `.pre-commit-config.yaml` updated with all Tier 1 hooks (pre-push stage)
- ✅ `.github/workflows/ci.yml` includes Tier 1 + Tier 2 checks
- ✅ All dependencies in `pyproject.toml` (dev group)

### 5. Code Cleanup & Refactoring

| Item | Status | Notes |
|------|--------|-------|
| yellow_belt.py re-exports removed | ✅ | Re-creates unnecessary layer; public API now at lss4py/__init__.py |
| kernels/__init__.py as private marker | ✅ | Will rename to `_kernels/` in v0.3 when code-base-wide refactor occurs |
| _event_log.py (private helpers) | ✅ | 280 lines of pandas-based validation (marked for v0.3 Narwhals migration) |
| kernels/_helpers.py (shared utilities) | ✅ | 250+ lines of backend detection, provenance building, column resolution |
| Type hints fixed (ty issues) | ✅ | `TimingResult.unit` now accepts "percentage", "ratio"; narwhals `.sum()` type corrected |
| Line-length violations fixed (E501) | ✅ | 9 violations broken into multi-line strings (timing.py, yield_.py) |

### 6. Test Status

| Suite | Passing | Xfailed | Failed | Coverage |
|-------|---------|---------|--------|----------|
| test_sprint1_results.py | 14 | — | — | 100% result models |
| test_yellow_belt.py | 20 | 7 | — | (v0.3 deferrals) |
| **Total** | **34** | **7** | **0** | **92.71%** |

**Xfailed Tests (Expected, Not Blocking):**
- 6 event-log tests (parallel/critical-path, parallel branch sum, rework, validation)
- 1 process-model cycle/value-add test

---

## Architecture Decisions (Accepted)

All ADRs below are **ACCEPTED** and guide future work:

1. **[ADR-0014: Backend Neutrality](adr/0014-backend-neutrality.md)**
   - All inputs/outputs use Narwhals
   - Supports pandas, Polars, PyArrow
   - Tests run against all backends

2. **[ADR-0015: Belt-Level Governance](adr/0015-belt-level-governance.md)**
   - Analyses tagged by belt level (Yellow, Green, Black)
   - Result models include method signature and assumptions
   - Provenance captures context for auditability

3. **[ADR-0016: Private Kernel Architecture](adr/0016-private-kernel-architecture.md)**
   - Kernels are private implementation details (will be `_kernels/` in v0.3+)
   - Public API exposed at `lss4py/__init__.py` only
   - Safe to refactor internals without breaking downstream

4. **[ADR-0017: Format Adapter Registry](adr/0017-format-adapter-registry.md)**
   - Pluggable adapter pattern for event-log formats
   - pandas v0.2 (done), OCEL 2.0 v0.3, XES v0.4+
   - Auto-detection + explicit format specification

---

## Known Deferrals (v0.3 Work)

These are **expected failures** marked `@pytest.mark.xfail`:

### Event-Log Refactoring (v0.3)

The 6 event-log test failures below are deferred because event-log input handling will be completely refactored in v0.3 to use Narwhals instead of pandas.

- `test_event_log_metrics_use_parallel_critical_path_semantics` — Needs ProcessModelIR.metric_semantics.parallel_timing logic
- `test_event_log_metrics_can_sum_parallel_branch_work` — Needs parallel branch aggregation
- `test_event_log_metrics_allow_rework_when_rework_edge_is_defined` — Needs rework edge detection
- `test_event_log_metrics_reject_unknown_steps_not_in_process_model` — Needs process model validation
- `test_event_log_metrics_reject_overlap_without_parallel_edges` — Needs overlap detection
- `test_event_log_metrics_reject_repeat_without_rework_edge` — Needs repeat validation

**Current behavior:** Event-log helpers in `_event_log.py` use pandas directly.  
**v0.3 plan:** Migrate to Narwhals + ProcessModelIR-aware logic.

### Process-Model Cycle/Value-Add Resolution (v0.3)

- `test_event_log_metrics_extract_values_via_process_model_cycle_time_columns` — Deferred
- Reason: Requires ProcessModelIR.steps[].cycle_time_column integration
- Current: Must pass explicit columns; process model awareness is planned

---

## What's Next (Priority Order)

### Phase 1: Backend & Adapter Infrastructure (v0.2 Core Work)

**Goal:** Implement Narwhals-based adapters so all inputs/outputs are format-agnostic.

#### 1.1 Pandas Adapter Registry (1-2 days)
- [ ] Create `src/lss4py/_adapters/__init__.py` (AdapterRegistry class)
- [ ] Implement `_adapters/_pandas.py` (pandas↔Narwhals bindings)
- [ ] Add `detect_format()` function to auto-detect input format
- [ ] Tests: Verify adapter round-trips (pandas DataFrame → Narwhals → back)
- **Link:** [ADR-0017](adr/0017-format-adapter-registry.md), `docs/ARCHITECTURE.md` Adapter Layer
- **Block:** All downstream adapters

#### 1.2 EventLog & Validation Layer (1-2 days)
- [ ] Migrate `_event_log.py` validation to use adapters
- [ ] Add `EventLogBindingsIR` validation using Narwhals
- [ ] Tests: All event-log helpers work with pandas, Polars, PyArrow backends
- **Note:** This unblocks v0.3 event-log refactoring
- **Block:** Stage yield, timing calculations on event logs

#### 1.3 Backend-Neutral Input Normalization (3-5 days)
- [ ] Create `_kernels/_normalize.py` with composable validators:
  - `normalize_timing_data()` — validates lead_time, cycle_time, timestamps
  - `normalize_stage_data()` — validates created, booked, completed columns
  - `normalize_event_log()` — validates event-log schema against bindings
- [ ] Reuse `domain/validation.py` validators
- [ ] Tests: Verify all normalizers work with multiple backends
- **Block:** All kernel functions must use normalizers

### Phase 2: Analysis Guidance & CTQ Infrastructure (v0.2 Secondary)

**Goal:** Implement CTQ models and analysis-suitability registry so users know which methods apply.

#### 2.1 CTQ & Specification Models (2-3 days)
- [ ] Create `domain/ctq.py`:
  - `CTQDefinition` dataclass (name, lower_spec, target, upper_spec, units, priority)
  - `SpecificationBindings` (map columns to CTQ)
  - Validation rules (lower < target < upper, etc.)
- [ ] Integrate with `ProcessModelIR.ctqs`
- [ ] Tests: Round-trip CTQ via JSON; validate boundaries
- **Reference:** ADR-0015 (Belt-Level Governance)

#### 2.2 Analysis Suitability Registry (2-3 days)
- [ ] Create `domain/guidance.py`:
  - `AnalysisSuitability` (suitable_belt_levels, data_requirements, assumptions, caveats)
  - Registry mapping function name → suitability
  - `validate_suitability()` to check input against method's needs
- [ ] Integrate with all kernel functions
- [ ] Example: `lead_time()` requires lead_time_column, not suitable if timestamps unavailable
- **Block:** Guidance system for v0.3 workflows

#### 2.3 Parity-Fixture Scaffolding (1-2 days)
- [ ] Create `tests/fixtures/parity/` directory structure
- [ ] Add reference cases (NIST, R SixSigma) as JSON
- [ ] Implement `ParityValidator` comparing LSS4PY results to reference
- [ ] Tests: Verify lead_time, yield results match reference implementations
- **Reference:** roadmap.md v0.2 scope: "introduce...parity-fixture scaffolding"

### Phase 3: Extension & Stabilization (v0.2 Polish)

#### 3.1 Kernel Expansion (As time permits)
- [ ] Add `capability.py` kernels (Cp, Cpk, Pp, Ppk, Z-score; v0.2 draft)
- [ ] Add `descriptive.py` kernels (percentiles, mode, skew, kurtosis)
- [ ] All follow same provenance + result model pattern

#### 3.2 Documentation & Examples
- [ ] Create `docs/v02-migration-guide.md` (how to update code from v0.1)
- [ ] Add worked example: "Basic time and yield analysis"
- [ ] Document adapter auto-detection and explicit format specification

#### 3.3 Final v0.2 Acceptance Tests
- [ ] Run full suite: `uv run pre-commit run --all-files --hook-stage pre-push`
- [ ] Confirm CI passes: lint, typecheck, test, smoke
- [ ] Branch protection checks pass
- [ ] No outstanding type errors (ty)
- [ ] 90%+ coverage maintained

---

## Quick Reference: Key Files

### Architecture & Contracts
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — 5-layer stack with import matrix
- [docs/roadmap.md](roadmap.md) — Release strategy and belt-level milestones
- [docs/adr/](adr/) — All Architecture Decision Records

### Implementation
- [src/lss4py/__init__.py](../src/lss4py/__init__.py) — Public API (7 functions)
- [src/lss4py/domain/results.py](../src/lss4py/domain/results.py) — Result models + Provenance
- [src/lss4py/domain/models.py](../src/lss4py/domain/models.py) — Domain data structures (ProcessModelIR, EventLog, etc.)
- [src/lss4py/kernels/timing.py](../src/lss4py/kernels/timing.py) — Timing calculations
- [src/lss4py/kernels/yield_.py](../src/lss4py/kernels/yield_.py) — Yield calculations
- [src/lss4py/_event_log.py](../src/lss4py/_event_log.py) — Event-log helpers (pandas; will migrate to Narwhals in v0.3)

### Quality & Testing
- [.pre-commit-config.yaml](../.pre-commit-config.yaml) — Pre-push hooks
- [.github/workflows/ci.yml](../.github/workflows/ci.yml) — CI jobs
- [pyproject.toml](../pyproject.toml) — Dependencies, tool configs, build system
- [tests/test_sprint1_results.py](../tests/test_sprint1_results.py) — Result model tests (14 passing)
- [tests/test_yellow_belt.py](../tests/test_yellow_belt.py) — Integration tests (20 passing, 7 xfailed)

### Quality Gate Commands
```bash
# Install
uv sync --locked --group dev
uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push

# Local fast stage (pre-commit)
uv run pre-commit run --all-files --hook-stage pre-commit

# Local full stage (pre-push)
uv run pre-commit run --all-files --hook-stage pre-push

# Individual gates
uv run ruff check .
uv run --locked interrogate -vv src/lss4py
uv run --locked pydocstyle src/lss4py
uv run --locked coverage run -m pytest && uv run --locked coverage report --fail-under=90
uv run --locked import-linter lint --config lint_imports_config.ini
uv run --locked ty check
uv run --locked pytest -v
uv run --locked bandit -r src/lss4py
uv run --locked pip-audit
```

---

## Continuation Checklist

When you return, use this checklist:

- [ ] Run `uv sync --locked --group dev` to refresh dependencies
- [ ] Run `uv run pre-commit run --all-files --hook-stage pre-push` to verify gates pass
- [ ] Read the "What's Next" section above for the current priority
- [ ] Open the relevant file(s) from "Quick Reference" section
- [ ] If uncertain, check xfailed tests to see what's deferred vs. broken
- [ ] Refer to ADRs for architectural rationale

---

## Signals That Something Broke

| Signal | Diagnosis | Fix |
|--------|-----------|-----|
| `ty check` fails | Type annotation mismatch | Check type hints in functions; verify Narwhals return types |
| `coverage` < 90% | Missing tests | Add tests for new code; check which lines aren't covered: `coverage report -m` |
| `import-linter` fails | Cross-layer import violation | Check which layer is importing from where; refer to ARCHITECTURE.md import matrix |
| `interrogate` < 80% | Missing docstrings | Add docstrings to public functions; `interrogate -vv src/lss4py` shows missing items |
| `pytest` fails | Logic error | Check xfail markers; run `pytest -v --tb=short` for details |
| `bandit` issues | Security concern | Review the flagged code; add security exception if legitimate |

---

## Context for AI Assistants

If you're asking an AI to continue this work, include:

1. **This file** (V02-PROGRESS.md) — Current status
2. **The relevant ADR** (e.g., ADR-0017 for adapters)
3. **The architecture diagram** from docs/ARCHITECTURE.md
4. **The failing test** (if applicable) — run `pytest -v tests/test_yellow_belt.py::test_name`

Example prompt:
> "I'm working on LSS4PY v0.2. See [docs/V02-PROGRESS.md](V02-PROGRESS.md#phase-1-backend--adapter-infrastructure-v02-core-work). 
> I need to implement Phase 1.1: Pandas Adapter Registry per ADR-0017. 
> The adapter should follow the pattern in `_kernels/_helpers.py::detect_backend()`. 
> Start with the test: `tests/fixtures/test_adapter_registry.py`."

---

## Contact & Questions

- **Roadmap & Belt Levels:** See [docs/roadmap.md](roadmap.md)
- **Architecture & Layers:** See [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- **Current Decisions:** See [docs/adr/](adr/) (especially 0015, 0016, 0017)
- **Run Quality Gates:** `uv run pre-commit run --all-files --hook-stage pre-push`
- **Check Test Status:** `pytest tests/ -v --tb=short`

---

**Happy coding! When you're back, start at Phase 1.1 (Pandas Adapter Registry) and feel free to ask "what's next" anytime.**
