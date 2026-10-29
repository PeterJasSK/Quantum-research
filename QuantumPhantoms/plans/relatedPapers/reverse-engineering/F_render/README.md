# F — Render into CT: realistic, scanner-matched insertion

> Letter folder `F_render/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/F_render/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
Cell states → HU from an LIDC-fitted lesion library; supersampled partial volume; additive-delta insertion (vessel max-rule, ground-glass α-blend); 3-D PSF + noise from the host scan's own fingerprint (MTF from the air–skin edge, local NPS and σ), inserted into the full 3-D host volume. 2-D slices only as a final export. Upgrade path: projection-domain insertion on Mayo Siemens raw data via XCIST, then a NAEOTOM Alpha approximation.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #13 | [SyntheticTumors / Label-free pipeline](dossiers/13-synthetic-tumors.md) | ★★★ | classical | adapted |
| #14 | [Lesion-model fitting (Ambrosini; Solomon–Samei PMB 2014)](dossiers/14-lesion-model-fitting.md) | ★★★ | classical | adapted |
| #15 | [Scanner fingerprint estimator (Sanders MTF 2016; Divel–Pelc 2019; Peng)](dossiers/15-scanner-fingerprint.md) | ★★★ | classical | adapted |
| #16 | [Projection-domain insertion rebuilt on XCIST (Mayo; Mayo LDCT raw data)](dossiers/16-xcist-projection-insertion.md) | ★★ | classical | adapted |
| #17 | [DukeSim NAEOTOM Alpha parameters (McCabe)](dossiers/17-naeotom-alpha-params.md) | ★★ | classical | dissected |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `growth_trajectory` — stub: [`shared/stubs/growth_trajectory/growth_trajectory.json`](../shared/stubs/growth_trajectory/growth_trajectory.json) · schema: [`growth_trajectory.schema.json`](../shared/contracts/growth_trajectory.schema.json)
- `anatomy_masks` — stub: [`shared/stubs/anatomy_masks/anatomy_masks.json`](../shared/stubs/anatomy_masks/anatomy_masks.json) · schema: [`anatomy_masks.schema.json`](../shared/contracts/anatomy_masks.schema.json)
- `site_candidates` — stub: [`shared/stubs/site_candidates/sites.json`](../shared/stubs/site_candidates/sites.json) · schema: [`site_candidates.schema.json`](../shared/contracts/site_candidates.schema.json)
- `tumor_draw` — stub: [`shared/stubs/tumor_draw/tumor_draw.json`](../shared/stubs/tumor_draw/tumor_draw.json) · schema: [`tumor_draw.schema.json`](../shared/contracts/tumor_draw.schema.json)
- `certificate` — extracted seed; stub: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json) · schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `lesion_model_library` — schema: [`lesion_model_library.schema.json`](../shared/contracts/lesion_model_library.schema.json) · stub example: [`shared/stubs/lesion_model_library/lesion_model_library.json`](../shared/stubs/lesion_model_library/lesion_model_library.json)
- `scanner_fingerprint` — schema: [`scanner_fingerprint.schema.json`](../shared/contracts/scanner_fingerprint.schema.json) · stub example: [`shared/stubs/scanner_fingerprint/scanner_fingerprint.json`](../shared/stubs/scanner_fingerprint/scanner_fingerprint.json)
- `hybrid_volume` — schema: [`hybrid_volume.schema.json`](../shared/contracts/hybrid_volume.schema.json) · stub example: [`shared/stubs/hybrid_volume/hybrid_volume.json`](../shared/stubs/hybrid_volume/hybrid_volume.json)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to F_render/runs/ via shared.runrecord. -->
F is classical, so no quantum labels apply. All commands run with cwd = `reverse-engineering/` and conda-base `python`.
Extra dependencies are in [`requirements.txt`](requirements.txt). Every run writes `F_render/runs/<ts>-<tag>/run.json` (gitignored).

```bash
# render: growth snapshot → hybrid_volume (defaults: shared/stubs/ + the fitted library)
python -m F_render.src.render                         # follow-up snapshot (last step)
python -m F_render.src.render --step 0 --tag baseline # baseline of the longitudinal pair
python -m F_render.src.render --export                # + final 2-D PNG slices in figures/
python -m F_render.src.export_slices <hybrid_volume.json> --tag NAME

# real LIDC host (F-local masks + one free site, plan Q8; patient voxels stay in runs/)
python -m F_render.src.lidc download --n 20           # once; ~4.3 GB to ~/data/LIDC-IDRI
python -m F_render.src.host_masks --lidc LIDC-IDRI-0001
python -m F_render.src.fingerprint --masks F_render/runs/<ts>-host-LIDC-IDRI-0001/anatomy_masks.json --slice-thickness 2.5
python -m F_render.src.render --masks <…/anatomy_masks.json> --sites <…/sites.json> \
       --fingerprint <…-fingerprint/scanner_fingerprint.json> --tag lidc0001 --export

# #14 library (parameters only) → F_render/library/lesion_model_library.json
python -m F_render.src.lesion_fit --lidc 20           # ~1 h CPU

# reproductions (each updates status.json and writes its figure)
python -m F_render.repro.r13_synthetic_tumors
python -m F_render.repro.r14_lesion_fit
python -m F_render.repro.r15_fingerprint [--selfcheck]
python -m F_render.repro.r16_projection_vs_image      # ~45 min, XCIST
python -m F_render.repro.r17_naeotom_spectrum         # ~25 min, XCIST
```

**Seeds.**
- Appearance (HU, texture, residual noise) comes from `rng(certificate.extracted_seed_hex, "F.<label>")`.
- Geometry (edge σ, lobulation, deformation, spicules) comes from `rng(tumor_draw.shape_seed_hex, "F.<label>")`.
- A `fail` certificate rejects the draw: exit code 2, nothing written.
- The same inputs give a byte-identical `hybrid_ct.nii.gz`.

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
F is classical, so `sim_mode` is n/a. "Simulated" below means a software phantom or simulator, never a scanner.

| # | Paper's number | Ours | Agreement | Figure |
|---|---|---|---|---|
| 13 | [H01] generation pipeline, Table 1/6 (qualitative, Fig. 3) | recipe reproduced on a synthetic liver; core HU = sampled µt | qualitative + parameter match; DSC 59.81 % **not** reproduced (needs LiTS training) | [r13](figures/r13-synthetic-tumors-liver.png) |
| 14 | [F01] SH(l≤3) 3-D correlation 0.8897 ± 0.0609 (17 metastases, 8–20 mm) | 0.8699 ± 0.0664 (11 solid LIDC nodules, 8–20 mm); all types 0.714 ± 0.242 | agree (Δ −0.020, z −0.79) | [r14](figures/r14-lesion-library.png) |
| 15 | [F05] patch-NPS noise moments within 2 % | σ +1.53 / +0.19 %, kurtosis −1.27 / +0.35 %; self-check PSF/σ within 10 % (PASS) | agree (synthetic ground truth) | [r15](figures/r15-peng-patch-noise.png), [self-check](figures/r15-selfcheck.png) |
| 16 | [F02] Table 4 volume PD: image −0.28…+0.57 %, projection −2.24…−1.01 % | image **+0.25 ± 1.02 %**, projection +1.97 ± 1.32 % (6 nodules, XCIST phantom) | agree, \|PD\| < 3 % (simulated) | [r16](figures/r16-projection-vs-image.png) |
| 17 | [F04] Table 1 real f50 0.39 mm⁻¹ (Br40) | 0.573 mm⁻¹ (pre-registered XCIST 'standard'); noise ∝ mAs^−0.501 | **disagree** (+47 %); approximation only | [r17](figures/r17-naeotom.png) |

The epic's F-row headline was Robins/Duke volume agreement < 3 %. The image-domain insert reproduces it (+0.25 ± 1.02 %).
Real-host render: [`figures/render-lidc0001-lung.png`](figures/render-lidc0001-lung.png).
- Volume 263 mm³ vs 264 mm³ in the lattice.
- σ inside/outside the lesion is 1.10.
- Every changed voxel lies within 8.1 mm of the lesion centre.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
Classical stage (claim level n/a).

- **Privacy-by-construction.**
  - Only fitted parameters leave LIDC: [`library/lesion_model_library.json`](library/lesion_model_library.json), about 4 KB of scalars.
  - LIDC pixel data live outside the repo (`~/data/LIDC-IDRI`). Hybrids of LIDC hosts stay in gitignored `runs/`.
  - The committed `figures/render-lidc0001-*.png` show a cropped slice of the public LIDC-IDRI scan 0001 (CC BY 3.0). That is a display export, not generator input.
  - Learned refiners (DiffTumor, MAISI) are ablation only and are not built.
- **F-local substitutes, replaced in INT.**
  - Masks and the single site on LIDC hosts come from `src/host_masks.py`: thresholds + connected components, lobes not
    derivable (all 0), lobe label by z-half.
  - These are not A's lungmask/TotalSegmentator masks.
- **Image domain is the main path.**
  - The projection-domain arm (#16) runs on a **synthetic XCIST phantom** with a Definition-*like* configuration from published parameters.
  - Real Mayo Siemens raw-data insertion is future work: it needs the TCIA agreement and the vendor geometry, and only Siemens cases may be used for Siemens work.
- **NAEOTOM Alpha (#17)** is an XCIST approximation, not DukeSim. CdTe crosstalk and covariance are not modelled, and f50 does not match
  Br40 under the pre-registered kernel.
- **Missing sources.** Solomon–Samei 2014, Sanders 2016 and Divel–Pelc 2019 are paywalled and not in `papers/`, so no number is claimed from them.
  F02, F03 and F04 were read as PMC full text.
- **Library HU.** The solid HU mean (−22 HU) sits below soft tissue because of partial volume in small nodules on 2.5 mm slices.
  Ground-glass nodules fit the shape-only check poorly (corr 0.42); their realism comes from texture.


## Pipeline readiness

<!-- readiness: caveats -->

Draft rating, not yet confirmed by the chain (the chain has not reached F). The image-domain insert reproduces the
volume headline (+0.25 ± 1.02 %), and every chain flag exists (`render --masks` already accepts A's manifest). The
runner asserts that the hybrid lies on A's host geometry (spacing, origin, direction, size). Two integration hazards
showed up in the probe: `--export` writes host-derived PNGs into the git-tracked `figures/`, and the lesion library
JSON is outside the commit's code hash.

**Weak links**

| Weak link | Kind | Why it limits reliability | Evidence | To strengthen |
|---|---|---|---|---|
| A's masks never used | integration | F-local threshold masks have all lobes = 0; behaviour with lungmask lobes is untested | honesty notes above | the chain's `render` stage with `--masks <A>` |
| `--export` into tracked `figures/` | integration | each chain run adds host-derived images to the repo | probe `F.render`; `render.py:114` | export into the run dir |
| Library outside the commit | integration | `library/lesion_model_library.json` can change after the commit | probe `G.commit` | hash parameter files into the commit |
| #17 NAEOTOM f50 +47 % | component | the photon-counting look is an approximation | #17 row | DukeSim or a kernel fit |
| Solid HU −22 (partial volume) | data | solid nodules render too dark | honesty notes above | fit on thinner slices / deconvolve |
| #16 projection domain synthetic only | data | the raw-data path is untested on real scanner data | #16 row | Mayo Siemens raw data (TCIA agreement) |

**Used as-is in the chain?** Expected yes; the geometry assert lives in the runner, not in F. Full gap list: [INT](../INT_integration/README.md); whole chain: [index](../index.html).


## Future

Shared, pipeline-wide context (end goal, digital-twin path, cross-letter risks) lives once in the
[whole-pipeline Future](../future.md). This section covers only what this letter adds. Every claim carries a label:
<span class="chip evidence">evidence-based</span> (a number in this repo or a cited paper), <span class="chip extrapolation">extrapolation</span> (a reasoned step beyond the evidence),
<span class="chip speculative">speculative</span> (possible, not supported yet).

### 1. Aim of the paper(s)

- **[H01] Hu (label-free liver tumours):** synthetic tumours good enough that segmentation AI trains without
  manual labels.
- **[F01] Ambrosini:** fit nodule shape and HU models to real annotations.
- **[F05] Peng:** generate realistic, position-dependent CT noise from the scan itself.
- **[F02] Robins, [F03] Mayo:** insert nodules in the image domain vs the projection (raw-data) domain, and show both
  agree on volume.
- **[F04] McCabe (DukeSim):** simulate the Siemens NAEOTOM Alpha photon-counting CT. **[A06]** Mayo low-dose CT
  images + raw projections.

Why it matters: a synthetic nodule is only useful if it **looks like it was scanned by that scanner**: the same
blur, noise and partial-volume edges.

### 2. Contribution

- Image-domain insertion reproduces the volume headline: +0.25 ± 1.02 % (projection arm +1.97 ± 1.32 %, synthetic
  XCIST phantom). <span class="chip evidence">evidence-based</span>
- Lesion shape model: 3-D correlation 0.8699 ± 0.0664 against the paper's 0.8897 ± 0.0609. <span class="chip evidence">evidence-based</span>
- Noise generator: σ and kurtosis within 2 %. NAEOTOM resolution is approximated but off (f50 +47 %). <span class="chip evidence">evidence-based</span>
- A privacy-by-construction library: about 4 KB of fitted scalars leave LIDC, and no patient voxels. <span class="chip evidence">evidence-based</span>

### 3. Role in cancer detection

**End goal:** synthetic nodules that detectors and readers cannot tell from real ones, **matched to each
scanner's resolution, noise and dose**, so sensitivity can be measured per scanner model and protocol, with exact
masks. The upgrade path runs through photon-counting CT [F04]. <span class="chip extrapolation">extrapolation</span>

### 4. Beyond lungs

- **Any CT organ.** The insertion and fingerprint code is organ-agnostic. <span class="chip extrapolation">extrapolation</span>
- **Other modalities.** MR needs its own physics (signal model, coil noise), which is not built here; the same
  "fit parameters, never copy voxels" rule carries over. <span class="chip speculative">speculative</span>
- **Dose and protocol studies.** Re-render the same lesion at lower dose to find where detection breaks. <span class="chip extrapolation">extrapolation</span>
- **Treatment planning QA.** Lesions with known extent test auto-contouring for radiotherapy. <span class="chip extrapolation">extrapolation</span>

### 5. Long-term vision: toward a digital twin

<div class="callout speculative">

<span class="chip speculative">speculative</span> F is the twin's **imaging layer**: predict what *this* patient's lesion would look like on another scanner,
dose or reconstruction. Path: (1) image-domain insertion with a fitted fingerprint (now) → (2) raw-data insertion
on vendor geometry [F03, A06] → (3) full scanner simulation [F04] → (4) virtual imaging trials on twin cohorts
[H04, G02].

</div>

### 6. Predictions

**5 years**
*Assumptions:* public LIDC/Mayo data; the XCIST simulator; no proprietary vendor geometry.
- Image-domain volume agreement < 3 % holds (+0.25 %). <span class="chip evidence">evidence-based</span>
- Rendering with A's lungmask lobes replaces F-local threshold masks. <span class="chip extrapolation">extrapolation</span>
- Solid-nodule HU fitted on thinner slices fixes the −22 HU partial-volume bias. <span class="chip extrapolation">extrapolation</span>

**10 years**
*Assumptions:* access to vendor raw data and geometry (the Mayo Siemens path).
- Projection-domain insertion becomes the default for scanner-specific studies. <span class="chip extrapolation">extrapolation</span>
- Photon-counting rendering matches the measured MTF. <span class="chip extrapolation">extrapolation</span>

<div class="callout speculative">

**15 years**
*Assumptions:* fault-tolerant hardware.
- <span class="chip speculative">speculative</span> F stays classical: image physics gains nothing from quantum hardware in any scenario this project can
  argue for. The 15-year change is regulatory: rendered lesions accepted as evidence in virtual imaging trials
  [G02, H03].

</div>

### 7. Risks and obstacles

| Risk | Kind | Why it matters | Mitigation |
|---|---|---|---|
| Domain gap | validation | readers or detectors may still spot synthetic lesions | visual Turing test [F10]; train-synthetic/test-real (H) |
| Vendor data access | data | raw-data insertion needs agreements | Mayo LDCT [A06]; Siemens-only cases for Siemens work |
| Learned refiners memorize patients | regulatory | diffusion models can reproduce training data [H07, H08] | keep parameter-only rendering (privacy by construction) |
| #17 not matched | technical | photon-counting look is approximate | DukeSim or kernel fit |
| `--export` into tracked folder | technical | host-derived images enter git (INT finding) | export into run dirs |

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[A06], [F01], [F03], [F04], [F05], [H01] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).
[F02] Robins 2017 (PMC5693368), [F03] Mayo 2017 (PMC5374359) and [F04] McCabe 2025 (PMC12285274) were read as PMC full text.
[F06] Lee 2018 supplies the GGO/solid HU thresholds.
Not available: Solomon–Samei PMB 2014, Sanders Med. Phys. 2016, Divel–Pelc SPIE 2019.

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
| ID | Contract | Field | Why | Local workaround |
|---|---|---|---|---|
| CR-F1 | `scanner_fingerprint` | optional `local_nps {path, sha256}` → NPZ (`nps_patches` float32 (n, f), `patch_centers_zyx` int32 (n, 3), `freq_cyc_per_mm`, `spacing_mm_xyz`) | CT noise is non-stationary; [F05] synthesises it patch-wise | `local_nps.npz` + `local_nps.ref.json` next to the fingerprint; linked from `hybrid_volume.insertion.params.local_nps_ref` |
| CR-F2 | `scanner_fingerprint` | optional `ssp {z_mm[], values[]}` (slice-sensitivity profile) | a single σ_z is a Gaussian approximation of the slice profile | z σ only; method recorded in the run notes |
