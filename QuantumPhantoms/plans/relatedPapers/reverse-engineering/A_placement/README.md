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
| #18 | [SYN-LUNGS anatomy-informed placement (+ lungmask, TotalSegmentator on LIDC)](dossiers/18-syn-lungs-placement.md) | ★★ | classical | adapted (pipeline validated; reproduction not matched, n=9) |

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


## Pipeline readiness

<!-- readiness: prototype -->

A has not run inside the chain yet. LIDC-IDRI-0004 has no segmentation cache, so the first `place` stage costs
~25–75 min CPU (probe `runs/20261029-185947-probe-gaps`). The CLI itself is chain-ready: every flag the chain passes exists, and the seed
descends from the certificate (`--seed-hex derive(cert, "A.place")`). The class rule is the real limit: on LIDC it
undercounts juxtapleural nodules (0.56 / 0.44 / 0.00 vs 0.33 / 0.45 / 0.22, n = 9), so the prior B samples from is biased.

**Weak links**

| Weak link | Kind | Why it limits reliability | Evidence | To strengthen |
|---|---|---|---|---|
| Juxtapleural undercount | assumption | the one-voxel contact rule misses nodules 0.8–2.5 mm from the wall; B's class prior inherits the bias | #18: 0.56 / 0.44 / 0.00 vs 0.33 / 0.45 / 0.22 (n = 9) | distance rule (`d_pleura ≤ r`) on the annotations too; rerun the 20-scan repro |
| No segmentation cache on the chain host | integration | the first chain on a host blocks ~25–75 min; caches in gitignored `runs/` were lost with the worktrees | probe `A.segment` | pre-segment LIDC-IDRI-0004 once; GPU |
| Radius fallback | integration | `place` without `--radius-mm` needs an A repro-proportions run (none on disk → `SystemExit`) | probe `A.place`; `place.py:33-36` | the runner passes `--radius-mm 4.72`; make the radius explicit (CCR-A1) |
| Size vs class re-check deferred | integration | a large draw at a juxtapleural site may cross the pleura or change class | runner check in `draw` (not reached yet) | re-classify with the drawn size; reject or re-place |

**Used as-is in the chain?** Yes, with `--radius-mm` supplied by the runner; not yet exercised on the chain host. Full gap list: [INT](../INT_integration/README.md); whole chain: [index](../index.html).


## Future

Shared, pipeline-wide context (end goal, digital-twin path, cross-letter risks) lives once in the
[whole-pipeline Future](../future.md). This section covers only what this letter adds. Every claim carries a label:
<span class="chip evidence">evidence-based</span> (a number in this repo or a cited paper), <span class="chip extrapolation">extrapolation</span> (a reasoned step beyond the evidence),
<span class="chip speculative">speculative</span> (possible, not supported yet).

### 1. Aim of the paper(s)

- **[A01] SYN-LUNGS / X-Lesions:** insert synthetic nodules into real chest CT at anatomically plausible
  places, so detection models learn from realistic locations rather than random ones.
- **[F01] Ambrosini–O'Dell:** a simulated lung-nodule dataset built from published shapes and three placement
  classes (free, juxtavascular, juxtapleural), citing Kostis.
- **[A03] lungmask, [A04] TotalSegmentator:** open, robust segmentation of lungs, lobes, vessels and many other
  structures, so anatomy can be measured automatically on any scan.
- **[A02] LIDC-IDRI:** a public chest-CT collection with nodules annotated by several radiologists, the reference
  every other letter is checked against.

Why it matters: where a nodule sits changes how hard it is to see. A nodule touching the chest wall or a vessel
blends into its neighbour, and a detector trained without such cases never learns them.

### 2. Contribution

- A seeded, replayable **site sampler** on real LIDC hosts: native-grid masks, candidate sites per class, and a
  **context vector** (class, lobe, distances to pleura/vessel/airway, local HU) that B, E and F all consume. <span class="chip evidence">evidence-based</span>
- An honest **negative result** with a diagnosis: the pre-registered one-voxel contact rule gives class proportions
  0.56 / 0.44 / 0.00 against Kostis' 0.33 / 0.45 / 0.22 (n = 9). Juxtapleural nodules 0.8–2.5 mm from the wall are
  missed, and the dossier names the fix. <span class="chip evidence">evidence-based</span>
- A reusable contract (`site_candidates`, `anatomy_masks`): any later organ module can plug into B–H unchanged. <span class="chip extrapolation">extrapolation</span>

### 3. Role in cancer detection

**End goal:** test sets that deliberately **over-sample the hard locations** (juxtapleural, juxtavascular), each
with an exact ground-truth mask, so a detector's sensitivity can be measured *per location class*. The
placement layer decides which clinical blind spot a cohort probes. It does not make tumours look more real; that
is F's job. <span class="chip extrapolation">extrapolation</span>

### 4. Beyond lungs

- **Other organs.** "Segment, then sample sites with context" works for any organ a segmentation tool covers:
  liver lesions near portal vessels (Pixel2Cancer [E01] already grows liver tumours), kidney, pancreas. <span class="chip extrapolation">extrapolation</span>
- **Beyond cancer.** The same site logic can place non-tumour findings in vessel or parenchyma masks, such as
  emboli or emphysema regions, for training and quality control. <span class="chip speculative">speculative</span>
- **Treatment planning.** Distances to airways and vessels already sit in the context vector. They are the
  quantities that decide biopsy paths, ablation margins and radiotherapy organ-at-risk constraints. <span class="chip extrapolation">extrapolation</span>

### 5. Long-term vision: toward a digital twin

<div class="callout speculative">

<span class="chip speculative">speculative</span> A is the twin's **anatomy layer** ("where things are"). The logical path from today:
(1) a generic host scan plus a sampled site (now) →
(2) the patient's *own* segmentation, with a lesion at the patient's real nodule position →
(3) all organs, using multi-structure segmentation [A04] and computational phantoms built from CT
([A05] XCAT 3.0 digital twins) →
(4) an anatomy model that updates at each new scan. Steps 2–3 are engineering on existing tools; step 4 needs
longitudinal data access that does not exist in this project.

</div>

### 6. Predictions

**5 years**: grounded in what runs today.
*Assumptions:* CPU/GPU segmentation as now (lungmask, TotalSegmentator); public LIDC-IDRI data; A stays classical.
- The pipeline places sites on real LIDC hosts, and the reproduction is diagnosed but not matched. <span class="chip evidence">evidence-based</span>
- A distance-based class rule (`d_pleura ≤ r`) applied to annotations as well as planned spheres brings the
  juxtapleural share toward 0.22. <span class="chip extrapolation">extrapolation</span>
- Class priors re-estimated over all LIDC nodules replace B's sidecar prior. <span class="chip extrapolation">extrapolation</span>

**10 years**: reasonable extrapolation.
*Assumptions:* routine automatic segmentation in clinical archives; validated placement priors per organ.
- Patient-specific "where would a new nodule be hardest to see?" studies on a given patient's anatomy. <span class="chip extrapolation">extrapolation</span>
- The same contract carries liver and kidney placement, with organ-specific classes. <span class="chip extrapolation">extrapolation</span>

<div class="callout speculative">

**15 years**: speculation allowed.
*Assumptions:* fault-tolerant quantum hardware exists; anatomy segmentation stays classical.
- <span class="chip speculative">speculative</span> Fault tolerance unlocks nothing *directly* for A. The gain is indirect: B could jointly sample over
  thousands of candidate sites with amplitude-estimation-style algorithms (claim level L3), which needs deep
  circuits that only fault-tolerant hardware runs.

</div>

### 7. Risks and obstacles

| Risk | Kind | Why it matters | Mitigation |
|---|---|---|---|
| Segmentation errors at the pleura | technical | wall-contact classes hinge on a few voxels | check against the readers' annotations; report per-class uncertainty |
| 25–75 min CPU per host | technical | slows any cohort to hours | cache per host; GPU |
| Few juxtapleural examples (n = 9 matched nodules) | data | the class prior is statistically weak | all LIDC nodules; a second public set |
| Old scanners in LIDC | data | anatomy and noise from 2000s CT | add newer hosts (Mayo [A06]) |
| Prior provenance | regulatory | a prior without a citation cannot be defended | every prior cited and versioned in the rulebook |
| Reproduction not matched | validation | the class rule is not yet trustworthy | rerun the 20-scan repro after the fix |

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
