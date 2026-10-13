# Next analytical slices

- Updated: 2026-10-13
- Status: Z-distance slice implemented and tested; yield/study work remains planned
- Architecture: [ADR-0020](../adr/0020-delegate-numerical-algorithms-and-own-analytical-contracts.md)
  and [ADR-0021](../adr/0021-reuse-flo-and-established-presentation-libraries.md)
- Release ownership: [roadmap](../roadmap.md); UR-023/TR-023 primarily target v0.3

Cp/Cpk, components, and confidence intervals already have typed results and
passing genuine R references across pandas, duplicate-index pandas, Polars, and
provisional Arrow. The next analytical slices consume the retained Z/yield
baselines. v0.2 validation, bundle, and acceptance gaps remain tracked separately
in the [continuation guide](../V02-PROGRESS.md); these slices do not complete them
or move release ownership.

## 1. Capability Z distance — implemented

Extend `capability_indices` using its existing mean, variation estimate, and
components. Populate the existing `CapabilityResult.z_score` as distance to the
governing specification limit: `3*Cpk`, using whichever limit is available.
Do not introduce a generic observation-standardization API or refit/re-extract
the measurements to obtain the same estimate.

Implemented policy: an explicit `sigma_shift=0.0` parameter. Subtract an explicitly
requested shift; `1.5` corresponds to the R `LT=True` convention. Require a finite,
nonnegative shift and record it, the unshifted distance, and the estimator in
provenance/result metadata. The shift is an assumption, not evidence of observed
short-/long-term performance. The unshifted distance is stored as metadata["z_to_spec"], and provenance
records sigma_shift and the governing-specification-distance method. The existing
sample-variation interpretation is preserved.

Acceptance covered by tests:

- Pass the retained two-sided and shifted R Z cases at declared tolerances.
- Extend genuine R fixtures for lower-only, upper-only, and negative distances,
  with version/provenance/hash review rather than Python-derived expectations.
- Test null policies, invalid shifts, constant/insufficient data, overflow,
  strict serialization, input preservation, and all four backend variants.
- Keep Z unavailable when Cpk is unavailable; retain signed distance values.
- Update suitability, docs, requirements evidence, and the compatibility matrix
  only for passing behavior. Existing Cp/Cpk estimates and intervals remain stable.

## 2. Defect/rework yield contract, then implementation

Define a result capable of carrying Yield, FTY, RTY, DPMO, and the underlying counts
and denominators. The existing scalar `YieldResult` is not a complete study result
for all of those quantities. Choose an additive typed contract after reviewing
serialization and existing funnel callers; preserve the binary funnel APIs.

Resolve these input/result meanings before implementing formulas:

- Are rows units, stages, or aggregate counting records? What population does each
  denominator describe, and what does the R `opportunities` parameter mean?
- How are defects and rework counted, aligned, and combined? How are multiple
  defects on one unit distinguished from defective units?
- R's returned `DPU` field is the sum of defects in the retained fixture. Document
  that legacy meaning explicitly; a canonical defects-per-unit result needs an
  explicit unit denominator. Do not silently relabel the count as a rate.
- What constraints apply to counts, missingness, zero denominators, and impossible
  combinations? Prefer typed validation over R vector recycling or infinities,
  and register each intentional difference.

Acceptance:

- Execute the genuine defect/rework and zero-defect R cases with an explicit
  field/semantics mapping. Extend reference evidence for the selected contract.
- Record zero-opportunity and length-mismatch differences already observed in R;
  add negative/fractional counts, nulls, alignment, and denominator-domain tests.
- Verify independent denominator calculations and backend-equivalent complete
  results, provenance, strict JSON, and unchanged funnel behavior.
- Record the reused primitives and source formulas under ADR-0020; do not add
  a numerical dependency merely to implement reductions or ratios.

## 3. Review the next study boundary

After the two slices, review reusable validation reporting (UR-016), auditable
bundles (UR-033/TR-033), and the remaining v0.2 acceptance evidence. Select the
next Yellow Belt stability/control-chart slice against the roadmap and reference
coverage. Defer full capability-study orchestration until its distribution and
stability inputs have governed contracts; calculating indices alone is not a
complete study. No automatic method selection or plotting layer is needed for
these next two calculations.

## Completion gate for each slice

Before implementation, identify the upstream algorithm or documented small domain
formula and verify its estimator/policy against the intended contract. Reuse FLO
for process/value-stream rendering through an explicit supported mapping;
statistical plotting consumes results without recalculation. Review existing
diagram capabilities before selecting a fishbone renderer. Numerical parity and
rendering/export acceptance remain separate checks joined by an installed-package
end-to-end workflow where presentation is part of the feature.

Run the locked quality gates, the required Arrow matrix, targeted R verification
when reference artifacts change, and built-wheel smoke checks. Review documentation
and requirement traceability alongside code. Promote only the covered compatibility
claims; passing tests do not by themselves declare a release ready.
