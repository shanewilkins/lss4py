# 0007: Analysis suitability registry

- Status: Proposed
- Date: 2026-09-02
- Deciders: Maintainers
- Related requirements: UR-017, TR-019

## Context

LSS4PY analyses should not silently select a statistical test or method based on
observed data alone (see ADR-0003). Users need to see candidate analyses, understand
when each is appropriate, and explicitly choose one.

Currently, there is no registry of available analyses or their suitability criteria.
Guidance functions (TR-019) need metadata about each analysis to recommend candidates
for a given question and dataset.

## Decision

Create a decorator-based analysis suitability registry in `src/lss4py/guidance/`.

Each analysis function registers a `AnalysisSuitability` that documents:

- **Family** (capability, inference, SPC, MSA, quality loss, etc.)
- **Name and question tag** (e.g., "can_process_meet_specs")
- **Applicability:** required sample size, supported data types, design types
- **Assumptions** (e.g., normality, independence) and checks available
- **Alternatives** (similar analyses for comparison)
- **Interpretation limits** (e.g., "requires stable process")

Example:

```python
@register_analysis(
    AnalysisSuitability(
        family=AnalysisFamily.CAPABILITY,
        name="normal_capability_study",
        question_tag="can_process_meet_specs",
        required_scale=30,
        data_types=frozenset(["numeric_continuous"]),
        design_types=frozenset(["observational", "random_sample"]),
        assumptions=["normality", "independence"],
        alternatives=["non_normal_capability", "empirical_capability"],
        limits=["requires stable process"],
    )
)
def capability_study(data, **kwargs) -> CapabilityResult:
    ...
```

The `get_candidates()` function discovers analyses matching a question, data type,
and study design. Users explicitly select from candidates and call the analysis
function with `method=` parameter.

**No auto-selection.** Guidance recommends; users decide.

## Alternatives considered

- **Central config (YAML/JSON).** Single source of truth. Rejected: couples
  governance to data files; synchronization burden; hard to evolve with code.
- **Guidance API (separate module).** Decouples from implementation. Rejected: hard
  to keep in sync; guidance stales; discovery is difficult.

## Consequences

- Every new analysis must register via decorator with suitability metadata.
- Registry is discoverable via inspection; supporting tools can enumerate candidates.
- Analysis functions optionally accept `method=` parameter for explicit selection
  (useful for reproducibility and avoiding auto-selection).
- Pre-1.0, suitability criteria are not stable; categories and question tags may
  evolve (documented in deprecation policy, ADR-0014).
