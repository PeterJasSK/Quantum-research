# Feature W — Foundation: frozen contracts, stubs, shared helpers, site skeleton

**Epic:** [`epic-reverse-engineering.md`](./epic-reverse-engineering.md) (Approved, 2026-10-28). W is the strictly-first foundation step (Wave 0).
**Feature ID:** W
**Author:** Claude (Opus)
**Date:** 2026-10-28
**Status:** Complete (implemented 2026-10-28; approved by developer with all Q1–Q9 defaults accepted)

> **Technical constraints / core directive.** Python 3.13 (conda base, `/home/peter/anaconda3/bin/python3`) with the libraries already installed: qiskit 2.3.1, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.47.0, numpy, scipy, SimpleITK 2.5.6, jsonschema 4.23, markdown-it-py 2.2, jinja2 3.1, cryptography 44. **No new installs.** Simulation only (`AerSimulator`, ideal and `FakeMarrakesh` noise); no IBM jobs. Nothing imported from `QuantumPhantoms/code/` (MVP). All files live under `QuantumPhantoms/plans/relatedPapers/reverse-engineering/` (written `RE/` below). Every command runs with `RE/` as the working directory (`python -m shared.…`). Generated HTML is static and offline, with no CDN. **No automated tests; verification is manual only.**

---

## 1. Why (Step Goal)

**Before.** `RE/` contains only the epic and the targets list. There are no file contracts, no stub inputs, no shared helpers and no letter folders. Starting the A–H sessions now would leave eight parallel Claude sessions to invent incompatible formats for the same hand-offs: sites, draws, seeds, volumes and receipts. INT would then have to reconcile all of them.

**After.** One small, sequential session freezes the common ground that every parallel letter builds on:
- **Frozen file contracts** in `shared/contracts/`:
  - one JSON Schema per §4 hand-off entity;
  - a common envelope (provenance, upstream hashes, honesty labels);
  - one volume-conventions document (NIfTI, spacing, orientation, HU, NPZ).
- **Stub fixtures** in `shared/stubs/`. They form one consistent synthetic "tumor story" (no patient data), and each validates against its contract. Every letter can therefore run before its upstream exists.
- **Shared helpers**, and only these:
  - seed and hash utilities;
  - a run-record writer;
  - the `FakeMarrakesh` simulator factory;
  - a contract validator;
  - NIfTI volume I/O;
  - the site build.
- **Eight letter skeletons** `A_placement` … `H_analysis`. Each has a pre-filled README, its own `status.json` (its targets pre-filled), and a dossier file per target created from the template.
- **Documentation surface:**
  - `about.html`, the internal explainer;
  - root `README.md`, the AI entry point;
  - the site build that aggregates the per-letter status and Markdown into `index.html` + `site/`, rendering all 21 targets.

After W is committed to `main`, the wave-1 worktrees (A, C, E, F) can start (epic §7).

---

## 2. Acceptance Criteria

- [x] **AC-1** (W.1): The `RE/` skeleton exists exactly as in epic §3 "Folder layout".
  → `README.md`, `about.html`, `index.html`, `site/`, `shared/`, `runs/` (local only; gitignored) and eight letter folders: `A_placement`, `B_mapping`, `C_certificate`, `D_quantum_growth`, `E_classical_growth`, `F_render`, `G_provenance`, `H_analysis`. Each letter folder holds:
  - `README.md` and `status.json`;
  - `dossiers/`;
  - `src/__init__.py` and `repro/__init__.py`;
  - `figures/.gitkeep`;
  - an `__init__.py` at the letter root.
- [x] **AC-2** (W.2): Every §4 hand-off entity has a frozen JSON Schema in `shared/contracts/`.
  → Draft 2020-12 schemas, one file per contract (list in §5). Each shares the envelope in `_envelope.schema.json`:
  - `contract`, `contract_version: "1.0.0"`;
  - `produced_by`;
  - `created_utc`;
  - `stub`;
  - `upstream[]` (path + sha256).

  `shared/contracts/README.md` indexes every contract with: canonical filename, producer letter, consumer letters, on-disk format, stub path.
- [x] **AC-3** (W.2): Volume conventions are frozen in `shared/contracts/VOLUMES.md` and enforced by code.
  → The rules are listed in §4 "Volume conventions" (NIfTI `.nii.gz`, LPS, spacing from the host DICOM, HU `int16`, masks `uint8`, shared host grid, NPZ for off-grid arrays).

  `shared/volumes.py` provides `read_volume` / `write_volume` / `check_same_grid`. These are the only sanctioned NIfTI I/O path.
- [x] **AC-4** (W.2): The honesty gates are expressed in the schemas, not only in prose.
  → Every quantum-bearing contract (quantum job record, certificate, witness, memory advantage, simulability, quantum lineage, seed shape):
  - requires `sim_label` ∈ {`"simulated: ideal"`, `"simulated: Heron-class noise (FakeMarrakesh)"`};
  - requires `hardware: null`.

  In addition:
  - `certificate` requires `certification_status: "certification-ready, not certified (simulated)"`, and `status` ∈ {`pass`, `fail`};
  - a `fail` certificate must have `extracted_seed_hex: null` (`if/then`; epic decision 6);
  - quantum deliverables carry `claim_level` ∈ {`L0`, `L1`, `L1′`}.
- [x] **AC-5** (W.3): There is one stub fixture per contract in `shared/stubs/<contract>/`, generated deterministically and committed.
  → `python -m shared.stubs.make_stubs` regenerates them byte-identically from a fixed seed. The stubs form one consistent story:
  - a synthetic 3-D chest phantom (no patient voxels): body, two lungs with five lobes, vessel tubes, airway;
  - `sites.json` with three sites, one per placement class;
  - a 2-node rulebook;
  - a compiled stub circuit;
  - a quantum job record from a real ideal-Aer run of a CHSH stub circuit;
  - a draw that references site `S001`;
  - a `pass` certificate;
  - a seed shape;
  - a baseline/follow-up growth trajectory;
  - a fingerprint;
  - a hybrid volume with an inserted sphere at `S001`;
  - an Ed25519-signed receipt (stub key from a fixed seed);
  - a 2-entry chained ledger;
  - a validation report.

  Each stub is marked `"stub": true`, with `produced_by.letter: "stub"`.
- [x] **AC-6** (W.3): The contract validator passes on all stubs.
  → `python -m shared.validate --stubs` exits `0` and prints one `OK <path> (<contract>)` line per stub. It does three things:
  - picks the schema from the file's `contract` field;
  - validates `ledger.jsonl` line by line and checks the hash chain;
  - for manifests, checks that every referenced file exists, that its `sha256` matches, and that NIfTI/NPZ files obey the VOLUMES rules (dtype, LPS direction, positive spacing, same grid across one manifest).

  `python -m shared.validate <file…>` validates arbitrary letter outputs. Any violation gives a non-zero exit and a readable error naming the JSON pointer.
- [x] **AC-7** (W.3): Seed and hash helpers exist in `shared/seedhash.py` (no qiskit import, so E/F/G/H stay qiskit-free). It provides:
  - `sha256_bytes`, `sha256_file`;
  - `canonical_json` (sorted keys, compact separators, UTF-8);
  - `hash_json(obj, exclude=())`;
  - `code_hash(paths)` (tree hash over sorted relative path + content of `.py` files);
  - `git_state()` → `{commit, dirty}` or `null`;
  - `derive_seed(seed_hex, label) -> int` (uint64 from `sha256(bytes.fromhex(seed_hex) + label.encode())`);
  - `rng(seed_hex, label) -> numpy.random.Generator` (PCG64).

  This is the single sanctioned way every E/F PRNG is seeded from C's extracted seed.
- [x] **AC-8** (W.3): The run-record writer exists in `shared/runrecord.py`.
  → `start_run(letter_dir, tag, *, seed_hex=None, sim_mode=None) -> Run` creates `<letter_dir>/runs/<YYYYmmdd-HHMMSS>-<tag>/`. Its methods are:
  - `Run.add_job(job_id, transpiled_hash, shots, counts)`, which writes `counts_<job_id>.json`;
  - `Run.add_input(path, contract)` / `Run.add_output(path, contract)`, which record sha256;
  - `Run.finish(notes="")`, which validates against `run_record.schema.json` and writes `run.json`.

  `run.json` holds:
  - backend / sim mode / fake backend name;
  - calibration snapshot;
  - job IDs;
  - transpiled-circuit hashes;
  - counts files;
  - code hash + git state;
  - seed.

  These are the epic §3 "Logging" fields.
- [x] **AC-9** (W.3): The simulator factory exists in `shared/simbackend.py`.
  → `REFERENCE_FAKE = "FakeMarrakesh"`, with:
  - `fake_backend()`;
  - `transpile_heron(circ, *, seed, optimization_level=1)` (always against the `FakeMarrakesh` target: heavy-hex, CZ basis);
  - `make_simulator(mode: "ideal" | "heron", *, seed)`: `ideal` is a noiseless `AerSimulator`, `heron` is `AerSimulator.from_backend(FakeMarrakesh())`;
  - `run_counts(circ, mode, shots, seed) -> (counts, transpiled_hash, job_id)`;
  - `sim_label(mode)`, which returns the exact contract strings;
  - `calibration_snapshot()` → `{fake_backend, qiskit_ibm_runtime_version, props_sha256, last_update_date}`;
  - `circuit_hash(circ)` (sha256 of the `qiskit.qasm3.dumps` text).
- [x] **AC-10** (W.4): Each letter has its own `status.json`, pre-filled.
  → It conforms to `target_status.schema.json`. The 21 targets are distributed by the epic's §1 table (A: #18; B: #1–3; C: #4–5; D: #6–10; E: #11–12; F: #13–17; G: #19; H: #20–21), each with:
  - number, slug, name;
  - priority (1–3 stars);
  - kind (`quantum`/`classical`);
  - paper codes;
  - `state: "listed"`;
  - dossier link.

  The handling of #10 depends on **Q1**.
- [x] **AC-11** (W.4): The templates exist and are already applied.
  → `shared/templates/LETTER_README.template.md` has the epic §3 fixed sections, plus "Contract change requests". `shared/templates/DOSSIER.template.md` has the 8 fixed sections.

  Each letter README is instantiated with:
  - Purpose (from the epic §2 row);
  - Targets;
  - Inputs/Outputs (contract names + stub paths from §4);
  - Claim level (from the epic);
  - References (paper codes).

  "How to run" and "Reproduced result" are marked `_Pending (feature <L>)._`. Each target gets `dossiers/<NN>-<slug>.md` from the template, with sections marked `_Not yet dissected._`.
- [x] **AC-12** (W.5): The site build renders everything offline.
  → `python -m shared.site.build` performs these steps:
  1. validates every `<L>_*/status.json` (aborting on error);
  2. checks that the 21 target numbers are unique and complete, and that every dossier link resolves;
  3. renders Markdown with markdown-it-py (CommonMark + tables) through jinja2 templates;
  4. rewrites `.md` links to `.html`;
  5. copies `figures/`;
  6. writes `index.html` and `site/<L>_<name>/index.html` + `site/<L>_<name>/<NN>-<slug>.html` + `site/style.css`.

  `index.html` shows:
  - per-letter cards with state counts;
  - a 21-row target table (#, letter, name, priority, state badge, claim level, sim mode, reproduced number, links);
  - a link to `about.html`.

  No external URLs appear in any `<script>`/`<link>`/`<img>`. Each page carries a "GENERATED — do not edit" comment. `--update-readme` also rewrites the status table between `<!-- STATUS:BEGIN -->` / `<!-- STATUS:END -->` in the root `README.md` (W and INT only).
- [x] **AC-13** (W.5): `about.html` exists as a hand-written, self-contained internal explainer.
  → Inline CSS, light/dark through `prefers-color-scheme`, no scripts or CDN. It contains:
  - an inline-SVG A→H pipeline diagram labelled with the contract hand-offs;
  - why reverse-engineer (dissect → reproduce → adapt → integrate | reject);
  - the claim ladder L0 / L1 / L1′ / L2 (blocked: heavy-hex shallow = BP-simulable) / L3 (FT only);
  - "simulation only" and "simulated CHSH certifies nothing";
  - privacy-by-construction (parameters only, no patient voxels);
  - the parallel-worktree workflow;
  - links to `index.html` and `README.md`.
- [x] **AC-14** (W.5): The root `README.md` serves as the AI entry point. It contains:
  - purpose;
  - folder map;
  - run conventions (cwd = `RE/`, `python -m`, Python path);
  - contract list (links to `shared/contracts/README.md`);
  - helper API summary;
  - lifecycle states;
  - honesty gates;
  - the ownership rules for parallel sessions (copied from epic §3 "Parallel execution": write only in your letter folder and feature plan; record contract changes as requests; never commit `index.html`/`site/`);
  - the per-session workflow;
  - the generated status table.
- [x] **AC-15** (W.1): `shared/` is declared frozen.
  → `shared/README.md` opens with a FROZEN notice (contract version 1.0.0, frozen 2026-10-28, changed only in INT via the letters' "Contract change requests"). It then documents each helper module. The existing `.gitignore` rules (`relatedPapers/papers/`, `reverse-engineering/**/runs/`) are confirmed in place and left unchanged.

---

## 3. Out of Scope (Postponed)

- Any target work: dissection, reproduction, adaptation or integration of #1–#21. Owned by features **A–H**.
- Real upstream data: LIDC/Mayo downloads, lungmask/TotalSegmentator runs, `pydicom` (not installed; first needed by **A**/**F**).
- Real Ed25519 key management, ledger policy, DICOM tag writing → **G**. (W's stub signature only proves the schema shape.)
- CHSH min-entropy maths, the Toeplitz extractor and CURBy → **C**. (The stub certificate values are placeholders.)
- Checking that Aer supports noisy dynamic-circuit feed-forward → **D** (epic §6).
- Belief-propagation adversary tooling → **D** (#9).
- Contract amendments after the freeze, swapping stubs for real files, and every site rebuild after W → **INT**.
- Hardware runs (future work everywhere). A Siemens or non-specialist explainer is not needed (epic decision 9).
- MathJax / KaTeX equation rendering (it needs a CDN). Equations stay as Unicode or fenced blocks (see Q7).

---

## 4. Technical Decisions

Epic §3 is adopted as-is: stack, sim-only, 3-D only, MVP isolation, folder layout, file-only contracts, parallel ownership rules, honesty gates, seed chain, logging, no tests.

| Component | Choice / Implementation |
|---|---|
| Interpreter | conda base Python 3.13.5; run from `RE/` as `python -m <module>` |
| Contracts | **JSON Schema draft 2020-12**, validated with `jsonschema` 4.23 (`Draft202012Validator`, with `format_checker`) |
| Contract versioning | `contract_version` const `"1.0.0"` in every schema; bumped only in INT |
| Volume I/O | **SimpleITK** (installed; nibabel is not) through `shared/volumes.py`; `sitk.DICOMOrient(img, "LPS")` on read and write |
| Off-grid arrays | `.npz` (`numpy.savez_compressed`) with `spacing_mm`, `origin_mm` arrays + documented keys |
| Hashing | SHA-256 everywhere; canonical JSON = `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")` |
| Seed derivation | `derive_seed(seed_hex, label)` = first 8 bytes (big-endian) of `sha256(seed || label)`; `rng()` → `np.random.Generator(np.random.PCG64(...))` |
| Simulator | `AerSimulator()` (ideal) / `AerSimulator.from_backend(FakeMarrakesh())` (heron); both modes run circuits transpiled to the `FakeMarrakesh` target (Q6) |
| Circuit hash | sha256 of `qiskit.qasm3.dumps(transpiled)` (QPY bytes embed version metadata, so they are not stable) |
| Stub signature | `cryptography` Ed25519; private key = `sha256(b"qp-re-stub-key")`; public key stored in the stub receipt |
| Markdown → HTML | **markdown-it-py** `MarkdownIt("commonmark").enable("table")` |
| HTML templating | **jinja2** templates in `shared/site/templates/` |
| Site assets | one local `site/style.css`; `about.html` fully inline; no JS needed |

**Volume conventions (frozen in `VOLUMES.md`):**
- **Files:** every volume on the host grid is NIfTI-1 `.nii.gz`. Arrays are read with `sitk.GetArrayFromImage`, giving numpy index order **(z, y, x)**. Spacing, origin and direction are always taken from the image and never assumed.
- **Physical frame:** **DICOM/ITK LPS**. The direction matrix is the identity after `DICOMOrient("LPS")`, and the validator rejects anything else.
- **Spacing:** in mm, inherited from the host DICOM. There is no implicit isotropic resampling in any contract. A letter that resamples records the target spacing in its manifest.
- **CT:** `int16` HU, clipped to [−1024, 3071]. There is no rescale slope/intercept (HU stored directly). Air is −1000.
- **Masks:**
  - stored as `uint8`;
  - binary masks use {0, 1};
  - label maps declare their label table in the manifest (lungs: 1 right, 2 left; lobes: 1 LUL, 2 LLL, 3 RUL, 4 RML, 5 RLL, following lungmask).
- **Grid:** every NIfTI referenced by one manifest shares the host grid (size, spacing, origin, direction) unless a field says otherwise. `check_same_grid` enforces this.
- **Cell states** (NPZ key `state`, `uint8`, 3-D):
  - 0 = host/empty;
  - 1 = proliferating;
  - 2 = dormant (non-proliferating);
  - 3 = necrotic.

  Codes 4–15 are reserved for letter-specific states declared in the manifest's `state_labels`. A lattice maps to the host through `origin_mm` (LPS) + `spacing_mm`.
- **2-D slices:** PNG under a letter's `figures/` only. They are never a contract input.

**Conventions & Notes:**
- `shared/` imports nothing from the MVP or from any letter. Letters import only `shared`, never each other (hand-offs are files).
- Only `shared/simbackend.py` imports qiskit. `seedhash`, `runrecord`, `volumes` and `validate` stay qiskit-free.
- Paths inside manifests and `upstream[]` are **relative to the file that contains them**, with `/` separators. Each carries a `sha256`.
- `produced_by.letter` ∈ {`A`…`H`, `INT`, `stub`}.
- Quantum-bearing records carry `sim_label` + `hardware: null` (reserved for future hardware fields).
- Generated HTML starts with a GENERATED comment. Stubs carry no extra marker key; they are plain contract instances with `stub: true`. Schemas stay strict (`additionalProperties: false`), except inside `extra{}` / `params{}` objects.
- **Repo analogues to mirror (pattern only, no import):**
  - `artificial-life/code/backlog/stage3_teleport.py:497` `_get_noisy_backend` (from_backend factory + cache);
  - `THESIS/CriticalQuantumLife/code/closed_loop.py:410` `write_run` (run JSON layout);
  - `QuantumPhantoms/code/f3_web/build_web.py` (offline self-contained HTML build).
- **Plan location:** this plan sits in `RE/` (epic §3 layout), not in `tasks/plans/`.
- **Note for the epic (§4):** W adds a `RunRecord` contract (`run.json`) and a `LedgerEntry` line format (`ledger.jsonl`). The epic implies both through §3 "Logging" and the `Receipt` / `LedgerEntry` row, but does not list them as separate files.

---

## 5. Data Model (Additions/Modifications)

All files are new. Nothing is modified (the MVP datamodel is untouched). There is no database; the "schema" is the set of JSON Schemas below. Fields marked `?` are nullable/optional. Every contract below also carries the envelope.

```text
[New — shared envelope]  _envelope.schema.json  ($defs, referenced by every contract)
  contract          str const   e.g. "site_candidates"
  contract_version  str const   "1.0.0"
  produced_by       {letter: A..H|INT|stub, tool: str, run_id?: str, code_hash: hex64}
  created_utc       str date-time
  stub              bool
  upstream[]        {contract: str, path: str (relative), sha256: hex64}
  quantum-bearing only:  sim_label enum["simulated: ideal","simulated: Heron-class noise (FakeMarrakesh)"],
                         hardware: null

[New] TargetStatus            <L>_<name>/status.json            (W; own letter; site build)
  letter A..H, letter_name str
  targets[] {number 1..21, slug kebab, name, priority 1..3, kind quantum|classical,
             papers[] str (e.g. "B01"), state listed|dissected|reproduced|adapted|integrated|rejected,
             rejection_reason? str (required iff rejected),
             reproduced? {quantity, paper_value, our_value, unit, agreement, sim_mode?, figure?},
             claim_level? L0|L1|L1′|n/a, sim_mode? ideal|heron|both|n/a,
             dossier str (relative), figures[] str, updated date}

[New] RunRecord               <L>/runs/<ts>-<tag>/run.json      (shared helper; G, H)
  run_id, letter, tag, created_utc, code_hash, git? {commit, dirty}, seed_hex?,
  sim? {mode ideal|heron, sim_label, fake_backend, calibration_snapshot{fake_backend,
        qiskit_ibm_runtime_version, props_sha256, last_update_date}},
  jobs[] {job_id, transpiled_hash, shots, counts_file},
  inputs[]/outputs[] {contract, path, sha256}, notes

[New] AnatomyMasks            anatomy_masks.json + *.nii.gz      (A → E, F)
  host_scan_id, grid {size[3], spacing_mm[3], origin_mm[3]},
  files {host_ct, lungs, lobes, vessels, airway, body?} each {path, sha256},
  label_tables {lungs:{1:right,2:left}, lobes:{1:LUL,2:LLL,3:RUL,4:RML,5:RLL}}

[New] SiteCandidates          sites.json                         (A → B, E, F)
  host_scan_id, anatomy_masks_ref {path, sha256},
  sites[] {site_id "S\d{3}", center_vox_zyx[3] int, center_mm_lps[3],
           context {placement_class free|juxtavascular|juxtapleural, lung right|left,
                    lobe LUL|LLL|RUL|RML|RLL, dist_pleura_mm, dist_vessel_mm, dist_airway_mm,
                    local_hu_mean, local_hu_std, extra? {str: number}}}

[New] Rulebook                rulebook.json                      (B → B, G, H)
  rulebook_id, nodes[] {name, states[], parents[], cpt (nested array, rows sum to 1),
                        context_keys[] (context fields that select the CPT), sources[] (citation, required)},
  rulebook_hash hex64 (= hash_json(self, exclude=["rulebook_hash","created_utc"]))

[New] CompiledCircuit         compiled_circuit.json + .qasm      (B → C, D, G)
  rulebook_hash, qasm3_path+sha256, transpiled_for "FakeMarrakesh", qubit_map {node: [int]},
  gate_counts {str:int}, depth, two_qubit_count, circuit_hash

[New] QuantumJobRecord        quantum_job_record.json            (B/C/D → C, D, G)   quantum-bearing
  job_id (local uuid4), sim_mode ideal|heron, fake_backend, sim_seed, shots,
  transpiled_hash, counts {bitstring: int} | counts_file, test_round_mask? [bool] | file,
  calibration_snapshot

[New] TumorDraw               tumor_draw.json                    (B → D, E, H)
  draw_id, site_id, size_mm, type solid|part-solid|ground-glass,
  margin smooth|lobulated|spiculated, shape_seed_hex, rulebook_hash, job_record_ref

[New] Certificate             certificate.json                   (C → D, E, F, G, H)  quantum-bearing
  chsh_S, n_rounds, n_test_rounds, h_min_per_round, certified_bits,
  extractor {kind "toeplitz", input_bits, output_bits}, curby_pulse_id?,
  status pass|fail, extracted_seed_hex? (null iff fail),
  certification_status const "certification-ready, not certified (simulated)", claim_level const L0

[New] WitnessRecord           witness_record.json                (D → G, H)           quantum-bearing
  claim_level L1, observables {name: {value, stderr}} (e.g. XX, ZZ, sum), threshold, passed,
  bases[] (≥ 2 required), mi_network? {nodes, edges[{i,j,mi}]}

[New] MemoryAdvantageRecord   memory_advantage_record.json       (D → G, H)           quantum-bearing
  claim_level L1′, process_description, C_mu_bits, C_q_bits, C_q_measured?, n_qubits, passed

[New] SimulabilityReport      simulability_report.json           (D → H)              quantum-bearing
  circuits[] {circuit_hash, method "belief-propagation", bond_dim?, fidelity_vs_sim, runtime_s}

[New] QuantumLineage          quantum_lineage.json               (D → E)              quantum-bearing
  job_record_ref, generations[] {g, measured_bits, fate[], chsh_round bool}, claim_level

[New] SeedShape               seed_shape.json + seed_shape.npz   (D → E)              quantum-bearing
  npz keys: occupancy uint8 (z,y,x), spacing_mm[3]; json: lineage_ref, n_cells, claim_level

[New] GrowthTrajectory        growth_trajectory.json + step_*.npz (E → F, H)
  site_id, seed_hex (from certificate), seed_shape_ref?, origin_mm_lps[3], spacing_mm[3],
  state_labels {0..15: name} (0–3 fixed), snapshots[] {step, day, role baseline|follow-up|other, path, sha256}

[New] LesionModelLibrary      lesion_model_library.json          (F → F, H)
  source "LIDC fitted parameters (no voxels)", types {solid|part-solid|ground-glass:
  {shape_params{}, edge_profile{model, params}, hu{mean, std}, n_fitted}}

[New] ScannerFingerprint      scanner_fingerprint.json + sigma_map.nii.gz (F → F, H)
  host_scan_id, mtf {freq_cyc_per_mm[], values[]}, psf_sigma_mm_zyx[3],
  nps {freq_cyc_per_mm[], values[]}, sigma_map {path, sha256}

[New] HybridVolume            hybrid_volume.json + host_ct/hybrid_ct/lesion_mask .nii.gz (F → G, H)
  host_scan_id, site_id, draw_id, files {host_ct, hybrid_ct, lesion_mask}, insertion
  {method, params{}}, seed_hex, fingerprint_ref, trajectory_ref, snapshot_step

[New] Receipt                 receipt.json                       (G → H)
  commit {rulebook_hash, code_hash, committed_utc} (BEFORE job), fill {job_ids[], counts_sha256,
  chsh_S, h_min_per_round, witness_refs[], params_sha256, seed_hex, hybrid_volume_sha256},
  signature {alg "Ed25519", public_key_b64, sig_b64 over canonical_json(commit+fill)}, state
  committed|filled|signed|ledgered

[New] LedgerEntry             ledger.jsonl (one entry per line)  (G → H)
  index int, prev_hash hex64 (64×"0" for genesis), receipt_sha256, entry_hash = sha256(canonical(entry − entry_hash))

[New] ValidationReport        validation_report.json             (H → —)
  hybrid_refs[], realism {}, radiomics {}, utility {}, drift {}, certificate_stats {}, baseline {}, notes
```

Each NPZ schema (key names, dtypes, ndim = 3) is listed in `VOLUMES.md`. Each manifest's JSON Schema references the NPZ by path + sha256, and `shared/validate.py` checks the NPZ keys.

---

## 6. File Plan (Concrete Changes)

`RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`.

**Shared: contracts**

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/shared/__init__.py` | package marker |
| New | `RE/shared/README.md` | FROZEN notice (v1.0.0, 2026-10-28, INT-only changes) + module docs for every helper |
| New | `RE/shared/contracts/README.md` | contract index: name, canonical filename, producer, consumers, format, stub path |
| New | `RE/shared/contracts/VOLUMES.md` | volume conventions (§4) + NPZ key tables |
| New | `RE/shared/contracts/_envelope.schema.json` | envelope `$defs` (envelope, sim fields, file_ref, hex64) |
| New | `RE/shared/contracts/target_status.schema.json` | TargetStatus |
| New | `RE/shared/contracts/run_record.schema.json` | RunRecord |
| New | `RE/shared/contracts/anatomy_masks.schema.json` | AnatomyMasks manifest |
| New | `RE/shared/contracts/site_candidates.schema.json` | SiteCandidate / ContextVector |
| New | `RE/shared/contracts/rulebook.schema.json` | Rulebook |
| New | `RE/shared/contracts/compiled_circuit.schema.json` | CompiledCircuit |
| New | `RE/shared/contracts/quantum_job_record.schema.json` | QuantumJobRecord |
| New | `RE/shared/contracts/tumor_draw.schema.json` | TumorDraw |
| New | `RE/shared/contracts/certificate.schema.json` | Certificate (pass/fail `if/then`) |
| New | `RE/shared/contracts/witness_record.schema.json` | WitnessRecord (`bases` minItems 2) |
| New | `RE/shared/contracts/memory_advantage_record.schema.json` | MemoryAdvantageRecord |
| New | `RE/shared/contracts/simulability_report.schema.json` | SimulabilityReport |
| New | `RE/shared/contracts/quantum_lineage.schema.json` | QuantumLineage |
| New | `RE/shared/contracts/seed_shape.schema.json` | SeedShape manifest |
| New | `RE/shared/contracts/growth_trajectory.schema.json` | CellLattice / GrowthTrajectory manifest |
| New | `RE/shared/contracts/lesion_model_library.schema.json` | LesionModelLibrary |
| New | `RE/shared/contracts/scanner_fingerprint.schema.json` | ScannerFingerprint |
| New | `RE/shared/contracts/hybrid_volume.schema.json` | HybridVolume manifest |
| New | `RE/shared/contracts/receipt.schema.json` | Receipt |
| New | `RE/shared/contracts/ledger_entry.schema.json` | one `ledger.jsonl` line |
| New | `RE/shared/contracts/validation_report.schema.json` | ValidationReport |

**Shared: helpers**

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/shared/seedhash.py` | hashing, canonical JSON, code/git hash, `derive_seed`, `rng` (AC-7) |
| New | `RE/shared/volumes.py` | SimpleITK NIfTI read/write in LPS, `check_same_grid`, NPZ load/save with key check |
| New | `RE/shared/simbackend.py` | FakeMarrakesh factory, transpile, run, labels, calibration snapshot, circuit hash (AC-9); mirrors `artificial-life/code/backlog/stage3_teleport.py:497` |
| New | `RE/shared/runrecord.py` | `start_run` / `Run` (AC-8); mirrors `THESIS/CriticalQuantumLife/code/closed_loop.py:410` |
| New | `RE/shared/validate.py` | contract dispatch, file-ref + sha256 checks, volume checks, ledger chain, `--stubs`, `--status` CLI (AC-6) |
| New | `RE/shared/requirements.txt` | documents the already-installed deps (qiskit, qiskit-aer, qiskit-ibm-runtime, numpy, scipy, SimpleITK, jsonschema, markdown-it-py, jinja2, cryptography); no install step |

**Shared: stubs**

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/shared/stubs/__init__.py` | package marker |
| New | `RE/shared/stubs/make_stubs.py` | deterministic generator for every stub below (fixed seed `"00"*32`); builds a synthetic chest phantom of 160×128×80 voxels @ (2.0, 2.0, 2.5) mm; noise-free so the gz files stay small; runs the stub CHSH circuit on ideal Aer for the job record |
| New | `RE/shared/stubs/README.md` | the stub "story" (one tumor at `S001`), and a note that it is synthetic with no patient data |
| New | `RE/shared/stubs/anatomy_masks/{anatomy_masks.json, host_ct.nii.gz, lungs.nii.gz, lobes.nii.gz, vessels.nii.gz, airway.nii.gz, body.nii.gz}` | generated |
| New | `RE/shared/stubs/site_candidates/sites.json` | generated; 3 sites, one per placement class |
| New | `RE/shared/stubs/rulebook/rulebook.json` | generated; 2 nodes (type ← placement_class) with a placeholder citation marked stub |
| New | `RE/shared/stubs/compiled_circuit/{compiled_circuit.json, circuit.qasm}` | generated |
| New | `RE/shared/stubs/quantum_job_record/quantum_job_record.json` | generated from a real ideal-Aer run |
| New | `RE/shared/stubs/tumor_draw/tumor_draw.json` | generated |
| New | `RE/shared/stubs/certificate/certificate.json` | generated; `pass`, placeholder S and H_min |
| New | `RE/shared/stubs/witness_record/witness_record.json` | generated |
| New | `RE/shared/stubs/memory_advantage_record/memory_advantage_record.json` | generated |
| New | `RE/shared/stubs/simulability_report/simulability_report.json` | generated |
| New | `RE/shared/stubs/quantum_lineage/quantum_lineage.json` | generated |
| New | `RE/shared/stubs/seed_shape/{seed_shape.json, seed_shape.npz}` | generated; 7³ ball |
| New | `RE/shared/stubs/growth_trajectory/{growth_trajectory.json, step_0000.npz, step_0030.npz}` | generated; baseline + follow-up |
| New | `RE/shared/stubs/lesion_model_library/lesion_model_library.json` | generated |
| New | `RE/shared/stubs/scanner_fingerprint/{scanner_fingerprint.json, sigma_map.nii.gz}` | generated |
| New | `RE/shared/stubs/hybrid_volume/{hybrid_volume.json, host_ct.nii.gz, hybrid_ct.nii.gz, lesion_mask.nii.gz}` | generated; 8 mm sphere at `S001` |
| New | `RE/shared/stubs/receipt/receipt.json` | generated; Ed25519 stub signature |
| New | `RE/shared/stubs/ledger_entry/ledger.jsonl` | generated; 2 chained entries |
| New | `RE/shared/stubs/validation_report/validation_report.json` | generated |
| New | `RE/shared/stubs/run_record/run.json` | generated by `runrecord` during `make_stubs` |

**Shared: templates and site build**

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/shared/templates/LETTER_README.template.md` | 8 fixed sections + "Contract change requests" |
| New | `RE/shared/templates/DOSSIER.template.md` | 8 fixed dossier sections + header (letter, #, papers, state) |
| New | `RE/shared/site/__init__.py` | package marker |
| New | `RE/shared/site/build.py` | site build (AC-12); `--update-readme` flag; mirrors offline style of `QuantumPhantoms/code/f3_web/build_web.py` |
| New | `RE/shared/site/templates/base.html.j2` | page shell (nav: about · index · letters), GENERATED comment |
| New | `RE/shared/site/templates/index.html.j2` | letter cards + 21-row target table |
| New | `RE/shared/site/templates/page.html.j2` | rendered README / dossier page with status badge header |
| New | `RE/shared/site/style.css` | source stylesheet copied to `site/style.css`; light/dark tokens, state badge colours |

**Root of `RE/`**

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/README.md` | AI entry point (AC-14) with STATUS markers |
| New | `RE/about.html` | hand-written explainer (AC-13) |
| New (generated) | `RE/index.html` | first build output, committed by W |
| New (generated) | `RE/site/style.css`, `RE/site/<L>_<name>/index.html`, `RE/site/<L>_<name>/<NN>-<slug>.html` | 8 letter pages + 21 dossier pages, committed by W |

**Letter skeletons.** Every letter folder gets the same files (`<L>_<name>` ∈ `A_placement`, `B_mapping`, `C_certificate`, `D_quantum_growth`, `E_classical_growth`, `F_render`, `G_provenance`, `H_analysis`):

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/<L>_<name>/__init__.py`, `RE/<L>_<name>/src/__init__.py`, `RE/<L>_<name>/repro/__init__.py` | package markers |
| New | `RE/<L>_<name>/figures/.gitkeep` | keeps the folder in git |
| New | `RE/<L>_<name>/README.md` | instantiated letter README |
| New | `RE/<L>_<name>/status.json` | pre-filled TargetStatus |

**Dossier stubs.** One file per target, under each letter's `dossiers/` folder:

| Letter folder | Dossier files |
|---|---|
| `RE/A_placement/dossiers/` | `18-syn-lungs-placement.md` |
| `RE/B_mapping/dossiers/` | `01-bn-circuit-compiler.md`, `02-quantum-enhanced-mcmc.md`, `03-quantum-blur.md` |
| `RE/C_certificate/dossiers/` | `04-bell-entropy-accounting.md`, `05-curby-beacon-chain.md` |
| `RE/D_quantum_growth/dossiers/` | `06-quantum-causal-states.md`, `07-goldilocks-qca.md`, `08-dynamic-circuit-feedforward.md`, `09-bp-heavy-hex-adversary.md`, `10-measurement-induced-transition.md` (#10 also keeps the post-selection note; see Q1) |
| `RE/E_classical_growth/dossiers/` | `11-pixel2cancer.md`, `12-hpc-cellular-automaton.md` |
| `RE/F_render/dossiers/` | `13-synthetic-tumors.md`, `14-lesion-model-fitting.md`, `15-scanner-fingerprint.md`, `16-xcist-projection-insertion.md`, `17-naeotom-alpha-params.md` |
| `RE/G_provenance/dossiers/` | `19-ct-gan-tamper-test.md` |
| `RE/H_analysis/dossiers/` | `20-victre-pipeline.md`, `21-ai-rad-companion.md` |

**Untouched:**
- `.gitignore`: the rules are already present at lines 17–20. W verifies them only.
- `epic-reverse-engineering.md` and `reverse-engineering-targets.md`.
- Everything outside `RE/`.

---

## 7. Manual Verification (No Tests)

All commands run from `QuantumPhantoms/plans/relatedPapers/reverse-engineering/` with the conda base `python`.

- [x] **Verify AC-1:** `ls -d */` lists `A_placement/ B_mapping/ C_certificate/ D_quantum_growth/ E_classical_growth/ F_render/ G_provenance/ H_analysis/ shared/ site/`. `ls A_placement` shows `README.md status.json dossiers src repro figures __init__.py`.
- [x] **Verify AC-2:** `ls shared/contracts/*.schema.json | wc -l` gives **22** (envelope + 21 contracts). Open `shared/contracts/README.md`: every row has a producer, consumers and a stub path that exists.
- [x] **Verify AC-3:** Open `shared/contracts/VOLUMES.md` and check that it states LPS, `(z, y, x)`, `int16` HU, `uint8` masks and the cell codes 0–3.
  Then run `python -c "from shared.volumes import read_volume; a,meta=read_volume('shared/stubs/hybrid_volume/hybrid_ct.nii.gz'); print(a.dtype, a.shape, meta)"`. Expected: `int16 (80, 128, 160)`, spacing `(2.0, 2.0, 2.5)` and identity direction.
- [x] **Verify AC-4:** Copy the stub certificate to a temp file, set `"status": "fail"` while keeping a non-null seed, and run `python -m shared.validate <tmp>`. Expected: non-zero exit, with an error on `/extracted_seed_hex`.
  Then delete `sim_label` from a copy of the job record and validate again. Expected: rejected.
- [x] **Verify AC-5:** Run `python -m shared.stubs.make_stubs`, then `git status --short shared/stubs`. Expected: no changes (regeneration is byte-identical; timestamps are fixed to `2026-10-28T00:00:00Z` in stubs).
  Also run `du -sh shared/stubs`. Expected: ≲ 2 MB.
- [x] **Verify AC-6:** `python -m shared.validate --stubs` prints one `OK` line per stub file (20 stub contracts; `target_status` is covered by `--status` against the real letter files) and exits `0` (`echo $?` gives `0`). Then flip one byte of `shared/stubs/hybrid_volume/lesion_mask.nii.gz` in a temp copy of the folder and validate it. Expected: an sha256 mismatch is reported.
- [x] **Verify AC-7:** `python -c "from shared.seedhash import derive_seed, rng; print(derive_seed('00'*32,'E.growth'), derive_seed('00'*32,'E.growth'), derive_seed('00'*32,'F.noise'))"`. Expected: the first two values are equal and the third differs. Also check that `python -c "import shared.seedhash, sys; print('qiskit' in sys.modules)"` prints `False`.
- [x] **Verify AC-8:** Open `shared/stubs/run_record/run.json`. It should contain code hash, git state, seed, sim mode, the `calibration_snapshot` with `fake_backend: "FakeMarrakesh"`, and one job with `counts_file`. The stub generator also leaves a real run dir under `shared/runs/` (gitignored). Confirm that `git check-ignore -v` matches it.
- [x] **Verify AC-9:** `python -c "from shared.simbackend import *; from qiskit import QuantumCircuit; q=QuantumCircuit(2); q.h(0); q.cx(0,1); q.measure_all(); print(run_counts(q,'ideal',1000,7)[0], run_counts(q,'heron',1000,7)[0], sim_label('heron'))"`. Expected:
  - ideal gives only `00`/`11`;
  - heron has a small `01`/`10` leakage;
  - the label is exactly `simulated: Heron-class noise (FakeMarrakesh)`.
- [x] **Verify AC-10:** `python -m shared.validate --status` gives OK for all 8 letters. `python -c "import json,glob; print(sorted(t['number'] for f in glob.glob('*_*/status.json') for t in json.load(open(f))['targets']))"` gives `[1..21]` with no gaps or duplicates.
- [x] **Verify AC-11:** Open `D_quantum_growth/README.md`. It should show all 8 fixed sections + "Contract change requests", targets #6–#10, Inputs (TumorDraw, Certificate stubs) and Outputs (WitnessRecord, MemoryAdvantageRecord, SimulabilityReport, QuantumLineage, SeedShape). Open `F_render/dossiers/15-scanner-fingerprint.md`. It should show the 8 dossier sections.
- [x] **Verify AC-12:** Run `python -m shared.site.build --update-readme`, then open `index.html` in a browser **with networking disabled** (or check the DevTools network tab). Expected:
  - 8 letter cards and 21 table rows;
  - the badges read `listed` (and #10 per Q1);
  - every dossier link opens its page;
  - the about link works.

  Running `grep -rE '(src|href)="https?://' index.html site/` should print nothing. As a negative check, corrupt a `state` in a temp copy of a status file. Expected: the build aborts naming the file.
- [x] **Verify AC-13:** Open `about.html` offline. The A→H SVG diagram, the claim ladder and the sim-only and privacy sections render in both the light and dark OS themes. `grep -c '<script' about.html` gives `0`.
- [x] **Verify AC-14:** Read `README.md` top to bottom as a fresh agent would. It names the cwd, the commands, the ownership rules and the contract index. The table between the STATUS markers matches `index.html`.
- [x] **Verify AC-15:** `head -5 shared/README.md` shows the FROZEN notice. `git diff .gitignore` contains no changes from W. `git check-ignore -v ../papers/x.pdf A_placement/runs/x` matches both rules.
- [x] **Edge case — MVP isolation:** `grep -rn "QuantumPhantoms/code\|from common\|import f1_quantum" shared/` prints nothing.
- [ ] **Edge case — release gate:** W is committed to `main` before any `git worktree add ../qp-re-<L> -b re-<L>` (epic §7).

---

## 8. Open Questions

- [x] **Q1: How should W record target #10?** The W row's done-criterion says "all 21 targets as `listed`". Decision 5 says #10 is recorded as `rejected (out of scope)` in `D_quantum_growth/status.json`. *Resolved (accepted default):* W pre-fills #10 as `rejected` with `rejection_reason: "out of scope (epic decision 5, D-4 not built)"`, and writes its dossier with only the post-selection note. The site then renders 20 `listed` + 1 `rejected`. The done-criterion is read as "all 21 targets present".
- [x] **Q2: Where should the plan file live?** *Resolved (accepted default):* `RE/feature-W-foundation.md`, following the epic §3 layout `feature-<L>-<name>.md`, rather than the command's default `tasks/plans/`. It is already saved there.
- [x] **Q3: Which NIfTI library and frame?** nibabel is not installed; SimpleITK is. *Resolved (accepted default):* SimpleITK only, in the DICOM/ITK **LPS** frame with identity direction and numpy `(z, y, x)`. This means no new install, and the frame matches DICOM hosts natively.
- [x] **Q4: Should the stubs be committed or regenerated?** *Resolved (accepted default):* commit them. They are small, because the phantom is noise-free (≲ 2 MB). Each worktree then has them immediately, and `make_stubs.py` keeps them reproducible byte-for-byte.
- [x] **Q5: Who commits the generated site?** Epic §3 says only INT commits the rebuilt site. *Resolved (accepted default):* W commits the **initial** `index.html` + `site/`, all targets at their initial state, so the done-criterion is visible in git. After that only INT commits rebuilds.
- [x] **Q6: Should ideal-mode circuits also be transpiled to the `FakeMarrakesh` target?** *Resolved (accepted default):* yes. Gate counts and depth are then identical across modes, so only the noise differs, which matches "design as if it had to run on Heron r2".
- [x] **Q7: How should equations render in dossiers?** *Resolved (accepted default):* no math rendering, because MathJax/KaTeX need a CDN. Equations are written in Unicode inline or as fenced `text` blocks. A later INT could vendor KaTeX locally if wanted.
- [x] **Q8: Should W add `RunRecord` (`run.json`) and the `ledger.jsonl` line format as contracts?** Neither is a separate row in epic §4. *Resolved (accepted default):* yes. They are implied by §3 "Logging" and the `Receipt / LedgerEntry` row. Note them in the epic at INT.
- [x] **Q9: Should W freeze the domain enums?** These are the placement classes (`free | juxtavascular | juxtapleural`), tumor types (`solid | part-solid | ground-glass`), margins (`smooth | lobulated | spiculated`), cell states 0–3 (+ 4–15 reserved), and the minimal required context-vector keys (§5 SiteCandidates). *Resolved (accepted default):* freeze as listed. A, B, E and F extend only through `extra{}` / reserved codes, or through contract change requests.

---

## 9. Post-Implementation Notes

**Built (2026-10-28, on `main`, uncommitted at hand-back).** 22 JSON Schemas, 20 stub contracts (472 KB; they regenerate byte-identically), 6 helper modules, the site build with 3 jinja2 templates + CSS, 2 Markdown templates, 8 letter skeletons (8 status.json, 8 READMEs, 21 dossiers), `about.html`, root `README.md`, and the first `index.html` + `site/` (34 pages, 20 listed + 1 rejected).

**AC evidence:**

| AC | Evidence |
|---|---|
| AC-1 | `A_placement/` … `H_analysis/` (each `README.md`, `status.json`, `dossiers/`, `src/__init__.py`, `repro/__init__.py`, `figures/.gitkeep`); `shared/__init__.py:12` `LETTERS` |
| AC-2 | `shared/contracts/_envelope.schema.json:205` envelope; 21 contract schemas; index `shared/contracts/README.md` |
| AC-3 | `shared/contracts/VOLUMES.md`; `shared/volumes.py:30` `read_volume`, `:52` `write_volume`, `:75` `check_same_grid`, `:84` `save_npz` |
| AC-4 | `shared/contracts/_envelope.schema.json:242` quantum gate; `shared/contracts/certificate.schema.json:122` pass/fail `if/then`; `shared/contracts/witness_record.schema.json:60` bases ≥ 2 |
| AC-5 | `shared/stubs/make_stubs.py:89` phantom, `:454` `main`; `shared/stubs/README.md` story |
| AC-6 | `shared/validate.py:64` `schema_errors`, `:116` `_semantic_errors`, `:162` `_verify_signature`, `:175` `ledger_errors`, `:207` `stub_files`, `:255` CLI |
| AC-7 | `shared/seedhash.py:52` `code_hash`, `:70` `git_state`, `:82` `derive_seed`, `:88` `rng` |
| AC-8 | `shared/runrecord.py:106` `start_run`, `:55` `add_job`, `:95` `finish` (validates before write) |
| AC-9 | `shared/simbackend.py:19` `REFERENCE_FAKE`, `:40` `make_simulator`, `:52` `transpile_heron`, `:57` `circuit_hash`, `:62` `run_counts`, `:70` `calibration_snapshot` |
| AC-10 | `<L>_*/status.json` (21 targets; `D_quantum_growth/status.json:95` #10 `rejected`); `shared/validate.py:216` `check_status_set` |
| AC-11 | `shared/templates/LETTER_README.template.md`, `shared/templates/DOSSIER.template.md`; instantiated in every letter |
| AC-12 | `shared/site/build.py:141` `build`, `:36` external-asset guard, `:179` `update_readme`; `index.html`, `site/` |
| AC-13 | `about.html:70` SVG pipeline, `:135` claim ladder, `:151` simulation only, `:162` privacy |
| AC-14 | `README.md` (ownership rules, conventions, contracts), `README.md:88` STATUS block |
| AC-15 | `shared/README.md:1` FROZEN notice; `.gitignore:19-20` unchanged, and `git check-ignore` matches `papers/` and `**/runs/` |

**Manual verification run (all passed):**
- `--stubs` gives 20 × OK and `--status` gives 8 × OK, exit 0.
- Regenerating the stubs is byte-identical.
- A `fail` certificate with a seed is rejected at `/extracted_seed_hex`.
- A `pass` certificate with S = 1.9 is rejected.
- A job record without `sim_label` is rejected.
- Flipping one byte in `lesion_mask.nii.gz` gives an sha256 mismatch.
- A tampered receipt fails the Ed25519 check.
- `derive_seed` is deterministic and label-separated, and importing `seedhash`, `volumes`, `runrecord` and `validate` loads no qiskit.
- The ideal Bell state gives only `00`/`11`; heron mode leaks 16/1000 into `01`/`10`.
- A real `start_run('A_placement', …)` records git state and the Heron sim label, its output validates, and the test run dir was deleted afterwards.
- A bad `state` aborts the build and names the file.
- 774 relative links in the site all resolve, and no external `src`/`href` exists.
- Headless Chrome screenshots of `index.html` and `about.html` render correctly.
- The MVP-isolation grep is clean.

**Deviations from the plan:**
- Dossier pages render to `site/<L>/dossiers/<NN>-<slug>.html` instead of the planned `site/<L>/<NN>-<slug>.html`. Mirroring the source tree keeps relative links correct. The shared docs (`shared/README.md`, contracts README, VOLUMES, stubs README) are also rendered under `site/shared/`.
- The stub quantum job record runs the **compiled 2-node BN stub circuit** on ideal Aer, not a separate CHSH circuit. This keeps one consistent story (job → draw). The certificate values remain placeholders.
- The stub `run.json` has `git: null` (`include_git=False`) so the stubs stay byte-identical across commits. Real runs record `{commit, dirty}`, with `dirty` scoped to `reverse-engineering/`.
- `target_status` and `ledger_entry` carry `contract` / `contract_version` but not the full envelope. `status.json` is hand-edited, and each ledger line is hashed on its own.
- JSON vectors are named with an explicit axis order (`spacing_mm_xyz`, `origin_mm_lps`, `center_vox_zyx`), a slight rename of §5's `spacing_mm[3]` and similar fields. The rule is in VOLUMES.md.
- The exploration agent was skipped. Every file is new and there was nothing existing to trace. A direct API probe confirmed the FakeMarrakesh props file, Aer on a 156-qubit transpiled circuit, qasm3, SimpleITK and markdown-it.
- No lint config exists in the repo. pyflakes is clean; a few lines are over 120 characters in `make_stubs.py` / `build.py`.

**Follow-ups:**
- Commit W to `main` **before** creating any wave-1 worktree (A, C, E, F). The release-gate edge case in §7 stays open until then.
- Note `RunRecord` + `ledger.jsonl` in epic §4 at INT (Q8).
- D must check Aer support for noisy dynamic-circuit feed-forward (not covered by `simbackend`).
- Any later change to `shared/*.py` (INT only) requires `python -m shared.stubs.make_stubs`, because the stubs embed `code_hash(shared/)`.
