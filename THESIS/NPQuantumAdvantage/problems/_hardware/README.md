# Deferred hardware appendix (old F7) — obstruction, not a headline

This directory is the **deferred, obstruction-labelled** QAOA feasibility appendix.
It is **not** part of the √2 map and makes **no** advantage claim.

- `qaoa_appendix.py` — converts P4's sparse/local kernel QUBO to an Ising cost
  Hamiltonian and runs a fixed-depth (p=1) QAOA on **noiseless Aer** as a
  sign/correctness gate, reporting the best-sampled cost against a matched classical
  greedy baseline and the exact optimum.

## Why deferred / why obstruction
- QAOA has **no provable query speedup** — unlike Dürr–Høyer/Grover, which carries the
  BBBV-optimal quadratic query advantage that is this study's headline.
- Low-depth QAOA on these problems is **locality-obstructed** (Farhi, Gamarnik &
  Gutmann 2020, arXiv:2004.09002).
- **QDEP** already showed the teleport/routing advantage does **not survive readout
  error on Heron** — on modern hardware the advantage inverts. So the real-device run
  is the *obstruction result*, not a hole in the map.
- The headline (the √2 map) needs **zero** QC. Real-device submission is deferred:
  `--backend <name>` only prints a deferral notice. When run manually, JSONs land in
  `research_runs/` with live calibration (2q err, readout err) recorded per the
  number-partitioning / QuantumLife workflow.
