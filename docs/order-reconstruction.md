# Reconstructing the White Belt orders

`reconstruct_orders(log, policy=...)` accepts a validated `NumericEventLog` with
four ordered numeric endpoints and an `OrderReconstructionPolicy`. The runnable
[example](../examples/white_belt/reconstruct.py) supplies the book's declared
policy and pinned, licensed source data. Run it without the sibling book checkout:

```sh
uv run --locked python examples/white_belt/reconstruct.py
uv run --locked python tools/reconstruct_book_simulation.py
```

The second command saves an audited
[reconstruction bundle](../examples/white_belt/reconstruction-bundle.json), linking
the source bytes to reconstruction and the four public analytical readouts. It
reproduces 39 orders, 330 activity records, five correction occurrences affecting
five orders, mean lead 662.6 minutes, eligible nearest-rank P90 676.2 minutes,
six misses among 21 eligible orders, and cohort PCE 13.7%.

## Accounting and completeness

Each source observation retains its case, child load, activity, pass, scope and
zero-based source position. Source processing = work end minus work start;
waiting = setup start minus queue entry; setup = work start minus setup start.
Source timing is calculated from endpoints. Extra supplied duration columns remain
source evidence and do not override those formulas.

Within each scope/case/activity/pass, declared parallel activities use minimum
queue entry, minimum setup start, maximum work start and maximum work end. The
book declares Wash and Dry parallel and binds `Compatible Loads` as their expected
cardinality. Missing child identities or a missing load fail explicitly. When
`parallel_load_count_column` is omitted, completeness of unobserved child loads
cannot be established from the observed group alone. All other activity/pass
groups must be singular; ambiguous multiplicity fails. Repeated passes remain
separate. This envelope convention is specific to the declared serial accounting
path; it does not infer arbitrary branching or sum machine effort as elapsed time.

Arrival is the first declared arrival activity's queue entry. Readiness is the
final declared readiness activity's work end. Required activities must be present.
Activity envelopes must cover that boundary consecutively, within the declared
absolute tolerance, with no gaps, overlaps or extra records beyond readiness.
Invalid endpoints, duplicates, missing activities, unknown rework flags and empty
inputs fail. No records are excluded or zero-filled. Source order is retained as
evidence; chronological envelope checks also work on unsorted records.

The operating clock stays numeric, including observations beyond closing minute
690; closed hours are already omitted. No calendar or overnight conversion occurs.
Scenario/run scope columns participate in grouping, so repeated order IDs across
runs cannot merge. Fixed output field names are reserved for summary measurements;
colliding case/scope bindings fail explicitly. Downstream methods requiring a
single unique case column should consume one explicitly selected scope at a time.

## Classification and inspectable results

The policy declares right-first-time VA activities, RNVA processing activities,
both accepted rework flag values and a singular correction activity. All other
processing is NVA; a rework flag makes that activity/pass's processing NVA.
For the book, right-first-time Wash, Dry, Fold and package, and Send readiness
notification processing are VA. Intake, sort and staging processing are declared
RNVA. Failed packaging attempts and corrections are NVA. Waiting and setup remain
separate components outside VA. Parallel collapse does not erase original load
observations or their own classifications.

`OrderReconstructionResult` is a versioned `AnalyticalResult` with provenance and
four fresh Polars table views:

- `result.to_polars()` returns complete orders with arrival, readiness, lead time,
  processing, waiting, setup, VA, activity-record count and correction count.
- `result.to_polars("activities")` returns collapsed activity/pass envelopes,
  processing classification, right-first-time flag, child IDs and source positions.
- `result.to_polars("activity_records")` returns each source observation's own
  durations and processing classification, before parallel collapse.
- `result.to_polars("source_records")` retains every original observation.

Units, clock, boundary, cohort, policy, input contract and ingestion evidence stay
with the result. Full floating precision is retained until formatting. Correction
occurrences count singular correction activity/pass records; affected orders count
distinct scoped cases with corrections. Trigger and correction flags are never
added together as correction occurrences. Results serialize and restore through
`AnalysisBundle`, retaining source and intermediate evidence.

All 39 orders match the independently pinned prepared summary for every timing
component and correction count. WNF-003 retains two Wash loads, two Dry loads and
one correction: lead 166.3 = processing 111.3 + waiting 50.8 + setup 4.2 minutes,
with 82.7 VA minutes. Missing-load, incomplete-boundary, overlap, scope, repeated
pass, classification and serialization regressions exercise the public route.

Single-time lifecycle inputs are ingestible but require a separate, explicit
pairing policy before this analysis. General branch metrics, OCEL interchange and
publication into the book's officially released dependency remain separate work.

Current 0.2.0 candidate verification passes 1,750 tests with five deferred
branch-metric expected failures and 95.22% coverage. Installed base, pandas,
Arrow/storage and ecosystem workflows pass. See the
[acceptance gate snapshot](assessments/v02-release-gates.json).

## Derive baseline classes from FLO

`lss4py.integration.derive_reconstruction_policy` accepts a validated
`ProcessProjection`, the distinct `observed_activities` vocabulary from the
supplied event log, and a `ReconstructionConventions` declaration. It returns a
`DerivedReconstructionPolicy`:

```python
from lss4py.integration import derive_reconstruction_policy

# projection: public FLO export plus explicit observation-to-step mapping
# conventions: ReconstructionConventions with measurement rules, no class lists
bound = derive_reconstruction_policy(
    projection,
    observed_activities=tuple(log.frame[log.contract.activity_column].unique()),
    conventions=conventions,
)
result = reconstruct_orders(log, policy=bound.policy)
result.metadata["policy_derivation"] = bound.to_dict()
```

`ReconstructionConventions` declares arrival/readiness activities, required and
parallel activities, rework column and accepted flags, correction activity,
cohort, value-add convention, optional parallel-load count column and tolerance.
It reuses the existing policy's validation and accounting semantics. It has no
VA/RNVA lists: those come exclusively from each mapped task's FLO
`value_class` (`VA`, `RNVA`, or `NVA`, case-sensitive) for FLO 0.5.
Saved 0.4.x projections still read `metadata.value_class`; attribution records
the version-appropriate field. Missing or explicit `unknown` classifications
cannot supply a numerical reconstruction policy.

Classification remains optional for general FLO projection. Derivation requires
it for every mapped task, including conditional correction tasks, and rejects
mappings to routing nodes. Unmapped routing nodes need no annotation. Every
observed activity and every activity referenced by the analyst must be mapped.
Supply the vocabulary of the actual log that will be reconstructed; the derived
policy is an ordinary domain policy, not a runtime binding to future datasets.
Mapping is explicit and one-to-one; display names are never used to match data.

The correction activity must be NVA; declaring it VA or RNVA conflicts with this
reconstruction method and fails. Right-first-time rules can make individual
failed attempts NVA even when their baseline class is VA or RNVA. Other valid
model classification changes flow into the derived policy and measured results.
The governed book fixture's acceptance tests pin its original baseline; there is
no separate runtime profile lock or analyst override for model classes.

`bound.to_dict()` and `bound.to_json()` preserve the projection SHA-256, source,
model revision, FLO producer version, observed vocabulary, activity/step/class
attribution, analyst conventions and complete derived policy. The JSON is
preparation evidence suitable for result metadata, not a standalone analytical
result or a new bundle result type. Keep the projection alongside it when the
full source model is needed. Modeled durations and topology do not infer numeric
measurement rules or enter observed arithmetic. The CSV-only API remains usable
without a projection, and derivation itself does not import FLO.
