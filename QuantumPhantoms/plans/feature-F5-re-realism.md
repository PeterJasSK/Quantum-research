# Feature F5 — RE realism refactor: Siemens LIDC host + E growth + F render, folded into one `imaging` package

**Epic:** [epic-quantum-phantoms-mvp.md](epic-quantum-phantoms-mvp.md) (Approved; F5 row added 2026-10-31)
**Feature ID:** F5
**Author:** Claude (Opus)
**Date:** 2026-10-31
**Status:** Complete (implemented 2026-10-31; see §9)

> Stack locked: Python 3.13 (conda base), numpy, scipy, scikit-image and SimpleITK, all already pinned in `requirements.txt`, so no new dependency.
> Core directive: **copy** a limited, frozen subset of the reverse-engineering (RE) letters **E** (classical growth) and **F** (render) into the MVP. The MVP never imports the RE tree.
> **Fold** the copied code and the existing F2 code into one renamed package, `code/imaging/`. The old `f2_imaging/` goes away.
> The output contract is still `tiles.json` + `CohortTile`, with optional new fields. F3 stays sampler-blind and is still one static page.
> No automated tests; verification is manual only. No IBM job is submitted; development uses Aer and PRNG runs.

---

## 1. Why (Step Goal)

**Before.** The MVP page works, but it looks like a demo rather than a dataset viewer.
- **Host.** Every nodule is pasted into **one 8-bit JPEG** (`data/ct_slices/thorax_ptrump16_cc-by-sa-4.0.jpg`).
  - It is not in HU, and its spacing is a guessed 0.7 mm.
  - All 12 nodules sit on the same axial slice.
- **Lesion.** The lesion is a procedural blob built in `code/f2_imaging/lesion.py`.
  - HU values are constants per type (solid +30, GGO −650).
  - The shape comes from hand-picked harmonics.
  - Only its 2-D central slice is used.
- **Blur and noise.** The blur is a fixed Gaussian (`psf=0.7` px), and the noise is matched to the local patch std.
- **Growth.** The only "growth" is `code/f4_qalife/grow.py`. It builds a union of independent blobs that roughly doubles each generation, which is unphysical. It produced the static strip `web/progressionDEMO.html`.

**What RE learned and the MVP does not use yet:**
- **F (render), evidence:**
  - an LIDC-fitted lesion library containing parameters only (`F_render/library/lesion_model_library.json`), whose spherical-harmonic (SH) shape correlation of 0.87 matches [F01]'s 0.89;
  - a supersampled partial-volume edge (erf σ ≈ 1.1–1.5 mm);
  - an additive-delta 3-D insert that reproduces the volume headline (**+0.25 ± 1.02 %**);
  - a fingerprint of the host scanner (PSF σ zyx + NPS), with noise moments within 2 % of [F05].
- **E (growth), evidence:**
  - a Kansal–Torquato layered automaton that matches **3 of 4 stages** of Table 2;
  - Pixel2Cancer pressure barriers (the pleura is a hard wall);
  - lung calibration to volume doubling times (VDT) of **147.6 / 465.8 / 825.4 d** (solid / part-solid / GGO), against targets of 149 / 457 / 813 *(verify)*;
  - about 5 s for a solid nodule to reach Ø 8 mm.

**After F5.** One `imaging` package renders the F1 (or F4) cohort with the new default renderer `grown`:
1. **Host.** Each nodule lives in a **real 3-D HU CT volume from a Siemens scanner**. The default is public LIDC-IDRI case `LIDC-IDRI-0481`, a SIEMENS SOMATOM Definition scan (259 images, CC BY 3.0, TCIA). Each nodule sits at its own z-level inside the lung mask.
2. **Growth.** The copied E engine grows the shape from a Ø 2 mm seed to the quantum-rolled `size_mm`. The pleura is a hard wall. Growth then continues for a +90-day follow-up snapshot.
3. **Rendering.** The copied F library renders the grown shape: HU, edge, texture, and spicules when the margin is spiculated.
4. **Insertion.** The lesion is inserted in 3-D with that Siemens scan's own measured blur and noise.
5. **Page.** The page shows the realistic tile **and a "pixel growth" player**: 8 frames running seed → baseline → follow-up, labelled with simulated day and diameter. This is the requested proof of concept.

**Old look still available.** The old procedural look stays one flag away (`--renderer procedural`), on the old JPEG. `--compare` writes an image with F2.1 and F5 side by side for the same tumours.

**What does not change.** The claim stays the same. Parameters come from a certified-quantum roll; growth and image are classical. The quantum bits seed growth and appearance, which makes them **replayable provenance, not realism**.

---

## 2. Acceptance Criteria

- [x] **AC-0** (F5.0): `code/f2_imaging/` is renamed to `code/imaging/` (git mv), and every caller is updated.
  - Evidence: `git mv` done; imports `code/imaging/build_tiles.py:33-41`, `code/f4_qalife/grow.py:40-42`, `code/f4_qalife/run_qalife.py:7`; `--renderer procedural` output `diff -r` + `cmp tiles.json` **byte-identical** to the pre-rename baseline; `grep f2_imaging code/` empty.
  - Callers: `code/f4_qalife/grow.py:40-42`, the `code/f4_qalife/run_qalife.py:7` docstring, `code/README.md`, `plans/runlog-mvp-run.txt`.
  - There is no `f2_imaging` compatibility shim. `grep -rn f2_imaging code/` returns nothing, apart from historical plan files.
  - `python -m imaging.build_tiles --run <f1> --renderer procedural` reproduces today's F2.1 output byte for byte.
- [x] **AC-1** (F5.1): A Siemens LIDC host can be fetched and loaded.
  - Evidence: `code/imaging/lidc_fetch.py:33` (`lookup_series`), `:81` (non-Siemens warning); `code/imaging/host.py:101` (`_read_series`), `:75` (`make_masks`), `:125` (`load_host`, npz cache). LIDC-IDRI-0481 fetched (259 DICOM; SIEMENS Definition, kernel B45f, 1 mm, 259×512×512, 0.605 mm in-plane); host prep 41 s.
  - `imaging/lidc_fetch.py` is copied from RE `F_render/src/lidc.py` `download_series`, using the public TCIA NBIA `getImage` call.
  - `python -m imaging.lidc_fetch LIDC-IDRI-0481` puts the series under `~/data/LIDC-IDRI/` in the pylidc layout. The series UID is resolved through NBIA `getSeries?Collection=LIDC-IDRI` and the request is filtered to `Manufacturer == SIEMENS`. A non-Siemens id prints a warning.
  - `imaging/host.py: load_host(lidc_id) -> Host(hu int16 zyx, spacing_zyx, origin_lps, lungs, left_right, body, series_uid, manufacturer, model, kernel, slice_thickness)` reads the series with `SimpleITK.ImageSeriesReader`.
  - The masks are copied from RE `host_masks.py`: thresholds + connected components, without pylidc and without a vessel mask (Q8).
  - The cache is `research_runs/_hosts/<lidc_id>/host.npz` + `host.json` (gitignored, AC-10).
- [x] **AC-2** (F5.2): Each host has a scanner fingerprint.
  - Evidence: `code/imaging/fingerprint.py:201` (`estimate`), `:191` (`plausibility`), `:222` (`load_or_estimate`, override). LIDC-0481: PSF σ zyx [0.61, 0.60, 0.60] mm, noise σ 56 HU, f50 0.34 cyc/mm → **PASS**; RE LIDC-0001 JSON loads via `--fingerprint`.
  - `imaging/fingerprint.py: estimate(host) -> {psf_sigma_mm_zyx, noise_sigma_hu, nps{freq_cyc_per_mm, values}, method}` is copied from RE `fingerprint.estimate`. It measures the air–skin edge MTF and takes the NPS from patches of air or uniform tissue.
  - It is cached as `fingerprint.json`. `--fingerprint <json>` overrides it.
  - **Plausibility check (logged; there is no RE reference for a Siemens host):**
    - in-plane PSF σ between 0.4 and 1.5 mm;
    - z PSF σ between 0.3·thickness and 1.0·thickness;
    - noise σ in air between 5 and 60 HU.
- [x] **AC-3** (F5.3): Each tumour gets a 3-D site that respects `lobe`.
  - Evidence: `code/imaging/place.py:19` (`_BAND`), `:22` (`Placer`), `:58` (`place`). All 12 sites inside the lung, correct side, correct z band (lower lobes 0.17–0.45, upper 0.51–0.69 of the lung's z extent).
  - `imaging/place.py: place_site(host, lobe, rng) -> (z, y, x)` picks a voxel inside the lung mask.
  - Side comes from the left/right lung component. Height comes from a z band: upper lobes = top half, lower lobes = bottom half, RML = right middle third.
  - Sibling daughters go to the nearest lung voxel about 3·r from the parent.
  - Sites at least 2·r apart are preferred.
- [x] **AC-4** (F5.4): Each non-calcified tumour is grown by the copied E engine.
  - Evidence: `code/imaging/growth.py:97` (hard = outside lung), `:112` (Ø 2 mm seed), `:266` (`grow`, +90 d, `max_days` 15000). Byte-identical PNGs/tiles.json across two runs. Solid 7 mm VDT 163 d (target 149 @ 8 mm, within 15 %); juxtapleural tiles flatten on the pleura (wall contacts 779–3823).
  - `imaging/growth.py: grow(host, site, params, seed_hex, frames=8) -> Growth(baseline, followup, frames[(day, role, state)], summary)`.
  - **Engine.** It copies `LungEngine` + `kt.py` + `Environment`. The lattice is 0.5 mm, and the masks are resampled with `scipy.ndimage.zoom` (order 0), so no SimpleITK is needed.
  - **Walls.** The only hard wall is outside-lung. There are **no soft barriers**: no vessel mask (Q8), and airways are out of scope.
  - **Parameters.** Per-type parameters are copied verbatim from `params_lung.json`.
  - **Seed and stop.** The seed is a Ø 2 mm ball. The baseline is the first day the equivalent diameter is ≥ `size_mm`. The follow-up is baseline + **90 d** (Q7).
  - `max_days` is 15000. The output is deterministic (byte-identical for identical inputs).
- [x] **AC-5** (F5.5): States are rendered into lesion HU with the copied F library.
  - Evidence: `code/imaging/lesion_fitted.py:184` (`render_lesion`), `:40`+`:135` (Q4 solid HU), `:335` (calcified `procedural_lesion_3d`); `diag.hu_source` = `f2.1-constant` / `f2.1-constant core + library rim` / `library` / `procedural-f2.1`.
  - `imaging/lesion_fitted.py: render_lesion(state, host_meta, site, type, margin, library, seeds) -> Lesion(F, LF, bbox, hu_core, diag)` copies RE `lesion_render.py`.
  - It supersamples the partial volume and applies the erf edge per type, SH lobulation, spicules for spiculated margins, and texture std per type.
  - **Solid core HU (Q4).** Solid lesions draw the core HU from N(+30, 30) instead of the library's −22. The type keeps the library's texture std and edge σ, and the tile records `diag.hu_source = "f2.1-constant"`.
  - Part-solid and GGO use the library unchanged.
  - Calcified tumours use the existing procedural `build_lesion` 3-D cube, with `renderer: procedural-3d` and no growth.
- [x] **AC-6** (F5.6): The lesion is inserted in 3-D with the host fingerprint.
  - Evidence: `code/imaging/insert3d.py:43` (`insert`, ROI only), `:77` (GGO α-blend), `:108` (`volume_pd_pct`). Final run: |volume error| ≤ 0.03 % on 8/9 grown tiles, +2.4 % on the spiculated one (spicule volume) — all < 3 %.
  - `imaging/insert3d.py: insert(host_roi, lesion, type, fingerprint, seed_hex) -> (hybrid_roi int16, mask, diag)` copies RE `insert.py` + `noise.py`.
  - It applies an additive delta and, for GGO, an α-blend so the underlying parenchyma shows through. There is no vessel max-rule (Q8).
  - It applies the 3-D PSF and the residual noise from the NPS.
  - It runs on a region of interest (ROI) of about r + 15 mm, never on the full volume.
  - **Volume check.** The rendered mask volume is within 3 % of the lattice volume, recorded as `diag.volume_pd_pct`.
- [x] **AC-7** (F5.7): The tile export keeps the contract.
  - Evidence: `code/imaging/build_tiles.py:304` (`full_<host>_<z>`), zoom write + `CohortTile` build in `_write_grown` (`:252`), `:383` (`_log_stale`). Log: `stale: tiles/full_slice.png` (file kept).
  - The tile is the axial slice through the lesion centroid, using `window_to_uint8` (lung window), resampled to isotropic in-plane spacing and cropped to 128 px.
  - **Overwrite (Q6).** The renderer **overwrites** `tiles/zoom_<shot>_<gen>.png` and `tiles.json` in the run dir.
  - **New files.** It adds `tiles/full_<host>_<z>.png`, one per distinct z, and `tiles/grow_<shot>_<gen>_<k>.png`.
  - **Stale files.** Files from the older renderer that the new one does not produce (e.g. `tiles/full_slice.png`) are **left in place** and listed in the log as `stale:`. They are not auto-deleted.
- [x] **AC-8** (F5.8): Pixel-growth frames are produced for **every** grown tile (Q5).
  - Evidence: `code/imaging/frames.py:63` (`render_tumor`), `:99` (frame supersample 2), `:39` (`_roi`, no black border); `code/imaging/build_tiles.py:317` (`grow_<shot>_<gen>_<k>`). 72 frames (9 grown × 8), calcified `growth: []`; identical background across frames.
  - There are K = 8 frames: 6 at log-spaced diameters from seed to baseline, then baseline, then follow-up.
  - Each frame is rendered and inserted on the same ROI with **the same noise seed**, so nothing flickers. The crop and window are fixed per tile.
  - `CohortTile.growth = [{k, day, diameter_mm, role, png_path}]`. Calcified tiles get `growth: []`.
- [x] **AC-9** (F5.9): The F3 page shows the new tiles with a growth player and stays backward-compatible.
  - Evidence: `code/f3_web/build_web.py:120` (frame embed), `:135` (provenance passthrough); `code/f3_web/web_template.html:261` (renderer chip), `:307` (F5 modal rows), `:331` (`setupGrowth` player). Headless Chromium: 0 console errors, 0 external requests, 3249 KB; play advances frames, scrub → `day 1176 · Ø 13.9 mm · follow-up`; old procedural run page: no player, no errors.
  - **Embedding.** `f3_web/build_web.py` embeds the growth frames and the per-z full slices, de-duplicating by path.
  - **Player.** The modal growth player has play/pause, a scrub slider and a "day N · Ø X mm · baseline/follow-up" label.
  - **Cards.** Each card has a `renderer` chip.
  - **Attribution.** The page states the host scanner ("LIDC-IDRI-0481 · SIEMENS SOMATOM Definition · public, CC BY 3.0").
  - **Size.** The page stays one HTML file of at most 6 MB.
  - **Backward compatibility.** Old F2-format runs render exactly as today.
- [x] **AC-10** (F5.10): Privacy and repo hygiene hold.
  - Evidence: `.gitignore:24-25` (repo root); `git status --ignored` shows `research_runs/_hosts/` as `!!`. Only 2-D PNG crops in `tiles/` and the page.
  - Host voxels, masks and hybrid ROIs live only in `research_runs/_hosts/` and `research_runs/*/_roi/`. Both are added to `.gitignore`, because `research_runs/` itself is not ignored today.
  - Only cropped 2-D PNG display exports of the public scan reach `tiles/` and the page.
  - The library and parameters are scalars only.
- [x] **AC-11** (F5.11): The honest label and provenance are recorded.
  - Evidence: `code/imaging/build_tiles.py:46` (`GROWN_HONEST_LABEL`), `:340` (attribution, "no Siemens involvement"), `:350` (`provenance`); `code/imaging/seedhash.py:28` (`tile_seeds`). Page search for the forbidden phrases: none.
  - **Label.** `tiles.json.honest_label` reads:
    - parameters = certified-quantum roll (job-level CHSH, with the sim/hardware label unchanged);
    - growth = classical cellular automaton (Kansal–Torquato layers + Pixel2Cancer pleura wall, VDT-calibrated *(verify)*);
    - image = classical 3-D insertion into a public Siemens LIDC CT with that scan's blur and noise;
    - the quantum bits seed growth and appearance as replayable provenance only.
  - **Provenance.**
    - Per tile: `seed_hex_geometry`, `seed_hex_appearance`, `host_id`.
    - Top level: `provenance{library_sha256, params_lung_sha256, ported_from: "RE@2609cbe", hosts[{host_id, series_uid, manufacturer, model, kernel, fingerprint}]}`.
  - **Forbidden wording.** Nothing says "more realistic because quantum", and nothing implies Siemens involvement. The text is "public Siemens-scanner case", not "Siemens data".
- [x] **AC-12** (F5.12): One CLI drives both renderers.
  - Evidence: `code/imaging/build_tiles.py:73` (`--renderer`), `:236` (`_compare_figure`), `:391` (`main`, exits `:408`=2, `:412`=3). Clean run **11:15 / 11:24 wall** (12 tiles × 8 frames, three 26 mm tumours). `--max-days 50` → 12 × `procedural-fallback`, exit 3; unknown host → exit 2 with fetch hint; bad run dir → exit 1.
  - Command: `python -m imaging.build_tiles --run research_runs/<f1_or_f4_run> [--renderer grown|procedural] [--host LIDC-IDRI-0481] [--frames 8] [--fingerprint …] [--compare] [--ct-source …]`.
  - **Defaults.** The default renderer is `grown` and the default host is `LIDC-IDRI-0481`. `--ct-source` applies to `procedural` only.
  - **Compare.** `--compare` also renders the procedural path in memory on the bundled JPEG and writes `compare_procedural_vs_grown.png`: 12 rows, old zoom beside new zoom.
  - **Runtime.** 12 tiles × 8 frames on a cached host takes at most 15 min of CPU. The host fetch and preparation time is logged separately.
  - **Exit codes:** 0 ok, 1 bad input, 2 host data missing (the message gives the `lidc_fetch` command), 3 at least one tile fell back.
  - **Fallback.** A failed tile is re-rendered procedurally with `renderer: procedural-fallback` and `diag.fallback_reason`. It is never dropped.

---

## 3. Out of Scope (Postponed)

- **A placement** (lungmask/TotalSegmentator lobes, the Ambrosini placement-class mix), plus **fissure walls** and **airway** barriers. → later RE→MVP sync (F6 candidate). F5 uses threshold masks and a z-band lobe proxy.
- **Vessel mask, vessel soft barrier, vessel max-rule.** Dropped by decision Q8. They can come back with A's TotalSegmentator vessels.
- **D quantum seed shape** (D-3 QCA occupancy) as the E seed, and **D-2 lineage driving growth**. These are a later step that needs its own claim-level review.
- **Non-stationary local NPS** (RE CR-F1) and the slice-sensitivity profile (CR-F2). F5 uses one global NPS per host.
- **Projection-domain insertion (#16), the NAEOTOM approximation (#17), G provenance record, H validation.**
- **Multiple hosts per cohort.** `--host` takes one id; round-robin over several Siemens hosts is a later change. Another Definition case is a one-flag swap: `LIDC-IDRI-0507` or `-0736`.
- **Deleting stale outputs, the bundled JPEG, or F4's `grow.py`/`web/progressionDEMO.html`.** These are left for the developer to remove (Q6). `grow.py` keeps working because its imports are updated by AC-0.
- **MPR/coronal views, a 3-D viewer, a real hardware run.**

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Package | `code/f2_imaging/` → **`code/imaging/`** (Q9: fold together, general name). The old modules keep their file names (`lesion.py`, `insert.py`, `ctsource.py`, `build_tiles.py`); the new modules sit next to them. |
| RE reuse | **Copy** (Q2) about 850 lines from RE `E_classical_growth/src/{engine,kt,lattice}.py`, `F_render/src/{host_masks,fingerprint,lesion_render,insert,noise,texture,params,lidc}.py`, and `shared/seedhash.py`. Each file gets the header `# copied from <RE path> @ 2609cbe`, and `imaging/PORTED.md` lists every change. The MVP never imports RE. |
| Host | `LIDC-IDRI-0481` (SIEMENS SOMATOM Definition, 259 images, 136 MB), fetched once from public TCIA into `~/data/LIDC-IDRI`. There are **no Siemens scans among the 47 local ones** (46 GE, 1 Toshiba), so the fetch is a required first step. If a Definition case fails the AC-2 plausibility check, the fallbacks are `-0507` and `-0736` (also Definition). |
| Masks | Threshold + connected components: lungs, left/right, body. No vessels. |
| Growth | Copied `LungEngine`: 0.5 mm lattice, per-type parameters from the copied `params_lung.json`, Ø 2 mm seed, pleura hard wall only, `max_days` 15000, follow-up +90 d. |
| Lesion | Copied `render_lesion` + copied `lesion_model_library.json` (solid / part-solid / ground-glass). Solid core HU is N(+30, 30) (Q4). Calcified uses procedural `build_lesion` in 3-D. |
| Insert | Copied additive-delta insert, GGO α-blend, 3-D PSF + NPS noise from the fingerprint, ROI only. |
| Seeds | `seedhash.rng(seed_hex, label)` (PCG64 over sha256). Geometry and appearance are separate streams, matching RE F's seed split. |
| Output | The same run dir; same-named files are overwritten, new files added, stale files listed but not deleted (Q6). |
| Web | `f3_web` is changed in place, with optional fields only. The player is plain JS image swapping, with no library and no network. |

**Conventions & Notes:**
* **Epic §3 is adopted.** The `Sampler` seam is unchanged. `imaging` reads only `cohort_params.json` + `quantum_run.json`, and copies `chsh_value`/`backend_name`/`job_id` as F2 did.
* **Epic wording.** The epic says "insert into a real LIDC/LUNA16 lung-CT slice". F5 inserts in 3-D and exports a slice. It is still image-domain, with no CT-physics simulation and no phantom anatomy.
* **Seed derivation.** Per tile:
  - `seed_hex_geometry = sha256(job_id or run_dir_name ‖ "geom" ‖ shot_index ‖ raw_bits[shot])`;
  - `seed_hex_appearance` is the same with `"app"`.
  - Each shot carries only about 9 quantum bits, so this seed is a replay key and provenance, not a strong random seed. It is written in the README, as F2.1 already does.
* **Frozen copy.** The copied code is frozen at RE `2609cbe`. Syncing later RE fixes is manual, and `PORTED.md` makes the drift visible.
* **Siemens wording (CLAUDE.md).** "A public LIDC case scanned on a Siemens SOMATOM Definition". Never "Siemens data" or "in collaboration with". The Definition is a 2005–2010-era dual-source scanner, not NAEOTOM; mark `(verify)` on any model-year claim.
* **Runtime guard.** A GGO >20 mm needs about 9,000 simulated days on an ~80³ lattice: about 8 min, rare (p ≈ 0.4 %). Hitting `max_days` triggers the fallback.

### Push-back on the request (kept from review)

1. **"Simple pixel growth" is model E shown frame by frame, not a new 2-D toy automaton.** E is reproduced (3/4 KT stages, B1–B4) and costs seconds per nodule. A new 2-D model would be a third model with no reproduced paper behind it.
2. **The 8-bit JPEG cannot host the RE render.** RE F's realism gain needs a calibrated 3-D HU volume.
3. **The GGO follow-up barely changes:** about +2.6 % in diameter at +90 d (VDT ≈ 813 d). That is shown honestly, not tuned to look dramatic.
4. **F4's `grow.py` strip is not growth.** The F5 player supersedes it for display. Do not show both as growth on one page.

---

## 5. Data Model (Additions/Modifications)

```text
[Existing Entity - Modifying]  code/common/datamodel.py
CohortTile
  ...(existing fields)...
  renderer            str | None   None/"procedural" | "grown+fitted" | "procedural-3d" | "procedural-fallback"
  host_id             str | None   e.g. "LIDC-IDRI-0481"
  slice_z             int | None   axial index of the exported slice
  growth              list[dict]   default []   [{k, day, diameter_mm, role: "growth"|"baseline"|"follow-up", png_path}]
  seed_hex_geometry   str | None
  seed_hex_appearance str | None
  diag                dict  default {}   {volume_pd_pct, vdt_d, day_baseline, sigma_ratio_in_out, hu_source, fallback_reason?}

[Existing Entity - Modifying]  tiles.json (top level)
  renderer_version    str          "imaging-grown@RE-2609cbe" (absent on old runs)
  provenance          dict         {library_sha256, params_lung_sha256, ported_from,
                                    hosts:[{host_id, series_uid, manufacturer, model, kernel, slice_thickness, fingerprint}]}

[New Entity — imaging-local, not a shared contract]
Host        research_runs/_hosts/<id>/host.npz + host.json   (gitignored)
  hu int16 (z,y,x) · lungs / left_right / body uint8 · spacing_zyx · origin_lps · series_uid · manufacturer · model · kernel
Fingerprint research_runs/_hosts/<id>/fingerprint.json
  psf_sigma_mm_zyx[3] · noise_sigma_hu · nps{freq_cyc_per_mm[], values[]} · method · plausibility{…}
Growth      in-memory; summary goes into CohortTile.diag
```

**Migration.** Every field is optional with a default, so old `tiles.json` files load unchanged. The epic's §4 has been updated with `Host`/`Fingerprint` and the `CohortTile.growth` extension.

---

## 6. File Plan (Concrete Changes)

All paths are relative to `QuantumPhantoms/`.

| Action | Path | Change / Note |
|--------|------|---------------|
| Rename | `code/f2_imaging/` → `code/imaging/` | `git mv`; the module names inside stay the same |
| Modify | `code/imaging/build_tiles.py` | imports → `imaging.*`; `--renderer grown|procedural` (default grown), `--host`, `--frames`, `--fingerprint`, `--compare`; the grown path orchestrates host → place → grow → render → insert → export; overwrite + `stale:` log; exit codes |
| Keep | `code/imaging/{lesion.py,insert.py,ctsource.py}` | the procedural path, unchanged; `lesion.build_lesion` is also used for calcified/fallback, and `insert.window_to_uint8`/`crop` are reused |
| New | `code/imaging/PORTED.md` | table: file ← RE source @ `2609cbe`, what was dropped (`shared`, SimpleITK in growth, vessels, pylidc) |
| New | `code/imaging/seedhash.py` | copy of `shared/seedhash.py` `derive_seed` + `rng`; `tile_seeds(run_id, tumor, raw_bits)` |
| New | `code/imaging/lidc_fetch.py` | copy of RE `lidc.py` `download_series`; NBIA `getSeries` lookup of the series UID by PatientID with a Siemens filter; CLI `python -m imaging.lidc_fetch <id>` |
| New | `code/imaging/host.py` | DICOM series → HU volume + DICOM tags (manufacturer, model, kernel, thickness); masks copied from RE `host_masks.py` minus vessels; npz cache |
| New | `code/imaging/fingerprint.py` | copy of RE `fingerprint.estimate`; plausibility check; JSON override |
| New | `code/imaging/place.py` | lobe → z-band/side site in the lung mask; sibling offset; separation |
| New | `code/imaging/growth.py` | copy of RE `engine.py` + `kt.py` + `Environment` (`lattice.py`); scipy resample; `grow()` |
| New | `code/imaging/lesion_fitted.py` | copy of RE `lesion_render.py` + `texture.py` + SH helpers (`lesion_fit.py:39-51`) + `RenderParams`; solid-HU rule (Q4) |
| New | `code/imaging/insert3d.py` | copy of RE `insert.py` + `noise.py`; ROI only; no vessel max-rule; volume diag |
| New | `code/imaging/frames.py` | 8 growth frames with a fixed noise seed, crop and window |
| New | `code/imaging/data/params_lung.json` | verbatim copy of RE `E_classical_growth/src/params_lung.json` + `_source` sha256 |
| New | `code/imaging/data/lesion_model_library.json` | verbatim copy of RE `F_render/library/lesion_model_library.json` + `_source` sha256 |
| Modify | `code/common/datamodel.py` | optional `CohortTile` fields from §5; `from_dict` tolerant of missing keys |
| Modify | `code/f3_web/build_web.py` | embed growth frames + per-z full slices (de-duplicated); pass renderer/growth/diag/provenance; host attribution |
| Modify | `code/f3_web/web_template.html` | modal growth player, renderer chip, new honest-label text; old runs unchanged |
| Modify | `code/f4_qalife/grow.py` | imports `f2_imaging.*` → `imaging.*` (lines 40-42), no other change |
| Modify | `code/f4_qalife/run_qalife.py` | docstring command → `python -m imaging.build_tiles` |
| Modify | `code/README.md` | F2 section → "imaging": both renderers, Siemens host fetch prerequisite, honest label, seed-entropy note, runtime |
| Modify | `plans/runlog-mvp-run.txt` | commands → `python -m imaging.build_tiles …` + `imaging.lidc_fetch` step |
| Modify | `../.gitignore` | add `QuantumPhantoms/research_runs/_hosts/` and `QuantumPhantoms/research_runs/*/_roi/` |
| Done (plan time) | `plans/epic-quantum-phantoms-mvp.md` | F5 row in §2, §4 entities, §7 graph (Q1) |

Analogue to mirror: the existing `code/f2_imaging/build_tiles.py`, for the CLI shape, the run-dir layout and how `tiles.json` is assembled.

---

## 7. Manual Verification (No Tests)

All commands run from `QuantumPhantoms/code/`.

- [x] **Setup:**
  - Run `python -m f1_quantum.run --backend aer --tiles 12 --pairs 2`, which gives `research_runs/<f1>`.
  - Before the rename, keep a copy of the current procedural output for AC-0: run `python -m f2_imaging.build_tiles --run research_runs/<f1>`, then `cp -r research_runs/<f1>/tiles /tmp/claude-…/scratchpad/tiles_before`.
- [x] **Verify AC-0:**
  - Run `python -m imaging.build_tiles --run research_runs/<f1> --renderer procedural`, then `diff -r` against `tiles_before`: no differences.
  - `grep -rn "f2_imaging" code/` returns nothing.
  - `python -m f4_qalife.grow --help` still runs.
- [x] **Verify AC-1:**
  - `python -m imaging.lidc_fetch LIDC-IDRI-0481` downloads about 136 MB.
  - The first `build_tiles` run logs `host LIDC-IDRI-0481: SIEMENS Definition, kernel …, thickness …, shape …`.
  - `research_runs/_hosts/LIDC-IDRI-0481/host.npz` exists and is **not** in `git status`.
  - `python -m imaging.lidc_fetch LIDC-IDRI-0001` prints a non-Siemens warning.
- [x] **Verify AC-2:** `fingerprint.json` exists, and the log shows `plausibility: PASS`. Re-running with `--fingerprint <json>` logs "fingerprint: override".
- [x] **Verify AC-3:** Open `tiles/full_*.png`. Every bbox lies inside the lung, and each lobe lands on the correct side and half. Sibling pairs are close but do not overlap.
- [x] **Verify AC-4:**
  - In `tiles.json` `diag`, the solid `vdt_d` is within ±15 % of 149 d, and `day_baseline` increases with size.
  - Run twice and `cmp` the `grow_*.png` files: they are byte-identical.
  - A nodule near the pleura flattens against the wall, with no lesion pixels outside the lung.
- [x] **Verify AC-5/AC-6:**
  - `volume_pd_pct` is within ±3 % for every grown tile.
  - Solid tiles look soft-tissue bright, not grey, and `hu_source` is `f2.1-constant`.
  - Spiculated tiles show spicules. GGO tiles are hazy, with parenchyma visible through them.
  - `sigma_ratio_in_out` is between 1.0 and 1.2.
- [x] **Verify AC-7:**
  - `zoom_*.png` files have a new mtime (overwritten).
  - The log lists `stale: tiles/full_slice.png`, and that file still exists.
  - `tiles.json` loads with `CohortTile.from_dict` in a REPL.
- [x] **Verify AC-8:** Every non-calcified tile has 8 frames. Flipping through them, the background is identical and only the lesion grows. Calcified tiles have `growth: []`.
- [x] **Verify AC-9:**
  - Run `python -m f3_web.build_web --run research_runs/<f1>`, then open `web/index.html` offline. The Network tab shows 0 external requests, and the file is at most 6 MB.
  - The player plays and scrubs.
  - The footer and modal name LIDC-IDRI-0481 / SIEMENS SOMATOM Definition / CC BY 3.0.
  - Rebuilding from an old F2-format run shows no player and no console errors.
- [x] **Verify AC-10:** `git status --ignored` shows `_hosts/` and `_roi/` as ignored.
- [x] **Verify AC-11:** The honest label is in the page footer and in `tiles.json`. Searching the page for "realistic because quantum", "quantum imaging" and "Siemens data" finds nothing.
- [x] **Verify AC-12:**
  - `--compare` writes `compare_procedural_vs_grown.png` with 12 rows.
  - `time` shows at most 15 min on a cached host.
  - The debug flag `--max-days 50` makes tiles fall back (`procedural-fallback` + reason) and exits with code 3.
  - Moving `~/data/LIDC-IDRI/LIDC-IDRI-0481` away temporarily gives exit code 2 with the fetch hint.
- [x] **Sampler-blind:** a PRNG run (`--sampler prng`) and an F4 QALife run both render, and their labels are unchanged ("classical baseline" / "simulator").

---

## 8. Open Questions

- [x] **Q1: Epic placement.** **Answer: add to the epic.** Done: F5 row in §2, entities in §4, edge in §7.
- [x] **Q2: Port or import.** **Answer: copy the files** (frozen at `2609cbe`, `PORTED.md`).
- [x] **Q3: Hosts.** **Answer: a Siemens scan.**
  - None of the 47 local scans is Siemens. TCIA lists 205 Siemens LIDC series.
  - The default is `LIDC-IDRI-0481` (SOMATOM Definition), with `-0507` and `-0736` as fallbacks. The fetch is part of AC-1.
- [x] **Q4: Solid HU.** **Answer: yes.** Solid core is N(+30, 30); the library is used for part-solid and GGO.
- [x] **Q5: Frames for all tiles.** **Answer: yes.**
- [x] **Q6: Output location.** **Answer: overwrite where possible, otherwise add.** Stale files are listed, not deleted; the developer removes them later.
- [x] **Q7: Follow-up horizon.** **Answer: +90 d.**
- [x] **Q8: Vessels.** **Answer: no.** No vessel mask, no soft barrier, no max-rule.
- [x] **Q9: Refactor depth.** **Answer: fold together under a general name.** `f2_imaging` becomes `imaging`, holding both renderers.

---

## 9. Post-Implementation Notes

**Built (2026-10-31, on `main`, uncommitted).** `code/f2_imaging/` → `code/imaging/` (git mv) with two renderers behind
one CLI. The `grown` default copies RE E + F (frozen @ `2609cbe`, see `code/imaging/PORTED.md`): Siemens LIDC host →
threshold masks → fingerprint → lobe-proxy site → E growth → F render → 3-D insert → tile + 8 growth frames. F3 gained
a renderer chip, F5 modal rows and a pixel-growth player; old runs render unchanged. Host `LIDC-IDRI-0481` fetched to
`~/data/LIDC-IDRI` (none of the 47 older local scans is Siemens).

**Deviations from a straight copy (all documented in `PORTED.md`), found while verifying on a real host:**
1. **Enclosed holes.** E grown in real lung HU leaves 1.5–8 % isolated unfilled voxels inside the mass (parenchyma
   levels with take-rates < 1). In RE's renderer each hole caps the interior signed distance at ~5 mm, so big or
   wide-edged nodules rendered as a grey partial-volume haze (26 mm tile: 673 vs 4793 voxels at F > 0.9). The render
   fills enclosed holes first (`diag.filled_holes_vox`, up to 933). RE never saw it: it only ran on uniform stubs —
   this confirms RE E's "stub-only runs" weak link. **Feed back to RE.**
2. **Volume-preserving edge.** RE's fixed σ²/r offset leaves +2…+6 % (deformation, wide σ) and ≈ +16 % (lobulated)
   volume error, *also in the original RE code* (checked side by side). The edge offset is now solved per lesion, so
   the rendered volume equals the grown volume (AC-6).
3. **σ reference shell.** Without a vessel mask (Q8) the residual-noise target included vessel edges (σ_out
   106–122 HU vs ~56 HU host noise) and over-noised lesions. The shell now keeps aerated voxels (A < −500 HU) — a
   σ-measurement stand-in for RE's `~vessels` only; growth and insert stay vessel-free.
4. **Speed ≈ 4×.** Deformation field and SH lobulation evaluated on the host grid and up-sampled, spicules in their
   own boxes, texture added after box integration, float32; growth-player frames at supersample 2 (tile stays 4).
   Random draws therefore differ from RE for the same seed.

**Numbers (final run `research_runs/qrng_aer_20261031-082938`, Aer roll, CHSH 2.861 simulator):** 9 grown + 3
calcified (procedural-3d), 72 frames, 11 full slices, 3249 KB page, 11:24 wall (three 26 mm tumours ≈ 2–3 min each;
a small-nodule PRNG cohort takes 4.4 min). σ ratio in/out after top-up: 0.69–1.19 on grown tiles — the plan's
1.0–1.2 is **not met for small lesions** (7 mm spiculated 0.69: the top-up is weighted by partial F; RE behaviour);
calcified procedural 1.4–1.8 (speckle counts as texture). Simulated VDT rises with size (163 d @ 7 mm, 250–350 d @
13 mm, 520–700 d @ 26 mm): Gompertz slow-down; p0 is calibrated at 8 mm only.

**Follow-ups for the developer:**
- `web/index.html` (git-tracked) now holds the F5 page built from the Aer run (3.2 MB, embeds cropped public
  LIDC-0481 slices, CC BY 3.0). Rebuild from the real-hardware run before showing it.
- `research_runs/qrng_aer_20261031-082938/` and `prng_prng_20261031-101821/` are new, untracked verification runs
  (`tiles/full_slice.png` in the first is a stale procedural file, kept per Q6).
- Calcified tiles look the same as before (procedural); lesions < 5 mm GGO are very faint at lung window (honest).
- Q8 consequence: tumours engulf vessels freely; the vessel max-rule is gone, but bright host vessels still win via
  `max(A′, …)`.
- `imaging.lidc_fetch` has no retry: one transient TCIA error was seen (the second call worked).
- Consider sending fixes 1–3 back to RE letters E/F (they are real RE findings, invisible on stubs).
