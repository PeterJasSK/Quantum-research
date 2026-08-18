# QH Idea 13 — NP-hard problems that the QuantumLife teleport finding could unlock on heavy-hex hardware

**Tag: QUANTUM · qh · effort: medium-high**

## Pitch
The QuantumLife teleport study proved a **constant-depth long-range CNOT** on real IBM
heavy-hex silicon. This idea takes that one primitive and asks a systematic question:
*which named NP-hard optimization problems are currently blocked on heavy-hex hardware
purely because their interaction graph is too dense/non-local to route with SWAP networks —
and would therefore be unlocked by teleport-routing?* The answer is a ranked map from
"already done (topology-friendly, SWAP never stressed)" to "guaranteed-dense and never run
on hardware." The single strongest novel target is **fully-connected Number Partitioning
(Sherrington–Kirkpatrick) QAOA**: a complete interaction graph where *every* coupling is
long-range, so the teleport-vs-SWAP contrast is maximal and no hardware result exists.

**Paper strength score: 78/100** — first real-hardware execution of teleport-routed QAOA
(prior work is simulation-only) on a guaranteed-dense problem, at a scale existing heavy-hex
demos deliberately avoid. Docked because the primitive and the routing idea both exist
separately in the literature; the contribution is the hardware fusion + the honest
noise-cost verdict, not new physics.

---

## 0. Progression — how we got here

**Step 1 — what QuantumLife found.**
`QuantumLife/research/conclusion_teleportation_longrange.md` established, on
`ibm_marrakesh` (156-qubit Heron r2), that a **long-range CNOT implemented via
teleportation** (Bell pair + 2 mid-circuit measurements + classical feed-forward, i.e.
dynamic circuits) delivers a measurable, crosstalk-immune, single-sign correlation at
12-qubit separation at **constant depth 9**, where the logically-equivalent **SWAP ladder
costs depth 31** (O(distance), ~85 at d=36). Verified independently against the run JSONs:
teleport seed-mean `c(d) ≈ −0.065` (4/4 seeds negative), SWAP `≈ +0.040` (4/4 positive),
depth win deterministic. The reusable asset is not the correlation number — it is the
**constant-depth long-range coupling**.

**Step 2 — where that primitive actually bites.**
On heavy-hex, the dominant cost of running any optimization circuit is not the algebra — it
is **mapping a non-local interaction graph onto a sparse chip.** Every pair of variables
that interact but are not physical neighbours needs a SWAP chain; depth grows O(distance)
per non-local edge; decoherence eats the answer. A constant-depth long-range gate attacks
exactly this bottleneck.

**Step 3 — the connectivity cheat in existing demos.**
A literature sweep (see §4 references) shows every 100+ qubit IBM heavy-hex optimization
result runs problems whose interaction graph **already matches the chip**: Pelofske's
127-qubit spin-glass is *"built to match the heavy-hex graph"*; Sachdeva's 156-node MaxCut
uses topology-friendly 3-regular graphs. **Zero long-range edges → SWAP routing is never
stressed → the routing barrier is invisible.** The moment a problem forces a *dense* graph,
the hardware result disappears.

**Step 4 — the search.**
So we enumerated the named NP-hard problems, scored each on (a) QUBO/Ising interaction-graph
density (how non-local, from Lucas 2014), and (b) whether it has an actual heavy-hex
*hardware* demonstration. The intersection **"guaranteed-dense × never-run-on-hardware"** is
the unclaimed territory the teleport finding can open. This document is that map.

**Prior art we must not reinvent (confirmed):**
- **Primitive, on hardware:** Bäumer et al., *Efficient long-range entanglement using
  dynamic circuits*, PRX Quantum 5, 030339 (2024) / arXiv:2308.13065 — long-range CNOT via
  gate teleportation, 101 qubits apart, on IBM heavy-hex. This is our exact mechanic.
- **Teleport-routed QAOA — simulation only:** Babu et al., *Gate teleportation-assisted
  routing for quantum algorithms*, arXiv:2502.04138 (2025) — benchmarks QAOA on the 127-qubit
  heavy-hex *topology in simulation*, ~10–25% depth reduction vs SWAP. **Never executed on
  real hardware.** ← the open gap.
- **Theory backbone:** Bravyi–Gosset–König, *Quantum advantage with shallow circuits*,
  Science 362 (2018) / arXiv:1704.00690 — measurement + feed-forward buys long-range
  correlation at constant depth that local unitaries provably cannot.

**The precise unclaimed slice:** *the first real-hardware execution of teleport-routed QAOA,
on a guaranteed-dense problem, at a scale existing heavy-hex demos avoid by using
topology-matched sparse graphs.* Babu did the sim; Bäumer did the primitive; nobody fused
them on hardware on a complete graph.

---

## 1. The full map — every NP problem, density × hardware status × teleport benefit

Density = how non-local the standard QUBO/Ising interaction graph is (Lucas 2014).
HW = has a published IBM **heavy-hex hardware** demonstration (not simulation, not D-Wave,
not trapped-ion). Benefit = expected payoff from constant-depth teleport routing.
Novelty = dense **and** unclaimed **and** teleport helps.

| # | Problem | QUBO graph density | On heavy-hex HW? | Teleport benefit | Novelty |
|---|---------|--------------------|------------------|------------------|---------|
| 1 | **Number Partitioning (SK)** | Complete Kₙ — guaranteed | ~No (only market-split variant) | **Maximal** (every edge long-range) | **★★★ best** |
| 2 | **Quadratic Knapsack (dense profit)** | Complete + inequality clique | No (only linear MDKP) | Very high | ★★★ |
| 3 | **Traveling Salesman (TSP)** | Overlapping N-cliques, O(N³) | Weak/tiny only | High | ★★★ |
| 4 | **Graph Coloring** | Color-cliques + edges | No solid demo | High | ★★ |
| 5 | **Max-Clique (dense input)** | = complement graph | No | High (dense regime) | ★★ |
| 6 | **Maximum Independent Set (dense input)** | = input graph | Yes, but sparse graphs only | High if input dense | ★★ |
| 7 | **Set Cover** | Shared-element cliques + aux | Weak/none | Medium-high | ★★ |
| 8 | **Quadratic Assignment (QAP)** | ~Complete, O(n⁴) terms | **Yes** (arXiv:2607.11637) | High but taken | ★ |
| 9 | **Portfolio (full covariance)** | Complete Kₙ | **Yes** (4–16 assets) | High but partly taken | ★ |
| 10 | **Vehicle Routing (VRP)** | Dense, routing+assignment | Weak (sim-dominated) | Medium-high | ★★ |
| 11 | **Job-Shop Scheduling** | Precedence + machine chains | Yes (small) | Medium (structured, not dense) | ★ |
| 12 | **Max-SAT / 3-SAT** | Clause-dependent, often non-local | Weak/none on IBM | Medium | ★★ |
| 13 | **Feedback Arc / Vertex Set** | Height-ordering, sparse edges | No | Low (sparse) | ○ |
| 14 | **Steiner Tree** | Sparse | No | Low (sparse) | ○ |
| 15 | **Hamiltonian Cycle** | Permutation cliques, medium | No | Medium but niche | ○ |
| 16 | **Lattice protein folding** | Medium, turn-interaction | No (IBM run was pre-heavy-hex 20q) | Medium | ★ |
| 17 | **MaxCut / weighted MaxCut / spin-glass** | Topology-matched sparse | **Yes** (156q flagship) | ~None (already local) | ○ done |

Reading the map: the top band (1–5, plus 10/12) is **dense-and-unclaimed** — the teleport
target zone. The middle band (6, 8, 9, 11, 16) is dense but partly or fully demonstrated —
teleport helps but the "first on hardware" novelty is gone. The bottom band (13, 14, 17) is
either already local (no routing to save) or sparse (little to save).

---

## 2. Each problem — what it is and how the teleport finding improves it

### 1. Number Partitioning (Sherrington–Kirkpatrick) — **the flagship target**
**What it is.** Given a list of numbers `{nᵢ}`, split into two sets with equal sums.
Objective is a single squared penalty `H = A(Σᵢ nᵢ sᵢ)²`, `sᵢ ∈ {±1}`.
**Why dense.** Expanding the square gives a coupling `2A·nᵢnⱼ` for **every** pair — a
complete graph Kₙ, structurally identical to a fully-connected Sherrington–Kirkpatrick spin
glass. There is no locality to exploit; the input is just numbers.
**Hardware status.** Classic partitioning is essentially undemonstrated on heavy-hex; only a
market-split/target-allocation cousin has appeared on Heron.
**How teleport improves it.** On a complete graph *every* QAOA cost-layer edge is
long-range, so SWAP routing incurs its worst case and dominates depth. Teleport routing
gives each ZZ interaction a constant-depth path. Cleanest possible demonstration: no one-hot
constraints, no penalty ancillas, **no infeasible states** (every bitstring is a valid
partition), so the only variable between arms is the routing. This is the purest
teleport-vs-SWAP stress test that exists.
**Verdict.** Start here. Maximal density, unclaimed, trivial encoding, recognizable physics.

### 2. Quadratic Knapsack (dense profit matrix)
**What it is.** Pick items to maximize a **quadratic** profit `Σᵢⱼ pᵢⱼ xᵢxⱼ` subject to a
weight budget `Σ wᵢxᵢ ≤ W`.
**Why dense.** The quadratic profit couples every item pair (complete graph on a dense `p`),
and the inequality budget must be encoded with slack bits and squared → a second all-to-all
clique. Exactly Lucas's "inequalities → highly connected graphs" case.
**Hardware status.** Only *linear* multi-dimensional knapsack (MDKP) has run on Heron; the
quadratic, dense-profit version has not.
**How teleport improves it.** Two dense cliques stacked (objective + constraint) → routing is
the entire cost. Teleport routing collapses both to constant-depth couplings. Slightly
harder than partitioning because of the slack bits, but still no permutation structure.
**Verdict.** Strong second target; adds a realistic constraint to the partitioning story.

### 3. Traveling Salesman (TSP)
**What it is.** Shortest tour visiting N cities once. Permutation encoding: N² binaries
`x_{v,i}` (city v at tour position i).
**Why dense.** Row one-hot (each city once) and column one-hot (each position once) put
every variable in two overlapping N-cliques; the distance term couples adjacent tour
positions, which map to arbitrary distant qubits. O(N³) quadratic terms, no natural
heavy-hex embedding.
**Hardware status.** Formulated and simulated with heavy-hex as target, but only tiny
proof-of-principle QPU runs — effectively unclaimed on hardware at scale.
**How teleport improves it.** The permutation cliques are the canonical SWAP-blowup case;
constant-depth long-range gates route the clique edges directly. High profile — TSP is the
recognizable NP poster child.
**Verdict.** Highest "story" value, but N² qubits + feasibility penalties make it the
hardest to actually run. Good third target once partitioning proves the method.

### 4. Graph Coloring
**What it is.** Color a graph with n colors so no edge joins same-colored vertices.
`|V|·n` binaries `x_{v,i}`.
**Why dense.** Per-vertex one-hot → an n-clique per vertex; edge terms couple color-copies
across every input edge. Density grows with the number of colors.
**Hardware status.** No solid IBM heavy-hex demo (D-Wave / simulation dominated).
**How teleport improves it.** The n color-copies of each vertex plus input adjacency create
many non-local edges; teleport routing shortens the color-clique couplings.
**Verdict.** Solid ★★ target; denser and more constraint-heavy than partitioning.

### 5. Max-Clique (on dense input graphs)
**What it is.** Largest fully-connected subset of vertices. Equivalent to MIS on the
complement graph.
**Why dense.** The QUBO coupling graph *is* the input edge set (or its complement). A dense
input clique problem → dense QUBO.
**Hardware status.** No dedicated heavy-hex hardware demo.
**How teleport improves it.** On dense inputs the coupling graph is near-complete → SWAP
routing dominates → teleport wins. Payoff is input-conditional (target the dense regime
explicitly).
**Verdict.** Good ★★, pairs naturally with #6.

### 6. Maximum Independent Set (dense input)
**What it is.** Largest vertex set with no edge between members. Penalty `Σ_{(u,v)∈E} xᵤxᵥ`.
**Why dense.** Coupling graph = input edge set; dense input → dense QUBO.
**Hardware status.** MIS **has** run on Heron (2607.11637, QOBLIB on ibm_fez) — but on
graphs chosen/matched to be hardware-friendly (sparse). The **dense-input** regime is the
untested part.
**How teleport improves it.** Running MIS on a genuinely dense input graph forces long-range
edges the existing demos avoided; teleport routing is what makes that regime reachable.
**Verdict.** ★★ with a twist — the novelty is specifically "dense-input MIS," not MIS in
general.

### 7. Set Cover
**What it is.** Choose fewest subsets whose union covers a universe. One binary per subset.
**Why dense.** Each element's coverage is a "≥1" inequality → clique over all subsets
containing it, plus counting ancillas. Heavily-overlapping subsets → many large cliques.
**Hardware status.** No clear IBM heavy-hex hardware demo.
**How teleport improves it.** Overlap cliques are non-local; teleport routing shortens them.
Auxiliary-heavy, so more qubits per logical variable.
**Verdict.** ★★ but messier; behind the top group.

### 8. Quadratic Assignment (QAP)
**What it is.** Assign n facilities to n locations minimizing flow×distance. Generalizes TSP.
**Why dense.** Flow×distance objective couples nearly all `xᵢₚ, xⱼ_q` pairs; two families of
one-hot constraints add row- and column-cliques. Up to O(n⁴) quadratic terms.
**Hardware status.** **Already demonstrated** on Heron (arXiv:2607.11637, "Circuits to
Hardware," ibm_fez / marrakesh / torino). Taken.
**How teleport improves it.** Would still benefit enormously from routing, but the
"first-on-hardware" novelty is gone. Possible angle: teleport-routed QAP *beats* the
published SWAP-routed QAP result — a head-to-head, not a first.
**Verdict.** ★ — comparison paper only, not a first.

### 9. Portfolio optimization (full covariance)
**What it is.** Markowitz: minimize `xᵀΣx` risk minus return, budget constraint.
**Why dense.** `xᵀΣx` couples every asset pair with nonzero covariance → complete graph for
a dense Σ; budget `(Σxᵢ − K)²` adds a second full clique.
**Hardware status.** Demonstrated small–mid on Heron (4→16 assets).
**How teleport improves it.** At **scale** (dense Σ, 50+ assets) the existing small runs hit
the routing wall; teleport routing is what pushes past 16 assets. Angle: "dense-covariance
portfolio at a scale SWAP routing can't reach."
**Verdict.** ★ — partly taken; novelty only at larger, denser instances.

### 10. Vehicle Routing (VRP)
**What it is.** Optimal routes for a fleet serving customers from a depot. TSP's multi-vehicle
generalization.
**Why dense.** Combines routing (TSP-like permutation cliques) with vehicle-assignment
one-hots → dense and non-local.
**Hardware status.** Simulation-dominated; QOBLIB defines instances but hardware runs are
minimal.
**How teleport improves it.** Same permutation-clique SWAP blowup as TSP, worse. Teleport
routing helps proportionally.
**Verdict.** ★★ but harder than TSP; a later target.

### 11. Job-Shop Scheduling (JSSP)
**What it is.** Schedule operations on machines minimizing makespan. Time-indexed binaries.
**Why dense.** Non-local via precedence chains and per-machine no-overlap constraints — but
globally **sparse**, not all-to-all.
**Hardware status.** Small instances demonstrated on IBM superconducting hardware.
**How teleport improves it.** Only the awkward long-range precedence/machine edges benefit;
per qubit the payoff is smaller than a complete-graph problem.
**Verdict.** ★ — structured, not dense; weaker teleport case.

### 12. Max-SAT / 3-SAT
**What it is.** Satisfy the maximum number of boolean clauses.
**Why dense.** Clause structure — clauses can join arbitrary distant variables, so the
constraint graph is non-local (though density depends on clause-to-variable ratio).
**Hardware status.** Mostly ≤10-variable simulation; no clean IBM heavy-hex Max-SAT demo.
**How teleport improves it.** Non-local clause couplings route via teleport. Payoff scales
with clause spread.
**Verdict.** ★★ — unclaimed on hardware; density is instance-dependent, so pick hard,
high-spread instances.

### 13. Feedback Arc / Vertex Set
**What it is.** Remove fewest edges/vertices to make a directed graph acyclic. Height-ordering
encoding.
**Why sparse.** Each edge induces only local height-comparison terms; coupling graph is
comparatively sparse.
**Hardware status.** No IBM heavy-hex demo.
**How teleport improves it.** Little — sparse coupling means few long-range edges to save.
**Verdict.** ○ — skip for a teleport-routing paper.

### 14. Steiner Tree
**What it is.** Cheapest tree connecting a required vertex subset.
**Why sparse.** Encoding is edge-local and sparse.
**Hardware status.** No heavy-hex demo.
**How teleport improves it.** Minimal — nothing dense to route.
**Verdict.** ○ — skip.

### 15. Hamiltonian Cycle
**What it is.** Does a cycle visiting every vertex once exist? Permutation encoding like TSP
without weights.
**Why medium.** Permutation cliques (medium density) but no distance objective.
**Hardware status.** No heavy-hex demo.
**How teleport improves it.** Permutation cliques benefit like TSP, but it is a decision
problem, less headline value.
**Verdict.** ○ — niche; TSP dominates it.

### 16. Lattice protein folding
**What it is.** Find the minimum-energy fold of a residue chain on a lattice.
**Why medium.** Turn-interaction terms couple non-adjacent residues → medium non-locality.
**Hardware status.** IBM's only run (Robert et al. 2021, 20 qubits) used a **pre-heavy-hex**
chip; recent larger runs are trapped-ion (IonQ). No heavy-hex demo.
**How teleport improves it.** Non-local residue-interaction terms route via teleport; a
heavy-hex protein-folding demo would itself be new.
**Verdict.** ★ — appealing application story, but encoding overhead is heavy.

### 17. MaxCut / weighted MaxCut / Ising spin-glass
**What it is.** Partition graph vertices to maximize cut-edge weight. The QAOA workhorse.
**Why already local.** The flagship 100–156 qubit demos deliberately use graphs that **match
the heavy-hex topology** (3-regular, hardware-native spin glass) → couplings sit on physical
edges → **no routing at all**.
**Hardware status.** Fully demonstrated at 156 qubits (Sachdeva/Q-CTRL; Pelofske/LANL).
**How teleport improves it.** Nothing — there are no long-range edges to save. This is the
control that shows why the *dense* problems above are the real target.
**Verdict.** ○ done — the baseline that exposes the connectivity cheat.

---

## 3. Recommended progression (build order)

1. **Number Partitioning / SK QAOA** (§1) — flagship. Complete graph, no ancillas, no
   infeasibility; isolates routing perfectly. Prove teleport-routed QAOA on hardware here
   first.
2. **Quadratic Knapsack** (§2) — adds a realistic dense constraint; shows the method survives
   inequality-clique overhead.
3. **TSP** (§3) — the recognizable headline, once the method is proven on the clean cases.
4. Optional breadth: dense-input MIS/Max-Clique (§5–6), Graph Coloring (§4).

**Minimal first experiment.** Small SK instance (n = 8–12). Build the QAOA cost layer two
ways — SWAP-routed (`_swap_cx`) vs teleport-routed (`_teleport_cx`), both already in
`QuantumLife/code`. Compare on noiseless sim first (depth, then approximation ratio), then a
single hardware run on marrakesh: **does the approximation ratio beat SWAP, net of
mid-circuit-measurement noise?**

## 4. The honest risk (why this is real research, not a foregone win)

A complete graph has n(n−1)/2 edges → **many** teleported gates per QAOA layer → heavy
ancilla budget and many noisy mid-circuit measurements. The QuantumLife data already shows
strong noise attenuation (ideal `c(d) ≈ −0.29` → hardware `≈ −0.07`). So the central open
question is: **does teleport routing's depth win survive the measurement-noise cost on a
dense problem?** It could lose to SWAP on fidelity even while winning on depth. That
either-way outcome is exactly the contribution — the first honest hardware verdict, where
prior work (Babu et al.) only had simulation depth counts.

## 5. Connection to what already exists
- Reuses `QuantumLife/code` (`research_qtree_teleport.py` `_teleport_cx`,
  `research_qtree_swaplr.py` `_swap_cx`, and the bond/correlation machinery) — only a QAOA
  cost/mixer layer over a chosen QUBO is missing.
- Builds directly on the verified result in
  `research/conclusion_teleportation_longrange.md` and the depth-scaling claim in §6c there.
- Sibling ideas: `qh-10-teleport-vs-swap-routing-benchmark.md` (the routing benchmark this
  operationalizes on real problems), `qh-11-entanglement-reach-device-metric.md` (the
  reach `R` that bounds how far these teleported couplings stay alive),
  `qh-12-swap-depth-sign-inversion.md` (the sign anomaly that must stay controlled when the
  bond becomes a QAOA cost term).

## 6. References (verified)
- Bäumer et al., *Efficient long-range entanglement using dynamic circuits*, PRX Quantum 5,
  030339 (2024) / arXiv:2308.13065 — long-range CNOT via teleport on IBM heavy-hex, 101q apart.
- Babu et al., *Gate teleportation-assisted routing for quantum algorithms*, arXiv:2502.04138
  (2025) — teleport-routed QAOA, **simulation only** on heavy-hex, ~10–25% depth cut.
- Bravyi, Gosset, König, *Quantum advantage with shallow circuits*, Science 362 (2018) /
  arXiv:1704.00690 — constant-depth + measurement separation (theory backbone).
- Lucas, *Ising formulations of many NP problems*, Front. Phys. 2:5 (2014) — every QUBO
  encoding and the "inequalities → highly connected graphs" density warning.
- Sachdeva et al. (Q-CTRL), arXiv:2406.01743 — 156-qubit MaxCut/spin-glass on IBM (topology-matched).
- Pelofske et al. (LANL), arXiv:2312.00997 / npj QI 2024 — whole-chip 127-qubit higher-order
  Ising QAOA, graph built to match heavy-hex.
- *From Circuits to Hardware*, arXiv:2607.11637 — MIS / MDKP / QAP / Market-Share on Heron r1/r2.
- QOBLIB, Nature Comp. Sci. s43588-026-00991-1 — NP-hard benchmark suite incl. MIS on ibm_fez.
