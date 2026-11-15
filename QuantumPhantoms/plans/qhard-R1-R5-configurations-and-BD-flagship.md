# Q-HARD addendum 2 — modular configurations for R1 to R5, and the strongest honest B and D available now

**Parent:** [feature-QHARD-heron-r2-routes-to-L1prime-and-L2.md](feature-QHARD-heron-r2-routes-to-L1prime-and-L2.md) (Draft)
**Sibling:** [qhard-D-L2-ring-configurations.md](qhard-D-L2-ring-configurations.md) (R5 / R6 ring family, modules M1 to M8)
**Date:** 2026-11-10 · **Status:** Draft, configurations only. No pipeline code, no QPU, no circuit simulator.

> **Label for every number here:** desk estimate from fake-backend snapshots (not live calibration) and
> classical NumPy optimisation. Nothing is claimed to work. Items marked **[verify]** are not checked against
> the source paper. A bound marked *numerical* can justify more simulation, never a claim.

---

## 1. Findings

| # | Finding | Basis | Consequence |
|---|---|---|---|
| F1 | **The tick-clock needs no routing.** A degree-3 qubit as memory with its 3 neighbours as outputs is exactly the L = 3 machine. Each step is a 1 → 2 qubit isometry (output qubit starts in \|0⟩), which needs ≤ 2 CZ [verify, Iten et al. 1501.06911]; the first step acts on a known state and needs 1. Total ≤ 5 CZ on 4 qubits, against the parent plan's ≤ 9 CZ on a path. | circuit counting | R1 becomes a tile. |
| F2 | **24 clocks fit at once.** 48 degree-3 nodes; 24 disjoint 4-qubit stars found by randomised greedy (lower bound) = 96 qubits. | own packing run | One circuit gives a per-tile L1′-T map. This answers the "per-tile L1" gap of the best live run. |
| F3 | **Optimal `001` instrument is simple.** Singular values: K₀ = (1, ½), K₁ = (√3/2, 0). p = 7/16 reproduced; classical 2-state value 8/27 reproduced. | own optimisation, 25 restarts | The instrument can be written in closed form and re-derived by hand before any claim. |
| F4 | **A 2-qubit memory may give a much larger gap than the parent plan assumed.** Own optimiser finds p(`00001`) = 0.632 for a 4-level memory. The classical 4-state one-tick bound of the published form ((L−1)/L)^L is 0.328. Parent R7 states the gap is ≈ 12 % of the bound. The two do not agree. | own optimisation, 12 restarts; bound form from 2402.16789 [verify] | Highest-value check in this file (G1). If 0.632 stands, R7 moves to the shortlist. |
| F5 | **Sequence choice is decisive.** With a qubit memory: `001` gap 0.141, `0011` gap 0.112, `001001` gap 0.104 (classical values numerical), `0001` gap 0.051, `011` gap negative (a 2-state machine emits it with certainty). | own optimisation | Only `001` has a proven classical bound and the largest gap. |
| F6 | **At most 64 Bell pairs exist on the chip.** Heavy-hex is bipartite with classes of 92 and 64 qubits, so the maximum matching is 64 pairs = 128 qubits. | own matching run + counting | R3 can run at twice the 64-qubit size reported by Seif et al. [verify], at CZ depth 2. |
| F7 | **R3 signal survives at full size.** Per-pair signal r (2 CZ, 2 readouts): median 0.946 marrakesh, 0.965 aachen, 0.976 boston. Per-qubit sample overhead 1/r² ≈ 1.12, 1.07, 1.05, against the memoryless bound of 2 quoted in the parent plan [verify] and the 1.33 ± 0.05 measured by Seif et al. | fake snapshots | Expect 1.1 to 1.35 on hardware. A few bad pairs kill a full-weight Pauli, so pairs must be selected. |
| F8 | **R4 is decided by the backend, and n = 12 is the only size.** Forecast ε on the best hexagon (parent formula, 86 layers): marrakesh 0.140, kingston 0.174, aachen 0.250, pittsburgh 0.262, boston 0.274. Threshold ≈ 0.16. Smaller rings (8, 10) are not native; larger rings (20) need a Haar-state preparation that is out of reach. | own hexagon ranking | R4 fails on marrakesh, passes on aachen / boston with ≈ 34 to 40 bits against 12 qubits (two-point linear reading of the paper's bound, crude). |
| F9 | **8 disjoint hexagons fit at once** (96 qubits). | own packing run | The hexagon game can run as a chip map in one circuit per input. |

---

## 2. Modules (added to M1 to M8 of the sibling file)

| ID | Module | Parameters | Output | Notes |
|---|---|---|---|---|
| M9 | `tile_layout` | `backend`, `shape` (`star4` \| `pair` \| `hexagon` \| `ring20`), `rank_by`, `max_tiles` | disjoint tiles, ranked by summed CZ + readout error | Packing numbers: 24 stars, 64 pairs, 8 hexagons. |
| M10 | `instrument` | `memory_qubits`, `seq` | Kraus pair (K₀, K₁), initial state, quantum value, classical bound, `rigour` | For `001`: closed form from F3. Others from the optimiser. |
| M11 | `clock_circuit` | instrument, tile, `identical_steps` (bool) | deferred-measurement machine: one isometry per step onto a fresh output qubit, all measured at the end | `identical_steps: true` applies the same 2-CZ isometry at every step (6 CZ). `false` compiles step 1 from the known input (5 CZ). Report both; a referee may ask for the first. |
| M12 | `rac_circuit` | `d` (2 \| 4), `n_inputs` | preparation per input string + measurement per question | d = 2: 0 CZ. d = 4: 1 CZ to prepare, ≤ 3 CZ to measure in the second basis. |
| M13 | `pair_layer` | pairs, `channel` (`programmed` \| `intrinsic`), hidden Pauli | Bell preparation, channel on the founder half, Bell measurement | `intrinsic` = the R6 ring's own twirled CZ layer acts as the channel. |
| M14 | `pauli_estimator` | Bell outcomes, Pauli support | eigenvalue estimate ± σ, fitted per-qubit overhead | Memoryless arm is a coded baseline for illustration; the bound it is compared with is a theorem, not that arm. |
| M15 | `ring_ansatz` | `n = 12`, `layers`, target state | trained RZZ brickwork on the hexagon, ansatz fidelity | Classical training only. 10,000 targets for a full run. |
| M16 | `xeb_bits` | measured ε, n | proven classical-bit lower bound | Constants to be transcribed from 2509.07255 Supplement [verify]. |

---

## 3. Configurations to build

```yaml
# R1 — temporal memory (stage D)
R1-STAR-001:   {modules: [M9, M10, M11], tile: star4, memory_qubits: 1, seq: "001", cz: "<=5", tiles: 1}
R1-TILE24:     {modules: [M9, M10, M11], tile: star4, seq: "001", tiles: 24, qubits: 96}      # per-tile map
R1-M2-00001:   {modules: [M9, M10, M11], memory_qubits: 2, seq: "00001", outputs: 5, cz: "50-100"}
# R2 — hand-off (stage B -> D)
R2-Q2:         {modules: [M12], d: 2, n_inputs: 2, cz: 0}
R2-Q3:         {modules: [M12], d: 2, n_inputs: 3, cz: 0}
R2-D4:         {modules: [M12], d: 4, n_inputs: 2, cz: "<=4"}
# R3 — sister-memory learning (stage D)
R3-LADDER:     {modules: [M9, M13, M14], pairs: [8, 16, 32, 48, 64], channel: programmed}
R3-CHIP64:     {modules: [M9, M13, M14], pairs: 64, qubits: 128, cz_depth: 2, channel: programmed}
R3-INTRINSIC:  {modules: [M1, M13, M14], pairs: 32, channel: intrinsic, source: "R6 ring CZ layer"}
# R4 — information supremacy (stage B -> D)
R4-HEX:        {modules: [M1, M15, M16], n: 12, layers: [40, 60, 86], circuits: 10000, shots_each: 1}
# R5 — see sibling file: R5-H12, R5-D20, R5-Y18, R5-LADDER; add:
R5-MAP8:       {modules: [M9, M2, M6], tile: hexagon, tiles: 8, qubits: 96}
```

| Config | Level | Classical bound (rigour) | Desk forecast | Pass rule | P (subjective) |
|---|---|---|---|---|---|
| R1-STAR-001 | L1′-T | 8/27 = 0.296 (proven) | p ≈ 0.40 marrakesh, 0.42 aachen, 0.425 boston | p > 0.296 by 3σ; ≈ 13σ at 4,000 shots | 0.88 |
| R1-TILE24 | L1′-T per tile | same | median tile as above; worst tiles unknown | ≥ 20 of 24 tiles pass at 3σ after Bonferroni | 0.70 |
| R1-M2-00001 | L1′-T, 4-state adversary | 0.328 (published form [verify]) | 0.632 ideal (own numerical); ≈ 0.49 at 75 CZ on marrakesh, ≈ 0.55 on aachen | p > 0.328 by 3σ | 0.45, conditional on G1 |
| R2-Q2 / Q3 | L1′-C, smallest | 0.75 (textbook [verify]) | 0.846 / 0.783 | above 0.75 by 3σ | 0.95 / 0.80 |
| R2-D4 | L1′-C, 2 qubits against 2 bits | 0.625 (textbook [verify]) | 0.75 ideal, ≈ 0.72 | above 0.625 by 3σ | 0.85 |
| R3-LADDER | L1′-L | per-qubit overhead 2 [verify] | overhead 1.1 to 1.35 | fitted overhead < 2 by 3σ | 0.60 |
| R3-CHIP64 | L1′-L at 128 qubits | same | full-weight signal on 64 selected pairs ≈ 0.02 (aachen); 5σ in ≈ 5 × 10⁴ shots | hidden Pauli sign recovered at 5σ, overhead < 2 | 0.45 |
| R3-INTRINSIC | L1′-L on a real process | same | not estimated | as R3-LADDER | 0.35 |
| R4-HEX | L1′-C, n = 12 | bits(ε) > 12 needs ε ≳ 0.16 [verify] | ε 0.14 marrakesh, 0.25 aachen, 0.27 boston | proven bits > 12 | 0.10 marrakesh, 0.40 aachen, 0.50 boston |
| R5-MAP8 | L1.5 against depth 1 | 0.80 [verify] | win ≈ 0.92 to 0.95 per hexagon | ≥ 6 of 8 hexagons above 0.80 by 3σ | 0.75 |

---

## 4. The strongest honest B and D available now

One session on one 156-qubit processor, `ibm_aachen` (r2) or `ibm_boston` (r3). Each line names its adversary.
No line says anything about the tumour; every certificate is about the device that generates the seed or the
process record.

**Stage B — the seed register**

| Step | Config | What the page may say if it passes |
|---|---|---|
| B-1 | R2-Q2 → R2-D4 | "The hand-off qubit carries more than one classical bit can" (dimension assumption stated). |
| B-2 | R4-HEX on the best hexagon | "The 12-qubit seed register solved a task that provably needs more than 12 classical bits" (forecast 34 to 40). |
| B-3 | R5-MAP8, then R5-D20 on the seed hexagons | "No depth-1 local classical rule reproduces these correlations", per hexagon, as a chip map. |
| B-4 | seed draw | Z-basis draw from the certified hexagon in the same job. The draw itself stays L0; the certificate sits next to it (parent Q10). |

**Stage D — the start of growth**

| Step | Config | What the page may say if it passes |
|---|---|---|
| D-1 | R1-TILE24 | "On 24 tiles a one-qubit division clock beat every one-bit clock" (per-tile L1′-T). |
| D-2 | R1-M2-00001 | "A two-qubit clock beat every four-state clock" (after G1). |
| D-3 | R3-CHIP64 | "With a sister memory on 128 qubits the growth channel was learned with a per-qubit overhead below the proven memoryless limit." |
| D-4 | R3-INTRINSIC → R6a → R6b-LEAN64 | "Certified fidelity > 0 on a 64-qubit, ≥ 200-T lineage circuit" (the only L2 line; see sibling file for its open gap). |

**Honest headline if all pass:** four unconditional quantum-over-classical resource separations (memory,
communication, learning, locality) on up to 128 qubits at once, plus one certified L2 attempt, in one session.
Rough joint probability that B-1, B-3, D-1 and D-3 all pass on aachen: ≈ 0.25. Adding B-2: ≈ 0.10. Adding D-4:
≈ 0.02. On `ibm_marrakesh` B-2 and D-4 are out; the rest stand.

**QPU time, order of magnitude:** R1, R2, R5 seconds each; R3 one to three minutes; R4 dominated by 10,000
distinct single-shot circuits (job overhead, not shots); R6 about ten minutes. Total 20 to 25 minutes.

---

## 5. Impossible configurations (do not build)

| # | Configuration | Why it cannot work |
|---|---|---|
| X1 | R1 on a path with the memory swapped along it, for L = 3 | Adds ≥ 3 CZ per move for nothing; the star needs none |
| X2 | R1 with L ≥ 4 on a star | Maximum degree is 3, so at most 3 fresh outputs touch the memory |
| X3 | R1 with sequence `011`, or `0001` as a headline | `011`: a 2-state machine emits it with certainty. `0001`: gap 0.05 |
| X4 | R1 claimed against 3-state machines | A 3-state machine emits `001` with certainty |
| X5 | Any sequence other than `001` (1 qubit) carried as a claim today | Its classical value is numerical, and the optimiser can undershoot it (it returned 0.296 where the published 4-state bound is 0.328) |
| X6 | R1 or R2 called device-independent | Both rest on the memory being one (or two) qubits |
| X7 | R3 on more than 64 pairs | Bipartite count (F6) |
| X8 | R3 with low-weight hidden Paulis, or with the identity channel | No separation: a memoryless learner handles local Paulis cheaply |
| X9 | R3 on all 64 pairs without selection, full-weight Pauli | A few bad pairs drive the product signal to ≈ 0 (marrakesh, boston snapshots) |
| X10 | R3's coded memoryless arm presented as the classical limit | The limit is a theorem; the arm is an illustration |
| X11 | R4 on `ibm_marrakesh` | ε ≈ 0.14, below ≈ 0.16 |
| X12 | R4 at n = 8 or 10 natively, or at n = 20 | No such rings on heavy-hex; a 20-qubit Haar state is not preparable |
| X13 | R4 with product-Clifford measurements, a PRNG for the inputs, or several shots per circuit | Bound becomes ε²(3/2)ⁿ (useless at 12), or the theorem's assumptions fail |
| X14 | Readout mitigation in any score above | Changes the claim |
| X15 | Mid-circuit measurement to reuse an output qubit | D-SCALE lint rule 1; own hardware evidence |

---

## 6. Research gaps and connections

| # | Gap or connection | Smallest step that closes it |
|---|---|---|
| G1 | 2-qubit clock: own 0.632 against the parent plan's "≈ 12 % gap". | Read Table 1 of 2402.16789 for d = 4. Re-run the optimiser with more restarts and export the isometry; count its CZ after synthesis. |
| G2 | Isometry cost: is every R1 step really ≤ 2 CZ after transpilation to heavy-hex CZ? | Synthesize the closed-form `001` step and count. |
| G3 | The memoryless bound for R3: "2 per qubit" in the parent plan against the Ω(2^(n/3)) form of the earlier theorems. | Read 2408.03376 and 2112.00778 for the exact task and bound. At n = 64 the two differ by 2⁴³. |
| G4 | **R3 feeds R6.** R6's certificate assumes Pauli noise and needs a noise model for its doping-loss term. R3-INTRINSIC learns exactly that model, on the same ring, with the sister-memory method. It also answers the referee objection that R3's channel is synthetic. | Run R3-INTRINSIC on the R6 ring's CZ layer; pass the learned eigenvalues to M8. |
| G5 | **R2 → R4 is one ladder; so is R1 → R1-M2.** Both raise the memory size of the same witness (1, 2, 12 qubits for hand-off; 1, 2 qubits for the clock). | Report them as ladders with the memory size on the axis. |
| G6 | **One tile module for four routes.** Pair, star, hexagon and ring are disjoint tiles of the same map; R3 pairs and R5 hexagons are graph states and share M2. | Build M9 once. |
| G7 | **Two loss meters.** The pair signal r (R3) and the hexagon game score (R5) both estimate the effective loss per CZ that gates R6. | Compare the two estimates on the same qubits. |
| G8 | Worst-tile behaviour for R1-TILE24 and R5-MAP8 is unknown; simultaneous drive adds crosstalk the snapshots do not show. | Noisy simulation of 2 adjacent tiles, then the hardware map. |
| G9 | The bit bound for R4 is read off two published points by a straight line. | Transcribe the bound and its constants (parent AC-6). |

---

## 7. Method note

- Sequence optima: isometry parametrised by QR of a complex matrix, BFGS, 12 to 25 restarts; classical machine
  by softmax-parametrised sub-stochastic matrices, 40 restarts (it undershoots for 4 states, see X5).
- Packings: randomised greedy independent sets (lower bounds); matching by `networkx.max_weight_matching`.
- Forecasts: R1 loss = (5/3) × summed star CZ error + summed output readout error; R3 signal =
  (1 − 2e_ro)² × (1 − 16/15 e_cz)² per pair; R4 from the parent plan's formula on the best hexagon.
- Probabilities are subjective and assume the simulation step passed first, as in the parent plan.
