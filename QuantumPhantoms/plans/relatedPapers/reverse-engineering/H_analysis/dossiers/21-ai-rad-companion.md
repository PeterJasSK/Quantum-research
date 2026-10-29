# #21 — Siemens AI-Rad Companion Chest CT (documented-interface black box)

**Letter:** H ([`H_analysis`](../README.md)) · **Priority:** ★ · **Kind:** classical · **Papers:** — (vendor whitepaper / documented interface only) · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

AI-Rad Companion Chest CT (Siemens Healthineers) is a commercial, software-only assistant for adult thoracic CT: lung nodule detection and measurement, lung/lobe density, and cardiovascular and musculoskeletal modules. We treat it strictly as a **documented-interface black box**: we know what goes in (DICOM CT) and what comes out (structured report), nothing inside. **No decompiling, no reverse engineering of binaries, ever.** Status: dissected from public documentation; nothing run; official access to be asked of Jan (no one contacted).

## Equations

None: no model is published. Planned acceptance statistics for the longitudinal test: volume error `e_V = (V_reported - V_true) / V_true` per lesion (Bland-Altman bias and 95 % limits of agreement), diameter error in mm, and volume-doubling-time error `e_VDT = VDT_reported - VDT_true` with `VDT = Δt ln2 / ln(V2/V1)`.

## Parameters

| Item | Documented | Source |
|---|---|---|
| Input | Adult thoracic CT, DICOM; software-only | https://fda.innolitics.com/device/K183271 |
| Indication | adults ≥ 22 y for the sub-solid nodule update (K233753, 2024), DICE / bias / RMSE vs ground truth | https://fda.innolitics.com/device/K233753 |
| Pulmonary update | K213713 (2022); no acceptance numbers for lobe segmentation given | https://fda.innolitics.com/device/K213713 |
| Product description | Pulmonary / cardiovascular / musculoskeletal modules, runs on teamplay | https://academy.siemens-healthineers.com/_/en-us/whitepaper-features-data-and-algorithms-ai-rad-companion-chest-ct |
| Slice thickness, spacing, kernel, coverage, positions | **(verify)** not found in the search snippets; see `src/airad_requirements.json` | 510(k) summaries on accessdata.fda.gov |

## Paper's claimed result

No paper. Stated performance (510(k) summaries): retrospective evaluation on > 4,500 CT datasets for the first clearance (K183271); sub-solid nodule segmentation reported as DICE, bias, RMSE (K233753). Exact numbers **(verify)**.

## Our reproduction (number + figure)

Not reproducible without access. `status.json`: `reproduced: null`, note "no access; documented-interface only". Harness ready: `python -m H_analysis.src.airad_check <dicom_dir>` checks a DICOM series against the encoded documented requirements; checked on a LIDC host series as a smoke test (modality, thickness, spacing, kernel, coverage and position lines print; `adult_patient` is unknown because LIDC strips age).

## Adaptation

Longitudinal protocol: E baseline/follow-up snapshots → F hybrids (known ground-truth masks) → G DICOM export → submit both timepoints → compare reported diameter/volume and growth with the ground-truth mask: per-lesion volume error, VDT error, Bland-Altman limits, fraction of lesions detected at baseline and follow-up. Acceptance: |bias| of volume error < 10 % and VDT classification (growing vs stable at a 400-day threshold) agreement ≥ 0.8 (thresholds are ours, to be agreed). Status: awaiting official access (Jan).

## Verdict

Dissected. Claim level n/a. Not run.

## What to reuse next

When access exists: export the pilot cohort through G's DICOM export, run `airad_check` on it first, then execute the protocol above and add the numbers to the `utility` section of the report.
