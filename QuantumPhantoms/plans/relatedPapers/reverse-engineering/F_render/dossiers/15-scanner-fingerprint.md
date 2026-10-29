# #15 — Scanner fingerprint estimator (Sanders MTF 2016; Divel–Pelc 2019; Peng)

**Letter:** F ([`F_render`](../README.md)) · **Priority:** ★★★ · **Kind:** classical · **Papers:** F05 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

An inserted lesion only looks scanned if it carries the host scan's own blur and noise. F therefore measures both
from the patient image itself, with no phantom scan:
- **Resolution (Sanders, Hurwitz & Samei, Med. Phys. 2016):**
  - the air–skin boundary of every patient is a natural high-contrast edge;
  - profiles across it give an oversampled edge-spread function (ESF), then the line-spread function (LSF), then the MTF.
- **Noise (Peng et al. 2023 [F05], after Divel & Pelc, SPIE 2019):**
  - CT noise is non-stationary;
  - estimate a noise power spectrum (NPS) per small patch;
  - synthesise noise by filtering white noise with √NPS patch by patch;
  - merge the overlapping patches with trapezoid windows.

**Source availability:** Sanders 2016 and Divel–Pelc 2019 are paywalled and **not in `papers/`**. Their methods are
re-derived from the descriptions quoted in [F05] §2.2.1 and the analysis doc. Only [F05] supplies a number.

## Equations

```text
ESF        pixels in a 1.5 px-wide strip along the outward body normal, binned by projected distance s − s0
           (s0 = the strip's own sub-pixel edge, from the area under the normalised profile); 0.1 px bins
LSF        −dESF/ds ;  MTF(f) = |FFT(LSF · Hann)| / MTF(0) ;  σ_xy from a Gaussian fit to the LSF
σ_z        same strip method across lung/soft-tissue boundaries with |n_z| > 0.9 (fallback: slice/2.355)
NPS        S(fx, fy) = Δx Δy / (Nx Ny) · ⟨|F(n)|²⟩         ([F05] eq. 3); single-scan ROIs are 2nd-order detrended
synthesis  n = F⁻¹( √(S / ΔxΔy) · F(w) ),  w ~ N(0, 1)  →  var(n) = Σ S / (N ΔxΔy)
patches    6.8 mm, 30 % overlap, trapezoid weights, Σ w n / √Σ w²   ([F05] §2.2.1)
σ map      σ² = G_w[(x − G_1.5 x)² · flat] / G_w[flat] / k²,  k² = Σ S (1 − Ĝ)² / Σ S   (high-pass gain from the NPS)
```

## Parameters

| Parameter | Value | Source |
|---|---|---|
| strip half-length | 8 mm | ours |
| ESF bin | 0.1 px | standard oversampled-edge practice |
| boundary points | 3000 (xy), 12000 candidates (z) | ours |
| NPS ROI | 24 mm, soft tissue (−150…150 HU), ≥ 10 mm inside the body | ours |
| patch size / overlap | 6.8 mm / 30 % | [F05] §2.2.1 |
| repeated acquisitions for patch NPS | 20 | [F05] §2.2.1 |
| σ-map window / flat threshold | 10 mm / gradient < 15 HU/mm, 2 px from edges | ours |

## Paper's claimed result

[F05] §3, Fig. 2(i): noise synthesised from the patch NPS matches the real repeated-scan noise. Its moments
up to the 4th order differ by **within 2 %**.

## Our reproduction (number + figure)

Command: `python -m F_render.repro.r15_fingerprint` (run dir `F_render/runs/*-repro-15/`).

- **[F05] moments:**
  - **Setup:** a non-stationary ground-truth noise field stands in for the orange-man phantom. It has a soft NPS with σ 20 HU on the left
    and a sharp NPS with σ 35 HU on the right.
    - 20 realisations give the patch NPS.
    - It is compared with 20 independent realisations.
  - **σ difference:** **+1.53 %** (left), **+0.19 %** (right).
  - **Kurtosis difference:** **−1.27 %** (left), **+0.35 %** (right).
  - **Agreement:** agree, worst case 1.53 % ≤ 2 %.
  - **Figure:** [`r15-peng-patch-noise.png`](../figures/r15-peng-patch-noise.png).
- **Self-check (plan AC-5):**
  - **Setup:** the stub phantom blurred by a known PSF σ = (3.0, 1.6, 1.6) mm (z, y, x), with NPS-shaped noise of σ = 15 HU.
  - **Estimated:** σ_z 2.78 mm (−7 %), σ_xy 1.65 mm (+3 %), σ map 14.3 HU (−5 %). The NPS peak is within one bin.
  - **Result:** **PASS**.
  - **Figure:** [`r15-selfcheck.png`](../figures/r15-selfcheck.png).
- **Real host (LIDC-IDRI-0001, 0.70 × 0.70 × 2.5 mm):**
  - in-plane σ 0.81 mm, from 2454 air–skin strips;
  - σ_z 1.33 mm, from 660 lung z-edges;
  - global NPS σ 35 HU, σ-map median 26 HU.

  The NPS σ is above the σ map because single-scan soft-tissue ROIs still contain fat/muscle texture.

## Adaptation

- Fully 3-D. In-plane strips sit on axial planes; z strips run along lung domes and apices.
- **Output:** `scanner_fingerprint.json` with MTF, `psf_sigma_mm_zyx`, NPS and `sigma_map.nii.gz`.
- **Local NPS patches** go to `local_nps.npz`. This is contract change request **CR-F1**, because the frozen schema has only a global NPS.
- The patient has only one acquisition, so the patch NPS of a host comes from detrended single-scan ROIs.
  [F05]'s 20-repeat ensemble is used only in the reproduction.
- **Consumer:** the F insert blurs only the lesion delta with this PSF. If the lesion interior is quieter than the surrounding lung, it tops the noise up with this NPS.

## Verdict

**adapted.** Both the estimator and the patch-NPS synthesis are reproduced and used in every hybrid.

## What to reuse next

- **H:** "NPS inside the lesion vs outside" and the MTF are the physics-realism checks.
- **INT:** apply CR-F1 (`local_nps`) and CR-F2 (slice-sensitivity profile instead of a single σ_z).
- **#16:** the estimator measures the XCIST reconstruction's PSF for the image-domain arm.
- **#17:** it measures the NAEOTOM approximation's f50.
