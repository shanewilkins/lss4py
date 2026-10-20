# 0025: Audited bundles and portable validation

- Status: Accepted
- Date: 2026-10-19
- Deciders: Maintainers
- Related requirements: UR-033, TR-009, TR-020, TR-033
- Clarifies: ADR-0005, ADR-0014, ADR-0022, ADR-0024

## Context

The existing AnalysisBundle serializes results but its reader discards them.
Its v1 format has no required source identity or software context, and its default
package version describes an unreleased milestone. EvidenceManifest already
captures a FLO-specific journey; requiring FLO context for an ordinary statistical
study would violate the general analytics contract. Reviewers also need portable
validation without importing concrete dataframe or numerical dependencies.

## Decision

Keep direct legacy v1 construction readable and implement real restoration for all
five current analytical result families. Add audited v2 capture with named result
ids, explicit result/input relationships, selected and fingerprinted source
references, software versions, typed specifications, cohort and finite JSON context.
Each result entry records a result-schema version independently of bundle version.
Source references never cause implicit I/O. Loading never imports or invokes a
method described by saved metadata.

A standard-library-only module validates both wire formats. The package API wraps
its errors in ValidationError, while the same module runs as an independent script
with no package imports. Validate finite JSON, exact supported field sets and
versions, result types, provenance, relationships, software context and relevant
internal count/key/specification invariants. A canonical JSON fingerprint detects
accidental edits; separate input-byte verification checks referenced artifacts.
Neither substitutes for source review or numerical verification.

Capture detaches caller-owned results and context. Objects remain editable; each
export is revalidated and fingerprinted as a new snapshot. Existing standalone
result serializers retain their payload shapes and now reject nonfinite JSON.
Shared reconstruction restores NumPy arrays and scalar key identity, interval and
bucket tuples, provenance timestamps and structured warnings. EvidenceManifest
uses that same restoration for timing data without changing its envelope.

Legacy v1 cannot become auditable without new evidence. Preserve its schema and
original metadata on load; require explicit missing context to upgrade it to v2.
Keep original bundle context in the migrated record. ADR-0014's proposed automatic
migration must not manufacture missing sources or software versions. Reject unknown
future schema versions until a migration is explicitly implemented.

## Alternatives considered

- Make a v1 bundle appear audited after adding empty defaults: rejected because
  no source identities or rerun context would have been recovered.
- Require the FLO evidence envelope for every study: rejected because ordinary
  statistical analyses do not require process-rendering semantics.
- Dynamically import a recorded method on load: rejected because restoring saved
  data must be independent of executing a new analysis.
- Depend on dataframe libraries to validate JSON: rejected because reviewers need
  a small portable artifact; typed runtime reconstruction remains optional.

## Consequences

Audited v2 is the supported general study exchange contract for current results.
Legacy readers no longer drop results. Migration and installed-wheel rerun tests
protect the new format; a fixed v1 fixture protects compatibility. The broader
bundle work does not declare v0.2 release readiness or make placeholder analyses
supported. Application-specific context, process models and source selection
remain explicit caller responsibilities.
