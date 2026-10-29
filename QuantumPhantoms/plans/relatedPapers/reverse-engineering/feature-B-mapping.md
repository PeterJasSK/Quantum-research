# Feature B — Mapping: rulebook + CT context → circuit

**Epic:** [epic-reverse-engineering.md](epic-reverse-engineering.md) (Approved, 2026-10-28)
**Feature ID:** B
**Author:** Claude (Opus)
**Date:** 2026-10-29
**Status:** Complete (approved 2026-10-29; implemented 2026-10-29 on branch `re-B`)

> **Technical constraints.**
> - Stack: Python 3.13 (conda `base`), qiskit 2.3.1, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.47.0 (`FakeMarrakesh`), numpy 2.4.6, scipy 1.15.3, matplotlib 3.10.0, jsonschema 4.23.0, SimpleITK 2.5.6, pylidc. Same environment C used.
> - **Simulation only.** Every quantum number is labelled `simulated: ideal` or `simulated: Heron-class noise (FakeMarrakesh)`, and `hardware: null`.
> - Write scope: only `B_mapping/` and this file. Never edit `shared/`, other letters, the epic, the targets list, `about.html`, `index.html`, `site/`, `.gitignore`. Nothing is imported from `QuantumPhantoms/code/` or from another letter's `src/`.
> - All commands run with cwd = `reverse-engineering/` (`python -m B_mapping.…`).
> - Built in worktree `../qp-re-B` (branch `re-B`), wave 2.
> - **No automated tests.** Verification is manual plus the reproduction step.

---

## 1. Why (Step Goal)

**Before.**
- `B_mapping/` is the W skeleton: template README, three template dossiers (#1 BN compiler, #2 QeMCMC, #3 quantum blur), `status.json` with all three targets `listed`.
- The only "rulebook → circuit" artifacts are the hand-made W stubs (`stub-rulebook-2node`, a 2-qubit compiled circuit). Nothing turns a rulebook plus a site's CT context into a circuit, and nothing decodes a measured shot into a `TumorDraw`.
- D, E, G and H all consume `Rulebook` / `CompiledCircuit` / `QuantumJobRecord` / `TumorDraw` from stubs only.

**After.**
- A **general Bayesian-network → circuit compiler** (Low–Yoder–Chuang [B01], Borujeni [B09, B10]) that compiles any contract-valid `rulebook.json`: multi-state nodes on ⌈log₂n⌉ qubits, CPTs as (multi-)controlled Ry trees, context selecting the CPT at compile time.
- **Reproduction:** Borujeni's 4-node oil-stock network rebuilt from its CPTs, run on Aer ideal and Heron-class noise across transpiler levels, drift reported in the paper's metric (RMSPE of marginals) and in ours (TVD of the joint).
- A **cited lung rulebook** (type, size, margin; placement-class prior and context-conditioned rows) built from published statistics and LIDC aggregate counts only.
- **B-1** (context-conditioned certified draw): one site's context → compiled circuit → job record → decoded `TumorDraw`, all contract-valid. Claim level L0.
- **B-2** (joint site × phenotype): a site register in superposition with the phenotype registers controlled on it, so one shot draws site and phenotype jointly. Claim level L0 (classical equivalent = joint lookup table), stated honestly.
- **Drift** of every variant measured against the exact rulebook distribution and against the classical ancestral sampler (the baseline).
- **QeMCMC research arm (B-5):** Layden's spectral-gap scaling reproduced in ideal simulation, then a tumor-in-anatomy Ising energy on a 3-D voxel patch, with mixing measured against classical Metropolis (ideal + Heron-class noise).
- **Quantum blur (#3):** dissected, a minimal reproduction, and always shown next to its classical Gaussian baseline.
- Dossiers, README and `status.json` updated so the site shows B's real state.

---

## 2. Acceptance Criteria

- [x] **AC-1** (B.1): *Lung rulebook, contract-valid and cited.* ✅ *Evidence:* `B_mapping/src/rulebook.py:53` (build), `B_mapping/src/lidc_stats.py:31,39,74`; `data/rulebook_lung.json` validates; class prior in sidecar `data/class_prior.json` (contract has no params/extra → CCR-B1); 2567 LIDC nodules in `data/lidc_counts.json`.
  → `B_mapping/src/rulebook.py` builds `rulebook.json` (contract `rulebook` v1.0.0): nodes `tumor_type` (solid | part-solid | ground-glass), `size_bin` (4 bins, edges 3 / 6 / 10 / 20 / 30 mm), `margin` (smooth | lobulated | spiculated). Edges: `tumor_type → size_bin`, `tumor_type, size_bin → margin`. `tumor_type` and `margin` carry `context_keys: ["placement_class"]` and use `cpt_by_context` (keys `free`, `juxtavascular`, `juxtapleural`); `size_bin` uses `cpt`. Every node lists `sources` (paper code or citation + table/figure). The placement-class prior (used by B-2 site weights) is stored in the rulebook's `params`/`extra` if the contract allows, otherwise as a CCR (Q2).
  → LIDC aggregate counts come from `B_mapping/src/lidc_stats.py` (pylidc, radiologist ratings median per nodule) and are committed as `B_mapping/data/lidc_counts.json` (counts only, no voxels).
  → `rulebook_hash = hash_json(doc, exclude=['rulebook_hash','created_utc','produced_by'])`; `python -m shared.validate B_mapping/data/rulebook_lung.json` passes (rows sum to 1).

- [x] **AC-2** (B.2): *Exact classical reference and baseline sampler.* ✅ *Evidence:* `B_mapping/src/rulebook.py:120` (`joint_table`), `:140` (`ancestral_sample`); ancestral TVD 0.0048 at 1e5 shots.
  → `rulebook.py` provides `joint_table(rulebook, context) -> dict[tuple, float]` (exact enumeration over all node states, numpy) and `ancestral_sample(rulebook, context, shots, rng)`. pyAgrum is not installed; this enumeration is the reference (Q1). The ancestral sampler is the **classical baseline** for every B quantum number.

- [x] **AC-3** (B.3): *General BN → circuit compiler.* ✅ *Evidence:* `B_mapping/src/compiler.py:37` (Ry tree), `:62` (emit mcry/ancilla), `:90` (node_ops), `:146` (statevector_joint), `:170,180` (`--check`); max|Δp| ≤ 3.6e-14 for stub, Borujeni, lung rulebooks, every context, both modes; 5-state edge case passes.
  → `B_mapping/src/compiler.py`: `compile_rulebook(rulebook, context, *, multi_control="mcry"|"ancilla") -> Compiled` (a `QuantumCircuit` + logical qubit map + clbit order).
  - Node with n states → ⌈log₂n⌉ qubits. The categorical distribution is loaded as a binary tree of Ry rotations, θ = 2·atan(√(P₁/P₀)) at each split [B01, B09]. Unused codes get probability 0.
  - Children: one Ry tree per parent-state combination, controlled on the parent qubits with `ctrl_state` (`mcry` = qiskit `RYGate().control(k, ctrl_state=…)`), or Borujeni-style ancilla + Toffoli (`ancilla`, ancillas shared across nodes).
  - Context selects the `cpt_by_context` row at compile time (B-1: context costs +0 qubits).
  - Works for any contract-valid rulebook (any node count, any state count ≥ 2, any parent set in topological order).
  → Correctness check (`python -m B_mapping.src.compiler --check <rulebook>`): statevector probabilities equal `joint_table` to within 1e-9 for the W stub, the Borujeni network and the lung rulebook, every context, both control modes.

- [x] **AC-4** (B.4): *Reproduction, ideal: Borujeni 4-node network.* ✅ *Evidence:* `B_mapping/repro/borujeni.py:20,48,65`; simulated: ideal RMSPE 0.36 % (mcry) / 0.18 % (ancilla), marginals within ±0.01 of Netica.
  → `B_mapping/repro/borujeni.py` builds the oil-stock network (IR, OI, SM|IR, SP|OI,SM) from the CPTs in [B09] (P(IR=1)=0.25; P(OI=1)=0.4; P(SM=1|IR)=0.7/0.2; P(SP=1|OI,SM)=0.1/0.6/0.5/0.8) as a contract-valid rulebook, compiles it, and runs 10 runs × 8192 shots on Aer ideal (paper protocol).
  → **Published number:** simulator RMSPE 0.1 % over the 4 marginals; Netica marginals P(IR=0)=0.750, P(OI=0)=0.600, P(SM=0)=0.425, P(SP=0)=0.499.
  → **Match criterion:** every marginal within ±0.01 of Netica and RMSPE ≤ 0.5 %. Also report joint TVD to `joint_table`.

- [x] **AC-5** (B.5): *Reproduction, Heron-class noise: drift vs transpiler level.* ✅ *Evidence:* `B_mapping/repro/borujeni.py:65` (`--mode heron`); table in dossier #1; `B_mapping/figures/borujeni_rmspe_vs_level.png`.
  → Same script, `--mode heron`: optimization levels 0–3 × {`mcry`, `ancilla`}, 10 × 8192 shots each, via `transpile_heron(…, optimization_level=k)` and `make_simulator("heron", seed=…)`.
  → Reports RMSPE, joint TVD, depth and CZ count per cell, set against the paper's hardware range (Level 0: 4.9 % Yorktown … 36.3 % Burlington; Level 3: 9.1–24 %). This is a comparison, not a pass criterion: a 2025 Heron noise model on 2020 devices' protocol.
  → Figure `B_mapping/figures/borujeni_rmspe_vs_level.png`.

- [x] **AC-6** (B.6): *B-1 end-to-end: context-conditioned draw, contract-valid.* ✅ *Evidence:* `B_mapping/src/map.py:62` (`run_variant`), `:49` (`physical_map`), `:66` (certificate fail → exit 2), `:96` (`B.sim`), `:144` (validate outputs); all four contracts pass `shared.validate`; fail certificate → no draw, exit 2; unknown site → clear error, no run dir.
  → `python -m B_mapping.src.map --variant b1 --mode ideal|heron --site S001 [--sites <sites.json>] [--certificate <certificate.json>] [--shots 4096]`. Defaults: `shared/stubs/` sites and certificate.
  - Reads the site's `context.placement_class`, compiles the lung rulebook for it, runs it, writes into the run directory: `rulebook.json`, `compiled_circuit.json` + `.qasm` (transpiled for FakeMarrakesh), `quantum_job_record.json`, `tumor_draw.json`, `drift.json`.
  - Every output has the envelope (`produced_by{letter:"B", tool, run_id, code_hash}`, `upstream[]` with sha256 of sites, certificate, rulebook), and the quantum outputs carry `sim_label(mode)` and `hardware: null`.
  - `start_run(LETTER_DIR, "b1-<mode>", sim_mode=mode, tool="B_mapping.src.map")` → `add_input` / `add_output` / `add_job` / `finish`; outputs pass `shared.validate.validate_file`.
  - Certificate `status: fail` → no draw, logged, exit non-zero (epic decision 6: no retry, no fallback).

- [x] **AC-7** (B.7): *B-2 joint site × phenotype draw.* ✅ *Evidence:* `B_mapping/src/joint.py:9,24,31,56,65`; statevector = classical joint < 1e-9 (map asserts). Deviation: stub has only 3 sites, so K=8 (9 logical qubits + 7 ancillas) was verified on a synthetic 8-site file (simulated: ideal); one controlled tree per site code instead of per class; B-2 defaults to `ancilla` control mode (8-control mcry transpiles to ~10^5 CZ). README states L0.
  → `--variant b2 [--k-sites 8]`. `B_mapping/src/joint.py` picks K sites from `sites.json` (seeded, `rng(seed,"B.site_pick")`, every class represented when available), puts them on a ⌈log₂K⌉-qubit site register with amplitudes √w, w_site = P(class) / n_class-in-subset (class prior from the rulebook), then controls `tumor_type` and `margin` on the site register's class (one controlled tree per class, `ctrl_state` over the codes of that class's sites).
  → Default K=8: 3 site + 2 type + 2 size + 2 margin = 9 qubits (inside the 9–14 q budget). Statevector check vs the classical joint (site × phenotype) to 1e-9, as in AC-3.
  → Same outputs as AC-6; `compiled_circuit.context` = `{"variant":"b2","sites":"<comma-joined site ids>"}`; decoded `site_id` comes from the shot.
  → README and dossier state claim level **L0**: the joint is a lookup table classically; no interference claim (single-qubit phase-dial lesson, epic §3).

- [x] **AC-8** (B.8): *Shot decoding and seed chain.* ✅ *Evidence:* `B_mapping/src/decode.py:8,17,28,33,37`; `map.py:96`; two ideal runs gave identical draws; Heron runs report invalid fraction (33–59 %) in `drift.json`.
  → `B_mapping/src/decode.py`: bitstring (clbit order from the compiler) → states → `TumorDraw`.
  - Draw selection: `shot_index = derive_seed(cert_seed, "B.shot_select") % shots` over the job's memory order (Q6).
  - `size_mm` = uniform inside the drawn size bin via `rng(cert_seed, "B.size")`.
  - `shape_seed_hex` = `sha256(cert_seed ‖ "B.shape" ‖ draw_id)` hex (classical, L0 provenance).
  - `sim_seed` in the job record = `derive_seed(cert_seed, "B.sim")`. Re-running with the same certificate reproduces the same draw bit-for-bit in ideal mode.
  - Codes with probability 0 (e.g. the unused 4th code of a 3-state node) that appear under noise are counted as **invalid shots** in `drift.json`, and the selected shot skips forward to the next valid one.

- [x] **AC-9** (B.9): *Drift report.* ✅ *Evidence:* `B_mapping/src/drift.py:7,11,32`; `B_mapping/src/drift_report.py`; `B_mapping/figures/drift_b1_b2.png`. Deviation: B-2 Heron case ran 256 shots (11.5k CZ circuit, noisy trajectories too slow at 4096).
  → `B_mapping/src/drift.py`: `tvd(p, q)`, `rmspe(marginals_measured, marginals_exact)`. `drift.json` (run directory, not a contract) holds per variant and mode: phenotype TVD vs `joint_table`, per-node marginal TVD, invalid-shot fraction, the classical ancestral sampler's TVD at the same shot count (baseline), and gate counts / depth / CZ count.
  → `python -m B_mapping.src.drift_report` runs B-1 (all three classes) and B-2, ideal and heron, and writes `B_mapping/figures/drift_b1_b2.png`.

- [x] **AC-10** (B.10): *Reproduction: Layden QeMCMC spectral-gap scaling (ideal).* ✅ *Evidence:* `B_mapping/src/qemcmc.py:24-84`; `B_mapping/repro/layden.py:25`; k_quantum 0.250, k_local 1.017, k_uniform 0.939 (simulated: ideal), all within tolerance; `B_mapping/figures/layden_gap_scaling.png`.
  → `B_mapping/src/qemcmc.py`: Ising energy E = −Σ J s s − Σ h s; quantum proposal U = exp(−iHt), H = (1−γ)αH_prob + γH_mix, α = √n / √(ΣJ² + Σh²), γ ~ U[0.25, 0.6], t ~ U[2, 20] [B11]. Proposal matrix Q = mean over M (γ, t) draws of |⟨s'|U|s⟩|² (exact, scipy `expm`). Metropolis–Hastings transition matrix P; spectral gap δ = 1 − |λ₂|. Baselines: local (single spin flip) and uniform proposals.
  → `B_mapping/repro/layden.py`: random SK instances, n = 3…8, T = 1; fit ⟨δ⟩ ∝ 2^(−kn).
  → **Published number:** k_quantum = 0.264(4), k_local = 0.94(4), k_uniform = 0.948(7). **Match criterion:** k_quantum within ±0.08 of 0.264 and k_local, k_uniform within ±0.15 of theirs (fewer instances and smaller n than the paper). Figure `B_mapping/figures/layden_gap_scaling.png`.

- [x] **AC-11** (B.11): *Adaptation: tumor-in-anatomy energy, quantum vs classical mixing.* ✅ *Evidence:* `B_mapping/src/tumor_energy.py:24`, `B_mapping/src/qemcmc.py:98,128,147`; ideal 8 and 6 spins, Heron 6 spins (the plan's Q8 fallback: the 8-spin Heron run exceeded 1 h and was stopped); noisy-Q asymmetry 0.135; `B_mapping/figures/qemcmc_tumor_gap.png`.
  → `B_mapping/src/tumor_energy.py`: a 2×2×2 voxel patch (8 spins, s = tumor/no tumor) at the site, at a coarse spacing set from the drawn size. h_i from the masks of `anatomy_masks` (stub by default): vessel proximity attracts (h > 0), pleura proximity repels (h < 0), plus a size term; J > 0 nearest-neighbour compactness. Every coefficient is a named parameter recorded in the run.
  → `python -m B_mapping.src.qemcmc --tumor --mode ideal|heron`:
  - ideal: exact δ for quantum, local and uniform proposals;
  - heron: the proposal matrix is estimated by transpiling the second-order Trotter circuit of U for a fixed grid of (γ, t) values (Q8) and every basis input state, running on Aer Heron-class noise, then building P and δ from the noisy Q. MH acceptance keeps the target distribution correct only up to the asymmetry of the noisy Q; that asymmetry is reported.
  → Result table (δ quantum / local / uniform, both modes) in the dossier. Claim: "correct sampler with quantum proposals; any speedup is ideal-simulation only". No claim level (Q8).

- [x] **AC-12** (B.12): *Quantum blur (#3), dissected with baseline.* ✅ *Evidence:* `B_mapping/src/blur.py:22,31,46`; `B_mapping/repro/wootton_blur.py:25`; verdict rejected (r 0.97–0.99 vs Gaussian at small θ); `B_mapping/figures/quantum_blur_vs_gaussian.png`.
  → `B_mapping/src/blur.py`: re-implementation of Wootton's quantum blur from [B04, B05]: an image or height map loaded as amplitudes (√ normalised) on n qubits with the paper's coordinate-to-bitstring mapping, Rx(θ) on every qubit, probabilities read back (statevector, ideal) as the blurred map. Baseline: `scipy.ndimage.gaussian_filter`.
  → `B_mapping/repro/wootton_blur.py`: a 2-D height map as in the paper's figure (paper figure reproduced qualitatively; there is no published number). Adaptation: one 8×8×8 3-D shape seed (9 qubits, W stub `SeedShape` or a sphere) blurred at three θ, with the Gaussian baseline at matched σ and the voxel-wise correlation between the two. Figure `B_mapping/figures/quantum_blur_vs_gaussian.png`.
  → Verdict recorded in the dossier from the comparison (integrate as shape-variation option, or reject because the classical blur is equivalent). Q9.

- [x] **AC-13** (B.13): *Documentation and status.* ✅ *Evidence:* `B_mapping/README.md` (run commands, results table, CCR-B1/B2), `B_mapping/dossiers/01..03`, `B_mapping/status.json` (#1 adapted L0, #2 adapted, #3 rejected); `shared.validate --status` OK; `shared.site.build` rendered B's pages (build output reverted, not committed).
  → `B_mapping/README.md`: every fixed section filled. How to run lists every command above. "Reproduced result vs paper" is a table with a Sim mode column carrying the literal labels. Claim levels: B-1 L0, B-2 L0, QeMCMC no claim, blur none. Inputs now also list `certificate`. "Contract change requests" uses the `**CCR-B<n>: \`contract\`, topic.**` format with *Need / Request / Local workaround*.
  → Dossiers `01-bn-circuit-compiler.md`, `02-quantum-enhanced-mcmc.md`, `03-quantum-blur.md`: all sections filled (Unicode or fenced `text` equations, no MathJax).
  → `status.json` transitions, each with `reproduced{quantity, paper_value, our_value, agreement, unit, sim_mode, figure}` where reproduced: #1 → `adapted` (claim L0), #2 → `adapted` if AC-11 ran, else `reproduced` (claim `null`), #3 → `reproduced` or `rejected` with reason.
  → `python -m shared.validate --status` passes; `python -m shared.site.build` renders B's pages locally (not committed).

- [x] **AC-14** (B.14): *Isolation and honesty.* ✅ *Evidence:* Only `B_mapping/` and this file changed (site build output reverted); isolation grep empty; every quantum number in README/dossiers carries a sim label.
  → `git diff --stat main...re-B` touches only `B_mapping/` and `feature-B-mapping.md`. No `import` of `QuantumPhantoms/code`, `A_placement`, `C_certificate`, `D_…`, `E_…`, `F_render` etc. (B reads their *files* only through contracts). Every quantum number in the README, dossiers and figures carries a sim label. No "quantum because more realistic" wording.

---

## 3. Out of Scope (Postponed)

- **CHSH pair in the same job as the B-2 draw** (analysis B-2 design) → certificate generation stays in C; joining draw and test rounds in one job belongs to D-2 (one-job dynamic circuit) / INT. B's `test_round_mask` is `null`.
- **Belief-propagation simulability number for B circuits** → D owns the adversary (#9). B records gate counts and "BP number pending D #9"; INT runs D's adversary over B's circuits.
- **L1 entanglement witness on the B-2 state** → `WitnessRecord` is introduced in D. B claims L0 only.
- **B-3 amplitude-amplified evidence inference** → cited in dossier #1 only (0–1 Grover rounds on Heron, analysis §2).
- **B-4 FRQI/NEQR CT patch** → explicitly not reverse-engineered (epic §1).
- **B-6 heavy-hex tissue graph** → shared with D-3; D owns it.
- **Coarse-grained QeMCMC (Ferguson–Wallden [B12]) beyond dissection** → noted in dossier #2; no build.
- **Real A output, real C seed** → B runs on `shared/stubs/` (or a path given on the CLI). Swapping in A's real `sites.json` (A not merged yet) and C's real certificate is INT.
- **Re-checking A's placement class at the drawn size** (A plan Q7/Q8) → INT / F.
- **Using the draw to grow or render** → D, E, F.
- **Hardware runs** → future work everywhere.

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Classical BN reference | Own exact enumeration + ancestral sampler in numpy (pyAgrum, pgmpy not installed) |
| Multi-state encoding | ⌈log₂n⌉ qubits, binary Ry tree, little-endian code = state index, unused codes probability 0 |
| Angle formula | θ = 2·atan(√(P₁/P₀)) per split [B01, B09] |
| Multi-control | default `mcry` (qiskit `RYGate().control(k, ctrl_state)`); `ancilla` (Borujeni CCX + shared ancillas) for the repro comparison |
| Context (B-1) | compile-time CPT row selection from `cpt_by_context`, key = `'|'`-joined `context_keys` values; only categorical context keys (`placement_class`) in v1 |
| Joint draw (B-2) | site register ⌈log₂K⌉ q, default K=8, amplitudes √(P(class)/n_class); phenotype controlled on class code sets |
| Transpile / simulate | `shared.simbackend.transpile_heron` + `make_simulator(mode, seed=…)` with `memory=True` (as C does); `run_counts` where memory is not needed |
| Seeds | all from the certificate's `extracted_seed_hex` via `derive_seed` / `rng` with labels `B.sim`, `B.shot_select`, `B.size`, `B.shape`, `B.site_pick`, `B.qemcmc` |
| Rulebook statistics | LIDC aggregate ratings (pylidc) + published placement prior; context-stratified rows from literature, marked *(verify)* where not in `../papers/` (Q2, Q3) |
| Drift metric | joint TVD (ours) + RMSPE of marginals (Borujeni's) |
| QeMCMC | exact `expm` for ideal; Trotterized (2nd order) circuits on a fixed (γ, t) grid for Heron-class noise |
| Figures | matplotlib PNG in `B_mapping/figures/`, committed |
| CLI style | argparse, `python -m B_mapping.src.<module>`, `--mode` choices `ideal`/`heron` required (mirrors `C_certificate.src.certify`) |

**Conventions & Notes:**
*   Adopt the epic's §3 decisions verbatim: simulation only, FakeMarrakesh, 3-D imaging artifacts (the energy patch and blur seed are 3-D; only the blur paper reproduction is 2-D because the paper is), files-only contracts, frozen `shared/`.
*   Envelope built by a local `_envelope(run)` helper, as in `C_certificate/src/certify.py`.
*   `compiled_circuit.qubit_map` holds **physical** qubit indices of the transpiled circuit (they match `$n` in the QASM). Clbit `i` measures logical qubit `i`, so decoding uses the logical order from the compiler. The logical → physical layout goes in `extra` if the contract allows it, else a CCR (Q12).
*   Classical baseline for every quantum number: the ancestral sampler (B-1/B-2), local + uniform proposals (QeMCMC), Gaussian blur (#3).
*   Runs land in `B_mapping/runs/<timestamp>-<tag>/` (gitignored). The canonical lung rulebook is also committed at `B_mapping/data/rulebook_lung.json` so consumers can reference it.
*   **Note for the epic:** the epic did not say where the class prior lives once A emits equal counts per class; this plan puts it in B's rulebook (A's plan already says "the class prior belongs to B's rulebook").

---

## 5. Data Model (Additions/Modifications)

No new contracts; B is the first real producer of four frozen v1.0.0 contracts.

```text
[Existing contract — first real producer]
Rulebook (rulebook.json)
  rulebook_id     "lung-v1"
  nodes[]         tumor_type{states[3], parents[], context_keys["placement_class"], cpt_by_context, sources}
                  size_bin{states["3-6","6-10","10-20","20-30"], parents["tumor_type"], cpt, sources}
                  margin{states[3], parents["tumor_type","size_bin"], context_keys["placement_class"], cpt_by_context, sources}
  class prior     P(free, juxtavascular, juxtapleural) — in params/extra if allowed, else CCR-B1
  rulebook_hash   hash_json(exclude rulebook_hash, created_utc, produced_by)

[Existing contract — first real producer]
CompiledCircuit (compiled_circuit.json + .qasm)
  context         B-1: {"placement_class": "<class>"} · B-2: {"variant":"b2","sites":"S001,S004,…"}
  qubit_map       node name → physical qubits; B-2 adds "site"; ancilla mode adds "ancilla"
  qasm3           transpiled for FakeMarrakesh

[Existing contract — first real producer]
QuantumJobRecord (quantum_job_record.json)
  sim_mode / sim_label / hardware:null, sim_seed = derive_seed(cert_seed,"B.sim"), test_round_mask null

[Existing contract — first real producer]
TumorDraw (tumor_draw.json)
  site_id, size_mm, type, margin, shape_seed_hex, rulebook_hash, job_record_ref, shot_index

[Local, not a contract]
drift.json (run dir)        per variant × mode: TVDs, marginals, invalid-shot fraction, baseline TVD, gate counts
data/lidc_counts.json       aggregate LIDC rating counts (type × size_bin × margin), no voxels
```

---

## 6. File Plan (Concrete Changes)

All paths relative to `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`. Analogue: `C_certificate/`.

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `B_mapping/src/rulebook.py` | build/validate/hash the lung rulebook; `joint_table`, `ancestral_sample`; CLI `--write` → `data/rulebook_lung.json` |
| New | `B_mapping/src/lidc_stats.py` | pylidc query (with the `np.int` / `SafeConfigParser` aliases pylidc needs), ratings → enum mapping (Q3), writes `data/lidc_counts.json` |
| New | `B_mapping/src/compiler.py` | BN → `QuantumCircuit` (Ry trees, `mcry` / `ancilla`), context row selection, qubit map; `--check` statevector vs `joint_table` |
| New | `B_mapping/src/joint.py` | B-2 site pick, site-register amplitudes, class-controlled phenotype trees |
| New | `B_mapping/src/decode.py` | bitstring → states → `TumorDraw`, seeded shot selection, invalid-shot handling |
| New | `B_mapping/src/drift.py` | `tvd`, `rmspe`, `drift.json` writer |
| New | `B_mapping/src/drift_report.py` | runs B-1 × 3 classes + B-2, both modes; `figures/drift_b1_b2.png` |
| New | `B_mapping/src/map.py` | CLI orchestrator for B-1/B-2: run record, envelopes, contract outputs, validation |
| New | `B_mapping/src/qemcmc.py` | Layden proposal (exact + Trotter circuit), MH matrix, spectral gap, local/uniform baselines; `--tumor --mode` |
| New | `B_mapping/src/tumor_energy.py` | 2×2×2 patch Ising (h from anatomy masks, J compactness) |
| New | `B_mapping/src/blur.py` | quantum blur (statevector) + Gaussian baseline, 2-D and 3-D |
| New | `B_mapping/repro/borujeni.py` | 4-node oil-stock repro, ideal + heron × levels 0–3 × control modes; `figures/borujeni_rmspe_vs_level.png` |
| New | `B_mapping/repro/layden.py` | SK n=3…8 gap scaling fit; `figures/layden_gap_scaling.png` |
| New | `B_mapping/repro/wootton_blur.py` | 2-D paper-style reproduction + 3-D seed adaptation; `figures/quantum_blur_vs_gaussian.png` |
| New | `B_mapping/data/lidc_counts.json` | aggregate counts (committed) |
| New | `B_mapping/data/rulebook_lung.json` | canonical lung rulebook (committed, contract-valid) |
| New | `B_mapping/data/rulebook_borujeni.json` | the oil-stock network as a contract-valid rulebook (committed) |
| New | `B_mapping/figures/borujeni_rmspe_vs_level.png`, `drift_b1_b2.png`, `layden_gap_scaling.png`, `qemcmc_tumor_gap.png`, `quantum_blur_vs_gaussian.png` | committed figures |
| Modify | `B_mapping/README.md` | fill every section, CCR list, results table with sim labels |
| Modify | `B_mapping/dossiers/01-bn-circuit-compiler.md` | full dossier #1 (incl. B-3 note) |
| Modify | `B_mapping/dossiers/02-quantum-enhanced-mcmc.md` | full dossier #2 (incl. B12 coarse-graining note) |
| Modify | `B_mapping/dossiers/03-quantum-blur.md` | full dossier #3 with verdict |
| Modify | `B_mapping/status.json` | state transitions + `reproduced{…}` blocks |
| Modify | `feature-B-mapping.md` | tick ACs, §9 notes |

Untouched: `shared/`, every other letter folder, the epic, `reverse-engineering-targets.md`, `about.html`, `index.html`, `site/`, `.gitignore`, `QuantumPhantoms/code/`.

---

## 7. Manual Verification (No Tests)

Run from `reverse-engineering/` in conda `base`.

- [ ] **Verify AC-1:** `python -m B_mapping.src.lidc_stats` → `data/lidc_counts.json` with non-zero counts per type; `python -m B_mapping.src.rulebook --write` then `python -m shared.validate B_mapping/data/rulebook_lung.json` → OK. Open the file: every node has `sources`, every `cpt_by_context` has all three classes.
- [ ] **Verify AC-2:** `python -m B_mapping.src.rulebook --joint --context free` prints the joint table; it sums to 1; ancestral sampler at 10⁵ shots is within TVD ≈ 0.01 of it.
- [ ] **Verify AC-3:** `python -m B_mapping.src.compiler --check shared/stubs/rulebook.json`, then the same for `B_mapping/data/rulebook_borujeni.json` and `B_mapping/data/rulebook_lung.json` → max |Δp| ≤ 1e-9 for every context, both `--multi-control mcry|ancilla`.
- [ ] **Verify AC-4:** `python -m B_mapping.repro.borujeni --mode ideal` → marginals ≈ 0.750 / 0.600 / 0.425 / 0.499 (±0.01), RMSPE ≤ 0.5 %.
- [ ] **Verify AC-5:** `python -m B_mapping.repro.borujeni --mode heron` → table of RMSPE / TVD / depth / CZ for levels 0–3 × both control modes; figure exists; printed comparison to the paper's 4.9–36.3 % range.
- [ ] **Verify AC-6:** `python -m B_mapping.src.map --variant b1 --mode ideal --site S001` and `--mode heron` → new run dir with the five files; `python -m shared.validate B_mapping/runs/<dir>/*.json` → OK; job record has `sim_label` + `hardware: null`. Then pass a certificate copy edited to `status: fail` → no draw, logged, non-zero exit.
- [ ] **Verify AC-7:** `python -m B_mapping.src.map --variant b2 --mode ideal` → 9-qubit circuit; `--check` style statevector match printed; decoded `site_id` is one of the K picked sites; README states L0.
- [ ] **Verify AC-8:** run B-1 ideal twice with the same certificate → identical `tumor_draw.json` (same `shot_index`, `size_mm`, `shape_seed_hex`). Heron run reports an invalid-shot fraction in `drift.json`.
- [ ] **Verify AC-9:** `python -m B_mapping.src.drift_report` → `figures/drift_b1_b2.png`; ideal TVD ≈ baseline TVD (shot noise), Heron TVD larger, both printed.
- [ ] **Verify AC-10:** `python -m B_mapping.repro.layden` → fitted k_quantum, k_local, k_uniform printed against 0.264 / 0.94 / 0.948; figure exists.
- [ ] **Verify AC-11:** `python -m B_mapping.src.qemcmc --tumor --mode ideal` and `--mode heron` → δ for quantum / local / uniform in both modes and the noisy-Q asymmetry number; parameters logged in the run record.
- [ ] **Verify AC-12:** `python -m B_mapping.repro.wootton_blur` → figure with quantum blur next to Gaussian (2-D and 3-D mid-slice export), correlation numbers printed; dossier #3 verdict matches them.
- [ ] **Verify AC-13:** `python -m shared.validate --status` → OK; `python -m shared.site.build` → B's letter page shows the new states, the results table and the figures (do not commit `index.html` / `site/`).
- [ ] **Verify AC-14:** `git diff --stat main...re-B` lists only `B_mapping/**` and `feature-B-mapping.md`; `grep -rnE "QuantumPhantoms\.code|from (A_|C_|D_|E_|F_|G_|H_)" B_mapping/src B_mapping/repro` → nothing; `grep -rn "simulated:" B_mapping/README.md B_mapping/dossiers` shows a label beside every quantum number.
- [ ] Edge case: a rulebook with a 5-state node (3 qubits, 3 unused codes) compiles and passes `--check`.
- [ ] Edge case: `--site` not in `sites.json` → clear error, no run directory left half-written.

---

## 8. Open Questions

- [x] **Q1: pyAgrum (the targets list's reference implementation) is not installed. Install it?** *Resolved (accepted default):* no. Own numpy exact enumeration is the reference and the baseline; the dossier notes that pyAgrum's qBN was read only.
- [x] **Q2: Where do the lung rulebook numbers come from, and where does the class prior live?** *Resolved (accepted default):* `tumor_type`, `size_bin`, `margin` from LIDC aggregate radiologist ratings (pylidc, counts only). Placement prior ≈ 0.45 juxtavascular / 0.33 free / 0.22 juxtapleural from Ambrosini / Kostis [F01] (as in A's plan). Context-stratified rows (e.g. juxtapleural → more often smooth / solid, perifissural literature: Ahn 2010, de Hoop 2012) marked *(verify)* where the paper is not in `../papers/`. Class prior goes in the rulebook's `params`/`extra` if the schema has it; otherwise kept in `data/rulebook_lung.json` sidecar + CCR-B1.
- [x] **Q3: LIDC rating → enum mapping.** *Resolved (accepted default):* median texture 1–2 → ground-glass, 3 → part-solid, 4–5 → solid; median spiculation ≥ 3 → spiculated, else median lobulation ≥ 3 → lobulated, else smooth; size = annotation diameter, nodules < 3 mm or > 30 mm dropped.
- [x] **Q4: B-2 site register size and weights.** *Resolved (accepted default):* K = 8 (3 qubits, 9 qubits total), seeded pick with every class represented; w_site = P(class)/n_class-in-subset. `--k-sites` allows 4 or 16.
- [x] **Q5: Multi-control synthesis.** *Resolved (accepted default):* `mcry` default for the pipeline (fewer hand-written gates, transpiler optimises); `ancilla` only to mirror Borujeni in the repro and compare depth / CZ / drift.
- [x] **Q6: One draw or many per run?** *Resolved (accepted default):* one `tumor_draw.json` per run (the contract is one draw), chosen by the seeded shot index; the full shot distribution stays in the job record and `drift.json` for cohort drift.
- [x] **Q7: Certificate input.** *Resolved (accepted default):* B consumes `shared/stubs/` certificate by default, or C's real `certificate.json` via `--certificate` (C is merged). All B seeds derive from its `extracted_seed_hex`; `status: fail` → no draw.
- [x] **Q8: QeMCMC sizes and claim.** *Resolved (accepted default):* Layden repro n = 3…8, 100 SK instances per n, M = 64 (γ, t) draws. Tumor patch 2×2×2 = 8 spins. Heron arm: a fixed 4-point (γ, t) grid × 256 input states = 1024 noisy circuits, 1024 shots each (drop to n = 6, 2×3×1 patch, if runtime > 1 h). `claim_level: null` with the note "speedup ideal-sim only".
- [x] **Q9: Quantum blur scope (★ = read only in the epic table, but row B says "only with its baseline").** *Resolved (accepted default):* dissect + the small statevector reproduction + Gaussian baseline (cheap, ~1 module). Final state `reproduced` or `rejected` from the comparison.
- [x] **Q10: Where to build.** *Resolved (accepted default):* commit this plan to `main` once approved, then `git worktree add ../qp-re-B -b re-B` and run `/implement-feature` there (avoids the stale untracked plan copy that hit F).
- [x] **Q11: BP simulability number (honesty gate) for B circuits.** *Resolved (accepted default):* deferred to INT with D's adversary (#9); B's README says "BP number pending D #9" and records the gate counts needed.
- [x] **Q12: `qubit_map` semantics and layout.** *Resolved (accepted default):* physical qubit indices (match the QASM); logical order = clbit order; logical → physical layout in `extra` if the schema allows, else CCR-B2.

---

## 9. Post-Implementation Notes

Built in worktree `../qp-re-B` (branch `re-B`). All numbers labelled `simulated: ideal` or `simulated: Heron-class noise (FakeMarrakesh)`; no hardware.

- **Deviations (all noted in the ACs):** the rulebook and compiled_circuit contracts have no `params`/`extra`, so the class prior is a sidecar (CCR-B1) and layout/ancilla info is carried in `qubit_map` (CCR-B2). The stub has 3 sites, so the K=8 B-2 circuit was verified on a synthetic 8-site file. B-2 uses one controlled tree per site code and defaults to Toffoli-chain controls. The QeMCMC Heron arm ran on a 2×3×1 patch (plan fallback). The B-2 Heron drift case used 256 shots.
- **Results worth knowing:** Borujeni reproduced (RMSPE 0.36 % vs 0.1 % paper; within the plan's match criterion). Layden k_quantum 0.250 vs 0.264. The lung rulebook compiles to depth ~5900 / 2000 CZ (B-1) and ~32 000 / 11 500 CZ (B-2, 3 sites), so Heron-class noise dominates (TVD 0.57–0.74, 33–59 % invalid shots) while the ideal circuits match the classical sampler to shot noise. The noisy QeMCMC proposal is asymmetric (0.135). The quantum blur is equivalent to a Gaussian → rejected.
- **Follow-ups:** the placement-class prior and context tilts are marked *(verify)*; A's real masks are needed for a non-flat tumor energy; the BP-simulability number is pending D #9; reduce circuit depth (class register) before any hardware discussion.
- **Housekeeping:** LIDC median-texture mapping gives 84 % solid nodules (2162 of 2567).
