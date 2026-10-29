# Feature H — Analysis / use: VICTRE-shaped validation harness (model observer + MRMC, realism, radiomics, train-synthetic/test-real, drift, certificate/witness statistics, baselines) + AI-Rad Companion black-box protocol (targets #20, #21)

**Epic:** [`epic-reverse-engineering.md`](./epic-reverse-engineering.md) (Approved, 2026-10-28). H is a wave-2 letter (epic §7), built in its own worktree `re-H`. It depends on W (committed). It benefits from merged C (`249a4fe`), E (`b02dc96`), F (`16c195d`) and G (`6079294`), and from B/D outputs once merged, but runs on `shared/stubs/` by default. Full validation on the integrated output belongs to INT.
**Feature ID:** H
**Author:** Claude (Opus)
**Date:** 2026-10-29
**Status:** Approved (by developer, 2026-10-29; all Q1–Q10 defaults accepted)

> **Technical constraints / core directive.**
> - **Stack.** Python ≥ 3.12 (`shared` needs `Path.relative_to(walk_up=)`), NumPy/SciPy, SimpleITK 2.5.6, pydicom, pylidc 0.2.3, scikit-learn, scikit-image, matplotlib, jsonschema. **PyRadiomics is not installed anywhere** (Q1). No torch in conda base, no GPU on this machine: every observer is a **linear model observer** (CHO), not a deep network.
> - **Classical analysis only.** H runs no quantum job. It *reports* quantum numbers produced elsewhere, each with its sim label, classical baseline and BP simulability number (epic honesty gates). Claim level of H itself: `n/a`.
> - **Scope of writes.** The session writes only inside `RE/H_analysis/` and this plan, where `RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`. `shared/` is frozen and is imported, never edited. Nothing is imported from `QuantumPhantoms/code/` (MVP) or from any other letter: upstream letters are consumed **only through their contract files** (stubs by default, real files via a cohort manifest). Other letters' CLIs may be *run from the shell* to produce a pilot cohort (Q4); their code is never imported.
> - **Commands** run with `RE/` as the working directory.
> - **Privacy.** LIDC voxels are read only for validation references; nothing in H feeds a generator. ROI crops and reader kits stay in gitignored `H_analysis/runs/`.
> - **Framing.** Data credibility and traceability. Never "more realistic because quantum".
> - **No automated tests.** Verification is manual, plus the reproduction step.

---

## 1. Why (Step Goal)

**Before.**
- `H_analysis/` is the W skeleton: README with purpose/inputs/outputs pre-filled, `status.json` with #20 and #21 at `listed`, two empty dossiers, empty `src/` and `repro/`.
- `shared/contracts/validation_report.schema.json` exists, but its six sections (`realism`, `radiomics`, `utility`, `drift`, `certificate_stats`, `baseline`) are **open objects**: nobody has decided what goes in them. The stub report is empty.
- Every other letter has produced numbers (F's hybrid volumes and LIDC lesion library, C's certificates, D's witness records, E's trajectories, G's receipts), but nothing judges them together: is a synthetic nodule physically and statistically like a real LIDC nodule, does an observer trained on synthetics work on real nodules, does the cohort follow the rulebook, how do the certificate and witness numbers distribute, and what does the classical baseline give.
- The H03 (VICTRE), H04 and H05 (PyRadiomics) PDFs are not in `../papers/` (manual download, `../README.md` l. 226–233). The VICTRE full text is available from Europe PMC (PMC6324392).

**After.** H is a standalone validation harness shaped like the FDA VICTRE in-silico trial (phantom → lesion → imaging → model observer → MRMC statistics), applied to 3-D lung CT:
1. **Target #20, VICTRE (Badano 2018, H03):** dissected; its reader machinery rebuilt from scratch: a **Laguerre–Gauss channelized Hotelling observer (CHO)**, location-known-exactly, 30 computational readers each trained on resampled pairs, **fully-crossed MRMC analysis** of AUC and ΔAUC (U-statistic variance, Gallas 2006, the method in iMRMC). Reproduced on two levels (Q2): (a) the CHO hits the analytic ideal-observer AUC on a signal-known-exactly task; (b) VICTRE's trial design (30 readers × 100 training pairs, 1500 neg / 2000 pos test) gives a ΔAUC standard error consistent with the paper's Table 2 SE (0.0073, heterogeneous group). The DM-vs-DBT AUCs themselves (0.9005 vs 0.9596) are reported, not reproduced (no MC-GPU breast imaging chain).
2. **Adaptation to our pipeline**, one CLI that turns a **cohort manifest** into a contract-valid `validation_report.json`:
   - `realism`: per-lesion physics (interior HU, edge 10–90 % width, local NPS/σ) against LIDC real nodules of the same type;
   - `radiomics`: per-feature distribution comparison synthetic vs real + a classifier two-sample test;
   - `utility`: **train-synthetic/test-real** with the 3-D CHO and MRMC ΔAUC against train-real/test-real;
   - `drift`: cohort/shot marginals vs the rulebook (TVD, RMSPE);
   - `certificate_stats`: distributions of CHSH S, H_min, certified bits, witness values, C_q vs C_μ, BP fidelity, receipt/ledger validity, every number sim-labelled;
   - `baseline`: the classical counterpart of every quantum number, plus a seed-source arm showing realism does not depend on where the seed came from.
3. **In-context visual Turing test kit** (protocol from Chuquicusma F10, benchmark 64–66 % [F08], goal ≈ 50 %): offline HTML reader form + scorer. Running it with radiologists is future work.
4. **Target #21, AI-Rad Companion Chest CT:** documented-interface black box only. Dossier from public documentation, an input-conformance checker for our DICOM exports, and a longitudinal test protocol (baseline/follow-up pairs). No access → state `dissected`, nothing run.
5. A **pilot cohort** (Q4) run end to end through the harness, labelled "pilot, pre-INT, under-powered".

INT then runs the same CLI on the integrated A→G output to close the epic.

---

## 2. Acceptance Criteria

- [ ] **AC-1** (H.1) — *Dossier #20 dissected.*
  - `dossiers/20-victre-pipeline.md`, all 8 sections: concept (in-silico trial chain, Siemens Mammomat Inspiration copy, MC-GPU, FBP DBT); equations (LG channels `u_j(r) = (√2/a) e^{-πr²/a²} L_j(2πr²/a²)`, CHO template `w = K_v⁻¹ Δv̄`, AUC from test statistics, U-statistic MRMC variance); parameters (2,986 phantoms in 4 density classes; 5 mm spiculated mass +2 %, 5-calc cluster; 5 LG channels; 30 readers × 100 training pairs from pools of 260/1000; test sets 360/500 and 1500/2000); claimed result (AUC DM 0.9005 (0.0058), DBT 0.9596 (0.0035), ΔAUC 0.0587 (0.0062); masses Δ 0.0903, calcs Δ 0.0268; comparator human trial Δ 0.043 (0.017) with calcs sign opposite; Table 2 "Total" DM 0.9009 inconsistency noted); source = Europe PMC full text of PMC6324392 until the PDF is added (Q3).
  - Licence of `github.com/DIDSR/VICTRE` checked and recorded (read-only reference; no code copied).
  → `H_analysis/dossiers/20-victre-pipeline.md`; `status.json` #20 → `dissected`.
- [ ] **AC-2** (H.2) — *Model observer core.*
  - `observer.py`: `lg_channels_2d(size, a, n=5)`, `lg_channels_3d(shape_zyx, a_mm, spacing_mm, n=5)` (radially symmetric 3-D generalisation; Q5), `cho_train(pos, neg, channels, reg=1e-6)` → template, `cho_score(template, rois)`, `auc(scores_pos, scores_neg)` (Mann–Whitney).
  - `mrmc.py`: fully-crossed U-statistic variance (Gallas 2006) for single-modality AUC and paired ΔAUC with readers and cases random; returns `{auc, se, df, ci95}`.
  - Reader variability = each of `n_readers` readers trains on its own `n_train` pairs drawn with `shared.seedhash.rng(seed_hex, "H.reader.<k>")`, same test set for all readers (fully crossed).
  → `H_analysis/src/observer.py`, `H_analysis/src/mrmc.py`.
- [ ] **AC-3** (H.3) — *Reproduction R20a: CHO = ideal observer where it must be.*
  - Gaussian signal (σ_s = 3 px) on white Gaussian noise, 64², SKE/BKE. Ideal observer `d' = ‖s‖/σ`, `AUC = Φ(d'/√2)`; channel width `a` matched so the signal lies in channel 0.
  - Five amplitudes spanning AUC 0.6–0.98; |AUC_CHO − AUC_analytic| < 0.01 at every point (30 readers × 100 pairs, 2000 test pairs).
  - Prints `paper=analytic ours=<x> agreement=`; figure `figures/r20a_cho_vs_ideal.png`.
  → `H_analysis/repro/r20a_cho_ideal.py`.
- [ ] **AC-4** (H.4) — *Reproduction R20b: VICTRE trial design → ΔAUC SE.*
  - Lumpy-background surrogate (Rolland–Barrett lumps, 64²), two paired "modalities" from the same phantom with amplitudes tuned to the Table 2 heterogeneous-group AUCs; inter-modality case correlation swept ρ ∈ {0, 0.25, 0.5, 0.75}.
  - Exact VICTRE heterogeneous design: 30 readers, training pool 1000 pairs, 100 pairs per reader, test 1500 neg / 2000 pos, fully crossed.
  - Reports our MRMC SE(ΔAUC) per ρ and whether the paper's 0.0073 lies inside the swept band; **reproduced** if it does (Q2). Also prints the dense-group design (pool 260, test 360/500) SE vs paper 0.0148.
  - `status.json` #20 `reproduced{quantity:"SE(ΔAUC), VICTRE heterogeneous design", paper_value:0.0073, our_value:"<band>", agreement, sim_mode:null, figure:"figures/r20b_mrmc_se.png"}`, state → `reproduced`, then `adapted` after AC-8.
  → `H_analysis/repro/r20b_victre_design.py`.
- [ ] **AC-5** (H.5) — *LIDC real-nodule reference set.*
  - `python -m H_analysis.src.lidc_ref --scans <list> [--out]` reads LIDC via pylidc (own `np.int`/`SafeConfigParser` alias shim, re-written, not imported from F), clusters annotations, keeps nodules ≥ 3 mm with ≥ 2 readers, 50 % consensus mask, type from median texture rating (≤ 2 ground-glass, < 5 part-solid, 5 solid — same published mapping as F).
  - Per nodule: 3-D ROI 48³ mm resampled to 1 mm isotropic (linear; mask nearest), centroid LPS, d_eq, type, patient id. Negative ROIs: same size, centred in lung parenchyma (H-local threshold lung mask: −400 HU, two largest air components, hole fill, ≥ 15 mm from any annotation), 3 per scan.
  - Patient-level split (Q6): hosts used for synthetic insertion are disjoint from patients whose real nodules form the test set.
  - Output (gitignored): `H_analysis/runs/<ts>-lidc-ref/{lidc_ref.json, rois.npz}`; `lidc_ref.json` holds only per-nodule scalars + file refs.
  → `H_analysis/src/lidc_ref.py`, `H_analysis/src/roi.py` (shared ROI crop/resample for real and synthetic).
- [ ] **AC-6** (H.6) — *`realism` section.*
  - Per hybrid (type joined via `draw_id` → TumorDraw in the manifest; fallback `extra.type` / "unknown"): interior HU mean/std on the mask eroded by 1 mm; edge = radial profile across the mask boundary, erf fit → σ_mm and 10–90 % width (= 2.563 σ); local σ and 3-D NPS in a 10–20 mm shell outside the lesion, hybrid vs host at the same shell (insertion must not change noise: ratio within ±10 %).
  - Same metrics on LIDC real nodules (AC-5). Per metric and type: synthetic value's percentile in the real distribution, KS D and p when n_syn ≥ 5, pass = inside the real 5–95 % range.
  - Figure `figures/h_realism.png` (synthetic points over real per-type distributions).
  → `H_analysis/src/realism.py`.
- [ ] **AC-7** (H.7) — *`radiomics` section.*
  - Features on 1 mm isotropic ROIs with the lesion mask, fixed bin width 25 HU: PyRadiomics `firstorder`, `shape`, `glcm`, `glrlm`, `glszm` (Q1); fallback "radiomics-lite" (first-order 18 + shape 10 + 3-D GLCM 13 directions, own NumPy, IBSI definitions) labelled as such.
  - Per feature: KS D, p (Benjamini–Hochberg), standardised mean difference synthetic vs real per type; **null** = same statistics for real-vs-real split halves (patient-level, 50 random splits).
  - **Classifier two-sample test:** logistic regression (standardised features, L2) real-vs-synthetic, 5-fold patient-grouped CV AUC with bootstrap CI; 0.5 = indistinguishable.
  - Summary: fraction of features with |SMD| < 0.5, C2ST AUC, both next to the real-vs-real null.
  → `H_analysis/src/radiomics_cmp.py`.
- [ ] **AC-8** (H.8) — *`utility` section: train-synthetic / test-real with the model observer.*
  - Task: LKE detection, nodule present vs absent, 3-D ROIs at 1 mm.
  - Arm S: CHO (3-D LG, `a` scaled to the median d_eq) trained on synthetic positives (hybrid ROIs) vs negatives from the same hosts; arm R: trained on real positives from training patients. Both tested on the same held-out real positives + negatives.
  - MRMC over `n_readers` resampled readers (AC-2): AUC_S, AUC_R, ΔAUC = AUC_S − AUC_R with SE and CI; plus a VICTRE-style per-type breakdown when every type has ≥ 10 test positives.
  - The section records `n_train`, `n_test`, readers, and `powered: false` when n is below the VICTRE heterogeneous design.
  - After this AC, `status.json` #20 → `adapted`.
  → `H_analysis/src/utility.py`.
- [ ] **AC-9** (H.9) — *`drift` section: cohort vs rulebook.*
  - Exact rulebook marginals (and joint, if ≤ 2¹⁶ states) by own NumPy enumeration of the Bayesian network (context-conditioned CPTs, context taken from the compiled circuit).
  - Empirical side, both when present: (a) shot-level: job-record counts decoded through `compiled_circuit.qubit_map` (state index = little-endian over the listed qubits, Q8 / CCR-H2); (b) cohort-level: the manifest's TumorDraw files.
  - Per node: TVD, RMSPE of marginals (Borujeni's metric), χ² goodness-of-fit p; joint TVD; invalid-shot fraction (codes outside a node's state count). Each split by `sim_label`.
  → `H_analysis/src/drift.py`.
- [ ] **AC-10** (H.10) — *`certificate_stats` section.*
  - Certificates: n, pass rate, S mean/std/min/max, h_min_per_round, certified_bits, extractor output bits; per `sim_label` (taken from each certificate's job record).
  - Witness records: per witness_expression, value distribution vs threshold, pass rate, bases used; flags any witness read in < 2 bases (epic single-qubit lesson).
  - Memory-advantage records: C_μ, C_q, C_q_measured, passed.
  - Simulability reports: per circuit hash, BP fidelity_vs_sim, bond_dim; join to witness/memory records by circuit hash where possible; missing → `"bp_simulability": "not provided"`.
  - Receipts/ledger: `shared.validate` result per receipt and ledger chain (OK / errors), state counts.
  - Every number carries its `sim_label`; the section has the constant `"hardware": null` and `"certification_status": "certification-ready, not certified (simulated)"`.
  → `H_analysis/src/certstats.py`.
- [ ] **AC-11** (H.11) — *`baseline` section + honesty gates.*
  - For each quantum number in AC-10, its classical counterpart side by side: CHSH S vs classical bound 2 (and C's `--settings classical` runs if in the manifest); witness vs separable bound (= threshold); C_q vs C_μ; drift TVD vs a classical ancestral-sampling cohort of the same size (own sampler, `rng(seed, "H.ancestral")`); BP fidelity.
  - **Seed-source arm:** when the manifest tags hybrids with `seed_source: certified | prng`, realism + radiomics metrics are compared between arms (KS per metric); expected and reported: no difference — the quantum stage contributes provenance (L0) and evidence (L1/L1′), not realism.
  - `honesty` sub-object: claim levels present, every quantum number labelled, no hardware fields set; a phrase check over `notes` and the README for "more realistic because quantum", "quantum biology", "classically impossible" fails the run.
  → `H_analysis/src/baseline.py`.
- [ ] **AC-12** (H.12) — *Visual Turing test kit.*
  - `python -m H_analysis.src.turing_kit --manifest <cohort.json> --lidc-ref <run> [--n 40]` → `H_analysis/runs/<ts>-turing/kit.html`: one self-contained offline page (inline PNG data URIs, no CDN), in-context axial lung-window crop 96 × 96 mm through the lesion centroid (2-D export of the 3-D volumes), real/synthetic shuffled with `rng(seed,"H.turing")`, size/type-matched, per case "real / synthetic" + confidence 1–5, downloads `answers.json`; the answer key stays in `key.json` beside it.
  - `python -m H_analysis.src.turing_score <answers.json> <key.json>` → accuracy, Clopper–Pearson 95 % CI, binomial test vs 0.5, comparison with the 64–66 % benchmark, per-confidence breakdown.
  - Protocol (reader instructions, case count, blinding) written into dossier #20 "Adaptation" from F10.
  → `H_analysis/src/turing_kit.py`, `H_analysis/src/turing_score.py`.
- [ ] **AC-13** (H.13) — *Cohort manifest + ValidationReport CLI.*
  - `H_analysis/cohorts/stub.json` (committed) lists the `shared/stubs/` files per kind: `hybrids[]` (with optional `seed_source`), `draws[]`, `rulebook`, `compiled_circuit`, `job_records[]`, `certificates[]`, `witness[]`, `memory[]`, `simulability[]`, `trajectories[]`, `receipts[]`, `ledger`. Format documented in the README.
  - `python -m H_analysis.src.report --cohort H_analysis/cohorts/stub.json --lidc-ref <run|none> [--readers 30] [--sections all]`: validates every input with `shared.validate` (abort on errors), runs AC-6…AC-11, writes `H_analysis/runs/<ts>-report-<tag>/validation_report.json` (envelope via `shared.runrecord`, `hybrid_refs` = file_refs, `upstream` = every input) + `report_detail.json` (per-lesion/per-feature tables) and figures.
  - Sections that lack inputs or n are present with `{"status": "insufficient input", "n": …}` rather than omitted. On stubs every section runs and the report passes `python -m shared.validate`.
  → `H_analysis/src/report.py`, `H_analysis/src/manifest.py`, `H_analysis/cohorts/stub.json`.
- [ ] **AC-14** (H.14) — *Pilot cohort run (Q4).*
  - `python -m H_analysis.src.pilot plan --hosts 20 --per-host 3` writes `H_analysis/runs/<ts>-pilot/{commands.sh, cohort.json}`: per member an H-local input variant (copies of the stub TumorDraw / Certificate with new `shape_seed_hex` / `extracted_seed_hex` from `rng(seed,"H.pilot")`, types cycled, `stub: true`, `produced_by.letter: "H"`) and the F/C shell commands that render it on the LIDC host (F `host_masks`, `fingerprint`, `render --draw --certificate --masks --sites --fingerprint --out`), plus 10 C `certify` runs (5 ideal, 5 heron) and 2 `--settings classical`. The developer runs `bash commands.sh`; H never imports F or C.
  - Half the members `seed_source: certified` (C certificates), half `prng` (`os.urandom`-derived) — feeds AC-11.
  - Then `report --cohort <pilot>/cohort.json` → pilot `validation_report.json`; headline numbers copied into README "Reproduced result vs. paper" labelled **pilot, pre-INT**.
  → `H_analysis/src/pilot.py`.
- [ ] **AC-15** (H.15) — *Target #21 AI-Rad Companion: dissected, harness ready, nothing run.*
  - `dossiers/21-ai-rad-companion.md`, 8 sections from public documentation only (Siemens product pages/whitepapers, FDA 510(k) summaries — each source URL cited, numbers marked "(verify)" until read): what it measures (lung nodule detection/segmentation, diameters/volumes, lobe densities), documented input requirements, output objects (DICOM SR / secondary captures), stated performance. Licence note: no decompiling, no reverse engineering of binaries.
  - `python -m H_analysis.src.airad_check <dicom_dir>` checks a DICOM series (e.g. G's export) against the documented input requirements encoded in `H_analysis/src/airad_requirements.json` (modality, slice thickness, spacing, kernel class, coverage, patient position) and prints pass/fail per requirement.
  - Longitudinal protocol in the dossier: E baseline/follow-up snapshots → F hybrids → submit both → compare reported diameter/volume and growth vs ground-truth mask (volume error, VDT error); acceptance statistics defined; status "awaiting official access (Jan)".
  - `status.json` #21 → `dissected`, `reproduced: null`, note "no access; documented-interface only".
  → `H_analysis/dossiers/21-ai-rad-companion.md`, `H_analysis/src/airad_check.py`, `H_analysis/src/airad_requirements.json`.
- [ ] **AC-16** (H.16) — *Docs, status, isolation.*
  - README: Purpose, Targets, Inputs (+ manifest format), Outputs (ValidationReport section layout — the de-facto sub-schema for CCR-H1), How to run, Reproduced result vs. paper (R20a, R20b, pilot), Claim level and honesty notes, Contract change requests (CCR-H1…H3), References (H03, F08, F09, F10, H01, A01, Gallas 2006, PMC6324392).
  - `python -m shared.validate --status` passes; site previewed with `python -m shared.site.build`, then `git checkout -- index.html site/`.
  - `grep -rnE "QuantumPhantoms/code|from (A|B|C|D|E|F|G)_" H_analysis/` prints nothing; `git diff --stat main -- shared/` is empty.
  → `H_analysis/README.md`, `H_analysis/status.json`, `H_analysis/requirements.txt`.

---

## 3. Out of Scope (Postponed)

- **Full-scale validation on the integrated A→G output** (real B draws, D witness/simulability, G receipts per tumor, cohort at VICTRE power) → **INT**, using this feature's `report` CLI unchanged.
- **Reproducing VICTRE's DM-vs-DBT AUCs** (MC-GPU, breast phantoms, FEM compression, DBT reconstruction): dissected only; not this epic.
- **Running the visual Turing test with radiologists** → future work (needs readers; developer pilot only, Q7).
- **Running AI-Rad Companion** → future work, blocked on official access through Jan. No decompiling, ever.
- **Deep-learning train-synthetic/test-real** (nnU-Net / detector training as in H01/A01) → future work; no GPU. The CHO is the in-scope utility observer.
- **Building the BP simulator** (#9) → D. H only reports its numbers or "not provided".
- **Fixing sub-schemas for the six ValidationReport sections** in `shared/contracts/` → INT (CCR-H1).
- **Memorisation / privacy audits of learned refiners** (H07, H08) → not applicable; no learned generator in the main path.
- **QML benchmarking (H06, H09, H10)** → not a target of this epic.

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Model observer | **CHO, 5 Laguerre–Gauss channels**, LKE, as VICTRE; 2-D for repro, **3-D radially symmetric LG** for lung ROIs (Q5); covariance regularised `K + λ·tr(K)/n·I`, λ = 1e-6 |
| Reader variability | 30 readers by default, each = CHO trained on its own resampled training pairs; fully crossed test set |
| MRMC statistics | Own NumPy re-implementation of the U-statistic (Gallas 2006) variance used by iMRMC; no Java iMRMC |
| Radiomics | PyRadiomics 3.1.0 in env `qp-re-h` (Q1); fallback radiomics-lite (IBSI definitions), labelled |
| Two-sample tests | KS + Benjamini–Hochberg; SMD; classifier two-sample test (sklearn LogisticRegression, patient-grouped CV) with real-vs-real null |
| Real reference | LIDC via pylidc, own shim; 50 % consensus masks; texture → type mapping as published (≤2 GGO, <5 part-solid, 5 solid) |
| ROI geometry | 48³ mm at 1 mm isotropic, SimpleITK resampling in LPS (`shared.volumes`) |
| Edge metric | erf fit of radial profile, 10–90 % width = 2.563 σ |
| NPS | 3-D NPS in shell ROIs, radially averaged, same estimator for hybrid, host and LIDC |
| Rulebook marginals | Own NumPy enumeration of the BN (no pyAgrum, not installed) |
| Turing kit | Single offline HTML, inline data URIs, vanilla JS, answers downloaded as JSON |
| Seeds | Analysis seed = `hash_json(manifest)`; every random step `rng(seed, "H.<purpose>")` → replayable |
| Runs | `shared.runrecord.start_run("H_analysis", tag)`; outputs in gitignored `H_analysis/runs/` |

**Conventions & Notes:**
* Adopt epic §3 verbatim: 3-D only (2-D only in figures and the Turing kit), simulation labels, honesty gates, Markdown = source of truth, letter commits no `index.html`/`site/`.
* Upstream data enters only through `shared.validate`-checked contract files listed in a manifest; a file that fails validation aborts the report.
* Every ValidationReport section reports its `n` and either a result or `"insufficient input"`; nothing is silently skipped.
* Every statistic comes with its null or baseline (real-vs-real split, classical bound, ancestral cohort, PRNG seed arm). A bare number is not a result.
* Figures for the README/site go to `H_analysis/figures/` (committed) and contain no identifiable patient metadata; LIDC crops in figures are allowed (public CC BY 3.0 data) but kept small.
* Epic gap filled here: the content of the six ValidationReport sections (README "Outputs" + CCR-H1).

---

## 5. Data Model (Additions/Modifications)

No shared contract changes. Letter-local files only:

```text
[Consumed - shared contracts, unchanged]
HybridVolume, TumorDraw, Rulebook, CompiledCircuit, QuantumJobRecord, Certificate,
WitnessRecord, MemoryAdvantageRecord, SimulabilityReport, GrowthTrajectory, Receipt, LedgerEntry

[Produced - shared contract, unchanged]
ValidationReport (validation_report.json)
  hybrid_refs[]        file_ref
  realism              {per_type:{metric:{syn[], real_summary{p5,p50,p95,n}, ks_D, ks_p, pass}}, shell_noise_ratio, n}
  radiomics            {engine:"pyradiomics 3.1.0"|"radiomics-lite", n_features, frac_abs_smd_lt_0p5,
                        c2st{auc, ci95}, null{frac_abs_smd_lt_0p5, c2st_auc}, per_feature_ref}
  utility              {task:"LKE detection 3-D", observer:"CHO-LG3D", n_readers, n_train, n_test{pos,neg},
                        auc_train_syn, auc_train_real, delta_auc{value, se, ci95}, per_type{}, powered}
  drift                {by_sim_label:{<label>:{per_node:{tvd, rmspe_pct, chi2_p}, joint_tvd, invalid_shot_fraction, n}},
                        cohort:{per_node{}, n}}
  certificate_stats    {certificates{by_sim_label{}}, witnesses{}, memory{}, simulability{}, receipts{}, hardware:null,
                        certification_status}
  baseline             {pairs[]{quantity, quantum_value, classical_value, sim_label}, seed_source_arm{}, honesty{}}
  notes                str

[New - letter-local]
cohort.json (H_analysis/cohorts/*.json, runs/<ts>-pilot/cohort.json)
  seed_note, hybrids[]{path, seed_source?}, draws[], rulebook, compiled_circuit, job_records[], certificates[],
  witness[], memory[], simulability[], trajectories[], receipts[], ledger
lidc_ref.json + rois.npz          (runs/, gitignored) per-nodule scalars + ROI arrays
report_detail.json                (runs/) per-lesion and per-feature tables
turing kit: kit.html, key.json, answers.json (runs/)
airad_requirements.json           (src/, committed) documented input requirements, each with source URL
```

**Contract change requests (INT decides):**
- **CCR-H1** `validation_report`: replace the six open objects with the sub-schemas above (v1.1.0). *Why:* reports from different runs must be comparable. *Local workaround:* layout documented in README "Outputs", enforced by `report.py`.
- **CCR-H2** `compiled_circuit`: add `state_encoding` (bit order per node, valid state count). *Why:* decoding counts to node states currently assumes little-endian over `qubit_map` lists. *Workaround:* assumption stated in `drift.py` and the report notes; INT confirms with B.
- **CCR-H3** `hybrid_volume`: add optional `tumor_type`, `size_mm` (or make `draw_ref` a file_ref). *Why:* H joins type through `draw_id` across files. *Workaround:* manifest lookup; "unknown" type bucket if absent. (Related: E's CCR-1 `snapshots[].summary`.)

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/H_analysis/requirements.txt` | pyradiomics==3.1.0, SimpleITK, pydicom, pylidc, numpy, scipy, scikit-learn, scikit-image, matplotlib, jsonschema (env `qp-re-h`, Q1) |
| New | `RE/H_analysis/src/observer.py` | LG channels 2-D/3-D, CHO train/score, Mann–Whitney AUC (AC-2) |
| New | `RE/H_analysis/src/mrmc.py` | Gallas U-statistic MRMC variance, AUC and paired ΔAUC (AC-2) |
| New | `RE/H_analysis/src/roi.py` | 3-D ROI crop + 1 mm isotropic resample, shell masks, radial profiles (AC-5/6) |
| New | `RE/H_analysis/src/lidc_ref.py` | pylidc shim, nodule clustering, consensus masks, negatives, patient split (AC-5) |
| New | `RE/H_analysis/src/manifest.py` | load + `shared.validate` every cohort file, joins (draw_id → type), analysis seed (AC-13) |
| New | `RE/H_analysis/src/realism.py` | HU / edge / NPS metrics vs LIDC per type (AC-6) |
| New | `RE/H_analysis/src/radiomics_cmp.py` | PyRadiomics or radiomics-lite extraction, KS/SMD/C2ST + real-vs-real null (AC-7) |
| New | `RE/H_analysis/src/utility.py` | train-synthetic/test-real 3-D CHO, MRMC ΔAUC (AC-8) |
| New | `RE/H_analysis/src/drift.py` | BN enumeration, counts decoding, TVD/RMSPE/χ² (AC-9) |
| New | `RE/H_analysis/src/certstats.py` | certificate / witness / memory / simulability / receipt statistics (AC-10) |
| New | `RE/H_analysis/src/baseline.py` | classical pairs, ancestral cohort, seed-source arm, honesty checks (AC-11) |
| New | `RE/H_analysis/src/report.py` | CLI: manifest → `validation_report.json` + detail + figures (AC-13) |
| New | `RE/H_analysis/src/pilot.py` | pilot input variants + `commands.sh` + pilot manifest (AC-14) |
| New | `RE/H_analysis/src/turing_kit.py` | offline HTML reader kit + key (AC-12) |
| New | `RE/H_analysis/src/turing_score.py` | accuracy, Clopper–Pearson CI, binomial test (AC-12) |
| New | `RE/H_analysis/src/airad_check.py` | DICOM series vs documented requirements (AC-15) |
| New | `RE/H_analysis/src/airad_requirements.json` | requirement list with source URLs (AC-15) |
| New | `RE/H_analysis/repro/r20a_cho_ideal.py` | CHO vs analytic ideal observer (AC-3) |
| New | `RE/H_analysis/repro/r20b_victre_design.py` | VICTRE design SE(ΔAUC) reproduction, updates status #20 (AC-4) |
| New | `RE/H_analysis/cohorts/stub.json` | manifest over `shared/stubs/` (AC-13) |
| New | `RE/H_analysis/figures/r20a_cho_vs_ideal.png` | repro figure (AC-3) |
| New | `RE/H_analysis/figures/r20b_mrmc_se.png` | repro figure (AC-4) |
| New | `RE/H_analysis/figures/h_realism.png`, `h_radiomics.png`, `h_utility_roc.png`, `h_drift.png`, `h_certstats.png` | pilot report figures (AC-6…AC-10, AC-14) |
| Modify | `RE/H_analysis/dossiers/20-victre-pipeline.md` | all 8 sections (AC-1, AC-3, AC-4, AC-8, AC-12) |
| Modify | `RE/H_analysis/dossiers/21-ai-rad-companion.md` | all 8 sections, protocol (AC-15) |
| Modify | `RE/H_analysis/README.md` | fixed sections, manifest + report layout, CCR-H1..H3 (AC-16) |
| Modify | `RE/H_analysis/status.json` | #20 → reproduced → adapted; #21 → dissected (AC-1, AC-4, AC-8, AC-15) |
| Modify | `RE/feature-H-analysis.md` | ticks + §9 notes during implementation |

`RE/H_analysis/src/__init__.py` and `RE/H_analysis/repro/__init__.py` exist already (W).

---

## 7. Manual Verification (No Tests)

Environment: `conda activate qp-re-h` (or base with the radiomics-lite fallback), cwd = `RE/`.

- [ ] **Verify AC-1:** open `H_analysis/dossiers/20-victre-pipeline.md` → 8 sections filled, numbers match PMC6324392 (AUC 0.9005/0.9596, Δ 0.0587 (0.0062)), licence line present.
- [ ] **Verify AC-2/AC-3:** `python -m H_analysis.repro.r20a_cho_ideal` → prints `agreement=` with max |ΔAUC| < 0.01 over 5 amplitudes; figure written.
- [ ] **Verify AC-4:** `python -m H_analysis.repro.r20b_victre_design` → SE band per ρ printed, `paper=0.0073 ours=[lo, hi] agreement=yes|no`; `status.json` #20 `reproduced` filled; dense-group line printed vs 0.0148.
- [ ] **Verify AC-5:** `python -m H_analysis.src.lidc_ref --scans 47` → `lidc_ref.json` lists per-type counts; spot-check one ROI (`python -c` load `rois.npz`, centre voxel HU in nodule range); train/test patient sets disjoint (printed).
- [ ] **Verify AC-13 (stubs):** `python -m H_analysis.src.report --cohort H_analysis/cohorts/stub.json --lidc-ref none` → all six sections present (most `insufficient input`), `python -m shared.validate H_analysis/runs/<ts>-report-stub/validation_report.json` → OK.
- [ ] **Verify AC-6…AC-11 (pilot, AC-14):** `python -m H_analysis.src.pilot plan --hosts 20 --per-host 3`; `bash H_analysis/runs/<ts>-pilot/commands.sh`; `python -m H_analysis.src.report --cohort H_analysis/runs/<ts>-pilot/cohort.json --lidc-ref H_analysis/runs/<ts>-lidc-ref` →
  - realism: per-type percentiles, shell noise ratio within ±10 %;
  - radiomics: engine name, C2ST AUC with CI next to real-vs-real null;
  - utility: AUC_S, AUC_R, ΔAUC ± SE, `powered: false`;
  - drift: TVD/RMSPE per node by sim label (job-record counts);
  - certificate_stats: 10 certificates split ideal/heron, 2 classical-settings runs listed as `fail`; `hardware: null`;
  - baseline: seed-source arm shows no significant KS difference; honesty `ok`.
- [ ] **Verify AC-12:** `python -m H_analysis.src.turing_kit --manifest <pilot cohort.json> --lidc-ref <run> --n 20` → open `kit.html` offline (network off) → complete, download `answers.json`; `python -m H_analysis.src.turing_score answers.json key.json` → accuracy + CI + p printed.
- [ ] **Verify AC-15:** `python -m H_analysis.src.airad_check <a G DICOM export dir>` → one line per requirement, pass/fail; dossier #21 sections filled with source URLs; `status.json` #21 `dissected`.
- [ ] **Verify AC-16:** `python -m shared.validate --status` → OK; `python -m shared.site.build` → H page shows #20 adapted, #21 dissected; `git checkout -- index.html site/`; isolation grep prints nothing; `git diff --stat main -- shared/` empty.
- [ ] Edge: a manifest pointing at an invalid contract file (edit a copy, break `contract_version`) → report aborts with the `shared.validate` error, nothing written.
- [ ] Edge: insert the phrase "more realistic because quantum" into a copy of the notes → honesty check fails the run.
- [ ] Edge: rerun the same report command → byte-identical `validation_report.json` apart from `created_utc`/`run_id` (seeded).
- [ ] Privacy: `git status` shows no ROI arrays, kits or LIDC crops outside `runs/` except the small committed figures.

---

## 8. Open Questions

- [x] **Q1: PyRadiomics.** Not installed; base is Python 3.13 (wheel support unverified). *Resolved (accepted default):* new conda env `qp-re-h` (Python 3.12) from `H_analysis/requirements.txt` with `pyradiomics==3.1.0`; if it fails to install, use the radiomics-lite fallback and label it.
- [x] **Q2: What counts as "reproduced" for #20.** VICTRE's AUCs need the full MC-GPU breast chain. *Resolved (accepted default):* R20a (CHO = analytic ideal observer, method correctness) + R20b (VICTRE design → SE(ΔAUC) band contains the paper's 0.0073) = `reproduced`; the DM/DBT AUCs are reported, not reproduced, and said so in the dossier.
- [x] **Q3: Missing PDFs H03/H04/H05.** *Resolved (accepted default):* dossier cites the Europe PMC full text of PMC6324392 now; you drop the PDFs into `../papers/` when convenient (`H03_…`, `H04_…`, `H05_…`), no code depends on them.
- [x] **Q4: Pilot cohort.** H must not import F/C, and stubs give one lesion. *Resolved (accepted default):* AC-14 as written — H writes stub-flagged input variants + a `commands.sh` running F/C CLIs over 20 LIDC hosts × 3 = 60 hybrids, 10 C certificates (5 ideal, 5 heron) + 2 classical; labelled "pilot, pre-INT". Runtime of F per hybrid to be measured; cut to `--per-host 2` if > 6 h. Alternative: harness on stubs only, all numbers in INT.
- [x] **Q5: 3-D channels.** VICTRE used 2-D LG (stacked for DBT). *Resolved (accepted default):* 3-D radially symmetric LG for CT ROIs (lesion-scaled `a`), with a 2-D central-slice LG CHO also reported for comparability.
- [x] **Q6: LIDC split.** 47 scans on disk; F used 20 (`f_render_selection.json`) as hosts. *Resolved (accepted default):* those 20 = synthetic hosts + training negatives; the other 27 = real nodules (train-real arm on half the patients, test on the other half) — patient-disjoint everywhere.
- [x] **Q7: Turing test readers.** *Resolved (accepted default):* build kit + scorer; one developer self-read of 20 cases as a non-expert pilot, recorded as such; radiologist session future work.
- [x] **Q8: Counts → node states.** No encoding field in `compiled_circuit`. *Resolved (accepted default):* little-endian over each node's `qubit_map` list, out-of-range codes = invalid shots; raise CCR-H2 and confirm with B's code at INT.
- [x] **Q9: AI-Rad Companion sources.** *Resolved (accepted default):* dossier from Siemens public product/whitepaper pages and FDA 510(k) summaries, each cited and marked "(verify)"; ask Jan for official access and an interface spec — I will not contact anyone.
- [x] **Q10: Plan location + worktree.** The command template says `tasks/plans/`; this epic keeps plans in `RE/`. *Resolved (accepted default):* this file stays at `RE/feature-H-analysis.md`; commit it on main once approved, then `git worktree add ../qp-re-H -b re-H` and implement there.

---

## 9. Post-Implementation Notes

[Filled after implementation.]
