# #16 — Projection-domain insertion rebuilt on XCIST (Mayo; Mayo LDCT raw data)

**Letter:** F ([`F_render`](../README.md)) · **Priority:** ★★ · **Kind:** classical · **Papers:** F03, A06 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

Mayo's projection-domain lesion insertion [F03 §2.1] works in four steps:
1. decode the Siemens raw data (geometry, flying focal spot, post-log projections);
2. forward-project a segmented lesion with that exact geometry;
3. add the lesion's line integrals to the patient projections;
4. reconstruct with the scanner's own reconstruction.

The lesion therefore inherits the scanner's real blur, noise and reconstruction non-linearities. Robins et al. (Duke) [F02]
compared this projection-domain insertion (Technique A) against image-domain insertion (Technique B: voxelise,
partial-volume correct, blur with the system MTF, add). They found both within a few percent in volume of nodules that
were physically present.

**Access:**
- Mayo's code and the vendor decoder are not public.
- F02, F03 and F04 were read as full text from PubMed Central (PMC5693368, PMC5374359), since they are not in `papers/`.
- The Mayo LDCT raw data [A06] needs a TCIA data-use agreement and was **not** used (plan Q3).

So the scanner is XCIST configured from published parameters, and the host is a synthetic voxel phantom.

## Equations

```text
p_host(θ, u, v)   = −ln(I/I0)                       post-log projections (XCIST prep)
p_les (θ, u, v)   = ∫ Δµ_lesion dl                   lesion excess over lung, projected alone, noise off
p_A               = p_host + p_les                   (Technique A)
image_A           = FBP(p_A)
image_B           = FBP(p_host) + PSF ⊗ [ F_pv · (HU_nod − HU_lung) ]     (Technique B; F_pv partial volume)
PD                = 100 · (V_technique − V_real) / V_real
```

## Parameters

| Parameter | Value | Source |
|---|---|---|
| scanner | SOMATOM Definition Flash, 120 kV, 128 × 0.6 mm, 0.28 s, B46f | [F03 §2.2] |
| geometry | SID 595 mm, SDD 1085.6 mm, 736 channels | published Definition geometry (Flohr et al. 2006; not in `papers/`) |
| reductions | 24 rows, 500 views, axial | compute budget (marked "(reduced)" in the cfg) |
| lesion projection | polychromatic, log-domain add | ours (Mayo: monochromatic 70 keV [F03 §2.1]) |
| phantom | Ø 180 mm water cylinder, Ø 150 mm lung core at 0.2 water, 0.4 mm voxels | ours |
| nodules | 5 / 8 / 10 mm × sphere / lobulated SH (#14 powers) | after [F02] (3 sizes × 4 morphologies) |
| segmentation | threshold at the lung/nodule HU midpoint, connected component | after [F02] (commercial tool) |

Config: [`../xcist/siemens_definition_like.cfg`](../xcist/siemens_definition_like.cfg). Every line is cited.

## Paper's claimed result

[F02] Table 4: average volume PD of virtual vs CT-derived (physically present) nodules.
- **Technique B (image domain):** −0.28 %, +0.34 %, +0.57 %, −2.28 % across FBP/IR at 1.4/22 mGy.
- **Technique A (projection domain):** −2.24 %, −1.03 %, −1.01 %, −1.69 %.
- R² 0.98–0.99 throughout.

[F03]'s headline is reader-based (AUC 0.62 for real-vs-inserted discrimination), so it cannot be reproduced without readers.

## Our reproduction (number + figure)

Command: `python -m F_render.repro.r16_projection_vs_image`.
- **Cost:** three XCIST scans, ~45 min CPU.
- **Re-analysis without rescanning:** `--xcist-dir <old run>/xcist`.
- **Run dir:** `F_render/runs/*-repro-16/` (`r16_results.json`).

| Nodule | True (mm³) | Real (CT-derived) | A projection | PD_A | B image | PD_B |
|---|---|---|---|---|---|---|
| 5 mm sphere | 65.2 | 60.0 | 62.4 | +4.00 % | 59.1 | −1.50 % |
| 5 mm lobulated | 71.1 | 64.2 | 66.3 | +3.27 % | 65.2 | +1.64 % |
| 8 mm sphere | 268.2 | 257.1 | 259.8 | +1.05 % | 256.9 | −0.06 % |
| 8 mm lobulated | 298.4 | 285.4 | 288.4 | +1.05 % | 286.6 | +0.42 % |
| 10 mm sphere | 523.9 | 509.8 | 514.8 | +0.97 % | 511.8 | +0.38 % |
| 10 mm lobulated | 600.4 | 581.2 | 589.9 | +1.50 % | 584.7 | +0.59 % |
| **mean ± sd** | | | | **+1.97 ± 1.32 %** | | **+0.25 ± 1.02 %** |

**Setup** (simulated: XCIST, not a physical phantom):
- **Recon:** lung −794 HU, nodule −2 HU, threshold −398 HU.
- **PSF:** measured by #15 on the host reconstruction, MTF f50 0.37 mm⁻¹.
- **Co-registration:** 0.17 px.

**Comparison with [F02]:**
- **Technique B (image domain, the main F path):** agrees with [F02]'s −0.28…+0.57 %.
- **Technique A:** has the same magnitude as [F02]'s −2.24…−1.01 % but the opposite sign. Both are within the paper's ±3 %.
  - **Likely cause:** we project the lesion polychromatically **alone**, so its spectrum is not hardened by the body. Its line integrals are therefore slightly too large.
  - Mayo avoided this by projecting monochromatically at the beam-hardening-correction energy (70 keV) [F03 §2.1]. That is the next refinement.
- **CT-derived vs true volume:** −3 % to −10 %, smallest nodules worst. [F02] Table 3 reports 13–16 % for its commercial segmentation tool.

**Agreement:** agree. |PD| < 3 % on average for both techniques. Figure: [`r16-projection-vs-image.png`](../figures/r16-projection-vs-image.png).

## Adaptation

- `F_render/src/projection_insert.py`: an XCIST voxel-phantom writer, `simulate` (seeded quantum and electronic noise),
  `add_prep` (the insertion) and `reconstruct`.
- The image-domain arm (Technique B) uses our own pieces:
  - the #14 spherical-harmonic voxeliser with partial volume;
  - the #15 estimator measuring the PSF of the XCIST reconstruction.

  The comparison therefore also validates the F image-domain insert against a projection-domain reference.
- The main F path stays image-domain, because [F02] shows it is within ~3 % of projection-domain. Projection domain
  is the Siemens-native upgrade.

## Verdict

**adapted.** The [F02] volume agreement is reproduced in simulation. The XCIST projection-domain pipeline exists, and it validates the image-domain
insert used on the main path. Real Mayo Siemens raw-data insertion stays future work. It needs the TCIA agreement and the
vendor geometry. Only Siemens cases may be used for Siemens work (epic §6).

## What to reuse next

- **INT / Siemens path:** replace the synthetic phantom with Mayo LDCT Siemens projections [A06] once access is granted.
  - Use XCIST only as the forward projector for the lesion.
  - `add_prep` is the insertion step unchanged.
- **H:** the 6-nodule A/B/real set gives a physics benchmark (volume, HU, edge) for the image-domain insert.
