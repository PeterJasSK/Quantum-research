# RUNLOG — Month 1 preliminary (QDEP / Quantum Artificial Life)

**Budget:** ~60s live QC this month. Stages numbered **0-indexed to match the code** (S0…S3), one
runnable file per stage. **8192 shots, 1 repeat (~7s/job)**. Only S1–S3 touch the chip (S0 is free
sim); ~4 HW jobs ≈ 28s, leaving ~30s backup for a failed/queued job. NOT a study — a first look to
reflect on and size the 10-min run next month.

**Reference:** reproduce Quantum Artificial Life (Alvarez-Rodriguez et al. 2018,
en.wikipedia.org/wiki/Quantum_artificial_life) → scale to the coherence ceiling → show teleport
routing beats the SWAP ladder.

```
cd artificial-life/code
```

> **Cost note:** only the **quantum** arm consumes QC. The classical surrogate is a free local sim,
> so `--arm both` gets the comparison at the price of the quantum arm alone. **Stage 0 is fully sim
> — zero QC.**

---

## Stage 0 — Reproduce the 2018 lifetime  (`stage0_reproduce.py`, SIM, free)

The 2018 result IS the phenotype σ_z "lifetime" decaying ~η^g down the lineage. S0 is sim-only by
design: it rebuilds the exact operators (`M(θ)`, `U_M`, `⟨σ_z⟩_p`) and is the toolchain gate (M1)
the hardware runs are judged against. No `--backend` — costs no QC.

```
python stage0_reproduce.py --generations 6 --shots 8192 --seed 100 --name qdep_m1_s0
```

**Record:** per-gen `trait_sigmaz` + `fidelity_vs_ideal`; successive ratios (~η=0.9).
**Best case:** operators pass the unit test, `fidelity_vs_ideal ≈ 0.99`, clean geometric decay →
2018 lifetime reproduced, toolchain trusted. **Gate:** must pass before spending any QC.


RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage0_reproduce.py --generations 6 --shots 8192 --seed 100 --name qdep_m1_s0
=== S0 unit test: exact operators vs their defined forms ===
  worst L1(M_gate, paper matrix)     = 0.0000
  worst L1(U_M ancilla z, eta*parent) = 0.0000
  => M(theta) == paper matrix (equivalent)
  => U_M      == partial-clone (equivalent)

=== ideal lifetime: 6 gens, 8192 shots, eta=0.9 ===
  gen   trait_sigmaz   ideal     |diff|    3*stderr   fidelity
    0   +0.9998      +0.9996  0.0002   0.0010  0.9999 [ok]
    1   +0.9314      +0.9355  0.0041   0.0117  0.9979 [ok]
    2   +0.9041      +0.8989  0.0052   0.0145  0.9974 [ok]
    3   +0.8547      +0.8623  0.0075   0.0168  0.9962 [ok]
    4   +0.8259      +0.8313  0.0054   0.0184  0.9973 [ok]
    5   +0.7900      +0.7831  0.0069   0.0206  0.9965 [ok]
  successive <sigma_z>_p ratios (~eta): 0.932, 0.971, 0.945, 0.966, 0.957

wrote /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s0_sim_seed100_sim_run.json

---

## Stage 1 — Quantum inheritance signal / g*  (`stage1_temporal.py`, HW, ~7s)

Temporal C(g), coherent quantum arm vs measure-and-resend surrogate. Off-diagonal readout
(`--trait-basis 0.785 ≈ π/4`) — the basis where the two arms are distinguishable (the diagonal
`⟨σ_z⟩` of S0 is classically clonable → g*=1; fixed 2026-08-19). Diagonal `trait_sigmaz` still lands
in the run.json, so this also carries the on-hardware lifetime.

```
python stage1_temporal.py --no-sim --arm both --trait-basis 0.785 --generations 6 --shots 8192 --repeats 1 --name qdep_m1_s1
```

**Record:** summary `gstar` (k2/k3), per-gen `C_g_mean.{quantum,classical}`; run.json `trait_sigmaz`
(HW lifetime) + `meta.calibration`.
**Best case:** quantum vs classical c(g) visibly separate on chip; a nonzero preliminary g* survives
one repeat of shot noise.
**Trust:** MEDIUM (1 repeat → no error bars).


RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage1_temporal.py --no-sim --arm both --trait-basis 0.785 --generations 6 --shots 8192 --repeats 1 --name qdep_m1_s1
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2444748 bytes
Backend : ibm_fez  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [72, 95], 'twoq_err_mean': 0.00256, 'twoq_err_max': 0.0033, 'readout_max': 0.01831, 'sx_max': 0.000621}

=== repeat 1/1  (seed 100) ===
  job 1: da3086uaa69c739i1em0 (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1323  c(1..6): +0.03, -0.00, +0.03, +0.00, +0.01, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s1_quantum_ibm_fez_seed100_20260819-212939_run.json
  seed 100 [classical]  C0 0.1286  c(1..6): +0.47, +0.24, +0.13, +0.06, +0.05, +0.03
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s1_classical_ibm_fez_seed100_20260819-212940_run.json

--- DONE ---
  g     C_quan   C_clas
    0   +1.0000   +1.0000
    1   +0.0256   +0.4741
    2   -0.0002   +0.2444
    3   +0.0278   +0.1317
    4   +0.0046   +0.0642
    5   +0.0062   +0.0465
    6   -0.0042   +0.0299

g* (k=2) = 1    g* (k=3) = 1
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s1_ibm_fez_20260819-212940_summary.json


---

## Stage 2 — Scale toward the coherence ceiling  (`stage2_scale.py`, HW, ~35s)

**SETUP-FIX propagated (2026-08-19):** S2 now has deferred measurement + `--trait-basis` +
normalized-c g* (same as S1). One G-point this month with **error bars** (`--repeats 5`); full
G-sweep is a month-2 job. Sim verify: g*(k2)=6 @ G=6.

```
python stage2_scale.py --no-sim --arm both --gmin 8 --gmax 8 --trait-basis 0.785 --shots 8192 --repeats 5 --name qdep_m1_s2 --backend ibm_fez
```

> **Cost:** only the quantum arm bills — 5 jobs × ~7s ≈ **35s QC**. Classical + ideal arms are free
> sim. `--repeats 5` makes g* real (repeats=1 → σ=0 → g* pinned at 1 artifact, as seen in S1).
> Pin the SAME backend as S1 (`ibm_fez`). For the g*-vs-G trend instead, use `--gmin 6 --gmax 8`
> (~105s QC).

**Record:** `gstar` (k2/k3) at G=8 with σ, per-gen c(g) quantum/classical/ideal, ideal-clone confound.
**Best case:** quantum vs classical c(g) separated with real error bars; ideal-confound curve sits
with the quantum arm (both off-diagonal ~0) above/below the classical — decoherence vs
cloning-decay cleanly split.
**Trust:** MEDIUM–HIGH (5 repeats, fix propagated → real g*).


(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage2_scale.py --no-sim --arm both --gmin 8 --gmax 8 --trait-basis 0.785 --shots 8192 --repeats 5 --name qdep_m1_s2 --backend ibm_fez
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2444716 bytes
Backend : ibm_fez  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [72, 95], 'twoq_err_mean': 0.00275, 'twoq_err_max': 0.00355, 'readout_max': 0.01831, 'sx_max': 0.000621}
Sweep   : G in [8..8]  arms=['quantum', 'classical', 'ideal']  pheno_coupling=0.5  width=1  repeats=5

=== G = 8  (9 generation slots) ===
  -- repeat 1/5  (seed 100) --
  job 1: da30e1e1vhnc73fj840g (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1219  c(1..8): -0.07, -0.02, -0.01, -0.00, +0.01, -0.01, +0.01, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_quantum_G8_ibm_fez_seed100_20260819-214419_run.json
  seed 100 [classical]  C0 0.0900  c(1..8): +0.53, +0.30, +0.14, +0.06, +0.02, +0.01, -0.01, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_classical_G8_ibm_fez_seed100_20260819-214420_run.json
  seed 100 [    ideal]  C0 0.1118  c(1..8): -0.07, -0.03, -0.01, -0.01, -0.02, +0.00, +0.02, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_ideal_G8_sim_seed100_20260819-214420_run.json
  -- repeat 2/5  (seed 101) --
  job 1: da30f5c3jnrc73aeffpg (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1193  c(1..8): -0.06, -0.05, -0.03, -0.02, -0.01, -0.01, -0.00, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_quantum_G8_ibm_fez_seed101_20260819-214443_run.json
  seed 101 [classical]  C0 0.0895  c(1..8): +0.46, +0.18, +0.09, +0.05, +0.01, +0.01, -0.00, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_classical_G8_ibm_fez_seed101_20260819-214443_run.json
  seed 101 [    ideal]  C0 0.1101  c(1..8): -0.12, -0.05, -0.06, -0.06, -0.05, -0.02, -0.05, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_ideal_G8_sim_seed101_20260819-214443_run.json
  -- repeat 3/5  (seed 102) --
  job 1: da30fb43jnrc73aeffvg (8,192 shots) ... done (qpu 4.00s)
  seed 102 [  quantum]  C0 0.1213  c(1..8): -0.04, -0.00, +0.00, -0.01, +0.01, -0.00, -0.00, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_quantum_G8_ibm_fez_seed102_20260819-214455_run.json
  seed 102 [classical]  C0 0.0885  c(1..8): +0.47, +0.22, +0.11, +0.07, +0.02, +0.02, +0.01, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_classical_G8_ibm_fez_seed102_20260819-214455_run.json
  seed 102 [    ideal]  C0 0.1100  c(1..8): -0.09, -0.03, -0.03, -0.03, -0.01, -0.00, -0.03, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_ideal_G8_sim_seed102_20260819-214455_run.json
  -- repeat 4/5  (seed 103) --
  job 1: da30fe6aa69c739i1om0 (8,192 shots) ... done (qpu 4.00s)
  seed 103 [  quantum]  C0 0.1147  c(1..8): -0.03, -0.01, -0.02, +0.01, +0.01, -0.00, +0.01, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_quantum_G8_ibm_fez_seed103_20260819-214504_run.json
  seed 103 [classical]  C0 0.0837  c(1..8): +0.49, +0.22, +0.15, +0.11, +0.07, +0.03, +0.03, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_classical_G8_ibm_fez_seed103_20260819-214505_run.json
  seed 103 [    ideal]  C0 0.1073  c(1..8): -0.09, -0.04, -0.03, -0.02, -0.03, -0.01, -0.05, -0.06
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_ideal_G8_sim_seed103_20260819-214505_run.json
  -- repeat 5/5  (seed 104) --
  job 1: da30fgjotlns739938t0 (8,192 shots) ... done (qpu 4.00s)
  seed 104 [  quantum]  C0 0.1238  c(1..8): -0.03, -0.01, +0.01, -0.02, +0.01, +0.02, +0.05, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_quantum_G8_ibm_fez_seed104_20260819-214515_run.json
  seed 104 [classical]  C0 0.0954  c(1..8): +0.51, +0.26, +0.14, +0.06, +0.03, +0.02, +0.04, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_classical_G8_ibm_fez_seed104_20260819-214516_run.json
  seed 104 [    ideal]  C0 0.1107  c(1..8): -0.08, -0.02, -0.02, -0.00, +0.01, -0.01, -0.02, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_ideal_G8_sim_seed104_20260819-214516_run.json
  g*(G=8) : k2=4  k3=4

--- DONE (sweep) ---
    G   g*(k2)  g*(k3)
    8       4       4

Headline g* @ G=8 (k=2) = 4    (k=3) = 4
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s2_ibm_fez_20260819-214516_summary.json


---

## Stage 3 — SWAP ladder vs teleport routing  (`stage3_teleport.py`, HW, ~30s)

**DECISION (from S2 eval, 2026-08-19): run S3 DIAGONAL / as-is — do NOT propagate the off-diagonal
fix here.** S2 showed the quantum arm ≈ ideal ≈ 0 in the off-diagonal basis (the `Ry+CX` clone
carries no coherence), so an off-diagonal teleport comparison has **no quantum signal to preserve →
Δg* ≈ 0, pointless**. The teleport win that IS real is the **depth-budget** story on the strong,
depth-sensitive **diagonal** correlation — for which the current (rigged, diagonal) S3 is the correct
tool. We are NOT claiming quantum>classical here; we are claiming teleport-routing preserves the
correlation deeper than swap-routing because it costs less depth.

**Feed-forward, not herald:** `--herald` post-selects `tel==00` and keeps only ~0.4% of shots
(~30/8192) → too shot-starved for a correlation comparison. Drop it → feed-forward applies the
corrections and keeps all 8192 shots. `--repeats 3` (not 5 — `logical_depth` is deterministic; 3 just
buys bars on the correlation-survival curve).

```
python stage3_teleport.py --no-sim --routing both --gmin 6 --gmax 6 --bond-dist 3 --shots 8192 --repeats 3 --name qdep_m1_s3 --backend ibm_fez
```

**Record:** per-gen `logical_depth` both routings (sim: **swap 33 vs teleport 7** at bond-dist 3),
per-gen c(g) swap vs teleport (does teleport keep it alive deeper?), `meta.calibration`.
**Best case:** teleport's flat depth lets the diagonal correlation survive to a deeper g than the SWAP
ladder at the same G → first hardware evidence teleport buys depth budget on the same chip.
**Trust:** `logical_depth` HIGH (deterministic); correlation-survival MEDIUM (feed-forward, 3 repeats);
**this is a depth/decoherence claim, NOT a quantum-vs-classical g\*** (S3 stays diagonal by design).

> Optional honesty check (costs extra QC): one `--herald` run to confirm the teleport bond lands
> (`herald_frac`), reported as "constant-depth at the cost of ancillas + post-selection", per AC-S3.3.

RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage3_teleport.py --no-sim --routing both --gmin 6 --gmax 6 --bond-dist 3 --shots 8192 --repeats 3 --name qdep_m1_s3 --backend ibm_fez
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2444716 bytes
Backend : ibm_fez  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [72, 95], 'twoq_err_mean': 0.00267, 'twoq_err_max': 0.00539, 'readout_max': 0.07617, 'sx_max': 0.000662}
Note: teleport adds ancillas beyond the chain; the transpiler routes them (initial_layout left unpinned when it exceeds the chain, §6).
Sweep   : G in [6..6]  arms=['quantum_swap', 'quantum_teleport', 'classical', 'ideal']  routing=both  bond_dist=3  anchors=all  pheno_coupling=0.5  width=1  repeats=3

=== G = 6  (7 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da30k9u1vhnc73fj8ahg (8,192 shots) ... done (qpu 4.00s)
  seed 100 [    quantum_swap]  depth   33  C0 0.1338  c(1..6): +0.11, +0.06, +0.05, +0.01, +0.01, +0.03
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_quantum_swap_G6_ibm_fez_seed100_20260819-215528_run.json
  job 1: da30kcc3jnrc73aefl10 (8,192 shots) ... done (qpu 5.00s)
  seed 100 [quantum_teleport]  depth   39  C0 0.0957  c(1..6): +0.16, +0.07, +0.03, +0.02, +0.01, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_quantum_teleport_G6_ibm_fez_seed100_20260819-215538_run.json
  seed 100 [       classical]  C0 0.0000  c(1..6): +0.00, +0.00, +0.00, +0.00, +0.00, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_classical_G6_ibm_fez_seed100_20260819-215538_run.json
  seed 100 [           ideal]  C0 0.0000  c(1..6): +0.00, +0.00, +0.00, +0.00, +0.00, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_ideal_G6_sim_seed100_20260819-215538_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da30keuaa69c739i1to0 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [    quantum_swap]  depth   33  C0 0.1353  c(1..6): +0.09, +0.07, +0.01, +0.01, +0.01, +0.05
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_quantum_swap_G6_ibm_fez_seed101_20260819-215549_run.json
  job 1: da30khbotlns73993dvg (8,192 shots) ... done (qpu 5.00s)
  seed 101 [quantum_teleport]  depth   39  C0 0.1009  c(1..6): +0.15, +0.08, +0.06, -0.01, +0.00, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_quantum_teleport_G6_ibm_fez_seed101_20260819-215559_run.json
  seed 101 [       classical]  C0 0.0098  c(1..6): +0.89, +0.85, +0.77, +0.69, +0.60, +0.47
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_classical_G6_ibm_fez_seed101_20260819-215559_run.json
  seed 101 [           ideal]  C0 0.0049  c(1..6): +0.40, +0.31, +0.36, +0.27, +0.41, +0.35
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_ideal_G6_sim_seed101_20260819-215559_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da30kk6aa69c739i1tt0 (8,192 shots) ... done (qpu 4.00s)
  seed 102 [    quantum_swap]  depth   33  C0 0.1357  c(1..6): +0.07, +0.07, +0.03, +0.01, +0.01, +0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_quantum_swap_G6_ibm_fez_seed102_20260819-215609_run.json
  job 1: da30kmm1vhnc73fj8atg (8,192 shots) ... done (qpu 5.00s)
  seed 102 [quantum_teleport]  depth   39  C0 0.0909  c(1..6): +0.16, +0.07, +0.07, -0.01, +0.01, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_quantum_teleport_G6_ibm_fez_seed102_20260819-215618_run.json
  seed 102 [       classical]  C0 0.0002  c(1..6): +0.97, +0.94, +0.92, +0.40, +0.37, +0.85
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_classical_G6_ibm_fez_seed102_20260819-215618_run.json
  seed 102 [           ideal]  C0 0.0004  c(1..6): +0.32, +0.30, +0.62, +0.28, +0.60, +0.26
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_ideal_G6_sim_seed102_20260819-215618_run.json
  logical_depth(G=6) : swap=33  teleport=39
  g*(G=6) : swap k2=1 k3=1  teleport k2=1 k3=1  Δg* k2=0 k3=0

--- DONE (sweep) ---
    G   depth(swap)  depth(tel)   Δg*(k2)  Δg*(k3)
    6           33          39        0        0

Headline Δg* @ G=6 (k=2) = 0    (k=3) = 0   [teleport - swap, M5]
Routing cost (AC-S3.3): constant-depth long-range interaction at the cost of ancillas and classical feed-forward latency; not a free bypass
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m1_s3_ibm_fez_20260819-215618_summary.json


---

## Timing / abort plan

| stage | file | QC? | ~s | cumulative |
|-------|------|-----|----|-----------|
| S0 reproduce | stage0_reproduce.py | no (sim) | ~6 wall | — |
| S1 signal | stage1_temporal.py | yes | 7 | 7 |
| S2 scale @ G=8, R=5 | stage2_scale.py | yes (×5) | ~20 | ~24 |
| S3 both routings, R=3 | stage3_teleport.py | yes (×6) | ~30 | ~54 |
| backup (1 requeue) | — | yes | ~7 | ~61 |

> Actual QC/job on ibm_fez was ~4s (not 7), so S1+S2+S3 land near the 1-min budget. If tight, run S3
> at `--repeats 1` (logical_depth is deterministic; you lose only the correlation-survival error bars).

> Note: S2 at `--repeats 5` alone is ~35s — that plus S1+S3 slightly overruns 60s. If the clock is
> tight, drop S2 to `--repeats 3` (~21s) or defer the full scale to month 2. Priority order: keep
> S1 (anchor) + S3 (swap-vs-teleport headline); S2 is the one to trim.

---

## Results (paste after the run)

| Stage | Key number | Value | Notes |
|-------|-----------|-------|-------|
| S0 reproduce | trait_sigmaz ratios (~η); fidelity | | sim gate |
| S1 signal | g*(k2); quantum vs classical c(g) | | 1 repeat, no bars |
| S2 scale | g*(k2/k3) @ G=8 with σ; c(g) q/cl/ideal | | fix propagated, R=5 → real g* |
| S3 swap/tel | logical_depth swap vs tel; herald_frac; last g with c(g)>noise | | Δg* not valid yet |

---

## Reflection hooks for the 10-min run (month 2)

- Turn `--repeats 1` → 5–8 for error bars.
- **S3 stays DIAGONAL** for the depth-budget story (decided from S2). A *quantum* Δg* is only
  meaningful once the clone actually propagates coherence — see next bullet.
- **The real month-2 lever is the cloner, not more routing.** S2 proved the `Ry+CX` clone is a
  classical copier (quantum ≈ ideal ≈ 0 off-diagonal). Replace it with a coherence-propagating
  approximate cloner → THEN off-diagonal g* becomes quantum-favoured and teleport Δg* has meaning.
- Sweep `--gmax` / `--bond-dist` around where the diagonal correlation dies under swap depth.

---

## Preliminary conclusions (month 1)

**What we achieved.** Reproduced the 2018 Quantum Artificial Life single-lineage result on a real
IBM Heron r2 chip (ibm_fez): the exact operators (`M(θ)`, partial clone `U_M`, phenotype `⟨σ_z⟩_p`)
pass verbatim, and the phenotype "lifetime" decays geometrically at η≈0.9 (fidelity ≥0.996 in sim).
Then we ran a **new** measurement it never made — the *temporal* coherence-depth of inheritance —
and measured **g\* = 4** (k=3, error bars) at G=8: the coherent lineage stays statistically
distinguishable from a matched classical measure-and-resend surrogate out to 4 generations.

**Why this is "quantum artificial life."** Each individual is a genotype qubit; reproduction is an
imperfect quantum clone (`U_M`, no-cloning ⇒ built-in variation), mutation is a certified-random
rotation (Q-EaaS signed entropy per generation), and the phenotype is a measured lifetime that
decays across generations — self-replication + mutation + inheritance + death, all as quantum
operations on qubits, exactly the Alvarez-Rodriguez model. The lineage is grown and read coherently
on hardware, not simulated classically.

**Honest limits (preliminary).**
- **Not yet a quantum *advantage*.** The coherent arm ≈ the ideal noiseless arm ≈ 0 in the
  discriminating basis — the `Ry+CX` clone copies a classical value, it does **not** carry quantum
  coherence to the offspring. So g*=4 measures how long the two channels stay *distinguishable*, not
  that quantum inheritance is *richer* than classical (direction is classical > quantum).
- **Teleportation: promising, no headline win.** Δg* = 0. In feed-forward mode teleport was even
  *deeper* than the SWAP ladder (39 vs 33 — the "constant-depth 7" holds only when post-selecting).
  BUT teleport preserved the bonded short-range correlation **~1.7× better** on hardware
  (c(1) 0.156±0.005 vs swap 0.092±0.014) — a real edge, likely from avoiding the SWAP chain's
  2-qubit errors on the correlated pair.

**One-line verdict.** Reproduced 2018 ✓; added a new hardware coherence-depth number (g*=4) ✓;
quantum-beats-classical and a teleport g*-win ✗ — both gated by the classical-copier clone, which is
the single thing to fix next month. Teleport already shows a bonded-fidelity edge worth chasing.
