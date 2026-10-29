# Feature A — Placement: anatomy-informed site + context vector

**Epic:** [epic-reverse-engineering.md](epic-reverse-engineering.md) (Approved, 2026-10-28)
**Feature ID:** A (target #18)
**Author:** Claude (Opus)
**Date:** 2026-10-28
**Status:** Approved (by developer, 2026-10-28) — IN PROGRESS, paused 2026-10-29 (see §9 checkpoint; Q2 amended: 20 scans, parallel)

> **Constraints.**
> - Python 3 + NumPy/SciPy/scikit-image + SimpleITK, with lungmask, TotalSegmentator and pylidc on LIDC-IDRI.
> - Classical stage: no Qiskit, no quantum claim, `sim: null` in run records.
> - Fully 3-D. 2-D slices are figures only.
> - Writes only inside `A_placement/` and this file. `shared/` is frozen and the contracts are v1.0.0.
> - Built in worktree `re-A`.
> - No automated tests; manual verification plus the paper reproduction only.

---

## 1. Why (Step Goal)

**Before.** `A_placement/` is a W skeleton: an empty `src/` and `repro/`, a template README, dossier `18-syn-lungs-placement.md` in state `listed`, and `status.json` in state `listed`. Every downstream letter (B, E, F) runs against `shared/stubs/site_candidates/sites.json`. That stub holds three hand-placed sites on a geometric phantom, classified by a placeholder 5 mm rule that has no published basis. No real CT, no real anatomy masks and no evidence-based placement classes exist yet.

**After.**
- **Masks:** for any LIDC-IDRI host scan, A produces contract-valid 3-D `anatomy_masks` (host CT, lungs, lobes, vessels, airway, body). The masks come from lungmask and TotalSegmentator, on the host's own grid.
- **Sites:** A produces a contract-valid `site_candidates` (`sites.json`). It holds candidate tumor sites in all three placement classes (free / juxtavascular / juxtapleural), each with a full context vector. This is the vector B maps into the circuit: lobe, pleura, vessel and airway distance, vessel density and local HU.
- **Class rule:** the placement-class rule is published, not invented. It is re-implemented from Ambrosini [F01]: free means no contact; vascularized means sharing voxels with a large vessel at a bifurcation; juxtapleural means merged with the lung contour. Ambrosini cites Kostis's 200-nodule class proportions.
- **Reproduction:** the rule is **reproduced** by classifying LIDC consensus nodules and comparing the resulting class proportions with Kostis's (≈ ½ vascularized, ≈ ⅓ well-circumscribed, ≈ ¼ juxtapleural).
- **SYN-LUNGS [A01]:** it is dissected honestly. Its PDF contains no placement rules or thresholds, which the dossier records. A01 contributes the size range and context only.
- **Status:** the README, dossier and `status.json` move target #18 to `adapted`. It becomes `integrated` in INT.

---

## 2. Acceptance Criteria

- [ ] **AC-1** (A.1): A dedicated, reproducible environment runs A.
  → `A_placement/environment.yml` creates a conda env `qp-re-a` (Python 3.11) with:
    - CPU torch, `lungmask`, `TotalSegmentator`, `pylidc`, `pydicom`, `tcia_utils`;
    - `SimpleITK`, `scipy`, `scikit-image`, `numpy`, `jsonschema`, `matplotlib`.

  Running `python -m shared.validate --stubs` succeeds inside it, which proves `shared/` works unchanged in the new env. The README "How to run" section documents creating the env and the `~/.pylidcrc` setup.
- [ ] **AC-2** (A.2): A downloads a LIDC-IDRI subset reproducibly, outside git.
  → `A_placement/src/lidc_fetch.py` downloads the CT series of a given patient list via `tcia_utils` into `$LIDC_ROOT` (default `~/data/LIDC-IDRI`, outside the repo) and writes `~/.pylidcrc`.
  The patient list is `A_placement/repro/lidc_subset.txt` (committed). It is selected deterministically by `--select N`: the first N patients in ID order with slice thickness ≤ 2.5 mm and ≥ 1 nodule annotated by ≥ 3 readers.
  The download is idempotent: patients already present are skipped.
- [ ] **AC-3** (A.3): Host CT conversion lands on the contract grid.
  → `A_placement/src/lidc_io.py::load_host(patient_id)` reads the DICOM series with SimpleITK `ImageSeriesReader`. It writes `host_ct.nii.gz` through `shared.volumes.write_volume`: LPS, identity direction, `int16` HU clipped to [−1024, 3071], native spacing, **no resampling**.
  `nodule_masks(patient_id, grid)` turns each pylidc consensus nodule (`cluster_annotations()`, `consensus(clevel=0.5)`) into a `(z,y,x)` mask on that exact grid. The pylidc `(i,j,k)` → `(z,y,x)` mapping is verified as described in §7.
- [ ] **AC-4** (A.4): Anatomy masks are generated and contract-valid.
  → `A_placement/src/segment.py::segment(host_ct_path, out_dir)` produces six masks on the host grid:

  | Mask | Source | Values |
  |---|---|---|
  | `lungs` | lungmask `R231` | 1 = right, 2 = left |
  | `lobes` | lungmask `LTRCLobes` | 1..5 in contract order LUL, LLL, RUL, RML, RLL |
  | `vessels` | TotalSegmentator task `lung_vessels`, class `lung_vessels` | binary |
  | `airway` | TotalSegmentator task `lung_vessels`, class `lung_trachea_bronchia` | binary |
  | `body` | HU > −500, largest connected component, holes filled | binary |
  | `host_ct` | copied from AC-3 | HU |

  It writes `anatomy_masks.json` with `produced_by.letter="A"`, an `upstream[]` entry and `file_ref` sha256 values. The file passes `python -m shared.validate <dir>/anatomy_masks.json`, which covers the schema, label sets, LPS orientation and same grid.
- [ ] **AC-5** (A.5): Known LIDC nodules are excluded from anatomy-driven analysis.
  → All consensus-nodule voxels (dilated by 2 voxels) are removed from `vessels`, so TotalSegmentator cannot count a nodule as vessel. They are also stored as an exclusion zone, so no candidate site lands on or within `2 × nominal_radius` of an existing nodule.
- [ ] **AC-6** (A.6): The context vector is computed per voxel and per site from the masks.
  → `A_placement/src/context.py` computes these fields with `scipy.ndimage.distance_transform_edt(sampling=spacing_zyx)`:
    - `dist_pleura_mm`: EDT inside `lungs>0` to the lung boundary.
    - `dist_vessel_mm`: EDT to `vessels`.
    - `dist_airway_mm`: EDT to `airway`.
    - `lung` and `lobe`: label lookup at the site center.
    - `local_hu_mean` / `local_hu_std`: computed in a sphere of `nominal_radius_mm` around the center, excluding vessel voxels.
    - `extra.vessel_density`: vessel voxel fraction in a 10 mm sphere.
    - `extra.dist_bifurcation_mm`: EDT to the vessel bifurcation points from AC-7.
    - `extra.nominal_radius_mm`: the radius the class was decided for.

  The `extra` field is the only contract extension point (W Q9 freeze), so no contract change is needed.
- [ ] **AC-7** (A.7): Vessel bifurcations are detected, so juxtavascular sites follow Ambrosini.
  → `A_placement/src/bifurcation.py`:
    1. Skeletonize `vessels` with `skimage.morphology.skeletonize` (3-D).
    2. Mark skeleton voxels with ≥ 3 skeleton neighbours (26-connectivity) as branch points.
    3. Keep only branch points whose local vessel radius (vessel EDT at the skeleton point) is ≥ `min_vessel_radius_mm`, Ambrosini's "large vessel" (default 1.5 mm, Q5).
- [ ] **AC-8** (A.8): The published placement-class rule is implemented once and shared by the reproduction and placement code.
  → `A_placement/src/classes.py` defines two functions.

  `classify_mask(nodule_mask, lungs, vessels, spacing)` labels a real nodule (reproduction):
    - **Contact ring:** dilate the nodule by one voxel (6-connectivity) and remove the nodule itself.
    - **`juxtapleural`:** at least `pleura_contact_frac` of the ring lies outside `lungs ∪ nodule ∪ airway`, i.e. the nodule is merged with the lung contour.
    - **`juxtavascular`:** otherwise, if the ring touches ≥ `vessel_contact_vox` vessel voxels.
    - **`free`:** neither.
    - **Precedence:** pleura before vessel before free (classes are mutually exclusive, as in Kostis).

  `classify_site(dist_pleura, dist_vessel, dist_bif, r)` labels a planned sphere of radius `r` with the same rule:
    - **`juxtapleural`:** `dist_pleura ≤ r`.
    - **`juxtavascular`:** `dist_vessel ≤ r` and `dist_bif ≤ r`.
    - **`free`:** `dist_pleura > r + margin` and `dist_vessel > r + margin`.
    - **No class:** anything in the band in between is ambiguous and never emitted.

  Every threshold is a named, documented parameter in the dossier's Parameters section and is recorded in the run record.
- [ ] **AC-9** (A.9): The reproduction compares LIDC class proportions against Kostis via Ambrosini [F01].
  → `A_placement/repro/class_proportions.py --subset repro/lidc_subset.txt`:
    1. Segments each scan, caching masks under `A_placement/runs/`.
    2. Classifies every consensus nodule (≥ 3 readers, diameter ≥ 3 mm) with `classify_mask`.
    3. Writes `runs/<run_id>/proportions.json`: counts, proportions and Wilson 95 % confidence intervals per class, plus the median nodule radius.
    4. Writes the committed bar chart `A_placement/figures/18-class-proportions.png`: ours with CIs vs Kostis ≈ 0.45 / 0.33 / 0.22.

  **Agreement criterion:** every class is within ±10 percentage points of Kostis, **and** the ordering is vascularized > free > juxtapleural.
  The number is recorded in `status.json.reproduced` as `{quantity: "placement-class proportions (vasc/free/juxtapleural)", paper_value, our_value, agreement, figure}`.
  A miss is reported honestly. It is not tuned away: thresholds may be fixed **before** the run (Q5) and are never fitted to Kostis.
- [ ] **AC-10** (A.10): Candidate sites are sampled per class, deterministically.
  → `A_placement/src/place.py --patient <id> --per-class K --seed-hex <hex>`:
    1. Builds the voxel-wise context fields.
    2. Uses the median LIDC consensus radius from AC-9 (from `--radius-mm`, default taken from the latest `proportions.json`) as `nominal_radius_mm`.
    3. Computes the eligible voxel set per class with `classify_site`, inside `lungs`, outside `airway` and the AC-5 exclusion zone.
    4. Draws K sites per class with `shared.seedhash.rng(seed_hex, "A.place.<class>")`, keeping a minimum spacing of `2 × r` between sites.

  Sites are numbered `S001…` in class order (free, juxtavascular, juxtapleural). If a class has fewer eligible voxels than K, the run emits what exists and states the shortfall in `notes`.
- [ ] **AC-11** (A.11): `sites.json` is contract-valid and traceable.
  → `sites.json` contains:
    - `produced_by.letter="A"` and `stub=false`;
    - `upstream[]` and an `anatomy_masks_ref` holding the sha256 of the `anatomy_masks.json` it was built from;
    - `center_vox_zyx` integers;
    - `center_mm_lps`, computed from the grid's origin and spacing.

  The run is wrapped in `shared.runrecord.start_run("A_placement", "place", seed_hex=…)` with its inputs and outputs, then `finish()`.
  `python -m shared.validate runs/<id>/sites.json runs/<id>/anatomy_masks.json runs/<id>/run.json` passes.
- [ ] **AC-12** (A.12): A 2-D export figure exists for humans, as an export only.
  → `A_placement/src/export_figures.py` renders `A_placement/figures/18-host-sites.png`: three orthogonal slices through one site of each class, with lungs, lobes, vessels and airway as contours and site markers. The figure is generated from the 3-D outputs and never feeds back into the pipeline.
- [ ] **AC-13** (A.13): Documentation and status are complete.
  → `A_placement/dossiers/18-syn-lungs-placement.md` fills all eight sections. Three points are explicit:
    - A01 provides **no** placement rules or thresholds; the class rule comes from F01 / Kostis.
    - The lungmask/TotalSegmentator choices and licences.
    - The verdict is `adapted`.

  `A_placement/README.md` fills the fixed sections: Purpose, Targets, Inputs, Outputs, How to run (env, fetch, segment, reproduce, place), Reproduced result vs paper, Claim level ("classical: no quantum claim"), References and Contract change requests ("none", or what was found).
  `A_placement/status.json`:
    - `state: "adapted"`, with `papers` extended with `"F01"`;
    - `reproduced` filled, `claim_level: null`, `sim_mode: null`;
    - `figures` listing both PNGs.

  `python -m shared.validate --status` passes.

---

## 3. Out of Scope (Postponed)

- **Choosing *the* site for a tumor:** A emits candidates only. **B** (B-2) draws site × phenotype jointly.
- **Class prior as rulebook statistics:** the measured LIDC/Kostis class proportions are reported by A, but encoding them as CPTs belongs to **B**'s `Rulebook`.
- **Swapping the stub sites for real `sites.json` in B/E/F:** that happens in **INT**.
- **Lesion shape, HU and the juxtapleural clip against the lung mask during insertion:** owned by **F** (#14 Ambrosini lesion library, insertion step).
- **Mayo Siemens raw-data hosts and projection-domain work:** owned by **F** (#16).
- **Pleural-tail class (≈ 1 % in Kostis):** not modelled; it is merged into juxtapleural and noted in the dossier.
- **Realism validation of placement vs radiologists:** owned by **H**.
- **Edits to `shared/`, contracts, `about.html`, `index.html` and `site/`:** forbidden for A (epic §3). Any contract need goes to README "Contract change requests" and is applied in **INT**.
- **GPU acceleration and full LIDC (1,018 scans):** subset only (Q2).

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Environment | Separate conda env `qp-re-a`, Python 3.11 (`A_placement/environment.yml`). Base is 3.13, where torch/pylidc wheels are risky. CPU-only torch (no NVIDIA GPU on this machine). |
| LIDC access | `pylidc` (nodule annotations and consensus) + `tcia_utils` (download). Data lives in `$LIDC_ROOT`, default `~/data/LIDC-IDRI`, **outside the repo**. |
| DICOM → volume | SimpleITK `ImageSeriesReader` → `shared.volumes.write_volume` (LPS, int16 HU, native spacing). pydicom is used only by pylidc. |
| Lungs / lobes | `lungmask` `R231` (lungs, left/right split) + `LTRCLobes`. Label order already matches the contract. |
| Vessels / airway | TotalSegmentator task `lung_vessels` (`lung_vessels`, `lung_trachea_bronchia`), CPU. The licence is checked first; fallback is in Q4. |
| Body | HU threshold > −500, largest component, `binary_fill_holes`. Cheap, and avoids an extra model. |
| Distances | `scipy.ndimage.distance_transform_edt` with `sampling=spacing_zyx`, in mm. |
| Bifurcations | `skimage.morphology.skeletonize` (3-D) + 26-neighbour count ≥ 3 + vessel-radius gate. |
| Class rule | Ambrosini [F01] contact definitions, one module (`classes.py`) for the reproduction and for placement. |
| Randomness | `shared.seedhash.rng(seed_hex, "A.place.<class>")`. Default `--seed-hex` is `"00"*32`, recorded in the run record. |
| Run records | `shared.runrecord.start_run("A_placement", tag, seed_hex=…, sim_mode=None)`. Outputs go to `A_placement/runs/<run_id>/` (gitignored). |
| Figures | matplotlib PNGs in `A_placement/figures/` (committed). |

**Conventions and notes:**
- Adopt epic §3 and W verbatim:
  - arrays `(z,y,x)`;
  - JSON vectors `(x,y,z)` unless suffixed `_zyx`;
  - every volume read and written via `shared.volumes`;
  - no implicit resampling;
  - masks `uint8`.
- Commands run from `RE/` as `python -m A_placement.src.<module>` / `python -m A_placement.repro.class_proportions`, mirroring W's `python -m shared.…` style.
- Segmentation outputs are cached per patient under `A_placement/runs/cache/<patient_id>/`, so the reproduction and placement never re-segment. The cache key is the host CT sha256 plus the tool versions.
- Thresholds are fixed in code **before** the reproduction run and documented. They are never fitted to Kostis (honesty: no tuning to the target).
- Licence check is part of the dissect step: lungmask, TotalSegmentator `lung_vessels`, pylidc and LIDC (TCIA). The results are recorded in the dossier.
- **Note for the epic:** SYN-LUNGS [A01] does not supply placement rules. The epic §1 row #18 ("SYN-LUNGS anatomy-informed placement") effectively rests on F01 + Kostis. A records this, and the epic/targets wording can be amended in INT.

---

## 5. Data Model (Additions/Modifications)

No new contracts and no schema changes. A is the first real producer of two frozen v1.0.0 contracts.

```text
[Existing contract — first real producer]
anatomy_masks (anatomy_masks.json, contracts v1.0.0)
  host_scan_id   "LIDC-IDRI-NNNN"
  grid           native host grid (no resampling)
  files          host_ct, lungs, lobes, vessels, airway, body   (all non-null in A)

[Existing contract — first real producer]
site_candidates (sites.json, contracts v1.0.0)
  sites[].context               required fields unchanged
  sites[].context.extra         (existing optional {str: number}) — A fills:
    nominal_radius_mm     float  radius the placement class was decided for
    vessel_density        float  vessel voxel fraction in 10 mm sphere [0,1]
    dist_bifurcation_mm   float  EDT to nearest large-vessel bifurcation

[Existing per-letter file — updated]
A_placement/status.json  target 18
  state       listed → dissected → reproduced → adapted
  papers      + "F01"
  reproduced  {quantity, paper_value, our_value, agreement, figure}

[Local, non-contract artifact]
A_placement/runs/<run_id>/proportions.json
  per class: count, proportion, wilson_ci95; n_nodules; n_scans; median_radius_mm;
  thresholds used; kostis reference values
```

---

## 6. File Plan (Concrete Changes)

All paths are relative to `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`.

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `A_placement/environment.yml` | conda env `qp-re-a`: py3.11, CPU torch, lungmask, TotalSegmentator, pylidc, pydicom, tcia_utils, SimpleITK, scipy, scikit-image, numpy, jsonschema, matplotlib. |
| New | `A_placement/src/lidc_fetch.py` | `--select N` writes `repro/lidc_subset.txt`; `--fetch` downloads the listed series to `$LIDC_ROOT` and writes `~/.pylidcrc`. Idempotent. |
| New | `A_placement/src/lidc_io.py` | `load_host(pid)` → `host_ct.nii.gz` via `shared.volumes`; `nodule_masks(pid, grid)` → consensus masks in `(z,y,x)`; pylidc index mapping. |
| New | `A_placement/src/segment.py` | lungmask R231/LTRCLobes + TotalSegmentator `lung_vessels` + HU body. Nodule removal from vessels (AC-5). Writes the masks + `anatomy_masks.json`. Per-patient cache. |
| New | `A_placement/src/context.py` | EDT fields, lung/lobe lookup, local HU, vessel density, `context` dict builder. |
| New | `A_placement/src/bifurcation.py` | 3-D skeleton, branch points, large-vessel gate. |
| New | `A_placement/src/classes.py` | `classify_mask` + `classify_site` + the threshold constants (single source). |
| New | `A_placement/src/place.py` | CLI: per-class eligible sets, seeded sampling with minimum spacing, `sites.json`, run record. Mirrors `shared/stubs/make_stubs.py::make_sites` for JSON assembly. |
| New | `A_placement/src/export_figures.py` | 2-D orthogonal-slice export `figures/18-host-sites.png`. |
| New | `A_placement/repro/class_proportions.py` | LIDC subset → nodule classes → `proportions.json` + `figures/18-class-proportions.png`. |
| New | `A_placement/repro/lidc_subset.txt` | Committed deterministic patient list. |
| New | `A_placement/figures/18-class-proportions.png` | Reproduction figure (committed). |
| New | `A_placement/figures/18-host-sites.png` | Placement export figure (committed). |
| Modify | `A_placement/dossiers/18-syn-lungs-placement.md` | Fill all eight sections (A01 gap, F01/Kostis rule, parameters, reproduction, verdict). |
| Modify | `A_placement/README.md` | Fill the fixed sections, including How to run and Contract change requests. |
| Modify | `A_placement/status.json` | #18 → `adapted`; `papers` + F01; `reproduced`; `figures`; `updated`. |
| Modify | `feature-A-placement.md` | Tick ACs, fill §9 during implementation. |

There are no edits to `shared/`, `.gitignore`, other letters, `index.html` or `site/`. The `runs/` folder is already gitignored, and LIDC data lives outside the repo.

---

## 7. Manual Verification (No Tests)

All commands run from `RE/` in env `qp-re-a`.

- [ ] **Verify AC-1:** `conda env create -f A_placement/environment.yml && conda activate qp-re-a && python -m shared.validate --stubs` → all stubs OK.
- [ ] **Verify AC-2:** `python -m A_placement.src.lidc_fetch --select 40 --fetch` → `repro/lidc_subset.txt` has 40 IDs, `$LIDC_ROOT` holds 40 series and `pylidc` `pl.query(pl.Scan).first().load_all_dicom_images()` works. A second run downloads nothing.
- [ ] **Verify AC-3:**
  - Convert `LIDC-IDRI-0001`. `read_header` shows LPS identity and the DICOM spacing.
  - Overlay the pylidc consensus mask of one nodule on its centroid slice (export PNG) and confirm by eye that it sits on the nodule, not mirrored or shifted.
- [ ] **Verify AC-4:**
  - `python -m A_placement.src.segment --patient LIDC-IDRI-0001` → `python -m shared.validate A_placement/runs/cache/LIDC-IDRI-0001/anatomy_masks.json` OK.
  - Lobes count 5 non-empty labels. Right lung (label 1) is on patient-right (−x in LPS ⇒ low x index).
- [ ] **Verify AC-5:** the vessel mask has zero voxels inside any dilated consensus nodule. No site in `sites.json` is within `2r` of a nodule centroid.
- [ ] **Verify AC-6/AC-7:**
  - For 3 sites, recompute `dist_pleura_mm` by hand: the nearest non-lung voxel distance in mm via a small script. It matches within one voxel diagonal.
  - Bifurcation points overlaid on a vessel MIP sit at visible branchings.
- [ ] **Verify AC-8:** the classes table in the reproduction log shows each nodule's ring statistics. Spot-check 5 nodules per class visually in a 3-slice export: juxtapleural touch the wall, juxtavascular touch a vessel.
- [ ] **Verify AC-9:** `python -m A_placement.repro.class_proportions --subset A_placement/repro/lidc_subset.txt` → `proportions.json` + figure. Read the per-class proportions, CIs and agreement verdict against ±10 pp + ordering, and record them in the dossier whatever the outcome.
- [ ] **Verify AC-10/AC-11:**
  - `python -m A_placement.src.place --patient LIDC-IDRI-0001 --per-class 10` → `python -m shared.validate` on `sites.json`, `anatomy_masks.json` and `run.json` → OK.
  - Rerun with the same seed: the `sites` array is identical. A different `--seed-hex` gives different sites.
  - Each emitted class re-checks with `classify_site`.
- [ ] **Verify AC-12:** open `figures/18-host-sites.png`. One site per class sits at the expected anatomy.
- [ ] **Verify AC-13:** `python -m shared.validate --status` OK. `python -m shared.site.build` (local preview, **not committed**) shows #18 as `adapted` with the reproduced number.
- [ ] **Edge case:** for a patient with slice thickness > 2.5 mm, `lidc_fetch --select` excludes it. A class with zero eligible voxels yields a shortfall note, not a crash.

---

## 8. Open Questions

- [x] **Q1 — Environment:** create a separate conda env `qp-re-a` (Python 3.11, CPU torch), or install into base (3.13)? *Resolved (accepted default):* separate env. Base 3.13 + numpy 2.4 likely breaks pylidc/torch wheels, and an env file keeps it reproducible.
- [x] **Q2 — LIDC subset size and location:** how many scans, and where? *Resolved (accepted default):* 40 scans (≈ 80–120 consensus nodules, ≈ 4–8 GB, ~6 h of CPU segmentation). Location `~/data/LIDC-IDRI`, outside the repo. Download via `tcia_utils`; fallback is a manual NBIA Data Retriever download with the same list.
  - **AMENDED by developer 2026-10-29: 20 scans, run in parallel, target ≤ 6 h wall clock.**
    - Measured cost is ~25 min per scan on CPU (TotalSegmentator ≈ 20 min, lungmask ≈ 5 min, using ~3 of 8 cores), so 40 sequential scans ≈ 16 h.
    - New scope: the **first 20 patients** of the deterministic list. `repro/lidc_subset.txt` is trimmed to its first 20 lines, so the order and selection rule are unchanged. All 40 are already downloaded; the extra 20 stay on disk unused.
    - New behaviour: `class_proportions.py --workers 3` segments scans in a `ProcessPoolExecutor`, with torch threads per worker set to `max(1, cpu_count // workers)`. The aggregation stays sequential afterwards.
    - Estimate: 17 uncached scans × ~25–30 min ÷ 3 ≈ 2.5–3.5 h.
    - No per-scan method speed-ups (skipping the separate R231 call, TotalSegmentator `robust_crop=False`). They would make the 3 already-cached scans methodologically different from the rest.
- [x] **Q3 — Reproduction reference and pass criterion:** Kostis via Ambrosini [F01] gives only qualitative fractions ("almost half / around one-third / approaching one-quarter"). *Resolved (accepted default):* reference 0.45 / 0.33 / 0.22. Pass = each class within ±10 pp **and** the same ordering. Report Wilson CIs. A miss is recorded as is, not tuned.
- [x] **Q4 — Vessel source:** TotalSegmentator `lung_vessels` is the planned source. *Resolved (accepted default):* use it if its licence is free for this task (check in the dissect step). Fallback: Frangi vesselness (`skimage.filters.frangi`) on lung-masked HU, thresholded. Whichever is used is recorded in the dossier.
- [x] **Q5 — Fixed thresholds (decided before reproduction):** *Resolved (accepted default):*
  - ring = 1 voxel (6-conn);
  - `pleura_contact_frac = 0.10`;
  - `vessel_contact_vox = 5`;
  - `min_vessel_radius_mm = 1.5`;
  - site `margin = 3 mm`;
  - consensus `clevel = 0.5`, ≥ 3 readers, diameter ≥ 3 mm.
- [x] **Q6 — Default host scan for the committed figure and the INT hand-off:** *Resolved (accepted default):* the first patient in `lidc_subset.txt` with slice thickness ≤ 1.25 mm (a good 3-D grid for E/F). Use native spacing, with no resampling per the contract.
- [x] **Q7 — Sites per class:** *Resolved (accepted default):* `--per-class 10` (30 sites). Use equal counts per class, because the class prior belongs to B's rulebook, not to A's candidate set.
- [x] **Q8 — `nominal_radius_mm`:** placement class depends on lesion size, which B draws later. *Resolved (accepted default):* use the median LIDC consensus radius from the reproduction, recorded in `context.extra.nominal_radius_mm`. B/F may recheck the class for the actual drawn size. Record this in "Contract change requests" as a possible future first-class field.
- [x] **Q9 — Where the plan/implementation runs:** *Resolved (accepted default):* commit this plan on `main`, then `git worktree add ../qp-re-A -b re-A` and run `/implement-feature` there, per epic §3.

---

## 9. Post-Implementation Notes

### Progress checkpoint — PAUSED 2026-10-29 (developer stopped the run; resume with `/implement-feature` on this file in worktree `../qp-re-A`, branch `re-A`)

**Done and verified by hand**
- **AC-1:** env `qp-re-a` exists. `A_placement/environment.yml` was changed from the plan in three ways:
  - **Python 3.12, not 3.11:** frozen `shared/runrecord.py` uses `Path.relative_to(walk_up=True)`, which needs ≥ 3.12.
  - **Added `cryptography`:** `shared.validate --stubs` verifies receipt signatures.
  - **Added `setuptools<81`:** pylidc 0.2.3 imports `pkg_resources`.

  `python -m shared.validate --stubs` passes in it.
- **pylidc shim:** pylidc 0.2.3 uses `np.int/np.float/np.bool`. `lidc_io.pylidc()` re-adds the aliases before import, so there is no numpy downgrade, because torch/TotalSegmentator need numpy 2.
- **AC-2:**
  - `lidc_fetch --select 40` wrote `repro/lidc_subset.txt` (40 patients).
  - `--fetch` downloaded all 40 series to `~/data/LIDC-IDRI` (5.0 GB).
  - `~/.pylidcrc` was written.
- **AC-3 (verified on LIDC-IDRI-0001):**
  - Host CT is 133×512×512 at 0.703/0.703/2.5 mm, LPS identity.
  - The consensus nodule contour lands exactly on the nodule (overlay checked by eye).
  - Right lung (label 1) sits at low x, which is correct for LPS.
- **AC-4:** `anatomy_masks.json` validates OK.
  - **Deviation:** TotalSegmentator 2.18 splits task `lung_vessels` into `lung_arteries`, `lung_veins`, `lung_airways` and `lung_airways_wall`. So `vessels` = arteries ∪ veins, and `airway` = airway lumen ∪ wall. Existing TotalSegmentator outputs are reused.
- **AC-5:** zero vessel voxels inside the nodule (61 before removal).
- **AC-10/AC-11 smoke run (`--radius-mm 5`, run `20261029-055342-place`):**
  - 10/10/10 sites, no shortfall.
  - `sites.json`, `anatomy_masks.json` and `run.json` all validate OK.
  - This is a test only. The final run must use the median radius from the reproduction.
- **Rule sanity:** the LIDC-0001 nodule (32.8 mm) classifies as juxtavascular (56 vessel contact voxels, pleura_frac 0.0). The lung mask shows ~1.4–3.5 mm of parenchyma between the nodule and the chest wall, so "not juxtapleural" is correct under the pre-registered 1-voxel-contact rule. **Thresholds were NOT changed.**
- **Licences:** lungmask Apache-2.0, TotalSegmentator Apache-2.0 (`lung_vessels` ran with no licence key), pylidc MIT, tcia_utils Apache-2.0.

**Segmentation cache** (in `A_placement/runs/cache/`, gitignored): LIDC-IDRI-0001, 0003 and 0004 are complete. 0005 is partial (killed mid-run, no `meta.json`, so it is recomputed automatically).

**Code written** (all in `A_placement/`): `environment.yml`, `src/{classes,lidc_fetch,lidc_io,segment,context,bifurcation,place,export_figures}.py`, `repro/class_proportions.py`, `repro/lidc_subset.txt`.

**Remaining on resume, in order**
1. Trim `repro/lidc_subset.txt` to its first 20 patients (Q2 amendment).
2. Add `--workers N` (default 3) to `repro/class_proportions.py`:
   - parallel `segment(pid)` via `ProcessPoolExecutor`;
   - `torch.set_num_threads(max(1, os.cpu_count() // N))` in each worker;
   - classification and aggregation stay as they are.
3. Run `python -m A_placement.repro.class_proportions --workers 3` in the background (≤ 6 h; cached scans are skipped). This gives `proportions.json` and `figures/18-class-proportions.png`. Record the result honestly, pass or miss (AC-9).
4. Run the final `place` for the Q6 host: the first patient in the subset with slice thickness ≤ 1.25 mm, `--per-class 10`, radius taken from `proportions.json`. Validate the outputs (AC-10/11).
5. Run `export_figures --run <place run>` to produce `figures/18-host-sites.png` (AC-12).
6. Write the dossier (8 sections: A01 has no rules, F01/Kostis rule, the TotalSegmentator 2.18 class split, airway = lumen ∪ wall, licences, the lungmask nodule-exclusion note), the README and `status.json` → `adapted`, `papers` + F01. Then run `python -m shared.validate --status` (AC-13).
7. Do the §6 sanity sweep, tick the ACs with file:line evidence, set Status Complete, commit on `re-A`, and merge to `main`.
