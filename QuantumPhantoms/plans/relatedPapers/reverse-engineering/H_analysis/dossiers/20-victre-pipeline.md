# #20 — FDA VICTRE pipeline

**Letter:** H ([`H_analysis`](../README.md)) · **Priority:** ★★ · **Kind:** classical · **Papers:** H03 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

VICTRE (Virtual Clinical Trial for Regulatory Evaluation, Badano et al., JAMA Netw Open 2018, [H03]) is a complete in-silico imaging trial: 2,986 procedural breast phantoms in four density classes, lesion insertion (a 5 mm spiculated mass at +2 % contrast, or a cluster of 5 microcalcifications), a physics-based imaging chain (Monte Carlo MC-GPU of a Siemens Mammomat Inspiration copy; digital mammography and filtered back-projection DBT), and 30 computational readers analysed with a fully-crossed multi-reader multi-case (MRMC) study. The point is the chain phantom → lesion → imaging → observer → statistics, with the observer a **channelized Hotelling observer (CHO)** so the trial runs without human readers. We reuse the *study architecture* and the reader/statistics machinery, not the breast physics.

Source: Europe PMC full text of PMC6324392 until the PDF is added to `../papers/` (plan Q3). Code reference: `github.com/DIDSR/VICTRE` is **CC0 1.0** (licence file checked 2026-10-29); read-only reference, no code copied.

## Equations

```text
LG channels   u_j(r) = (sqrt(2)/a) exp(-pi r^2 / a^2) L_j(2 pi r^2 / a^2),  j = 0..4   (a = channel width)
channel out   v = U^T g                         g = vectorised ROI, U = [u_0 .. u_4]
CHO template  w = K_v^-1 (mean_v(signal) - mean_v(absent)),   K_v = average class covariance of v
test stat     t = w^T v
AUC           (1/(N0 N1)) sum_i sum_j [ 1(t_pos_j > t_neg_i) + 0.5 1(t_pos_j = t_neg_i) ]
MRMC variance (Gallas 2006)  Var(AUC) = sum_k n_k M_k / (R N0 N1) - M_8,  8 moments M_k of the U-statistic kernel
              over (reader, negative case, positive case) index-sharing patterns; readers and cases random
```

## Parameters

| Parameter | Value | Source |
|---|---|---|
| Phantoms | 2,986 in 4 density classes | [H03] Methods |
| Lesions | 5 mm spiculated mass (+2 %), 5-calcification cluster | [H03] |
| LG channels | 5 | [H03] |
| Readers | 30, each trained on 100 pairs drawn from a pool of 260 (dense) / 1000 (heterogeneous) | [H03] |
| Test sets | 360 neg / 500 pos (dense); 1500 neg / 2000 pos (heterogeneous) | [H03] |

## Paper's claimed result

AUC DM 0.9005 (SE 0.0058), DBT 0.9596 (0.0035), ΔAUC 0.0587 (0.0062); masses Δ 0.0903, calcifications Δ 0.0268. SE(ΔAUC) of the heterogeneous group 0.0073 (Table 2), dense group 0.0148. The comparator human trial gave Δ 0.043 (0.017), with the calcification sign opposite. Table 2 "Total" lists DM 0.9009, which is inconsistent with the 0.9005 quoted elsewhere. The DM/DBT AUCs themselves are **reported, not reproduced** (no MC-GPU breast chain; plan Q2).

## Our reproduction (number + figure)

**R20a, CHO = analytic ideal observer** (`repro/r20a_cho_ideal.py`, `figures/r20a_cho_vs_ideal.png`): Gaussian signal on white noise, 5 amplitudes spanning AUC 0.6-0.98, 30 readers; max |AUC_CHO - AUC_analytic| = **0.0054 < 0.01, agreement yes**. Two deviations from the plan text, both forced by statistics rather than by the observer: the agreement criterion uses readers trained on 1000 pairs (a CHO trained on 100 pairs pays a finite-training penalty of up to 0.025 AUC at low AUC, printed alongside), and the test set has 20,000 pairs (2000 pairs leave a +-0.013 common-test-set error at AUC 0.6, larger than the 0.01 criterion).

**R20b, VICTRE design → SE(ΔAUC)** (`repro/r20b_victre_design.py`, `figures/r20b_mrmc_se.png`): lumpy-background surrogate, two paired modalities tuned to AUC ≈ 0.90 / 0.96, exact heterogeneous design, ρ swept over {0, 0.25, 0.5, 0.75}. Our SE band is **[0.0033, 0.0051]; the paper's 0.0073 lies outside it: agreement NO.** Dense group: ours [0.0068, 0.0105] vs paper 0.0148, also outside. Our surrogate is too homogeneous: the paper's SE includes lesion and phantom variability that this surrogate does not model. The target is therefore **not marked reproduced**; see the README for the open decision.

## Adaptation

Adapted to 3-D lung CT in the validation harness `src/report.py`: 3-D radially symmetric LG channels with `a` scaled to the median lesion diameter, location-known-exactly detection, train-synthetic/test-real versus train-real/test-real, MRMC ΔAUC from `src/mrmc.py`, plus a 2-D central-slice CHO for comparability. Companion sections: realism (HU, edge, NPS), radiomics, drift, certificate statistics, classical baselines. Provenance: every statistic is reported next to its null/baseline.

**In-context visual Turing test protocol** (from Chuquicusma et al., F10; benchmark accuracy 64-66 % [F08], goal ≈ 50 %): 40 cases (20 real LIDC nodules, 20 synthetic), shuffled, size/type-matched, 96 mm axial lung-window crops through the lesion centroid; reader marks real/synthetic and confidence 1-5; blinded (the key is never shown); scored with `turing_score` (accuracy, Clopper-Pearson CI, binomial test vs 0.5). Readers are future work; a developer self-read is a non-expert pilot only (plan Q7).

## Verdict

Dissected; study architecture adapted. Claim level `n/a` (classical analysis). R20a passes; R20b does **not** match the paper's SE, so the target stays below `reproduced` pending a decision.

## What to reuse next

INT runs `python -m H_analysis.src.report` unchanged on the integrated A→G output. CCR-H1 (sub-schemas for the six report sections), CCR-H2 (state encoding), CCR-H3 (type on hybrid_volume) are listed in the README.
