# QH Idea 10 — Teleport-vs-SWAP Long-Range Gate Routing: at what on-chip distance does teleported routing beat a SWAP ladder in fidelity-per-depth?

**Tag: QUANTUM · qh · effort: medium**

## Pitch
Every limited-connectivity superconducting chip pays a "SWAP tax": a compiler routes a
long-range 2-qubit gate by dragging one qubit across the lattice with SWAPs, and that
`O(distance)` depth is a dominant NISQ error source. Teleported routing (one Bell pair +
mid-circuit measure + classical feed-forward) applies the *same* logical gate at
*constant* depth. The QuantumTree teleport run already showed the low-depth route holds a
long-range correlation the depth-31 SWAP equivalent washes out. This idea strips the art
and makes it a clean **routing benchmark**: for a single long-range CNOT, measure depth,
two-qubit-gate count, and gate fidelity as a function of separation, and report the
**crossover distance `d*`** beyond which teleport-routing wins.
**Paper strength score: 76/100** — directly useful to NISQ compilation and cleanly
falsifiable; docked because "teleport wins at long range" is expected in principle, so the
contribution is the *measured* `d*` and the honest fidelity accounting, not a surprise.

## How it becomes a study
**Research question:** For a single long-range CNOT on Heron r2, at what qubit separation
`d*` does teleported routing exceed SWAP-ladder routing in gate fidelity at fixed logical
task, and how does `d*` move with device error rates?
**Hypothesis:** There is a finite `d*`; below it the SWAP ladder is as good or better
(teleport pays a fixed Bell-pair + feed-forward overhead), above it teleport wins and the
gap grows with distance.
**Method:** Build both implementations of `CX(q_i,q_j)` (already exist as
`research_qtree_teleport._teleport_cx` and `research_qtree_swaplr._swap_cx`). Isolate the
gate on a known input, sweep `d = 6,12,18,24,30,36` qubits. Estimate fidelity three ways,
cheapest first: (a) **noiseless Aer** to fix the ideal reference; (b) **noisy Aer** with a
depolarizing + readout model scaled to live calibration; (c) a small **hardware** confirm
at 2–3 distances. Hold shots and the qubit chain fixed; record `qc.depth()` and 2q count
(deterministic, zero-cost).
**Baseline:** the SWAP ladder is the baseline by construction; the noiseless sim is the
ideal reference both must reproduce.
**Metrics:** process/state fidelity (or a correlation-observable proxy) vs `d`; logical
depth and 2q-gate count vs `d`; the crossover `d*`; fidelity-per-depth ratio.
**Novel contribution:** a measured, device-referenced crossover distance for
teleport-vs-SWAP routing of a single long-range gate — the number a pass-manager needs to
decide which routing to emit.

## Connection to what already exists
Reuses the two circuit builders and the `c(d)`/`bond_correlations` machinery in
`QuantumLife/code/`. Sits next to `viz-9-teleport-grown-tree` (which established the
correlation result inside the art pipeline) and the README's `qh-5` GHZ-crossover stub,
but asks the compiler question — single-gate routing cost/fidelity vs distance — not GHZ
state prep and not art.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** Everything starts in simulation, so the paper is mostly written before touching
QC; the depth curves are deterministic; the crossover is a crisp, citable figure that a
compiler audience wants.
**Bear:** Feed-forward latency and mid-circuit-measurement error on current hardware may
push `d*` out past the useful register, i.e. SWAP wins everywhere reachable — a weaker
(but still honest) headline.
**Likely outcome:** A finite `d*` in the noisy model around the teens of qubits, confirmed
at one or two hardware distances, with a clean fidelity-per-depth crossover figure.
**Value if null:** If teleport never beats SWAP on today's Heron, that itself is a useful
compilation result — it bounds when dynamic-circuit routing is premature on this hardware
generation and tells compiler writers to keep SWAP-routing until feed-forward latency drops.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Where is the teleport-vs-SWAP routing crossover for a long-range gate
on Heron r2? **Single defended claim:** there is a measurable crossover distance beyond
which constant-depth teleported routing beats SWAP-ladder routing in fidelity-per-depth.
**Why it fits 6–8 pp:** two existing circuit builders, one distance sweep, a three-tier
(noiseless/noisy/hardware) fidelity ladder, one crossover figure. **Target venue:** IEEE
Quantum Week (QCE) / quantum-software-and-compilation track. **Compelling-study
likelihood: 76/100.**
