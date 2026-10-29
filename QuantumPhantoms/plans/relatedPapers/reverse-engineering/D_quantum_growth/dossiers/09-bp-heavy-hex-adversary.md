# #09 — Belief-propagation simulator of heavy-hex circuits (Tindall)

**Letter:** D ([`D_quantum_growth`](../README.md)) · **Priority:** ★★ · **Kind:** classical · **Papers:** HW04 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

<!-- The method in plain words: what problem it solves, the core idea. -->
Tindall et al. [HW04] simulate IBM's 127-qubit Eagle kicked-Ising experiment classically with a tensor network that has one tensor per qubit and one bond per coupling edge, kept in a canonical gauge by belief propagation (BP): messages along edges are iterated to a fixed point and give the environment for truncation and expectation values. It is exact on trees and accurate when correlations are locally tree-like. Here it is the **adversary**: the measured number of how small a bond dimension reproduces each D circuit, i.e. the measured "no L2 claim".

## Equations

<!-- The equations we re-implement, with symbols defined. -->
```text
state:            tensors T_i[p, legs per edge], bond weights lambda_e (Vidal form)
2q gate on (i,j): weight the other legs by lambda, apply the gate, SVD, keep chi, divide the weights out (simple update)
BP messages:      m_{i->j}[x,x'] = sum_{p,b} T_i[p,x,b] conj(T_i[p,x',b']) prod_{k != j} m_{k->i}[b_k,b_k']   (normalised, iterated)
BP gauge:         m_{i->j} = P_i P_i^+, m_{j->i} = P_j P_j^+, P_i^T P_j = U L W^+ ;  X_i = pinv(P_i^T) U,  X_j = (W^+ pinv(P_j))^T ;  new bond L
expectation:      <O_i> from T_i contracted with incoming messages;  <O_i O_j> from the two edge environments
kicked Ising (HW04 Eq. 1):  U = prod_<vv'> exp(i pi/4 Z Z) prod_v exp(-i theta_h X / 2)
fidelity_vs_sim (plan Q6):  1 - 1/2 mean |BP - exact| over every <Z_i>, nearest-neighbour <Z_i Z_j>, <X_i X_j>, clipped to [0,1]
```

## Parameters

<!-- Every parameter with its published value/range and source (paper code, section, table). -->
chi ∈ {2, 4, 8, 16} for D circuits; proof-of-concept Tindall sweep chi ∈ {2, 4, 8}, θ_h ∈ {π/4, 1.0} for the exact comparison and 5 θ_h points for the ⟨Z₆₂⟩ sweep (cut down on request: the full 5-χ, 9-θ sweep took more than an hour with other jobs on the machine). Eagle coupling map from FakeSherbrooke (geometry only), 5 Trotter steps, BP ≤ 60 iterations, tol 10⁻¹⁰.

## Paper's claimed result

<!-- The single published number or figure we will reproduce, with exact reference. -->
[HW04] p. 2: "For short circuit depths n < 6 our method gives perfect agreement with the exact simulation" (the light cone does not reach round the loops); BP error grows at larger depth and shrinks with the number of hexagons at fixed χ.

## Our reproduction (number + figure)

<!-- Our number vs the paper's, agreement, figure in ../figures/, run id. Quantum: label the sim mode. -->
`python -m D_quantum_growth.repro.tindall_kicked_ising` (figure `tindall_magnetisation.png`; classical, no noise model). **Proof of concept**, not a full reproduction.

Max |BP − exact light-cone statevector| of ⟨Z⟩ over 3 sites (0, 1, 2; light cone ≤ 20 qubits), 5 steps:

| θ_h | χ = 2 | χ = 4 | χ = 8 |
|---|---|---|---|
| π/4 | 3.8·10⁻¹ | 7.7·10⁻² | 5.7·10⁻³ |
| 1.0 | 6.9·10⁻¹ | 2.1·10⁻¹ | 4.3·10⁻² |

The error falls monotonically with χ, but the 10⁻³ level the paper's "perfect agreement" implies is **not reached at χ ≤ 8** (this repro caps χ at 8; the paper uses far larger bond dimensions). ⟨Z₆₂⟩ sweep over θ_h = 0, π/8, π/4, 3π/8, π/2 at χ = 8: +1.000, +0.922, +0.530, +0.102, +0.007. Separate sanity check: on small random loopy circuits BP is exact at χ ≥ 4 for shallow depth and keeps a ~10⁻² loop error at depth 5 on a ring with chords, as expected for BP.

## Adaptation

<!-- How it is adapted to lungs, 3-D, certification and our contracts. -->
`src/bp.py` runs on every D circuit (`python -m D_quantum_growth.src.bp --run <run_dir>`, also called by `grow`): lineage generation blocks, q-machine step, and the QCA t_max circuit (transpiled to the FakeMarrakesh coupling map so every gate is an edge). Output `simulability_report` (circuit_hash, method, bond_dim, fidelity_vs_sim, runtime_s). Measured (run `20261029-112717-grow-ideal`, `…-112719-grow-heron`):

| circuit | smallest χ with fidelity_vs_sim ≥ 0.99 | fidelity at χ = 2 / 4 / 8 / 16 |
|---|---|---|
| lineage blocks (divide_Z, divide_X, chsh) | 2 | 1.000 |
| q-machine step | 2 | 1.000 |
| QCA, 21-qubit patch, t = 10 (ideal run) | **none ≤ 16** | 0.799 / 0.830 / 0.881 / 0.899 (χ = 16: 20 min) |
| QCA, 12-qubit hexagon, t = 10 (Heron run) | **none ≤ 16** | 0.888 / 0.949 / 0.960 / 0.956 |

The lineage and q-machine circuits are tiny (3 and 2 qubits) and BP-trivial; they are not evidence of anything beyond their size. The QCA circuits are not reproduced to 0.99 by BP up to χ = 16: the hexagon saturates near 0.96 at χ ≥ 8 (single 12-ring plus loop correction), the full patch is still rising at χ = 16. This says BP is not a cheap classical shortcut for these QCA circuits at this depth; it does **not** establish quantum advantage (an exact 21-qubit statevector is trivial).

## Verdict

<!-- integrated | rejected (with reason). Claim level for quantum targets. -->
**dissected**, used as the adversary; the reproduction is a proof of concept (monotone convergence, paper's exact-agreement level not reached at χ ≤ 8). Classical method, claim level n/a. The explicit BP gauge step is implemented (`BPTN.gauge`) and runs in every simulation; for expectation values it does not change results (BP environments are gauge-invariant).

## What to reuse next

<!-- Pointers for downstream letters / INT. -->
`bp.py` is a drop-in adversary for any circuit whose 2-qubit gates sit on coupling edges; raising χ and the sweep size is the first step to a full reproduction of HW04's Fig. 4. INT: run it on B's real founder circuit and on G's receipts' circuits.
