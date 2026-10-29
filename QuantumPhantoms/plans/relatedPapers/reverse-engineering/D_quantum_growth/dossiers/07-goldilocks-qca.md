# #07 — Goldilocks quantum cellular automata (Hillberry; Jones; Farrelly)

**Letter:** D ([`D_quantum_growth`](../README.md)) · **Priority:** ★★★ · **Kind:** quantum · **Papers:** D13, D14, D03 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

<!-- The method in plain words: what problem it solves, the core idea. -->
A quantum cellular automaton updates qubits by local controlled rules. Goldilocks rules activate a site only for a "just right" neighbourhood, and generate non-equilibrating coherent dynamics and complex mutual-information networks [D13]. Jones et al. [D14] ran the 1-D rule T6 on a 23-qubit Sycamore-class chip. D-3 re-derives T6, then builds a heavy-hex-native rule on a patch of the FakeMarrakesh lattice and lifts one snapshot to a 3-D seed shape for E.

## Equations

<!-- The equations we re-implement, with symbols defined. -->
```text
T6 (D14 SM Eq. 3):   U_i = |00><00| + |01> H <01| + |10> H <10| + |11><11|   (on the neighbours; H acts on site i)
Compile:             H iff exactly one neighbour is 1  <=>  CH(a->i) CH(b->i) (H H = 1);  CH = RY(pi/4) CZ RY(-pi/4)
Cycle:               sublattice holding the central flip first, then the other; |0> padding at both ends
Invariant:           O = sum_i Z_i Z_{i+1} (domain walls) conserved by T6
MI network:          I_ij = H(z_i) + H(z_j) - H(z_i,z_j)  (Shannon, z basis)
Clustering:          C = Tr[I^3] / sum_{i!=j} [I^2]_ij;  path length l = mean_ij min_path sum 1/I_kl;  node strength g_i = sum_j I_ij/(L-1)
Heavy-hex rule:      H on site i iff exactly one neighbour is 1; A sublattice then B (heavy-hex is bipartite)
                     = CH from every neighbour (H^k) + one C^3-H on the 3 neighbours of a degree-3 site (cancels k=3)
Witness:             negativity N_ij = sum |negative eigenvalues of rho_ij^{T_B}|, rho_ij by linear inversion from 9 bipartite settings
                     (sublattice A basis x sublattice B basis in {X,Y,Z}^2) + nearest physical state (Smolin-Gambetta-Smith)
```

## Parameters

<!-- Every parameter with its published value/range and source (paper code, section, table). -->
- T6: single central flip, t ≤ 15 cycles, L ∈ {11, 15, 17, 23} ideal (Aer statevector), L = 11 Heron-class noise (1 000 shots per cycle).
- Heavy-hex: 21-qubit patch = two adjacent heavy-hex cells (FakeMarrakesh physical qubits 3–11, 16–18, 23–31, centre qubit 7), t_max = 10, 4 000 shots, 11 population circuits + 9 setting circuits in one job. Seed: 0.5 mm voxels, tube radius 1.2 voxels.
- **Heron mode runs one 12-qubit hexagon of this patch**, not the 21-qubit patch: Aer re-simulates every shot, one ideal 21-qubit circuit takes ~37 s and the noisy MPS run did not finish 20 shots (decision recorded with the developer).

## Paper's claimed result

<!-- The single published number or figure we will reproduce, with exact reference. -->
D14 prints no numeric table for the emulated curves; Fig. 3 (clustering coefficient C(t), L = 15, 17, 19, blue = noise-free emulation) is graphical. Main claims: the T6 mutual-information network has large clustering that does not decay with L, short path length and a broad node-strength distribution (small-world); raw Weber data decay to the random limit at t ≈ 12. SM: O = Σ Z_i Z_{i+1} is a dynamical invariant.

## Our reproduction (number + figure)

<!-- Our number vs the paper's, agreement, figure in ../figures/, run id. Quantum: label the sim mode. -->
`python -m D_quantum_growth.repro.jones_t6` (figures `jones_t6_population.png`, `jones_t6_network.png`).

- **Invariant O(t)** conserved to ≤ 2.5·10⁻¹⁴ for L = 11, 15, 17, 23 (ideal): the rule is implemented exactly.
- **Clustering vs D14 Fig. 3, L = 17** (paper values read from the printed figure, ±0.03 reading error; simulated: ideal):

| t | 2 | 4 | 6 | 8 | 10 |
|---|---|---|---|---|---|
| paper (figure reading) | 0.09 | 0.19 | 0.26 | 0.30 | 0.31 |
| ours | 0.089 | 0.193 | 0.261 | 0.308 | 0.307 |

Max difference 0.008. The plan asked for ±0.02 against values read from the figure; pixel reading limits the paper side to about ±0.03, so agreement is stated at that tolerance. The update order matters: updating the sublattice that does *not* hold the central flip first gives C(2) = 0.115 for L = 17 and misses the printed curve; the sublattice holding the flip first matches.
- Heron-class noise, L = 11: C(t) peaks at ≈ 0.21 (t = 5–7) and decays towards the random limit by t ≈ 10–11, the qualitative decay D14 reports for raw hardware data (no numeric matching claim; label simulated: Heron-class noise (FakeMarrakesh)).
- Network measures: D14's three measures (clustering, path length, node strength) are implemented; the plan's "density and disparity" are not D14's measures and were not used.

## Adaptation

<!-- How it is adapted to lungs, 3-D, certification and our contracts. -->
Heavy-hex Goldilocks rule on FakeMarrakesh (`src/qca.py`, `src/heavyhex.py`), updated sublattice by sublattice, read in Z per cycle and in the 9 bipartite settings at t_max; negativity witness and MI network from the reconstructed nearest-neighbour states; one Z snapshot → 3-D `seed_shape` (solid of revolution about the principal axis through the centre node, closing, connected component). E accepts it (`python -m E_classical_growth.src.grow --seed-shape …` ran to completion).

| | simulated: ideal (21-qubit patch) | simulated: Heron-class noise (12-qubit hexagon) |
|---|---|---|
| routing SWAPs | 376 (C³-H on degree-3 sites) | **0** |
| best NN negativity | 0.0167 ± 0.0055 (qubits 16–23), 3.04σ | 0 (state decohered; measured populations deviate 0.51 from exact) |
| witness passed (some N_ij > 3σ) | yes, barely; best of 22 edges, no look-elsewhere correction | **no** |
| seed shape | 301 voxels, claim L1 | 90 voxels, claim **L0** ("MI structure only, no L1") |

Measured populations vs exact statevector (ideal): max deviation 0.020 (shot noise at 4 000 shots).

**Deviations.** (1) The exact rule on the degree-3 sites needs a C³-H between mutually non-adjacent neighbours, so the full patch is **not SWAP-free** (376 routing SWAPs); the hexagon has no degree-3 site and is SWAP-free. The cheaper odd-parity form (CH from every neighbour only) was rejected: it differs from the exact rule by up to 0.57 in population. (2) Heron QCA is the 12-qubit hexagon. (3) The ideal 3σ pass is borderline and is the maximum over 22 edges; treat as weak evidence of NN entanglement, not a strong L1.

## Verdict

<!-- integrated | rejected (with reason). Claim level for quantum targets. -->
**adapted** (T6 reproduced within the figure-reading tolerance; heavy-hex rule built). Claim level **L1 only for the ideal run, and borderline**; **L0 for the Heron-noise hexagon** (witness failed). No L2: the BP adversary (#9) does not reproduce the 21-qubit circuit up to χ = 16, which is a statement about BP, not a quantum-advantage claim.

## What to reuse next

<!-- Pointers for downstream letters / INT. -->
`qca.py` (`t6_run`, `goldilocks_circuit`, MI measures) and `seed_shape.py` (3-D lift) are reusable. INT: the QCA initial condition could be coupled to the lineage outcome (plan Q2, proposal only). A less noise-sensitive witness (fewer cycles, or error-mitigated tomography) is needed before the Heron-noise QCA can claim L1.
