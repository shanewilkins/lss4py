# White Belt book fixture and public API assessment

- Assessed: 2026-10-23
- Scope: Current-sprint assessment in the [book plan](../plans/white-belt-book-preview.md)
- Evidence: [machine-readable snapshot](book-preview-assessment.json)
- Reproducer: [assessment script](../../tools/assess_book_preview.py)
- Boundary: [ADR-0026](../adr/0026-method-specific-input-contracts-and-ocel-interchange.md)
- Outcome: Assessment complete; revised fixture adopted 2026-10-23; prepared-data slice implemented

The prepared-summary preview is feasible with existing loading, validation,
descriptive statistics, and PCE calculations plus small public-contract extensions.
The current sibling book differs from the accepted requirement fixture. Its VA
classification and final activity changed on October 22. That version was adopted
on October 23 and pinned as `washnfold-friday91` version 1.0.0 in the reference
catalog. The [prepared-data preview](../book-preview.md) now implements the scoped
public contracts and rendered cell. The findings below describe the pre-implementation
snapshot; they remain as assessment history. Full reconstruction remains v0.3 work.
This assessment does not declare any preview requirement satisfied.

## Source and fixture inventory

All required files are available in the sibling `modern-process-improvement`
checkout. The evidence JSON records SHA-256 hashes for their exact bytes, including
the chapter and license, plus the relevant lss4py implementations. The book HEAD
at assessment was `a10b7ecbc33908cffcafd4bbc3783b3447163406`; the chapter had
uncommitted changes. Therefore HEAD alone does not identify this assessment's
source version; the byte hashes are authoritative for the observed snapshot.

| Source under the book checkout | Role and observed shape |
| --- | --- |
| `data/washnfold/washnfold_learner_order_summary.csv` | 39 unique order rows; numeric operating-minute boundaries, timing components, VA, correction counts, and promise flags |
| `data/washnfold/washnfold_event_log.csv` | 330 activity rows: 39 each for intake, sorting, folding, staging, and notification; 65 Wash loads, 65 Dry loads, and 5 correction occurrences |
| `data/washnfold/washnfold_baseline_readout.csv` | Renderable baseline with metric, aggregation, observation/physical units, boundary, cohort, clock, and interpretation |
| `data/washnfold/washnfold_simulation.py` | `learner_order_summary` documents current order aggregation; inspection only, no simulation run |
| `data/washnfold/washnfold_representative_run.csv` | Friday 91, selected by current-state multivariate medoid |
| `book/content/white_belt/measuring_process.qmd` | Chapter definitions, worked arithmetic, and current VA classification |
| `data/washnfold/README.md` and `LICENSE.md` | Source history, synthetic provenance, measurement boundary, and mixed-license notice |

The data README explicitly separates current exports from historical batch/pull
outputs. Do not combine them to recover an earlier answer. These are simulated
teaching observations, not observed customer-business evidence. The simulation
need not become a runtime dependency of the preview.

The local license assigns original instructional non-code material CC BY 4.0
and original source code MIT, subject to local third-party notices. No CSV-specific
notice was found in the inspected fixture sources. The adopted strategy is a
small immutable test snapshot of the
prepared summary and event log, with source hashes, schema, expected values,
synthetic provenance, source URL, version, and attribution to Shane M. Wilkins,
*Modern Process Improvement with Python*. Retain the source license notice/link
and identify any changes under TR-037. Avoid copying the simulator. The assessment
JSON remains diagnostic evidence, separate from the new governed test fixture.
The [pinned fixture](../../tests/fixtures/reference/washnfold-friday91/conventions.json)
copies source CSVs and the source README/license with checksums and attribution;
it does not copy the simulator or chapter prose.

## Independent numerical verification

The assessment uses Decimal arithmetic on displayed one-decimal observations.
All 39 prepared rows match an independent audit of the inspected generator's
current convention. All 330 activity rows satisfy endpoint ordering and their
P/T, W/T, S/T formulas; all order partitions and correction counts reconcile.
There are no duplicate order IDs, promise-flag mismatches, or event orders lacking
a prepared summary in this snapshot. These findings establish fixture consistency,
not general invalid-input handling in the product.

| Measure | Original registered expectation | Current book snapshot |
| --- | --- | --- |
| All / eligible / ineligible orders | 39 / 21 / 18 | Same |
| All-order mean operating lead time | 662.6 min | Same |
| Eligible sum / mean / median lead time | 8899.2 / 423.8 / 424.5 min | Same |
| Eligible nearest-rank P90 | Position 19, 676.2 min | Same |
| Promise misses / eligible count | 6 / 21 = 28.6% | Same |
| All-order lead-time sum | 25840.5 min | Same |
| All-order VA sum | 3582.3 min | **3535.3 min** |
| Cohort PCE | 13.9% | **13.6812368…%, displayed 13.7%** |
| Mean order P/T / W/T / S/T | 104.5 / 554.0 / 4.1 min | Same |
| Correction occurrences / affected orders | 5 / 5 | Same; 10 rework-flagged rows must not be counted as 10 corrections |
| WNF-003 arrival / readiness / lead time | 12.1 / 178.4 / 166.3 min | Same |
| WNF-003 P/T / W/T / S/T | 111.3 / 50.8 / 4.2 min | Same |
| WNF-003 VA | 94.4 min | **82.7 min** |
| Final activity | Stage and notify | **Send readiness notification**, following separate Stage for collection |

Current VA includes right-first-time Wash, Dry, Fold and package, and readiness
notification. Failed packaging attempts and corrections are excluded; staging is
RNVA. WNF-003 VA is 30.0 Wash + 51.5 Dry + 1.2 notification = 82.7 min. Its flagged
12.9-minute failed packaging attempt and 4.1-minute correction are outside VA.
The all-order VA difference is -47.0 min. This is a semantic change, not a rounding
or percentile-method difference.

Decision adopted 2026-10-23: use the current split-activity book fixture and its
explicit right-first-time VA policy. UR-047/UR-049, TR-040/TR-042/TR-044, associated
preview expectations, and the sprint's PCE gate now use the revised values. The
table above and the fixture conventions retain the superseded values as history;
they are not current acceptance targets.

## Existing public APIs and precise gaps

Probes executed against package version 0.1.0 using Polars inputs. They are an
assessment of this backend and snapshot, not a new cross-backend support claim.

| Capability | Reusable public surface | Gap / implementation action |
| --- | --- | --- |
| Load prepared CSV | Polars CSV loading outside lss4py, allowed by the demo boundary | No new general-purpose CSV adapter is needed to start the preview. Bind the original column names explicitly. |
| Validate prepared data | `DataContract`, `ColumnRule`, `validate_data` | Existing numeric/domain/unit/key checks pass; duplicate order IDs are rejected with `duplicates="error"`. Add numeric endpoint ordering and cross-column invariants; `timestamp_order` currently permits timestamp rules only. |
| All-order mean, median, count, extrema, range | `describe(..., missing="raise", unit="minutes")` | Mean 662.576923… and count 39 already work. Add a numeric sum field: `DescriptiveResult.total` is observation count, not measurement sum. Preserve its meaning. |
| Eligible P90 | `describe` selection and result framework | Add an explicit nearest-rank option and method metadata, preserving the current linear default. The current eligible fixture returns 676.2 for both methods because `(21-1)*0.9` is exactly 18; matching this value alone cannot verify nearest rank. `[1,2,3,4]` gives linear P90 3.7 versus nearest-rank 4. |
| Promise evaluation | Explicit numeric cohort filtering outside lss4py is available | No public promise evaluator exists. Add a reusable fixed-deadline conformance calculation accepting declared eligibility/deadline bindings and policies, with typed counts, rate, ineligible identities, and exclusions. Do not hardcode book cutoffs in the kernel or treat `process_yield` as a substitute. |
| Cohort PCE | `process_cycle_efficiency` on a transparent one-row table of VA and lead-time sums | Existing public arithmetic returns 13.6812368…%. Averaging row PCE gives **18.9635933…%**, which is wrong for this cohort measure. Retain the 39 source orders, sum derivation, unit, classification, cohort/count, and boundary in the result/evidence; the current totals result alone has no cohort definition. A governed cohort aggregation option can encapsulate this; a second ratio formula is unnecessary. |
| Numeric operating lead time | Use the already prepared numeric lead-time column with `describe` | **Do not call current `lead_time` on numeric boundaries.** For WNF-001 it returns 0.00000275 minutes instead of 165.2, due to numeric-to-datetime coercion. Add an explicit numeric clock mode/contract and reject ambiguous numeric inputs in the calendar path. |
| Numeric event-log ingestion | None in current calendar interval adapter | `load_event_log` on bound numeric endpoints raises `AdapterError` while attempting date parsing. Preserve the existing calendar API; define a numeric activity-time route in the reconstruction sprint. |
| Activity waits and setup | Existing result/provenance structures | `wait_time(lead, processing)` includes setup and is not the book's W/T formula. On minute inputs it also returns a hardcoded `hours` label (55.4 for WNF-001, while actual W/T is 51.2 and S/T 4.2). Do not use it for book activity waiting; address units without broadening the preview into general branch timing. |
| Renderable metadata and evidence | Typed results, provenance, `AnalysisBundle`, validation reports | Bind clock, units, order selection/count, boundary, aggregation, quantile and VA policy explicitly. Review bundle restoration if result schemas change. Formatting may remain in the book. |

For the minimum prepared preview, no timestamp parsing or endpoint subtraction is
needed: the supplied lead-time column is honest prepared input. Numeric endpoint
validation is still necessary before trusting the supplied measurements. Existing
numeric field validation cannot by itself assert readiness minus arrival equals
lead time, VA <= lead time, or the component partition.

## Implementation checklist for the dedicated v0.2 sprint

1. **Fixture version — adopted and pinned.** Use `washnfold-friday91` version
   1.0.0, with immutable attributed CSVs, conventions, checksums, and independent
   expectations in the reference catalog. The book build still needs an explicit
   prepared-input artifact pin so learners have no sibling-checkout setup requirement.
2. **Validate the prepared contract.** Declare Order ID, numeric operating-minute
   fields, nonmissing/nonnegative domains, unique summaries, aligned cohort, VA
   bounds, endpoint ordering, and component/lead consistency. Record clock identity
   and exclusions. Do not route numeric minutes through calendar conversion.
3. **Extend `describe` conservatively.** Add an explicit nearest-rank convention
   and measurement sum. Preserve ordinary even-sample median, the linear default,
   and existing observation-count fields; update serialization and bundle contracts
   if needed. Exercise small-sample indexing where linear and nearest-rank differ.
4. **Add fixed-deadline evaluation.** Return eligible count, miss count/rate,
   ineligible cases, invalid/incomplete findings, and policy metadata. Test arrival
   120 versus above, readiness 600 versus above, no eligible orders, missing
   readiness, and a case where lead-time allowance gives the wrong classification.
5. **Reuse PCE arithmetic with governed aggregation evidence.** Sum VA and lead
   time over identical validated orders, then use the existing ratio calculation.
   Preserve source count and sum derivation rather than reporting one aggregate row
   as one observed order. Test unequal lead times, zero/invalid denominators,
   missingness, and mismatched selections.
6. **Build and render the short cell.** It should load identified prepared inputs,
   call actual public calculations, and display the four measures with units and
   cohorts. Use the adopted 13.7% PCE expectation. Include a clean book
   build and installed-package execution; no assessment script or unreleased helper
   should substitute for the public methods.
7. **Close relevant checks and evidence.** Run the supported backend contracts,
   numerical and invalid-input regressions, result/bundle compatibility tests, and
   required release gates. Promote only the covered requirement slices.

The numeric datetime-coercion issue should be guarded before advertising numeric
endpoint support. Its correction can be small and separate; full general-purpose
numeric interval reconstruction is not necessary for the prepared-summary cell.

## v0.3 reconstruction handoff

Preserve the order/load/activity/pass keys and original observations. Apply the
declared min-queue/min-setup/max-start/max-end collapse only to Wash/Dry within an
order/activity/pass. For the current source, intake queue entry and final readiness
notification work end define the boundary. Keep staging, notification, failed
packaging, and corrections separately classified. The WNF-003 activity spans are
retained in the evidence JSON for a hand check.

The diagnostic script independently audits this fixed, complete fixture to scope
the implementation. It is not a released reconstruction function: it deliberately
does not establish missing-boundary policy, arbitrary topology support, lifecycle
pairing, or a reusable result contract. Those remain implementation work under
TR-040/TR-043/TR-046. OCEL support is not required for either book sprint.

## Reproduce this assessment

From the lss4py checkout with the locked environment and sibling book available:

```bash
uv run --locked python tools/assess_book_preview.py \
  --book-root ../modern-process-improvement \
  --output /tmp/book-preview-assessment.json
```

The output captures independently calculated measurements, actual public API
behavior (including errors), reference-audit mismatches, and source fingerprints.
Decimal reference values serialize as strings to retain their decimal precision.
API errors and fixture drift are findings rather than successful acceptance
checks. Compare source hashes before comparing regenerated evidence with this
snapshot; changes require review, not automatic replacement of expected answers.
The executed locked `--no-sync` rerun reproduced the hashes, metrics, audit, and
API findings. Polars can report either `started_at` or `completed_at` first when
both fail date parsing; that backend diagnostic expression is not stable between
runs. Compare its error type and root cause rather than requiring identical text.
