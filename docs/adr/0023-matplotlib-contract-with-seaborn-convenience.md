# 0023: Matplotlib contract with Seaborn convenience

- Status: Accepted
- Date: 2026-10-13
- Deciders: Maintainer approval following plotting-library comparison
- Related requirements: UR-029, TR-008, TR-032
- Resolves: decision 10 in [ADR-0022](0022-ecosystem-integration-contracts-and-journey-gates.md)
- Complements: [ADR-0021](0021-reuse-flo-and-established-presentation-libraries.md)

## Context

Practitioners need easy default plots and familiar customization. Matplotlib and
Seaborn share native axes, whereas a ggplot-style Python interface such as Plotnine
adds another public plotting grammar. Several convenient statistical plotters also
aggregate, estimate uncertainty, sort, bin or fit data implicitly, which conflicts
with rendering completed analytical evidence.

## Decision

Matplotlib defines the statistical plotting object and export contract. Single-
panel functions accept an optional `ax=` and return native `Axes`; future composed
study plots return a native `Figure`. LSS4PY supplies domain-oriented entry points
with usable defaults. Seaborn provides local styling and suitable convenience over
prepared results. Both remain in the existing optional visualization extra.

Use Matplotlib directly where exact values, observation order, limits, flags and
annotations matter. Do not invoke implicit Seaborn estimation, uncertainty,
regression, sorting, histogram binning or density fitting during result rendering.
Such numerical preparation belongs in an explicit analytical operation. Preserve
caller-owned axes, result data, diagnostic messages and global plotting settings.
Saving and display remain caller-controlled.

The first plotting implementation is `plot_timing(result, ax=None)`, consuming a
completed `TimingResult`. It is not a control-chart implementation or a capability
study. SVG/PNG journey exports use a declared size/font and freeze measured layout
before switching export backends. Structural checks and a reviewed visual fixture
protect the exported artifact.

## Alternatives considered

- Matplotlib alone gives precise control but requires more presentation setup.
- Seaborn as the public object contract mixes axes-level and figure-level return
  types and requires guarding its implicit statistical operations.
- Plotnine offers a useful grammar of graphics but introduces another interface
  without a current practitioner need.

## Consequences

Consumers can customize native plotting objects and compose plots. Numerical
results remain useful without importing Matplotlib or Seaborn. Adding another
backend requires a concrete workflow and its own contract/export evidence.
Fishbone ownership and any future general rendering-package extraction remain
open; this decision does not restructure FLO.

## Sources

- [Matplotlib object model](https://matplotlib.org/stable/users/explain/quick_start.html)
- [Seaborn axes-level integration](https://seaborn.pydata.org/tutorial/function_overview.html)
- [Seaborn lineplot defaults](https://seaborn.pydata.org/generated/seaborn.lineplot.html)
- [Plotnine grammar of graphics](https://plotnine.org/)
