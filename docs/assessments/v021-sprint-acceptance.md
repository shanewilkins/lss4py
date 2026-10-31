# v0.2.1 sprint acceptance

Assessed locally on 2026-10-27. **S1–S6 standalone implementation scope is
accepted.** This assessment covers the current working tree and an explicitly
fingerprinted installed wheel. It does not assert publication or completion of
the sibling book's dependency update. Package metadata remains 0.2.0 under the
accepted sprint constraint; v0.2.1 is the intended release target.

## Tested identity

The working tree includes uncommitted sprint changes based on Git revision
`bce22b33bfdad5e16d7d83cad56123cee748e868`. A commit ID alone would not identify
the tested code. The retained `artifacts/acceptance/source-snapshot.json` hashes
192 source, test, fixture/example, tool, CI and dependency/quality configuration
files. Documentation is excluded so this acceptance record can be finalized
without changing the executable snapshot.

- Executable-input snapshot SHA-256:
  `34ddd1470a379236b0965662edb5e1856b7af3e18ee2eba3c26e99a3dd993dff`.
- Exact tested wheel: `lss4py-0.2.0-py3-none-any.whl`.
- Wheel SHA-256:
  `c9a762cea2f70aef1d8aef1683df5d192293aa8893d2f884e976451aa04a1028`.
- Runtime: local macOS, Python 3.14.2, locked dependencies, released FLO 0.4.3.

Artifacts and logs are retained under ignored `artifacts/acceptance/`. They are
local evidence, not committed release artifacts. The final input snapshot is
checked again against the working tree after the gates.

## Gate results

| Gate | Local result |
| --- | --- |
| Locked pre-push source gates | Pass: Ruff, formatting, hook validation, Vulture, lock consistency, ty and all eight import boundaries |
| Full source suite with required Arrow | 1,983 passed; five explicitly deferred expected failures |
| Full-package statement coverage | 95.71%; 3,684 statements, 158 missing; unchanged 90% gate, no exclusions |
| Exact-wheel base installation | 28 passed |
| Exact-wheel pandas installation | 38 passed |
| Exact-wheel storage installation | 40 passed |
| Exact-wheel FLO/plotting ecosystem installation | 51 passed |
| Complete installed matrix | 157 passed, outside the checkout, no editable imports |
| Installed development-environment dependency audit | No known vulnerabilities found |
| Wheel and source distribution metadata | Twine passes both; project/source/distribution versions agree at 0.2.0 |
| GitHub workflow validation | actionlint 1.7.11 passes; optional shellcheck/pyflakes integrations disabled as in CI |

These are local results, not a claim that hosted Linux CI has executed this
working tree. Statement coverage does not establish branch coverage. Workflow
and Markdown-rendering stubs remain visible in coverage and unimplemented.

## Acceptance evidence

The installed subprocess example reads the actual pinned book `.flo`, calls
FLO's public validation/export facade and creates a projection with explicit
observation-to-node mapping. Model metadata supplies every mapped task's baseline
VA/RNVA/NVA class. Analyst conventions supply the clock/boundary, complete cohort,
parallel Wash/Dry envelope and right-first-time rules; Python does not duplicate
the baseline class lists.

`tests/test_derived_policy.py` verifies that changing a model class changes
measured VA/PCE, while display-name and modeled-duration changes leave observed
calculations intact. Missing/invalid classes, unmapped activities and correction
conflicts fail explicitly. The pinned example additionally rejects changed
model, mapping and observed CSV bytes before writing successful evidence to a
fresh destination.

`e2e/ecosystem/test_book_journey.py` runs the actual example through installed
packages. It compares all eight reconstructed fields for every order with the
independently prepared CSV, including WNF-003's two Wash/two Dry loads and
82.7 VA minutes. It reproduces:

- 39 complete orders and 330 retained source observations.
- 3535.3 VA minutes / 25840.5 lead minutes; 13.7% cohort PCE.
- 662.6-minute mean lead; 676.2-minute nearest-rank P90 among 21 eligible orders.
- Six deadline misses among 21 eligible orders.
- Five correction occurrences affecting five orders.

The restored audited bundle preserves typed reconstruction/metrics, input hashes,
source snapshots/licenses, model/producer revisions, mapping/classes, clock,
boundary and remaining analyst conventions. The FLO SVG is a modeled rendering;
it does not claim a measured overlay. The CSV-only route and the base installation
remain independent of FLO. Portable schema validation and policy derivation do
not import the producer. Installed duration-conversion checks retain baseline
PCE and conversion attribution. The standalone bundle-validator journey retains
its standard-library-only installation boundary.

## Pydantic pilot recommendation

Retain the bounded process/projection pilot. Strict shape validation improves
nested error locations and removes handwritten traversal/flag policy while
keeping graph/mapping constraints explicit. The measured S2 comparison reduced
conditional/loop/exception constructs from 28 to 18, but increased combined code
from 247 to 263 lines. This justifies clearer boundary policy, not a claim of
less total code or a broad migration.

The source, base-install and ecosystem tests preserve original canonical
snapshots/fingerprints, optional fields, extensible producer metadata and both
0.4.2/0.4.3 restoration profiles. Keep domain dataclasses, numerical kernels and
the standalone bundle validator unchanged. Consider another Pydantic boundary
only when it has a concrete validation burden and measured compatibility and
dependency benefits. See the [dated S2 assessment](v021-pydantic-pilot.md).

Pydantic (`>=2.12,<3`) and Pint (`>=0.25,<1`) are explicit core dependencies.
FLO remains optional and pinned to 0.4.3. Pint conversion is a separate explicit
seconds/minutes/hours boundary with a private lazy registry and portable
preparation evidence; it does not infer operating calendars. No further
Pydantic migration or general unit/calendar expansion is accepted here.

## Release handoff

The [workflow guide](../flo-book-workflow.md) documents execution and restoration;
[draft release notes](../releases/v0.2.1.md) describe the delivered scope and
dependency/toolchain changes. Requirements evidence links cover demonstrated
behavior without changing publication-related statuses.

Before an official release, select and synchronize the package version, rebuild
and verify the selected publication artifacts, then perform the tag/publication
and official-installation checks. Updating the sibling book lockfile and
verifying its published Chapter 9 environment remain separate work. This sprint
neither published a package nor changed that sibling repository.
