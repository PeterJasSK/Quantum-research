# Reverse-engineering targets: full pipeline

**Date:** 2026-10-28 · **Context:** [../analysis-stages-B-D-F.md](../analysis-stages-B-D-F.md), [../README.md](../README.md) · **Epic:** [epic-reverse-engineering.md](epic-reverse-engineering.md)
**Meaning:** take the published concept, decompose it, and re-implement it standalone in this folder. This is independent of the MVP. Do not copy proprietary code.
Codes in brackets (B01, HW04 …) are files in `../papers/`. Code links marked "(verify)" have not been checked.

★★★ = do now · ★★ = analyse deeper, rebuild parts · ★ = read only

---

## B: mapping biology + CT context into the circuit

1. **★★★ Bayesian-network → circuit compiler** (Low–Yoder–Chuang B01; Borujeni B09, B10)
   - Extract: CPT → controlled-Ry mapping, multi-state nodes on several qubits, ancilla use for multi-control, transpiler-level comparison.
   - Build: a general compiler from rulebook + CT context to circuit, so no circuit is hand-written. Reference implementation: pyAgrum qBN sampling.
   - Why: core of options B-1 and B-2. New rules then need no new circuit code.
2. **★★ Quantum-enhanced MCMC** (Layden B11; Ferguson–Wallden B12)
   - Extract: quantum proposal with classical accept/reject, and coarse-graining for lattices larger than the chip.
   - Build: a tumor-in-anatomy Ising/Potts energy (vessels attract, pleura repels). Measure mixing time against classical Metropolis.
   - Why: option B-5. A provably correct sampler under hardware noise; the same energy can be reused for growth in D.
3. **★ Quantum blur** (Wootton B04/B05; qiskit-community/QuantumBlur (verify))
   - Use only for shape-seed variation, always with the classical-blur baseline.

## C: certificate

4. **★★★ Entropy accounting from Bell tests** (Pironio C01; Liu 2025 C02; Vazirani–Vidick C05)
   - Extract: min-entropy bound from CHSH, H_min ≥ 1 − log₂(1 + √(2 − S²/4)); hidden test rounds; Toeplitz extractor.
   - Build: CHSH value → number of certified bits → extracted seed.
   - Why: "CHSH > 2" on its own is a label. This turns "certified" into a number.
5. **★★ CURBy / NIST beacon chain** (Kavuri C04)
   - Extract: hash-chained, signed pulse format and its traceability chain.
   - Build: template for our receipt ledger (stage G), and the source of external seeds for test-round choice.

## D: quantum growth

6. **★★★ Quantum causal-state (memory-efficient) process models** (Gu D06; Elliott D17; Wu D16; Palsson D07; Ghafari D08)
   - Extract: q-machine construction for renewal and Markov processes; computation of C_q vs C_μ.
   - Build: a quantum model of the division-timing/fate process on 2–4 Heron qubits, with measured memory advantage.
   - Why: option D-5, the headline L1′ result. Nobody has done this for tumor growth.
7. **★★★ Goldilocks quantum cellular automata** (Hillberry D13; Jones D14; Farrelly D03)
   - Extract: gate decomposition of the rule; mutual-information network and complexity metrics.
   - Build: first reproduce the 1-D chain rule on Heron, then a heavy-hex-native neighbourhood variant. The measured snapshot becomes the CA initial shape.
   - Why: option D-3, the bridge from quantum growth to the image.
8. **★★★ Dynamic-circuit feed-forward** (Bäumer HW05; Córcoles HW06)
   - Extract: measure → conditional-gate patterns, latency handling, ancilla reset.
   - Build: option D-2, all generations in one job with hidden CHSH rounds plus the DD lever (PJ2.5).
   - Why: the whole lineage and its certificate sit under one job ID and one calibration.
9. **★★ Belief-propagation simulator of heavy-hex circuits** (Tindall HW04; ITensorNetworks (verify))
   - Use the competitor as our adversary: run every D circuit through it and quantify how classically simulable it is.
   - Why: makes the "no L2 claim" statement quantitative instead of a disclaimer.
10. **★ Measurement-induced transition** (Koh D15)
    - Only the trick that avoids post-selection, and only if option D-4 is chosen.

## E: classical growth

11. **★★★ Pixel2Cancer** (E01; MrGiovanni/Pixel2Cancer (verify)), plus Kansal–Torquato layers (E02)
    - Extract: growth/invasion/death rule parameters, organ-mask constraint, cell state → HU mapping, blending.
    - Build: a lung port with proliferating, dormant and necrotic layers. This is the stage-E engine.
12. **★ High-performance CA** (Poleszczuk–Enderling E03)
    - Data structures for millions of cells. Only needed when a cohort is large.

## F: render into CT

13. **★★★ SyntheticTumors / Label-free pipeline** (H01; MrGiovanni/SyntheticTumors (verify))
    - Extract: texture synthesis (smoothed Gaussian noise), shape deformation, mass-effect and capsule post-processing.
    - Why: the fastest realism win.
14. **★★★ Lesion-model fitting** (Ambrosini F01; Solomon–Samei, PMB 2014 (manual download))
    - Extract: shape and edge-profile parameterisation, and the fitting procedure.
    - Build: fit to LIDC nodules and keep a parameter library. Only parameters leave the patient data, so privacy holds.
15. **★★★ Scanner fingerprint estimator** (Sanders MTF 2016; Divel–Pelc 2019; Peng F05)
    - Extract: MTF from the air–skin edge, local NPS, local σ map.
    - Build: a per-host-scan module whose output drives the PSF blur and the noise matching.
16. **★★ Projection-domain insertion rebuilt on XCIST** (Mayo F03; XCIST (`pip install gecatsim`); Mayo LDCT raw data A06)
    - Mayo's code is not public. Re-implement: forward-project the lesion with the Siemens raw-data geometry, add it to the raw data, reconstruct with FBP.
    - Why: the Siemens-native upgrade without Duke.
17. **★★ DukeSim NAEOTOM Alpha parameters** (McCabe F04)
    - Only the published spectra, thresholds and noise correlation, written as an XCIST configuration.

## A: placement (feeds B)

18. **★★ SYN-LUNGS placement logic** (A01; lungmask A03; TotalSegmentator A04)
    - Re-implement the anatomy-informed placement rules on LIDC.

## G: signing / provenance

19. **★★ CT-GAN as a tamper test** (G01)
    - Re-implement injection and removal only to show the signature check catches both. Present it as a traceability validation.

## H: analysis / use

20. **★★ FDA VICTRE pipeline** (H03; DIDSR/VICTRE (verify))
    - Template for the study architecture (phantom → lesion → imaging → model observer) and for the model-observer analysis.
21. **★ Siemens AI-Rad Companion Chest CT**
    - Black-box test target through its documented interface and whitepaper only. **No decompiling** (licence). Ask Jan for official access.

---

## Not worth reverse engineering

- **FRQI/NEQR CT amplitude encoding:** the data-loading cost cancels any benefit [B13].
- **Carleman PDE solvers [D21] and quantum amplitude estimation:** fault-tolerant hardware only.
- **Quantum-walk invasion [D19, D20]:** tumors do not spread ballistically.
- **MAISI [F11] and DiffTumor [F07]:** large models trained on patient data. Ablation arm only.
- **QALife 2018 [D01]:** already reproduced in this repo.

## Suggested order

1. #11 + #13: working lung tumors in real CT.
2. #15: realism.
3. #4: "certified" becomes a number.
4. #1: stage B becomes general.
5. #6: the quantum headline.
6. #7 checked by #9: the QCA bridge, with honest simulability numbers.