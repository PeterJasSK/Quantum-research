# Contracts (FROZEN v1.0.0, 2026-10-28)

Letters exchange data **only through these files**. Each JSON contract has a JSON Schema (draft 2020-12)
here; volumes and arrays follow [`VOLUMES.md`](VOLUMES.md). Validate any file with
`python -m shared.validate <file>` (cwd = `reverse-engineering/`). Changes happen only in INT, from the
letters' "Contract change requests".

## Common rules

- **Envelope** ([`_envelope.schema.json`](_envelope.schema.json) `#/$defs/envelope`): `contract`,
  `contract_version: "1.0.0"`, `produced_by {letter, tool, run_id, code_hash}`, `created_utc`, `stub`,
  `upstream[] {contract, path, sha256}`. Every contract except `target_status` and `ledger_entry` carries it.
- **File references** are `{path, sha256}`; `path` is relative to the file that contains it, `/` separators.
  The validator checks existence and hash.
- **Honesty gate** (`#/$defs/quantum`): quantum-bearing records require
  `sim_label` ∈ {`simulated: ideal`, `simulated: Heron-class noise (FakeMarrakesh)`} and `hardware: null`.
- **Strict**: unknown fields are rejected (`unevaluatedProperties: false`); extend only inside `extra{}`,
  `params{}`, or the open report objects, or via a change request.
- **Frozen vocabularies**: placement class `free | juxtavascular | juxtapleural`; tumor type
  `solid | part-solid | ground-glass`; margin `smooth | lobulated | spiculated`; lobes `LUL LLL RUL RML RLL`;
  cell states 0 host, 1 proliferating, 2 dormant, 3 necrotic (4–15 reserved); claim level `L0 | L1 | L1′`.

## Index

| Contract (epic §4) | Schema | Canonical file | Producer | Consumers | Format | Quantum | Stub |
|---|---|---|---|---|---|---|---|
| TargetStatus | [`target_status`](target_status.schema.json) | `<L>_<name>/status.json` | W, each letter | site build | JSON (no envelope) | – | the 8 letter `status.json` files |
| RunRecord | [`run_record`](run_record.schema.json) | `<L>/runs/<ts>-<tag>/run.json` | `shared.runrecord` | G, H | JSON + `counts_<job>.json` | – | [`run_record/run.json`](../stubs/run_record/run.json) |
| AnatomyMasks | [`anatomy_masks`](anatomy_masks.schema.json) | `anatomy_masks.json` | A | E, F | JSON manifest + host-grid NIfTI | – | [`anatomy_masks/`](../stubs/anatomy_masks/anatomy_masks.json) |
| SiteCandidate / ContextVector | [`site_candidates`](site_candidates.schema.json) | `sites.json` | A | B, E, F | JSON | – | [`site_candidates/sites.json`](../stubs/site_candidates/sites.json) |
| Rulebook | [`rulebook`](rulebook.schema.json) | `rulebook.json` | B | B, G, H | JSON | – | [`rulebook/rulebook.json`](../stubs/rulebook/rulebook.json) |
| CompiledCircuit | [`compiled_circuit`](compiled_circuit.schema.json) | `compiled_circuit.json` + `.qasm` | B | C, D, G | JSON + OpenQASM 3 | – | [`compiled_circuit/`](../stubs/compiled_circuit/compiled_circuit.json) |
| QuantumJobRecord | [`quantum_job_record`](quantum_job_record.schema.json) | `quantum_job_record.json` | B, C, D | C, D, G | JSON | yes | [`quantum_job_record/`](../stubs/quantum_job_record/quantum_job_record.json) |
| TumorDraw | [`tumor_draw`](tumor_draw.schema.json) | `tumor_draw.json` | B | D, E, H | JSON | – | [`tumor_draw/`](../stubs/tumor_draw/tumor_draw.json) |
| Certificate | [`certificate`](certificate.schema.json) | `certificate.json` | C | D, E, F, G, H | JSON | yes | [`certificate/`](../stubs/certificate/certificate.json) |
| WitnessRecord | [`witness_record`](witness_record.schema.json) | `witness_record.json` | D | G, H | JSON | yes | [`witness_record/`](../stubs/witness_record/witness_record.json) |
| MemoryAdvantageRecord | [`memory_advantage_record`](memory_advantage_record.schema.json) | `memory_advantage_record.json` | D | G, H | JSON | yes | [`memory_advantage_record/`](../stubs/memory_advantage_record/memory_advantage_record.json) |
| SimulabilityReport | [`simulability_report`](simulability_report.schema.json) | `simulability_report.json` | D | H | JSON | yes | [`simulability_report/`](../stubs/simulability_report/simulability_report.json) |
| QuantumLineage | [`quantum_lineage`](quantum_lineage.schema.json) | `quantum_lineage.json` | D | E | JSON | yes | [`quantum_lineage/`](../stubs/quantum_lineage/quantum_lineage.json) |
| SeedShape | [`seed_shape`](seed_shape.schema.json) | `seed_shape.json` + `.npz` | D | E | JSON + NPZ | yes | [`seed_shape/`](../stubs/seed_shape/seed_shape.json) |
| CellLattice / GrowthTrajectory | [`growth_trajectory`](growth_trajectory.schema.json) | `growth_trajectory.json` + `step_*.npz` | E | F, H | JSON + NPZ | – | [`growth_trajectory/`](../stubs/growth_trajectory/growth_trajectory.json) |
| LesionModelLibrary | [`lesion_model_library`](lesion_model_library.schema.json) | `lesion_model_library.json` | F | F, H | JSON (parameters only) | – | [`lesion_model_library/`](../stubs/lesion_model_library/lesion_model_library.json) |
| ScannerFingerprint | [`scanner_fingerprint`](scanner_fingerprint.schema.json) | `scanner_fingerprint.json` + `sigma_map.nii.gz` | F | F, H | JSON + NIfTI | – | [`scanner_fingerprint/`](../stubs/scanner_fingerprint/scanner_fingerprint.json) |
| HybridVolume | [`hybrid_volume`](hybrid_volume.schema.json) | `hybrid_volume.json` + 3 NIfTI | F | G, H | JSON + host-grid NIfTI | – | [`hybrid_volume/`](../stubs/hybrid_volume/hybrid_volume.json) |
| Receipt | [`receipt`](receipt.schema.json) | `receipt.json` | G | H | JSON, Ed25519 over `canonical_json({commit, fill})` | – | [`receipt/`](../stubs/receipt/receipt.json) |
| LedgerEntry | [`ledger_entry`](ledger_entry.schema.json) | `ledger.jsonl` (one entry per line) | G | H | JSONL, hash-chained | – | [`ledger_entry/ledger.jsonl`](../stubs/ledger_entry/ledger.jsonl) |
| ValidationReport | [`validation_report`](validation_report.schema.json) | `validation_report.json` | H | — | JSON | – | [`validation_report/`](../stubs/validation_report/validation_report.json) |

## Semantic checks beyond the schema (`shared/validate.py`)

- every `{path, sha256}` exists and matches; NIfTI obey VOLUMES (dtype per field name, LPS identity
  direction, spacing > 0, label values); all NIfTI referenced by one manifest share a grid;
- `anatomy_masks.grid` equals the NIfTI header; NPZ keys/dtypes for `seed_shape` and `growth_trajectory`;
- `rulebook`: every CPT row sums to 1; `rulebook_hash = hash_json(doc, exclude=[rulebook_hash, created_utc, produced_by])`;
- `quantum_job_record`: counts total = shots;
- `certificate`: `status: fail` ⇒ `extracted_seed_hex: null`; `pass` ⇒ seed present and S > 2;
- `receipt`: Ed25519 signature verifies;
- `ledger.jsonl`: index sequence, `prev_hash` chain (genesis = 64 × `0`), `entry_hash = sha256(canonical_json(entry − entry_hash))`.

Hashing conventions are in [`../seedhash.py`](../seedhash.py): `canonical_json` = sorted keys, `(",", ":")`
separators, UTF-8, `ensure_ascii=False`.
