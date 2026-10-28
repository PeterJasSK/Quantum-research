# A — Placement: anatomy-informed site + context vector

> Letter folder `A_placement/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/A_placement/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
Choose where a synthetic nodule may sit in a real 3-D chest CT. Lung, lobe, vessel and airway masks (lungmask, TotalSegmentator) on LIDC host scans; SYN-LUNGS-style placement rules with three placement classes (free, juxtavascular, juxtapleural). Each candidate site carries a **context vector** (placement class, lobe, distances to pleura/vessel/airway, local HU) that B conditions the circuit on and E/F use to constrain growth and insertion.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #18 | [SYN-LUNGS anatomy-informed placement (+ lungmask, TotalSegmentator on LIDC)](dossiers/18-syn-lungs-placement.md) | ★★ | classical | listed |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- host CT (LIDC-IDRI DICOM, read locally)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `anatomy_masks` — schema: [`anatomy_masks.schema.json`](../shared/contracts/anatomy_masks.schema.json) · stub example: [`shared/stubs/anatomy_masks/anatomy_masks.json`](../shared/stubs/anatomy_masks/anatomy_masks.json)
- `site_candidates` — schema: [`site_candidates.schema.json`](../shared/contracts/site_candidates.schema.json) · stub example: [`shared/stubs/site_candidates/sites.json`](../shared/stubs/site_candidates/sites.json)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to A_placement/runs/ via shared.runrecord. -->
_Pending (feature A)._

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
_Pending (feature A)._ Planned: Placement-class proportions against LIDC annotations.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
Classical stage (claim level n/a). No patient voxels leave this letter except as masks/sites for the host scan itself; privacy-by-construction applies to generators downstream.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[A01], [A02], [A03], [A04] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
