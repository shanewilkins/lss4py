# Original FLO 0.4.2 producer snapshot

These are the original synthetic `baseline.flo` and public `process-export.json`
used by the 0.4.2 bridge tests. They are retained unmodified to verify restoration
of that supported producer profile after the integration extra moves to 0.4.3.

The old source assigns processing time to a decision node. FLO 0.4.3 rejects
that placement with E1508. The current parent fixture separates the review task
from its decision, retaining observation IDs, numerical expectations and explicit
rework/handoff meaning. Do not regenerate this historical export with the current
producer or describe its source as valid FLO 0.4.3.
