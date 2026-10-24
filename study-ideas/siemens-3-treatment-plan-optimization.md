# Siemens Idea 3 — QAOA Beam Planning: does quantum optimization of radiotherapy beam-angle/fluence selection reach any crossover against the classical planner on a NISQ-sized problem?

**Tag: QUANTUM · siemens · effort: medium**

## Pitch
Radiotherapy treatment planning — choosing beam angles and fluence to hit the tumour and spare healthy tissue — is a combinatorial optimization Siemens/Varian solves classically in Eclipse/Ethos every day. Cast the beam-angle-selection subproblem as a QUBO and it becomes a natural **QAOA / quantum-annealing** target: a concrete, named, product-relevant optimization rather than an abstract Max-Cut. The honest question is whether quantum optimization reaches *any* regime of solution quality or speed where it competes, given that NISQ QAOA advantage is unproven.
**Paper strength score: 66/100** — concrete and NISQ-closer than dose MC, and the clinical framing is strong, but "QAOA on a real-world QUBO, no clear advantage" is a well-trodden genre; docked for near-certain null on advantage.

## How it becomes a study
**Research question:** For a small beam-angle-selection QUBO, how does QAOA solution quality (approximation ratio) scale with depth p and problem size against the classical optimum, and is there any size/depth where it is competitive?
**Hypothesis (falsifiable):** QAOA reaches the classical optimum only for trivially small instances; beyond a modest number of candidate angles the approximation ratio degrades below a greedy/classical solver at any depth reachable on hardware.
**Method:** Encode beam-angle selection (pick k of N candidate angles minimising a dose-to-organ-at-risk penalty) as a QUBO. Run QAOA at increasing depth p on statevector, noisy sim, then small hardware instances. Compare against brute-force optimum (small N) and a classical heuristic (greedy / simulated annealing) at larger N.
**Baseline:** Classical exact optimum (small N) and a standard classical heuristic (same QUBO, same objective).
**Metrics:** approximation ratio vs classical optimum; depth p needed for a target ratio; largest N where QAOA matches the heuristic; wall-clock and shots to solution.
**Novel contribution:** A quantified map of QAOA competitiveness on the *specific* radiotherapy beam-selection QUBO — a named Siemens/Varian problem rather than a synthetic graph.

## Connection to what already exists
Shares the QUBO-density / heavy-hex framing of `qh-13-np-problems-teleport-routing.md` and the teleport-routed QAOA build already queued — the beam-selection QUBO could become a *clinically named* instance for that same routing machinery. Reuses the SK/QAOA tooling from the Number Partitioning epic.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** A clinically concrete QAOA target gives the teleport-routed-QAOA work a real-world QUBO to point at; the planning framing sells to Siemens.
**Bear:** The result is almost certainly "classical heuristic wins," and the genre is crowded with QAOA-on-real-problem papers.
**Likely:** QAOA matches classical only for toy N; honest negative scaling beyond.
**Value if null:** Establishes the problem-size threshold below which quantum planning is even conceivable — a scaling datapoint for Siemens, and a named benchmark instance for the repo's routing studies.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Is QAOA competitive on the radiotherapy beam-selection QUBO at NISQ scale? **Single defended claim:** the approximation ratio falls below a classical heuristic beyond N candidate angles, at any reachable depth. **Why 6–8 pp:** one QUBO family, one approximation-ratio-vs-size figure. **Target venue:** IEEE QCE workshop. **Compelling-study likelihood: 66/100.**
