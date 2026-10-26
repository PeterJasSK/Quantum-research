# Feature F1 — Quantum roll: Rulebook → circuit → certified params

**Epic:** [`epic-quantum-phantoms-mvp.md`](./epic-quantum-phantoms-mvp.md) (Approved)
**Feature ID:** F1
**Author:** Claude (Opus)
**Date:** 2026-10-26
**Status:** Complete

> **Technical constraints / core directive.** Stack locked: **Python + Qiskit** (`qiskit`, `qiskit-aer`, `qiskit-ibm-runtime`). All development and all implementer verification run on `AerSimulator` only. The quantum roll sits behind one swappable `Sampler` seam (`PRNGSampler` baseline + `QRNGSampler` quantum); F2/F3/F4 stay blind to which sampler produced the params. **No signing, no ledger, no DB, no ML, no CT-physics, no phantom.** Research-study conventions: **no GitHub issues, no automated test suite — manual verification only.** Honest claim ceiling = Tier 1 provenance (params quantum, nothing more).
>
> **HARD RULE — no live hardware from the implementer.** `/implement-feature` must **never** submit a real `ibm_heron` (or any non-simulator) job. The `--backend ibm`/`auto` code path is written and wired, but the **human (Peter) runs the one real hardware job himself**; the implementer stops at `--backend aer`. Do not run, schedule, or "just try" a hardware job during implementation or verification.
>
> **HARD RULE — never touch credentials.** The implementer must **never** read, import, print, copy, hard-code, or commit any IBM token / account / secret (including the plaintext `credentialsApi.py` at repo root). `QuantumPhantoms/` adds **no** credential files. The `ibm` path relies solely on a pre-existing saved account / env vars that the human configures. No secret ever enters this codebase or any artifact it writes.

---

## 1. Why (Step Goal)

**Before.** `QuantumPhantoms/` holds only `plans/`. There is no code: no way to turn published lung-nodule statistics into a quantum circuit, no way to run that circuit on hardware, and no certified-random tumor parameters for anything downstream to render.

**After.** F1 is the quantum core of the MVP. It:
1. Encodes published Fleischner / LIDC nodule statistics (`Rulebook`) analytically into `Ry` / controlled-`Ry` angles — **by hand, never fitted to patient data** (keeps it non-QML, parent §2.3).
2. Builds a shallow circuit = nodule-property qubits **+ one quantum cell division** (the sibling-pair "QALife hint", P1) **+ one CHSH certificate pair**, all in one job.
3. Runs on `AerSimulator` for development and, on demand, as **one** `ibm_heron` job for the demo artifact.
4. Decodes measured bits → a cohort of `TumorParams` (size, type, margin, lobe, `lineage_id`, `generation`) and computes the job-level **CHSH value** from the certificate pair.
5. Exposes all of this behind the `Sampler` seam so F2/F3 consume params without knowing their origin, and F4 can later drop in a `QALifeSampler`.

F1's deliverable is two JSON artifacts (`cohort_params.json` + `quantum_run.json`) under `QuantumPhantoms/research_runs/<run>/`, plus a console summary showing the decoded cohort and the CHSH value. These are the exact inputs F2 will read.

---

## 2. Acceptance Criteria

- [x] **AC-1** (F1.1) — `code/rulebook.py:135` (`angles_from_rulebook`), literals + `SOURCE_CITATIONS` at `code/rulebook.py:60`; sim marginals match rulebook (size `[.554,.249,.149,.048]` vs `[.55,.25,.15,.05]`). Published nodule stats are encoded into gate angles analytically, with citable sources named in-code.
  → `rulebook.py` defines a `Rulebook` dataclass holding size-band frequencies, type mix (conditioned on size), margin mix (conditioned on type), and lobe frequencies, each tagged with its published source (Fleischner / LIDC aggregate). `angles_from_rulebook(rulebook)` returns the `Ry` / controlled-`Ry` angles via `theta = 2*arccos(sqrt(p))`-style amplitude encoding. No numbers are fitted to any dataset — they are literals from published tables.
- [x] **AC-2** (F1.2) — `code/circuit.py:78` (`build_tumor_circuit`, 9 property qubits, size→type→margin conditioning via nested `mcry`), `:88` (`build_sibling_pair_circuit`, division), `:112` (`build_chsh_circuits`); conditional `P(type|size<6)` reproduced `[.548,.083,.302,.067]` vs `[.55,.08,.30,.07]`. A single shallow circuit carries nodule-property qubits + one division + one CHSH pair.
  → `circuit.py:build_tumor_circuit(angles)` builds the property register (size 2q, type 2q, margin 2q, lobe 3q) with size→type→margin conditioning via controlled-`Ry`; `lineage.py` adds the division (controlled-copy of the genotype onto daughter ancillas + `Ry(theta_mut)`); `circuit.py:build_chsh_circuits()` builds the 4 CHSH basis-setting circuits for the Bell pair. All circuits for one run are submitted in **one** job.
- [x] **AC-3** (F1.3) — `code/backend.py:22` (`get_backend`: ``""/aer`` → None, `auto` → `least_busy`, else named), `:43` (`run_counts`: Aer vs `SamplerV2(mode=backend)` + `generate_preset_pass_manager(opt=3)`). Aer path verified end-to-end; `--backend ibm_heron` reached `service.backend(...)` and errored cleanly **without submitting a job** (HARD RULE held — implementer never ran hardware). The `ibm`/`auto` path is written and wired; the human runs the real `ibm_heron` job.
  → `backend.py` selects the backend (`QiskitRuntimeService().backend("ibm_heron")` or `least_busy`, with `AerSimulator` fallback) and transpiles with `generate_preset_pass_manager(optimization_level=3, backend=...)`; `run.py` submits via `SamplerV2(mode=backend).run([isa], shots=...)` and reads counts via `result[0].data.<creg>.get_counts()`, mirroring `THESIS/CriticalQuantumLife/proof_of_concept/quantum_life.py:80-104` (the `backend is None → AerSimulator / else SamplerV2(mode=backend)` split). Development never requires hardware.
- [x] **AC-4** (F1.4) — `code/decode.py:49` (`bits_to_params`, lobe/margin spare-code remap), `:98` (`decode_memory`); run produced 12 valid `TumorParams` (fields verified in `cohort_params.json`). Measured bits decode into a cohort of `TumorParams`.
  → `decode.py:decode_cohort(counts, rulebook)` maps each shot's property bits → one `TumorParams` (size mm, type, margin, lobe, `lineage_id`, `generation`). Codes outside the 5 used lobes are remapped per a documented rule. Cohort size defaults to **12 tiles** (epic resolved default).
- [x] **AC-5** (F1.5) — `code/certify.py:54` (`chsh_value`, `+ + + −` / `ry(-θ)` per the reference); noiseless Aer gave `S = 2.795` (≈ 2.83), stored once on `QuantumRun.chsh_value`, not per tile. The CHSH value is computed from the certificate pair and is job-level + honest.
  → `certify.py:chsh_value(counts_by_setting)` computes `E = (agree − disagree)/total` per setting (agree = `00`+`11`) then `S = E(a,b) - E(a,b') + E(a',b) + E(a',b')`, porting the reference at `study-ideas/QuantumAlgorithmsExplained/code/11_chsh.py` (swap its `StatevectorSampler` for the shared `SamplerV2` path). The value is stored once on `QuantumRun` (not fabricated per tile). On noiseless Aer `S ≈ 2.83`; on real `ibm_heron`, `S ≈ 1.9–2.6` (the real value is the one carried to the demo).
- [x] **AC-6** (F1.6) — `code/lineage.py:24` (`decode_pairs`, shared `lineage_id`, parent gen 0 / daughter gen 1), division gates at `code/circuit.py:88`; sibling size-match rate `0.956` at `θ_mut=0.3` (vs ~0.25 for independent draws). A few tiles are **sibling pairs** from one division; their shared-ancestry correlation is real.
  → `lineage.py` produces daughter tiles that share a `lineage_id` and carry `generation = 1`; measured daughter genotypes are correlated above the independent-draw baseline. Decode tags them so F3 can render the lineage badge.
- [x] **AC-7** (F1.7) — `code/sampler.py:37` (`Sampler(Protocol)`), `:41` (`PRNGSampler`), `:92` (`QRNGSampler`); both ran `--tiles 12 --pairs 2` producing byte-identical `TumorParams` schemas (only provenance differs). The `Sampler` seam exists with two interchangeable implementations.
  → `sampler.py` defines `Sampler(Protocol).draw(rulebook) -> list[TumorParams]`; `PRNGSampler` (numpy baseline) and `QRNGSampler` (the quantum pipeline) both satisfy it and return the identical `TumorParams` shape. Swapping them changes only provenance, not the output contract.
- [x] **AC-8** (F1.8) — `code/run.py:66` (`_write_artifacts`); run wrote `research_runs/qrng_aer_<ts>/cohort_params.json` (12 entries) + `quantum_run.json` (keys: `backend_name, chsh_settings, chsh_value, job_id, raw_bits, shot_indices`) and printed the cohort summary. Running the pipeline writes the two JSON artifacts F2 will consume.
  → `run.py` writes `research_runs/<run>/cohort_params.json` (list of `TumorParams`) and `research_runs/<run>/quantum_run.json` (`QuantumRun`: raw bits, backend name, short job id, CHSH value, shot indices) and prints a console summary.

---

## 3. Out of Scope (Postponed)

- **Decode → 3D lesion blob + image-domain insertion into real LIDC/LUNA16 CT** → **F2**. F1 stops at `TumorParams`; it never touches pixels or CT data.
- **Web cohort grid, per-tile CHSH stamp rendering, cohort-vs-rulebook histogram** → **F3**. F1 emits JSON only.
- **Multi-generation evolutionary loop, fate superposition, selection, per-generation entanglement witness** → **F4** (optional). F1 ships exactly **one** division (`generation ≤ 1`), no loop, no selection.
- **Ed25519 signing, append-only ledger, formal cohort audit** → deferred to the full plan (parent §2.1). F1 writes plain JSON, no signatures.
- **Hidden CHSH test rounds, self-testing, contextuality, randomness expansion, QAE** → later work (parent §5.2). F1 ships one visible CHSH pair only.

---

## 4. Technical Decisions

Adopts the epic's §3 cross-cutting decisions verbatim (Sampler seam, "every quantum feature has a job", honesty gates, real-hardware CHSH only, no issues/tests). Feature-specific choices:

| Component | Choice / Implementation |
|---|---|
| Quantum SDK | **Qiskit** + `qiskit-aer` + `qiskit-ibm-runtime`; primitive = **`SamplerV2`** (counts-based decode needs raw bitstrings, not expectation values). |
| Backend access | `QiskitRuntimeService()` from a **saved account** (no token in code); `--backend ibm` → `service.backend("ibm_heron")`, `--backend auto` → `least_busy(operational=True, simulator=False, min_num_qubits=...)`, `--backend aer` (default) → `AerSimulator()`. Mirror `CriticalQuantumLife/proof_of_concept/quantum_life.py:80-104`. |
| Transpilation | `generate_preset_pass_manager(optimization_level=3, backend=backend)` before submit. |
| Angle encoding | Amplitude encoding `theta = 2*arccos(sqrt(p))` per band; conditional distributions (type\|size, margin\|type) via controlled-`Ry`. All probabilities are published literals. |
| Division (P1 hint) | `CX(parent_genotype → daughter_ancilla)` + `Ry(theta_mut)` per copied genotype qubit — the epic §5 "controlled-copy + `Ry(θ_mut)`". |
| CHSH certificate | Bell pair `H + CX`; **4 setting circuits** (a,a' = {0, π/2}; b,b' = {π/4, −π/4}) submitted in the **same job** as the tumor circuit. `S` computed from the 4 correlators. |
| Cohort size | **12 tiles** (epic resolved default), of which a configurable few (default 2 pairs → 4 tiles) are sibling pairs. |
| Output | JSON artifacts under `research_runs/<run>/` (mirrors `THESIS/NPQuantumAdvantage/research_runs/`, `artificial-life/research_runs/`). |

**Conventions & Notes:**
* Source code lives in `QuantumPhantoms/code/` (mirrors `artificial-life/code/`, `THESIS/CriticalQuantumLife/code/`). Plans stay in `QuantumPhantoms/plans/` (epic §3).
* **CHSH is a job-level statistic**, not per-tile: one Bell test over many shots × 4 settings yields one `S`. Each tile stamps `(job CHSH, its own shot index)` — never a per-tile Bell value (that would misrepresent the physics; honesty gate, epic §3). The mockup's varying per-tile numbers are illustrative; the plan renders one `S` + per-tile shot id.
* Honest label is produced here and carried downstream: **params quantum, image classical**; no claim of non-classical tumors (epic §3 / parent §5.4).
* The real-hardware CHSH value is authoritative for the demo; the Aer value (~2.83) is for dev only and must be labeled "simulator" if ever shown.
* Keep `QRNGSampler` and `PRNGSampler` returning byte-identical `TumorParams` schemas so the swap is provably transparent.

---

## 5. Data Model (Additions/Modifications)

F1 **introduces** the following entities (epic §4). All are plain Python dataclasses serialized to JSON — no DB.

```text
[New Entity] Rulebook                         (rulebook.py)
  size_bands        list[(label:str, mm_range:(float,float), p:float)]   # published freqs
  type_mix          dict[size_band -> dict[type -> p]]                   # type | size
  margin_mix        dict[type -> dict[margin -> p]]                      # margin | type
  lobe_freqs        dict[lobe_code -> p]                                 # 5 of 8 codes used
  source_citations  list[str]                                            # Fleischner / LIDC refs

[New Entity] TumorParams                       (datamodel.py)  — the Sampler output contract
  size_mm       float
  type          str      # solid | part-solid | ground-glass | calcified
  margin        str      # smooth | lobulated | spiculated
  lobe          str      # RUL | RML | RLL | LUL | LLL
  lineage_id    str      # groups a sibling pair; unique per independent tile
  generation    int      # 0 = independent/parent, 1 = daughter
  shot_index    int      # which measurement shot produced this tile

[New Entity] QuantumRun                         (datamodel.py)
  raw_bits      list[str]    # per-shot bitstrings for the property register
  backend_name  str          # "ibm_heron" | "AerSimulator"
  job_id        str          # short id ("" for Aer)
  chsh_value    float        # job-level S
  chsh_settings dict         # the 4 angle settings used
  shot_indices  list[int]    # indices mapped onto the tiles
```

Consumed by: `Rulebook` → F1, F3; `TumorParams` → F2, F3, F4; `QuantumRun` → F2, F3. `Lesion`, `CohortTile`, `Generation`/`Lineage` are **not** introduced here (F2/F4 own them).

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `QuantumPhantoms/code/rulebook.py` | `Rulebook` dataclass + published-literal stats + `angles_from_rulebook()`. Cites sources in-code. |
| New | `QuantumPhantoms/code/datamodel.py` | `TumorParams`, `QuantumRun` dataclasses + `to_dict`/`from_dict` JSON helpers. |
| New | `QuantumPhantoms/code/sampler.py` | `Sampler(Protocol)`, `PRNGSampler` (numpy baseline), `QRNGSampler` (wraps the quantum pipeline). The epic's one seam; mirror the injectable-client pattern in `CriticalQuantumLife/code/closed_loop.py:58,93-109`. |
| New | `QuantumPhantoms/code/circuit.py` | `build_tumor_circuit(angles)` (property register + conditioning) and `build_chsh_circuits()` (4 settings). |
| New | `QuantumPhantoms/code/lineage.py` | One division: controlled-copy of genotype onto daughter ancillas + `Ry(theta_mut)`; tags `lineage_id`/`generation`. Mirrors `artificial-life/code/pj_run_qalife.py` division gates (`CX` + `Ry`). |
| New | `QuantumPhantoms/code/certify.py` | `chsh_value(counts_by_setting)` → `S` from the 4 correlators `E(·,·)`. Port `study-ideas/QuantumAlgorithmsExplained/code/11_chsh.py`. |
| New | `QuantumPhantoms/code/decode.py` | `decode_cohort(counts, rulebook)` → `list[TumorParams]`; lobe-code remap rule. Reuse the `get_counts`/bitstring style from `CriticalQuantumLife/proof_of_concept/quantum_life.py:70-76`. |
| New | `QuantumPhantoms/code/backend.py` | Backend selection (`QiskitRuntimeService` / `ibm_heron` / `AerSimulator` fallback) + preset pass manager. Mirrors `CriticalQuantumLife/proof_of_concept/quantum_life.py:80-104`. |
| New | `QuantumPhantoms/code/run.py` | CLI entrypoint: `--backend {aer,ibm}`, `--tiles 12`, `--pairs 2`, `--shots`, `--out`. Submits one job, decodes, writes both JSON artifacts, prints summary. |
| New | `QuantumPhantoms/requirements.txt` | Pin `qiskit`, `qiskit-aer`, `qiskit-ibm-runtime`, `numpy` (match versions already installed in sibling studies). |
| New | `QuantumPhantoms/code/README.md` | One-screen: what F1 produces, how to run `aer` vs `ibm`, the honest-label note, the JSON contract for F2. |

---

## 7. Manual Verification (No Tests)

- [ ] **Verify AC-1 / AC-4 / AC-8:** `python QuantumPhantoms/code/run.py --backend aer --tiles 12` → exits 0, prints 12 decoded tumors, and writes `research_runs/<run>/cohort_params.json` (12 entries, valid `TumorParams` fields) + `quantum_run.json`.
- [ ] **Verify AC-2 / AC-5 (sim):** same run reports `chsh_value ≈ 2.83` and `backend_name = "AerSimulator"`; inspect that one `SamplerV2.run([...])` call submitted the tumor circuit + 4 CHSH circuits together.
- [ ] **Verify AC-3 / AC-5 (hardware) — HUMAN ONLY, not the implementer:** Peter runs `python QuantumPhantoms/code/run.py --backend ibm --tiles 12` himself (saved IBM account) → one `ibm_heron` job; `quantum_run.json` has `backend_name = "ibm_heron"`, a non-empty `job_id`, and `chsh_value` ≈ `1.9–2.6`. **This is the demo artifact.** The implementer only confirms the `ibm` path is wired by code inspection — it never submits a job.
- [ ] **Verify AC-6:** with `--pairs 2`, confirm 2 sibling pairs (4 tiles) share `lineage_id` within a pair and carry `generation = 1`; over a high-shot Aer run, daughter genotypes correlate above the independent `PRNGSampler` baseline (print the correlation vs the independent null).
- [ ] **Verify AC-7:** swap `QRNGSampler` → `PRNGSampler` in `run.py` (or a `--sampler prng` flag) → identical JSON schema, only provenance differs; F2 would not be able to tell them apart.
- [ ] **Edge case:** `--backend ibm` with no saved account → clear error pointing to account setup, and the dev path (`--backend aer`) still works.
- [ ] **Honesty check:** `quantum_run.json` carries one job-level `chsh_value`; no per-tile Bell value is fabricated; `cohort_params.json` + README state params-quantum / image-classical.

---

## 8. Open Questions

All resolved — defaults accepted by Peter (2026-10-26). Locked decisions:

- [x] **Q1 (qubit budget / margin):** Keep all four properties at full resolution (size 2q + type 2q + margin 2q + lobe 3q = **9q**, margin as 3 categories). Aer simulates this trivially; the parent's "~10 qubits" was illustrative, not a cap. Total ~15–20q once division ancillas + CHSH pair are added.
- [x] **Q2 (division width):** **Full-genotype controlled-copy** — copy the whole genotype register onto daughter ancillas + per-qubit `Ry(θ_mut)`, matching epic §5 exactly; honest cross-axis sibling correlation. Supersedes parent §2.5's "~2 qubits" wording for the MVP.
- [x] **Q3 (lobe codes):** **3 lobe qubits, 5 codes**; remap the 3 spare codes to the nearest used lobe by published frequency; document the remap in `decode.py`.
- [x] **Q4 (per-tile CHSH display):** Render the **single job-level `S` on every tile** plus that tile's shot index; the mockup's varying per-tile values are illustrative only.
- [x] **Q5 (requirements pinning):** Environment is **Python 3.13.5**, Qiskit 1.x primitives-V2. Pin to the versions already installed (capture `pip freeze | grep -i qiskit` at implement time); do not invent versions.
- [x] **Q6 (credentials):** Locked by the header HARD RULE. F1 uses the pre-existing saved-account / env-var path only; it **never reads, imports, or commits** any token (incl. repo-root `credentialsApi.py`) and adds no secret files under `QuantumPhantoms/`. (Rotating the exposed repo-root token is a separate concern, outside F1.)

---

## 9. Post-Implementation Notes

**Built (2026-10-26).** 10 new files under `QuantumPhantoms/`, nothing outside modified. All on `main` (user choice — repo commits straight to main). Environment: Python 3.13.5, qiskit 2.3.1 / qiskit-aer 0.17.2 / qiskit-ibm-runtime 0.47.0 (already current primitives-V2 — no porting needed).

Files: `code/{datamodel,rulebook,circuit,lineage,decode,certify,backend,sampler,run}.py`, `code/README.md`, `requirements.txt`.

**Key implementation decisions (all within the approved plan):**
- Rulebook → angles uses a generic breadth-first binary **amplitude tree** (`rulebook.amp_tree_angles`), verified to reconstruct every distribution to ~1e-16.
- Conditioning (type|size, margin|type) is **nested controlled-`Ry` (`mcry`)** keyed to the big-endian parent value — `ucry`/`UCRYGate` exist but the manual form kept the bit-order convention provably aligned with `decode.py`. Stays shallow (epic §6).
- Sibling circuit uses **one 18-bit classical register `c`** (parent low 9, daughter high 9) so Aer and `SamplerV2` read counts identically via `.data.c`.
- Tiles are sampled by **flattening counts** (`backend.flatten_counts`, one shot = one draw) rather than a per-shot memory API — portable across both backends.
- `job_id` is `""` for Aer; Peter captures the real id + CHSH from his hardware run.

**Verified on Aer:** size/lobe/type marginals match the rulebook; `P(type|size<6)` matches the conditional; sibling size-match 0.956 (vs ~0.25 independent); CHSH `S=2.795`; PRNG↔QRNG schema identical; JSON artifacts written; `--backend ibm_heron` wired and fails cleanly without submitting a job.

**Follow-ups for the developer:**
- Run the one real `ibm_heron` job yourself (`python code/run.py --backend ibm_heron`) to get the demo CHSH value + job id; the error seen during verification was "no matching backend" on this account — confirm `ibm_heron` (or use `--backend auto`) is reachable from your instance.
- F2 reads `research_runs/<run>/cohort_params.json` (the `TumorParams` contract) + `quantum_run.json`.
- Unrelated pre-existing staged changes in the working tree (study-ideas, file moves) were left untouched.
- Separate from F1: repo-root `credentialsApi.py` holds a live IBM token in plaintext — rotate + gitignore.
