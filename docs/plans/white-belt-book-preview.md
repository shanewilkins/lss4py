# White Belt book preview sprint plan

- Updated: 2026-10-23
- Status: Prepared preview, numeric ingestion and activity-to-order reconstruction implemented; official release/book integration remains
- Source: `fromTheBook.md`, supplied and read in this chat; the source file is
  currently absent from the checkout. The requirement registers retain its
  accepted criteria and sibling-book fixture paths.
- Release ownership: [roadmap](../roadmap.md)
- Acceptance criteria and status: [user requirements](../requirements/user-requirements.csv)
  and [technical requirements](../requirements/technical-requirements.csv)

Deliver the familiar Wash n' Fold Chapter 9 baseline in two implementation
sprints after a bounded assessment in the current v0.2 sprint. Reuse existing
public calculations and retain the book's explicit cohorts, clock, and aggregation
conventions. Dates and effort estimates remain unset until assessment is complete.

## Current v0.2 sprint: assess the fixture and existing APIs

Completed 2026-10-23: see the [assessment and implementation checklist](../assessments/book-preview.md)
and [captured evidence](../assessments/book-preview-assessment.json). The current
October 22 book snapshot changes the final activity and VA policy: PCE is 13.7%,
total VA 3535.3 min, and WNF-003 VA 82.7 min. Adopted 2026-10-23 as
[`washnfold-friday91` version 1.0.0](../../tests/fixtures/reference/washnfold-friday91/conventions.json),
with immutable source CSVs, checksums, attribution, and independent expectations.
The requirement registers and gates below use this version. Mean lead time,
eligible P90, and promise misses remain unchanged. The assessment preserves
superseded values as history; do not mix fixture versions.

Read the Friday 91 prepared summary, event log, completed baseline readout,
`learner_order_summary` reconstruction reference, and Chapter 9 worked examples
listed in the source. Check availability, provenance, and redistribution conditions
before choosing a checked-in fixture strategy under TR-037.

Map the four preview calculations and input/result contracts to current public
APIs. Record what can be reused, the smallest extensions needed, and any mismatch
between the prepared observations and declared expected results. Inspect the
event-log convention sufficiently to scope reconstruction without implementing it.

Exit evidence: a concrete API/fixture gap assessment and reproducible baseline
expectations sufficient to implement the next sprint. Keep existing v0.2 contract
and release work in scope; full reconstruction belongs to the v0.3 sprint below.

Apply [ADR-0026](../adr/0026-method-specific-input-contracts-and-ocel-interchange.md)
in the assessment: distinguish prepared measurements, numeric operating-time
observations, and calendar intervals. Identify method preconditions and the user
declarations versus adapter transformations needed for each route (TR-046).
Do not make OCEL conversion or fabricated datetimes prerequisites. OCEL ingestion
and object-preserving projection contracts (TR-047) belong to later infrastructure.

## Dedicated v0.2 sprint: preview from prepared summaries

Implemented: see the [public contract guide and runnable artifacts](../book-preview.md).
The supplied CSV, notebook, rendered cell and Quarto excerpt use the pinned
version with no sibling-checkout dependency. Publication into the sibling book
waits for an official package release and lockfile update; its existing chapter
is not switched to unreleased APIs. The v0.3-owned activity-to-order route is now implemented; see the reconstruction delivery below.

Deliver these dependent slices in order:

1. Bind prepared summary columns, case identity, units, and numeric cumulative
   operating minutes explicitly (TR-039). Record cohort selections and preserve
   source evidence using the existing validation and provenance contracts.
2. Reuse or extend descriptive calculations for count, sum, mean, median,
   minimum, maximum, range, and explicitly labeled nearest-rank P90
   (UR-004/TR-006). Keep even-sample median and percentile conventions distinct.
3. Implement fixed-deadline promise evaluation (UR-048/TR-041) and same-cohort
   ratio-of-sums PCE (UR-049/TR-042). Preserve ineligible orders and the declared
   book VA classification; include cutoff/deadline equality and undefined-denominator
   cases, plus a fixture distinguishing ratio-of-sums from mean-of-ratios.
4. Return inspectable values, units, cohort/count, boundary, clock, aggregation,
   calculation convention, exclusions, and validation evidence for prepared inputs
   (the prepared-input portion of TR-043). Keep full precision until rendering.
5. Deliver one short Chapter 9 cell using real public lss4py calculations with
   honestly labeled prepared inputs, rendered output, and no learner setup
   requirement (the preview portions of UR-046/TR-044/TR-045).

The rendered cell must show all-order mean lead time **662.6 min**, eligible-order
nearest-rank P90 **676.2 min**, eligible misses/count **6/21** (28.6% if displayed),
and all-order PCE **13.7%**. Validate explicit populations of 39 all orders and 21
eligible orders, eligible mean/median 423.8/424.5 min, and all-order VA/lead-time
totals 3535.3/25840.5 min against the pinned one-decimal source observations.

Exit evidence: the executed cell and prepared-input numerical, invalid-input,
metadata, and supported-backend checks. Complete the relevant repository quality
and packaging gates before the v0.2 release. Record only demonstrated requirement
progress; the complete book contract still awaits event-log reconstruction.

## First v0.3 timing sprint: reconstruct complete orders

The [numeric activity/lifecycle ingestion slice](../simulation-ingestion.md) is
already implemented and exercised on the live simulation exports. Begin the
remaining work from its explicit contracts and preserved evidence; loading is
not a substitute for lifecycle pairing, activity aggregation or order reconstruction.

Implement the separately reproducible event-log route (UR-047/TR-040), retaining
Order ID, child Load ID, activity, pass, and intermediate P/T, W/T, and S/T records.
Use the declared Drop-off queue-entry to final Send readiness notification work-end boundary.
Keep Stage for collection separate as RNVA; VA includes right-first-time Wash,
Dry, Fold and package, and Send readiness notification processing. Failed
packaging attempts and corrections remain NVA and outside the numerator.
Collapse Wash/Dry within each order/activity/pass using earliest Queue Entry and
Setup Start and latest Work Start and Work End, explicitly labeled as this
fixture's convention. Preserve parallel-load and correction evidence and the
book's order-level VA convention.

Complete missing-endpoint, invalid-ordering, duplicate-summary, incomplete-case,
exclusion, and correction-count behavior (TR-043). Distinguish occurrences from
affected orders and avoid counting a trigger flag and its correction twice.

Verify every TR-044 expectation against the prepared summaries and reconstructed
records, including mean order P/T/W/T/S/T **104.5/554.0/4.1 min** and **5 correction
occurrences**. Retain the WNF-003 hand check: two Wash loads, two Dry loads, one
correction; arrival 12.1, readiness 178.4, lead time 166.3, VA 82.7, and
111.3 + 50.8 + 4.2 = 166.3 min.

Exit evidence: the executable separate reconstruction example, full fixture and
error regressions, inspectable intermediate records, and supported-backend
validation. Complete UR-046/UR-047 and TR-040/TR-043/TR-044/TR-045 only when their
full acceptance criteria pass. Advance shared requirements from Planned to
Partial only when implementation and relevant validation exist; planning alone
does not change status.

Takt, time-weighted WIP, throughput, Little's Law, capacity estimates, before/after
comparisons, plots, simulation, inference, automatic waste diagnosis, and causal
judgment remain outside these preview sprints.

## Reconstruction implementation — 2026-10-24

The four-endpoint activity route is implemented through public `reconstruct_orders`
and `OrderReconstructionPolicy`. It reproduces all 39 pinned summaries, preserves
raw and collapsed activity/load/pass evidence and classifications, checks complete
serial envelope coverage and declared parallel load counts, and counts five
corrections across five orders. A separately runnable example and audited bundle
are supplied; see [order reconstruction](../order-reconstruction.md). TR-040,
TR-043, TR-044, TR-046 and UR-047 are satisfied for this declared slice. UR-046 and
TR-045 retain the official release/book publication gap. Lifecycle pairing, OCEL
and general branch algorithms remain outside this implementation.
