# RUNLOG — Month 3 (QDEP / Quantum Artificial Life) — MAXIMIZE THE LIFE

**Mission (revised 2026-08-24).** Teleport routing is dropped (refuted on this chip — see Appendix A).
New goal: **reproduce Alvarez-Rodriguez 2018 and SCALE it to the largest coherent lineage a 156-qubit
Heron-r2 can sustain** — push both **depth** (generations G) and **width** (parallel lineages), and
report the honest headline number: **LIFE g\*** = the deepest generation whose inheritance correlation
`C(g)` is still statistically nonzero on real hardware, and the population `W` carried alongside it.

**Deliverable.** A preprint-grade result ("largest on-hardware quantum-artificial-life lineage to date:
N generations × W lineages, measured inheritance depth") + a **technical web demo** (data-forward, in the
spirit of QuantumLife but less artistic). Publication → arXiv → *then* a Wikipedia edit citing the
preprint. **This is a scale/application milestone, not a new-physics claim** (keep that honest).

```
cd artificial-life/code
```

---

## The design (locked) and why each piece

The maximize-the-life circuit is the **shallowest, deepest-reaching** lineage we can build:

| flag | choice | why |
|------|--------|-----|
| `--bond-dist 1` | direct adjacent clone (no routing) | no SWAP ladder, no teleport — minimal depth per generation → deepest reach |
| `--founder` | seed genotype 0 on the equator (\|+⟩) | the trait actually varies → `Var(T_0)≈1` → **deep** `C(g)` (fixes the Month-2 g\*=0 null) |
| `--defer-readout` | one terminal readout, no per-gen measure | lineage stays coherent; and the per-gen mid-circuit measure is the single worst noise source on this chip (Appendix A) |
| `--eta 0.9` | paper contraction | `C(g)≈0.9^g` decays slowest → survives the most generations → largest LIFE g\* |
| `--quantum-only` | drop classical + ideal context arms | those run on the statevector (2^(G+1)); dropping them lets G/width scale far past the ~26-qubit sim ceiling — the quantum arm runs on the chip |
| diagonal readout | (default) | the Z-copy lineage signal is deep and depth-robust here |

New metric: **LIFE g\*** = deepest `g` with `|C(g)| > k·σ` (`σ` from repeats + shot floor), no classical
comparison needed — the raw generations-survived count. Prints as `LIFE g*(G=…) [swap] : k2=… k3=…`.

Code added this month to `stage3_teleport.py` (all verified in sim): `--founder`, `--eta`,
`--defer-readout`, `--quantum-only`, `--sim-method matrix_product_state`, `gstar_lifetime`. Meta records
`eta / founder_seed / defer_readout / quantum_only`.

Sanity (noiseless sim): `eta 0.9`, founder, defer, direct → `C0≈0.25`, `c(g)=0.90,0.80,0.70,0.63,…`
(clean `0.9^g`), LIFE g\* saturates at G (so the real ceiling is set by hardware decoherence — a
hardware push, Phase 2). Under FakeFez the lineage still survives to g=10 (`c(10)≈0.29`) — the fake noise
is too benign to find the ceiling, confirming the push must be **live**.

---

## PHASE 1 — design bake-off (3 cheap live runs, ~30s QC each, pick the winner + get error bars)

Goal: confirm the locked design beats its variants and get `C(g)` error bars (`--repeats 5`). All at a
moderate `G=10` so they are cheap and the ranking is clear.

**1a — the deep design (baseline to beat):**
```
python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 10 --gmax 10 --bond-dist 1 --eta 0.9 --founder --defer-readout --shots 8192 --repeats 5 --name qdep_m3p1_deep
```

RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage3_teleport.py --no-sim --routing swap --quantum-only  --gmin 10 --gmax 10 --bond-dist 1 --eta 0.9 --founder --defer-readout  --shots 8192 --repeats 5 --name qdep_m3p1_deep
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2443852 bytes
Backend : ibm_marrakesh  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [39, 58, 82, 94, 102, 113, 130], 'twoq_err_mean': 0.00323, 'twoq_err_max': 0.00536, 'readout_max': 0.08105, 'sx_max': 0.001087}
Note: teleport adds ancillas beyond the chain; the transpiler routes them (initial_layout left unpinned when it exceeds the chain, §6).
Sweep   : G in [10..10]  arms=['quantum_swap']  routing=swap  bond_dist=1  anchors=all  pheno_coupling=0.5  width=1  repeats=5

=== G = 10  (11 generation slots) ===
  -- repeat 1/5  (seed 100) --
  job 1: da63b63otlns739cj19g (8,192 shots) ... done (qpu 4.00s)
  seed 100 [    quantum_swap]  depth   23  C0 0.2496  c(1..10): +0.84, +0.73, +0.64, +0.57, +0.51, +0.43, +0.38, +0.32, +0.28, +0.25
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_deep_quantum_swap_G10_ibm_marrakesh_seed100_20260824-141435_run.json
  -- repeat 2/5  (seed 101) --
  job 1: da63bb3otlns739cj1ig (8,192 shots) ... done (qpu 4.00s)
  seed 101 [    quantum_swap]  depth   23  C0 0.2485  c(1..10): +0.81, +0.71, +0.63, +0.55, +0.48, +0.41, +0.34, +0.28, +0.25, +0.23
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_deep_quantum_swap_G10_ibm_marrakesh_seed101_20260824-141529_run.json
  -- repeat 3/5  (seed 102) --
  job 1: da63bomaa69c739lh8eg (8,192 shots) ... done (qpu 4.00s)
  seed 102 [    quantum_swap]  depth   23  C0 0.2420  c(1..10): +0.83, +0.73, +0.65, +0.58, +0.52, +0.45, +0.37, +0.30, +0.28, +0.24
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_deep_quantum_swap_G10_ibm_marrakesh_seed102_20260824-141543_run.json
  -- repeat 4/5  (seed 103) --
  job 1: da63bs6aa69c739lh8og (8,192 shots) ... done (qpu 4.00s)
  seed 103 [    quantum_swap]  depth   23  C0 0.2467  c(1..10): +0.79, +0.70, +0.62, +0.54, +0.48, +0.39, +0.33, +0.27, +0.25, +0.22
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_deep_quantum_swap_G10_ibm_marrakesh_seed103_20260824-141552_run.json
  -- repeat 5/5  (seed 104) --
  job 1: da63bu43jnrc73ahv5n0 (8,192 shots) ... done (qpu 4.00s)
  seed 104 [    quantum_swap]  depth   23  C0 0.2403  c(1..10): +0.83, +0.72, +0.66, +0.57, +0.51, +0.43, +0.37, +0.33, +0.30, +0.26
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_deep_quantum_swap_G10_ibm_marrakesh_seed104_20260824-141600_run.json
  logical_depth(G=10) : swap=23  teleport=None
  g*(G=10) : Δg* needs both routings + the classical arm (--routing both).
  LIFE g*(G=10) [swap] : k2=10 k3=10  (deepest surviving generation, vs own noise)

--- DONE (sweep) ---
    G   depth(swap)  depth(tel)   Δg*(k2)  Δg*(k3)
   10           23           -        -        -

Headline Δg*: needs both routings + the classical arm (--routing both).
Routing cost (AC-S3.3): constant-depth long-range interaction at the cost of ancillas and classical feed-forward latency; not a free bypass
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_deep_ibm_marrakesh_20260824-141600_summary.json



**1b — per-generation readout (test the mid-circuit-measure cost at scale):** same, **drop**
`--defer-readout`. Expect LIFE g\* to drop — quantifies how much the per-gen measurement hurts.
```
python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 10 --gmax 10 --bond-dist 1 --eta 0.9 --founder --shots 8192 --repeats 5 --name qdep_m3p1_pergen
```

RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 10 --gmax 10 --bond-dist 1 --eta 0.9 --founder --shots 8192 --repeats 5 --name qdep_m3p1_pergen
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2443852 bytes
Backend : ibm_marrakesh  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [39, 58, 82, 94, 102, 113, 130], 'twoq_err_mean': 0.00323, 'twoq_err_max': 0.00536, 'readout_max': 0.08105, 'sx_max': 0.001087}
Note: teleport adds ancillas beyond the chain; the transpiler routes them (initial_layout left unpinned when it exceeds the chain, §6).
Sweep   : G in [10..10]  arms=['quantum_swap']  routing=swap  bond_dist=1  anchors=all  pheno_coupling=0.5  width=1  repeats=5

=== G = 10  (11 generation slots) ===
  -- repeat 1/5  (seed 100) --
  job 1: da63cjeaa69c739lhajg (8,192 shots) ... done (qpu 4.00s)
  seed 100 [    quantum_swap]  depth   34  C0 0.2417  c(1..10): +0.10, +0.11, +0.08, +0.08, +0.06, +0.08, +0.04, +0.03, +0.02, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_pergen_quantum_swap_G10_ibm_marrakesh_seed100_20260824-141725_run.json
  -- repeat 2/5  (seed 101) --
  job 1: da63cljotlns739cj4jg (8,192 shots) ... done (qpu 4.00s)
  seed 101 [    quantum_swap]  depth   34  C0 0.2424  c(1..10): +0.08, +0.10, +0.08, +0.05, +0.04, +0.05, +0.02, +0.02, +0.03, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_pergen_quantum_swap_G10_ibm_marrakesh_seed101_20260824-141733_run.json
  -- repeat 3/5  (seed 102) --
  job 1: da63cnmaa69c739lhb00 (8,192 shots) ... done (qpu 4.00s)
  seed 102 [    quantum_swap]  depth   34  C0 0.2452  c(1..10): +0.11, +0.10, +0.09, +0.07, +0.07, +0.04, +0.05, +0.03, +0.03, +0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_pergen_quantum_swap_G10_ibm_marrakesh_seed102_20260824-141743_run.json
  -- repeat 4/5  (seed 103) --
  job 1: da63cpuaa69c739lhb7g (8,192 shots) ... done (qpu 4.00s)
  seed 103 [    quantum_swap]  depth   34  C0 0.2399  c(1..10): +0.10, +0.11, +0.09, +0.08, +0.06, +0.06, +0.03, +0.03, +0.04, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_pergen_quantum_swap_G10_ibm_marrakesh_seed103_20260824-141752_run.json
  -- repeat 5/5  (seed 104) --
  job 1: da63cs43jnrc73ahv850 (8,192 shots) ... done (qpu 4.00s)
  seed 104 [    quantum_swap]  depth   34  C0 0.2339  c(1..10): +0.12, +0.11, +0.10, +0.09, +0.07, +0.05, +0.04, +0.03, +0.05, +0.03
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_pergen_quantum_swap_G10_ibm_marrakesh_seed104_20260824-141800_run.json
  logical_depth(G=10) : swap=34  teleport=None
  g*(G=10) : Δg* needs both routings + the classical arm (--routing both).
  LIFE g*(G=10) [swap] : k2=2 k3=0  (deepest surviving generation, vs own noise)

--- DONE (sweep) ---
    G   depth(swap)  depth(tel)   Δg*(k2)  Δg*(k3)
   10           34           -        -        -

Headline Δg*: needs both routings + the classical arm (--routing both).
Routing cost (AC-S3.3): constant-depth long-range interaction at the cost of ancillas and classical feed-forward latency; not a free bypass
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_pergen_ibm_marrakesh_20260824-141800_summary.json



**1c — faster contraction (eta 0.7):** does a steeper clone change the reachable depth? Expect a shorter
LIFE g\* (0.9 should win).
```
python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 10 --gmax 10 --bond-dist 1 --eta 0.7 --founder --defer-readout --shots 8192 --repeats 5 --name qdep_m3p1_eta07
```

RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 10 --gmax 10 --bond-dist 1 --eta 0.7 --founder --defer-readout --shots 8192 --repeats 5 --name qdep_m3p1_eta07
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2443852 bytes
Backend : ibm_marrakesh  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [39, 58, 82, 94, 102, 113, 130], 'twoq_err_mean': 0.00323, 'twoq_err_max': 0.00536, 'readout_max': 0.08105, 'sx_max': 0.001087}
Note: teleport adds ancillas beyond the chain; the transpiler routes them (initial_layout left unpinned when it exceeds the chain, §6).
Sweep   : G in [10..10]  arms=['quantum_swap']  routing=swap  bond_dist=1  anchors=all  pheno_coupling=0.5  width=1  repeats=5

=== G = 10  (11 generation slots) ===
  -- repeat 1/5  (seed 100) --
  job 1: da63g343jnrc73ahvflg (8,192 shots) ... done (qpu 4.00s)
  seed 100 [    quantum_swap]  depth   23  C0 0.2468  c(1..10): +0.65, +0.43, +0.31, +0.23, +0.15, +0.10, +0.07, +0.05, +0.04, +0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_eta07_quantum_swap_G10_ibm_marrakesh_seed100_20260824-142453_run.json
  -- repeat 2/5  (seed 101) --
  job 1: da63g5m1vhnc73fmomp0 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [    quantum_swap]  depth   23  C0 0.2496  c(1..10): +0.65, +0.43, +0.29, +0.19, +0.13, +0.09, +0.06, +0.05, +0.04, +0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_eta07_quantum_swap_G10_ibm_marrakesh_seed101_20260824-142502_run.json
  -- repeat 3/5  (seed 102) --
  job 1: da63g7s3jnrc73ahvfvg (8,192 shots) ... done (qpu 4.00s)
  seed 102 [    quantum_swap]  depth   23  C0 0.2490  c(1..10): +0.63, +0.43, +0.31, +0.21, +0.15, +0.11, +0.07, +0.05, +0.03, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_eta07_quantum_swap_G10_ibm_marrakesh_seed102_20260824-142510_run.json
  -- repeat 4/5  (seed 103) --
  job 1: da63g9uaa69c739lhivg (8,192 shots) ... done (qpu 4.00s)
  seed 103 [    quantum_swap]  depth   23  C0 0.2496  c(1..10): +0.63, +0.42, +0.27, +0.19, +0.13, +0.09, +0.05, +0.04, +0.02, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_eta07_quantum_swap_G10_ibm_marrakesh_seed103_20260824-142519_run.json
  -- repeat 5/5  (seed 104) --
  job 1: da63gc43jnrc73ahvgb0 (8,192 shots) ... done (qpu 4.00s)
  seed 104 [    quantum_swap]  depth   23  C0 0.2497  c(1..10): +0.65, +0.44, +0.31, +0.21, +0.16, +0.09, +0.07, +0.04, +0.03, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_eta07_quantum_swap_G10_ibm_marrakesh_seed104_20260824-142528_run.json
  logical_depth(G=10) : swap=23  teleport=None
  g*(G=10) : Δg* needs both routings + the classical arm (--routing both).
  LIFE g*(G=10) [swap] : k2=6 k3=5  (deepest surviving generation, vs own noise)

--- DONE (sweep) ---
    G   depth(swap)  depth(tel)   Δg*(k2)  Δg*(k3)
   10           23           -        -        -

Headline Δg*: needs both routings + the classical arm (--routing both).
Routing cost (AC-S3.3): constant-depth long-range interaction at the cost of ancillas and classical feed-forward latency; not a free bypass
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p1_eta07_ibm_marrakesh_20260824-142528_summary.json


**Pick:** the config with the largest LIFE g\* and cleanest `C(g)` bars (expected: 1a).

**Phase 1d — error-detection post-selection ("herald on the clone chain").** The teleport herald cleaned
data by post-selecting a syndrome; SWAP/direct has no syndrome. To get one, add a **parity-check ancilla**
over the genotype spine and keep only correct-parity shots (symmetry-verification *error detection*, not
correction). **TO BUILD** (`--postselect`, one ancilla + a `chk` register + post-select) — needs a small,
verified code add before any live run (the count-key parsing is fragile; do not burn QC on it untested).
Record kept-fraction vs LIFE-g\* gain. If it lifts g\* by ≥1 generation it earns a place in Phase 2.




-----------------------------------------------------------------------------------------------------------------

## PHASE 2 — push the limit (find the coherence ceiling in generations, then widen)

Take the Phase-1 winner (1a). The ceiling is a **hardware** number — sim can't find it. Run **cheap**:
one command per G, **by hand, one at a time** (no `for` loop), `--repeats 3`. After each run read
`LIFE g*`; only fire the next (bigger) G if g\* is **still climbing**. Stop the moment g\* plateaus —
that plateau IS the answer, no need to run the rest. Budget ~2 min for 2a.

**2a — depth sweep, staged.** Ladder 14 → 18 → 24 (Phase 1 already gave clean data at G=10, so start at
14). Each is a single G (`--gmin == --gmax`).

Step 1 — G=14:
```
python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 14 --gmax 14 --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --name qdep_m3p2_G14
```
If `LIFE g*` < 14 → **plateau found, stop.** If g\* == 14 (still ceilinged by G) → run step 2.

RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 14 --gmax 14 --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --name qdep_m3p2_G14
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2443820 bytes
Backend : ibm_marrakesh  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [82, 94, 113, 130], 'twoq_err_mean': 0.00558, 'twoq_err_max': 0.03491, 'readout_max': 0.19116, 'sx_max': 0.007504}
Note: teleport adds ancillas beyond the chain; the transpiler routes them (initial_layout left unpinned when it exceeds the chain, §6).
Sweep   : G in [14..14]  arms=['quantum_swap']  routing=swap  bond_dist=1  anchors=all  pheno_coupling=0.5  width=1  repeats=3

=== G = 14  (15 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da63k061vhnc73fmov8g (8,192 shots) ... done (qpu 4.00s)
  seed 100 [    quantum_swap]  depth   31  C0 0.2443  c(1..14): +0.84, +0.72, +0.59, +0.55, +0.48, +0.40, +0.35, +0.30, +0.26, +0.23, +0.20, +0.18, +0.16, +0.12
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G14_quantum_swap_G14_ibm_marrakesh_seed100_20260824-144537_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da63psm1vhnc73fmp9l0 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [    quantum_swap]  depth   31  C0 0.2500  c(1..14): +0.85, +0.74, +0.52, +0.50, +0.43, +0.34, +0.28, +0.25, +0.22, +0.19, +0.16, +0.13, +0.12, +0.11
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G14_quantum_swap_G14_ibm_marrakesh_seed101_20260824-144629_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da63q9k3jnrc73ai03vg (8,192 shots) ... done (qpu 4.00s)
  seed 102 [    quantum_swap]  depth   31  C0 0.2484  c(1..14): +0.83, +0.70, +0.43, +0.39, +0.27, +0.30, +0.26, +0.22, +0.19, +0.17, +0.15, +0.12, +0.11, +0.08
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G14_quantum_swap_G14_ibm_marrakesh_seed102_20260824-153801_run.json
  logical_depth(G=14) : swap=31  teleport=None
  g*(G=14) : Δg* needs both routings + the classical arm (--routing both).
  LIFE g*(G=14) [swap] : k2=14 k3=11  (deepest surviving generation, vs own noise)

--- DONE (sweep) ---
    G   depth(swap)  depth(tel)   Δg*(k2)  Δg*(k3)
   14           31           -        -        -

Headline Δg*: needs both routings + the classical arm (--routing both).
Routing cost (AC-S3.3): constant-depth long-range interaction at the cost of ancillas and classical feed-forward latency; not a free bypass
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G14_ibm_marrakesh_20260824-153801_summary.json

Step 2 — G=18:
```
python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 18 --gmax 18 --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --name qdep_m3p2_G18
```
If g\* < 18 → stop. Else → step 3.

RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 18 --gmax 18 --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --name qdep_m3p2_G18
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2443820 bytes
Backend : ibm_fez  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [72], 'twoq_err_mean': 0.02997, 'twoq_err_max': 1.0, 'readout_max': 0.15479, 'sx_max': 0.001286}
Note: teleport adds ancillas beyond the chain; the transpiler routes them (initial_layout left unpinned when it exceeds the chain, §6).
Sweep   : G in [18..18]  arms=['quantum_swap']  routing=swap  bond_dist=1  anchors=all  pheno_coupling=0.5  width=1  repeats=3

=== G = 18  (19 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da64reuaa69c739ljcb0 (8,192 shots) ... done (qpu 4.00s)
  seed 100 [    quantum_swap]  depth   39  C0 0.2497  c(1..18): +0.77, +0.68, +0.58, +0.50, +0.42, +0.37, +0.26, +0.27, +0.21, +0.18, +0.10, +0.08, +0.08, +0.07, +0.05, +0.04, +0.03, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G18_quantum_swap_G18_ibm_fez_seed100_20260824-155726_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da64rhuaa69c739ljce0 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [    quantum_swap]  depth   39  C0 0.2427  c(1..18): +0.76, +0.66, +0.58, +0.51, +0.43, +0.39, +0.28, +0.28, +0.21, +0.18, +0.12, +0.11, +0.10, +0.09, +0.06, +0.07, +0.06, +0.05
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G18_quantum_swap_G18_ibm_fez_seed101_20260824-155736_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da64rke1vhnc73fmqg70 (8,192 shots) ... done (qpu 4.00s)
  seed 102 [    quantum_swap]  depth   39  C0 0.2484  c(1..18): +0.73, +0.66, +0.56, +0.49, +0.40, +0.37, +0.27, +0.27, +0.20, +0.18, +0.12, +0.10, +0.11, +0.09, +0.06, +0.06, +0.05, +0.05
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G18_quantum_swap_G18_ibm_fez_seed102_20260824-155749_run.json
  logical_depth(G=18) : swap=39  teleport=None
  g*(G=18) : Δg* needs both routings + the classical arm (--routing both).
  LIFE g*(G=18) [swap] : k2=13 k3=10  (deepest surviving generation, vs own noise)

--- DONE (sweep) ---
    G   depth(swap)  depth(tel)   Δg*(k2)  Δg*(k3)
   18           39           -        -        -

Headline Δg*: needs both routings + the classical arm (--routing both).
Routing cost (AC-S3.3): constant-depth long-range interaction at the cost of ancillas and classical feed-forward latency; not a free bypass
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G18_ibm_fez_20260824-155749_summary.json
(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ 




Step 3 — G=13  10 clean 14 degraded 18 garbage:
```
python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 13 --gmax 13 --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --name qdep_m3p2_G24
```

RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 13 --gmax 13 --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --name qdep_m3p2_G24
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2443788 bytes
Backend : ibm_fez  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [72], 'twoq_err_mean': 0.03996, 'twoq_err_max': 1.0, 'readout_max': 0.15479, 'sx_max': 0.001286}
Note: teleport adds ancillas beyond the chain; the transpiler routes them (initial_layout left unpinned when it exceeds the chain, §6).
Sweep   : G in [13..13]  arms=['quantum_swap']  routing=swap  bond_dist=1  anchors=all  pheno_coupling=0.5  width=1  repeats=3

=== G = 13  (14 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da64t8rotlns739cl9eg (8,192 shots) ... done (qpu 4.00s)
  seed 100 [    quantum_swap]  depth   29  C0 0.2498  c(1..13): +0.75, +0.66, +0.55, +0.48, +0.40, +0.36, +0.26, +0.27, +0.21, +0.19, +0.11, +0.10, +0.09
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G24_quantum_swap_G13_ibm_fez_seed100_20260824-160115_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da64tb61vhnc73fmqi50 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [    quantum_swap]  depth   29  C0 0.2473  c(1..13): +0.76, +0.68, +0.56, +0.49, +0.40, +0.34, +0.25, +0.24, +0.18, +0.17, +0.10, +0.10, +0.08
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G24_quantum_swap_G13_ibm_fez_seed101_20260824-160125_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da64tdm1vhnc73fmqi80 (8,192 shots) ... done (qpu 4.00s)
  seed 102 [    quantum_swap]  depth   29  C0 0.2455  c(1..13): +0.76, +0.68, +0.57, +0.51, +0.43, +0.37, +0.28, +0.26, +0.20, +0.18, +0.12, +0.11, +0.09
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G24_quantum_swap_G13_ibm_fez_seed102_20260824-160137_run.json
  logical_depth(G=13) : swap=29  teleport=None
  g*(G=13) : Δg* needs both routings + the classical arm (--routing both).
  LIFE g*(G=13) [swap] : k2=13 k3=10  (deepest surviving generation, vs own noise)

--- DONE (sweep) ---
    G   depth(swap)  depth(tel)   Δg*(k2)  Δg*(k3)
   13           29           -        -        -

Headline Δg*: needs both routings + the classical arm (--routing both).
Routing cost (AC-S3.3): constant-depth long-range interaction at the cost of ancillas and classical feed-forward latency; not a free bypass
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G24_ibm_fez_20260824-160137_summary.json


-FEZ is broken retry on marrakesh
````
python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 14 --gmax 14 --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --backend ibm_marrakesh --name qdep_m3p2_G14 
````
(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 14 --gmax 14 --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --backend ibm_marrakesh --name qdep_m3p2_G14 
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2443788 bytes
Backend : ibm_marrakesh  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [82, 94, 113, 130], 'twoq_err_mean': 0.00323, 'twoq_err_max': 0.00892, 'readout_max': 0.03223, 'sx_max': 0.000792}
Note: teleport adds ancillas beyond the chain; the transpiler routes them (initial_layout left unpinned when it exceeds the chain, §6).
Sweep   : G in [14..14]  arms=['quantum_swap']  routing=swap  bond_dist=1  anchors=all  pheno_coupling=0.5  width=1  repeats=3

=== G = 14  (15 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da650duaa69c739ljhu0 (8,192 shots) ... done (qpu 4.00s)
  seed 100 [    quantum_swap]  depth   31  C0 0.2495  c(1..14): +0.82, +0.74, +0.63, +0.56, +0.49, +0.41, +0.36, +0.32, +0.28, +0.26, +0.22, +0.20, +0.17, +0.14
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G14_quantum_swap_G14_ibm_marrakesh_seed100_20260824-161843_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da655guaa69c739ljo00 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [    quantum_swap]  depth   31  C0 0.2495  c(1..14): +0.84, +0.75, +0.60, +0.53, +0.48, +0.38, +0.33, +0.30, +0.26, +0.22, +0.21, +0.19, +0.16, +0.14
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G14_quantum_swap_G14_ibm_marrakesh_seed101_20260824-163917_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da65f5m1vhnc73fmr5ug (8,192 shots) ... done (qpu 4.00s)
  seed 102 [    quantum_swap]  depth   31  C0 0.2476  c(1..14): +0.83, +0.74, +0.59, +0.53, +0.44, +0.37, +0.33, +0.30, +0.25, +0.23, +0.20, +0.18, +0.16, +0.13
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G14_quantum_swap_G14_ibm_marrakesh_seed102_20260824-164324_run.json
  logical_depth(G=14) : swap=31  teleport=None
  g*(G=14) : Δg* needs both routings + the classical arm (--routing both).
  LIFE g*(G=14) [swap] : k2=14 k3=14  (deepest surviving generation, vs own noise)

--- DONE (sweep) ---
    G   depth(swap)  depth(tel)   Δg*(k2)  Δg*(k3)
   14           31           -        -        -

Headline Δg*: needs both routings + the classical arm (--routing both).
Routing cost (AC-S3.3): constant-depth long-range interaction at the cost of ancillas and classical feed-forward latency; not a free bypass
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m3p2_G14_ibm_marrakesh_20260824-164324_summary.json




Step 2 — G=18 RETESTING:
```
python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin 18 --gmax 18 --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --backend ibm_marrakesh --name qdep_m3p2_G18
```





Watch each run's chain line: `twoq_err_max` / `readout_max`. Bad edge dragged in by auto-chain =
ceiling is chain-limited not physics — rerun / pin a cleaner `--backend`. Qubit budget ≈ `2·(G+1)`
(G=24 ≈ 50 qubits — fine on 156). **Headline = the G where LIFE g\* saturates** (the g_sat above).

**2b — width (population), small.** At the deepest clean G (`<G_best>` = the saturating G from 2a),
add parallel lineages. `--width 4` submits 4 independent lineages and pools them (tighter σ + a real
population). Qubit count per job unchanged; width costs more jobs, not more qubits. Single command:
```
python stage3_teleport.py --no-sim --routing swap --quantum-only --gmin <G_best> --gmax <G_best> --bond-dist 1 --eta 0.9 --founder --defer-readout --sv-max-qubits 200 --shots 8192 --repeats 3 --width 4 --name qdep_m3p2_pop
```
**Headline number:** *"coherent quantum inheritance sustained for LIFE g\* = N generations across W = 4
lineages on ibm_marrakesh (156-qubit Heron r2)."*

---

## PHASE 3 — optimize the winner into a web demo + preprint

Lock the Phase-2 config. Products:

**Figures (preprint-grade, from the run.json files):**
1. `C(g)` decay curve — hardware vs ideal `0.9^g`, error bars → the measured **lifetime**.
2. **LIFE g\* vs G** — the scaling curve; the plateau is the coherence ceiling.
3. **Population grid** — `W × G` heatmap of per-lineage trait (the "population" visual).
4. Circuit depth vs G — shallow/linear → feasibility.

**Web demo (technical, self-contained HTML Artifact):** animate the lineage growing generation by
generation; overlay the *measured* `C(g)` decay and the ideal; show the qubit chain used, the live depth
counter, and the LIFE-g\* readout. Data-forward, not artistic — every number is a real measurement. Built
from the Phase-2 `run.json` / summary files. (I can build this Artifact once Phase-2 data lands.)

**Publication path (be honest):** Wikipedia cannot cite a self-run experiment directly. Sequence:
(1) write the arXiv note (reproduce 2018 + scale to N×W on hardware, methods + data + code);
(2) post the web demo as the outreach artifact; (3) *then* edit the Wikipedia "Quantum artificial life"
article to cite the preprint as a hardware-scale follow-up. The claim is **scale/application progress**
("movement in the field"), not novel physics — the same honest framing QuantumLife used.

---

## Appendix A — why teleport routing was dropped (Month-3 first half, settled on hardware)

Founder-seed fix validated live (`ibm_marrakesh`, C0≈0.19–0.25, deep `C(g)`, resolving the Month-2 null).
Then the teleport-vs-SWAP finale, across the full intervention ladder:

| setup | outcome | Δg\* |
|-------|---------|------|
| per-gen readout, feed-forward | teleport dies g=2, swap g=4 | **−2/−3** (live) |
| defer readout, feed-forward | parity | 0 (sim) |
| defer + heralded, bd 5→9→13 | teleport constant depth **7** vs swap 24→40→56 | 0 (sim; swap never dies) |
| **defer + heralded, LIVE** | teleport 7 c(1..3) 0.48/0.22/0.11 vs swap 40 **0.47/0.27/0.15** | **swap wins** |

**Verdict: on current Heron-r2, SWAP-ladder routing BEATS teleport for this correlation — every config,
including the full QuantumLife setup (deferred readout + heralded constant-depth-7 teleport).** SWAP is
all-gates (2-qubit error ~0.3%, robust to depth 40); teleport is measurement-heavy (this run hit
`readout_max 0.214` — 21% on one qubit) and herald keeps ~1.6% of shots. `logical_depth` favours teleport
7-vs-40; **effective error favours swap** — measurement is the dominant channel.

**Why QuantumLife's teleport DID win and QDEP's doesn't** (`QuantumLife/research/conclusion_teleportation_longrange.md`):
QuantumLife is ONE spatial long-range bond (distance 12, `c(d)`), a *depth-fragile coherent* observable
that the depth-31 SWAP ladder decohered to a wrong-signed floor — so SWAP failed and teleport (depth 9)
won (−0.065 vs +0.040, p<0.05), on a calibration with **worse gates (twoq 0.032) but better readout
(0.082)**. QDEP is a *series* of G bonds (temporal lineage), a *depth-robust classical-copy* observable,
on a run with **great gates (0.011) but a 21% readout qubit** — the opposite error balance. Teleport wins
only when: one/few genuinely long-range coherent bonds, a depth-fragile signal so SWAP fails, and
gate-error ≫ readout-error. QuantumLife hit all three; QDEP hits none. Not a regression — a different
circuit type (single spatial link vs temporal lineage chain) on an inverted error balance.

The founder/eta/defer/quantum-only machinery built here is the reusable payoff → it powers the
maximize-the-life program above.
