# E — Classical growth: lung Pixel2Cancer engine

> Letter folder `E_classical_growth/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/E_classical_growth/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
Grows one lung tumor in 3-D from a chosen site to a baseline and a follow-up snapshot, using classical cellular automata rebuilt from two papers:
- **Kansal–Torquato [E02]** gives the internal structure: a proliferating rim, a dormant shell and a necrotic core, with thicknesses ∝ Rt^(2/3).
- **Pixel2Cancer [E01]** gives the interaction with anatomy: tissue levels from HU, and pressure-threshold barriers.

The lung is constrained by A's masks:
- the pleura and fissures are hard walls;
- vessels and airways give way only under pressure.

Growth starts from D's seed shape, and every random choice comes from C's extracted seed. The parameters per tumor type (solid / part-solid / ground-glass) are calibrated to published lung doubling times. The output is a `growth_trajectory`: 0.5 mm 3-D state lattices, states 0 host / 1 proliferating / 2 dormant / 3 necrotic. It goes to F, which turns states into HU and inserts them into CT, and to H, which validates against follow-up pairs.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #11 | [Pixel2Cancer + Kansal–Torquato layers](dossiers/11-pixel2cancer.md) | ★★★ | classical | adapted |
| #12 | [High-performance CA (Poleszczuk–Enderling)](dossiers/12-hpc-cellular-automaton.md) | ★ | classical | dissected |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `anatomy_masks` — `lungs`, `lobes`, `vessels`, `airway`, `host_ct` are resampled onto the growth lattice. Stub: [`shared/stubs/anatomy_masks/anatomy_masks.json`](../shared/stubs/anatomy_masks/anatomy_masks.json) · schema: [`anatomy_masks.schema.json`](../shared/contracts/anatomy_masks.schema.json)
- `site_candidates` — site centre, lung, lobe and placement class. Stub: [`shared/stubs/site_candidates/sites.json`](../shared/stubs/site_candidates/sites.json) · schema: [`site_candidates.schema.json`](../shared/contracts/site_candidates.schema.json)
- `tumor_draw` — `site_id`, `size_mm` (baseline size) and `type` (parameter set); `margin` is not used by E. Stub: [`shared/stubs/tumor_draw/tumor_draw.json`](../shared/stubs/tumor_draw/tumor_draw.json) · schema: [`tumor_draw.schema.json`](../shared/contracts/tumor_draw.schema.json)
- `certificate` — `status` must be `pass`; `extracted_seed_hex` seeds every PRNG. Stub: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json) · schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json)
- `seed_shape` — `occupancy` becomes the initial proliferating cells, centred on the site. Stub: [`shared/stubs/seed_shape/seed_shape.json`](../shared/stubs/seed_shape/seed_shape.json) · schema: [`seed_shape.schema.json`](../shared/contracts/seed_shape.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `growth_trajectory` — `E_classical_growth/runs/<run_id>/growth_trajectory/growth_trajectory.json` + `step_<day>.npz` (`state` uint8 (z, y, x), `spacing_mm_xyz`). Snapshots: `baseline` (equivalent diameter reaches `size_mm`), `follow-up` (+90 d by default), optional `other`. Schema: [`growth_trajectory.schema.json`](../shared/contracts/growth_trajectory.schema.json) · stub example: [`shared/stubs/growth_trajectory/growth_trajectory.json`](../shared/stubs/growth_trajectory/growth_trajectory.json)
- Sidecars in the same folder (letter-local, **not** contracts): `growth_summary.json` (per day: Rt, volume, equivalent diameter, layer fractions, VDT, barrier contacts/entries; checks: sphericity, inertia ratio, voxels outside lung, vessel-entry day) and `environment.npz` (barrier 0/1 hard/2 soft and tissue levels on the lattice).

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to E_classical_growth/runs/ via shared.runrecord. -->
All classical, no quantum simulation. Run from `reverse-engineering/`:

```bash
# reproductions
python -m E_classical_growth.repro.kt_table2                    # [E02] Table 2, ~1.85e6-site lattice (~15 min, ~4 GB)
python -m E_classical_growth.repro.kt_table2 --spacing-scale 1 --lattice-radius-mm 50   # literal eq. 2 lattice
python -m E_classical_growth.repro.p2c_behaviour                # [E01] behaviours B1–B4 (~15 s)
python -m E_classical_growth.repro.calibrate_lung               # p0 per tumor type → src/params_lung.json (~20 s)

# lung engine (all inputs default to shared/stubs)
python -m E_classical_growth.src.grow                           # exit 0 ok, 1 invalid input, 2 certificate refused, 3 growth failed
python -m E_classical_growth.src.grow --site-id S002 --follow-up-days 600   # verification override of the draw's site
python -m E_classical_growth.src.grow --masks … --sites … --draw … --certificate … --seed-shape …
python -m E_classical_growth.src.figures E_classical_growth/runs/<grow run> [...]   # 2-D slice export + growth curves
python -m shared.validate E_classical_growth/runs/<grow run>/growth_trajectory/growth_trajectory.json
```

Lattice caches for the KT repro are written to `runs/_cache/`. Like everything in `runs/`, they are gitignored.

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
**#11 Kansal–Torquato [E02] Table 2** (run `20261028-191231-kt-table2`; 1,851,791 sites; tolerance ±10 percentage points for fractions, ±35 % doubling time, ±25 % day):

| Rt (mm) | day Sim / ours | growth fraction Sim / ours | necrotic fraction Sim / ours | doubling time (d) Sim / ours | agreement |
|---|---|---|---|---|---|
| 0.5 | 87 / 61 | 0.40 / 0.50 | 0.38 / 0.08 | 5 / 10.5 | no |
| 5 | 198 / 227 | 0.30 / 0.29 | 0.45 / 0.36 | 38 / 25.7 | yes |
| 18.5 | 405 / 449 | 0.19 / 0.20 | 0.57 / 0.54 | 72 / 64.8 | yes |
| 25 | 492 / 555 | 0.13 / 0.19 | 0.60 / 0.58 | 112 / 105.1 | yes |

Three of the four clinical stages agree. The spheroid stage (0.5 mm) does not, and the reason is in the dossier. The literal eq. 2 lattice (47,037 sites; run `20261029-052947-kt-table2-k1`) fails at every stage, so the paper's reported site count is the operative parameter. Figures: [`kt_table2.png`](figures/kt_table2.png), [`kt_growth_curve.png`](figures/kt_growth_curve.png), [`kt_cross_sections.png`](figures/kt_cross_sections.png) (`*_k1.png` = literal lattice).

**#11 Pixel2Cancer [E01] behaviours.** The paper publishes no growth number; plan Q1 accepts behaviour as the reproduction. Run `20261029-053311-p2c-behaviour`, synthetic liver phantom, liver hyper-parameters:
- **B1 vessel: PASS.** Vessel voxels are invaded only at the 3-push threshold, and the tumor wraps the vessel (12/12 sectors).
- **B2 boundary: PASS.** Extent toward the boundary vs away from it is 6 / 16 mm, and 0 voxels survive outside the organ.
- **B3 death: PASS.** There are no dead cells at ≤ 50 steps, and dead cores appear in exactly the 2 of 6 runs with > 50 steps where the coin flip fired.
- **B4 sizes: PASS.** Diameter is 4.8–57.3 mm over 14–149 steps, with Spearman ρ = 1.0.

Figure: [`p2c_behaviour.png`](figures/p2c_behaviour.png).

**Lung adaptation:**
- **Calibration** (run `20261029-052808-calibrate-lung`): the VDT at 8 mm is 147.6 / 465.8 / 825.4 d against targets of 149 / 457 / 813 d for solid / part-solid / ground-glass. Figure: [`lung_calibration.png`](figures/lung_calibration.png).
- **S001 free** (runs `20261029-052830-grow-S001`, `-052837-grow-S002`, `-052843-grow-S003`): smoothed sphericity 0.89, inertia ratio 0.87.
- **S002 juxtavascular:** in contact with the vessel from day 253. In a 600-day follow-up (`20261029-052850-grow-S002`) the vessel is entered on day 629, only after 30 pushes.
- **S003 juxtapleural:** 0 voxels outside the lung, flattened against the pleura and fissure (inertia ratio 0.43).

Figures: [`lung_S001.png`](figures/lung_S001.png), [`lung_S002.png`](figures/lung_S002.png), [`lung_S003.png`](figures/lung_S003.png), [`lung_growth_curves.png`](figures/lung_growth_curves.png).

**#12** is dissected only: it is ★ read-only, and a reproduction is not needed at nodule scale.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
Classical stage, so no claim level applies. The certified seed gives **provenance only**: it makes every trajectory replayable from the receipt (identical inputs give byte-identical lattices). It does **not** make growth more realistic. Never write "more realistic because quantum".

Further honesty notes:
- All runs so far use **stub inputs**: a synthetic phantom, a stub certificate and a stub seed shape. Every output is `stub: true` until INT.
- The lung VDT targets (Hasegawa et al. 2000) are cited from memory, marked *(verify)*, and their PDF is not in `papers/`.
- `vessel_threshold`, the lung HU bounds, `a` and `Rmax` are stated assumptions (see `src/params_lung.json` `sources`).
- Sphericity is reported both raw and after a 0.5 mm smooth. The raw value (~0.72) is limited by sub-voxel surface roughness.


## Pipeline readiness

<!-- readiness: caveats -->

Draft rating, not yet confirmed by the chain (the chain has not reached E). E's CLI accepts every chain input
(probe: all flags exist), and its lung adaptation holds on the phantom (VDT 147.6 / 465.8 / 825.4 d vs 149 / 457 / 813 d;
KT Table 2 matches 3 of 4 stages). But every run so far is on stubs: E has never grown a tumour inside A's real
masks. The runner now checks `lung_hu_bounds` against the host's lung HU before E runs; `vessel_threshold` is a
push count, not HU, so the plan's HU check does not apply to it.

**Weak links**

| Weak link | Kind | Why it limits reliability | Evidence | To strengthen |
|---|---|---|---|---|
| Stub-only runs | data | behaviour inside real lungmask / TotalSegmentator masks is unknown | honesty notes above (27 runs, all `stub: true`) | the chain's `grow_c` stage |
| `lung_hu_bounds` unchecked on LIDC | assumption | [−950, −600] may exclude real parenchyma voxels | runner `_pre_grow_c` (not reached yet) | adjust only if outside the measured range (plan AC-10) |
| Site ≠ draw silently marks stub | integration | `--site-id` different from the draw's site makes the output `stub: true` (`grow.py:74-77`) instead of failing | agent read; runner check `_post_grow_c` | fail loudly |
| Parameters outside the commit | integration | `src/params_lung.json` is not in the `.py` code hash; it can change after the commit | probe `G.commit` | hash parameter files into the commit |
| VDT targets *(verify)* | assumption | calibration targets cited from memory | honesty notes above | add Hasegawa 2000 to `../papers/` |
| Spheroid stage (0.5 mm) mismatch | component | early growth is off (necrotic 0.08 vs 0.38) | KT table | irrelevant at nodule scale; document |

**Used as-is in the chain?** Expected yes (all flags exist); unverified on real masks. Full gap list: [INT](../INT_integration/README.md); whole chain: [index](../index.html).


## Future

Shared, pipeline-wide context (end goal, digital-twin path, cross-letter risks) lives once in the
[whole-pipeline Future](../future.md). This section covers only what this letter adds. Every claim carries a label:
<span class="chip evidence">evidence-based</span> (a number in this repo or a cited paper), <span class="chip extrapolation">extrapolation</span> (a reasoned step beyond the evidence),
<span class="chip speculative">speculative</span> (possible, not supported yet).

### 1. Aim of the paper(s)

- **[E01] Pixel2Cancer:** grow tumours with a cellular automaton *inside* CT anatomy, to produce synthetic tumours
  that train segmentation AI (liver, pancreas, kidney).
- **[E02] Kansal–Torquato:** a cellular automaton that reproduces Gompertz-like growth and the layered tumour
  structure (proliferating rim, dormant shell, necrotic core).
- **[E03] Poleszczuk–Enderling:** a fast automaton with growing domains for large cell populations.

Why it matters: real nodules **grow**, and growth between two scans is a key signal when doctors judge a nodule.
A generator of growth trajectories gives ground-truth follow-ups that real data rarely provides.

### 2. Contribution

- Kansal–Torquato Table 2 matched at 3 of 4 clinical stages (run `20261028-191231-kt-table2`). <span class="chip evidence">evidence-based</span>
- Pixel2Cancer behaviours B1–B4 pass (vessel, boundary, death, size). <span class="chip evidence">evidence-based</span>
- Lung calibration: volume-doubling time 147.6 / 465.8 / 825.4 d against targets of 149 / 457 / 813 d
  (solid / part-solid / ground-glass; targets marked *(verify)*). <span class="chip evidence">evidence-based</span>
- Lung rules: the pleura and fissures are walls, vessels yield only under pressure, and every trajectory replays
  byte-identically from its seed. <span class="chip evidence">evidence-based</span>

### 3. Role in cancer detection

**End goal:** **paired baseline and follow-up scans with known growth**, to train and test growth-based
assessment (volume, doubling time) and to test whether detectors catch small nodules at the moment they first
become visible. The H #21 protocol measures exactly this on a commercial assistant: reported vs true volume and
doubling time. <span class="chip extrapolation">extrapolation</span>

### 4. Beyond lungs

- **Other organs.** Pixel2Cancer already grows liver, pancreas and kidney tumours [E01]; the lung rules here add
anatomy walls and pressure. <span class="chip evidence">evidence-based</span>
- **Treatment response.** Kill rules for radiotherapy or chemotherapy (proliferating cells removed per dose; a
  slower rim) would turn E into a response simulator. <span class="chip extrapolation">extrapolation</span>
- **Drug response and monitoring.** Fitting the proliferation rate per patient from serial scans gives a
  monitoring quantity ("growing faster than expected"). <span class="chip speculative">speculative</span>

### 5. Long-term vision: toward a digital twin

<div class="callout speculative">

<span class="chip speculative">speculative</span> E is the twin's **dynamics layer**. Path: (1) population-calibrated growth in generic hosts (now) →
(2) parameters fitted to a patient's own serial CT → (3) forecasts of the next scan, checked retrospectively →
(4) "what if" branches for treatment options. Each step needs longitudinal data and validation the project does
not have yet.

</div>

### 6. Predictions

**5 years**
*Assumptions:* CPU/GPU automata as today; few public longitudinal lung CT pairs.
- Growth is calibrated on phantoms; the run on real masks is pending (INT). <span class="chip evidence">evidence-based</span>
- Validation against real follow-up pairs (the doubling-time distribution) on public data. <span class="chip extrapolation">extrapolation</span>
- Therapy-response rules (radiation kill fraction) are added and tested on phantoms. <span class="chip extrapolation">extrapolation</span>

**10 years**
*Assumptions:* access to longitudinal imaging datasets; GPU 3-D automata at whole-lung scale [E03].
- Patient-specific growth fits forecast nodule size at the next scan, evaluated retrospectively. <span class="chip extrapolation">extrapolation</span>

<div class="callout speculative">

**15 years**
*Assumptions:* fault-tolerant hardware.
- <span class="chip speculative">speculative</span> Quantum algorithms for nonlinear dissipative differential equations [D21] could integrate continuum growth
  models (reaction–diffusion) at scales that strain classical solvers (claim level L3). Reading out a full 3-D
  tumour from a quantum state is costly, so any end-to-end gain is uncertain.

</div>

### 7. Risks and obstacles

| Risk | Kind | Why it matters | Mitigation |
|---|---|---|---|
| Calibration targets *(verify)* | data | VDT targets cited from memory | add the source paper |
| Early stage off (0.5 mm) | technical | spheroid-stage fractions do not match | document; irrelevant at nodule scale |
| Stub-only runs | validation | never grown in real masks | INT chain stage `grow_c` |
| Model ≠ prognosis | regulatory | a growth forecast could be misread as clinical advice | research-use labelling; prospective validation |
| Biological realism | technical | layers + pressure are a caricature of tumour biology | compare with follow-up data in H |

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
- [E01] Lai et al., *From Pixel to Cancer: Cellular Automata in Computed Tomography*, MICCAI 2024 (arXiv:2403.06459). Code: github.com/MrGiovanni/Pixel2Cancer (Apache-2.0; read only, not vendored).
- [E02] Kansal, Torquato et al., *Cellular automaton of idealized brain tumor growth dynamics*, BioSystems 55 (2000) 119–127.
- [E03] Poleszczuk & Enderling, *A high-performance cellular automaton model of tumor growth with dynamically growing domains*, Appl. Math. 2014 (arXiv:1309.6015).
- Hasegawa et al., *Growth rate of small lung cancers detected on mass CT screening*, Br J Radiol 2000 *(verify; not in `papers/`)*.

The PDFs are in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
1. **`growth_trajectory.snapshots[]`**: optional `summary {eq_diameter_mm, volume_mm3, f_prolif, f_dormant, f_necrotic}`. *Why:* F and H need size and layer fractions per snapshot without recomputing them. *Workaround:* the `growth_summary.json` sidecar next to the manifest.
2. **`step_NNNN.npz`**: optional `population` uint8 (0–10) key carrying Pixel2Cancer's partial-population field. *Why:* F could use it for the blurry tumor boundary ([E01] §2.3 mapping). *Workaround:* not written in v1 (plan Q10). The engine is layer-based, so this would need a population field to be added in E.
3. **`growth_trajectory`**: optional `draw_id`. *Why:* today the draw is only reachable through `upstream[]`. *Workaround:* `growth_summary.json` carries `draw_id`.
4. **`growth_trajectory`** (note, not a schema change): the lattice placement convention is `origin_mm_lps` = LPS centre of voxel (0, 0, 0), with axes aligned to LPS. This is already implied by VOLUMES.md and is stated here for F.
