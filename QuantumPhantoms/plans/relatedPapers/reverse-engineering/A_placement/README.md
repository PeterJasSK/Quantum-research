# A — Placement: anatomy-informed site + context vector

> Letter folder `A_placement/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/A_placement/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
A chooses where a synthetic nodule may sit in a real 3-D chest CT.
- **Masks:** for an LIDC-IDRI host scan it builds lung, lobe, vessel, airway and body masks on the scan's native grid, using lungmask R231/LTRCLobes and TotalSegmentator `lung_vessels`.
- **Sites:** it then samples candidate sites in the three placement classes of Ambrosini [F01]: free, juxtavascular (at a large-vessel bifurcation) and juxtapleural.
- **Context vector:** each site carries the vector that B conditions the circuit on and that E/F use to constrain growth and insertion: placement class, lung, lobe, distances to pleura/vessel/airway, local HU, plus `extra` = nominal radius, vessel density and distance to a bifurcation.
- **Scope:** A emits **candidates only**. B draws the site (B-2) and owns the class prior.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #18 | [SYN-LUNGS anatomy-informed placement (+ lungmask, TotalSegmentator on LIDC)](dossiers/18-syn-lungs-placement.md) | ★★ | classical | dissected (pipeline validated; reproduction not matched, n=9) |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- **Host CT:** LIDC-IDRI DICOM, downloaded to `$LIDC_ROOT` (default `~/data/LIDC-IDRI`, outside the repo).
- **Annotations:** LIDC nodule annotations from pylidc's bundled database.
- A has no upstream contract.

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `anatomy_masks`:
  - schema: [`anatomy_masks.schema.json`](../shared/contracts/anatomy_masks.schema.json);
  - stub example: [`shared/stubs/anatomy_masks/anatomy_masks.json`](../shared/stubs/anatomy_masks/anatomy_masks.json).
- `site_candidates`:
  - schema: [`site_candidates.schema.json`](../shared/contracts/site_candidates.schema.json);
  - stub example: [`shared/stubs/site_candidates/sites.json`](../shared/stubs/site_candidates/sites.json).
- **Where they land:** a placement run writes both, plus copies of the six masks and `run.json`, to `A_placement/runs/<run_id>-place/`. The run directory is self-contained, so INT hands it over as is.
- **Reference run:** `runs/20261029-122607-place` (host LIDC-IDRI-0004, 1.25 mm slices, seed `00…00`, r = 4.72 mm, 10/10/10 sites). `runs/` is gitignored, so regenerate it with the commands below.

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to A_placement/runs/ via shared.runrecord. -->
A is classical, so there is no simulator and no quantum numbers. Run everything from `reverse-engineering/`:

```bash
conda env create -f A_placement/environment.yml && conda activate qp-re-a   # py3.12, CPU torch
python -m A_placement.src.lidc_fetch --select 20 --fetch      # subset list + TCIA download + ~/.pylidcrc
python -m A_placement.src.segment --patient LIDC-IDRI-0004    # masks -> runs/cache/<pid>/ (~25 min CPU)
python -m A_placement.repro.class_proportions --workers 3     # reproduction (cached scans skipped)
python -m A_placement.src.place --patient LIDC-IDRI-0004 --per-class 10 [--seed-hex HEX] [--radius-mm R]
python -m A_placement.src.export_figures --run A_placement/runs/<run_id>-place
python -m shared.validate A_placement/runs/<run_id>-place/{sites,anatomy_masks,run}.json
```

**Notes:**
- **Cost:** segmentation is CPU-bound: about 25 min per scan alone, and up to 75 min when the machine is shared. Masks are cached per patient (keyed by host sha256 and tool versions).
- **Tool versions:** pylidc 0.2.3 needs `setuptools<81` and a numpy-alias shim (`lidc_io.pylidc()`). TotalSegmentator 2.18 emits `lung_arteries`, `lung_veins`, `lung_airways` and `lung_airways_wall` for the `lung_vessels` task.

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
**#18, placement-class proportions of LIDC consensus nodules vs Kostis (via Ambrosini [F01]).**
- **Paper:** 0.33 / 0.45 / 0.22 (free / juxtavascular / juxtapleural).
- **Ours:** 0.56 / 0.44 / 0.00, n = 9 nodules in 6 scans.
- **Verdict:** not matched and inconclusive. Juxtavascular agrees, juxtapleural is undercounted by the pre-registered one-voxel contact rule (4 of 9 nodules sit 0.8–2.5 mm from the wall), and the thresholds were not tuned.
- **Details:** [figure](figures/18-class-proportions.png) and the [dossier](dossiers/18-syn-lungs-placement.md#our-reproduction-number--figure) (diagnostic table, candidate fix).

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
Classical stage: no quantum claim.
- **Privacy:** no patient voxels leave this letter except the host scan's own masks and sites. Privacy-by-construction applies to the generators downstream.
- **Known bias:** on real annotations the class rule **undercounts juxtapleural** nodules.
  - The placement of planned spheres uses distances (`d_pleura ≤ r`), and those sites do abut the wall.
  - The measured class proportions are not yet a trustworthy prior for B.
- **Source gap:** SYN-LUNGS [A01] contains no placement rules. The rule comes from F01.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
**Papers:** [A01] SYN-LUNGS / X-Lesions · [A02] LIDC-IDRI · [A03] lungmask (Hofmanninger) · [A04] TotalSegmentator (Wasserthal) · [F01] Ambrosini (nodule classes, citing Kostis). The PDFs are in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

**Licences:** lungmask Apache-2.0 · TotalSegmentator Apache-2.0 · pylidc MIT · tcia_utils Apache-2.0 · LIDC-IDRI CC BY 3.0 (TCIA).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
- **CCR-A1 (`site_candidates`, optional):** promote `context.extra.nominal_radius_mm` to a first-class context field.
  - **Why:** the placement class depends on lesion size, which B draws later.
  - **Local workaround:** the radius is carried in `extra`, and consumers re-check with `A_placement.src.classes.classify_site`.
