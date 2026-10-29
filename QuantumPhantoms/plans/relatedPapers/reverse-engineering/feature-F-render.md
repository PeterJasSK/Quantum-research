# Feature F — Render into CT: realistic, scanner-matched 3-D lesion insertion

**Epic:** [`epic-reverse-engineering.md`](./epic-reverse-engineering.md) (Approved, 2026-10-28). F is a wave-1 letter (epic §7), built in its own worktree `../qp-re-F` on branch `re-F`.
**Feature ID:** F
**Author:** Claude (Opus)
**Date:** 2026-10-28
**Status:** Complete (implemented 2026-10-29 in worktree `../qp-re-F`, branch `re-F`; uncommitted at hand-back)

> **Technical constraints / core directive.** Python 3.13 (conda base, `/home/peter/anaconda3/bin/python`), cwd = `RE/` (`QuantumPhantoms/plans/relatedPapers/reverse-engineering/`), run as `python -m F_render.…`. Installed and used: numpy 2.4, scipy 1.15, scikit-image 0.25, SimpleITK 2.5.6, matplotlib 3.10, jsonschema. **To install (Q2):** `pydicom`, `pylidc`, `gecatsim` (XCIST). F is a **classical** stage: no qiskit import, no claim level (`n/a`). **Fully 3-D**: every intermediate is a 3-D volume on the host grid or a 3-D NPZ; 2-D PNG slices exist only as the final export into `F_render/figures/`. Imports only `shared` (frozen v1.0.0); never another letter, never the MVP (`QuantumPhantoms/code/f2_imaging/` is explicitly not reused). Every PRNG is `shared.seedhash.rng(seed_hex, "F.<label>")` from the certificate's extracted seed. Privacy-by-construction: only fitted parameters leave LIDC. Writes only inside `F_render/` and this file. **No automated tests; manual verification + per-target paper reproduction only.**

---

## 1. Why (Step Goal)

**Before.** `F_render/` is a W skeleton: README with Purpose/Inputs/Outputs, `status.json` with #13–#17 all `listed`, five empty dossiers, empty `src/` and `repro/`. The only "rendered" tumor in the project is W's stub: a hard 4 mm sphere at 30 HU pasted into a noise-free phantom (`shared/stubs/hybrid_volume/`, method "STUB: hard sphere replacement (no PSF, no noise)"). It has no partial volume, no edge profile, no blur, no noise matching, and its HU is a placeholder. Any reader would see it is fake, and H has nothing realistic to validate.

**After.** F turns a 3-D cell lattice (E's `growth_trajectory`) into a lesion that looks like it was **scanned by the host scanner**, built from five reverse-engineered methods:
- **#14 Lesion library** — shape + edge-profile + HU parameters fitted per nodule type (solid / part-solid / ground-glass) on LIDC, written as `lesion_model_library.json`. Only parameters leave the patient data.
- **#15 Scanner fingerprint** — the host scan's own MTF (air–skin edge), 3-D PSF σ, NPS and local σ map, written as `scanner_fingerprint.json` + `sigma_map.nii.gz`.
- **#13 SyntheticTumors recipe** — texture (smoothed Gaussian noise), shape deformation, mass effect and capsule, adapted to lungs.
- **Image-domain insertion** — cell states → tissue-class HU on a ≥ 4× supersampled grid → box-integrated partial volume on the host grid → additive delta (lesion − local background) blurred by the 3-D PSF → vessel max-rule, ground-glass α-blend, lung-mask clip → residual NPS-shaped noise inside dense lesion. Output: `hybrid_volume.json` + `host_ct` / `hybrid_ct` / `lesion_mask` NIfTI, seeded and replayable.
- **#16 / #17 Siemens upgrade path** — a projection-domain insertion rebuilt on XCIST that reproduces the Robins/Duke image-vs-projection volume agreement (< 3 %), plus a NAEOTOM Alpha XCIST configuration from McCabe's published parameters.

Each target ends with its dossier dissected, one published number reproduced in `repro/`, and its `status.json` row advanced. H (wave 2) then validates real hybrids instead of a hard sphere, and G signs a `hybrid_volume_sha256` that means something.

---

## 2. Acceptance Criteria

**Dissection and reproduction (every target)**

- [x] **AC-1** (F.1): All five dossiers are dissected.
  → `F_render/dossiers/{13-synthetic-tumors,14-lesion-model-fitting,15-scanner-fingerprint,16-xcist-projection-insertion,17-naeotom-alpha-params}.md` fill all 8 fixed sections (Concept, Equations, Parameters, Paper's claimed result, Our reproduction, Adaptation, Verdict, What to reuse next). Equations as Unicode or fenced `text` (no MathJax, W Q7). Every claimed result quotes the paper's number with page/figure reference. Where a source PDF is missing locally, the dossier says so (see Q4).
- [x] **AC-2** (F.2): Each target reproduces one published number or figure in `F_render/repro/`, before adapting.
  → One script per target: `repro/r13_synthetic_tumors.py`, `repro/r14_lesion_fit.py`, `repro/r15_fingerprint.py`, `repro/r16_projection_vs_image.py`, `repro/r17_naeotom_spectrum.py`. Each writes a run dir via `shared.runrecord.start_run("F_render", "repro-<NN>")`, a figure in `F_render/figures/`, and fills `status.json → targets[].reproduced {quantity, paper_value, our_value, unit, agreement, figure}`. The specific number per target is fixed in Q5; the F-row headline is **Robins/Duke volume agreement < 3 %** (#16).

**#14 Lesion-model library**

- [x] **AC-3** (F.3): `python -m F_render.src.lesion_fit --lidc <N scans> --out F_render/library/lesion_model_library.json` fits a per-type parameter library from LIDC nodules and the file validates.
  → For each LIDC nodule (pylidc consensus mask at 50 % agreement, radiologist `texture` rating mapped 1–2 → ground-glass, 3–4 → part-solid, 5 → solid):
  - shape: low-order real spherical-harmonic radius expansion r(θ, φ) (Ambrosini [F01]) → `shape_params` = per-type mean/std of normalised coefficients ℓ ≤ 4, sphericity, volume-equivalent diameter range;
  - edge: radial HU profile fitted with an erf/sigmoid model (Solomon–Samei form; `edge_profile {model: "erf", params {width_mm_mean, width_mm_std, …}}`);
  - HU: interior mean/std per type, ground-glass/solid split at the [F06] thresholds (−400 / −160 HU).

  `n_fitted > 0` for every type present. `python -m shared.validate F_render/library/lesion_model_library.json` → OK. The JSON contains only scalars; the fitter never writes a voxel array to disk (privacy check in §7).

**#15 Scanner fingerprint**

- [x] **AC-4** (F.4): `python -m F_render.src.fingerprint --host-ct <nii> --body <mask nii> --out <dir>` writes `scanner_fingerprint.json` + `sigma_map.nii.gz` that validate.
  → Estimator:
  - **MTF (Sanders 2016):** sample edge-spread functions along outward normals of the body (air–skin) surface on axial planes, align on sub-voxel edge position, average → ESF → differentiate → LSF → |FFT| → in-plane MTF (`mtf.freq_cyc_per_mm`, `values`), f50 recorded in the run notes;
  - **3-D PSF:** in-plane Gaussian σ fitted to the LSF; z σ from the slice-sensitivity estimate (LSF across the diaphragm/lung-apex boundary along z, fallback: slice thickness / 2.355 from DICOM, recorded which) → `psf_sigma_mm_zyx`;
  - **NPS:** radially averaged 2-D NPS from detrended uniform ROIs (soft tissue, body interior away from edges), global curve → `nps`;
  - **σ map:** local std of the high-pass residual in a sliding 3-D window, smoothed, float32 HU, on the host grid → `sigma_map.nii.gz`.
- [x] **AC-5** (F.4): The estimator recovers known ground truth on a controlled phantom.
  → `repro/r15_fingerprint.py --selfcheck` blurs the noise-free stub phantom (`shared/stubs/anatomy_masks/host_ct.nii.gz`) with a known 3-D Gaussian PSF and adds NPS-shaped noise of known σ; the estimator returns PSF σ (in-plane and z) and σ within **10 %** and NPS peak frequency within one frequency bin (tolerances are Q7 proposals).

**#13 SyntheticTumors recipe (lung adaptation)**

- [x] **AC-6** (F.5): `F_render/src/texture.py` implements the [H01] generation steps as 3-D functions, each seeded by its own label:
  - `texture_field(shape, sigma_vox, hu_mean, hu_std, rng)` — Gaussian white noise → Gaussian smoothing → rescale to the library HU (`F.texture`);
  - `deform_shape(mask, alpha, sigma, rng)` — elastic deformation of the lattice outline (`F.deform`);
  - `mass_effect(host, center, radius, strength)` — radial displacement of the surrounding host intensities, limited to the lung mask;
  - `capsule(mask, thickness_mm, delta_hu)` — optional rim enhancement, off by default for lungs (H01 is liver; the dossier records the adaptation).

**Render and insert (the F engine)**

- [x] **AC-7** (F.6): Cell lattice → partial-volume lesion on the host grid.
  → `F_render/src/lesion_render.py`: read the trajectory snapshot NPZ (`state` uint8, 0.5 mm in the stub), place it via `origin_mm_lps` + `spacing_mm_xyz`, map states to tissue classes (1 proliferating / 2 dormant → solid or ground-glass HU per the draw's `type`; 3 necrotic → library-derived necrotic HU, documented in the dossier), apply the library edge profile and texture on a supersampled grid of **4× per host axis**, then box-integrate (mean over each 4×4×4 block) onto the host grid. Never point-sampled. Margin `spiculated` adds thin radial spicules seeded by `F.spiculation`; `lobulated` uses the library SH coefficients.
- [x] **AC-8** (F.6): Additive-delta insertion with physics-consistent composition.
  → `F_render/src/insert.py`:
  1. local background = host HU in the lesion support, inpainted by a large-kernel median over non-lesion lung;
  2. delta = lesion − background (partial-volume weighted);
  3. delta blurred by the 3-D Gaussian PSF from the fingerprint (only the delta is blurred, the host keeps its real resolution and noise);
  4. vessel max-rule: where the host is brighter than the lesion (vessels), keep the host ([F01]);
  5. ground-glass: α-blend so vessels show through;
  6. juxtapleural: delta clipped to the lung mask;
  7. residual noise: inside the solid part, add NPS-filtered white noise (`F.noise`, [F05] patch method) scaled so local σ inside the lesion matches the σ map outside;
  8. clip to int16 [−1024, 3071].

  Outside the PSF support (3 σ beyond the lesion mask dilation) `hybrid_ct == host_ct` voxel-for-voxel.
- [x] **AC-9** (F.6): One command renders and writes a contract-valid hybrid.
  → `python -m F_render.src.render --trajectory <growth_trajectory.json> --step <int> --masks <anatomy_masks.json> --sites <sites.json> --draw <tumor_draw.json> --certificate <certificate.json> --library <lesion_model_library.json> --fingerprint <scanner_fingerprint.json> --out <dir>` writes `hybrid_volume.json` + `host_ct.nii.gz` + `hybrid_ct.nii.gz` + `lesion_mask.nii.gz` (all on the host grid, `check_same_grid` clean), with `insertion {method: "image-domain additive delta v1", params {...every knob incl. supersample, psf, alpha, noise}}`, `seed_hex`, `fingerprint_ref`, `trajectory_ref`, `snapshot_step`, and `upstream[]` hashes of every input. `python -m shared.validate <out>/hybrid_volume.json` → OK. Defaults point at the `shared/stubs/` files, so `python -m F_render.src.render --out F_render/runs/…` works with no arguments.
- [x] **AC-10** (F.7): Seed chain and replay.
  → The seed is the certificate's `extracted_seed_hex`. A `fail` certificate (null seed) → the command exits non-zero with `certificate status fail: draw rejected (epic decision 6)` and writes nothing. Re-running with the same inputs produces byte-identical `hybrid_ct.nii.gz` (same sha256); changing only the seed changes texture/noise but not the lesion mask. Baseline and follow-up are rendered from the two `role` snapshots with the same seed, giving a longitudinal pair.
- [x] **AC-11** (F.7): Every run writes `F_render/runs/<ts>-<tag>/run.json` through `shared.runrecord` with `seed_hex`, inputs and outputs (contract + sha256), code hash, git state; `sim: null` (classical).

**#16 / #17 Siemens upgrade path**

- [x] **AC-12** (F.8): Projection-domain insertion rebuilt on XCIST and compared to image-domain.
  → `F_render/src/projection_insert.py`: with `gecatsim`, define a third-generation fan/helical geometry close to a Siemens scanner (Definition-class; parameters cited in the dossier), forward-project a host phantom and the lesion separately, add the lesion line integrals to the host projections, reconstruct with XCIST FBP. `repro/r16_projection_vs_image.py` inserts the same lesion by image domain (AC-8 path, PSF from the XCIST reconstruction's measured MTF) and by projection domain, segments both at the same threshold and reports volume difference. Target: **< 3 %** (Robins/Duke [F02]). Host = synthetic XCIST phantom in this feature; Mayo raw data per Q3.
- [x] **AC-13** (F.8): NAEOTOM Alpha approximation as XCIST configuration.
  → `F_render/xcist/naeotom_alpha.cfg` (+ `F_render/xcist/README.md`): only the published spectra/kVp, energy thresholds, detector pixel pitch, noise-correlation parameters from McCabe [F04], each line commented with the paper table/figure. Clearly labelled "approximation from published parameters, not DukeSim". `repro/r17_naeotom_spectrum.py` loads it in XCIST and reproduces one published curve or number (Q5).

**Export, docs, status**

- [x] **AC-14** (F.9): 2-D slices only at the end.
  → `F_render/src/export_slices.py` writes PNG (lung window W1500/L−600 and mediastinal W400/L40) axial/coronal/sagittal through the lesion centre for host, hybrid and difference, into `F_render/figures/`. No PNG is ever read back as input.
- [x] **AC-15** (F.9): Letter definition of done (epic §3).
  → `F_render/README.md`: "How to run" (every command above), "Reproduced result vs. paper" (table per target), honesty notes (classical, approximations, Siemens-cases-only rule, what is image-domain vs projection-domain), "Contract change requests" (Q6). `F_render/status.json` advances each target (`dissected` → `reproduced` → `adapted`; `integrated` is INT's), `claim_level: "n/a"`, `sim_mode: "n/a"`. `python -m shared.validate --status` → OK. `python -m shared.site.build` may be run for preview, but `index.html` / `site/` are **not committed**.
- [x] **AC-16** (F.9): Ownership respected.
  → `git diff --name-only main...re-F` lists only paths under `F_render/` and `feature-F-render.md`.

---

## 3. Out of Scope (Postponed)

- Real placement masks (lungmask / TotalSegmentator) and real `sites.json` → **A**. F uses the stub masks, plus an F-local threshold lung/body mask on LIDC hosts (Q8), replaced in **INT**.
- Real growth trajectories → **E**. F renders the stub `growth_trajectory` (33³ lattice @ 0.5 mm) until INT.
- Real certified seed → **C**. F uses the stub certificate seed.
- Signing the hybrid, DICOM tag, ledger → **G**.
- Realism validation (PyRadiomics distributions, visual Turing test, train-synthetic/test-real, NPS-vs-LIDC statistics at cohort scale) → **H**. F only checks its own physics (AC-5, §7 checks).
- Projection-domain insertion into **real Mayo Siemens raw data** at scale and DICOM re-export → after F's synthetic reproduction; scope per Q3, otherwise **INT / future work**.
- Learned refiners (DiffTumor, MAISI, LDM) → ablation arm only, not built here (epic §6 privacy).
- Large-cohort performance (Poleszczuk-style data structures) → **E** #12.
- Contract amendments (local NPS patches, PSF z-profile) → recorded as requests, applied in **INT**.
- Committing `index.html` / `site/` → **INT**.

---

## 4. Technical Decisions

Epic §3 adopted as-is (3-D only, MVP isolation, file contracts, ownership rules, seed chain, logging, no tests). W's frozen volume conventions apply: LPS, numpy (z, y, x), JSON vectors xyz, int16 HU, uint8 masks, `shared.volumes` as the only NIfTI I/O.

| Component | Choice / Implementation |
|---|---|
| Volume I/O | `shared.volumes.read_volume / write_volume / check_same_grid / save_npz / load_npz` only |
| Seeding | `shared.seedhash.rng(seed_hex, label)` with labels `F.texture`, `F.deform`, `F.spiculation`, `F.noise`, `F.xcist` |
| LIDC access | `pylidc` (annotations, consensus masks, `texture` rating) + `pydicom`; data outside the repo (Q1) |
| Shape model | real spherical harmonics via `scipy.special.sph_harm_y`, ℓ ≤ 4, least-squares on surface points |
| Edge model | erf radial profile, `scipy.optimize.curve_fit` |
| Partial volume | supersample 4× per host axis, block-mean down (`reshape(...).mean`) |
| PSF | separable 3-D Gaussian (`scipy.ndimage.gaussian_filter`, σ in voxels from `psf_sigma_mm_zyx / spacing`) |
| MTF | ESF along body-surface normals (`scipy.ndimage.map_coordinates`, order 1), 0.1 px binning, Hann-windowed FFT |
| NPS / noise | detrended ROI periodograms; noise synthesis = white noise × √NPS in Fourier space, patch-wise with overlap-add windows ([F05]) |
| Background inpaint | median filter over lung voxels with lesion support masked out |
| Projection domain | XCIST (`gecatsim`) forward projector + FBP; F-local geometry/config files in `F_render/xcist/` |
| Figures | matplotlib 3.10, PNG, from 3-D arrays at export only |
| CLI | `argparse` modules run as `python -m F_render.src.<name>`; defaults resolve to `shared/stubs/` |

**Conventions & Notes:**
- `F_render/src/` modules are pure functions + a thin `main()`; repro scripts import from `F_render.src`, never the reverse.
- Every tunable lives in one dataclass `RenderParams` (`F_render/src/params.py`); its `asdict()` is written verbatim into `hybrid_volume.insertion.params` so the receipt can replay it.
- Inputs are always validated with `shared.validate.validate_file` before use; outputs are validated before the run is finished.
- Paths in output manifests are relative to the manifest, `/` separators, with sha256 (W convention).
- Licences: H01 SyntheticTumors code may be read only within its licence (dossier records it); Mayo / DukeSim never decompiled — rebuilt from papers only.
- **Note for the epic:** F needs `pydicom`, `pylidc`, `gecatsim` (§3 lists them in the stack but W installed none). Recorded in `F_render/requirements.txt`, not in `shared/requirements.txt` (frozen).
- **Plan location:** `RE/feature-F-render.md` (epic §3 layout, W Q2 precedent), not `tasks/plans/`.

---

## 5. Data Model (Additions/Modifications)

No shared contract is changed. F produces the three frozen contracts it owns (`lesion_model_library`, `scanner_fingerprint`, `hybrid_volume`) and adds F-local files that are referenced only from `params{}` objects.

```text
[Produced — frozen contract, real values replace stub placeholders]
LesionModelLibrary   F_render/library/lesion_model_library.json
  source "LIDC fitted parameters (no voxels)"
  types.{solid|part-solid|ground-glass}:
    shape_params  {sphericity_mean, sphericity_std, d_eq_mm_min, d_eq_mm_max,
                   sh_l1..sh_l4_power_mean, sh_l1..sh_l4_power_std}      (numbers only)
    edge_profile  {model "erf", params {width_mm_mean, width_mm_std, hu_bg_offset}}
    hu            {mean, std}
    n_fitted      int > 0

ScannerFingerprint   <host>/scanner_fingerprint.json + sigma_map.nii.gz (float32 HU, host grid)
  mtf {freq_cyc_per_mm[], values[]}, psf_sigma_mm_zyx[3], nps {freq_cyc_per_mm[], values[]}

HybridVolume         <run>/hybrid_volume.json + host_ct/hybrid_ct/lesion_mask .nii.gz
  insertion {method "image-domain additive delta v1" | "projection-domain XCIST v1",
             params {RenderParams as dict, local_nps_ref? {path, sha256}}}

[New — F-local, not a contract]
local_nps.npz        alongside scanner_fingerprint.json
  nps_patches  float32 (n_patch, n_freq)   radially averaged NPS per patch
  patch_centers_zyx int32 (n_patch, 3)
  freq_cyc_per_mm float64 (n_freq)
  spacing_mm_xyz float64 (3)
  (workaround for contract change request CR-F1)

F_render/xcist/*.cfg  XCIST geometry / NAEOTOM approximation configs (text, cited per line)
```

**Contract change requests (to be written into `F_render/README.md`):**
- **CR-F1** `scanner_fingerprint`: add optional `local_nps {path, sha256}` (NPZ above). Workaround: referenced from `hybrid_volume.insertion.params.local_nps_ref`.
- **CR-F2** `scanner_fingerprint`: add optional `ssp {z_mm[], values[]}` (slice-sensitivity profile) so the z PSF is not reduced to one σ. Workaround: z σ only, method recorded in run notes.

---

## 6. File Plan (Concrete Changes)

`RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`. All work in worktree `../qp-re-F`, branch `re-F`.

**Source (`F_render/src/`)**

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/F_render/src/params.py` | `RenderParams` dataclass (supersample=4, psf from fingerprint, ggo_alpha, spicule count/length, noise on/off, capsule off) |
| New | `RE/F_render/src/io.py` | load + validate inputs (trajectory snapshot, masks, sites, draw, certificate, library, fingerprint); certificate `fail` guard (AC-10) |
| New | `RE/F_render/src/lidc.py` | pylidc scan/nodule iteration, consensus mask, texture → type mapping, DICOM → HU volume in memory (never written) |
| New | `RE/F_render/src/lesion_fit.py` | #14: SH shape fit, erf edge fit, HU stats, library writer + CLI (AC-3) |
| New | `RE/F_render/src/fingerprint.py` | #15: MTF from air–skin edge, PSF σ, NPS, σ map, local NPS NPZ + CLI (AC-4) |
| New | `RE/F_render/src/noise.py` | #15/[F05]: NPS-shaped noise synthesis, patch-wise overlap-add |
| New | `RE/F_render/src/texture.py` | #13: texture, deformation, mass effect, capsule (AC-6) |
| New | `RE/F_render/src/lesion_render.py` | lattice → tissue classes → supersampled HU → box-integrated partial volume (AC-7) |
| New | `RE/F_render/src/insert.py` | additive delta, PSF blur, max-rule, GGO α-blend, lung clip, residual noise (AC-8) |
| New | `RE/F_render/src/render.py` | end-to-end CLI → `hybrid_volume` + run record (AC-9, AC-11) |
| New | `RE/F_render/src/host_masks.py` | F-local threshold body/lung masks for LIDC hosts (Q8), labelled "F-local, replaced by A in INT" |
| New | `RE/F_render/src/projection_insert.py` | #16: XCIST geometry, forward projection, lesion line-integral add, FBP (AC-12) |
| New | `RE/F_render/src/export_slices.py` | final 2-D PNG export (AC-14) |

**Reproductions (`F_render/repro/`)**

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/F_render/repro/r13_synthetic_tumors.py` | #13 reproduction (Q5) + lung adaptation figure |
| New | `RE/F_render/repro/r14_lesion_fit.py` | #14 reproduction (Q5); runs the fit on the LIDC subset |
| New | `RE/F_render/repro/r15_fingerprint.py` | #15 reproduction (Q5) + `--selfcheck` ground-truth recovery (AC-5) |
| New | `RE/F_render/repro/r16_projection_vs_image.py` | #16 Robins/Duke volume agreement (< 3 %) |
| New | `RE/F_render/repro/r17_naeotom_spectrum.py` | #17 published spectrum/number from the cfg (Q5) |

**Config, library, docs**

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/F_render/requirements.txt` | `pydicom`, `pylidc`, `gecatsim` (+ already-installed numpy/scipy/scikit-image/SimpleITK/matplotlib) |
| New | `RE/F_render/library/lesion_model_library.json` | fitted library (committed; parameters only) |
| New | `RE/F_render/xcist/siemens_definition_like.cfg` | #16 geometry, cited |
| New | `RE/F_render/xcist/naeotom_alpha.cfg` | #17 approximation, cited per line |
| New | `RE/F_render/xcist/README.md` | what each config approximates and what it does not |
| New | `RE/F_render/figures/*.png` | repro figures + final slice exports (committed) |
| Modify | `RE/F_render/README.md` | How to run, Reproduced result, honesty notes, CR-F1/CR-F2 |
| Modify | `RE/F_render/status.json` | #13–#17 states, `reproduced{}`, figures, `updated` |
| Modify | `RE/F_render/dossiers/13-synthetic-tumors.md` | dissected (8 sections) |
| Modify | `RE/F_render/dossiers/14-lesion-model-fitting.md` | dissected |
| Modify | `RE/F_render/dossiers/15-scanner-fingerprint.md` | dissected |
| Modify | `RE/F_render/dossiers/16-xcist-projection-insertion.md` | dissected |
| Modify | `RE/F_render/dossiers/17-naeotom-alpha-params.md` | dissected |
| Modify | `RE/feature-F-render.md` | ticks + §9 notes during implementation |

**Untouched:** `shared/`, epic, targets list, `about.html`, `index.html`, `site/`, `.gitignore`, every other letter folder, `QuantumPhantoms/code/`. Run dirs land in `F_render/runs/` (already gitignored by `reverse-engineering/**/runs/`).

---

## 7. Manual Verification (No Tests)

All commands from `RE/` (in the `re-F` worktree) with conda base `python`.

- [x] **Verify AC-1:** open each of the five dossiers; no `_Not yet dissected._` remains; every "Paper's claimed result" cites a page/figure.
- [x] **Verify AC-2:** each `python -m F_render.repro.r1N_…` prints `paper=<x> ours=<y> agreement=<…>`, writes a figure, and the matching `status.json` row has `reproduced{}` filled.
- [x] **Verify AC-3:** `python -m F_render.src.lesion_fit --lidc 20 --out F_render/library/lesion_model_library.json` → `python -m shared.validate F_render/library/lesion_model_library.json` OK; every type has `n_fitted > 0`. Privacy: `python -c "import json;d=json.load(open('F_render/library/lesion_model_library.json'));print(max(len(json.dumps(v)) for v in d['types'].values()))"` is small (< 2 KB per type) and `git status` shows no `.nii.gz`/`.npz`/`.dcm` from LIDC anywhere under `F_render/` outside `runs/`.
- [x] **Verify AC-4:** _(holds except the f50 range: LIDC-IDRI-0001 gives 0.225 cyc/mm, below the 0.3–0.6 guess; consistent with its σ 0.81 mm soft-kernel PSF — see §9)_ run the fingerprint CLI on one LIDC host → validate OK; plot shows a monotone-ish MTF with f50 in 0.3–0.6 cyc/mm (typical clinical range) and σ map non-zero only in the body.
- [x] **Verify AC-5:** `python -m F_render.repro.r15_fingerprint --selfcheck` prints true vs estimated PSF σ (zyx), σ and NPS peak, all within tolerance, with a `PASS` line.
- [x] **Verify AC-6/AC-7:** `python -m F_render.src.render` (stub defaults) → open `figures/` slice export: lesion edge is graded (no single-voxel step); `lesion_mask` volume vs lattice occupied volume within 5 % (printed).
- [x] **Verify AC-8:** on the stub output, `python -c` loading host/hybrid via `shared.volumes.read_volume` shows `(hybrid != host)` is false everywhere outside the dilated support; at S003 (juxtapleural) no delta outside the lung mask; a ground-glass draw (copy of stub draw with `type: ground-glass`) keeps stub vessel HU visible through the lesion.
- [x] **Verify AC-8 noise:** the printed lesion-interior σ vs surrounding-lung σ ratio is within 0.8–1.25 on an LIDC host.
- [x] **Verify AC-9:** `python -m shared.validate F_render/runs/<ts>-render/hybrid_volume.json` → OK including grid check.
- [x] **Verify AC-10:** run render twice → `sha256sum` of both `hybrid_ct.nii.gz` equal. Copy the stub certificate with `"status": "fail", "extracted_seed_hex": null` → render exits non-zero with the rejection message and creates no output dir. Change the seed in a copy → `hybrid_ct` sha differs, `lesion_mask` sha equal. Baseline (step 0) and follow-up (step 30) render to two hybrids.
- [x] **Verify AC-11:** `run.json` in each run dir validates (`python -m shared.validate F_render/runs/<ts>-render/run.json`), `sim` is null, `seed_hex` = certificate seed.
- [x] **Verify AC-12:** `python -m F_render.repro.r16_projection_vs_image` prints image-domain volume, projection-domain volume and % difference (< 3 % target; if missed, the number is recorded honestly and the dossier verdict explains).
- [x] **Verify AC-13:** `F_render/xcist/naeotom_alpha.cfg` loads in XCIST without error; every parameter line has a citation comment; `r17` prints its reproduced number.
- [x] **Verify AC-14:** `grep -rn "imread\|Image.open" F_render/src F_render/repro` prints nothing (PNG never read back).
- [x] **Verify AC-15:** `python -m shared.validate --status` → 8 × OK; `python -m shared.site.build` previews F pages; `git status` then shows `index.html`/`site/` modified → `git checkout -- index.html site/` before committing.
- [x] **Verify AC-16:** `git diff --name-only main...re-F` only shows `F_render/**` and `feature-F-render.md`.
- [x] **Edge case — isolation:** `grep -rn "QuantumPhantoms/code\|f2_imaging\|from [A-EGH]_\|import qiskit" F_render/` prints nothing.

---

## 8. Open Questions

- [x] **Q1: Real CT data.** Nothing is local: no LIDC, no Mayo, no DICOM anywhere. #14 (fit on LIDC) and #15 (fingerprint of a real host) need real scans. *Resolved (accepted default):* download a **20-scan LIDC-IDRI subset** chosen via pylidc so all three texture classes are represented (~ 2–4 GB), stored **outside the repo** at `~/data/LIDC-IDRI/`, configured in `~/.pylidcrc`. The stub phantom stays the default for every command; LIDC is used for fitting, fingerprinting and one real-host hybrid.
- [x] **Q2: New installs.** W said "no new installs", but F needs `pydicom`, `pylidc`, `gecatsim`. *Resolved (accepted default):* `pip install pydicom pylidc gecatsim` into conda base, recorded in `F_render/requirements.txt`. (pylidc pins old numpy/SQLAlchemy in some versions — if it fails on numpy 2.4, fall back to reading LIDC XML annotations directly with `xml.etree` + pydicom, no pylidc.)
- [x] **Q3: #16 scope — Mayo Siemens raw data.** The Mayo LDCT-and-Projection data needs a TCIA data-use agreement and is large; epic says Siemens cases only. *Resolved (accepted default):* F reproduces the Robins/Duke < 3 % agreement on a **synthetic XCIST phantom** (state `reproduced`), writes the Mayo raw-data adaptation as the dossier's "What to reuse next", and leaves real Mayo insertion to INT/future work. If you already have the Mayo data or want it in F, say so and AC-12 extends to one Siemens case.
- [x] **Q4: Missing source PDFs.** Not in `../papers/`: F02 Robins 2017, F03 Mayo 2017, F04 McCabe 2025, Solomon–Samei PMB 2014, Sanders 2016, Divel–Pelc 2019 (all "manual download"). Dissecting #14–#17 without them means guessing numbers. *Resolved (accepted default):* you download them into `../papers/` (filenames from `../README.md` table) **before** `/implement-feature`; the four PMC ones are open access. Without them, the affected dossiers are written from available sources and their `reproduced{}` is left empty with the state kept at `dissected`.
- [x] **Q5: Which published number per target?** Only #16 is fixed by the epic. *Resolved (accepted default):*
  - #13 (H01): their headline (Dice from training on synthetic liver tumors) needs LiTS + model training → not reproduced. Instead reproduce the **generation recipe's documented statistics** (texture HU mean/std and smoothing scale they report, shape/size ranges) and the qualitative figure; `agreement: "qualitative + parameter match"`.
  - #14: Ambrosini [F01] — reproduce the reported SH-shape nodule set statistics (size/volume distribution or volume accuracy of the simulated set, whichever the paper tabulates); Solomon–Samei — edge-width distribution, if the PDF arrives (Q4).
  - #15: Peng [F05] — reproduce their noise-synthesis NPS/σ error metric on the stub phantom; Sanders — f50 for one LIDC host compared with the published range for that kernel class.
  - #16: Robins/Duke volume agreement < 3 % (AC-12).
  - #17: one McCabe spectrum or noise number regenerated from the cfg in XCIST.

  Final choice is made at dissection time and written in the dossier; I will not invent numbers.
- [x] **Q6: Local-NPS contract gap.** `scanner_fingerprint` has only a global NPS (strict schema, `additionalProperties: false`), but the recipe uses local NPS. *Resolved (accepted default):* CR-F1 + CR-F2 (§5) recorded in the README; F writes `local_nps.npz` and links it via `hybrid_volume.insertion.params.local_nps_ref` until INT.
- [x] **Q7: Self-check tolerances (AC-5) and noise ratio (AC-8).** *Resolved (accepted default):* PSF σ and noise σ within 10 %, NPS peak within one bin, lesion/background σ ratio 0.8–1.25. Adjust if you have a reference.
- [x] **Q8: Lung/body masks on LIDC hosts before A exists.** A's lungmask/TotalSegmentator output is not available (and torch is not installed). *Resolved (accepted default):* F-local `host_masks.py` = HU threshold (body > −500, lungs < −400 inside body) + connected components, used only for F's LIDC runs and labelled as such; INT swaps in A's masks.
- [x] **Q9: Necrotic and dormant HU.** LIDC does not label necrosis; the library has no necrotic class. *Resolved (accepted default):* dormant = same HU as the type's interior; necrotic = interior mean − 1 library std (low-attenuation core), cited to the lung-cavitation literature in the dossier, flagged as an assumption in `RenderParams`.
- [x] **Q10: Where to draft/implement.** This plan was drafted on `main`. *Resolved (accepted default):* commit only this plan file on `main` (or carry it into the worktree), then `git worktree add ../qp-re-F -b re-F` and run `/implement-feature` there, per epic §3.

---

## 9. Post-Implementation Notes

**Built (2026-10-29, worktree `../qp-re-F`, branch `re-F`, uncommitted).**
- **`F_render/src/`, 15 modules:**
  - `params`, `io`, `lidc`, `host_masks`;
  - `texture`, `noise`, `fingerprint`, `lesion_fit`, `lesion_render`, `insert`, `render`;
  - `export_slices`, `projection_insert`, `status`.
- **`F_render/repro/`, 5 reproductions:** `r13`–`r17`.
- **Configs and data:** 2 cited XCIST configs, the fitted library (41 LIDC nodules, about 4 KB of scalars), 12 figures.
- **Docs and status:** 5 dissected dossiers, README (run, results, honesty, CR-F1/CR-F2), `status.json` (#13–#16 `adapted`, #17 `dissected`), `requirements.txt`.

**AC evidence** (paths relative to `F_render/`):

| AC | Evidence |
|---|---|
| AC-1 | `dossiers/13…17-*.md`: 8 sections each, no "Not yet" left |
| AC-2 | `repro/r13_synthetic_tumors.py:102`, `r14_lesion_fit.py:31`, `r15_fingerprint.py:154`, `r16_projection_vs_image.py:95`, `r17_naeotom_spectrum.py:37`; `src/status.py:14` writes `reproduced{}` |
| AC-3 | `src/lesion_fit.py:115` `fit_nodule`, `:186` `aggregate`, `:214` CLI; `library/lesion_model_library.json` validates (n = 20/11/10) |
| AC-4 | `src/fingerprint.py:111` `estimate_psf`, `:170` `estimate_nps`, `:199` `estimate_sigma_map`, `:232` `write` |
| AC-5 | `repro/r15_fingerprint.py:43` `selfcheck`. PASS: σz −7 %, σxy +3 %, σ −5 %, NPS peak within one bin |
| AC-6 | `src/texture.py:12` `texture_field`, `:34` `deform_shape`, `:48` `mass_effect`, `:66` `capsule` |
| AC-7 | `src/lesion_render.py:54` `render_lesion`; `:173` box integration; volume 256 vs 264 mm³ (stub), 263 vs 264 (LIDC) |
| AC-8 | `src/insert.py:38` `insert`; `:68` δ clipped to lung; `:72` GGO α; `:74` max-rule; σ in/out 1.10 on LIDC; 0 voxels changed outside the lungs (S003, GGO) |
| AC-9 | `src/render.py:27` `run_render`; stub and LIDC `hybrid_volume.json` validate |
| AC-10 | `src/io.py:50` `seed_from_certificate`, `:53` `RejectedDraw` (exit 2, nothing written). Replay gives sha256 identical; a new certificate seed changes `hybrid_ct`, `lesion_mask` stays identical |
| AC-11 | `src/render.py:89` `run.finish`; `run.json` validates, `sim: null` |
| AC-12 | `src/projection_insert.py:62` `simulate`, `:83` `add_prep`, `:89` `reconstruct`; `repro/r16_projection_vs_image.py`. PD_B +0.25 ± 1.02 %, PD_A +1.97 ± 1.32 % |
| AC-13 | `xcist/naeotom_alpha.cfg` (cited per line); `repro/r17_naeotom_spectrum.py`. Prints f50 0.573 vs 0.39 (disagreement recorded) and noise ∝ mAs^−0.501 |
| AC-14 | `src/export_slices.py:27`; the `imread` / `Image.open` grep is empty |
| AC-15 | `README.md` sections filled; `status.json`; `--status` OK; site built for preview, then reverted |
| AC-16 | `git status` lists only `F_render/**` + `feature-F-render.md` |

**Reproductions:**
- #13: qualitative + parameter match (DSC not attempted).
- #14: 0.870 ± 0.066 vs 0.890 ± 0.061 (solid, like-for-like).
- #15: [F05] moments within 1.53 %.
- #16: [F02] < 3 % reproduced in simulation.
- #17: f50 **not** matched (+47 %; the 'soft' kernel at +19 % was only checked afterwards and is not claimed).

**Deviations from the plan:**
- **pylidc:** the Q2 fallback (raw XML) was not needed. Instead `src/lidc.py:28` `_numpy2_compat` aliases `np.int/float/bool` and
  `configparser.SafeConfigParser`, which pylidc 0.2.3 uses and which numpy 2 / Python 3.12+ removed.
- **gecatsim:** the PyPI sdist has CRLF build scripts. It was installed from a local copy after `sed 's/\r$//'` (recorded in `requirements.txt`).
- **Seeds:** geometry draws (edge σ, lobulation, deformation, spicules) use the TumorDraw's `shape_seed_hex`. Appearance (HU, texture,
  noise) uses the certificate seed. With a single seed, a new certificate also changed the mask, which violates AC-10. This is a
  clarification of the epic §3 seed chain for INT/G.
- **#14 comparison population:** the comparison is restricted to **solid** nodules, because [F01]'s 17 nodules are metastases. All types (0.714) are reported too.
- **Edge model:** the edge is shifted inward by σ²/r so a convex lesion keeps its lattice volume (+6 % → −3 %).
- **#16 co-registration:** the 6 nodules sit on a symmetric ring, so flips are position-equivalent. Ties are broken by volume agreement. The first run's
  results were wrong (permuted nodules) and were re-analysed on the cached scans (`--xcist-dir`), so no physics was rerun.
- **Fingerprint f50:** on LIDC-IDRI-0001 it is 0.225 cyc/mm, below §7's guessed 0.3–0.6. It is consistent with the measured σ 0.81 mm; LIDC uses soft
  kernels and the air–skin edge includes the skin layer.
- **Papers:** F02, F03 and F04 were read as PMC full text, not PDFs. Solomon–Samei, Sanders and Divel–Pelc are still missing, so no number is claimed from them.
- **No exploration agent was spawned at implement time.** The plan-time survey covered every touched file (all new, inside `F_render/`).

**Follow-ups:**
- Commit `re-F`, then merge to `main` (disjoint folders). `index.html` / `site/` stay uncommitted (INT).
- **INT:**
  - apply CR-F1 / CR-F2;
  - swap the F-local LIDC masks for A's;
  - the stub lattice → E;
  - the stub certificate → C.
- **#16 refinement:** project the lesion monochromatically at 70 keV (Mayo) to remove the positive PD_A bias.
- **Privacy decision for the developer:** `figures/render-lidc0001-*.png` show a cropped public LIDC slice (CC BY 3.0). Delete them if no
  patient pixels may be committed.
- **H:** consume the r16 A/B/real nodule set and the per-type library distributions as physics benchmarks.
