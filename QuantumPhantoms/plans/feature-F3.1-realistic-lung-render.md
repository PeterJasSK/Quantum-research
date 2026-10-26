# Feature F3.1 — Realistic lung render: real CT background + full-slice & marked-zoom views

**Epic:** [`epic-quantum-phantoms-mvp.md`](./epic-quantum-phantoms-mvp.md) (Approved) — **refinement of F3** (no dedicated epic §2 row; requested after the MVP shipped because the synthetic background read as a cartoon, not a scan).
**Feature ID:** F3.1
**Author:** Claude (Opus)
**Date:** 2026-10-26
**Status:** Complete

> **Technical constraints / core directive.** Spans **f2_imaging** (insertion/placement/outputs) and **f3_web** (page). Python + the existing imaging stack (numpy/scipy/Pillow); page stays **one self-contained static HTML, no backend, no CDN**. Uses a **bundled real public lung CT** so the demo looks like an actual scan by default. Honest-label and sampler-blind rules unchanged (epic §3/§6). **No automated tests — manual verification only.**
>
> **FEASIBILITY: confirmed (2026-10-26).** A clean real thorax CT (axial, lung window, Siemens SOMATOM Sensation 64, 1024×1024) was downloaded from Wikimedia Commons and a nodule was dropped into a lung field with matched noise + a marker — it reads as a realistic lung nodule (prototype verified visually). Asset: `data/ct_slices/thorax_ptrump16_cc-by-sa-4.0.jpg`, **CC BY-SA 4.0, author Ptrump16** — attribution + share-alike are **mandatory** (see §4).

---

## 1. Why (Step Goal)

**Before.** F3 renders tiles, but the default F2 background is a procedural noise field that looks like a cartoon ellipse, not a scan. The page does not convey "a tumor placed in a real lung" and shows only small 128² crops — there is no full-lung view and no marker.

**After.** The pipeline uses a **real, clean lung CT** as the default background. For each certified tumor it: places the nodule **inside an actual lung field**, inserts it realistically (matched noise), and produces **two coordinated views** — the **full lung slice** (the whole thorax, so you see where the tumor sits) and a **marked zoom** (cropped + a box/circle around the nodule). The web page leads with the **full picture of the lungs** (the first case marked), and every tile offers the full-slice + marked-zoom pair. The result reads like a real synthetic-cohort viewer: *quantum rolled this tumor, here it is sitting in a real lung, here is the zoom with it marked.*

This does not touch the biology claim — the lesion model and HU values are unchanged (Peter is not doing new biology here; we reuse the published rulebook from F1 and the lesion model from F2). F3.1 is purely about **realistic presentation**: real background + full/zoom/marked views.

---

## 2. Acceptance Criteria

- [x] **AC-1** (F3.1.1) — `code/f2_imaging/ctsource.py:25` (`BUNDLED_CT`), `:91` (`_read_bundled`), `:102` (`load_background`, `bundled` default); `build_tiles.py` default `--ct-source bundled`. Run printed `background: bundled_real`. A real public lung CT is bundled and used as the default background.
  → `data/ct_slices/thorax_ptrump16_cc-by-sa-4.0.jpg` (CC BY-SA 4.0, Ptrump16) is committed; `ctsource.py` gains a `bundled` source that loads it, and `--ct-source bundled` is the new **default** (replacing `synthetic`). `synthetic` and `<dir>` remain available.
- [x] **AC-2** (F3.1.2) — `code/f2_imaging/insert.py:24` (`lung_field_mask`), `:52` (`place_for_lobe(..., mask)`). Run reported `lung mask: yes`; screenshots show every nodule inside a lung field (none in mediastinum/outside). Each nodule is placed inside an actual lung field, lobe-biased.
  → `insert.py` computes a **lung-field mask** (dark parenchyma regions inside the body contour) and `place_for_lobe` samples a point within the mask in the lobe's region (upper/mid/lower × left/right); it never lands in mediastinum, bone, or outside the body. Falls back to the current region heuristic only if no mask is found.
- [x] **AC-3** (F3.1.3) — `code/f2_imaging/insert.py:71` (`insert_lesion` + `_match_noise`). Grid/zoom screenshots show nodules blending into real parenchyma near vessels, no hard paste edge; solid reads brighter than part-solid. The nodule is inserted into the real slice realistically.
  → `insert_lesion` blends the lesion into the real background with local-σ matched noise (already present; verified on the real JPG in the feasibility prototype). Solid/GGO/calcified contrast still reads correctly on the lung window.
- [x] **AC-4** (F3.1.4) — `code/f2_imaging/build_tiles.py:131` (shared `full_slice.png`), `:138-151` (per-tile `zoom_*.png` + normalised `bbox`); `CohortTile.full_png_path`/`bbox` at `code/common/datamodel.py:94-95`. Run wrote full-slice + 12 zoom PNGs; `tiles.json` carries `full_png_path` + `bbox` per tile. F2 emits a full-slice view + a marked zoom with the nodule's bbox.
  → `build_tiles.py` writes `tiles/full_<shot>_<gen>.png` (the whole lung slice with this nodule inserted) and `tiles/zoom_<shot>_<gen>.png` (crop centered on the nodule); each `CohortTile` records `full_png_path`, `png_path` (zoom), and `bbox` (`[x,y,w,h]` of the nodule in full-slice coords) so the marker can be drawn precisely.
- [x] **AC-5** (F3.1.5) — `code/f3_web/web_template.html:158` (`renderHero`) + `:145` (`markedHTML`). Screenshot: hero panel "TUMOR PLACED IN A REAL LUNG — FIRST CASE MARKED" shows the full lung with a green circle + "4mm ps" on the first case. The page leads with the full picture of the lungs, first case marked.
  → `web_template.html` shows a hero panel: the full lung slice with an overlaid marker (box/circle + label) on the **first** tile's nodule, captioned "tumor placed in a real lung — nodule marked".
- [x] **AC-6** (F3.1.6) — `code/f3_web/web_template.html:259` (`openModal`: full marked slice + zoom thumb side by side), marker via `markedHTML` SVG overlay from `bbox` (Siemens green). Modal screenshot confirms the full lung with the nodule circled + the zoom thumbnail + params. Each tile offers full-slice + marked-zoom.
  → the grid shows the marked zoom per tile; the detail modal shows the **full slice + marked zoom side by side**, the marker drawn from `bbox` (SVG/CSS overlay, so the underlying CT pixels stay clean). The marker uses the Siemens bright-green accent.
- [x] **AC-7** (F3.1.7) — `code/f2_imaging/ctsource.py:28` (`BUNDLED_ATTRIBUTION`) → `tiles.json` `ct_attribution` → `web_template.html:300` (footer credit). `data/ct_slices/NOTICE.md` records source/author/license/changes + share-alike. Screenshot footer: "CT background: Ptrump16, CC BY-SA 4.0 …". The CC BY-SA attribution is shown on the page and recorded in the repo.
  → the page footer credits "CT background: Ptrump16, CC BY-SA 4.0 (Wikimedia Commons), changes: synthetic lesion inserted"; a `data/ct_slices/NOTICE.md` records the source URL, author, license, and the share-alike obligation. (Honest-label line from F2 is preserved.)
- [x] **AC-8** (F3.1.8) — `code/f3_web/build_web.py:106-118` embeds everything inline (full slice once @512, zooms per tile); built `web/index.html` (388 KB) with **0 external URLs**. Real-CT tiles have no "synthetic bg" marker; honest-label footer intact; renders for QRNG + PRNG. Sampler-blindness, self-containment, and honesty preserved.
  → the real-CT tiles drop the "synthetic bg" marker; `build_web.py` still embeds everything inline (one self-contained file, no external requests); nothing claims a quantum image; works for both QRNG and PRNG runs.

---

## 3. Out of Scope (Postponed)

- **Multiple real patients / a real multi-slice volume** → later. F3.1 uses **one** bundled lung slice (all cohort nodules are shown in that same lung — a labeled dev simplification; a per-patient real volume is future work). LUNA16 `.mhd` volumes via `--ct-source <dir>` remain supported for richer data.
- **True 3D scroll-through / MPR views** → out of scope; F3.1 shows one axial slice (full) + zoom.
- **Automatic lung-lobe segmentation (anatomically exact lobe boundaries)** → out of scope; placement uses a lung-field mask + lobe region bias, not a segmentation model.
- **The quantum roll, lesion HU model, CHSH** → F1/F2 (unchanged). F3.1 changes presentation + placement + background only.
- **Signing/ledger/audit, F4 evolved lineages** → unchanged deferrals (epic §7).

---

## 4. Technical Decisions

Adopts epic §3 + the F2/F3 decisions verbatim. Feature-specific:

| Component | Choice / Implementation |
|---|---|
| Real CT asset | `data/ct_slices/thorax_ptrump16_cc-by-sa-4.0.jpg` (1024×1024, axial lung window, Siemens SOMATOM Sensation 64). **CC BY-SA 4.0, author Ptrump16, Wikimedia Commons.** Committed to the repo. |
| Default background | `--ct-source bundled` becomes the **default** (was `synthetic`). `synthetic` kept for a no-asset fallback; `<dir>` kept for LUNA16/`.npy`. |
| Lung-field mask | threshold the windowed slice for parenchyma (low intensity) **inside** the body contour via `scipy.ndimage` (fill body, remove air outside, remove airways/mediastinum by size) → boolean lung mask. Placement samples within it by lobe region. |
| Insertion | existing `insert_lesion` intensity path (JPG is non-HU) with matched local noise; HU path unchanged for `.mhd`/`.npy`. Verified realistic in the feasibility prototype. |
| Two views | `full_<id>.png` (whole slice, display-downscaled to 512 for embed weight) + `zoom_<id>.png` (crop, default 128, upscaled for display). |
| Marker | **not baked into pixels** — F2 stores `bbox`; F3 overlays an SVG/CSS box+circle+label in Siemens green, so the clean CT is preserved and the marker is crisp. |
| Hero | the first tile's full slice + marker, shown above the grid. |
| Attribution | visible page-footer credit + `data/ct_slices/NOTICE.md`; indicate changes made (lesion inserted) per CC BY-SA. |
| Embed weight | embed the full slice **once** (shared across tiles; all nodules live in the same lung image) + small per-tile zoom crops; keeps the single HTML reasonable. |

**Conventions & Notes:**
* Code stays in the package layout (`f2_imaging/`, `f3_web/`, `common/`); run via `python -m`.
* Share-alike: the page embeds a CC BY-SA image, so distributing the page carries the attribution; keep the footer credit intact. Colors-only Siemens theme already avoids trademarked assets.
* All cohort nodules sharing one lung slice is an honest dev simplification — label it ("nodules shown in a shared reference lung") so it is not mistaken for 12 distinct patients.

---

## 5. Data Model (Additions/Modifications)

Extends `CohortTile` (F2) — no new entity.

```text
[Modifying] common/datamodel.py — CohortTile: add
  full_png_path  str            # whole-slice view with this nodule
  bbox           list[int]      # [x, y, w, h] of the nodule in full-slice coords
  # (png_path continues to hold the zoom crop; background_source now includes "bundled_real")

[New artifact] data/ct_slices/thorax_ptrump16_cc-by-sa-4.0.jpg   (committed real CT)
[New artifact] data/ct_slices/NOTICE.md                          (source/author/license/changes)
```

`tiles.json` gains `full_png_path`/`bbox` per tile; its top-level keeps `honest_label` + `quantum_run` and adds `ct_attribution` (string) for the page footer.

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New (asset) | `QuantumPhantoms/data/ct_slices/thorax_ptrump16_cc-by-sa-4.0.jpg` | the bundled real lung CT (already downloaded). |
| New | `QuantumPhantoms/data/ct_slices/NOTICE.md` | source URL, author (Ptrump16), CC BY-SA 4.0, changes-made note. |
| Modify | `QuantumPhantoms/code/f2_imaging/ctsource.py` | add `bundled` source (loads the committed JPG, `background_source="bundled_real"`); make it the default; keep `synthetic`/dir. |
| Modify | `QuantumPhantoms/code/f2_imaging/insert.py` | add `lung_field_mask(slice)`; make `place_for_lobe` sample within the mask by lobe region (fallback to current heuristic). |
| Modify | `QuantumPhantoms/code/f2_imaging/build_tiles.py` | emit `full_<id>.png` + `zoom_<id>.png`, compute `bbox`, populate new `CohortTile` fields + `ct_attribution`; default `--ct-source bundled`. |
| Modify | `QuantumPhantoms/code/common/datamodel.py` | `CohortTile`: add `full_png_path`, `bbox`. |
| Modify | `QuantumPhantoms/code/f3_web/build_web.py` | embed full-slice (once) + zoom PNGs; pass `bbox` + `ct_attribution` into `COHORT_DATA`. |
| Modify | `QuantumPhantoms/code/f3_web/web_template.html` | hero full-lung panel (first case marked); detail modal shows full+zoom with SVG/CSS marker from `bbox`; footer CT attribution. |
| Modify | `QuantumPhantoms/code/README.md` | note the real-CT default, the asset + license, the full/zoom/marked views. |

---

## 7. Manual Verification (No Tests)

- [ ] **Verify AC-1 / AC-8:** `python -m f2_imaging.build_tiles --run research_runs/<f1_run>` (no `--ct-source`) → uses the bundled real lung; `tiles.json` `background_source` = `bundled_real`; `python -m f3_web.build_web --run <same>` → `web/index.html` with 0 external URLs, opens offline.
- [ ] **Verify AC-2 / AC-3:** open a few `full_<id>.png` → each nodule sits **inside a lung field** (not mediastinum/outside) and blends realistically (no hard paste edge); a solid nodule is brighter than a GGO.
- [ ] **Verify AC-4:** `tiles.json` has `full_png_path`, `png_path` (zoom), and a plausible `bbox` per tile; both PNG files exist.
- [ ] **Verify AC-5:** the page hero shows the full lungs with the **first** case marked and the caption.
- [ ] **Verify AC-6:** grid zooms show the nodule; clicking a tile shows full slice + marked zoom side by side with the green marker on both, aligned to the nodule.
- [ ] **Verify AC-7:** the footer credits Ptrump16 / CC BY-SA 4.0; `data/ct_slices/NOTICE.md` exists with source URL + license + changes note.
- [ ] **Edge case:** `--ct-source synthetic` still works (labeled dev); a lung with no detectable mask falls back to region placement without crashing; PRNG run renders too.
- [ ] **Visual sign-off (headless):** render `web/index.html` with playwright/chrome and screenshot the hero + a detail modal to confirm it reads as a real lung with a marked tumor.

---

## 8. Open Questions

All resolved — defaults accepted by Peter (2026-10-26). Locked decisions:

- [x] **Q1 (default background):** `--ct-source bundled` (the real lung) is the **default**, replacing `synthetic`; `synthetic` kept as explicit fallback.
- [x] **Q2 (one shared lung):** all cohort nodules shown in one **shared reference lung**, each at a lobe-appropriate spot, labeled "shared reference lung (dev)"; real multi-patient via `--ct-source <luna16 dir>`.
- [x] **Q3 (marker):** store `bbox` in `CohortTile`; draw the marker as an **SVG/CSS overlay** in F3 (clean CT underneath).
- [x] **Q4 (placement):** threshold-based **lung-field mask** (scipy) + lobe-region sampling; no segmentation model.
- [x] **Q5 (image weight):** embed the full slice **once**, downscaled to 512 for display, + small zoom crops (~1 MB page).
- [x] **Q6 (license):** keep the CC BY-SA 4.0 asset; visible footer credit + `data/ct_slices/NOTICE.md`; the credit must stay on any public sharing.

---

## 9. Post-Implementation Notes

**Built (2026-10-26).** 2 new files + 6 modified under `QuantumPhantoms/`, on `main`. **No new runtime dependency** (reuses PIL/scipy/numpy). The page now reads as a real scan.

New: `data/ct_slices/thorax_ptrump16_cc-by-sa-4.0.jpg` (committed real CT), `data/ct_slices/NOTICE.md`.
Modified: `code/f2_imaging/ctsource.py` (bundled source + `load_background`), `insert.py` (`lung_field_mask` + mask-aware `place_for_lobe`), `build_tiles.py` (shared-lung flow, full+zoom+bbox, default `bundled`), `common/datamodel.py` (`CohortTile.full_png_path`/`bbox`), `code/f3_web/build_web.py` (embed full once @512 + bbox + attribution), `web_template.html` (hero + modal full/zoom + SVG marker + footer credit), `code/README.md`.

**Decisions / deviations within the plan:**
- One **shared reference lung** holds all cohort nodules (Q2); `full_slice.png` is shared, each tile stores its own normalised `bbox`. The F3 marker is an **SVG overlay** (viewBox 0–100) from `bbox` — resolution-independent, so build_web can downscale the embedded full slice to 512 without breaking the marker.
- `lung_field_mask` = threshold dark → label → drop border-touching (outside air) + tiny specks → lungs; falls back to the region heuristic if empty.

**Verified (Aer run, headless chrome):** F2 printed `background: bundled_real`, `lung mask: yes`, full 1024² slice + 12 zoom PNGs; page 388 KB, 0 external URLs; hero shows the real lung with the first nodule circled; grid zooms show nodules in real parenchyma; modal shows full marked slice + zoom + params + CHSH bar; footer carries the CC BY-SA credit; honest label notes the shared reference lung.

**Follow-ups for the developer:**
- CC BY-SA 4.0: keep the footer credit on any public sharing; `NOTICE.md` has the obligation. Swap to a CC0 asset (update NOTICE) to drop share-alike.
- For a true multi-patient demo, use `--ct-source <luna16 dir>` (one slice per patient is still a later feature; today all nodules share one lung).
- Type-mix on the demo page reflects whatever that F1 run decoded (small sample can skew, e.g. 92% solid) — not a bug.
- The earlier F1/F2/F3 plans still cite pre-restructure flat paths in their AC evidence (historical).
