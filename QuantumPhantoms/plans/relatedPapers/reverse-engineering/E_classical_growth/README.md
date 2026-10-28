# E — Classical growth: lung Pixel2Cancer engine

> Letter folder `E_classical_growth/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/E_classical_growth/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
Rebuild Pixel2Cancer's growth/invasion/death rules standalone and port them to lungs with Kansal–Torquato proliferating/dormant/necrotic layers, constrained by A's masks, seeded from C's extracted seed (shared.seedhash.rng) and started from D's seed shape (stub shape until D exists). Snapshots give baseline/follow-up pairs.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #11 | [Pixel2Cancer + Kansal–Torquato layers](dossiers/11-pixel2cancer.md) | ★★★ | classical | listed |
| #12 | [High-performance CA (Poleszczuk–Enderling)](dossiers/12-hpc-cellular-automaton.md) | ★ | classical | listed |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `anatomy_masks` — stub: [`shared/stubs/anatomy_masks/anatomy_masks.json`](../shared/stubs/anatomy_masks/anatomy_masks.json) · schema: [`anatomy_masks.schema.json`](../shared/contracts/anatomy_masks.schema.json)
- `site_candidates` — stub: [`shared/stubs/site_candidates/sites.json`](../shared/stubs/site_candidates/sites.json) · schema: [`site_candidates.schema.json`](../shared/contracts/site_candidates.schema.json)
- `tumor_draw` — stub: [`shared/stubs/tumor_draw/tumor_draw.json`](../shared/stubs/tumor_draw/tumor_draw.json) · schema: [`tumor_draw.schema.json`](../shared/contracts/tumor_draw.schema.json)
- `certificate` — extracted seed; stub: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json) · schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json)
- `seed_shape` — stub: [`shared/stubs/seed_shape/seed_shape.json`](../shared/stubs/seed_shape/seed_shape.json) · schema: [`seed_shape.schema.json`](../shared/contracts/seed_shape.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `growth_trajectory` — schema: [`growth_trajectory.schema.json`](../shared/contracts/growth_trajectory.schema.json) · stub example: [`shared/stubs/growth_trajectory/growth_trajectory.json`](../shared/stubs/growth_trajectory/growth_trajectory.json)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to E_classical_growth/runs/ via shared.runrecord. -->
_Pending (feature E)._

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
_Pending (feature E)._ Planned: Pixel2Cancer growth behaviour on one of their organs.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
Classical stage (n/a). The certified seed gives provenance only; never claim "more realistic because quantum".

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[E01], [E02], [E03] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
