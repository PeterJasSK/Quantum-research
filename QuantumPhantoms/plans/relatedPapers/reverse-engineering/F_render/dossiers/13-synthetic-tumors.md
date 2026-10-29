# #13 — SyntheticTumors / Label-free pipeline

**Letter:** F ([`F_render`](../README.md)) · **Priority:** ★★★ · **Kind:** classical · **Papers:** H01 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

Hu et al., "Label-Free Liver Tumor Segmentation", CVPR 2023 [H01]. Rule-based synthetic liver tumours are
painted into healthy CT, with no learned generator. There are four steps (§3.1, Fig. 3):
1. pick a location in the liver that avoids vessels;
2. make a Gaussian texture coarsened by up-scaling;
3. make a deformed, edge-blurred ellipsoid mask;
4. post-process with a mass effect (local scaling warp) and a capsule (brightened edge).

The paper reports that a segmentation network trained only on these tumours does as well as one trained on real annotated tumours.
F takes this as the fastest realism recipe and re-implements it from the paper's equations. The code at
github.com/MrGiovanni/SyntheticTumors was **not** copied or read for implementation.

## Equations

```text
vessels   v = [ f ⊗ g(σa) > T ] · l,   T = mean(f · l) + b                                   (1)(2)
texture   T(x) ~ N(µt, σp);  T' = cubic-zoom(T, η);  T'' = T' ⊗ g(σb)                          (3)
shape     t = ellipsoid(half-axes); t' = elastic(t; σe); t'' = t' ⊗ g(σc)
place     f'   = (1 − t'') f + t'' T''                                                      (4)
mass eff. γ'   = (1 − (1 − γ/γmax)² · I/100) · γ        (pixel at distance γ samples from γ')  (5)
capsule   e = [lb ≤ t'' ≤ ub],  e' = e ⊗ g(σd),  f''' = f'' + d · e'                           (6)(7)(8)
```

## Parameters

From Table 1 and Table 6 of [H01]. µp and σp are the mean and std of the liver parenchyma.

| Symbol | Value | Use |
|---|---|---|
| σa | 0.5 + 0.025 σp | vessel-detection smoothing |
| b | 15 HU | vessel threshold offset |
| µt | U(30, µp − 10) | tumour mean HU |
| η | U(1.1, 1.5) | texture up-scale (grain) |
| σb | 0.6 | texture blur (voxels) |
| σc | U(0.6, 1.2) | mask edge blur |
| γmax | 1.3 r | mass-effect radius |
| I | 30 | mass-effect intensity |
| (lb, ub) | (0.4, 0.7) | capsule band |
| σd | 0.8 | capsule blur |
| d | 120 HU | capsule brightening |
| r / σe | tiny 4 / U[0.5,1]; small 8 / U[1,2]; medium 16 / U[3,6]; large 32 / U[5,10] (voxels) | Table 6 sizes |

## Paper's claimed result

- **Headline (abstract, Fig. 2):** a U-Net trained on synthetic tumours only reaches DSC 59.81 % on real LiTS
  tumours, against 57.63 % when trained on real annotated tumours.
- **Visual Turing test (Table 2):** junior accuracy 26.5 %; senior accuracy 71.0 %, with 19/50 marked unsure.
- **Generation figures (Fig. 3; Appendix Figs 8–10):** qualitative.

## Our reproduction (number + figure)

- **What we reproduced:** the *generation pipeline* (eqs. 1–8), with every Table 1/Table 6 value used as published, on a synthetic
  contrast-liver phantom (no patient data).
- **What we did not reproduce:** the DSC headline. It needs LiTS/CHAOS data and network training, which is out of scope
  (plan Q5).
- **Result:**
  - Generated tumour core mean HU equals the sampled µt: small 101.4 vs µt 98.9; medium 43.2 vs µt 41.9.
  - Core σ ≈ 5 HU, because the σb blur reduces σp = 15, as in the paper.
  - The mass effect and capsule change nothing outside γmax (max |Δ| < 3·10⁻⁵ HU).
  - The stages look like Fig. 3.
- **Agreement:** qualitative + parameter match.
- **Figure:** [`r13-synthetic-tumors-liver.png`](../figures/r13-synthetic-tumors-liver.png).
- **Command:** `python -m F_render.repro.r13_synthetic_tumors` (run dir `F_render/runs/*-repro-13/`).

## Adaptation

Lung adaptation, in `F_render/src/texture.py` and `F_render/src/lesion_render.py`:
- **Shape:** E's cell lattice replaces the ellipsoid. The [H01] elastic deformation still perturbs the outline
  (`deform_alpha_mm` = 0.5, because E's shapes are already irregular).
- **Texture:** the same N → η-zoom → σb recipe, but generated at host-voxel scale and cubic-zoomed onto the 4×
  partial-volume sub-grid. Its σ is **renormalised** to the LIDC-fitted intrinsic texture σ (#14). Liver's
  σp has no lung equivalent.
- **HU:** from the #14 library per type, not U(30, µp − 10).
- **Edge:** the #14 fitted erf edge replaces σc.
- **Mass effect:** eq. 5, applied only to the noise-free anatomy inside the lung mask, so the host's noise is never
  resampled.
- **Capsule:** off for lungs (lung nodules have no capsule). Kept as `RenderParams.capsule` for the liver
  reproduction.
- **Location step:** replaced by A's placement (stub sites, or F-local sites on LIDC hosts).

## Verdict

**adapted.** The recipe is reproduced and is part of the F render. The DSC headline is not reproduced, and is not
claimed.

## What to reuse next

- **H:** the visual Turing test design (Table 2) is the template for the lung in-context reader test.
- **INT:** swap the stub lattice for E's real trajectories; texture and mass effect need no change.
- `texture.mass_effect` / `texture.capsule` are pure functions and can be reused on any 3-D volume.
