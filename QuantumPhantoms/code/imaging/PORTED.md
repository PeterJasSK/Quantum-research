# Code copied from the reverse-engineering (RE) pipeline (F5)

The `grown` renderer uses a **frozen copy** of part of RE letters E and F, taken at commit `2609cbe`
(F5 plan Q2). The MVP never imports the RE tree. Fixes made in RE do **not** reach this copy
automatically: to sync, diff the RE source against the file here and re-apply the changes listed below.

RE root: `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`.

| MVP file | Copied from (RE @ 2609cbe) | Kept | Changed / dropped |
|---|---|---|---|
| `seedhash.py` | `shared/seedhash.py` | `derive_seed`, `rng` | added `tile_seeds` (per-tile seeds from the run key + shot bits); dropped `code_hash`, `git_state` |
| `lidc_fetch.py` | `F_render/src/lidc.py` | `LIDC_ROOT`, `NBIA`, `download_series`, `series_dir` | NBIA `getSeries` lookup by PatientID, Siemens check, `find_local_series`; dropped pylidc `select_scans`/`load_scan`/`nodule_masks` |
| `host.py` | `F_render/src/host_masks.py` | `_largest`, `_fill_slices`, `make_masks` (thresholds unchanged) | no vessel mask (plan Q8), no lobes, no `free_site`; lungs returned as 0/1 + separate `left_right`; SimpleITK series reader instead of pylidc; npz cache in `research_runs/_hosts/` |
| `noise.py` | `F_render/src/noise.py` | `detrend2`, `nps2d`, `radial`, `nps_from_radial`, `sigma_of`, `noise_slices` | dropped `patch_noise_2d` (local NPS, CR-F1) |
| `fingerprint.py` | `F_render/src/fingerprint.py` | `_strip_esf`, `_lsf_mtf`, `_boundary_points`, `estimate_psf`, `estimate_nps`, JSON mapping of `write()` | dropped `estimate_sigma_map` (unused by the insert), NIfTI/npz/contract writing; added `noise_sigma_hu`, `plausibility`, JSON cache, `--fingerprint` override |
| `growth.py` | `E_classical_growth/src/engine.py`, `kt.py`, `lattice.py` | `LungParams`, `LungEngine` (verbatim), KT layer functions, `doubling_time`, `Environment`, the parenchyma-level rule of `lattice.build` | lattice built with scipy `map_coordinates` (no SimpleITK); hard wall = outside the lung mask only (no lobes/fissures), no soft barriers (Q8); `run()` replaced by `grow()` with log-spaced diameter snapshots; seed: Ø 2 mm ball by default, D-SCALE quantum seed shape when `<run>/dscale/seed_shapes.npz` is present (`grow(..., seed_mask=)`, `seed_from_mask`; a seed larger than half the rolled diameter is shrunk by `fit_seed`, shape kept, summary `seed_scaled`; ball fallback if the mask lies outside the lung; summary `seed_source` / `seed_cells` only when a mask is given, so the ball path is byte-identical to F5); `max_days` 15000 |
| `lesion_fitted.py` | `F_render/src/lesion_render.py`, `lesion_fit.py` (SH helpers), `texture.py`, `params.py` | `render_lesion` (structure and seed labels kept), `real_sh`, `lm_list`, `to_sph`, `texture_field`, `mass_effect`, `RenderParams` (lung defaults) | capsule fields dropped (off for lungs); `load_library` replaces the solid class HU (−22) with N(+30, 30) (plan Q4; also sets the part-solid solid core); added `procedural_lesion_3d` (calcified / fallback). **Enclosed holes:** E grown in real lung HU leaves 1.5–8 % isolated unfilled lattice voxels inside the mass (parenchyma levels with take-rates < 1); RE only ever ran on uniform stub phantoms, so this never showed there. Each hole is "outside" for the distance transform and caps the interior depth at ~5 mm (a hazy core, worst with a wide edge σ), so `render_lesion` fills enclosed holes before sampling (`diag.filled_holes_vox`). **Volume:** the erf edge offset is solved (`_volume_preserving_shift`) so the rendered volume equals the grown lattice volume — RE's fixed σ²/r leaves +2…+6 % (deformation, large σ) and ≈ +16 % (lobulated); needed for AC-6. **Speed (≈ 4×, same geometry up to interpolation):** deformation field and SH lobulation evaluated on the host grid and linearly up-sampled; each spicule evaluated in its own bounding box; texture added after box integration as tex·F; float32 sub-grid. The random draws therefore differ from RE for the same seed. |
| `insert3d.py` | `F_render/src/insert.py` | `_grow`, `_local_sigma`, `insert` composition | no vessel argument (Q8, background weight = lung & no lesion); runs on a ROI copy; adds `volume_pd_pct` |
| `data/params_lung.json` | `E_classical_growth/src/params_lung.json` | verbatim | `_source` block with the RE sha256 |
| `data/lesion_model_library.json` | `F_render/library/lesion_model_library.json` | verbatim | `_source` block with the RE sha256 |

MVP-only (not copied): `place.py` (lobe proxy placement), `frames.py` (per-tumour orchestration +
growth frames), the `grown` path in `build_tiles.py`.
