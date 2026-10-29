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
| #19 | [CT-GAN as a tamper test](dossiers/19-ct-gan-tamper-test.md) | ★★ | classical | adapted |

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

Working directory `reverse-engineering/`. G runs no quantum job; every number it reports comes from files other letters made.
Runs go to `G_provenance/runs/` (gitignored: keys, the ledger, series that may hold LIDC voxels).

```bash
python -m G_provenance.src.keys init                       # once: demo Ed25519 key + trusted_keys.json
python -m G_provenance.src.receipt commit                  # BEFORE the job: prints "committed: ledger index i"
# ... run C (certify), E / F, as usual ...
python -m G_provenance.src.receipt fill --commit G_provenance/runs/<ts>-commit/receipt.json \
    [--certificate .../certificate.json --job .../quantum_job_record.json --hybrid .../hybrid_volume.json ...]
python -m G_provenance.src.dicom_export G_provenance/runs/<ts>-fill/receipt.json   # CT series with provenance tags
python -m G_provenance.src.verify G_provenance/runs/<ts>-dicom/series              # VERIFIED / TAMPER DETECTED: ...
python -m G_provenance.repro.r19_ctgan_tamper --n 20       # target #19: tamper test, table + figures
```

Inputs not given default to `shared/stubs/` (exempt from the order and code checks, recorded in `fill_report.json`).
A certificate with `status: "fail"` signs nothing ("certificate failed, nothing to sign", exit 0). Any failed check
(order, producer code hash, rulebook hash) writes `fill_report.json`, signs nothing and exits 1.

## Reproduced result vs. paper

Target #19 (G01 §7.2: sign each scan to detect CT-GAN tampering). The GAN is replaced by a classical in-painter;
everything else in the pre/post-processing follows the paper (see the [dossier](dossiers/19-ct-gan-tamper-test.md)).

| | paper | ours (stub phantom, n = 20 per kind) |
|---|---|---|
| injection / removal detected by the signature | qualitative claim | 20 / 20 and 20 / 20, failing check `voxels`, slice Jaccard 1.00 |
| forgeries: seed edit / re-sign / ledger rewrite / commit deletion | — | caught by `signature` / `trusted_key` / `trusted_key` only / `commit_first` |
| controls (untampered, unbound tag re-saved) | — | 0 false positives |
| readers misdiagnose 99 % (injected) and 94 % (removed); AI 100 % | measured | not reproduced (needs radiologists and the trained GAN; H's territory) |

Figures: [`figures/r19-ctgan-tamper.png`](figures/r19-ctgan-tamper.png), [`figures/r19-detection-table.png`](figures/r19-detection-table.png).

## Claim level and honesty notes

Provenance layer (claim level n/a, no quantum claim). Everything after the quantum job must be deterministic and replayable from the receipt.

- **Traceability, not security.** The tamper test checks that data still matches what was committed and signed.
- **Demo key, not a PKI.** One random Ed25519 key per machine, pinned in `trusted_keys.json`. The stub key is never trusted.
- **Limit (attack c).** A forger who holds the trusted key and rewrites the ledger end to end cannot be detected from the files alone; only the pinned key stops it. Future fix: anchor the ledger head in a public beacon pulse (C dossier #5).
- **Order is proved by ledger index + `created_utc`**, with one-second resolution; stub inputs are exempt and flagged.
- Simulated upstream numbers keep their `sim_label` inside the files the receipt references; G does not restate them as hardware results.
- No GAN was trained or run; the in-painter is classical, so stealth against human readers is not claimed.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[G01] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

`shared/` is frozen; G works around each of these locally. INT decides.

| ID | Contract | Change | Local workaround |
|---|---|---|---|
| CCR-G1 | `ledger_entry` | `kind` gains `"commit"` | `kind "receipt"`, told apart by the receipt's `state: "committed"` |
| CCR-G2 | `receipt.commit` | gains `code_hashes{letter: hex64}` | `commit_manifest.json` + `code_hash = hash_json(code_hashes)` |
| CCR-G3 | `receipt.fill` | gains `voxel_sha256` (+ optional `slice_sha256s`) | bound via `params_sha256` → `bound_params.json` |
| CCR-G4 | `shared.validate` | receipt check takes an optional trusted-key list | `G_provenance.src.verify` pins keys |
