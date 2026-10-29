# #17 — DukeSim NAEOTOM Alpha parameters (McCabe)

**Letter:** F ([`F_render`](../README.md)) · **Priority:** ★★ · **Kind:** classical · **Papers:** F04 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

McCabe, Harrawood, Samei & Abadi, Med. Phys. 52(6) 2025 [F04] extend DukeSim with a photon-counting detector model
for the Siemens NAEOTOM Alpha. The model has three parts:
- per-threshold quantum efficiency;
- 3 × 3 crosstalk;
- a spatio-energetic noise covariance between thresholds.

They validate it against the real scanner on the ACR and Mercury phantoms. DukeSim and the detector response files are not public. The value F can take is
the **published acquisition and detector parameters**. Written as an XCIST configuration, they give a Siemens
photon-counting hook without the closed simulator. Nothing was decompiled. Full text was read from PMC12285274, because it is not in
`papers/`.

## Equations

```text
S_t(x, y) = Σ_E  N(E) · QE_t(E) · Σ_{3×3} X_t(E; i, j) · exp(−∫µ(E) dl)      ([F04] eq. 1, threshold t)
noise     = correlated Gaussian with the spatio-energetic covariance (Cholesky)  ([F04] §2.2)
f50       = frequency where MTF = 0.5, measured on an air edge                   ([F04] §2.9)
```

XCIST's `Detection_PC` provides threshold binning with a CZT response. It does not provide F04's CdTe crosstalk/covariance model.

## Parameters

| Parameter | Value | Source |
|---|---|---|
| tube | 120 kV | [F04 §2.9] |
| thresholds | 20, 65 keV | [F04 §2.9] |
| detector pixel | 0.4 mm at isocentre | [F04 §2.2] |
| collimation / pitch | 144 × 0.4 mm / 0.8 | [F04 §2.9] |
| rotation | 0.5 s | [F04 §2.9] |
| dose levels | 1.5 / 3 / 6 / 12 mGy = 19 / 38 / 72 / 152 mAs | [F04 §2.9] |
| recon | ReconCT, QIR-3, Br40/Br56/Br64, 0.4 mm | [F04 §2.9] |
| SID / SDD | 595 / 1085.6 mm | **assumed** (F04 lists them as inputs, not values) |
| sensor | CdTe | [F04 §2.2]; XCIST ships only a CZT 0.25 mm response, so it is approximated |

Config: [`../xcist/naeotom_alpha.cfg`](../xcist/naeotom_alpha.cfg) (cited per line; "(assumed)" / "(reduced)" marked).

## Paper's claimed result

[F04] Table 1 gives MTF f50 for the **real** scanner in the ACR phantom:
- 0.39 ± 0.003 mm⁻¹ (Br40);
- 0.77 (Br56);
- 1.08 (Br64).

DukeSim gives 0.39 / 0.73 / 0.97. Noise magnitude tracks dose with errors of 0.07–1.59 HU on 70 keV VMI (§3.1.1).

## Our reproduction (number + figure)

Command: `python -m F_render.repro.r17_naeotom_spectrum`. Run dir: `F_render/runs/*-repro-17/` (four photon-counting XCIST scans
of a Ø 200 mm water cylinder, ~25 min CPU).

| Quantity | Ours (simulated, XCIST) | Paper [F04] |
|---|---|---|
| f50, pre-registered kernel 'standard' | **0.573 mm⁻¹** (+47 %) | 0.39 mm⁻¹ (real, Br40) |
| f50, kernel 'soft' (checked afterwards, informational) | 0.463 mm⁻¹ (+19 %) | 0.39 mm⁻¹ |
| noise vs dose, 19 → 152 mAs | 65.0 / 46.2 / 33.3 / 23.0 HU, **σ ∝ mAs^−0.501** | tracks dose (Fig. 3) |
| water HU | 12.6 → 12.0 HU | 0 ± 2 HU after water calibration |

- **Agreement on f50:** disagree. The pre-registered XCIST 'standard' FBP kernel is sharper than Br40 + QIR. It lies between the
  paper's Br40 (0.39) and Br56 (0.77).
  - The informational 'soft' kernel lands within 25 %, but it was chosen after seeing the result, so it is not claimed.
- **Noise:** the noise–dose exponent is the quantum-limited −0.5 that a correct photon-counting model must show.
- **Not reproduced:**
  - F04's real-vs-simulated noise errors (needs the real scanner);
  - QIR;
  - the 70 keV VMI.

Figure: [`r17-naeotom.png`](../figures/r17-naeotom.png).

## Adaptation

- **What the cfg is:** an XCIST photon-counting configuration with F04's parameters (T1 ≥ 20 keV summed image), not a
  DukeSim clone.
- **Missing pieces:** the CdTe response, crosstalk and inter-threshold covariance are missing. XCIST's FBP 'standard' kernel stands in for
  Br40 + QIR-3.
- **Valid uses:** a Siemens-flavoured photon-counting forward model for #16-style insertions and for H's noise/MTF
  sensitivity studies.
- **Not valid:** a stand-in for the real scanner.

## Verdict

**dissected** (config delivered, published number not matched). The configuration is usable as a labelled approximation:
it has the right geometry class, pixel, thresholds, kV and dose levels, and quantum-limited noise. The resolution
does not match Br40 without kernel tuning, which we do not claim.

## What to reuse next

- **H:** sweep the four F04 dose levels to test whether detector-level noise realism changes the validation metrics.
- **INT / Siemens:** if Siemens or Duke can provide the PCCT response (QE, crosstalk, covariance), drop it into XCIST's
  `Detection_PC` response slot.
