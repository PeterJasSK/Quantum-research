# H — Analysis / use: VICTRE-shaped validation + black-box target

> Letter folder `H_analysis/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/H_analysis/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
VICTRE-modelled study architecture over the hybrid volumes: physics realism (HU, edge, NPS vs LIDC), PyRadiomics distributions, in-context visual Turing test, train-synthetic/test-real detection, cohort drift vs rulebook, certificate and witness statistics, classical baseline. AI-Rad Companion only as a documented-interface black box (no decompiling).

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #20 | [FDA VICTRE pipeline](dossiers/20-victre-pipeline.md) | ★★ | classical | dissected |
| #21 | [Siemens AI-Rad Companion Chest CT (documented-interface black box)](dossiers/21-ai-rad-companion.md) | ★ | classical | dissected |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `hybrid_volume` — stub: [`shared/stubs/hybrid_volume/hybrid_volume.json`](../shared/stubs/hybrid_volume/hybrid_volume.json) · schema: [`hybrid_volume.schema.json`](../shared/contracts/hybrid_volume.schema.json)
- `growth_trajectory` — stub: [`shared/stubs/growth_trajectory/growth_trajectory.json`](../shared/stubs/growth_trajectory/growth_trajectory.json) · schema: [`growth_trajectory.schema.json`](../shared/contracts/growth_trajectory.schema.json)
- `lesion_model_library` — stub: [`shared/stubs/lesion_model_library/lesion_model_library.json`](../shared/stubs/lesion_model_library/lesion_model_library.json) · schema: [`lesion_model_library.schema.json`](../shared/contracts/lesion_model_library.schema.json)
- `scanner_fingerprint` — stub: [`shared/stubs/scanner_fingerprint/scanner_fingerprint.json`](../shared/stubs/scanner_fingerprint/scanner_fingerprint.json) · schema: [`scanner_fingerprint.schema.json`](../shared/contracts/scanner_fingerprint.schema.json)
- `certificate` — stub: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json) · schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json)
- `witness_record` — stub: [`shared/stubs/witness_record/witness_record.json`](../shared/stubs/witness_record/witness_record.json) · schema: [`witness_record.schema.json`](../shared/contracts/witness_record.schema.json)
- `memory_advantage_record` — stub: [`shared/stubs/memory_advantage_record/memory_advantage_record.json`](../shared/stubs/memory_advantage_record/memory_advantage_record.json) · schema: [`memory_advantage_record.schema.json`](../shared/contracts/memory_advantage_record.schema.json)
- `simulability_report` — stub: [`shared/stubs/simulability_report/simulability_report.json`](../shared/stubs/simulability_report/simulability_report.json) · schema: [`simulability_report.schema.json`](../shared/contracts/simulability_report.schema.json)
- `receipt` — stub: [`shared/stubs/receipt/receipt.json`](../shared/stubs/receipt/receipt.json) · schema: [`receipt.schema.json`](../shared/contracts/receipt.schema.json)
- `ledger_entry` — stub: [`shared/stubs/ledger_entry/ledger.jsonl`](../shared/stubs/ledger_entry/ledger.jsonl) · schema: [`ledger_entry.schema.json`](../shared/contracts/ledger_entry.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `validation_report` — schema: [`validation_report.schema.json`](../shared/contracts/validation_report.schema.json) · stub example: [`shared/stubs/validation_report/validation_report.json`](../shared/stubs/validation_report/validation_report.json)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to H_analysis/runs/ via shared.runrecord. -->
Working directory `reverse-engineering/`. Environment: base Python 3.13 works (radiomics-lite engine); `requirements.txt` documents the `qp-re-h` env for PyRadiomics.

```bash
python -m H_analysis.repro.r20a_cho_ideal                       # CHO vs analytic ideal observer (~3 min)
python -m H_analysis.repro.r20b_victre_design                   # VICTRE design -> SE(dAUC) (~25 min)
python -m H_analysis.src.lidc_ref --scans all                   # real-nodule reference (LIDC on disk, ~30 min)
python -m H_analysis.src.report --cohort H_analysis/cohorts/stub.json --lidc-ref none      # stub smoke test
python -m H_analysis.src.pilot plan --hosts 20 --per-host 3     # then: bash H_analysis/runs/<ts>-pilot/commands.sh
python -m H_analysis.src.report --cohort H_analysis/runs/<ts>-pilot/cohort.json --lidc-ref H_analysis/runs/<ts>-lidc-ref
python -m H_analysis.src.turing_kit --manifest <cohort.json> --lidc-ref <run> --n 40
python -m H_analysis.src.turing_score answers.json key.json
python -m H_analysis.src.airad_check <dicom_dir>
```

Every quantum number in a report keeps its label ("simulated: ideal" / "simulated: Heron-class noise (FakeMarrakesh)"); no hardware numbers exist.

### Cohort manifest format

`cohorts/*.json`, paths relative to the manifest, every file checked with `shared.validate` (a failure aborts the report, nothing is written):
`seed_note`, `hybrids[]{path, seed_source?: certified|prng}`, `draws[]`, `rulebook`, `compiled_circuit`, `job_records[]`, `certificates[]`, `witness[]`, `memory[]`, `simulability[]`, `trajectories[]`, `receipts[]`, `ledger`.
`seed_source` lives in the manifest because the contracts have no field for it.

## Outputs: ValidationReport section layout (de-facto sub-schema, CCR-H1)

```text
realism            {per_type:{type:{metric:{syn[], real_summary{p5,p50,p95,n}, syn_percentile[], ks_D, ks_p, pass}}}, shell_noise_ratio, n}
radiomics          {engine:"radiomics-lite", n_features, frac_abs_smd_lt_0p5, c2st{auc,ci95}, null{frac_abs_smd_lt_0p5,c2st_auc}, per_feature_ref}
utility            {task, observer:"CHO-LG3D", n_readers, n_train, n_test{pos,neg}, auc_train_syn, auc_train_real, delta_auc{value,se,ci95,df}, per_type, auc_2d_central_slice, powered}
drift              {by_sim_label:{label:{per_node:{tvd,rmspe_pct,chi2_p,n}, joint_tvd, invalid_shot_fraction, n}}, cohort, exact_marginals}
certificate_stats  {certificates{by_sim_label}, witnesses, memory, simulability, bp_simulability_join, receipts, hardware:null, certification_status}
baseline           {pairs[]{quantity, quantum_value, classical_value, note, sim_label}, seed_source_arm, honesty{ok,...}}
```
Sections without inputs read `{"status": "insufficient input", "n": ...}`. `report_detail.json` (per-lesion / per-feature tables) sits beside the report and is not part of the contract.

## Reproduced result vs. paper

| Target | Quantity | Paper | Ours | Agreement |
|---|---|---|---|---|
| #20 R20a | CHO AUC vs analytic ideal observer, 5 amplitudes (method check) | analytic | max abs diff 0.0054 | **yes** (criterion < 0.01; 1000 training pairs, 20,000 test pairs, see dossier) |
| #20 R20b | SE(ΔAUC), VICTRE heterogeneous design | 0.0073 | [0.0033, 0.0051] over ρ ∈ [0, 0.75] | **no** (surrogate too homogeneous; dense group [0.0068, 0.0105] vs 0.0148) |
| #20 pilot | validation report on the pilot cohort | n/a | _pending: pilot not yet run_ | pilot, pre-INT |

Figures: `figures/r20a_cho_vs_ideal.png`, `figures/r20b_mrmc_se.png`.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
Analysis stage (n/a). Forbidden claims (never made here): the phrases "more realistic because quantum", "quantum biology", "classically impossible". Reports every quantum number with its sim label, classical baseline and simulability number.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
Contract change requests (INT decides): **CCR-H1** replace the six open ValidationReport objects with the sub-schemas above (v1.1.0); **CCR-H2** `compiled_circuit.state_encoding` (bit order per node; H assumes little-endian over `qubit_map`); **CCR-H3** `hybrid_volume.tumor_type` / `size_mm` (H joins through `draw_id`).

## References (paper codes)

[H03] Badano et al. 2018 (VICTRE; Europe PMC PMC6324392; PDF to be added to `../../papers/`) · [F08], [F09], [F10] Chuquicusma-line visual Turing test papers · [H01], [A01] train-synthetic/test-real references · Gallas 2006, MRMC U-statistic variance (iMRMC). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
