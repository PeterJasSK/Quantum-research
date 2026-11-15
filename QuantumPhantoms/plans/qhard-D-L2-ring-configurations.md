# Q-HARD addendum — modular ring configurations for R5 / R6a / R6b (stage D → L2)

**Parent:** [feature-QHARD-heron-r2-routes-to-L1prime-and-L2.md](feature-QHARD-heron-r2-routes-to-L1prime-and-L2.md) (Draft)
**Date:** 2026-11-10 · **Status:** Draft, configurations only. No pipeline code, no QPU, no circuit simulator.
**For builders:** build the modules of §2 once, then instantiate the configurations of §3. Do not build anything from §4.

> **Label for every number here:** desk estimate. Computed from fake-backend snapshots (not live calibration)
> and classical GF(2) algebra. Nothing is claimed to work. L2 stays "blocked" until a certified run exists.
> Paper facts marked **[verify]** come from a machine summary of the arXiv HTML, not from a read of the PDF.

---

## 1. Findings that change the parent plan

| # | Finding | Basis | Consequence |
|---|---|---|---|
| F1 | **R5 and R6 are one circuit family.** The published L2 experiment is a *cycle* of data qubits with dangling ancillas on degree-3 nodes, not a chain. A hexagon is the n = 12 member of that family. | Martiel et al. 2607.25941 v3 [verify] | One module set serves all three routes. R5 = (ring, depth 2, 0 T gates). R6 = (ring, depth ≈ n/2 or more, T-doped, checks). |
| F2 | **The parent plan's R6 numbers are out of date.** arXiv v3: 64 data + 12 ancilla qubits, depth 73, 2,644 CZ (2,336 computation + 308 ancilla), 314 T gates, post-selection 3.83 × 10⁻⁴, fidelity ≥ 0.349 (95 %), 93 % of first-order errors detected, rank-width ≥ 27. The plan has 70 + 27 qubits, 2,869 CZ, 5.9 × 10⁻⁴. | abstract (verbatim) + HTML summary [verify] | Correct §4.2, §4.3 and AC-8 of the parent plan. |
| F3 | **"Heron r2 is 2 to 2.5× short" holds for `ibm_marrakesh`, not for r2.** Best 64-ring mean CZ error in the fake snapshots: marrakesh 0.334 %, kingston 0.186 %, aachen 0.171 % (all r2); boston 0.134 %, pittsburgh 0.171 % (r3). | own enumeration of 6,026 64-cycles per backend | The backend choice is worth more than any circuit trick. `ibm_aachen` (r2) is at r3 level in CZ error. Needs a live calibration check by Peter. |
| F4 | **Entanglement saturates at half the published depth.** On a 64-ring, CZ brickwork with the paper's single-qubit set {√X, S√X} grows half-arc entropy at the maximal rate: 16 at depth 16, 24 at depth 24, min 29 at depth 32, min 30 at depth 40 and no gain after. Published depth is 73. | own GF(2) tableau run, 1 seed, contiguous arcs + 300 random bipartitions | A lean ring of depth 36 to 40 (1,152 to 1,280 CZ) has the same cut entropy as the 2,336-CZ circuit. What the extra depth buys (T capacity, flat spectra, anticoncentration) is **not known** and is the main open question (G1). |
| F5 | **The single-qubit gate set decides the cost by 2×.** With uniformly random single-qubit Cliffords the same brickwork reaches min entropy 13 at depth 32 and 29 only at depth 73. | same run | Never use uniform random 1q Cliffords in the skeleton. |
| F6 | **Theorem-1 game sizes do not exist on heavy-hex.** The proven depth-D bound is for n = 6D, D odd (18, 30, 42 …), all ≡ 2 mod 4. Every heavy-hex cycle built from hexagons has length ≡ 0 mod 4 (12, 20, 24, 28, 32, 36 …). | Daniel et al. 2110.04277 [verify, Theorem 1 and Remark 2 not read verbatim]; own cycle enumeration | The native game needs either the general-even-n bound (Remark 2) or the spacer trick of config R5-Y18. |
| F7 | **The hexagon (n = 12) beats depth-1 classical circuits only.** Reported bounds for 6 ≤ n < 18: β₁ = 4/5, β₂ = 1. A depth-2 classical circuit wins the n = 12 game perfectly, and the quantum circuit also has depth 2. | 2110.04277 Remark 2 [verify] | R5 on one hexagon is a weak L1.5. The 20-cycle (two hexagons) is the smallest size that can exclude depth 3. |
| F8 | **T count is the binding hardness axis for a lean circuit.** Stabilizer-decomposition cost is conjectured ≈ 2^(0.228 t); the paper says simulators reach about 75 T gates [verify]. t = 200 gives 2⁴⁶. | 2607.25941 [verify] | A lean config must still carry ≥ 200 T gates. Density needed at depth 36: 8.7 % of spacetime sites, against 6.7 % in the paper. Whether the checks allow it is unknown (G2). |

---

## 2. Modules

Each module is a pure function from parameters to a circuit fragment or a number. No mid-circuit measurement,
reset or feed-forward anywhere (D-SCALE lint rule 1).

| ID | Module | Parameters | Output | Notes |
|---|---|---|---|---|
| M1 | `ring_layout` | `backend`, `n`, `rank_by` (`cz` \| `cz+ro`), `n_anc` | ordered cycle of physical qubits + dangling ancillas (off-cycle neighbours of degree-3 cycle nodes) | Cycles = XOR of connected hexagon sets with a single-cycle boundary. Available n: 12, 20, 24, 28, … (step 4). Max ancillas: 6 at n = 12, 9 at 20, 14 at 28, 18 at 36, 22 at 44, 30 at 60 to 72. |
| M2 | `skeleton` | `n`, `depth`, `oneq_set` (`sx_ssx` only), `seed` | H layer, then `depth` × (1q layer from {√X, S√X}, CZ brickwork alternating even/odd bonds, periodic) | `depth = 0` gives the product state; `depth = 2` with no 1q layer gives the cyclic cluster state. |
| M3 | `cut_entropy` | skeleton, `n_random` | min half-arc entropy, min over random balanced bipartitions | GF(2) rank of the restricted stabilizer matrix minus subset size. Go rule for R6b: both ≥ 27. |
| M4 | `checks` | skeleton, ancilla map, `max_cz_per_anc` | spacetime Pauli checks, ancilla CZ list, list of spacetime sites where a Z-type rotation commutes with all checks | Paper: 12 ancillas, 308 CZ, found by decoder heuristics and randomised search [verify]. Builder starts from the GF(2) kernel of propagated single-wire insertions. |
| M5 | `t_doping` | allowed sites from M4, `t_target`, `seed` | T (or ZZ-rotation) placements | Returns the achieved t. Fails loudly if `t < t_target`. |
| M6 | `game_readout` | `n`, `input_set` | per-input X / Y basis layer and the parity win rule | Stabilizer-submeasurement game: bit 0 → X, bit 1 → Y; inputs on alternate sites. Exact rule and input sets to be transcribed from 2110.04277 Sec. III and VI. |
| M7 | `acceptance_model` | `backend`, layout, CZ count | predicted post-selection rate and raw sample fidelity | Desk model below. Replaced by a stabilizer simulation with Pauli noise in the build. |
| M8 | `certify` | accepted shots of the Clifford reference (t = 0) | direct fidelity estimate, doping-loss term, 95 % lower bound | Follows the paper: DFE on the stabilizer state, Monte-Carlo doping loss. Pauli-noise assumption → gate twirling required. |

**Desk acceptance model (M7).** One calibration point: 2,644 CZ accepted at 3.83 × 10⁻⁴ on a ring with mean CZ
error 0.134 % gives an effective loss of 0.298 % per CZ, i.e. κ = 2.2 × the mean CZ error (covers readout,
idle and 1q errors). Acceptance ≈ exp(−κ · e_cz · N_CZ). Raw fidelity of accepted samples ≈
exp(−0.07 · κ · e_cz · N_CZ) × (1 − e_ro)^n. The model reproduces the paper's readout-mitigated 0.55 (predicts
0.58). It is a one-point fit and nothing more.

---

## 3. Configurations to build

```yaml
# All: ring topology, oneq_set sx_ssx, all measurement at the end.
R5-H12:        {modules: [M1, M2, M6], n: 12, depth: 2, t: 0, n_anc: 0, cz: 12}
R5-D20:        {modules: [M1, M2, M6], n: 20, depth: 2, t: 0, n_anc: 0, cz: 20}
R5-Y18:        {modules: [M1, M2, M6], n: 20, players: 18, spacers_measured_in_Y: 2, depth: 2, cz: 20}
R5-LADDER:     {modules: [M1, M2, M6], n: [12, 20, 28, 36, 44], depth: 2}          # loss-per-CZ meter
R6a-S36:       {modules: [M1..M5, M7, M8], n: 36, depth: 22, t: [0, 5, 40], n_anc: 8,  cz_total: ~480}
R6a-S44:       {modules: [M1..M5, M7, M8], n: 44, depth: 26, t: [0, 5, 60], n_anc: 10, cz_total: ~670}
R6b-LEAN64:    {modules: [M1..M5, M7, M8], n: 64, depth: [36, 40], t: ">=200", n_anc: 12, cz_total: ~1350}
R6b-PUB64:     {modules: [M1..M5, M7, M8], n: 64, depth: 73, t: 314, n_anc: 12, cz_total: 2644}   # reference
```

| Config | Level it can earn | Pass rule | What it is for |
|---|---|---|---|
| R5-H12 | L1.5 against depth-1 classical circuits only | win > 0.80 by 3σ, raw counts | First rung. Runs on all 21 hexagons in one job as a chip map. |
| R5-D20 | L1.5 against depth-3, **if** the general-even-n bound holds | win > 0.80 by 3σ | Smallest native size with a useful separation. Bound not verified. |
| R5-Y18 | L1.5 against depth-3 under Theorem 1 | win > 0.80 by 3σ | Two ring qubits measured in Y contract the 20-ring to an 18-ring cluster state. The outcome-dependent byproduct is a Pauli, so it is a sign fix in post-processing; the fixed S-type basis change is compiled in. Whether Theorem 1 survives two helper nodes must be argued. |
| R5-LADDER | none (calibration) | — | Fit λ = −ln F_n / n from the game score. This is the measured "effective loss per CZ" that the parent plan assumes. It gates every R6 run: predicted acceptance = exp(−λ · N_CZ). |
| R6a-S36 / S44 | "L2 protocol, below threshold" | certified fidelity bound > 0 at 95 %, and samples agree with exact simulation | Classically checkable (t ≤ 60 is within stabilizer-decomposition reach; n = 36 fits a statevector cluster). Validates M4, M5, M8 and the acceptance model. |
| R6b-LEAN64 | **L2 candidate** | certified bound > 0 at 95 % with min cut entropy ≥ 27 and t ≥ 200 | The only configuration here that can reach L2 for stage D. Hardness of the reduced depth is unproven (G1). |
| R6b-PUB64 | L2 (published) | as published | Reference point for the model; affordable on r3 only. |

**Predicted post-selection rate (desk model, fake snapshots):**

| Config | N_CZ | marrakesh (r2) | kingston (r2) | aachen (r2) | boston (r3) | pittsburgh (r3) |
|---|---|---|---|---|---|---|
| R6a-S36 | 480 | 2.9 × 10⁻² | 0.14 | 0.17 | 0.24 | 0.17 |
| R6a-S44 | 670 | 7.3 × 10⁻³ | 6.5 × 10⁻² | 8.0 × 10⁻² | 0.14 | 8.0 × 10⁻² |
| R6b-LEAN64 | 1,350 | 4.9 × 10⁻⁵ | 4.0 × 10⁻³ | 6.2 × 10⁻³ | 1.9 × 10⁻² | 6.2 × 10⁻³ |
| R6b-PUB64 | 2,644 | 3.6 × 10⁻⁹ | 2.0 × 10⁻⁵ | 4.8 × 10⁻⁵ | 3.8 × 10⁻⁴ (fit point) | 4.8 × 10⁻⁵ |

Raw fidelity of accepted R6b-LEAN64 samples (same model): aachen ≈ 0.38, boston ≈ 0.51, marrakesh ≈ 0.17,
kingston ≈ 0.12 (its ring readout error is 2.6 %). At about 2.5 × 10⁵ shots per QPU-minute (from the paper's
1,389 samples in 14.5 minutes [verify]), a certificate needing ≈ 15,000 accepted reference shots costs about
10 minutes on aachen, 3 minutes on boston and 20 hours on marrakesh.

**Recommended route to L2 for stage D:** R5-LADDER → R6a-S36 → R6a-S44 → R6b-LEAN64, on `ibm_aachen` (r2) or
`ibm_boston` (r3). `ibm_marrakesh` carries R5 and R6a only. Subjective probability that R6b-LEAN64 returns a
certified bound > 0 with t ≥ 200: ≈ 0.15 to 0.20 on aachen, ≈ 0.35 on boston, < 0.02 on marrakesh. Probability
that a referee accepts the lean depth as L2 is a separate, lower number that G1 has to settle.

---

## 4. Impossible configurations (do not build)

| # | Configuration | Why it cannot work | Basis |
|---|---|---|---|
| X1 | R6b-PUB64 on `ibm_marrakesh` | Acceptance ≈ 4 × 10⁻⁹: one sample per 18 hours of shots | desk model |
| X2 | R6b-LEAN64 on `ibm_marrakesh` with a certificate | Acceptance 5 × 10⁻⁵; the reference DFE alone needs ≈ 3 × 10⁸ shots (≈ 20 h) | desk model |
| X3 | R6 on an open chain | One bond per cut instead of two: half the entangling rate, twice the depth and CZ count for the same cut entropy | light-cone count |
| X4 | Skeleton with uniform random 1q Cliffords at lean depth | Min half-arc entropy 13 at depth 32 (needs ≥ 27) | own GF(2) run (F5) |
| X5 | Lean ring with t < 200, or any ring with t ≤ 75 called "hard" | Stabilizer decomposition 2^(0.228 t) < 2⁴⁶; simulators already reach ≈ 75 T | 2607.25941 [verify] |
| X6 | Hardness ring with n < 58 | Cut entropy cannot reach 27 (max is n/2 minus a few) | counting |
| X7 | Native Theorem-1 game ring (n = 18, 30, 42) on heavy-hex | No cycle of length ≡ 2 mod 4 exists | own enumeration (F6) |
| X8 | R5-H12 sold as a separation against depth ≥ 2 | β₂ = 1 for n < 18; the quantum circuit itself has depth 2 | 2110.04277 [verify] |
| X9 | Game rings with n ≥ 44 on r2 | State fidelity × readout ≈ 0.56 to 0.62, win ≈ 0.78 to 0.81 against 0.80 | desk estimate, win = (1 + F)/2 [verify] |
| X10 | R6b on `ibm_kingston` | Ring readout error 2.6 % → raw sample fidelity factor 0.18 | fake snapshot |
| X11 | Readout-error mitigation in a game score or in certified samples | Changes the claim; the game paper's own raw score (79.4 %) fails where its corrected score passes | 2110.04277 Table 1 |
| X12 | Whole-chip constant-depth ring / cluster sampling as L2 | Treewidth ≤ 4; parent plan R17 | parent §4.2 |

---

## 5. Research gaps and connections

| # | Gap or connection | Smallest step that closes it |
|---|---|---|
| G1 | What does depth 73 buy over depth 36? Cut entropy is the same (F4). Candidates: T capacity of the code, flatter entanglement spectra against truncated MPS, anticoncentration. | Read the hardness section of 2607.25941 in the PDF. Then compare depth 36 and 73 in M3 on entanglement *spectrum* of the doped state at n ≤ 24, not only the stabilizer entropy. |
| G2 | T capacity at lean depth: do the checks leave ≥ 200 commuting sites in 36 layers? | Run M4 + M5 at n = 64, depth 36 and 40, report achieved t against the number of ancillas (trade detection for T sites). |
| G3 | Game bound for n ≡ 0 mod 4. | Read Remark 2 and Sec. VI of 2110.04277. If the general-even-n bound is not proven, use R5-Y18. |
| G4 | The hexagon game score as a loss meter for deep circuits. A depth-2 circuit does not see idle errors or crosstalk that a depth-40 ring accumulates. | Compare λ from R5-LADDER with λ fitted on R6a-S36 / S44 acceptance. Agreement within a factor 1.5 validates the meter. |
| G5 | Adversary list in the parent plan (§4.1, L2 row) lacks rank-width contraction and Clifford-augmented MPS. | Add both. The paper's own hardness metric is rank-width. |
| G6 | Unconditional + conditional evidence on the same qubits. R5 (proven, shallow adversary) and R6b (conjectured, any adversary) share layout, skeleton module and job family. | Run R5-D20 on two hexagons of the R6 ring in the same session and report both with their adversaries. |
| G7 | Live calibration of `ibm_aachen` and access to it. All backend numbers are fake snapshots. | Peter checks live properties and plan access. Parent Q3 becomes "which backend", not "r2 or r3". |
| G8 | Stage-D meaning. Ring = lineage skeleton, T gates = mutations, checks = integrity of the lineage record. The certificate is about the device, never the tumour. | Wording only; keep the honesty gate. |

---

## 6. Method note

- Cycle enumeration: connected unions of up to 9 hexagons of the 156-qubit heavy-hex map (35,536 face sets),
  kept when the XOR boundary is one simple cycle; ranked by mean CZ and readout error from
  `qiskit_ibm_runtime.fake_provider` targets.
- Entropy: 64-qubit ring, stabilizer tableau without phases, entropy = GF(2) rank of the stabilizer matrix
  restricted to the subset minus the subset size; contiguous arcs of length 27 to 32 and 300 random balanced
  bipartitions; one seed.
- Papers: abstract of 2607.25941 read verbatim; body and all of 2110.04277 beyond Sec. II through a machine
  summary. Every such item carries [verify].
