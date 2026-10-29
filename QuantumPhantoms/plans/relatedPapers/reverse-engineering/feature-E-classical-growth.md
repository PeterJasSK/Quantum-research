# Feature E — Classical growth: lung Pixel2Cancer engine with Kansal–Torquato layers

**Epic:** [`epic-reverse-engineering.md`](./epic-reverse-engineering.md) (Approved, 2026-10-28). E is a Wave-1 letter (parallel with A, C, F) and runs on the frozen W stubs.
**Feature ID:** E
**Author:** Claude (Opus)
**Date:** 2026-10-28
**Status:** Complete (implemented 2026-10-29 in worktree `../qp-re-E`, branch `re-E`; approved 2026-10-28 with all Q1–Q10 defaults)

> **Technical constraints / core directive.** Python 3.13 (conda base) with the libraries already installed: numpy 2.4, scipy 1.15, SimpleITK 2.5.6, scikit-image 0.25, matplotlib 3.10, jsonschema. **No new installs** (no torch, no CUDA, no OpenCV; there is no GPU on this machine). Classical stage: no quantum circuits, no Aer. All files live under `QuantumPhantoms/plans/relatedPapers/reverse-engineering/` (written `RE/` below); every command runs with `RE/` as the working directory (`python -m E_classical_growth.…`). Implement in the worktree `../qp-re-E` on branch `re-E` (epic §3 "Parallel execution"). Write **only** inside `RE/E_classical_growth/` and this plan; never edit `shared/`, the epic, `about.html`, `index.html`, `site/`, `.gitignore` or another letter. Everything is 3-D; 2-D slices are a figure export only. Every PRNG is seeded from the certificate seed via `shared.seedhash.rng`. Nothing is imported from the MVP (`QuantumPhantoms/code/`). **No automated tests; verification is manual plus the paper reproductions.**

---

## 1. Why (Step Goal)

**Before.** W left `E_classical_growth/` as a skeleton: README and dossier templates, `status.json` with #11 and #12 `listed`, and empty `src/`, `repro/`, `figures/`. Downstream letters (F render, H analysis) can only consume the hand-made `shared/stubs/growth_trajectory/` (two trivial snapshots). There is no tumor growth model in this epic, and no reproduced reference for one.

**After.**
- **#11 dissected and reproduced.** Two published methods are rebuilt from the papers in clean NumPy/SciPy:
  - **Kansal–Torquato 2000 [E02]**: the proliferating / dormant (G0) / necrotic layer automaton, with `p_d = p0(1 − r/Rmax)`, `d_p = b·Rt^{2/3}`, `d_n = a·Rt^{2/3}`. Its **Table 2** (growth fraction, necrotic fraction and doubling time at the four clinical radii 0.5 / 5 / 18.5 / 25 mm) is the published number we reproduce.
  - **Pixel2Cancer 2024 [E01]**: the three generic rules (R1 growth, R2 invasion, R3 death), the 4-level quantified organ with level-0 barriers, and the pressure-threshold invasion of vessels and boundaries. The paper publishes no growth number (its results are segmentation DSC and a reader study, which need trained U-Nets and radiologists). We reproduce its **documented growth behaviours** on its liver hyper-parameters instead.
- **#11 adapted to lungs.** One deterministic engine `E_classical_growth/src/` combines:
  - KT layers for the internal structure;
  - Pixel2Cancer's organ interaction for the anatomy: the lung mask is a hard boundary, vessels and airways are pressure-threshold barriers;
  - lung-specific growth parameters per tumor type.

  It reads A's masks and sites, B's draw, C's seed and D's seed shape (all stubs for now). It writes a valid `growth_trajectory` (3-D `step_NNNN.npz` lattices + manifest) with a **baseline** and a **follow-up** snapshot. The same inputs always give the same lattices.
- **#12 dissected.** The Poleszczuk–Enderling data-structure ideas (flattened 1-D lattice, active-cell index list, growing domain) are documented and used where they help. No reproduction, since it is ★ read-only.
- README, dossiers, figures and `status.json` are filled in, so the site shows E with real content at the next build.

This is the epic's highest-priority target (#11, together with #13 in F) and the classical half of the "nobody chose these" chain: certified seed → deterministic, replayable growth.

---

## 2. Acceptance Criteria

**Reproduction: Kansal–Torquato (published number)**

- [x] **AC-1** (E.1): The KT automaton is rebuilt from [E02] §3 on its own variable-density lattice. *Evidence:* `E_classical_growth/repro/kt_lattice.py:34` (RSA), `:63` (Delaunay CSR), `E_classical_growth/src/kt.py:65` (KTGraph), `:100` (search within dp), `:121` (step).
  → `E_classical_growth/repro/kt_lattice.py` places sites by random sequential addition with mean spacing `z(r) = r^{2/3}/6` mm (eq. 2) out to `R_lattice = 50 mm`. It builds neighbours from `scipy.spatial.Delaunay` (3-D) as a CSR adjacency. `E_classical_growth/src/kt.py` implements the algorithm exactly as listed in [E02] §3: initial proliferative ball of radius 0.1 mm; healthy and necrotic cells inert; dormant cells deeper than `d_n` below the proliferative rim turn necrotic; proliferative cells divide with `p_d = p0(1 − r/Rmax)` into the nearest free site within `d_p` (BFS over the adjacency), else turn dormant. Rt and Rn are averaged over edge cells (eq. 3). One step = 1 day.
- [x] **AC-2** (E.2): Table 2 is reproduced with the paper's parameters `p0 = 0.192, a = 0.42 mm^{1/3}, b = 0.11 mm^{1/3}, Rmax = 37.5 mm`. *Evidence:* `E_classical_growth/repro/kt_table2.py:38` (run), `:35` (tolerance); run `20261028-191231-kt-table2`: 3 of 4 stages within tolerance, 0.5 mm off (explained in dossier).
  → `python -m E_classical_growth.repro.kt_table2` runs to Rt = 25 mm (or day 600), records Rt, growth fraction, necrotic fraction and volumetric doubling time per day, and prints a table in Table 2's layout (paper Data | paper Sim | ours) at Rt = 0.5, 5, 18.5 and 25 mm. **Agreement** (proposed, Q3): growth and necrotic fractions within ±10 percentage points of paper Sim, doubling time within ±35 %, day of reaching each radius within ±25 %. The run writes `kt_table2.json` to its run directory.
- [x] **AC-3** (E.3): KT figures exported. *Evidence:* `E_classical_growth/repro/kt_table2.py:89`; `E_classical_growth/figures/kt_table2.png`, `kt_growth_curve.png`, `kt_cross_sections.png`.
  → `E_classical_growth/figures/kt_table2.png` (ours vs paper Sim vs Data, four panels), `kt_growth_curve.png` (radius and volume vs day, the Fig. 4 analogue), `kt_cross_sections.png` (central slices at the four stages, red proliferating / yellow dormant / black necrotic, the Fig. 3 analogue).

**Reproduction: Pixel2Cancer (published behaviour)**

- [x] **AC-4** (E.4): The Pixel2Cancer rules are rebuilt as a faithful CPU port. *Evidence:* `E_classical_growth/src/p2c.py:51` (P2C), `:87` (R1/R2), `:119` (R3), `:56`/`:67` (`faithful_int_cast`).
  → `E_classical_growth/src/p2c.py`:
  - population map `int8` ∈ {−1 dead, 0, 1…10};
  - 3×3×3 kernel;
  - R1: `0 < s < 10` grows +1 with probability;
  - R2: a cell with `s > 0` increments one random neighbour; a level-0 barrier is entered only once its pressure counter reaches `threshold`;
  - R3: cells at 10 fully surrounded by 10s die with probability, once the tumor is larger than 2 cm, then death spreads.

  The 4-level quantification follows [E01] §2.2 and the open Apache-2.0 reference code (`MrGiovanni/Pixel2Cancer`, read only, licence noted in the dossier). Two documented differences from the reference: (i) the CUDA `curand(clock64())` stream becomes a seeded `numpy.random.Generator`, so runs are deterministic; (ii) the parallel race-y update becomes a synchronous vectorized step with random conflict resolution.
- [x] **AC-5** (E.5): The Pixel2Cancer behaviours are reproduced on its liver setting. *Evidence:* `E_classical_growth/repro/p2c_behaviour.py:58`/`:82`/`:106`/`:131` (B1–B4); run `20261029-053311-p2c-behaviour`: all PASS.
  → `python -m E_classical_growth.repro.p2c_behaviour` runs on a synthetic liver phantom: an ellipsoid at liver HU with tubular vessels above `Organ_HU['liver'] = [100, 160]`, `steps ∈ [5, 150]`, `threshold = 10`. It reports four measured checks:
  - **B1**: vessel voxels stay uninvaded until their pressure reaches the threshold, and the tumor wraps around the vessel;
  - **B2**: growth flattens against the organ boundary;
  - **B3**: dead cells appear only after the 2 cm size rule triggers;
  - **B4**: the tumor diameter distribution over random `steps ∈ [5, 150]`.

  Each check gets a PASS/FAIL line and a number. Figure: `E_classical_growth/figures/p2c_behaviour.png`. If the developer provides a real liver CT + mask (Q2), the same script accepts `--ct/--mask`.

**Adaptation: lung engine**

- [x] **AC-6** (E.6): Inputs are read only through contracts, with stub defaults. *Evidence:* `E_classical_growth/src/io_contracts.py:24` (DEFAULTS), `:46` (validate_inputs), `E_classical_growth/src/grow.py:62` (validation before use), site lookup `E_classical_growth/src/grow.py:70`.
  → `python -m E_classical_growth.src.grow` takes `--masks`, `--sites`, `--draw`, `--certificate`, `--seed-shape`, defaulting to the files under `shared/stubs/`. Each input is validated with `shared.validate.validate_file` before use. The site is the draw's `site_id`, and a mismatch is an error.
- [x] **AC-7** (E.7): A certificate that fails is refused, with no fallback. *Evidence:* `E_classical_growth/src/io_contracts.py:39`, `E_classical_growth/src/grow.py:54`–`:60`; verified exit 2, run `20261029-052646-grow-rejected`.
  → If `certificate.status != "pass"` or `extracted_seed_hex` is null, `grow` writes a run record whose notes say `draw rejected: certificate status=<status>` and no trajectory, then exits with code 2. There is no retry and no alternate seed (epic §5, resolved decision 6).
- [x] **AC-8** (E.8): The lattice is a 3-D sub-voxel grid around the site. *Evidence:* `E_classical_growth/src/lattice.py:61` (resample + barriers), `:71`–`:72` (hard/soft), `:86` (uniform-HU note).
  → `E_classical_growth/src/lattice.py`:
  - builds an isotropic lattice (default 0.5 mm, Q4), axis-aligned with LPS, centred on `center_mm_lps`, with half-width `size_mm/2 + follow-up margin + 5 mm`;
  - resamples `lungs`, `lobes`, `vessels`, `airway` (nearest neighbour) and `host_ct` (linear) from the host grid with SimpleITK;
  - derives the lung environment:
    - **hard barrier**: outside the lung (pleura, chest wall, mediastinum) and lobe-label change (fissure);
    - **soft barrier, Pixel2Cancer level 0 with pressure**: vessels and airway;
    - **parenchyma levels 1–4**: lung HU quantified between lung HU bounds (Q5).

    Uniform HU, as in the stub phantom, collapses to one parenchyma level, and this is logged.
  - `origin_mm_lps` = LPS position of lattice index (0, 0, 0) (VOLUMES.md).
- [x] **AC-9** (E.9): Initial state from D's seed shape. *Evidence:* `E_classical_growth/src/lattice.py:90` (place_seed), `E_classical_growth/src/grow.py:95`.
  → `seed_shape.npz` `occupancy` is resampled onto the lattice (nearest neighbour), centred at the site, clipped to non-hard-barrier voxels, and set to state 1 (proliferating). A seed that lands entirely in a barrier is an error. The manifest's `seed_shape_ref` and `upstream` point at the seed-shape file.
- [x] **AC-10** (E.10): A combined KT + Pixel2Cancer step rule on the cubic lattice. *Evidence:* `E_classical_growth/src/engine.py:117` (step), `:129` (pressure), division loop below it; jittered lattice (deviation, see §9).
  → `E_classical_growth/src/engine.py` runs, per day:
  1. KT layer update (`d_p`, `d_n` from the current Rt, Rt measured as mean edge-cell distance from the seed centroid);
  2. proliferative cells, visited in a seeded random order, divide into a free parenchyma voxel within `d_p` (26-neighbourhood BFS, Poleszczuk–Enderling active-cell list);
  3. a soft-barrier target accumulates pressure and is entered only at `threshold` (Pixel2Cancer R2), so juxtavascular tumors wrap and then engulf vessels;
  4. a hard-barrier target is never entered, so juxtapleural tumors flatten against the pleura or fissure.

  The output states are 0 host, 1 proliferating, 2 dormant, 3 necrotic. No reserved codes are used.
- [x] **AC-11** (E.11): Lung parameters per tumor type, all cited. *Evidence:* `E_classical_growth/src/params_lung.json`, `E_classical_growth/repro/calibrate_lung.py:79` (secant), `:85` (write-back); run `20261029-052808-calibrate-lung`.
  → `E_classical_growth/src/params_lung.json` holds one parameter set per `tumor_draw.type` (`solid | part-solid | ground-glass`): `p0`, `a`, `b`, `Rmax_mm`, `vessel_threshold`, `parenchyma_rates[1..4]`, each with a source string.
  - `p0` is calibrated by `python -m E_classical_growth.repro.calibrate_lung` so that the simulated volumetric doubling time at the drawn size falls in the published lung range per type (Q6; proposed anchors: Hasegawa 2000 means of solid ≈ 149 d, part-solid ≈ 457 d, ground-glass ≈ 813 d, marked *(verify)*).
  - `a`, `b` are set so that necrosis is negligible below 20 mm diameter, matching Pixel2Cancer's 2 cm death rule (documented as our assumption).

  The calibration table is written to `E_classical_growth/figures/lung_calibration.png` and into the dossier.
- [x] **AC-12** (E.12): Baseline and follow-up snapshots. *Evidence:* `E_classical_growth/src/engine.py:166` (run), `:174` (baseline), `:177` (follow-up); `--max-days 10` → exit 3.
  → The **baseline** is the first day the equivalent-sphere diameter of the tumor (states 1–3) reaches `tumor_draw.size_mm`. The **follow-up** is baseline + `--follow-up-days` (default 90). Both are written; `--every N` adds `role: "other"` snapshots. Snapshot `day` is counted from the seed. Growth stops at `--max-days` (default 3000); if the baseline size is never reached, the run fails with a logged reason (no partial trajectory).
- [x] **AC-13** (E.13): A contract-valid, provenance-complete output. *Evidence:* `E_classical_growth/src/io_contracts.py:97` (write_trajectory), `:119` (stub), `E_classical_growth/src/grow.py:102` (rng label), `:112` (validate output).
  → `grow` writes `E_classical_growth/runs/<run_id>/growth_trajectory/{growth_trajectory.json, step_<NNNN>.npz}` via `shared.volumes.save_npz` (`state` uint8 (z, y, x) + `spacing_mm_xyz` float64). The manifest carries:
  - `seed_hex` = certificate seed;
  - `site_id`;
  - `upstream[]` = masks, sites, draw, certificate, seed shape (path + sha256);
  - `produced_by.letter = "E"`;
  - `stub` = true if any upstream is a stub.

  Every PRNG comes from `shared.seedhash.rng(seed_hex, "E/<component>/<draw_id>/<site_id>")`. The run directory comes from `shared.runrecord.start_run("E_classical_growth", tag, seed_hex=…)`, with `add_input`/`add_output` for every file. `python -m shared.validate <manifest>` reports OK. A non-contract sidecar `growth_summary.json` (per day: Rt, volume, eq. diameter, layer fractions) sits next to it for figures and H.
- [x] **AC-14** (E.14): Deterministic replay. *Evidence:* verified: two default runs → identical step_*.npz sha256 (runs `20261029-052934`/`-052941-grow-S001`).
  → Two `grow` runs with identical inputs produce byte-identical `step_*.npz` files (equal sha256). Only `run_id`, `created_utc` and the manifest hash differ.
- [x] **AC-15** (E.15): Three placement classes behave differently. *Evidence:* runs `20261029-052830/-052837/-052843`; `E_classical_growth/src/io_contracts.py:76` (sphericity), `E_classical_growth/src/figures.py:36`; S002 vessel entry in `20261029-052850-grow-S002`.
  → Running `grow` for the stub sites S001 (free), S002 (juxtavascular) and S003 (juxtapleural) gives, respectively: a near-spherical tumor (sphericity reported); a tumor in contact with and wrapping the vessel (contact-voxel count > 0, vessel voxels entered only after the threshold); and a tumor with zero voxels outside the lung and a flattened pleural face (reported). Their figures are `E_classical_growth/figures/lung_S001.png`, `lung_S002.png` and `lung_S003.png` (orthogonal central slices of baseline and follow-up, the 2-D export) and `lung_growth_curves.png`.

**Documentation and status**

- [x] **AC-16** (E.16): Dossiers complete. *Evidence:* `E_classical_growth/dossiers/11-pixel2cancer.md`, `E_classical_growth/dossiers/12-hpc-cellular-automaton.md`.
  → `dossiers/11-pixel2cancer.md` has every fixed section filled (concept, equations in Unicode or `text` blocks, parameter table with sources, claimed results, our reproduction numbers + figures + run ids, lung adaptation, verdict, reuse notes for F/H). `dossiers/12-hpc-cellular-automaton.md` has concept, data structures, what we used, and verdict "dissected; reproduction not needed at nodule scale (≤ 10^6 lattice cells)".
- [x] **AC-17** (E.17): README complete. *Evidence:* `E_classical_growth/README.md` (all sections, change requests 1–4).
  → All fixed sections of `E_classical_growth/README.md` are filled: exact commands, the Table 2 comparison, behaviour checks, claim note ("classical stage; the certified seed gives provenance only, never realism"), and **Contract change requests** (at minimum the `growth_summary` and `population` notes in §5).
- [x] **AC-18** (E.18): Status updated. *Evidence:* `E_classical_growth/status.json` (#11 adapted, #12 dissected); `python -m shared.validate --status` OK.
  → `status.json`: #11 `adapted` with `reproduced` = a short KT Table-2 summary string and `figures` listed; #12 `dissected`. `python -m shared.validate --status` passes. `python -m shared.site.build` renders E locally for preview, and its output is **not** committed.

---

## 3. Out of Scope (Postponed)

- Cell state → HU mapping, texture, partial volume, ground-glass α-blend, margin/shape deformation (lobulated, spiculated), mass effect, insertion into CT → **F** (#13, #14). E only records the draw's `type`/`margin`; `type` selects growth parameters, and `margin` is not used in E (Q7).
- Real LIDC host scans, real lung/vessel masks → **A**; E runs on `shared/stubs/anatomy_masks` until **INT**.
- Real certified seed → **C**; real QCA / lineage seed shape → **D**; both stubbed until **INT**.
- Validation against LIDC follow-up pairs, PyRadiomics, cohort statistics → **H**.
- Signing the trajectory / receipts → **G**.
- Any contract change (`growth_summary`, `population` key, `draw_id` in the manifest) → recorded as a change request, applied in **INT**.
- Large cohorts / millions of cells (#12 reproduction, C++/GPU kernels) → future work; not needed at nodule scale.
- Running the original Pixel2Cancer CUDA code as a differential reference → not possible here (no GPU/torch); noted in the dossier.
- Committing `index.html` / `site/` → **INT**.

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Language / libs | NumPy + SciPy (`scipy.spatial.Delaunay`, `scipy.sparse`, `scipy.ndimage`), SimpleITK for resampling, scikit-image (`measure.marching_cubes` for sphericity), matplotlib (Agg) for figures. No new installs. |
| KT repro lattice | Variable-density point set via random sequential addition (eq. 2, `z = r^{2/3}/6` mm) + 3-D Delaunay → CSR adjacency. Site count is reported; it is expected to be of order 10^5 to 10^6, and the paper reports 1.5 × 10^6. Fallback if RAM > 20 GB: shell-wise generation with a documented coarsening factor (Q3). |
| Lung lattice | Uniform isotropic cubic grid (default 0.5 mm), LPS-aligned, cropped around the site; 26-neighbourhood (Pixel2Cancer's 3×3×3 kernel). Random-order updates to reduce lattice anisotropy; sphericity reported. |
| I/O | Only `shared.volumes` (`read_volume`, `save_npz`, `load_npz`), `shared.validate`, `shared.seedhash`, `shared.runrecord`. No direct nibabel/np.save. |
| Randomness | `shared.seedhash.rng(seed_hex, label)` per component (`E/kt`, `E/p2c`, `E/engine/order`, `E/engine/divide`, `E/engine/death`). The repro scripts, which have no certificate, use the stub certificate seed and say so in the output. |
| Time | 1 step = 1 day (KT). Doubling time = `ln 2 · Δt / ln(V(t+Δt)/V(t))` over a sliding 10-day window. |
| Parameters | `params_lung.json` (versioned, hashed into the run record through code_hash, since it sits in the letter folder); KT and Pixel2Cancer published parameters are constants in `src/kt.py` / `src/p2c.py` with source comments. |
| CLI | `argparse` modules: `E_classical_growth.src.grow`, `E_classical_growth.repro.kt_table2`, `E_classical_growth.repro.p2c_behaviour`, `E_classical_growth.repro.calibrate_lung`, `E_classical_growth.src.figures`. |
| Performance budget | `kt_table2` ≤ 30 min on 8 cores / 31 GB; one lung `grow` ≤ 2 min at 0.5 mm. Only active (proliferative) cells are iterated (Poleszczuk–Enderling active list); the domain is the crop box. |

**Conventions & Notes:**
* Adopt the epic §3 decisions without change: 3-D only, file contracts only, seed chain, run logging, privacy-by-construction (host HU is read only to place and to quantify the environment; no patient voxel becomes tumor appearance).
* Pixel2Cancer code (Apache-2.0) may be **read** for parameter values and rule details; the rebuild is our own code, with the licence and the file/line provenance cited in the dossier. Nothing is vendored.
* `E_classical_growth/runs/` is gitignored; figures, README, dossiers, code and `params_lung.json` are committed.
* Honesty: E is classical. The README and dossier state that the certified seed is provenance only and does **not** make growth more realistic ([E05]-style argument; epic §3 honesty gates).
* Not in the epic, decided here (note for the epic): (i) the combined KT-layers + Pixel2Cancer-barrier rule (AC-10); (ii) the hard (pleura/fissure) vs soft (vessel/airway) barrier split; (iii) the baseline = drawn size, follow-up = +90 d snapshot policy; (iv) the non-contract `growth_summary.json` sidecar.

---

## 5. Data Model (Additions/Modifications)

No contract is changed (all of `shared/` is frozen). E produces the existing `growth_trajectory` contract and adds two letter-local files.

```text
[Existing contract - produced, unchanged]
growth_trajectory  (shared/contracts/growth_trajectory.schema.json v1.0.0)
  envelope: produced_by.letter = "E", tool = "E_classical_growth.src.grow", stub = any(upstream.stub)
  upstream[]       anatomy_masks, site_candidates, tumor_draw, certificate, seed_shape  (path + sha256)
  site_id          = tumor_draw.site_id
  seed_hex         = certificate.extracted_seed_hex
  seed_shape_ref   {path, sha256} of seed_shape.json
  origin_mm_lps    LPS of lattice index (0,0,0)
  spacing_mm_xyz   lattice spacing (default [0.5, 0.5, 0.5])
  state_labels     {"0":"host","1":"proliferating","2":"dormant","3":"necrotic"}
  snapshots[]      {step, day, role: baseline | follow-up | other, npz {path, sha256}}

step_<NNNN>.npz
  state            uint8 (z,y,x)  0..3
  spacing_mm_xyz   float64 (3,)
  (no extra keys in v1; a Pixel2Cancer `population` key is a change request, see below)

[New, letter-local, not a contract]
E_classical_growth/src/params_lung.json
  version          str
  types            {solid | part-solid | ground-glass: {p0, a_mm13, b_mm13, Rmax_mm,
                    vessel_threshold, parenchyma_rates[4], vdt_target_days, sources[]}}
  lung_hu_bounds   [lo, hi]   parenchyma quantification range
  lattice_mm       0.5

runs/<run_id>/growth_trajectory/growth_summary.json   (sidecar for figures + H)
  per_day[]        {day, Rt_mm, volume_mm3, eq_diameter_mm, f_prolif, f_dormant, f_necrotic,
                    vdt_days, barrier_contacts, barrier_entries}
  checks           {sphericity, voxels_outside_lung, vessel_entered_day | null}

runs/<run_id>/kt_table2.json   (repro output)
  rows[]           {radius_mm, day, n_sites, growth_fraction, necrotic_fraction, vdt_days,
                    paper_sim{...}, paper_data{...}, within_tolerance}
```

**Contract change requests (to record in the README, applied in INT):**
1. `growth_trajectory.snapshots[]`: optional `summary {eq_diameter_mm, volume_mm3, f_prolif, f_dormant, f_necrotic}`, so F/H need not read the sidecar.
2. `step_NNNN.npz`: optional `population` uint8 (0–10) key carrying Pixel2Cancer's partial-population field, which F could use for blurry boundaries ([E01] §2.3).
3. `growth_trajectory`: optional `draw_id` (today only reachable through `upstream`).

---

## 6. File Plan (Concrete Changes)

All paths are relative to `RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`.

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `E_classical_growth/src/kt.py` | Kansal–Torquato rules on a generic CSR-adjacency lattice (used by repro) plus the layer-update function reused by `engine.py`; published constants with [E02] citations. |
| New | `E_classical_growth/src/p2c.py` | Pixel2Cancer port: `quantify(hu, mask, lo, hi)` → levels 0–4; `step(pop, levels, pressure, rng, threshold)` R1/R2/R3; death-spread; seeded, vectorized. |
| New | `E_classical_growth/src/lattice.py` | Crop box around a site, SimpleITK resampling of host masks/HU onto the sub-voxel grid, hard/soft barrier and parenchyma-level maps, seed-shape placement, `origin_mm_lps`. |
| New | `E_classical_growth/src/engine.py` | Combined lung rule (AC-10): daily KT layer update + active-cell division with Pixel2Cancer barrier pressure; Rt/volume/fraction bookkeeping; snapshot policy. |
| New | `E_classical_growth/src/io_contracts.py` | Load + validate the five inputs, certificate pass check (AC-7), write the `growth_trajectory` manifest/NPZ and `growth_summary.json`, run-record wiring. |
| New | `E_classical_growth/src/grow.py` | CLI (`python -m E_classical_growth.src.grow`), stub defaults, `--site-id` override for AC-15, `--follow-up-days`, `--every`, `--max-days`, `--lattice-mm`. |
| New | `E_classical_growth/src/figures.py` | `python -m E_classical_growth.src.figures <run_dir>…`: orthogonal central-slice PNGs (2-D export) and growth curves; shared colour map for states 0–3. |
| New | `E_classical_growth/src/params_lung.json` | Lung parameter sets per tumor type with sources (filled by the calibration). |
| New | `E_classical_growth/repro/kt_lattice.py` | Variable-density RSA point set (eq. 2) + Delaunay CSR adjacency, cached under `E_classical_growth/runs/_cache/`. |
| New | `E_classical_growth/repro/kt_table2.py` | AC-2/AC-3: runs KT, writes `kt_table2.json`, prints the comparison, saves `figures/kt_table2.png`, `kt_growth_curve.png`, `kt_cross_sections.png`. |
| New | `E_classical_growth/repro/p2c_behaviour.py` | AC-5: synthetic liver phantom (or `--ct/--mask`), checks B1–B4, saves `figures/p2c_behaviour.png`. |
| New | `E_classical_growth/repro/calibrate_lung.py` | AC-11: sweeps `p0` per type on a free-site lattice, picks the value that hits the target VDT at the drawn size, writes `params_lung.json` and `figures/lung_calibration.png`. |
| New | `E_classical_growth/figures/kt_table2.png`, `kt_growth_curve.png`, `kt_cross_sections.png`, `p2c_behaviour.png`, `lung_calibration.png`, `lung_S001.png`, `lung_S002.png`, `lung_S003.png`, `lung_growth_curves.png` | Generated by the scripts above and committed; `.gitkeep` stays. |
| Modify | `E_classical_growth/README.md` | Fill every fixed section (AC-17), including commands, Table-2 comparison, behaviour checks, honesty note, contract change requests 1–3. |
| Modify | `E_classical_growth/dossiers/11-pixel2cancer.md` | Full dossier (AC-16) covering both E01 and E02. |
| Modify | `E_classical_growth/dossiers/12-hpc-cellular-automaton.md` | Dissection-only dossier (AC-16). |
| Modify | `E_classical_growth/status.json` | #11 → `adapted` (+ `reproduced`, `figures`, `updated`), #12 → `dissected` (AC-18). |
| Modify | `feature-E-classical-growth.md` | §2 checkboxes and §9 notes during implementation. |

Analogue to mirror: the stub producer `shared/stubs/make_stubs.py` (how a `growth_trajectory` manifest, NPZ and `upstream` refs are written with `shared.volumes` / `shared.seedhash`) and `shared/runrecord.py` (`start_run` → `add_input/add_output` → `finish`).

---

## 7. Manual Verification (No Tests)

All commands run from `RE/` inside the `re-E` worktree.

- [x] **Verify AC-1/AC-2:** `python -m E_classical_growth.repro.kt_table2` → prints the site count and a 4-row table; every row shows `within_tolerance: true` (or the deviation is explained in the dossier). `E_classical_growth/runs/<id>/kt_table2.json` exists.
- [x] **Verify AC-3:** open the three `figures/kt_*.png`: the Gompertz-like radius curve flattens; the cross-sections show a red rim, a yellow shell and a black core at the later stages.
- [x] **Verify AC-4/AC-5:** `python -m E_classical_growth.repro.p2c_behaviour` → B1–B4 PASS lines with numbers. Run it twice: identical numbers. Open `figures/p2c_behaviour.png`: the tumor wraps the vessel and is flattened at the boundary.
- [x] **Verify AC-6/AC-13:** `python -m E_classical_growth.src.grow` (all stub defaults) → prints the run dir; then `python -m shared.validate E_classical_growth/runs/<id>/growth_trajectory/growth_trajectory.json` → OK. Inspect the manifest: five `upstream` entries, `stub: true`, `seed_hex` equal to the stub certificate's `extracted_seed_hex`. `run.json` lists inputs and outputs.
- [x] **Verify AC-7:** copy `shared/stubs/certificate/certificate.json` to `E_classical_growth/runs/manual/cert_fail.json`, set `"status": "fail"` and `"extracted_seed_hex": null`, then `python -m E_classical_growth.src.grow --certificate E_classical_growth/runs/manual/cert_fail.json; echo $?` → `2`, the run notes say `draw rejected: certificate status=fail`, and there is no `growth_trajectory/` directory.
- [x] **Verify AC-8/AC-9:** `grow` log lines report the lattice shape, spacing 0.5 mm, origin, barrier voxel counts and "uniform HU → 1 parenchyma level" for the stub. Step 0's state-1 voxel count ≈ seed-shape `n_cells` scaled by the volume ratio (printed).
- [x] **Verify AC-10/AC-15:** `grow --site-id S001`, `--site-id S002`, `--site-id S003` (with a matching local draw copy if needed, see Q8), then `python -m E_classical_growth.src.figures <three run dirs>`:
  - S001: sphericity ≥ 0.85;
  - S002: `barrier_contacts > 0`, `vessel_entered_day` ≥ the first contact day + threshold;
  - S003: `voxels_outside_lung = 0`.

  Inspect `lung_S00*.png`: all three states are visible at follow-up only if the size exceeds 20 mm; otherwise proliferating + dormant only.
- [x] **Verify AC-11:** `python -m E_classical_growth.repro.calibrate_lung` → per-type table of target vs achieved VDT within ±15 %; `params_lung.json` updated with sources; `figures/lung_calibration.png` exists.
- [x] **Verify AC-12:** in the manifest, the baseline snapshot's `eq_diameter_mm` (sidecar) is within one lattice step of `tumor_draw.size_mm` (8 mm for the stub); follow-up day = baseline day + 90; `--max-days 10` → logged failure, no trajectory.
- [x] **Verify AC-14:** run `grow` twice with defaults; `sha256sum E_classical_growth/runs/<a>/growth_trajectory/step_*.npz E_classical_growth/runs/<b>/growth_trajectory/step_*.npz` → pairwise identical.
- [x] **Verify AC-16/AC-17:** read both dossiers and the README: no `_Pending_` / `_Not yet …_` placeholders remain; contract change requests 1–3 are listed.
- [x] **Verify AC-18:** `python -m shared.validate --status` → OK; `python -m shared.site.build` → open `site/E_classical_growth/index.html` locally and see #11 `adapted`, #12 `dissected`; then `git status` shows no staged `index.html`/`site/` changes (discard them before committing).
- [x] **Edge case:** a draw whose `site_id` is not in `sites.json` → clear error, exit ≠ 0, no output.
- [x] **Edge case:** `git status` shows changes only inside `E_classical_growth/` and this plan.

---

## 8. Open Questions

- [x] **Q1 (#11 reproduction target):** Pixel2Cancer publishes no growth number, only DSC and a reader study we cannot rerun. Is "KT Table 2 = the reproduced number, Pixel2Cancer = reproduced behaviours B1–B4" acceptable as #11's "reproduced" state? *Resolved (accepted default):* yes; the dossier states this plainly.
- [x] **Q2 (organ for Pixel2Cancer behaviour):** there is no liver CT on this machine, and MSD Task03 / LiTS are multi-GB downloads. *Resolved (accepted default):* a synthetic liver phantom with Pixel2Cancer's liver hyper-parameters is the default; `--ct/--mask` stays available if you later drop one public liver case (e.g. one MSD Task03 volume, CC BY-SA 4.0) into `E_classical_growth/runs/data/`.
- [x] **Q3 (Table 2 tolerance + lattice size):** *Resolved (accepted default):* fractions ±10 percentage points, doubling time ±35 %, day-to-radius ±25 %; a full eq.-2 lattice if it fits in ~20 GB RAM, else shell-wise coarsening with the factor reported.
- [x] **Q4 (lattice resolution):** *Resolved (accepted default):* 0.5 mm isotropic (matches the stub trajectory; a 30 mm nodule ≈ 60³ cells). `--lattice-mm` makes it configurable.
- [x] **Q5 (lung HU quantification bounds):** *Resolved (accepted default):* parenchyma levels 1–4 from host HU in [−950, −600]; voxels above −600 that are not vessel/airway become level 4 (dense, slow to invade). Revisit in INT with real LIDC scans.
- [x] **Q6 (lung growth calibration source):** no lung doubling-time paper is in `../papers/`. *Resolved (accepted default):* calibrate `p0` to Hasegawa et al., Br J Radiol 2000 mean VDTs (solid ≈ 149 d, part-solid ≈ 457 d, ground-glass ≈ 813 d), marked *(verify)* until you add the PDF; `a, b` set so necrosis appears only above 20 mm.
- [x] **Q7 (margin):** *Resolved (accepted default):* E ignores `tumor_draw.margin` (lobulated/spiculated shape is F's #13 shape deformation); E's tumor is the smooth, anatomy-constrained body. Alternative: lobulated = low-frequency heterogeneous `p0`, spiculated = Pixel2Cancer-R2 invasive strands, both in E.
- [x] **Q8 (AC-15 with one stub draw):** the stub `tumor_draw` only targets S001. *Resolved (accepted default):* `grow --site-id` overrides the draw's site for verification runs and marks the manifest `stub: true` with a log note; it never writes into `shared/stubs/`.
- [x] **Q9 (#12 final state):** *Resolved (accepted default):* `dissected` (not terminal; cohort-scale work may advance it later), rather than `rejected`.
- [x] **Q10 (`population` key):** *Resolved (accepted default):* do **not** write the extra NPZ key in v1 (keep it strictly to VOLUMES.md); file it as change request 2 for INT.

---

## 9. Post-Implementation Notes

**Built (2026-10-29, worktree `../qp-re-E`, branch `re-E`):**
- **Kansal–Torquato rebuild**: `src/kt.py`, `repro/kt_lattice.py`, `repro/kt_table2.py`.
- **Pixel2Cancer CPU port**: `src/p2c.py`, `repro/p2c_behaviour.py`.
- **Lung engine**: `src/lattice.py`, `src/engine.py`, `src/io_contracts.py`, `src/grow.py`, `src/params_lung.json`, `repro/calibrate_lung.py`, `src/figures.py`.
- **Docs and status**: README, both dossiers, `status.json`.
- **Figures**: 12 PNGs in `E_classical_growth/figures/`.

All files are inside `E_classical_growth/` plus this plan. Nothing in `shared/` or another letter was touched. The site build was run for preview only and reverted.

**Results:**
- **KT Table 2.** Three of four stages are within tolerance at the paper's site count (5 / 18.5 / 25 mm). The 0.5 mm spheroid stage is off: necrotic fraction 0.08 vs 0.38, day 61 vs 87. The literal eq. 2 lattice fails at every stage.
- **Pixel2Cancer B1–B4.** All pass.
- **Calibration.** Within ±4 % of the VDT targets.
- **Placement classes.** All three behave as intended; S002 needs a 600-day follow-up to show the vessel being entered.

**Deviations from the plan (all logged in the dossier):**
1. **KT lattice (AC-1).** The literal z = r^(2/3)/6 law gives only ~5 × 10⁴ sites to 50 mm, against the 1.5 × 10⁶ the paper reports, and it fails Table 2. I added `--spacing-scale` (default 0.29, which gives 1.85 × 10⁶ sites) and reduced the lattice radius to 30 mm, since the tumor stops at 25 mm. The literal run is kept as `*_k1.png` for comparison. The RSA processes radial shells in order, not one global random order.
2. **Lung division ordering (AC-10).** Plain nearest-first on a cubic lattice grew an octahedron, and random order grew a rough Eden cluster. Both gave raw sphericity ≈ 0.53–0.74. The engine now uses a **jittered cubic lattice**: a fixed random sub-voxel site offset of ±0.4 Δ per voxel, the cubic analogue of KT's Voronoi lattice, with nearest-first by jittered distance.
3. **Sphericity check (AC-15).** The raw marching-cubes sphericity stays ≈ 0.72 because of 0.5 mm surface roughness. The S001 check therefore uses sphericity after a 0.5 mm Gaussian smooth (0.89) plus the inertia ratio (0.87). Both raw and smoothed values are reported in `growth_summary.json`.
4. **Vessel pressure (AC-10).** Pressure from division searches alone was too rare: the vessel was not entered within 750 days of contact. Pressure is now Pixel2Cancer-style: every dormant (crowded) cell pushes one random kernel neighbour per day. With `vessel_threshold` = 30, S002 makes contact on day 278 and enters the vessel on day 629, in the 600-day run.
5. **`params_lung.json` provenance.** `shared.seedhash.code_hash` covers only `.py` files, so the parameter file is recorded as a run input (`contract: "params_lung"`) instead of through the code hash.
6. **Extra sidecar.** `environment.npz` (barrier and level maps for the figures) sits next to `growth_summary.json`. Neither is a contract.
7. **PRNG label.** The engine uses one stream, `E/engine/<draw_id>/<site_id>`, rather than separate per-component labels.

**Follow-ups:**
- Add the Hasegawa 2000 PDF and verify the 149 / 457 / 813 d targets. If they change, run `calibrate_lung` again.
- In INT, check `lung_hu_bounds` (Q5) and `vessel_threshold` against real LIDC scans. On the stub, HU partial volume near barriers puts levels 2–4 in a thin halo around vessels and the pleura; that is expected.
- The KT run `20261028-191231` was recorded before the lung-engine files existed, so its `code_hash` differs from the final tree. `kt.py` and `kt_lattice.py` are unchanged since then; rerun it (~15 min) if a fully matching hash is wanted.
- Contract change requests 1–4 are in the README for INT.
- Merge `re-E` to `main` when ready (wave 1).
