# G — Sign / provenance: commit-before-draw receipt + tamper test

> Letter folder `G_provenance/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/G_provenance/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
Commit rulebook + code hash before the job; fill the receipt (job IDs, counts, S/H_min, witnesses, params, seed, code hash); sign with Ed25519; append to a hash-chained ledger (format modelled on C's beacon chain) and a DICOM tag. A CT-GAN-style injection/removal must fail verification. Pitched as traceability, not security.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #19 | [CT-GAN as a tamper test](dossiers/19-ct-gan-tamper-test.md) | ★★ | classical | listed |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `rulebook` — stub: [`shared/stubs/rulebook/rulebook.json`](../shared/stubs/rulebook/rulebook.json) · schema: [`rulebook.schema.json`](../shared/contracts/rulebook.schema.json)
- `compiled_circuit` — stub: [`shared/stubs/compiled_circuit/compiled_circuit.json`](../shared/stubs/compiled_circuit/compiled_circuit.json) · schema: [`compiled_circuit.schema.json`](../shared/contracts/compiled_circuit.schema.json)
- `quantum_job_record` — stub: [`shared/stubs/quantum_job_record/quantum_job_record.json`](../shared/stubs/quantum_job_record/quantum_job_record.json) · schema: [`quantum_job_record.schema.json`](../shared/contracts/quantum_job_record.schema.json)
- `certificate` — stub: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json) · schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json)
- `witness_record` — stub: [`shared/stubs/witness_record/witness_record.json`](../shared/stubs/witness_record/witness_record.json) · schema: [`witness_record.schema.json`](../shared/contracts/witness_record.schema.json)
- `memory_advantage_record` — stub: [`shared/stubs/memory_advantage_record/memory_advantage_record.json`](../shared/stubs/memory_advantage_record/memory_advantage_record.json) · schema: [`memory_advantage_record.schema.json`](../shared/contracts/memory_advantage_record.schema.json)
- `hybrid_volume` — stub: [`shared/stubs/hybrid_volume/hybrid_volume.json`](../shared/stubs/hybrid_volume/hybrid_volume.json) · schema: [`hybrid_volume.schema.json`](../shared/contracts/hybrid_volume.schema.json)
- `run_record` — stub: [`shared/stubs/run_record/run.json`](../shared/stubs/run_record/run.json) · schema: [`run_record.schema.json`](../shared/contracts/run_record.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `receipt` — schema: [`receipt.schema.json`](../shared/contracts/receipt.schema.json) · stub example: [`shared/stubs/receipt/receipt.json`](../shared/stubs/receipt/receipt.json)
- `ledger_entry` — schema: [`ledger_entry.schema.json`](../shared/contracts/ledger_entry.schema.json) · stub example: [`shared/stubs/ledger_entry/ledger.jsonl`](../shared/stubs/ledger_entry/ledger.jsonl)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to G_provenance/runs/ via shared.runrecord. -->
_Pending (feature G)._

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
_Pending (feature G)._ Planned: CT-GAN injection and removal both detected by signature/receipt verification.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
Provenance layer (n/a). Everything after the quantum job must be deterministic and replayable from the receipt.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[G01] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
