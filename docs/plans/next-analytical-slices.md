# Next analytical slices

- Updated: 2026-10-19
- Status: Z-distance and defect/rework yield slices implemented; study-boundary review is next
- Architecture: [ADR-0020](../adr/0020-delegate-numerical-algorithms-and-own-analytical-contracts.md)
  and [ADR-0021](../adr/0021-reuse-flo-and-established-presentation-libraries.md)
- Release ownership: [roadmap](../roadmap.md); UR-022/UR-023/TR-023 primarily target v0.3

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

## 2. Defect/rework yield contract — implemented

`process_yield` returns an additive versioned `DefectYieldResult`; binary funnel
callers retain their existing APIs. Rows are aligned aggregate buckets with a
shared explicit opportunity population. Defect and rework losses must be disjoint;
combined losses cannot exceed that population. Optional units supplies actual DPU.
See [the contract and example](../defect-yield.md) for formulas and limitations.

Acceptance is covered by genuine R with-rework, zero-defect, single-bucket and
total-loss cases, independent denominator checks, complete neutral backend payloads,
strict JSON, exact integer reductions, input preservation and invalid domains.
Zero-opportunity, recycled-length and excess-loss R behavior is retained as reference
evidence and explicitly differs from Python validation. Python sum/division/product
implement documented small formulas under ADR-0020 without a new dependency.

## 3. Review the next study boundary

After the two slices, reuse the implemented validation reports (UR-016) and audited
bundles (UR-033/TR-033), then review remaining v0.2 acceptance evidence. Select the
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
