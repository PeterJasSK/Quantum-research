# F — Render into CT: realistic, scanner-matched insertion

> Letter folder `F_render/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/F_render/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
Cell states → HU from an LIDC-fitted lesion library; supersampled partial volume; additive-delta insertion (vessel max-rule, ground-glass α-blend); 3-D PSF + noise from the host scan's own fingerprint (MTF from the air–skin edge, local NPS and σ), inserted into the full 3-D host volume. 2-D slices only as a final export. Upgrade path: projection-domain insertion on Mayo Siemens raw data via XCIST, then a NAEOTOM Alpha approximation.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #13 | [SyntheticTumors / Label-free pipeline](dossiers/13-synthetic-tumors.md) | ★★★ | classical | listed |
| #14 | [Lesion-model fitting (Ambrosini; Solomon–Samei PMB 2014)](dossiers/14-lesion-model-fitting.md) | ★★★ | classical | listed |
| #15 | [Scanner fingerprint estimator (Sanders MTF 2016; Divel–Pelc 2019; Peng)](dossiers/15-scanner-fingerprint.md) | ★★★ | classical | listed |
| #16 | [Projection-domain insertion rebuilt on XCIST (Mayo; Mayo LDCT raw data)](dossiers/16-xcist-projection-insertion.md) | ★★ | classical | listed |
| #17 | [DukeSim NAEOTOM Alpha parameters (McCabe)](dossiers/17-naeotom-alpha-params.md) | ★★ | classical | listed |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `growth_trajectory` — stub: [`shared/stubs/growth_trajectory/growth_trajectory.json`](../shared/stubs/growth_trajectory/growth_trajectory.json) · schema: [`growth_trajectory.schema.json`](../shared/contracts/growth_trajectory.schema.json)
- `anatomy_masks` — stub: [`shared/stubs/anatomy_masks/anatomy_masks.json`](../shared/stubs/anatomy_masks/anatomy_masks.json) · schema: [`anatomy_masks.schema.json`](../shared/contracts/anatomy_masks.schema.json)
- `site_candidates` — stub: [`shared/stubs/site_candidates/sites.json`](../shared/stubs/site_candidates/sites.json) · schema: [`site_candidates.schema.json`](../shared/contracts/site_candidates.schema.json)
- `tumor_draw` — stub: [`shared/stubs/tumor_draw/tumor_draw.json`](../shared/stubs/tumor_draw/tumor_draw.json) · schema: [`tumor_draw.schema.json`](../shared/contracts/tumor_draw.schema.json)
- `certificate` — extracted seed; stub: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json) · schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `lesion_model_library` — schema: [`lesion_model_library.schema.json`](../shared/contracts/lesion_model_library.schema.json) · stub example: [`shared/stubs/lesion_model_library/lesion_model_library.json`](../shared/stubs/lesion_model_library/lesion_model_library.json)
- `scanner_fingerprint` — schema: [`scanner_fingerprint.schema.json`](../shared/contracts/scanner_fingerprint.schema.json) · stub example: [`shared/stubs/scanner_fingerprint/scanner_fingerprint.json`](../shared/stubs/scanner_fingerprint/scanner_fingerprint.json)
- `hybrid_volume` — schema: [`hybrid_volume.schema.json`](../shared/contracts/hybrid_volume.schema.json) · stub example: [`shared/stubs/hybrid_volume/hybrid_volume.json`](../shared/stubs/hybrid_volume/hybrid_volume.json)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to F_render/runs/ via shared.runrecord. -->
_Pending (feature F)._

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
_Pending (feature F)._ Planned: Robins/Duke volume agreement (< 3 %) on one case.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
Classical stage (n/a). Privacy-by-construction: only fitted parameters leave LIDC; learned refiners (DiffTumor, MAISI) are ablation only. Mayo raw data: Siemens cases only for Siemens work.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[A06], [F01], [F03], [F04], [F05], [H01] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
