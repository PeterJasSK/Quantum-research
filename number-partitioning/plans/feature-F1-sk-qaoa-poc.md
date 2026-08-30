# Feature F1: SK QAOA proof of concept — teleport vs SWAP cost layer

**Epic:** `number-partitioning/plans/epic-number-partitioning.md` (Approved)
**Ticket:** F1 (research repo — no GitHub issue; ACs from epic §9)
**Author:** Claude (Opus)
**Date:** 2026-08-26
**Status:** Approved

> No-tests directive: this plan covers production code + manual verification only. No test
> files, no test sections.

## 1. Context

Build a small Sherrington–Kirkpatrick number-partitioning QAOA and route its ZZ cost layer
two ways — via the teleported long-range CNOT and via the SWAP ladder — so the depth and
approximation-ratio contrast can be measured with routing as the only variable. This is the
flagship experiment of qh-13: a complete interaction graph Kₙ where every QAOA cost edge is
long-range, no ancilla-encoded constraints, no infeasible states.

Reuses the verified primitives from the QuantumLife teleport study by import:
- `QuantumLife/code/research_qtree_teleport.py::_teleport_cx(qc, ctrl, tgt, a1, a2, tel, k, feedforward=True)`
  — mutates `qc`; Bell-pair + 2 mid-circuit measures into `tel[2k],tel[2k+1]`; `feedforward=True`
  applies X/Z corrections via `qc.if_test()` (dynamic circuit), `feedforward=False` = herald
  (post-select `tel==00`).
- `QuantumLife/code/research_qtree_swaplr.py::_swap_cx(qc, lo, hi)` — mutates `qc`; SWAP up
  `lo..hi-1`, `CX(hi-1,hi)`, SWAP down; no ancilla, no measurement.

Environment confirmed: qiskit 2.3.1, qiskit-aer 0.17.2 (dynamic-circuit capable) — noiseless
Aer is the correctness/sign gate before any manual HW run.

## 2. Acceptance criteria (verbatim from epic §9, F1)

- **AC-1** (AC-F1.1) Generate a fixed-seed SK instance of `n` numbers (`n` a parameter) and
  compute its exact equal-sum-partition optimum classically (for the approximation ratio).
- **AC-2** (AC-F1.2) Build the QAOA cost layer `H = A(Σ nᵢ sᵢ)²` → `2A·nᵢnⱼ` ZZ couplings on
  the complete graph Kₙ, plus a standard transverse-field mixer, at parametrized depth `p`
  (default 1). Both `n` and `p` are exposed parameters.
- **AC-3** (AC-F1.3) Route the cost layer's long-range ZZ terms via the existing `_teleport_cx`
  (teleport arm) and via `_swap_cx` (SWAP arm) — same logical layer, routing is the only
  difference.
- **AC-4** (AC-F1.4) Report `qc.depth()` for both arms across n (or across bond distance) —
  show teleport constant vs SWAP O(distance). Deterministic, no QC.
- **AC-5** (AC-F1.5) Run both arms on a noiseless Aer simulator (dynamic circuits) and report
  the approximation ratio; confirm both arms are same-sign / logically equivalent ideally (the
  sign-check discipline from the teleport study §4b).
- **AC-6** (AC-F1.6) Real-hardware run(s) on a current Heron backend, submitted manually by the
  user (code emits circuits + run harness; user runs on QC), calibration recorded in the run
  JSON.
- **AC-7** (AC-F1.7) Persist run outputs as JSON under `number-partitioning/research_runs/`.

## 3. Out of scope (deferred)

- Any other NP problem from the qh-13 map (knapsack, TSP, MIS, coloring) — later epic targets.
- Penalty ancillas, one-hot encodings, infeasible-state handling — SK has none by design.
- QAOA hyperparameter optimization beyond a coarse grid needed to get a non-trivial approx
  ratio; multi-`p` sweeps as a study (parameter exists, tuning study is F2/later).
- The web demo, results writeup, and honest-verdict aggregation — those are F2.
- Automated backend submission — HW runs are manual (epic §3).

## 4. Design / approach

### 4.1 Problem encoding
- Instance: `n` integers `{aᵢ}` from a fixed-seed RNG (`--seed`), range parametrized.
- Spins `sᵢ ∈ {±1}` map to qubits: `|0⟩ = +1`, `|1⟩ = −1` (standard Z eigenbasis).
- Objective `H = A·(Σᵢ aᵢ sᵢ)²`. Expand: `H = A·Σᵢⱼ aᵢaⱼ sᵢsⱼ = A·Σᵢ aᵢ² + 2A·Σ_{i<j} aᵢaⱼ sᵢsⱼ`.
  Drop the constant `A·Σaᵢ²` for optimization; the Ising coupling is `Jᵢⱼ = 2A·aᵢaⱼ` on the
  complete graph K_n (no linear `h` term). `A` defaults to 1.
- Exact optimum (AC-1): brute-force all `2ⁿ` sign assignments (n≤~16 trivial; n=12 → 4096),
  record min `H` and the minimizing partition. This is the denominator of the approx ratio.

### 4.2 QAOA circuit (AC-2)
- `p` layers. Per layer: cost unitary `U_C(γ) = Π_{i<j} exp(-i γ Jᵢⱼ Zᵢ Zⱼ)` then mixer
  `U_M(β) = Π_i exp(-i β Xᵢ)` = `RX(2β)` on every qubit. Initial state `H⊗n |0⟩`.
- Each ZZ term uses the standard identity `exp(-i θ Zᵢ Zⱼ) = CX(i,j)·RZ(2θ, j)·CX(i,j)` — so
  **every** cost edge costs **two** long-range CNOTs plus one local `RZ`. This is where routing
  bites: on K_n that is `n(n−1)` long-range CNOTs per cost layer.
- Angles `(γ, β)` per layer: for the PoC, obtain them by a coarse classical grid search over
  the noiseless *logical* circuit (bare `CX`, no routing) maximizing the approx ratio, then
  reuse the SAME `(γ, β)` for both routed arms. Angle-finding is not the experiment; routing is.

### 4.3 The two arms (AC-3) — routing is the only difference
Build one **logical** cost layer (list of `(i, j, θ_ij)` ZZ terms + mixer). Two routers consume
the identical list:
- **Teleport arm:** each ZZ's two long-range CNOTs routed via `_teleport_cx`. Layout spins on a
  linear qubit line (positions `0..n−1`); a ZZ `(i,j)` bonds qubits at those positions with an
  ancilla pair. Ancilla budget: allocate 2 ancilla qubits and **reset between edges** (dynamic
  reset) so one `(a1,a2)` pair serves all edges sequentially — keeps qubit count `n + 2` rather
  than `n + n(n−1)`. `feedforward = not herald` (mirror teleport.py:254 call convention).
- **SWAP arm:** each ZZ's two long-range CNOTs routed via `_swap_cx(qc, lo, hi)` with
  `lo,hi = sorted(pos_i, pos_j)`. No ancilla, no measurement. Depth grows O(distance).

Both arms apply the same `(i,j,θ)` list on the same initial state → a noiseless simulator MUST
give the same objective/sign; any divergence is a routing/implementation bug (the §4b discipline).

### 4.4 Depth report (AC-4)
For each arm, build the cost-layer circuit at a range of `n` (and/or bond distance `d`),
transpile to a **linear/heavy-hex coupling map** with `generate_preset_pass_manager(optimization_level=3, ...)`
(mirroring teleport.py:422 / swaplr.py:333), and read `qc.depth()`. Emit a table
teleport(flat) vs SWAP(O(distance)). Deterministic, zero QC. This is the defensible advantage.

### 4.5 Noiseless simulation (AC-5)
- Use `AerSimulator()` directly (supports `if_test`/dynamic circuits and reset). Append
  `qc.measure_all()` (or measure into a genome-style creg), run at `--shots`, collect
  bitstrings.
- For each sampled bitstring compute `H`, take the best (and mean) → approximation ratio
  `= H(best sample) / H(optimum)` and `⟨H⟩/H(optimum)`.
- Sign check: also run the **logical** (bare-CX, unrouted) circuit and both routed arms in Aer;
  assert all three agree on the objective within shot noise. Record the comparison.
- Herald branch (teleport): when `--herald`, drop feed-forward and post-select `tel==00` before
  computing energies, matching the teleport study.

### 4.6 Hardware harness (AC-6) — manual
- Provide a `--backend <name>` path that transpiles each arm's circuit to the ISA (reuse
  `pipeline_common.connect` / preset pass manager as the teleport/swap runners do) and runs via
  the same Sampler path `run_hw()` uses (`pipeline_common`), chunked by `SHOTS_PER_JOB`.
- The user invokes this manually on QC (epic §3); the script writes the run JSON. Do not
  auto-submit in any default/sim path. Record live calibration (2q err, readout err, dead
  qubits) into `meta.calibration`, as teleport.py:520-551 does.

### 4.7 Angles / determinism
- All randomness (instance, angle grid) seeded via `--seed`. No wall-clock in the objective.

## 5. Inherited epic decisions (do not re-litigate)

- Reuse primitives by import, never copy (epic §3).
- Pure SK, no ancilla-encoded constraints (epic §3).
- `n`, `p` are parameters, default small (epic §3 / Q4).
- Noiseless-sim + sign-check before any claim (epic §3, §4b discipline).
- Verdict either-way — teleport may lose on fidelity while winning depth; F1 just produces the
  numbers, F2 writes the verdict (epic §3).
- Run JSONs under `number-partitioning/research_runs/` (epic §3).

## 6. File plan (concrete paths)

All new code strict-typed (`from __future__ import annotations`, full type hints), PSR-N/A
(Python); follow the style of the QuantumLife `research_qtree_*` scripts.

| Path | Change | Notes |
|------|--------|-------|
| `number-partitioning/array/sk_instance.py` | NEW | SK instance generator + exact brute-force optimum. `make_instance(n, seed, lo, hi) -> list[int]`; `ising_couplings(a, A=1.0) -> dict[(i,j),float]`; `brute_force_optimum(a, A) -> tuple[float, str]`. AC-1. |
| `number-partitioning/array/qaoa_sk.py` | NEW | Main script. Builds logical cost layer `build_cost_terms(couplings, gamma) -> list[(i,j,theta)]`; mixer; `route_teleport(qc, terms, layout, anc, tel, herald)` and `route_swap(qc, terms, layout)` consuming the identical term list; `build_circuit(arm, n, p, angles) -> QuantumCircuit`. Imports `_teleport_cx`, `_swap_cx` from `QuantumLife/code`. AC-2, AC-3. |
| `number-partitioning/array/depth_report.py` | NEW | Sweep `n`/distance, transpile both arms, emit `qc.depth()` table (stdout + JSON). AC-4. |
| `number-partitioning/array/run_sk.py` | NEW | Driver: argparse, angle grid-search on logical circuit, noiseless `AerSimulator` run of both arms + sign check, approx-ratio computation, JSON writer; `--backend` manual-HW path. AC-5, AC-6, AC-7. |
| `number-partitioning/research_runs/` | NEW DIR | Output run JSONs (created on first run). AC-7. |
| `number-partitioning/array/__init__.py` or `sys.path` shim | NEW | Make `QuantumLife/code` importable (add its path); mirror how repo scripts import siblings. |

Import reuse (no copy): `_teleport_cx` (research_qtree_teleport.py:201), `_swap_cx`
(research_qtree_swaplr.py:173). Transpile via `generate_preset_pass_manager`
(teleport.py:422). HW Sampler via `pipeline_common` (teleport.py:415-442).

## 7. Run-JSON schema (AC-7)

Mirror the teleport study schema (`meta` + per-run detail) so the existing tooling/voice
carries over. Top-level `meta`: `project="number-partitioning"`, `study="sk-qaoa-teleport-routing"`,
`arm` (`teleport`|`swap`|`logical`), `n`, `p`, `A`, `angles`, `couplings`, `layout`, `backend`,
`sim` (bool), `herald`, `shots`, `seed`, `n_qubits`, `n_ancillas` (2 for teleport, 0 for swap),
`logical_depth`, `optimum`, `optimum_partition`, `timestamp`, `calibration` (HW only).
Results block: `approx_ratio_best`, `approx_ratio_mean`, `best_partition`, `energy_hist`,
`sign_check` (`{logical, teleport, swap}` objective agreement). Depth report JSON: `arm`,
`n`/`d` sweep, `depth` list.

## 8. Manual verification

- **AC-1:** run `sk_instance.py` at `--seed 0 --n 12`; print instance + brute-force optimum;
  spot-check the optimum against a hand-computed small case (n=4).
- **AC-2/AC-3:** print both arms' circuits for n=4 (`qc.draw`); confirm teleport arm contains
  `if_test`/mid-circuit measures and the swap arm contains SWAP ladders; confirm both encode the
  same `(i,j,θ)` term list.
- **AC-4:** run `depth_report.py`; eyeball teleport depth ≈ constant across `n`, SWAP depth
  rising ~linearly with distance.
- **AC-5:** run `run_sk.py --sim`; confirm `sign_check` reports logical/teleport/swap objectives
  agree within shot noise (the §4b gate); read the two approx ratios.
- **AC-6:** (user, manual) `run_sk.py --backend <heron>` submitted by hand on QC; confirm a run
  JSON with `calibration` populated lands in `research_runs/`.
- **AC-7:** confirm each invocation writes a timestamped JSON under
  `number-partitioning/research_runs/`.

## 9. Risks / notes

- **Ancilla reset in Aer:** `reset` inside dynamic circuits must simulate correctly in Aer
  0.17.2 — verify the reuse-2-ancillas approach on n=4 before scaling; fall back to 2 ancillas
  per edge if reset misbehaves (documented trade-off, not a silent change).
- **MCM noise budget (the real open question):** K_n → `n(n−1)` teleport CNOTs → many MCMs; on
  HW teleport may lose approx ratio to SWAP even with the depth win. That either-way outcome is
  the contribution (epic §3) — F1 must report it honestly, not engineer around it.
- **Angle transfer:** angles found on the logical circuit are reused for both arms; valid on
  noiseless sim (same objective), and correct for the depth comparison; HW angle drift is a
  known caveat to note, not fix.

## 10. Implementation tasks (order)

1. `sk_instance.py` — instance gen + brute-force optimum (AC-1).
2. `qaoa_sk.py` — logical cost-term builder + mixer; teleport & swap routers over the shared
   term list; `build_circuit(arm,…)` (AC-2, AC-3).
3. `depth_report.py` — transpile + `qc.depth()` sweep table (AC-4).
4. `run_sk.py` — angle grid-search, noiseless Aer run of both arms + sign check, approx-ratio,
   JSON writer (AC-5, AC-7).
5. `run_sk.py --backend` manual-HW path + calibration capture (AC-6).
6. Manual verification pass (§8).

## 11. Open questions — RESOLVED (all defaults accepted 2026-08-26)

- [x] Q1: **Ancilla strategy** = reuse 2 ancilla qubits with dynamic `reset` between edges
  (width `n+2`); fall back to 2-per-edge per §9 only if Aer reset misbehaves.
- [x] Q2: **Qubit layout** = linear line positions `0..n−1` for the PoC (SWAP distance = index
  gap); heavy-hex anchor list adopted when the manual HW run is set up.
- [x] Q3: **Angle finding** = coarse seeded classical grid over `(γ,β)` on the logical circuit.
- [x] Q4: **`A` and integer range** = `A=1`, numbers in `[1, 2ⁿ)` (SK-typical), fixed `--seed`.
