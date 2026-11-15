# Feature QCAND — Candidate circuits for B, C and D (additive: four for B, four for D, three for C)

**Epic:** [epic-quantum-phantoms-mvp.md](epic-quantum-phantoms-mvp.md) (Approved); builds on
[feature-QSCALE-certified-seed-and-chip-scale-BD.md](feature-QSCALE-certified-seed-and-chip-scale-BD.md) (Approved).
No epic row exists for this step: standalone feature.
**Feature ID:** QCAND
**Author:** Claude (Opus)
**Date:** 2026-11-14
**Status:** Draft

> Stack locked: Python 3.13, Qiskit, the minimal pipeline in `code/`. **Additive only:** every candidate is a new
> row in a `CIRCUITS` table with its own module; no existing row changes behaviour. No automated tests, manual
> verification only. Dry runs stay small. Hardware jobs are run by Peter only. Every bound below was read through
> search results and partial page reads on 2026-11-14 and is `[verify]`: none is a claim before the PDF check.

---

## 1. Why (Step Goal)

**Before.** B and D each have one family that passes on `ibm_fez` at small size (R2 codes, R1 clock, R3 pairs) and
one that fails when a single state must be right everywhere (hexagon game, DSCALE). The plan so far gives no new
thing to try when a candidate fails. "Try the circuits and see what sticks" needs more candidates.

**Search.** 35 queries, about 70 distinct papers surfaced, 22 read in part through fetched pages (each page was
truncated at about 39,000 characters; the rest came as a machine summary). Not 50 papers read in full. Full list in
the Sources section.

**What the reading says, in one table.**

| Lesson | Evidence | Consequence |
|---|---|---|
| Wide, shallow, locally checked circuits work on today's chips | Graph-state Bell violation on 65 qubits with 2 circuits, raw (2101.10307); whole-device entanglement on 127 qubits with 36 circuits (2312.15170); GHZ parity game to 71 qubits (2512.02284) | Scale by width, score by local or parity checks |
| A game that needs only parity coherence passes where fidelity > 0.5 fails | GHZ game bound 1/2 + 2^-(N/2); our N = 14 GHZ had F 0.26 to 0.46 | The failed DSCALE spine would likely pass as a game |
| Deep circuits survive only with error detection | 2,450 CZ on 50 qubits with spacetime checks, fidelity gain up to 236 times, kept fraction about 2e-5 (2504.15725, same first author as the depth-73 ring) | The check finder is the tool for the L2 ring; adopt it |
| A deep chaotic circuit with an exactly known answer exists | Dual-unitary kicked Ising, 91 qubits, 4,095 gates, autocorrelation cos^t(2h) (2411.00765) | A depth-resolved loss meter that sees idle errors (gap G4) |
| `ibm_fez` already ran 144 qubits for 50 cycles | 2-D time crystal, 9 two-qubit layers per cycle (2501.18036) | A chip-scale dynamic for growth frames exists on our chip |
| Two-copy learning advantages are fragile under noise | 2512.10929: purity-testing advantage "completely degraded by only a single layer of noise" | Do not expand R3 into two-copy state learning as a claim |
| Heuristic hardness breaks | Peaked circuits (QSCALE section 1) | No candidate below claims L2 |
| A classically trained circuit can carry a data distribution | Parameterised IQP with classical MMD training to 1,000 qubits (2503.02934); deep noisy IQP is classically easy (2403.14607) | A real job for B's mapping; no hardness claim |

**After.** B, C and D each have a list of candidates, every one runnable by setting `CIRCUIT`, each with a dry-run
size, a stated bound with its rigour, an expected result on `ibm_fez`, and a kill rule. Peter runs them one at a
time and the run log decides which stay.

### Candidates at a glance

| ID | Section | What it shows | Qubits (live) | CZ depth | Bound (rigour) | Expected on fez | Level |
|---|---|---|---|---|---|---|---|
| B-GHZ | B | N-player GHZ parity game on a tree | 8 to 40 | tree depth 4 to 8 | 1/2 + 2^-(N/2), local players (proven; locality assumed) | pass to N about 30 | L1.5 |
| B-MSQ | B | Magic square game on two Bell pairs, many tiles | 4 per tile, 16 tiles | about 8 CZ | 8/9 (proven; locality assumed) | 0.92 to 0.95, close | L1.5 |
| B-KS | B | Sequential Peres–Mermin contextuality, memory cost | 3 per tile, 16 tiles | about 6 CZ, mid-circuit readout | chi <= 4; memory >= log2 6 bits (2506.06869) | uncertain: mid-circuit readout | L1′-C |
| B-IQP | B | Cohort drawn from a classically trained IQP circuit | 36 to 108 | 3 CZ layers | none (no hardness claim); MMD to target | works; a socket, not a separation | L0 |
| D-GRAPH | D | Every qubit of the chip entangled (per-edge negativity) | up to 156 | 3 CZ layers | negativity > 0 per edge (proven witness) | pass, most edges | L1 (bipartite per edge) |
| D-STC | D | Clifford growth circuit with spacetime checks | 36 + checks | 10 to 20 | none: fidelity gain from post-selection | gain > 1, kept fraction 1e-2 to 1e-4 | L2 protocol, below threshold |
| D-DU | D | Loss per layer in a deep chaotic circuit, exact reference | 21 to 51 | up to 40 | exact value cos^t(2h) (analytic) | a number: decay per layer | calibration |
| D-DTC | D | Time-crystal dynamics as growth frames | 35 to 144 | 9 per cycle, 8 to 30 cycles | none (diagonal observable) | signal for 20+ cycles | L0 |
| C-GBELL | C | One Bell inequality over the whole chip, 2 circuits | up to 156 | 3 CZ layers | Baccari bound for the chip graph (proven; locality assumed) | violation, raw | certificate |
| C-PBR | C | p-value valid for dependent trials, replaces "3 sigma" | uses Bell-map data | 0 extra | prediction-based ratio (proven) | stricter than today | certificate |
| C-CHAIN | C | Certificate bound to a public beacon pulse and the ledger | 0 | 0 | hash chain (no physics claim) | works | provenance |

Recommended order to try: **D-GRAPH, B-GHZ, C-GBELL** (cheap, likely to pass, chip-scale), then **D-DU** (the
number L2 planning needs), **B-MSQ**, **D-STC**, then the rest.

Reserve (not planned here): Bell magic for T-doped rings by two-copy Bell measurement (2204.10061), which would
replace the placeholder doping loss in `ring_l2.py`; an L-step clock with qubit reuse; 2-D hidden linear function
(only a conjectured bound at reachable sizes, 2512.02284).

---

## 2. Acceptance Criteria

**Common to every candidate**

- [ ] **AC-0** (QCAND.0): each candidate is one new row plus one module, selected by `CIRCUIT`, with a `dry`
  size, and writes `<run>/qhard/<CIRCUIT>/result.json` and its claims.
  → Rows carry `level`, `bound`, `rigour` (with `[verify]`), `adversary`, `pass`. Inputs come from
  `runio.draw_bits` (QSCALE AC-5). Layout uses the Bell map (QSCALE AC-6). A dry pass is labelled
  "(dry run: not a claim)".

**B candidates**

- [ ] **AC-1** (QCAND.B1) `B-GHZ`: the GHZ parity game on a tree of N qubits.
  → `B_mapping/games.py:run_ghz`. GHZ by breadth-first CZ tree on the best-connected region (reuse the tree
  builder in `D_quantum_growth/ghz_spine.py`). Inputs: 32 even-weight bit strings from the pool; player i measures
  X (bit 0) or Y (bit 1). Win when the output parity equals (sum of inputs / 2) mod 2. Sizes `n: [8, 16, 24, 32, 40]`,
  dry `[4, 6]`. Pass per size: win above 1/2 + 2^-ceil(N/2) by 3 sigma; the claim is the largest passing N.
- [ ] **AC-2** (QCAND.B2) `B-MSQ`: the Mermin–Peres magic square game.
  → `B_mapping/games.py:run_msq`. Tile = 4 qubits on a path (two Bell pairs, one routed by a SWAP). 9 input pairs
  (row, column) from the pool, each player's three commuting observables read after a two-qubit basis change.
  `tiles: 16`, `min_pass: 12`, dry `tiles: 2`. Pass: win above 8/9 by 3 sigma after Bonferroni.
- [ ] **AC-3** (QCAND.B3) `B-KS`: sequential Peres–Mermin test on 2 qubits with an ancilla.
  → `B_mapping/games.py:run_ks`. Each context = three compatible two-qubit Paulis measured one after another
  through the ancilla with mid-circuit readout and reset. Reports chi (bound 4, quantum 6) and the memory-cost
  statement as rigour text. `tiles: 8`, dry `tiles: 1`. Refused on a backend without mid-circuit measurement.
- [ ] **AC-4** (QCAND.B4) `B-IQP`: a cohort drawn from a trained IQP circuit.
  → `B_mapping/iqp.py`. Circuit: Hadamards, ZZ(theta) on the heavy-hex edges of the chosen region in 3 layers,
  RZ(phi), Hadamards. Parameters trained classically on the rulebook's joint distribution (type, size, lobe, margin
  per tumour, plus one shared cohort covariate) by MMD on Pauli-Z expectation values; training runs once and is
  cached in `B_mapping/iqp_params.json`. Live: 108 qubits (12 tumours x 9); dry: 18. Result: MMD of hardware
  samples to the target and to the noiseless model. No pass rule beyond "MMD below the untrained circuit's". When
  `CIRCUIT = "B-IQP"` the cohort is decoded from these samples by the existing `bits_to_params`.

**D candidates**

- [ ] **AC-5** (QCAND.D1) `D-GRAPH`: whole-device graph state with per-edge negativity.
  → `D_quantum_growth/graph_state.py`. Hadamard on every used qubit, CZ on every edge in 3 layers (edge colouring).
  For each batch of non-adjacent edges: neighbours measured in Z, the pair in the 9 Pauli bases; pair state
  reconstructed with the neighbour byproduct applied; negativity per edge. 4 batches x 9 = 36 circuits. Dry: 12
  qubits, 1 batch. Pass: edges with negativity above 0 by 3 sigma (Bonferroni) connect at least 90 % of the used
  qubits. Claim text: "bipartite entanglement on every edge; not genuine multipartite". Seed shapes come from one
  extra all-X snapshot circuit.
- [ ] **AC-6** (QCAND.D2) `D-STC`: a Clifford growth circuit with spacetime checks.
  → `D_quantum_growth/checks.py`. Payload: the 36-ring Clifford circuit of `ring_l2.py` at depth 10, 14, 20. Checks:
  ancilla in |+>, controlled-Paulis at two times chosen so the check commutes through the payload, X readout;
  candidates enumerated by back-propagating low-weight Paulis with `qiskit.quantum_info.Clifford`, kept when the
  two ends sit next to a free ancilla. Up to 8 checks. Result: direct fidelity estimate with and without
  post-selection, kept fraction, gain. Dry: 12 qubits, depth 4, 2 checks. Pass: gain above 1 by 3 sigma.
- [ ] **AC-7** (QCAND.D3) `D-DU`: dual-unitary loss meter.
  → `D_quantum_growth/du_meter.py`. Kicked-Ising brickwork on a chain at the dual-unitary point, h in (0, 0.1);
  the light-cone autocorrelation C(t) is cos^t(2h). Chains of 21 and 51 qubits, t up to 20. Fit raw C(t) /
  cos^t(2h) = A exp(-g t). Writes `loss_per_layer` to `qhard/loss_per_cz.json` next to the ladder's numbers; the
  L2 forecast (QSCALE AC-13) uses it when present. Dry: 9 qubits, t up to 4.
- [ ] **AC-8** (QCAND.D4) `D-DTC`: time-crystal growth frames.
  → `D_quantum_growth/dtc.py`. Floquet cycle of 2501.18036 on a heavy-hex patch (three two-qubit layers of the
  anisotropic coupling, then the imperfect pi-pulse). 8 circuits at cycle counts matched to the 8 growth frames.
  Result: Delta(t), the subharmonic contrast, and per-tumour seed shapes per frame from the Z snapshots of the
  tumour's patch (written to `dscale/seed_shapes.npz` in the existing format). Live 35 qubits first (plan: 144);
  dry 12 qubits, 3 frames. No pass rule; label "quantum-sourced dynamics, diagonal observable, no separation".

**C candidates**

- [ ] **AC-9** (QCAND.C1): C gets a `CIRCUIT` constant: `BELL-MAP` (QSCALE, default) | `GRAPH-BELL`.
  → `C_certificate/main.py` table `CIRCUITS`, same pattern as B and D.
- [ ] **AC-10** (QCAND.C2) `GRAPH-BELL`: one scalable Bell inequality over the chip graph.
  → `C_certificate/graph_bell.py`. Graph state on the used region, 2 measurement circuits (alternating X and Z by
  sublattice), the inequality of 2101.10307 Eq. 3 with its classical bound computed for the actual graph.
  Certificate verdict: value above the bound by 3 sigma. The bit pool is extracted only from `BELL-MAP`; with
  `GRAPH-BELL` the run still executes one matching of `BELL-MAP` for the pool.
- [ ] **AC-11** (QCAND.C3) `C-PBR`: finite-statistics verdict by prediction-based ratio.
  → `C_certificate/pbr.py`: first third of the rounds estimates the ratio, the rest are tested; p-value bound
  min(1, 1/t). `certificate.json` gets `p_value_local`. The stop rule (QSCALE AC-3) uses p < 1e-6 in place of
  "S_low > 2". The no-signalling p-value per pair is stored as a cross-talk flag in `pair_map`.
- [ ] **AC-12** (QCAND.C4) `C-CHAIN`: the certificate is bound to time and to the ledger.
  → Before the job: SHA-256 of the circuits and the run name is written as `commit`. After the job: the first
  public beacon pulse after the commit (drand HTTP API, one GET; skipped with a logged note when offline) seeds
  the Toeplitz extractor in place of `os.urandom`. `G_provenance` chains `commit`, `pulse`, `certificate.json`.

**Docs**

- [ ] **AC-13** (QCAND.X): `code/README.md` circuit lists, `CLAUDE.md` ("B, C and D have one switch each"),
  `code/RUNLOG.md` "Next".

---

## 3. Out of Scope (Postponed)

- Any L2 claim, any hardness claim for B-IQP, D-DTC or D-STC → blocked by the hard rules.
- Bell magic for doped rings, the L-step clock with qubit reuse, 2-D hidden linear function → reserve list;
  planned only if a candidate here is dropped.
- Two-copy state learning as an advantage claim → not planned (noise result of 2512.10929).
- Using an external spacetime-check package → own minimal finder first; the published code
  (github.com/ajavadia/spacetime-checks, not inspected) is a later comparison.
- Readout mitigation, tensor-network error mitigation → scores stay raw; D-DU reports the raw decay on purpose.
- Feeding D-DTC or B-GHZ outcomes into the growth law itself → separate feature (CLAUDE.md priority 1).
- Removing any existing circuit → nothing is removed here.

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Where candidates live | B: `B_mapping/games.py`, `B_mapping/iqp.py`. D: one module per candidate. C: `graph_bell.py`, `pbr.py` |
| Layout | Regions and trees from the Bell map of the same run; edge colouring by networkx for 3-layer CZ |
| GHZ tree | Existing spine builder, `by_cost` ordering, no parity checks |
| Tomography in D-GRAPH | Linear inversion of 9-basis two-qubit counts, negativity from the partial transpose (numpy) |
| IQP training | numpy + scipy L-BFGS on exact Pauli-Z expectation values (they are classical for IQP); no JAX dependency |
| Check search in D-STC | Back-propagation of weight-1 and weight-2 Paulis through the Clifford payload |
| Mid-circuit readout (B-KS) | Qiskit dynamic circuits (`measure` + `reset` mid-circuit); refused when the backend lacks it |
| Beacon | drand public HTTP endpoint, one GET, response stored verbatim |
| Significance | 3 sigma with Bonferroni over tiles, sizes or edges; C uses the PBR p-value |

**Conventions & Notes:**
* Nonlocal games on one chip: the players are not separated. Every such claim says "locality assumed (same chip)".
* B-KS and D-GRAPH claims name what they do not show (no dimension-free claim; not genuine multipartite).
* D-STC and D-DU are about the device and the road to L2; D-DTC and B-IQP are sockets with level L0.
* One job per candidate where possible; shots cut by the existing spend guard (45 QPU-s per run).
* Kill rule per candidate: two live runs below its bound on the best available backend → marked "dropped" in
  `RUNLOG.md`, row kept but commented as dropped.

---

## 5. Data Model (Additions/Modifications)

```text
[New files]  <run>/qhard/<CIRCUIT>/result.json, one per candidate
  B-GHZ     rows [{n, win, sigma, bound, passed, tree_depth}], largest_passing_n
  B-MSQ     tiles [{qubits, win, sigma}], win_per_input, tiles_passed
  B-KS      tiles [{qubits, chi, sigma}], contexts, memory_bound_bits
  B-IQP     n, mmd_target, mmd_model, mmd_untrained, params_sha256
  D-GRAPH   edges [{a, b, negativity, sigma}], connected_fraction, largest_component
  D-STC     rows [{depth, checks, F_raw, F_kept, kept_fraction, gain}]
  D-DU      rows [{n, h, t, C_raw, C_exact}], loss_per_layer, sigma
  D-DTC     rows [{cycle, delta}], subharmonic_contrast, frames

[Existing file - Modifying]  <run>/certificate.json
  circuit          "BELL-MAP" | "GRAPH-BELL"
  graph_bell       {value, classical_bound, quantum_bound, sigma}      (GRAPH-BELL only)
  p_value_local    float                                               (C-PBR)
  commit, pulse    hex strings                                         (C-CHAIN)

[New file]  code/B_mapping/iqp_params.json      trained parameters, tracked in git

[Existing file - Modifying]  <run>/qhard/loss_per_cz.json
  loss_per_layer, sigma_layer                                          (D-DU)
```

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `code/B_mapping/games.py` | `run_ghz`, `run_msq`, `run_ks` (mirror `common/game.py` structure: build, play, score) |
| New | `code/B_mapping/iqp.py` | IQP circuit, classical MMD training, hardware sampling, MMD report |
| New | `code/B_mapping/iqp_params.json` | Cached trained parameters |
| Modify | `code/B_mapping/main.py` | Rows `B-GHZ`, `B-MSQ`, `B-KS`, `B-IQP`; `CIRCUIT` comment |
| Modify | `code/B_mapping/roll.py` | When `CIRCUIT = "B-IQP"`: decode the cohort from the IQP samples |
| New | `code/D_quantum_growth/graph_state.py` | `D-GRAPH` |
| New | `code/D_quantum_growth/checks.py` | `D-STC` check finder and runner |
| New | `code/D_quantum_growth/du_meter.py` | `D-DU` |
| New | `code/D_quantum_growth/dtc.py` | `D-DTC`, writes seed shapes per frame |
| Modify | `code/D_quantum_growth/main.py` | Four rows; `CIRCUIT` comment |
| Modify | `code/D_quantum_growth/ring_l2.py` | Forecast reads `loss_per_layer` when present |
| New | `code/C_certificate/graph_bell.py` | `GRAPH-BELL` |
| New | `code/C_certificate/pbr.py` | Prediction-based-ratio p-values |
| Modify | `code/C_certificate/main.py` | `CIRCUIT` constant and table; PBR verdict; commit and beacon pulse |
| Modify | `code/G_provenance/main.py` | Chain `commit`, `pulse`, certificate |
| Modify | `code/common/qhard.py` | Edge colouring helper, region picker by Bell map |
| Modify | `code/E_classical_growth/main.py` | Accept per-frame seed shapes when present (D-DTC) |
| Modify | `code/README.md`, `CLAUDE.md`, `code/RUNLOG.md` | Circuit lists, C switch, next runs |

Build order: D-GRAPH → B-GHZ → C-GBELL + C-PBR → D-DU → B-MSQ → D-STC → B-IQP → D-DTC → B-KS → C-CHAIN.
Each step ends with a dry run and can go live on its own.

---

## 7. Manual Verification (No Tests)

- [ ] **Every candidate:** set its `CIRCUIT`, run `python main.py` (dry) → section finishes, `result.json`
  present, claim labelled "(dry run: not a claim)", whole pipeline under 3 minutes.
- [ ] **AC-1:** dry `B-GHZ` on the ideal simulator setting (`FAKE_BACKEND` noise off in a Python shell) → win 1.0
  at every size; with noise → win between the bound and 1.
- [ ] **AC-2:** ideal → win 1.0 on all 9 inputs; a product-state control (skip the Bell-pair CZ) → win at most 8/9.
- [ ] **AC-3:** ideal → chi = 6; with the entangling gates removed → chi at most 4.
- [ ] **AC-4:** after training, `mmd_model` < `mmd_untrained`; decoded cohort frequencies follow the rulebook.
- [ ] **AC-5:** ideal → negativity 0.5 on every edge; with one CZ removed → that edge reads 0 within sigma.
- [ ] **AC-6:** with a Pauli error injected by hand after layer 2, at least one check fires; `gain` > 1 on the
  noisy dry run.
- [ ] **AC-7:** ideal → `C_raw` equals cos^t(2h) within sampling error at h = 0 and h = 0.1.
- [ ] **AC-8:** ideal → Delta(t) alternates sign each cycle; `seed_shapes.npz` has one shape per tumour per frame
  and section E consumes it.
- [ ] **AC-10:** ideal → value equals the quantum bound; product state → value at most the classical bound.
- [ ] **AC-11:** simulated local data (S = 1.9) → p-value near 1; dry Bell data → p-value below 1e-6.
- [ ] **AC-12:** with the network off → note "beacon skipped", run continues; with it on → `pulse` stored and
  `python -m G_provenance.main <run>` passes.
- [ ] **Live (Peter):** one run per candidate in the build order; result added to `code/RUNLOG.md`.

---

## 8. Open Questions

- [ ] **Q1:** Does your IBM plan allow mid-circuit measurement and reset on `ibm_fez`? *Proposed:* build B-KS
  last; refuse it when unavailable.
- [ ] **Q2:** May C call a public beacon over the network (drand) during a run? *Proposed:* yes, one GET, skipped
  when offline.
- [ ] **Q3:** B-IQP target: the rulebook's independent marginals (as today) or a joint table with correlations
  from LIDC annotations? *Proposed:* marginals plus one shared cohort covariate first; LIDC joint table later.
- [ ] **Q4:** D-DTC writes seed shapes per growth frame, which touches section E. Acceptable in an additive plan?
  *Proposed:* yes, behind "file present" only; E is unchanged for every other circuit.
- [ ] **Q5:** Order of work: build all candidates, or build three (D-GRAPH, B-GHZ, C-GBELL), run them live, then
  decide? *Proposed:* three first.
- [ ] **Q6:** QSCALE first, or candidates first? Candidates assume QSCALE's bit pool and Bell map.
  *Proposed:* QSCALE parts C and B1 first, then the first three candidates.

---

## 9. Post-Implementation Notes

[Filled after implementation.]

---

## Sources (search and partial reads of 2026-11-14; verify in the PDFs before citing)

Read in part: 2512.02284 (contextuality tasks, Google), 2503.02934 (IQP generative), 2101.10307 (scalable Bell,
IBM), 2503.18949 (PBR Bell tests on IBM), 2504.15725 (spacetime checks), 2312.15170 (whole-device entanglement),
2501.18036 (2-D time crystal on ibm_fez), 2411.00765 (dual-unitary), 2209.14353 and 2402.08606 (contextual memory
separations, abstracts), 2506.06869 (memory cost of contextuality, abstract), 2512.10929 (noisy learning theory),
2112.00778 (learning from experiments), 2204.10061 (Bell magic), 2509.09033 (generative advantage), 2308.13065
(dynamic-circuit entanglement), 2509.07255, 2510.25838, 2510.09520, 2406.17841, 2609.40050, 2605.25983 (abstract).

Surfaced by search, not read: 2404.14493, 2510.00132, 2301.00995, 2105.00603, 2402.12246, 2408.16378, 2606.16425,
2311.01363, 2512.16886, 2511.03689, 2604.18014, 1812.04251, 1905.06953, PRX 9 041013, PRX 11 021019, 2105.06285,
2105.06448, 2105.14434, 2312.13473, 2005.02403, 1712.01234, 2003.14045, 2403.16718, 2603.12675, 2408.03064,
2004.14018, 2312.06062, 2308.00750, 2106.11722, 2105.03333, 0904.1655, 1304.1292, 1007.3650, 1611.07515,
1706.07370, 2510.20722, 2607.00507, 2606.28483, 2403.14607, 2411.02535, 2407.07754, 2305.19152, 2402.00766,
1801.03782, 1903.11747, 0906.3390, 1812.10428, 2001.04885, 1602.00440, 2105.09324, 2210.08039, 2503.22380,
2508.14621, 2312.16165, 2605.12713, 2111.00167, 0906.3195, 2602.04719, 2306.17839, 2306.14887, 2309.15642,
2603.18825, 1609.05957, 2109.02507, 1905.13454, 1704.00690, 1906.04410, 2303.01625, 2404.00091, 2601.22224,
1806.05747, 2205.01141, 2509.20668, 2406.10645, 2405.04247, 2203.12497, 2408.07881, 2502.08060, 2509.18259,
2403.00938; Liu et al. Nature 640, 343 (2025); CURBy beacon, Nature (2025), DOI 10.1038/s41586-025-09054-3.
