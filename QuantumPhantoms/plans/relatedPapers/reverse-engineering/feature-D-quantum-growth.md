# Feature D — Quantum growth: one-job certified lineage, quantum causal-state memory advantage, heavy-hex Goldilocks QCA seed shape, belief-propagation adversary

**Epic:** [`epic-reverse-engineering.md`](./epic-reverse-engineering.md) (Approved, 2026-10-28). D is a Wave-2 letter (parallel with B, G, H). It runs on the frozen W stubs; C and E are already merged to `main`, so their real outputs can be used as an optional cross-check, but the default inputs are the stubs.
**Feature ID:** D
**Author:** Claude (Opus)
**Date:** 2026-10-29
**Status:** Complete (implemented 2026-10-29 on branch `re-D`; AC-13 and AC-17 partial, see §9)

> **Technical constraints / core directive.** Python 3 (conda base, `/home/peter/anaconda3/bin/python`) with what is installed: qiskit 2.3.1, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.47.0, numpy, scipy 1.15, networkx 3.4, matplotlib 3.10, jsonschema. **No new installs proposed** (quimb / cotengra / cvxpy are not installed; see Q5). **Simulation only**: every circuit runs on `AerSimulator`, ideal and with the `FakeMarrakesh` Heron r2 noise model, through `shared.simbackend` (both modes transpiled to the FakeMarrakesh heavy-hex CZ target). Aer runs noisy dynamic circuits (mid-circuit measure + `if_test` + reset) on the FakeMarrakesh target: checked 2026-10-29 with a 2-qubit feed-forward circuit. All files live under `QuantumPhantoms/plans/relatedPapers/reverse-engineering/` (written `RE/` below). Every command runs with `RE/` as the working directory (`python -m D_quantum_growth.…`). Implement in the worktree `../qp-re-D` on branch `re-D` (epic §3 "Parallel execution"). Write **only** inside `RE/D_quantum_growth/` and this plan; never edit `shared/`, the epic, `about.html`, `index.html`, `site/`, `.gitignore` or another letter. The seed shape handed to E is 3-D; 2-D pictures are figure exports only. Every PRNG and every hidden choice (test-round mask, snapshot shot) comes from the certificate seed via `shared.seedhash.derive_seed` / `rng`. Nothing is imported from the MVP (`QuantumPhantoms/code/`) or from the QALife / QDEP code elsewhere in the repo: ideas are re-derived from the papers. **Every quantum number is labelled "simulated: ideal" or "simulated: Heron-class noise (FakeMarrakesh)". No automated tests; verification is manual plus the paper reproductions.**

---

## 1. Why (Step Goal)

**Before.** W left `D_quantum_growth/` as a skeleton:
- README template;
- dossiers #6–#10 as templates (#10 has its "rejected: out of scope" line, the other sections still say "Not yet dissected");
- `status.json` with #6–#9 `listed` and #10 `rejected (out of scope)`;
- empty `src/`, `repro/`, `figures/`.

Downstream letters consume only hand-made stubs: E grows from `shared/stubs/seed_shape/` (a 7×7×7 occupancy blob), and G/H read stub `quantum_lineage`, `witness_record`, `memory_advantage_record` and `simulability_report` files. The epic has no non-classical growth stage, no measured witness, no memory-advantage number, and its "no L2 claim" is still a disclaimer, not a measurement.

**After.** D is the epic's quantum claim (L1 / L1′), built honestly and checked against its classical adversary.

- **#8 Dynamic-circuit feed-forward (D-2): dissected, reproduced, adapted.**
  - Reproduce: the Bäumer [HW05] constant-depth long-range Bell pair by measurement + feed-forward, against the unitary SWAP chain, as fidelity vs. distance (ideal + Heron-class noise).
  - Adapt: a **one-job quantum lineage** of 8 generations on a ≤ 8-qubit heavy-hex register. Each generation runs: divide (entangle parent into a daughter pair) → mid-circuit measure → feed-forward of the next parent (`if_test`) → reset. Hidden CHSH test rounds sit at secret generations, a necrotic-stop threshold runs as on-chip feed-forward, and an optional dynamical-decoupling (DD) lever pads the idle windows.
  - Outputs `quantum_lineage`, a per-generation division-pair witness (`witness_record`, ⟨XX⟩+⟨ZZ⟩ > 1) and a `quantum_job_record`.
- **#6 Quantum causal states (D-5, the headline): dissected, reproduced, adapted.**
  - Reproduce:
    - Gu's perturbed-coin C_q(p) < C_μ [D06], analytic;
    - Wu's result [D16] that a period-modulated-decay (PMD) renewal process has a statistically exact quantum model with D_q ≤ 1 qubit for any period N, while the classical D_μ = log₂ N grows.
  - Adapt: a **cell-cycle division-timer** renewal process, simulated by a 1-qubit-memory quantum model run as a dynamic circuit (unitary step → measure output → reset output → repeat). Measured:
    - output statistics vs. the exact process (KL per symbol);
    - memory-state tomography giving C_q(measured);
    - the best 1-bit classical model as the baseline ("higher precision at fixed memory").
  - Outputs `memory_advantage_record` (L1′).
- **#7 Goldilocks QCA (D-3): dissected, reproduced, adapted.**
  - Reproduce: the Jones [D14] 1-D rule T6 (single central flip, Hadamard activation): population dynamics and mutual-information network measures.
  - Adapt: a **heavy-hex-native Goldilocks rule on a 21-qubit FakeMarrakesh patch** (two adjacent hexagons), updated sublattice by sublattice (heavy-hex is bipartite). It is read out:
    - in Z per Floquet step (population);
    - in the 9 bipartite basis settings (sublattice A basis × sublattice B basis ∈ {X, Y, Z}²), which give full 2-qubit tomography of every nearest-neighbour pair, hence a negativity witness and an MI network.
  - One Z snapshot is lifted to a **3-D `seed_shape`** for E.
- **#9 Belief-propagation adversary: dissected, reproduced, used.**
  - Reproduce: a NumPy re-implementation of Tindall's [HW04] belief-propagation-gauged tensor-network simulator, checked on the 127-qubit Eagle kicked-Ising circuit.
  - Use: every D circuit (lineage blocks, q-machine, QCA, all bond dimensions) is run through it, which turns "no L2 claim" into a measured `simulability_report`.
- **#10** stays `rejected (out of scope)`; only its post-selection note is written.
- README, dossiers, figures and `status.json` are filled in, so the site shows D with real content at the next INT build.

The epic's priority line ends with "#6 → #7 checked by #9". D is where the thesis's L1 / L1′ claims come from (`../analysis-stages-B-D-F.md` §3.1).

---

## 2. Acceptance Criteria

**Shared plumbing**

- [x] **AC-1** (D.1): D reads its inputs only through contracts, refuses a failed certificate, and writes every output as a contract-valid file in a run directory.
  ✔ Evidence: `D_quantum_growth/src/io_contracts.py:29` (certificate_refusal), `:61` (envelope), `:74` (write_contract), `:90` (begin: refusal → exit 2); verified: failed certificate → "draw rejected: certificate status=fail", exit 2, only `run.json`
  → `D_quantum_growth/src/io_contracts.py` (mirrors `E_classical_growth/src/io_contracts.py`):
    - It loads and validates `tumor_draw`, `certificate` and `compiled_circuit`. The defaults are `shared/stubs/...`, and each can be overridden with a flag.
    - `certificate_refusal()`: status ≠ `pass` or no `extracted_seed_hex` → "draw rejected", logged in `run.json` notes, no outputs, exit code 2 (epic §5: no retry, no fallback).
    - It provides `envelope()` (contract, version, `produced_by`, `created_utc`, `stub: false`, `sim_label`, `hardware: null`, `upstream` refs with sha256) and `write_contract()`, which writes the file and then validates it with `shared.validate`.
  → Runs go to `D_quantum_growth/runs/<run_id>/` via `shared.runrecord.start_run(...)`. One `add_job` per simulator job, `add_input` / `add_output` for every contract file.
  → Hidden choices come from the certificate seed via `shared.seedhash.derive_seed(seed_hex, label)`, with labels `"D2-test-mask"`, `"D2-sim"`, `"D5-sim"`, `"D3-sim"`, `"D3-snapshot-shot"`.
- [x] **AC-2** (D.2): one orchestrator produces the whole D hand-off in one run.
  ✔ Evidence: `src/grow.py:21` (orchestrator: lineage → memory → QCA → seed shape → BP); run `20261029-112717-grow-ideal` and `…-112719-grow-heron` validate with `python -m shared.validate`; stages alone: `src/lineage.py:283`, `src/memory_advantage.py:155`, `src/qca.py:328`, `src/bp.py:414`. Files: 3 job records, lineage, 2 witness records, memory record, simulability report, seed_shape.json+npz, run.json (+ counts, `*_detail.json` sidecars)
  → `python -m D_quantum_growth.src.grow --mode ideal|heron [--dd] [--tumor-draw P] [--certificate P] [--compiled-circuit P]` runs D-2 → D-5 → D-3 → BP adversary.
  → It writes `quantum_job_record_{lineage,qmachine,qca}.json`, `quantum_lineage.json`, `witness_record_{lineage,qca}.json`, `memory_advantage_record.json`, `simulability_report.json`, `seed_shape.json` + `seed_shape.npz` and `run.json`.
  → Every file passes `python -m shared.validate <file>`, and every JSON carries the run's sim label.
  → Each stage is also runnable alone: `python -m D_quantum_growth.src.lineage|memory_advantage|qca --mode …`, and `python -m D_quantum_growth.src.bp --run <run_dir>`.

**#8: dynamic-circuit feed-forward (D-2)**

- [x] **AC-3** (D.3): the Bäumer constant-depth long-range Bell pair is reproduced in simulation.
  ✔ Evidence: `repro/baumer_long_range.py` (dynamic/unitary builders, `fidelity`, `crossover`), figure `figures/baumer_fidelity_vs_distance.png`; ideal dynamic F = 1.0000 at n = 2…12; Heron: no crossover, paper's ≳ 10 not matched, recorded in dossier #8
  → `D_quantum_growth/repro/baumer_long_range.py` builds two circuits for distances n = 2…12 along a FakeMarrakesh heavy-hex path:
    1. the dynamic version: ancilla Bell chain → mid-circuit X/Z measurements → parity feed-forward `if_test` corrections, constant depth;
    2. the unitary SWAP / CNOT-ladder baseline.
  → It measures Bell fidelity from ZZ / XX / YY parities in both modes and plots `figures/baumer_fidelity_vs_distance.png`.
  → Ideal: the dynamic fidelity is 1.000 ± stat at every n, which is the paper's defining property and the number we reproduce.
  → Heron-class noise: the crossover distance (if any) is reported next to the one published in [HW05], **whether or not it matches**. A non-match is recorded as such, with readout ≫ 2q error as the documented suspect (this repo's QDEP finding: teleport routing does not pay off on Heron r2).
- [x] **AC-4** (D.4): the one-job lineage runs as one Aer job with feed-forward and is decoded into a valid `quantum_lineage`.
  ✔ Evidence: `src/lineage.py:47` (`build`: one dynamic circuit, G = 8, `if_test`, `reset`), `:157` (`run_job`: one `AerSimulator.run`), `:169` (`decode`), `:209` (`run`); `fate` is a one-element list per generation (schema requires an array)
  → `D_quantum_growth/src/lineage.py` builds one dynamic circuit with G = 8 generations on ≤ 8 logical qubits, laid out on a connected FakeMarrakesh path by `src/heavyhex.py`. Per generation:
    1. a basis coin (ancilla H → measure) chooses Z or X for this generation's daughter pair;
    2. divide: the parent is entangled into a daughter pair (ideally Φ⁺-like);
    3. fate from a **two-qubit correlation**: a fate rotation acts on the pair before readout, and fate is decoded from the pair's joint outcome, never from a single-qubit phase dial in Z (epic §3 honesty lesson);
    4. pair measured mid-circuit in the coin's basis;
    5. the next parent is seeded by `if_test` on the measured genotype bit;
    6. ancillas reset.
  → Fates ∈ {`divide`, `rest`, `necrotic`, `test`}. A `necrotic` outcome sets a dead flag through feed-forward, and the remaining generations are skipped on-chip (threshold selection, `../analysis-stages-B-D-F.md` D-2).
  → All circuits of the run go in **one** `AerSimulator.run([...])` call, so there is one job ID, one transpile seed and one calibration snapshot. Default 4,000 shots.
  → The decoder writes `quantum_lineage.json` (g, measured_bits, fate, chsh_round per generation) from the most-frequent-lineage shot selected by `derive_seed(seed, "D2-lineage-shot")`, plus `quantum_job_record_lineage.json` with `test_round_mask` = the secret generation mask.
- [x] **AC-5** (D.5): hidden CHSH test rounds are interleaved and scored.
  ✔ Evidence: `src/lineage.py:33` (mask from `D2-test-mask`, 2 of 8), `:185` (`lineage_witness`: S over all test rounds, `S_chsh` observable, label "certification-ready, not certified (simulated)"); `--chsh-settings classical` → S = 0.019, rejected, exit 3, no `seed_shape.json`
  → The mask is ~25 % of generations (at least 2), chosen from `derive_seed(seed, "D2-test-mask")`. It is fixed per job and recorded only in the job record.
  → In a test generation the daughter pair is measured in CHSH settings. Each side's setting comes from a per-shot in-circuit coin, so the settings are quantum-random per shot, not compiled per circuit. The lineage continues from the previous parent, and fate is `test`.
  → S is computed over all test rounds of all shots with its standard error and written into the lineage witness record's `observables` as `S_chsh`, with the label **"certification-ready, not certified (simulated)"**. If S ≤ 2: the run is **rejected and logged** (epic decision 6) and no seed shape is written. A debug flag `--chsh-settings classical` (mirrors C's `--settings classical`) forces this fail path.
- [x] **AC-6** (D.6): a per-generation division-pair witness is measured in ≥ 2 bases.
  ✔ Evidence: `src/lineage.py:185` (⟨XX⟩/⟨ZZ⟩ per generation with bootstrap, `src/witness.py:23`), `witness_record_lineage.json` ideal 1.54–1.76, heron 1.40–1.62, `passed: true`; README table has heron ± `--dd`
  → `src/witness.py`: ⟨ZZ⟩_g from the Z-coin shots and ⟨XX⟩_g from the X-coin shots of generation g, bootstrap standard error.
  → `witness_record_lineage.json`: `witness_expression = "<XX>_g + <ZZ>_g > 1 for every non-test generation g"`, `threshold = 1`, `bases = ["X","Z"]`, `observables` = one entry per generation + `S_chsh`, `passed` = every generation exceeds 1 by ≥ 3σ, `mi_network = null`, claim level L1.
  → It is reported for ideal and heron. In heron mode it is also reported with and without `--dd`.
- [x] **AC-7** (D.7): the dynamical-decoupling lever is measurable and honestly bounded.
  ✔ Evidence: `src/lineage.py:63` (`idle`: explicit delay windows, X–X echo with `--dd`); Aer applies thermal relaxation to `delay` (checked); XY4/`PadDynamicalDecoupling` impossible on this target (no `y`, ALAP fails on `if_else`); measured: −0.0027 ± 0.0060 → "no measured effect"
  → `--dd` transpiles with ALAP scheduling + `PadDynamicalDecoupling` (XY4) on idle windows around mid-circuit measurements, using FakeMarrakesh durations.
  → The implementer first confirms that the Aer FakeMarrakesh noise model applies thermal relaxation to `delay` instructions. If it does not, the README states that DD is **not modelled** in simulation and AC-7 records "lever inert in sim", not a fake gain.
  → The README table gives the witness mean (DD off / on) with errors. A difference within 2σ is reported as "no measured effect".

**#6: quantum causal states (D-5, headline)**

- [x] **AC-8** (D.8): the causal-state machinery is rebuilt and the published numbers are reproduced.
  ✔ Evidence: `src/causal_states.py:32` (survival), `:48` (causal states), `:76` (C_μ, D_μ), `:94` (Gram fixed point), `:119` (Wu model), `:187` (C_q, D_q); `repro/causal_states_repro.py` → `figures/gu_perturbed_coin.png`, `figures/wu_pmd_memory.png`; Gu C_q(0.2)=0.469<0.5, C_q(0.4)=0.0815<0.1; Wu D_q=1, D_μ=log₂N, N=2…16
  → `D_quantum_growth/src/causal_states.py`:
    - discrete-time renewal process from a survival function Φ(n);
    - causal states = time since last tick (merged where future distributions coincide);
    - stationary distribution → C_μ (Shannon) and D_μ = log₂(#causal states);
    - quantum memory states |σ_n⟩ = Σ_k √(P(k | n)) |k⟩-style construction per [D06]/[D16], Gram matrix → C_q = S(ρ) of the stationary mixture;
    - D_q = rank of the Gram matrix, log₂.
  → `D_quantum_growth/repro/causal_states_repro.py` reproduces:
    1. Gu's perturbed coin, C_q(p) vs C_μ = 1 over p ∈ (0, 1), analytic curve, `figures/gu_perturbed_coin.png`;
    2. Wu's PMD family, D_μ = log₂ N growing while D_q ≤ 1 for N = 2…16, at the parameter values printed in [D16].
  → Published values are matched to the precision printed in the paper. Any non-match is recorded in the dossier.
- [x] **AC-9** (D.9): the tumor-relevant process and its quantum model run as a dynamic circuit.
  ✔ Evidence: `src/causal_states.py:20-30` (CELLCYCLE N=8, Γ=0.5, V=0.4, cited), `src/memory_advantage.py:65` (`run`; `build` with unitary → measure → reset ×10, X/Y/Z variants in one job), `:155` (CLI)
  → Process: a **cell-cycle division timer** in Wu's PMD form (period N = 8 steps, modulation V, base survival γ). The parameter values are set in `src/causal_states.py` with a citation of where they come from (Q3).
  → `D_quantum_growth/src/memory_advantage.py` compiles the 1-qubit-memory quantum model into a 2-qubit unitary (memory + output) via isometry completion. Each step is: apply U → measure output mid-circuit → reset output, for L = 10 steps in one circuit.
  → Three tomography variants measure the final memory qubit in X / Y / Z, all in the same Aer job.
  → Measured:
    - per-symbol KL divergence d_KL between the simulated length-L word distribution and the exact process;
    - memory-state fidelity;
    - **C_q(measured)** = von Neumann entropy of the tomographically reconstructed stationary memory state.
- [x] **AC-10** (D.10): a classical baseline at equal memory is computed.
  ✔ Evidence: `src/causal_states.py:256` (`best_classical_fixed_memory`, n_states=2, seeded multi-start); d_KL 0.00315 (same sample count) / 0.00136 (exact) reported next to quantum 0.00192
  → `src/causal_states.py: best_classical_fixed_memory(process, n_states=2)`: a 2-state (1-bit) classical HMM fitted to minimise per-symbol KL (scipy, multi-start, starts from `rng(seed, "D5-baseline")`). Its d_KL is reported next to the quantum model's.
- [x] **AC-11** (D.11): `memory_advantage_record.json` is written and honest.
  ✔ Evidence: `src/memory_advantage.py:65-150` (record, `passed` rule); `memory_advantage_record.json` L1′, `n_qubits=1`; d_KL lives in `process_description` + `memory_advantage_detail.json` (no schema field, CCR-D2)
  → Fields: `process_description`, `C_mu_bits`, `C_q_bits` (theory), `C_q_measured`, `n_qubits` = 1 (memory), `passed`, `job_record_ref`.
  → `passed` = C_q_measured < C_μ **and** d_KL(quantum) < 10⁻² bits/symbol (Wu's distortion level) **and** d_KL(quantum) < d_KL(best 1-bit classical).
  → Reported per mode. The README states [D-5]'s caution: the advantage needs strong correlations; low-correlation processes are compressed classically too.
  → Claim level L1′, "simulated" label.

**#7: Goldilocks QCA (D-3)**

- [x] **AC-12** (D.12): Jones 1-D T6 is reproduced.
  ✔ Evidence: `src/qca.py:54` (`t6_circuit`), `:149` (`t6_run`), `:111` (clustering); `repro/jones_t6.py`; O(t) conserved to 2.5e-14; L=17 clustering within 0.008 of the figure readings (reading error ±0.03); L = 23 by statevector (MPS slower), Heron L = 11 only
  → `D_quantum_growth/src/qca.py`: rule T6 exactly as defined in [D14] (three-site totalistic, Hadamard activation, fixed |0⟩ boundaries, single central flip), compiled to controlled gates with even/odd sublattice updates.
  → `D_quantum_growth/repro/jones_t6.py` runs chains L ∈ {11, 17} (statevector) and 23 (`matrix_product_state`, ideal only), t ≤ 15 cycles, ideal + heron.
  → It computes the population dynamics ⟨n_j(t)⟩ and the MI network measures used in [D14]: clustering coefficient, network density and disparity, from Z-basis 1- and 2-site marginals.
  → It plots `figures/jones_t6_population.png` and `figures/jones_t6_network.png`.
  → Match target: the ideal-simulation values shown in [D14] for the same L and t, within ±0.02 (read from figure) or the printed precision. Our heron-mode curve is shown next to the paper's hardware curve, with no matching claim.
- [ ] **AC-13** (D.13): a heavy-hex Goldilocks QCA runs natively on a FakeMarrakesh patch.
  ◐ Evidence: PARTIAL. `src/heavyhex.py` (`patch`), `src/qca.py:170` (`goldilocks_circuit`, bipartite Floquet, 11 + 9 circuits, one job id). Deviations: the exact rule needs a C³-H at degree-3 sites → **376 routing SWAPs on the 21-qubit patch** (hexagon: 0); Heron mode runs the 12-qubit hexagon (Aer cost, developer decision).
  → `src/heavyhex.py`: deterministic choice of a 21-qubit connected FakeMarrakesh subgraph (two adjacent heavy-hex cells), its bipartition (A/B), planar layout coordinates and a centre node.
  → `src/qca.py: heavy_hex_goldilocks(patch, t_max=10)`: activation = H on a site **iff exactly one neighbour is active**, as the D-3 rule (`../analysis-stages-B-D-F.md` §3). Sublattice A is updated, then sublattice B, per Floquet cycle. Controls are ≤ 3 neighbours, decomposed into CZ + 1q.
  → Initial state: single flip at the centre node. `initial_layout` = the patch's physical qubits, and the transpiled circuit is checked to contain **no SWAPs**; this is reported.
  → Circuits in one job:
    - Z readout after each t = 0…t_max (population);
    - 9 bipartite-basis readouts at t_max.
- [x] **AC-14** (D.14): the QCA has an entanglement witness and an MI network in ≥ 2 bases.
  ✔ Evidence: `src/qca.py:233` (`run`: 9 bipartite settings, negativity + MI), `src/witness.py:52` (`tomo_pair`), `:69` (`nearest_physical`), `:85` (`negativity`); ideal 0.0167 ± 0.0055 (3.04σ) passed, Heron hexagon failed → `seed_shape` claim L0; `mi_network` edges on heavy-hex edges
  → `src/witness.py`: from the 9 settings it reconstructs ρ_ij for every nearest-neighbour pair (linear inversion → nearest physical state), computes negativity N_ij (bootstrap σ) and the MI network from the same reduced states.
  → `witness_record_qca.json`: `witness_expression = "max over NN pairs of negativity N_ij > 0"`, `threshold = 0`, `passed` = some pair with N_ij > 3σ, `bases = ["X","Y","Z"]`, `mi_network` = nodes (physical qubit IDs) + edges with MI.
  → Claim L1 only if `passed`. Otherwise the README says "MI structure only, no L1".
- [x] **AC-15** (D.15): the QCA snapshot becomes a valid 3-D `seed_shape` that E can read.
  ✔ Evidence: `src/seed_shape.py:27` (`lift`), `:56` (`write`); `seed_shape.npz` (17,17,17), sum = n_cells = 301, spacing 0.5; `python -m E_classical_growth.src.grow --seed-shape …` ran to completion (E run deleted); `figures/qca_snapshot_2d.png`
  → `D_quantum_growth/src/seed_shape.py`: takes the Z-basis snapshot at t_max from shot `derive_seed(seed, "D3-snapshot-shot")` and forces the centre node active. The **3-D lift** is a solid of revolution of the active node set about the patch's principal axis through the centre node (Q2). It is voxelised at 0.5 mm pitch (one patch-cell step = 1 voxel; Q4), morphologically closed by 1 voxel, and kept as the connected component containing the centre.
  → Output: `seed_shape.npz` (`occupancy` uint8 3-D, `spacing_mm_xyz` float64 (3,)) + `seed_shape.json`, with `lineage_ref` = this run's `quantum_lineage.json`, `claim_level` = L1 if the QCA witness passed else L0, and `n_cells` = occupancy sum.
  → Hand-off check: `python -m E_classical_growth.src.grow --seed-shape D_quantum_growth/runs/<run>/seed_shape.json` runs without error (read-only use of E's merged code for verification; nothing in E is edited).
  → `figures/qca_snapshot_2d.png` shows the patch, plus a 3-slice export of the 3-D seed.

**#9: belief-propagation adversary**

- [x] **AC-16** (D.16): a BP-gauged tensor-network simulator is rebuilt from [HW04].
  ✔ Evidence: `src/bp.py:30` (`BPTN`: simple update, BP messages `bp`, BP gauge `gauge`), `:214` (`gates_of`), `:241` (`simulate`); checked on small circuits vs exact statevector
  → `D_quantum_growth/src/bp.py`, pure NumPy:
    - one tensor per qubit with one virtual leg per coupling-graph edge;
    - gates are applied by simple update with SVD truncation to bond dimension χ;
    - the gauge is kept by BP message passing on the loopy graph (Tindall's BP / Vidal-gauge equivalence);
    - local expectation values are computed from BP fixed-point environments.
  → It accepts any Qiskit `QuantumCircuit` whose 2q gates act on coupling-graph edges, and ignores measurement / reset / feed-forward by simulating the coherent unitary blocks between them.
- [ ] **AC-17** (D.17): Tindall's kicked-Ising result is reproduced.
  ◐ Evidence: PARTIAL. `repro/tindall_kicked_ising.py`: proof-of-concept sweep χ ∈ {2,4,8}, 127-qubit Eagle map; BP vs exact light-cone error 5.7e-3 (θ=π/4) and 4.3e-2 (θ=1.0) at χ = 8, falling with χ; paper's exact agreement not reached; reduced on request. Figure `figures/tindall_magnetisation.png`.
  → `D_quantum_growth/repro/tindall_kicked_ising.py`: the 127-qubit Eagle heavy-hex coupling map (taken from `FakeSherbrooke`, geometry only), θ_J = −π/2, 5 Trotter steps, θ_h sweep over [0, π/2], χ ∈ {1, 2, 4, 8, 16}.
  → It checks against exact light-cone statevector values for observables whose light cone fits in ≤ 25 qubits, and against one value stated in the text or figures of [HW04], picked at dissection and named in the dossier: within the paper's stated accuracy, or ±0.02 if read from a figure.
  → It plots `figures/tindall_magnetisation.png`.
- [x] **AC-18** (D.18): every D circuit has a measured simulability number.
  ✔ Evidence: `src/bp.py:371` (`run_adversary`), `:394` (`write_report`), `:406` (`smallest_chi`); `simulability_report.json` one entry per (circuit, χ); README: smallest χ ≥ 0.99 = 2 (lineage, q-machine), none ≤ 16 (QCA)
  → `python -m D_quantum_growth.src.bp --run <run_dir>` (also called by `grow`) loads every circuit of the run (lineage coherent blocks, q-machine step, QCA t_max circuit). It runs BP at χ ∈ {2, 4, 8, 16} and compares to the ideal Aer result of the same circuit.
  → `simulability_report.json`: one entry per (circuit, χ) with `circuit_hash` (`shared.simbackend.circuit_hash`), `method = "belief-propagation"`, `bond_dim`, `fidelity_vs_sim` (definition Q6), `runtime_s`.
  → The README states the smallest χ at which each circuit is reproduced to ≥ 0.99. That is the measured "no L2 claim".

**Documentation and status**

- [x] **AC-19** (D.19): dossiers #6–#9 are filled in, and #10 gets its post-selection note.
  ✔ Evidence: `dossiers/06…09-*.md` all sections filled (`grep -c 'Not yet'` = 0); `dossiers/10-measurement-induced-transition.md` Koh post-selection paragraph only
  → Every fixed section of `dossiers/06…09-*.md` is written: Concept, Equations, Parameters, Paper's claimed result, Our reproduction (number + figure + run id + sim mode), Adaptation, Verdict, What to reuse next.
  → `dossiers/10-measurement-induced-transition.md`: its remaining "Not yet dissected" sections become one paragraph on Koh's [D15] trick for avoiding post-selection, and nothing more (epic decision 5).
- [x] **AC-20** (D.20): `status.json` and the README reflect what was really achieved.
  ✔ Evidence: `D_quantum_growth/status.json` (#6 adapted, #7 adapted, #8 dissected, #9 dissected, #10 unchanged), `python -m shared.validate --status` OK; README filled; `python -m shared.site.build` previewed (D renders), `index.html`/`site/` reverted
  → States:
    - #6 / #7 / #8: `reproduced` → `adapted` only where the published number was matched; otherwise `dissected` with the gap in the dossier, as F did with #17.
    - #9: `reproduced` / `adapted`.
    - #10 is unchanged.
  → `reproduced`, `claim_level` and `sim_mode` filled in; `figures` listed; `updated` = implementation date. `python -m shared.validate --status` passes.
  → README sections filled in: How to run (exact commands), Reproduced result vs paper (a table per target, both modes), Claim level and honesty notes (L0 / L1 / L1′ per output, BP number, "simulated", "certification-ready, not certified"), Contract change requests (Q7).
  → A local `python -m shared.site.build` preview renders D, but `index.html` / `site/` are **not** committed (epic §3).

---

## 3. Out of Scope (Postponed)

- **#10 / D-4 measurement-induced transition**: not built (epic decision 5). Only the dossier note.
- **D-1 QALife Mode A as separate per-generation jobs**: superseded by D-2. The MVP's F4 fate-dial fix belongs to the MVP, not this epic (isolation rule).
- **D-6 quantum-walk invasion and D-7 fault-tolerant spine**: cite only (epic §1 "not reverse-engineered").
- **Real IBM hardware runs**: future work everywhere (epic decision 4). No `hardware` fields filled in.
- **Feeding B's real founder circuit into D-2**: D records the `compiled_circuit` / `tumor_draw` refs as upstream, but prepares a fixed founder by default (Q1). Wiring the real B founder is **INT**.
- **Coupling the lineage outcome into the QCA initial condition** (alive cells → initial QCA excitations): proposal only (Q2). The default is the paper-faithful single flip; revisit in INT.
- **Scaling E with the seed shape (size_mm matching), cohort runs, drift statistics**: E and H.
- **Signing the receipt, hash-chaining D's records into the ledger**: G. D writes only run records.
- **Validation statistics over many D runs (witness / certificate distributions)**: H.
- **Any edit to `shared/` contracts**: recorded as Contract change requests; INT applies them.

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Simulator | `shared.simbackend.make_simulator(mode, seed=…)`, `transpile_heron`, `run_counts`, `calibration_snapshot`, `circuit_hash`. Both modes on the FakeMarrakesh target (the epic's pinned reference). |
| "One job" | One `AerSimulator.run([circuits…])` call per stage. All circuit variants of a stage (tomography bases, population time points, coin-driven bases) share one job ID, one transpile seed and one calibration snapshot. |
| Feed-forward | `QuantumCircuit.if_test` + `reset`, mid-circuit `measure` (Aer-verified with the FakeMarrakesh noise model on 2026-10-29). |
| Large ideal circuits | Aer `statevector` up to ~25 q; `matrix_product_state` for the 23-site T6 chain (ideal only). Heron-mode circuits stay ≤ 21 q. |
| D-2 register | ≤ 8 logical qubits on a FakeMarrakesh heavy-hex path, G = 8 generations, 4,000 shots. |
| D-5 process | Cell-cycle division timer in Wu's PMD renewal form, N = 8, 1 memory qubit + 1 output qubit, L = 10 steps. |
| D-3 patch | 21-qubit FakeMarrakesh subgraph (two adjacent heavy-hex cells), bipartite Floquet update, t_max = 10, rule "H iff exactly one active neighbour". |
| Tomography / witness | 9 bipartite global settings → every nearest-neighbour 2q state → negativity + MI; lineage witness ⟨XX⟩+⟨ZZ⟩ > 1; bootstrap σ (1,000 resamples, `rng(seed, "D-bootstrap")`). |
| BP adversary | Own NumPy implementation (Q5), χ ∈ {2, 4, 8, 16}; Tindall's Julia code (ITensorNetworks) is read only for reference, never called. |
| 3-D lift | Solid of revolution of the 2-D active set about the patch's principal axis, 0.5 mm pitch (Q2, Q4). |
| Figures | matplotlib PNGs in `D_quantum_growth/figures/`, each with its sim label in the title. |

**Conventions & Notes:**
* Adopt epic §3 verbatim: simulation only, FakeMarrakesh, files-only contracts, letter-folder ownership, Markdown as source of truth, honesty gates, logging into run records, no MVP imports.
* Module layout mirrors `C_certificate/src/` (quantum, Aer, `--mode ideal|heron`) and `E_classical_growth/src/io_contracts.py` (input loading, refusal, refs).
* **Two-qubit rule:** any "fate" or "interference" quantity is read from ≥ 2-qubit correlations in ≥ 2 bases. No single-qubit Z-basis phase dial anywhere.
* **Claim levels per output:** lineage = L1 (+ L0-style in-job CHSH, "certification-ready, not certified"); memory advantage = L1′; QCA = L1 only if the negativity witness passes; seed shape inherits from the QCA. Never L2 / L3; never "more realistic because quantum" / "quantum biology" / "classically impossible".
* Every quantum number is written with its sim label: JSON `sim_label`, README tables, dossier text and figure titles.
* Determinism: given the same inputs and mode, all outputs are byte-identical (all Aer `seed_simulator`, `seed_transpiler` and NumPy RNGs come from the certificate seed).
* Gaps the epic did not decide, decided here and noted for INT:
  - `quantum_job_record.fake_backend` is a `FakeMarrakesh` const, so repro scripts that use other geometry (Eagle for #9) emit no job record, only a run record.
  - `witness_record` has no slot for S_chsh, so it goes into `observables` (Q7).

---

## 5. Data Model (Additions/Modifications)

No contract changes. D **produces** these frozen W contracts (v1.0.0) for the first time with real content, and **consumes** stubs:

```text
[Consumed — frozen, stub defaults]
tumor_draw        shared/stubs/tumor_draw/tumor_draw.json            upstream ref + draw_id; founder fixed (Q1)
certificate       shared/stubs/certificate/certificate.json          status gate + extracted_seed_hex → all seeds
compiled_circuit  shared/stubs/compiled_circuit/compiled_circuit.json upstream ref only (Q1)

[Produced — per run in D_quantum_growth/runs/<run_id>/]
quantum_job_record_lineage.json   sim_mode, fake_backend=FakeMarrakesh, sim_seed, shots, transpiled_hash,
                                  counts_file, test_round_mask = [bool]*G (secret CHSH generations), calibration_snapshot
quantum_job_record_qmachine.json  same; test_round_mask = null
quantum_job_record_qca.json       same; test_round_mask = null
quantum_lineage.json              job_record_ref, claim_level L1, generations[g, measured_bits, fate∈{divide,rest,necrotic,test}, chsh_round]
witness_record_lineage.json       claim L1, observables {"XX+ZZ_g0".., "S_chsh"}, bases [X,Z], threshold 1, mi_network null
witness_record_qca.json           claim L1, observables {"N_<i>_<j>"..}, bases [X,Y,Z], threshold 0, mi_network {nodes, edges[i,j,mi]}
memory_advantage_record.json      claim L1′, process_description, C_mu_bits, C_q_bits, C_q_measured, n_qubits=1, passed, job_record_ref
simulability_report.json          circuits[{circuit_hash, method="belief-propagation", bond_dim, fidelity_vs_sim, runtime_s}]
seed_shape.json + seed_shape.npz  lineage_ref → quantum_lineage.json, claim L1|L0, npz{occupancy uint8 3-D, spacing_mm_xyz (3,)}, n_cells
run.json (+ counts_*.json)        shared.runrecord RunRecord: code_hash, git, seed_hex, sim, jobs[], inputs[], outputs[], notes

[Modified]
D_quantum_growth/status.json      #6–#9 lifecycle states, reproduced, claim_level, sim_mode, figures, updated
```

---

## 6. File Plan (Concrete Changes)

All paths relative to `RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`.

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `D_quantum_growth/src/io_contracts.py` | Input defaults (stubs), `load_inputs`, `certificate_refusal`, `envelope`, `write_contract` (+ validate), `ref()`. Mirror `E_classical_growth/src/io_contracts.py`. |
| New | `D_quantum_growth/src/heavyhex.py` | FakeMarrakesh coupling graph (networkx), deterministic path for D-2, 21-q two-cell patch for D-3, bipartition, planar layout coords, centre node. |
| New | `D_quantum_growth/src/witness.py` | ⟨XX⟩/⟨ZZ⟩ per generation, CHSH S, 2q linear-inversion tomography from bipartite settings, negativity, MI network, bootstrap σ. |
| New | `D_quantum_growth/src/lineage.py` | D-2 one-job dynamic circuit (coins, divide, two-qubit fate, mid-circuit measure, `if_test` seed, reset, hidden CHSH, necrotic stop), optional DD pass, decoder → `quantum_lineage` + lineage witness + job record. CLI `--mode --dd`. |
| New | `D_quantum_growth/src/causal_states.py` | Renewal process from Φ(n), causal states, C_μ / D_μ, quantum memory states, Gram matrix, C_q / D_q, isometry → unitary, best 1-bit classical HMM baseline, PMD cell-cycle process parameters (cited). |
| New | `D_quantum_growth/src/memory_advantage.py` | D-5 dynamic circuit (U → measure output → reset, L steps), X/Y/Z memory tomography, d_KL, C_q(measured), `memory_advantage_record` + job record. CLI `--mode`. |
| New | `D_quantum_growth/src/qca.py` | T6 1-D rule (repro) and heavy-hex "exactly one neighbour" Goldilocks rule, bipartite Floquet circuits, population + 9-setting readout circuits, SWAP-free check, QCA witness + job record. CLI `--mode`. |
| New | `D_quantum_growth/src/seed_shape.py` | Snapshot shot selection, solid-of-revolution 3-D lift, 0.5 mm voxelisation, closing, connected component, `seed_shape.npz` / `.json` via `shared.volumes.save_npz`. |
| New | `D_quantum_growth/src/bp.py` | BP-gauged simple-update tensor network on a coupling graph; Qiskit circuit → coherent blocks → local expectations; `--run <dir>` writes `simulability_report.json`. |
| New | `D_quantum_growth/src/grow.py` | Orchestrator CLI: inputs → refusal gate → lineage → memory advantage → QCA → seed shape → BP → run record. |
| New | `D_quantum_growth/repro/baumer_long_range.py` | #8 reproduction: dynamic vs unitary long-range Bell pair, fidelity vs distance, ideal + heron. |
| New | `D_quantum_growth/repro/causal_states_repro.py` | #6 reproduction: Gu perturbed coin C_q(p); Wu PMD D_μ vs D_q for N = 2…16 at the paper's parameters. |
| New | `D_quantum_growth/repro/jones_t6.py` | #7 reproduction: 1-D T6 population + MI network measures, L ∈ {11, 17, 23}, ideal + heron. |
| New | `D_quantum_growth/repro/tindall_kicked_ising.py` | #9 reproduction: 127-q Eagle kicked Ising, 5 steps, θ_h sweep, χ sweep, light-cone exact check. |
| New | `D_quantum_growth/figures/baumer_fidelity_vs_distance.png` | AC-3 figure. |
| New | `D_quantum_growth/figures/gu_perturbed_coin.png` | AC-8 figure. |
| New | `D_quantum_growth/figures/wu_pmd_memory.png` | AC-8 figure (D_μ vs D_q over N). |
| New | `D_quantum_growth/figures/cellcycle_memory_advantage.png` | AC-9/10/11: d_KL quantum vs 1-bit classical, C_q(measured) vs C_μ, both modes. |
| New | `D_quantum_growth/figures/lineage_witness.png` | AC-6/7: ⟨XX⟩+⟨ZZ⟩ per generation, ideal / heron / heron+DD, threshold line. |
| New | `D_quantum_growth/figures/jones_t6_population.png` | AC-12 figure. |
| New | `D_quantum_growth/figures/jones_t6_network.png` | AC-12 figure. |
| New | `D_quantum_growth/figures/qca_snapshot_2d.png` | AC-13/15: patch snapshot + 3-slice export of the 3-D seed. |
| New | `D_quantum_growth/figures/qca_mi_network.png` | AC-14: MI network on the patch layout, negativity per edge. |
| New | `D_quantum_growth/figures/tindall_magnetisation.png` | AC-17 figure. |
| New | `D_quantum_growth/figures/simulability.png` | AC-18: fidelity_vs_sim vs χ per D circuit. |
| Modify | `D_quantum_growth/dossiers/06-quantum-causal-states.md` | Fill all sections (AC-19). |
| Modify | `D_quantum_growth/dossiers/07-goldilocks-qca.md` | Fill all sections. |
| Modify | `D_quantum_growth/dossiers/08-dynamic-circuit-feedforward.md` | Fill all sections. |
| Modify | `D_quantum_growth/dossiers/09-bp-heavy-hex-adversary.md` | Fill all sections. |
| Modify | `D_quantum_growth/dossiers/10-measurement-induced-transition.md` | Post-selection note only. |
| Modify | `D_quantum_growth/status.json` | Lifecycle states and fields (AC-20). |
| Modify | `D_quantum_growth/README.md` | How to run, results vs paper, claim / honesty, Contract change requests section (as in C/E). |
| Modify | `feature-D-quantum-growth.md` | Tick ACs with evidence, §9 post-implementation notes. |

`D_quantum_growth/runs/` is gitignored (epic decision 7). `src/__init__.py` and `repro/__init__.py` already exist.

---

## 7. Manual Verification (No Tests)

All commands run from `RE/` inside the `re-D` worktree.

- [x] **Verify AC-1:** `python -m D_quantum_growth.src.grow --mode ideal --certificate <copy of the stub with "status": "fail">` → exit code 2, `run.json` notes "draw rejected: certificate status=fail", no contract outputs in the run dir.
- [x] **Verify AC-2:** `python -m D_quantum_growth.src.grow --mode ideal` and `--mode heron` → each run dir contains the 11 files listed in AC-2; `python -m shared.validate D_quantum_growth/runs/<run>/*.json` reports all valid. Run ideal twice → identical sha256 of every output except `created_utc` / run id.
- [x] **Verify AC-3:** `python -m D_quantum_growth.repro.baumer_long_range` → ideal dynamic fidelity ≈ 1.000 at all n; the heron crossover is printed next to the [HW05] value; figure written.
- [x] **Verify AC-4:** open `quantum_lineage.json`: 8 generations, fates from the allowed set, `chsh_round` matching `test_round_mask` in `quantum_job_record_lineage.json`; one job ID in `run.json` for the lineage stage; transpiled circuit contains `if_else` and `reset`.
- [x] **Verify AC-5:** ideal → `S_chsh` ≈ 2.8 > 2; a run forced with `--chsh-settings classical` (debug flag) → S ≤ 2 → run rejected + logged, no `seed_shape.json`.
- [x] **Verify AC-6/7:** `witness_record_lineage.json` ideal → every generation ≈ 2 > 1, `passed: true`; heron with and without `--dd` → values in the README table with σ; `figures/lineage_witness.png` shows all three.
- [x] **Verify AC-8:** `python -m D_quantum_growth.repro.causal_states_repro` → printed Gu C_q at the paper's p values and Wu D_q ≤ 1 for all N, next to the published numbers.
- [x] **Verify AC-9/10/11:** `python -m D_quantum_growth.src.memory_advantage --mode ideal` → d_KL < 10⁻², C_q(measured) < C_μ, d_KL(quantum) < d_KL(1-bit classical), `passed: true`; heron → same fields printed, `passed` whatever it honestly is.
- [x] **Verify AC-12:** `python -m D_quantum_growth.repro.jones_t6` → population and network metrics within tolerance of the [D14] ideal values; figures written.
- [x] **Verify AC-13:** `python -m D_quantum_growth.src.qca --mode heron` prints "SWAPs: 0" and the 21 physical qubits; job record has 11 + 9 circuits under one job ID.
- [x] **Verify AC-14:** `witness_record_qca.json` ideal → at least one N_ij > 3σ, `passed: true`, `mi_network` edges on heavy-hex edges; README states the heron verdict.
- [x] **Verify AC-15:** `python -c "import numpy as np; d=np.load('D_quantum_growth/runs/<run>/seed_shape.npz'); print(d['occupancy'].shape, d['occupancy'].sum(), d['spacing_mm_xyz'])"` → 3-D, sum = `n_cells`, spacing 0.5; then `python -m E_classical_growth.src.grow --seed-shape D_quantum_growth/runs/<run>/seed_shape.json` runs to completion (output into E's gitignored runs dir; delete afterwards).
- [x] **Verify AC-16/17:** `python -m D_quantum_growth.repro.tindall_kicked_ising` → BP vs light-cone exact agreement table per χ, plus the [HW04] reference value comparison; figure written.
- [x] **Verify AC-18:** `simulability_report.json` has one entry per (circuit, χ); README states the smallest χ reaching ≥ 0.99 per circuit.
- [x] **Verify AC-19/20:** `python -m shared.validate --status` passes; `python -m shared.site.build` locally → D page shows the filled dossiers and states; `git status` shows no change to `index.html` / `site/` / `shared/` (revert the preview build before committing).
- [x] **Edge case:** `--mode heron` QCA witness fails → `seed_shape.json` still written with `claim_level: "L0"`, README says "MI structure only, no L1".

---

## 8. Open Questions

- [x] **Q1: Founder state for the D-2 lineage.** B is not built, and the `compiled_circuit` stub is arbitrary. *Resolved (default accepted):* a fixed founder (|0⟩ parent, the fate rotation angles documented as illustrative constants, not fitted biology); `tumor_draw` and `compiled_circuit` recorded only as upstream refs; real B founder wired in INT.
- [x] **Q2: How the 2-D heavy-hex snapshot becomes 3-D.** The patch is planar, but the seed shape must be 3-D. *Resolved (default accepted):* solid of revolution about the patch's principal axis through the centre node (keeps the snapshot's radial profile, gives an isotropic-ish 3-D blob). Alternatives: (b) stack several shots as z-slices (no z-correlation, rejected); (c) build a 3-D QCA graph (needs SWAPs, breaks "heavy-hex native"). Also proposed: initial condition = paper-faithful single centre flip, not coupled to the lineage outcome (coupling = INT idea).
- [x] **Q3: Parameters of the cell-cycle renewal process (D-5).** *Resolved (default accepted):* Wu's PMD form with N = 8 steps per cycle, V and γ taken from one of Wu's own parameter sets (so the quantum model is guaranteed exact with 1 qubit), described as "a division-timer process of PMD form", not as fitted tumor biology. Alternative: derive γ from E's calibrated p0 (Hasegawa VDTs), which ties D-5 to E but may land in a low-correlation regime with little advantage.
- [x] **Q4: Seed-shape voxel pitch.** *Resolved (default accepted):* 0.5 mm (one patch step = one voxel = E's lattice spacing), so a 21-node patch gives a seed of a few mm, leaving E to grow it to `size_mm`. Alternative: scale the seed to a fixed fraction of `tumor_draw.size_mm`.
- [x] **Q5: BP simulator: own NumPy or `pip install quimb`?** quimb (Apache-2.0) has belief-propagation contraction built in, but is not installed. *Resolved (default accepted):* own NumPy implementation (the RE rule says re-implement from papers; no new dependency; the circuits are ≤ 21 q, and 127 q only for the repro at χ ≤ 16).
- [x] **Q6: Definition of `fidelity_vs_sim`** (the contract field is a single number in [0, 1]). *Resolved (default accepted):* 1 − ½·mean over the circuit's reported observables (every ⟨Z_i⟩ and every nearest-neighbour ⟨Z_iZ_j⟩, ⟨X_iX_j⟩) of |BP − ideal Aer|, clipped to [0, 1]. Tindall's own truncation-fidelity product goes into the README, not the contract.
- [x] **Q7: Contract change requests to log for INT.** *Resolved (default accepted):* (a) `witness_record` gets an optional `chsh` block (S, stderr, n_test_rounds), instead of `S_chsh` living in `observables`; (b) `quantum_job_record.fake_backend` could allow non-Marrakesh geometry for repro-only records. Both are only logged in the README; D works on the frozen contracts.
- [x] **Q8: One job for the in-lineage CHSH settings and witness bases.** *Resolved (default accepted):* per-shot in-circuit coin ancillas (quantum-random settings, at the cost of extra mid-circuit readouts on Heron), rather than compiling 4 + 2 circuit variants. If the extra readouts kill the heron witness, the fallback is circuit variants inside the same job (still one job ID), noted in the README.

---

## 9. Post-Implementation Notes

**Built.** Everything under `D_quantum_growth/src` and `repro` per the file plan, plus `src/figures.py`; dossiers #6–#10, README, `status.json` filled. Branch `re-D` (worktree `../qp-re-D`). Verified by manual runs (no automated tests).

**Contract surprises (recorded as CCR-D1…D7 in the README, no `shared/` edit):** `quantum_lineage.fate` is an array; `quantum_job_record` has one hash/count dict for multi-circuit jobs; `memory_advantage_record` has no d_KL field; `witness_record.claim_level` is const L1; XY4 DD is impossible on the FakeMarrakesh target (no `y`; ALAP fails on `if_else`), so X–X echoes are inserted by hand.

**Deviations from the plan.**
- Heron QCA runs a 12-qubit hexagon of the patch (21-qubit noisy Aer infeasible; developer decision). Ideal runs the full 21-qubit patch.
- The exact "one neighbour" rule on the degree-3 sites is not SWAP-free (376 routing SWAPs on the full patch); the odd-parity shortcut was rejected (population gap up to 0.57).
- Jones T6: update order = sublattice holding the central flip first (matches D14 Fig. 3); D14's network measures are clustering / path length / node strength, not "density and disparity"; L = 23 by statevector instead of MPS; paper values are read from a figure (±0.03).
- D-5: word statistics from the Z variant only (shared simulator seed → copied samples); comparison with the classical baseline at the same sample count.
- Tindall reproduction cut to a proof of concept on request (χ ≤ 8).
- Job ids are derived from the seed (deterministic) instead of uuid4.

**Results.** See README. In short: lineage S_chsh 2.87 (ideal) / 2.60 (Heron), witnesses pass; DD no measured effect; memory advantage small (d_KL 0.0019 vs 0.0031 classical at the same samples; C_q 0.063 / 0.174); QCA ideal witness passes borderline (3.04σ), Heron hexagon fails (seed shape L0); BP does not reach 0.99 on the QCA circuits up to χ = 16; Bäumer crossover not reproduced.

**Follow-ups.** INT: wire B's real founder into the lineage; couple lineage outcome into the QCA initial condition (Q2 proposal); apply CCR-D1…D7. A lower-noise QCA witness (fewer cycles / mitigation) before claiming L1 under Heron noise. Larger-χ Tindall sweep. Determinism checked byte-for-byte on the lineage and q-machine stages only. `runs/` is gitignored; run ids quoted in the dossiers (`20261029-112717-grow-ideal`, `20261029-112719-grow-heron`, `20261029-123452-lineage-heron`, `20261029-123546-lineage-heron-dd`).
