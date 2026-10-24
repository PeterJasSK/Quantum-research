# Siemens Idea 2 — Certifiably-Quantum Synthetic Medical Data: can a quantum circuit Born machine produce a *provably non-classical*, *non-memorising* distribution of medical-image features that classical diffusion cannot?

**Tag: QUANTUM · siemens · effort: medium**

## Pitch
Siemens Healthineers explicitly wants synthetic CT/MR to train ML detectors — and generative sampling is the *one* QML setting that dodges the data-loading wall (you sample a new distribution, you don't load a giant image in). A quantum circuit Born machine (QCBM / quantum GAN) samples a distribution; the twist nobody else brings is that we can **certify the samples are non-classical** (entanglement witness on the generator state) and argue the quantum sampler **does not memorise an individual patient** — the exact failure mode that makes classical diffusion (NVIDIA MAISI et al.) a privacy liability (diffusion re-identifies training patients, arXiv 2305.07644). The claim is not "prettier images." It is "a distribution with a certificate and a privacy property classical diffusion lacks."
**Paper strength score: 73/100** — strong Siemens fit, reuses QuantumTree, and the certify-non-classicality + anti-memorisation reframe makes even a quality-null publishable; docked because classical diffusion image quality is genuinely hard to approach.

## How it becomes a study
**Research question:** Can a QCBM trained on a low-dimensional medical-image feature (1-D intensity profile / small patch histogram) produce a distribution that (a) passes an entanglement-witness certificate of non-classicality and (b) demonstrably does not memorise individual training samples, where a matched classical generator does one or neither?
**Hypothesis (falsifiable):** The QCBM matches a classical small-data baseline on distributional fidelity while scoring strictly lower on a memorisation/re-identification metric and carrying a positive non-classicality witness the classical model cannot have.
**Method:** Take a public CT/MR dataset, reduce to a low-D feature (line profile across a lesion, or PCA of small patches). Train a QCBM (reuse QuantumTree's generative + certification code) and a matched-capacity classical baseline. Fix training-set size small (the regime where diffusion memorises). Swap *only* the generator.
**Baseline:** Classical small generator (tiny GAN / KDE / shallow diffusion) on the identical feature and training-set size.
**Metrics:** distributional fidelity (MMD / KS / Wasserstein to held-out real); **memorisation score** (nearest-neighbour distance from each synthetic sample to its closest training sample — low = memorised); entanglement-witness value on the generator state (certificate present/absent); samples needed for stable fidelity.
**Novel contribution:** The first synthetic-medical-data generator carrying a *certificate of non-classicality* plus a measured anti-memorisation (privacy) property — the one thing classical diffusion provably cannot offer.

## THE VISUALIZATION
Split screen: left, classical diffusion samples with faint "ghost" outlines of real patients it memorised (nearest-neighbour lines snapping to the training set); right, QCBM samples with no such snap, stamped with a live witness badge "⟨XX⟩+⟨ZZ⟩ > 1 — certified non-classical." One slider shrinks the training set; the classical side lights up red (memorising) while the quantum side stays clean. One screen = "quantum sampling you can certify and that doesn't leak a patient."

## Connection to what already exists
Direct reuse of `QuantumTree` (already a certified quantum generative model) and the entanglement-witness machinery proven in the QALife motile work (⟨XX⟩+⟨ZZ⟩≈1.96 survived on `ibm_marrakesh`). This is the **lead candidate** from ideas.txt Part 3 (A) and the scraped verdict (#2).

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** You land exactly what Jan named, with a certificate and a privacy angle no classical competitor has — a clean, ownable, Siemens-shaped claim.
**Bear:** Classical diffusion is so strong that "quantum matches on fidelity" looks underwhelming unless the privacy/certificate reframe lands with reviewers.
**Likely:** QCBM matches a small-data classical baseline on fidelity, wins on the certificate and on memorisation — a modest but honest and uniquely-framed result.
**Value if null:** Even if the QCBM loses on fidelity, a measured "here is the non-classicality certificate and the privacy gap" defines the one axis where quantum generation is *qualitatively* different — the scaling story Siemens funds.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Does certifiably-quantum generation buy a medical-data property classical diffusion cannot? **Single defended claim:** a QCBM on a low-D medical feature carries a non-classicality certificate and a lower memorisation score than a matched classical generator at equal fidelity. **Why 6–8 pp:** one generator, one feature, one fidelity + one memorisation + one witness figure. **Target venue:** IEEE QCE / a medical-imaging ML workshop (MICCAI-adjacent). **Compelling-study likelihood: 73/100.**
