# QuantumLife — Thesis Assessment folder

Honest scoping of whether the QuantumLife program's strongest empirical result — the real-hardware
teleport-vs-SWAP long-range routing head-to-head — can become a defensible thesis study.

## Contents
- [`teleport-routing-crossover-thesis-assessment.md`](teleport-routing-crossover-thesis-assessment.md)
  — the full assessment: what was measured (exact numbers), the candidate claim, the corrected physics
  (why the one-line "law" is incomplete), bull case, bear case, textbook-vs-novel dissection, the study
  design, falsifiable predictions, how it fits the wider program, and the mandatory zero-QC + literature
  checks to run before committing.

## One-paragraph summary
On `ibm_marrakesh` a constant-*logical*-depth teleported long-range CNOT produced a reproducible,
significant long-range correlation (−0.065, 4/4 seeds, p<0.05) where a depth-31 SWAP ladder washed out
— but on Heron-r2 (QDEP) the same idea was **refuted** (teleport lost to SWAP; readout ≫ 2q error
inverts the advantage). The proposed "law" (*teleport wins iff `SWAP_depth·ε_2q > readout_cost·ε_readout`*)
is **half-real** (it omits the O(d) Bell-pair distribution cost, the decisive term) and **not new** (the
dynamic-circuit-vs-SWAP tradeoff is published). What could still be a study: an **empirical,
calibration-driven crossover map** that reconciles the win and the refutation and tests a *corrected*
predictive model on a held-out backend — hardware-first and falsifiable, but with a
device-characterization ceiling, not novel physics. **Do the zero-QC physical-cost sim + the literature
check first (§11)** — they decide the framing for free.

## Source material (not in this folder)
- `../research/conclusion_teleportation_longrange.md` — the hardware result
- `../code/research_qtree_teleport.py`, `../code/research_qtree_swaplr.py` — the two arms
- QDEP memory (`qdep-setup-bug-fix`) — the contradicting Heron-r2 refutation
