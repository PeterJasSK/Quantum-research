# Validation plan: are the synthetic CT scans actually great?

Conceptual plan (2026-10-29), not a feature plan. It describes how to turn "the synthetic nodules look good" into a
measured result. The work behind it lives in [`relatedPapers/reverse-engineering/`](relatedPapers/reverse-engineering/)
(letters A–H); see the [index](relatedPapers/reverse-engineering/index.html) for the current state.

## 1. Goal

Prove, on held-out real patients, that the synthetic lung nodules are:

1. **Statistically like real nodules**: radiomics comparison.
2. **Useful for training AI**: train on synthetic, test on real.
3. **Indistinguishable to experts**: a radiologist visual Turing test.

Until these three exist, "great CT scans" is our opinion. Once they pass, it is evidence a clinical partner can check.

The customer here does not care whether anything is quantum, so the validation runs in **classical mode**: C (certificate)
and D (quantum growth) are skipped, and the seed comes from a normal random generator. They never affect how a tumour
looks. G (provenance) still signs every case.

## 2. What already exists

| Need | Already in the repo | State |
|---|---|---|
| Nodule inserted into real 3-D CT | F image-domain insertion, LIDC host render | volume +0.25 ± 1.02 %; noise σ/kurtosis within 2 % |
| Realistic shape | F lesion library fitted on LIDC | shape correlation 0.870 vs paper 0.890 (solid) |
| Growth with baseline + follow-up | E lung automaton | doubling times 148 / 466 / 825 d vs 149 / 457 / 813 d |
| Placement in real anatomy | A (lungmask, TotalSegmentator) | three placement classes on LIDC |
| Real reference nodules | H `lidc_ref` | LIDC ROIs extracted |
| Analysis report | H `report` (realism, radiomics, utility, drift, baseline) | ran on n = 1 only |
| Exact ground-truth masks | every F hybrid | by construction |

## 3. Step 0: build a cohort big enough to test

**Size.**
- 20 LIDC hosts × 3 placement classes × ~5 draws (solid / part-solid / ground-glass, several sizes) ≈ **300 synthetic
  nodules**, each with a baseline and a +90-day follow-up.
- The only slow step is A's segmentation, at 25–75 min per host on CPU. It runs once per host (overnight for 20 hosts) and
  is cached. Each host then gives ~10 sites per class.
- E growth and F rendering take seconds to minutes per tumour.

**Fix before validating** (otherwise the tests only re-discover known bugs):
- **Solid-nodule HU bias (−22 HU, partial volume).** Recalibrate the library on thinner slices or correct the bias.
- **Juxtapleural placement undercount (0.00 vs 0.22).** Without a fix a whole placement class is missing from the cohort.

**Do not fix before validating; measure instead:**
- **Ground-glass texture** (shape correlation only 0.42). The tests show how far off it is, and that is part of the result.

**Engineering prerequisites.**
- Run in classical mode, so the INT chain gaps (G `fill --job`, beacon freshness) do not block anything.
- Render with A's masks rather than F's local threshold masks.
- **No leakage:** a host used to make synthetic nodules never appears in any real test set. Split by patient.

## 4. Test 1: radiomics comparison (about 1–2 weeks)

**Question:** do synthetic nodules have the same measurable properties as real ones?

1. Extract shape, first-order intensity and texture features (GLCM and similar) from synthetic and real LIDC nodules,
   matched by type and size.
2. **Per feature:** compare distributions (Wasserstein distance or KS test, plus effect size). Report which features
   disagree.
3. **All features together:** a classifier two-sample test. Train a simple classifier to tell real from synthetic using the
   features, and report its cross-validated AUC. AUC ≈ 0.5 means indistinguishable.
4. Report per nodule type (solid / part-solid / ground-glass) and per placement class.

**Pre-registered pass bar (proposal):** classifier AUC < 0.6 per nodule type, and no feature with a large effect size.

**Decision:**
- H currently uses radiomics-lite.
- Reviewers will expect PyRadiomics [H05], which needs a one-time install in a separate environment.
- Use PyRadiomics for the published result.

## 5. Test 2: train on synthetic, test on real (about 3–6 weeks, GPU)

**Question:** does synthetic data help a real detector? This is the strongest evidence for usefulness.

1. **Cheap diagnostic first.** Train a small network to tell real patches from synthetic ones.
   - If it wins easily, its saliency maps show *where* the synthetic nodules are wrong (edges, texture, noise).
   - Fix those flaws before the expensive run.
2. **Main experiment.** Train a standard nodule detector or segmenter three times:
   - (a) real LIDC only;
   - (b) synthetic only;
   - (c) real + synthetic.
3. **Test** on held-out real LIDC patients (LIDC has about a thousand annotated scans [A02]).
4. **Metrics:** sensitivity at fixed false positives per scan (FROC, LUNA16-style) and segmentation Dice. Report them
   **per hard-case group:** small, ground-glass, juxtapleural and juxtavascular.

**Success looks like:**
- synthetic-only reaches a solid fraction of real-only performance;
- real + synthetic **beats** real-only on the hard cases.

That is the direct "it helps cancer detection" result. [H01] showed this for liver tumours.

## 6. Test 3: radiologist visual Turing test (about 1–2 weeks to build, then reader time)

**Question:** can experts tell synthetic nodules from real ones?

**Reader app.**
- An offline web viewer in the same style as the project site.
- Scrolls through a 3-D CT patch in lung window.
- Shows real and synthetic cases mixed about 50/50, in random order per reader.
- Records per case: "real or synthetic?", a confidence score, and optionally "would you report this nodule?".

**Readers.**
- 2–5 radiologists (e.g. through a clinical / Siemens contact).
- 150–200 cases each, about 1–2 hours per reader.

**Analysis.**
- Accuracy and ROC AUC per reader and pooled, with confidence intervals.
- "Indistinguishable" means the interval includes 0.5 and stays below a pre-registered bound.
- With ~200 cases the interval is roughly ±0.07, so set the case count from the bound wanted.
- Precedent: Chuquicusma's visual Turing test for lung nodules [F10].

**Paperwork.**
- LIDC is public (CC BY 3.0) and reader answers are anonymous.
- Still check whether the readers' institution requires an ethics or consent form.

## 7. Optional commercial check

H's target #21 already has a protocol. Run baseline and follow-up synthetic cases through Siemens AI-Rad Companion
Chest CT as a black box, and compare its reported diameter, volume and doubling time with the exact ground truth.
If a commercial detector measures synthetic nodules like real ones, that is strong practical evidence. It needs access to
the product.

## 8. Resources

| Resource | Why | Notes |
|---|---|---|
| CPU overnight | A segmentation of 20 hosts | cached afterwards |
| GPU (days) | Test 2 detector training | the main compute cost |
| PyRadiomics environment | Test 1 credibility | one-time install, separate env |
| 2–5 radiologists | Test 3 | the only part that cannot be automated |
| LIDC-IDRI | real reference and test set | already on disk (`~/data/LIDC-IDRI`) |

## 9. Timeline (rough)

| Phase | Duration |
|---|---|
| Cohort + the two fixes | 2–3 weeks |
| Test 1 radiomics | 1–2 weeks |
| Test 2 detector (incl. diagnostic) | 3–6 weeks |
| Test 3 harness | 1–2 weeks, then reader time |
| **Total** | **about 2–3 months** |

Tests 1 and 3 (harness) can run in parallel with Test 2.

## 10. Risks and what to do about them

| Risk | Effect | Response |
|---|---|---|
| Ground-glass texture fails | Tests 1–3 show GGO as distinguishable | treat it as the next fix (texture model); report it by type |
| Patient leakage | results look better than they are | patient-level splits fixed before any training |
| Cohort too homogeneous (LIDC scanners are old) | results do not transfer to modern CT | add Mayo / Siemens hosts later |
| Too few readers | wide intervals in Test 3 | more cases per reader; pre-registered bound |
| Detector too weak or too strong | Test 2 not informative | use a standard, published architecture and training recipe |

## 11. Expected outcome

The first runs will probably fail somewhere, most likely ground-glass texture and partial-volume edges. That is useful:
the radiomics classifier and the real-vs-synthetic patch detector give a ranked list of flaws to fix. When all three
tests pass on held-out real patients, "great CT scans" becomes a measured, reproducible result.
