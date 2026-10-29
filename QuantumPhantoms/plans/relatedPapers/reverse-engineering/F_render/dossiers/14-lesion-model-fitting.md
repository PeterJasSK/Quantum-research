# #14 — Lesion-model fitting (Ambrosini; Solomon–Samei PMB 2014)

**Letter:** F ([`F_render`](../README.md)) · **Priority:** ★★★ · **Kind:** classical · **Papers:** F01 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

A lesion model with few parameters can be fitted to real nodules. That gives type-correct shape, edge sharpness and HU **without carrying
any patient voxel** into the generator (privacy-by-construction).

- **Ambrosini, Wang & O'Dell, SPIE 2010 [F01]:**
  - contoured real lung metastases are reconstructed as a spherical-harmonic (SH) radius function;
  - each is voxelised with partial volume, blurred by a Gaussian PSF and inserted;
  - the vessel overlap is handled with a **max rule**;
  - the result is validated by a 3-D correlation with the real nodule.
- **Solomon & Samei, PMB 2014:** fitted analytic edge profiles for lesion margins. **Paywalled, not in `papers/`.**
  Its erf-edge form is used as described in `../analysis-stages-B-D-F.md` §4. No number from it is claimed.

## Equations

```text
shape      r(θ, φ) = Σ_{l ≤ lmax} Σ_{m=−l..l} a_lm Y_lm(θ, φ)        ([F01] eq. 1; real SH, least squares)
           P_l = Σ_m a_lm² / a_00²   (shape spectrum)   ψ = π^{1/3} (6V)^{2/3} / A   d_eq = (6V/π)^{1/3}
edge       I(d) = bg + Δ · ½ erfc((d − d0) / (√2 σ_obs))            d = signed distance to the 50 % consensus surface
           σ_int = √(σ_obs² − σ_psf²),  σ_psf = √((2σ_xy² + σ_z²)/3) from the scan's own fingerprint (#15)
HU         interior = d < −max(1 mm, 2σ_obs);  HU = median;  texture σ = √(σ_MAD² − σ_noise²)
check      SH(l ≤ 3) → partial-volume voxels (3³ sub-samples) → ⊗ PSF → corr3d(simulated, real) in mask ⊕ 2 vox
```

## Parameters

| Parameter | Value | Source |
|---|---|---|
| LIDC subset | 20 scans, slice ≤ 2.5 mm, deterministic by patient id, ~7 per type | plan Q1 |
| nodule inclusion | ≥ 3 readers (≤ 4: clusters pylidc could not split are dropped), d ≥ 6 mm | ours |
| consensus | 50 % reader agreement (pylidc) | standard |
| type | median LIDC texture rating: ≤ 2 ground-glass, < 5 part-solid, 5 solid | plan AC-3 |
| SH order | library lmax = 4; reproduction lmax = 3 | [F01] eq. 1 uses l ≤ 3 |
| edge bins | 0.25 mm, d ∈ [−4, 6] mm, bin medians | ours |
| GGO/solid HU reference | −400 / −160 HU | [F06] |

## Paper's claimed result

[F01] §3, Table 1: over 17 simulated-to-real comparisons (lung metastases, 8–20 mm), the 3-D correlation
coefficient was **0.8897 ± 0.0609**.

## Our reproduction (number + figure)

Commands:
- `python -m F_render.src.lesion_fit --lidc 20`, then `python -m F_render.repro.r14_lesion_fit`.
- Run dirs: `F_render/runs/*-lesion-fit/` (the per-nodule scalar table `nodules.json`) and `*-repro-14/`.

| Population | 3-D correlation | n |
|---|---|---|
| **solid LIDC nodules, 8–20 mm** (like-for-like: [F01]'s metastases are solid) | **0.8699 ± 0.0664** | 11 |
| [F01] | 0.8897 ± 0.0609 | 17 |
| all types, 8–20 mm | 0.7141 ± 0.2422 | 22 |
| per type, all sizes: solid / part-solid / ground-glass | 0.830 / 0.792 / 0.417 | 20 / 11 / 10 |

- **Solid nodules:** agree. The difference is −0.020, within one paper sd (z = −0.79).
- **Ground-glass nodules:** they correlate poorly with a uniform-HU SH model. Their appearance is internal texture (air bronchograms,
  heterogeneous opacity), not shape. That is why the render adds texture and why the library keeps a per-type texture σ.

Figure: [`r14-lesion-library.png`](../figures/r14-lesion-library.png).

**Library** (`F_render/library/lesion_model_library.json`, scalars only):
- 41 nodules fitted.
- 2 skipped: the edge fit did not converge.

| Type | n | HU mean ± sd | edge σ_int (mm) | ψ | texture σ (HU) | P_2 |
|---|---|---|---|---|---|---|
| solid | 20 | −22 ± 132 | 1.13 ± 0.62 | 0.78 | 87 | 0.014 |
| part-solid | 11 | −163 ± 175 | 1.48 ± 0.64 | 0.78 | 74 | 0.019 |
| ground-glass | 10 | −629 ± 96 | 1.10 ± 0.64 | 0.78 | 54 | 0.035 |

The ground-glass mean is below [F06]'s −400 HU and the solid mean is above −160 HU, so the types are consistent with [F06].
The solid mean is lower than typical soft tissue (~+30 HU). Small solid nodules keep partial volume in their "interior" on 2.5 mm slices.

## Adaptation

- `F_render/src/lesion_fit.py`:
  - pylidc consensus masks;
  - marching-cubes surface → SH;
  - signed-distance erf edge with the scan's own PSF removed (#15);
  - robust interior HU and texture;
  - an aggregate per type → `lesion_model_library` contract.
- `F_render/src/lesion_render.py` uses the library in four ways:
  - `hu` sets the class HU (sampled within ±2 sd);
  - `edge_profile.sigma_mm_*` sets the edge;
  - `sh_l*_power_*` drives margin `lobulated`;
  - `texture_std_hu_mean` sets the [H01] texture amplitude.
- **Max rule** ([F01] §2): in `insert.py`, `hybrid = A + N + max(A, B + δ) − max(A, B)`. Vessels brighter than the lesion
  stay, and nothing is summed.
- **Privacy:**
  - pixel data are read from `~/data/LIDC-IDRI` (outside the repo) into memory only;
  - the committed library is about 4 KB of scalars;
  - the per-nodule scalar table stays in the gitignored run dir.

## Verdict

**adapted.** The SH-reconstruction fidelity is reproduced on solid nodules, and the fitted library drives the F render.
Solid edge widths are fitted, not taken from Solomon–Samei (paper missing).

## What to reuse next

- **H:** the per-type HU and edge distributions are the physics-realism reference ("HU profile, 10–90 % edge width vs LIDC").
- **B:** type frequencies by LIDC texture rating could inform rulebook priors. Only published statistics may be used; our 41-nodule
  table is a convenience sample, not a prior.
- **INT:** more scans → tighter per-type statistics (`--lidc N`).
