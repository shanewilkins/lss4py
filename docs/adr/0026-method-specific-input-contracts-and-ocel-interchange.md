# 0026: Method-specific input contracts and OCEL interchange

- Status: Accepted
- Date: 2026-10-23
- Deciders: Maintainers
- Related requirements: UR-014, UR-015, UR-016, UR-047, TR-013, TR-039,
  TR-040, TR-046, TR-047
- Supersedes: ADR-0017's universal flattened event representation, kernel-driven
  format adaptation, and format rollout promises; ADR-0019's requirement that
  every event-log adapter return IntervalEventLog
- Preserves: ADR-0019's current public interval contract and layer boundaries;
  ADR-0018's canonical Polars ingestion engine; ADR-0024's explicit normalization

## Context

Different analyses need different observations: prepared order summaries,
activity intervals, counts, or events associated with multiple objects. Forcing
every observation through an event-log interchange format adds preparation work
without supplying the business meaning required to calculate a metric.

The book fixture also uses cumulative operating minutes, whereas the implemented
IntervalEventLog requires calendar datetimes. Encoding operating minutes as
fabricated dates would change the clock semantics. Future OCEL ingestion must
preserve object relationships rather than silently reduce every event to one case.

## Decision

1. **Validated, method-specific analytical inputs are the firm boundary.** Each
   public analysis documents its accepted observation shape, bindings, identities,
   units, clock, missing-data rules, and applicable analytical policies. Supported
   eager frames with explicit bindings remain valid inputs; users need not create
   an adapter result object or OCEL file to call a calculation. Methods enforce
   their preconditions even when a caller bypasses file adapters.
2. **The user supplies structured observations and declares business meaning.**
   Users or their pipelines extract source data and resolve business-specific
   cleaning and reconciliation. The user declares the case/object of interest,
   cohort, process boundary, operating clock, VA classifications, and parallel or
   correction aggregation policies where needed. These declarations may be reused
   from explicit models or specifications; lss4py validates and applies them.
3. **Adapters handle documented mechanical transformations.** Source-specific
   loading, column mapping, explicit parsing/unit conversion, and validation belong
   outside kernels. Transformations and exclusions must be inspectable. Ambiguous
   identities or semantics produce actionable findings, not inferred business
   rules, silent row loss, deduplication, or imputation. Kernels and workflows do
   not import adapters or detect file formats; an optional future registry belongs
   at the ingestion boundary.
4. **Support distinct observation families.** Prepared measurements can enter
   their analyses directly. Calendar activity intervals retain the implemented
   IntervalEventLog contract. Numeric cumulative operating times require an
   explicitly documented numeric-time input contract with units and clock identity;
   they must not be routed through datetime parsing or fabricated calendar values.
   The book preview implements the numeric prepared-input slice first. The exact
   generalized numeric interval type remains an implementation design task.
5. **OCEL is a future interchange contract, not a prerequisite for all analysis.**
   Future OCEL ingestion must preserve event/object identities, types, attributes,
   and event-to-object and object-to-object relationships within its declared
   supported version/profile. It must report unsupported content and conversion
   limitations. A projection into order/case/activity inputs requires explicit
   object selection, lifecycle/interval pairing where needed, boundary, shared-event
   attribution, and aggregation policies. Preserve source links and report
   exclusions or information loss so shared events are not silently duplicated
   across a metric denominator. OCEL structure does not supply these policies.
6. **Release claims follow executable contracts.** This decision changes planned
   architecture, not the current runtime. Existing CSV/calendar interval APIs
   remain unchanged. The v0.2 prepared-summary and v0.3 reconstruction sprints
   establish their relevant method contracts. Future OCEL support is assigned to
   v0.4 infrastructure, with practitioner workflow completion in v0.5; it does not
   block the book preview. Its exact supported version and serializations must be
   selected and tested before implementation claims are made.

## Alternatives considered

- **Require OCEL for all inputs.** This burdens prepared summaries and ordinary
  statistical measurements with an event representation and still leaves clocks,
  metric boundaries, and aggregation policies unresolved.
- **Require users to implement all formatting.** Explicit inputs are necessary,
  but repeated source parsing and column renaming are reasonable adapter duties
  already covered by UR-014. Keep direct prepared-input use and governed loaders.
- **Flatten every source into IntervalEventLog.** The current calendar interval
  shape cannot preserve arbitrary object relationships or numeric operating-clock
  semantics. Any analytical projection must be explicit and auditable.
- **Infer case selection and aggregation from source structure.** File validity
  cannot establish the intended customer boundary, denominator, or value judgment.

## Consequences

The firm contract is semantic and method-specific, independent of serialization
or caller dataframe choice. Supporting a new file format should not change metric
formulas. More than one observation model is necessary, with contract tests for
equivalent supported inputs and explicit rejection of incompatible clocks and
ambiguous projections. This is not a commitment to general ETL or automatic
business-data repair.

See the [OCEL specification](https://www.ocel-standard.org/specification/overview/)
for the interchange standard and the [book sprint plan](../plans/white-belt-book-preview.md)
for the first implementation slices.

## Implementation note (2026-10-23)

NumericLogContract and NumericEventLog now implement distinct numeric activity
and lifecycle ingestion; CSVTabularAdapter covers declared tabular sources.
The shared mechanical data-quality engine is outside analytical kernels, allowing
both public validation and adapters to enforce the same contract while keeping
the accepted import boundaries. This does not implement lifecycle projection,
order reconstruction, or OCEL ingestion.
