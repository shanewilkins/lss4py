# 0001: Use lightweight document governance

- Status: Accepted
- Date: 2026-08-09
- Deciders: Maintainers
- Related requirements: UR-007, TR-011, TR-012

## Context

The repository has a stable Yellow Belt slice, broader product-vision documents,
experimental modules, and an R `SixSigma` compatibility target. Without explicit
document roles, planned capabilities can be mistaken for implemented behavior and
sequencing can drift across multiple roadmaps.

The project needs enough governance to preserve intent and traceability without
creating a heavyweight approval process for a pre-1.0 library.

## Decision

LSS4PY will use:

- `UR-NNN` user requirements for user-verifiable outcomes;
- `TR-NNN` technical requirements for implementation constraints;
- numbered ADRs for durable decisions;
- one horizon-based roadmap as the source of delivery sequencing; and
- explicit requirement-to-requirement traceability.

Status claims must cite repository evidence. Vision documents remain useful inputs
but are non-normative.

## Alternatives considered

- **Use issues and the README only.** This is simple, but it does not preserve
  durable decisions or distinguish current behavior from long-term intent.
- **Adopt a formal requirements-management framework.** This would add more
  ceremony than the current project size justifies.
- **Keep all governance in one document.** This makes review easy initially but
  causes architecture history, requirements, and sequencing to blur over time.

## Consequences

- Public behavior changes require small, linked documentation updates.
- The roadmap and compatibility matrix have distinct ownership and should not
  duplicate sequencing.
- Maintainers must keep status evidence honest, especially for stubs and planned
  capabilities.
- Governance can be expanded later if multiple packages or release trains require
  it.

