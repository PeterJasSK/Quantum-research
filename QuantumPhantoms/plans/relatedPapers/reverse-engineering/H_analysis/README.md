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
| #20 | [FDA VICTRE pipeline](dossiers/20-victre-pipeline.md) | ★★ | classical | listed |
| #21 | [Siemens AI-Rad Companion Chest CT (documented-interface black box)](dossiers/21-ai-rad-companion.md) | ★ | classical | listed |

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
_Pending (feature H)._

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
_Pending (feature H)._ Planned: VICTRE study architecture / model-observer analysis on our cohort shape.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
Analysis stage (n/a). Reports every quantum number with its sim label, classical baseline and simulability number.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[H03] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
