# FLO Measurement-Profile Handoff

Date: 2026-09-05
Status: accepted FLO direction; no immediate lss4py implementation requested

## Summary

FLO accepted a future breaking replacement for its current scalar timing metadata.
The replacement will preserve multiple externally calculated statistics, explicit basis, sample context, and evidence references in one producer-neutral measurement profile.

FLO will continue to own process structure, profile validation and preservation, deterministic interchange, explicit projection selection, and rendering.
lss4py and other analytics systems will own event-level evidence, cohort construction, statistical calculation, and method implementation.

The current FLO `{value, unit}` timing syntax remains executable until the profile contract is implemented.
lss4py should not emit the conceptual profile example as FLO source yet.

## Accepted Boundary

A future FLO timing profile will contain:

- required `basis`, including observed, simulated, estimated, planned, or target;
- one or more statistic results containing value, unit, method, and applicable method parameters;
- shared sample context such as count, sample unit, cohort, aggregation level, and observation window;
- an explicit `primary` result for compact rendering;
- an optional explicit `analysis_input` result for modeled FLO static timing; and
- an optional opaque `evidence_ref` identifying evidence held outside FLO.

Core methods will include count, sum, minimum, maximum, mean, median, mode, percentile, and standard deviation.
Percentiles will use a parameterized `percentile` method rather than separate P90 and P99 method identifiers.
Standard deviation will identify its sample or population convention.
Producer-specific extensions will use namespaced identifiers such as `lss4py:trimmed_mean`.

FLO will support non-scalar results where the method requires them, including multimodal mode results.
Consumers that cannot display or analyze a result shape will diagnose the limitation instead of coercing or dropping it silently.

## lss4py Producer Responsibilities

When FLO publishes the implemented schema and public Python types, lss4py should:

1. Map governed lss4py result models into FLO profile types through an explicit adapter.
2. Record the exact statistic method and all interpretation-relevant parameters.
3. Supply `basis: observed` only when the result was calculated from observed evidence.
4. Preserve cohort, sample-unit, observation-window, inclusion, and aggregation semantics.
5. Emit a stable evidence reference without embedding row-level event data in the FLO process model.
6. Select `primary` only from an explicit caller or workflow policy.
7. Select `analysis_input` only when the caller explicitly intends the result to participate in modeled graph timing.
8. Keep FLO integration outside lss4py's numerical core so statistical functions remain dataframe-neutral and independently testable.

lss4py must not assume that `primary` and `analysis_input` are the same selection.
It must not mark a node-level mean as an empirical end-to-end process mean.

## Branch And Rework Frequency

FLO also accepted a structured edge-frequency profile that distinguishes:

- affected work-unit count;
- traversal or correction occurrence count; and
- denominator work-unit count.

lss4py should retain all three values when repeated rework is possible.
It should not reduce `5 affected orders, 8 corrections, 39 eligible orders` to an ambiguous rate or text string.

Edge-frequency evidence and correction-activity timing remain separate outputs even when one report presents them together.

## Delivery Sequence

- FLO 0.4: fix missing, invalid, unavailable, and measured-zero distinctions.
- FLO 0.5: implement profile source, IR, schema, validation, JSON, writer, public API, and compact/machine projections.
- FLO 0.6: support trace- or adapter-produced profiles, structured edge frequencies, and detailed projections.
- FLO 0.7: freeze method, selector, extension, writer, and migration contracts.

## Integration Trigger

No lss4py public API should change solely from this handoff.
Integration work starts when FLO publishes the 0.5 schema and supported public Python profile constructors.

At that point, add a cross-package conformance fixture proving that one lss4py result preserves basis, method parameters, sample context, selectors, units, and evidence identity through FLO canonical JSON.

## FLO Decision Records

- `FLO/docs/design/adr/measurement_profiles_and_evidence.md`
- `FLO/docs/design/adr/measurement_projection_and_analysis.md`
- `FLO/docs/design/adr/observed_branch_and_rework_frequency.md`
- `FLO/docs/requirements/user_requirements.csv`: `UR-079` through `UR-082`
- `FLO/docs/requirements/technical_requirements.csv`: `TR-109` through `TR-112`
