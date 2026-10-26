# Feature F2 — Lesion → CT image: decode params → 3D lesion → insert into real CT

**Epic:** [`epic-quantum-phantoms-mvp.md`](./epic-quantum-phantoms-mvp.md) (Approved)
**Feature ID:** F2
**Author:** Claude (Opus)
**Date:** 2026-10-26
**Status:** Complete

> **Technical constraints / core directive.** Stack locked: **Python** (numpy + scipy + Pillow + scikit-image; **SimpleITK** added for LUNA16 `.mhd` reads). Pure image-domain insertion — **no phantom, no CT-physics simulator** (fully-open Path A, parent §10). F2 consumes F1's `cohort_params.json` + `quantum_run.json` and is **blind to the sampler** that produced them (epic §3 seam). Output = labeled synthetic CT tiles (PNG + `tiles.json`) for F3. Research-study conventions: **no GitHub issues, no automated test suite — manual verification only.** Honest claim ceiling unchanged: params quantum, **image classical**; provenance is about lesion/cohort *selection*, never the CT background (epic §6).

---

## 1. Why (Step Goal)

**Before.** F1 produces certified-quantum tumor parameters as JSON (`TumorParams` cohort + `QuantumRun` provenance), but nothing turns them into something that *looks like a CT scan*. There is no lesion geometry, no CT background, no image.

**After.** F2 is the rendering stage. For each `TumorParams` it:
1. Builds a **3D lesion blob** whose geometry is driven by the decoded params — `size_mm` → radius, `type` → HU density profile, `margin` → surface deformation (smooth / lobulated / spiculated).
2. **Inserts** the lesion's central slice into a **real public lung-CT slice** (LIDC-IDRI / LUNA16) in the HU domain, with **matched local noise** so it does not read as pasted (parent §10 Path A).
3. Places **sibling-pair tiles** (same `lineage_id`) as two *related* lesions, preserving the lineage tag for F3's badge.
4. Writes **labeled synthetic CT tiles**: one PNG per tile + a `tiles.json` of `CohortTile` records carrying the decoded label, the insertion metadata, the background-source honesty flag, and the provenance stamp (backend, job id, CHSH) copied from `quantum_run.json`.

F2's deliverable is `research_runs/<run>/tiles/*.png` + `research_runs/<run>/tiles.json` — the exact inputs F3's web grid will render. Like F1's Aer-vs-hardware split, F2 has a **synthetic-background dev default** (pipeline runs with no downloaded data) and a **real-CT path** for the actual demo; every tile records which it used.

---

## 2. Acceptance Criteria

- [x] **AC-1** (F2.1) — `code/lesion.py:71` (`build_lesion`), `HU_BY_TYPE` at `:25`, margin deformation `_deformed_threshold`, `central_slice` at `:115`. Visually confirmed: tile_3 (13 mm solid spiculated) = large irregular/spiky bright blob; tile_0 (4 mm ground-glass) = faint/tiny. Each `TumorParams` becomes a 3D lesion blob whose geometry reflects its params.
  → `lesion.py:build_lesion(params, spacing_mm)` returns a `Lesion` (3D HU volume + mask). `size_mm`→radius in voxels via `spacing_mm`; `type`→HU profile (`HU_BY_TYPE`); `margin`→boundary deformation (smooth = clean ellipsoid; lobulated = few low-frequency bulges; spiculated = radial spikes). Shape detail seeded from `shot_index` for per-tile variation.
- [x] **AC-2** (F2.2) — `code/insert.py:46` (`insert_lesion`, HU-additive blend), `_match_noise` at `:35`, `window_to_uint8` at `:81`. Verified on a `.npy` HU background: lesion blends with local-σ matched noise, no hard paste edge. A lesion is inserted into a real lung-CT slice in the HU domain with matched noise.
  → `insert.py:insert_lesion(ct_slice, lesion, xy, spacing)` blends the lesion's central slice at `xy` using an alpha/HU-additive blend, then adds Gaussian noise whose σ matches the local background patch (`_match_noise`). Works on HU arrays from `.mhd`/`.npy`; falls back to intensity-domain for 8-bit PNG backgrounds.
- [x] **AC-3** (F2.3) — `code/ctsource.py:79` (`load_backgrounds`: `.mhd`/`.npy`/PNG readers), `synthesize_lung_field` at `:30`, `Background` at `:23`. Synthetic default run tagged `synthetic_dev`; `.npy` dir run tagged `npy`. A real public CT background is loaded, with a labeled synthetic fallback for development.
  → `ctsource.py:load_backgrounds(source)` reads real slices from a directory of LUNA16 `.mhd` (SimpleITK), `.npy` HU arrays, or grayscale PNG; `--ct-source synthetic` (dev default) generates a clearly-labeled synthetic lung field. Each returned background carries `background_source ∈ {real_lidc, real_luna16, npy, png, synthetic_dev}` and its `spacing_mm`.
- [x] **AC-4** (F2.4) — `code/insert.py:24` (`place_for_lobe`, `_LOBE_REGION` map). Verified in `tiles.json`: RLL lands image-left/low (`xy≈[140,385]`), LUL image-right/upper (`[372,149]`), RUL image-left/upper (`[181,158]`) per radiological convention. Lesion placement respects the decoded lobe.
  → `insert.py:place_for_lobe(lobe, slice_shape, rng)` maps the 5 lobes (RUL/RML/RLL/LUL/LLL) to an approximate region of the slice (left/right × upper/mid/lower heuristic, jittered). No lung segmentation in the MVP.
- [x] **AC-5** (F2.5) — `code/build_tiles.py:87` (`main`, `_group_by_lineage` at `:80`; daughter placed near the parent in one shared slice). tile_9 PNG shows two adjacent related lesions; `tiles.json` pairs share `lineage_id` (`pair8`/`pair9`) with generations 0 and 1. Sibling pairs render as two related, adjacent lesions sharing a lineage.
  → tiles with the same `lineage_id` are inserted as a nearby pair in one slice region; both `CohortTile`s carry the shared `lineage_id` and their `generation` (0 parent / 1 daughter).
- [x] **AC-6** (F2.6) — `code/build_tiles.py:87` (writes `tiles/*.png` + `tiles.json`), `CohortTile` at `code/datamodel.py:69`. Run produced 12 PNGs + a 12-record `tiles.json`; each record has all 15 fields incl. `insert_xy`, `spacing_mm`, `background_source`, and `chsh_value`/`backend_name`/`job_id` matching `quantum_run.json`. Every tile is written as a PNG plus a labeled `CohortTile` record with provenance.
  → `build_tiles.py` writes `research_runs/<run>/tiles/tile_<shot>_<gen>.png` (lung-windowed uint8 crop centered on the lesion) and `research_runs/<run>/tiles.json` (`list[CohortTile]`). Each record carries the decoded params, insertion `xy`/`spacing`, `background_source`, PNG path, and the provenance stamp (`backend_name`, `job_id`, `chsh_value`) read from `quantum_run.json`.
- [x] **AC-7** (F2.7) — `code/build_tiles.py:66` (`_load_f1` via `TumorParams.from_dict` / `QuantumRun.from_dict`). Ran against a `qrng_aer` F1 run; identical `TumorParams`/`QuantumRun` schema means a `prng` run renders identically (epic §3 seam). F2 is blind to the sampler and consumes F1 output unchanged.
  → `build_tiles.py --run <dir>` reads `cohort_params.json` via `TumorParams.from_dict` and `quantum_run.json` via `QuantumRun.from_dict`; it runs identically whether F1 used `QRNGSampler` or `PRNGSampler` (epic §3 seam).
- [x] **AC-8** (F2.8) — `code/build_tiles.py:32` (`HONEST_LABEL`, written as `tiles.json` top-level `honest_label`); every `CohortTile` carries `background_source`. Nothing claims a quantum/non-classical image. The honest label is preserved on the output.
  → `tiles.json` carries a top-level `honest_label` ("tumor parameters are quantum; the image is a classical rendering; provenance is about lesion selection, not the CT background") and each tile's `background_source`; nothing claims a quantum or non-classical image (epic §6, parent §5.4).

---

## 3. Out of Scope (Postponed)

- **The web cohort grid, per-tile CHSH stamp rendering, cohort-vs-rulebook histogram, lineage badge UI** → **F3**. F2 emits PNGs + JSON only; it does not build the page.
- **The quantum roll / CHSH computation** → **F1** (done). F2 only *copies* the provenance values forward.
- **Multi-generation lineages / evolved cohorts** → **F4** (optional). F2 handles only F1's single-division sibling pairs; if F4 later feeds a richer lineage, F2 consumes it unchanged (same `TumorParams` contract).
- **Phantom anatomy (XCAT), CT-physics simulation (DukeSim/XCIST), scanner-specific fidelity** → deferred to the full plan (parent §10). F2 is image-domain insertion only.
- **Lung segmentation / anatomically-exact lobe placement** → later refinement; MVP uses a heuristic region map (AC-4).
- **Signing / ledger / audit of tiles** → deferred (parent §2.1).

---

## 4. Technical Decisions

Adopts the epic's §3 cross-cutting decisions verbatim (sampler-blind consumption, honesty gates, self-contained static artifact downstream, no issues/tests). Feature-specific choices:

| Component | Choice / Implementation |
|---|---|
| Imaging stack | **numpy** (volumes), **scipy.ndimage** (blob deformation, gaussian), **scikit-image** (resize/draw helpers), **Pillow + imageio** (PNG write). All already installed. |
| CT reader | **SimpleITK** (new dep) for LUNA16 `.mhd/.raw` (gives HU + spacing); **numpy** for `.npy` HU arrays; **Pillow** for grayscale PNG. LIDC DICOM is **out of scope for the reader** in the MVP — convert to `.npy`/`.mhd` first (noted in README). |
| Dev fallback | `--ct-source synthetic`: a procedurally-generated lung field (low-HU parenchyma + vessels + noise), tagged `synthetic_dev`. Default for development so the pipeline runs with zero downloaded data (mirrors F1's Aer default). The real demo uses `--ct-source <dir>`. |
| Insertion domain | **HU-additive blend** for real/`.npy` backgrounds (physically meaningful); intensity blend for PNG. Matched Gaussian noise from the local background patch so the lesion grain matches. |
| HU by type | `solid` ≈ +30 HU, `part-solid` ≈ ground-glass halo (−650) + solid core (+30), `ground-glass` ≈ −650 HU, `calcified` ≈ +300 HU, over a lung parenchyma background (~ −750 HU). Table in `lesion.py`, confirmable (Q7). |
| Pixel spacing | from `.mhd` metadata where present; `--spacing 0.7` default (typical LUNA16 in-plane mm/px) for `.npy`/PNG/synthetic (Q4). |
| 3D → tile | build a small 3D blob volume, extract the **central axial slice** for insertion (keeps "3D lesion blob" honest and F4-extensible). |
| Tile PNG | lung window **WL −600 / WW 1500** → uint8; save a **crop centered on the lesion** (default 128×128) for the grid. Window + crop size configurable. |
| Output | `research_runs/<run>/tiles/*.png` + `tiles.json`, mirroring F1's `research_runs/<run>/` convention and `json.dump(..., indent=2, default=str)` style. |

**Conventions & Notes:**
* Source lives in `QuantumPhantoms/code/` (flat imports by bare module name, run from inside `code/`), mirroring F1.
* F2 **never** recomputes quantum anything — it reads `quantum_run.json` and copies `backend_name`/`job_id`/`chsh_value` onto each tile. CHSH stays a single job-level value (plan F1 §4 honesty note).
* Honest label is carried forward verbatim and the per-tile `background_source` makes the real-vs-synthetic status explicit; no tile ever implies a quantum image (epic §6).
* Deterministic given F1 output + `--seed` (placement/deformation RNG seeded per `shot_index`), so a run is reproducible.

---

## 5. Data Model (Additions/Modifications)

F2 **introduces** `Lesion` and `CohortTile` (epic §4) and **consumes** F1's `TumorParams` / `QuantumRun` unchanged.

```text
[Modifying] QuantumPhantoms/code/datamodel.py — add two dataclasses

[New Entity] Lesion                                 (lesion.py builds it)
  volume_hu     np.ndarray    # small 3D HU blob (not serialized to JSON)
  mask          np.ndarray    # 3D boolean support (not serialized)
  radius_vox    float
  hu_profile    str           # echo of the type-driven HU model used
  margin        str           # smooth | lobulated | spiculated

[New Entity] CohortTile                              (datamodel.py; serialized to tiles.json)
  tile_id            str       # f"tile_{shot_index}_{generation}"
  png_path          str        # relative path under the run dir
  size_mm           float
  type              str
  margin            str
  lobe              str
  lineage_id        str
  generation        int
  shot_index        int
  insert_xy         [int, int] # lesion centre in the slice
  spacing_mm        float
  background_source str        # real_lidc | real_luna16 | npy | png | synthetic_dev
  backend_name      str        # copied from QuantumRun
  job_id            str        # copied from QuantumRun
  chsh_value        float      # copied from QuantumRun (job-level)
```

`tiles.json` top-level shape: `{"honest_label": str, "quantum_run": {...}, "tiles": [CohortTile, ...]}`.

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `QuantumPhantoms/code/lesion.py` | `build_lesion(params, spacing_mm, seed)` → `Lesion`; `HU_BY_TYPE`; margin deformation (smooth/lobulated/spiculated) via scipy.ndimage. |
| New | `QuantumPhantoms/code/ctsource.py` | `load_backgrounds(source, spacing)` → list of `(array, background_source, spacing_mm)`; SimpleITK `.mhd` / numpy `.npy` / Pillow PNG readers + `synthesize_lung_field()` dev fallback. |
| New | `QuantumPhantoms/code/insert.py` | `insert_lesion(ct_slice, lesion, xy, spacing)` (HU-additive + `_match_noise`); `place_for_lobe(lobe, shape, rng)`; `window_to_uint8(hu, wl, ww)`; `crop(slice, xy, size)`. |
| New | `QuantumPhantoms/code/build_tiles.py` | CLI entrypoint: `--run <dir>` (F1 output), `--ct-source`, `--spacing`, `--crop`, `--seed`; reads F1 JSON, builds+inserts lesions, writes PNGs + `tiles.json`, prints summary. |
| Modify | `QuantumPhantoms/code/datamodel.py` | add `Lesion` (non-serialized) and `CohortTile` (`to_dict`/`from_dict`) dataclasses. |
| Modify | `QuantumPhantoms/requirements.txt` | add `Pillow`, `scipy`, `scikit-image`, `imageio`, `SimpleITK` (pin to installed versions; SimpleITK newly added). |
| Modify | `QuantumPhantoms/code/README.md` | add an F2 section: how to run `build_tiles.py`, the `--ct-source` synthetic-vs-real split, where LUNA16 data goes, the honest-label note, the `tiles.json` contract for F3. |

---

## 7. Manual Verification (No Tests)

- [ ] **Verify AC-1 / AC-7 (dev path):** `python QuantumPhantoms/code/build_tiles.py --run research_runs/<f1_run> --ct-source synthetic` → exits 0, writes `tiles/` PNGs + `tiles.json`; open a few PNGs and confirm visible lesions of varying size/margin.
- [ ] **Verify AC-1:** inspect that a `>20mm` tile's lesion is clearly larger than a `<6mm` tile's, a `spiculated` margin shows spikes vs a `smooth` one, and a `ground-glass` lesion is fainter than a `solid` one.
- [ ] **Verify AC-2 / AC-3 (real path):** drop one LUNA16 `.mhd/.raw` (or a `.npy` HU slice) into a dir, run `--ct-source <dir>` → tiles use the real background (`background_source` ≠ `synthetic_dev`), lesion blends without a hard paste edge (matched noise).
- [ ] **Verify AC-4:** confirm a `RUL` lesion lands upper-right and an `LLL` lesion lower-left of the slice (region heuristic).
- [ ] **Verify AC-5:** find a sibling pair in `tiles.json` (shared `lineage_id`, generations 0 and 1) and confirm the two PNGs show nearby related lesions.
- [ ] **Verify AC-6 / AC-8:** `tiles.json` has one record per tile with PNG path, insertion metadata, `background_source`, and `chsh_value`/`backend_name`/`job_id` matching `quantum_run.json`; the top-level `honest_label` is present.
- [ ] **Edge case:** `--ct-source <empty dir>` → clear error telling the user to add CT files or use `--ct-source synthetic`; `--run` pointing at a missing/invalid F1 dir → clear error.

---

## 8. Open Questions

All resolved — defaults accepted by Peter (2026-10-26). Locked decisions:

- [x] **Q1 (SimpleITK dependency):** Add **SimpleITK** to `requirements.txt` as the LUNA16 `.mhd/.raw` reader; also support `.npy` HU arrays and grayscale PNG via the installed libs. LIDC DICOM reading stays out of scope — user converts to `.npy`/`.mhd` first.
- [x] **Q2 (synthetic fallback default):** Ship a **labeled synthetic lung-field fallback** as the dev default (`--ct-source synthetic`); real demo uses `--ct-source <dir>`. Every tile records `background_source`; synthetic is dev-only per the honesty label.
- [x] **Q3 (3D blob → 2D tile):** Build a small 3D HU blob and insert its **central axial slice**.
- [x] **Q4 (pixel spacing):** `--spacing 0.7` mm/px default; use `.mhd` metadata when present.
- [x] **Q5 (lobe placement):** Heuristic region map (left/right × upper/mid/lower + jitter), no lung segmentation in the MVP.
- [x] **Q6 (tile image):** **128×128 crop centered on the lesion** (configurable) per tile.
- [x] **Q7 (HU values):** solid +30, part-solid (GGO −650 halo + +30 core), ground-glass −650, calcified +300 HU, over ~−750 HU lung background; lung window WL −600 / WW 1500. Tune after first render.

---

## 9. Post-Implementation Notes

**Built (2026-10-26).** 5 new files + 3 modified under `QuantumPhantoms/`, on `main` (consistent with F1). New dep **SimpleITK 2.5.6** installed and pinned. All other imaging libs were already present (Pillow 12, scipy 1.15.3, scikit-image 0.25, imageio 2.37).

New: `code/{lesion,ctsource,insert,build_tiles}.py`. Modified: `code/datamodel.py` (+`CohortTile`), `code/README.md` (+F2 section), `requirements.txt` (+imaging stack).

**Decisions within the plan:**
- `Lesion` dataclass lives in `code/lesion.py` (it holds numpy arrays and is a runtime object), not `datamodel.py`, so `datamodel.py` stays numpy-free / JSON-only. `CohortTile` (serialized) is in `datamodel.py` as planned. Minor placement deviation from §5's "add both to datamodel.py".
- F2 writes its outputs **into the same F1 run dir** (`<run>/tiles/` + `<run>/tiles.json`) so one run folder holds the whole pipeline's artifacts; `tiles.json` embeds the full `quantum_run` for F3 convenience.
- Sibling pairs are inserted into **one shared slice** and each tile is cropped from it, so a daughter's crop can show the nearby parent — makes the lineage visually obvious (tile_9 shows both lesions).

**Verified (synthetic + real `.npy`):** 12 tiles / 10 lineages rendered; lesion size/margin/type visibly differ (13 mm spiculated solid vs faint 4 mm GGO); HU-domain insertion blends with matched noise; lobe placement matches the region map; sibling pairs adjacent + shared lineage; `tiles.json` schema complete with CHSH/backend/job_id carried from `quantum_run.json`; honest label present; edge errors (empty CT dir, bad `--run`) are clear.

**Follow-ups for the developer:**
- For the real demo, drop LUNA16 `.mhd/.raw` (or `.npy` HU slices) in a dir and run `--ct-source <dir>`; the synthetic background is dev-only (tagged `synthetic_dev`).
- Ground-glass + small (<6 mm) lesions render faint by design — if the demo needs them punchier, tune `HU_BY_TYPE`/window in `lesion.py`/`build_tiles.py` (plan Q7 left this to post-render tuning).
- F3 reads `<run>/tiles.json` + `<run>/tiles/*.png`.
- LIDC DICOM is not read directly (no pydicom); convert to `.npy`/`.mhd` first.
