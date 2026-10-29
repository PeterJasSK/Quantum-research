# #19 — CT-GAN as a tamper test

**Letter:** G ([`G_provenance`](../README.md)) · **Priority:** ★★ · **Kind:** classical · **Papers:** G01 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

G01 (Mirsky, Mahler, Shelef, Elovici, *CT-GAN: Malicious Tampering of 3D Medical Imagery using Deep Learning*, USENIX Security 2019, arXiv 1901.03597) shows that an attacker with access to a hospital's PACS can add or remove lung nodules in a 3-D CT so that radiologists and screening AI accept the result.

- **Attack model (§4).** The scan is reached as *data-in-motion* (PACS traffic is often unencrypted) or *data-at-rest* (infected workstation or PACS server). The attacker edits pixels and leaves the DICOM header alone.
- **Pipeline (§5.3, 14 steps).** 1 capture; 2 localise and cut a cuboid; 3 rescale to 1:1:1 mm (3-D spline); 4 histogram equalisation; 5 normalise to [−1, 1]; 6 zero the central 16³ of a 32³ cube; 7 in-paint with a conditional GAN (pix2pix style, one injector, one remover); 8 denormalise; 9 un-equalise; 10 rescale back to the scan's spacing; 11 touch-up (Gaussian noise plus sigmoid-weighted merge); 12 paste; 13 repeat (removal needs a second pass); 14 return the data in the original format.
- **Why G cares.** The paper's own countermeasure (§7.2) is: *"The best way to detect this attack is to have the scanner sign each scan with a digital signature."* Our receipt does exactly that, plus a commit-before-draw order and a hash-chained ledger. CT-GAN is therefore the right adversarial test for the receipt: signed pixels must stop verifying the moment a pixel changes.

Framing: this is a traceability validation (does the data still match what was committed and signed?), not a security product.

## Equations

Step 11 merge (G01 eq. 1–2):

```text
W_{α,β}(x) = G(x) / (1 + exp(−(x + α) / β))                 (1)
merge_{α,β}(x, y) = W_{α,β}(x) · x + (1 − W_{α,β}(x)) · y   (2)
```

`x` is a cuboid in HU, `G` a 0–1 normalised Gaussian kernel (a smoothed region mask), `α` the HU threshold between wanted and unwanted voxels, `β` the sigmoid slope. With α = 500 the weight is ≈ 0 for air (≤ −900 HU) and ≈ 1 for soft tissue (≥ −300 HU), so generated tissue is copied in and the original lung noise is kept elsewhere.

Our reading of the argument: the paper's text does not say which cuboid `x` is taken from. We evaluate `W` on the voxel-wise maximum of the generated and the original cuboid, so that an injection copies new tissue in and a removal replaces old tissue. This is the one place where we interpret rather than copy.

## Parameters

| Parameter | Value | Source |
|---|---|---|
| cuboid | 32³ voxels at 1 mm | G01 §5.2 / step 3 |
| mask | central 16³ | G01 §5.2 / step 6 |
| resampling | 3-D spline, order 3 (`scipy.ndimage.zoom`) | G01 step 3, 10, footnote 14 |
| equalisation | histogram equalisation, then [−1, 1] | G01 steps 4–5 |
| touch-up noise | N(0, σ²), σ = std of voxels < −600 HU in the original cuboid | G01 step 11 |
| α, β | 500, 70 | G01 step 11 ("worked best") |
| nodule (ours) | diameter U(10, 16) mm, 0–60 HU, soft edge | G01's ≥ 10 mm trial nodules; step 7 replaced |
| training set (GAN, not run by us) | 11,323 injector samples (LUNA16-style data, augmented ×67: flips, shifts, rotations); 867 remover micro-nodules | G01 §5.2 |

## Paper's claimed result

- Readers (3 radiologists, §6): **99 %** of injected cases diagnosed as malignant, **94 %** of removals diagnosed as healthy; after being told about the attack, **60 %** (injections) and **87 %** (removals). A lung-cancer screening AI was fooled in **100 %** of tampered cases.
- Countermeasure claim (§7.2, the one we reproduce): scanner-side digital signatures detect the attack; the DICOM standard already allows signatures in the file, but PACS rarely use them. Other options named: watermarking, noise-pattern (PRNU) forensics that they found did not work out of the box on CT.

## Our reproduction (number + figure)

`python -m G_provenance.repro.r19_ctgan_tamper --n 20` on the stub phantom (160×128×80 voxels, 2×2×2.5 mm). Run record: `G_provenance/runs/<ts>-r19/`.

| attack | detected | failing checks |
|---|---|---|
| pixel injection (CT-GAN style, ×20) | 20 / 20 | `voxels` |
| pixel removal (×20) | 20 / 20 | `voxels` |
| (a) edit `seed_hex` in the tag | 1 / 1 | `signature`, `ledger_entry` |
| (b) (a) + re-sign with a fresh key | 1 / 1 | `trusted_key`, `ledger_entry` |
| (c) (b) + rewrite the ledger consistently | 1 / 1 | `trusted_key` only |
| (d) delete the commit entry and re-chain | 1 / 1 | `commit_first`, `ledger_entry` |
| control: untampered series | 0 flags | — |
| control: re-save with an unbound tag (`InstitutionName`) edited | 0 flags | — |

- Localisation: for every pixel tamper the verifier's list of failing slices equals the set of slices that actually changed (Jaccard 1.00).
- Stealth (not a gate): inside the cuboid the edit is large (mean |ΔHU| ≈ 560–580 on changed voxels, max ≈ 900, because the phantom has a 1000 HU step between air and tissue); outside the cuboid ΔHU = 0; the plain DICOM header of every tampered file is byte-identical to the original's. Pixel tampering is invisible to anything that does not recompute the voxel hash.
- **Honest limit (attack c).** A full re-forge with a *stolen or attacker-controlled key* and a ledger rewritten end to end is caught only because the verifier pins the public key. Without a pinned key (or an external anchor for the ledger head, e.g. a public randomness-beacon pulse; see C dossier #5, last row of the ledger template) nothing in the file set can distinguish it from the original. This is a property of any self-contained signature chain, not something G fixes.
- Not reproduced: the reader and AI numbers above (need radiologists and the trained GAN; H's reader-style test is the place for that).
- Figures: [`r19-ctgan-tamper.png`](../figures/r19-ctgan-tamper.png) (removal and injection on exported slices, |ΔHU| map, per-slice FAIL strip) and [`r19-detection-table.png`](../figures/r19-detection-table.png).

## Adaptation

- **No GAN.** This machine has no torch / TensorFlow / GPU, the paper's GAN is trained on patient scans (privacy), and nothing from the paper's code or weights is used. The repository `ymirsky/CT-GAN` is MIT licensed (checked 2026-10-29), so reading it is not a licence problem, but we did not need it. Step 7 is replaced by a classical in-painter: removal = harmonic (Laplace) fill of the masked 16³ from its boundary (exact discrete solution, sparse LU); injection = that fill plus a soft-edged solid nodule. The signature check does not depend on how realistic the pixels look, only on the fact that they changed.
- **3-D only.** All steps run on the 3-D array; 2-D appears only at DICOM export (one file per axial slice).
- **Our contract.** The receipt binds the voxels through `params_sha256` → `bound_params.json` (canonical voxel hash + one hash per slice + grid), so the verifier names the tampered slices. DICOM carries the receipt in private group `0x0011` (creator `QP-RE G PROVENANCE`) in every slice file.
- **Stub-input exemption.** Stub inputs predate any commit, so the order and code checks are skipped for them and the exemption is written to `fill_report.json`. With real upstream files (a C certificate made after the commit) the order check passes; made before the commit it fails; a one-comment edit to C's code after the commit fails the code check (all checked by hand, see the plan §9).

## Verdict

**Adapted.** G01's §7.2 countermeasure claim holds in our setting: signed provenance flags 40 / 40 CT-GAN-style pixel edits (injection and removal), localises the tampered slices exactly and gives 0 false positives on the two controls. Claim level: n/a (classical; no quantum claim). The one thing the signature cannot do alone is stop a forger who controls the trusted key.

## What to reuse next

- **H:** the tamper-detection rate and per-slice localisation as a reportable statistic; the reader numbers (99 % / 94 %) are the part H's in-context visual Turing test would have to supply.
- **INT:** put a real receipt at the end of the A→G chain (commit before the draw, fill after F), then run `python -m G_provenance.src.verify` on the exported series. Decide CCR-G1..G4 (README).
- **Upgrade path:** DICOM Digital Signatures Sequence (PS3.15, PS3.3 C.12.1) instead of a private tag block; anchoring the ledger head in a public beacon pulse to close the attack-(c) gap; key management beyond a pinned demo key.
- `ctgan_tamper.py` is reusable as a generic 3-D in-painting / injection test fixture for any pixel-integrity check.
