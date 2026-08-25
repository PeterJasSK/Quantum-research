# RUNLOG — Month 2 (QDEP / Quantum Artificial Life) — the 10-minute run

**Budget:** ~600s live QC. Stages **0-indexed to match the code** (S0…S3), one file per stage. Builds
on `RUNLOG_MONTH1.md` (reflect on month-1 first — where did the correlation start dying? that sets
`--gmax`/`--bond-dist`). Goal: study-grade preliminary with **error bars**, an **experimental
mid-circuit / multi-measure-per-shot** probe (inside S1), and a **clear teleport win** finale (S3).

**Reference:** Quantum Artificial Life (Alvarez-Rodriguez et al. 2018) → coherence ceiling →
teleport routing breaks the SWAP ladder.

```
cd artificial-life/code
```

---

## Prerequisites (DO BEFORE booking — not on the clock)

1. **Propagate the S1 setup-fix into S2/S3** (defer measurement + `--trait-basis` off-diagonal +
   normalized-c g*). Without it, S2/S3 `g*`/`Δg*` stay rig-limited. The finale depends on it.
   (See `qdep-setup-bug-fix` memory.)
2. **Add an experimental `--readout {deferred,midcircuit}` switch** to S1:
   - `deferred` = month-1 fixed path (all traits measured at circuit end, lineage stays coherent).
   - `midcircuit` = read T_g per generation mid-circuit (multiple measurements in one shot, one
     lineage per shot — the original CD-3 intent). This is the S1 experiment below.
3. Dry-run every command with `--sim` (free) once, so no flag typo burns the 10 min.
4. `QEAAS_API_KEY` set; backend pinned (`--backend ibm_<name>`) so all arms sit on ONE chip. The
   `/health` probe now prints up front — confirm `status ok / entropy healthy` before proceeding.

---

## Stage 0 — Reproduce gate  (`stage0_reproduce.py`, SIM, free)  ~10s wall

Re-confirm the 2018 lifetime + operators at higher shots. Free (no QC).

```
python stage0_reproduce.py --generations 8 --shots 8192 --seed 100 --name qdep_m2_s0
```

**Best case:** fidelity ≈0.99 to g=8, clean η-decay → gate passed, spend QC with confidence.


RUN : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage0_reproduce.py --generations 8 --shots 8192 --seed 100 --name qdep_m2_s0
=== S0 unit test: exact operators vs their defined forms ===
  worst L1(M_gate, paper matrix)     = 0.0000
  worst L1(U_M ancilla z, eta*parent) = 0.0000
  => M(theta) == paper matrix (equivalent)
  => U_M      == partial-clone (equivalent)

=== ideal lifetime: 8 gens, 8192 shots, eta=0.9 ===
  gen   trait_sigmaz   ideal     |diff|    3*stderr   fidelity
    0   +0.9998      +0.9996  0.0002   0.0010  0.9999 [ok]
    1   +0.9329      +0.9355  0.0026   0.0117  0.9987 [ok]
    2   +0.9036      +0.8989  0.0047   0.0145  0.9977 [ok]
    3   +0.8518      +0.8623  0.0105   0.0168  0.9948 [ok]
    4   +0.8213      +0.8313  0.0100   0.0184  0.9950 [ok]
    5   +0.7761      +0.7831  0.0070   0.0206  0.9965 [ok]
    6   +0.7637      +0.7653  0.0016   0.0213  0.9992 [ok]
    7   +0.7219      +0.7312  0.0093   0.0226  0.9954 [ok]
  successive <sigma_z>_p ratios (~eta): 0.933, 0.969, 0.943, 0.964, 0.945, 0.984, 0.945

wrote /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s0_sim_seed100_sim_run.json
(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ 


---

## Stage 1 — Signal with error bars + EXPERIMENTAL readout  (`stage1_temporal.py`, HW)  ~200s

### 1a — g* with error bars (~60s)
```
python stage1_temporal.py --no-sim --arm both --trait-basis 0.785 --generations 6 --shots 8192 --repeats 5 --name qdep_m2_s1_signal
```
**Best case:** quantum vs classical c(g) separated with **non-overlapping error bands** → a defended
small-G g* on hardware. Diagonal `trait_sigmaz` also gives the HW lifetime with σ.
RUN  : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage1_temporal.py --no-sim --arm both --trait-basis 0.785 --generations 6 --shots 8192 --repeats 5 --name qdep_m2_s1_signal
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2444076 bytes
Backend : ibm_fez  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [72], 'twoq_err_mean': 0.00271, 'twoq_err_max': 0.00392, 'readout_max': 0.02734, 'sx_max': 0.000442}

=== repeat 1/5  (seed 100) ===
  job 1: da60vcm1vhnc73fml7og (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1061  c(1..6): -0.07, -0.02, -0.02, -0.00, +0.01, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_quantum_ibm_fez_seed100_20260824-113244_run.json
  seed 100 [classical]  C0 0.0762  c(1..6): +0.55, +0.30, +0.14, +0.08, +0.04, +0.03
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_classical_ibm_fez_seed100_20260824-113244_run.json

=== repeat 2/5  (seed 101) ===
  job 1: da60vgk3jnrc73ahs0u0 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1186  c(1..6): -0.06, -0.02, -0.02, -0.03, -0.01, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_quantum_ibm_fez_seed101_20260824-113300_run.json
  seed 101 [classical]  C0 0.0904  c(1..6): +0.53, +0.27, +0.14, +0.06, +0.02, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_classical_ibm_fez_seed101_20260824-113301_run.json

=== repeat 3/5  (seed 102) ===
  job 1: da60vl3otlns739cg0a0 (8,192 shots) ... done (qpu 4.00s)
  seed 102 [  quantum]  C0 0.1178  c(1..6): -0.05, -0.02, -0.01, -0.01, -0.02, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_quantum_ibm_fez_seed102_20260824-113317_run.json
  seed 102 [classical]  C0 0.0971  c(1..6): +0.46, +0.24, +0.10, +0.05, +0.03, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_classical_ibm_fez_seed102_20260824-113318_run.json

=== repeat 4/5  (seed 103) ===
  job 1: da60vp61vhnc73fml8cg (8,192 shots) ... done (qpu 4.00s)
  seed 103 [  quantum]  C0 0.1147  c(1..6): -0.08, -0.00, -0.00, -0.04, -0.03, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_quantum_ibm_fez_seed103_20260824-113333_run.json
  seed 103 [classical]  C0 0.0931  c(1..6): +0.44, +0.24, +0.13, +0.06, +0.02, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_classical_ibm_fez_seed103_20260824-113333_run.json

=== repeat 5/5  (seed 104) ===
  job 1: da60vsrotlns739cg0m0 (8,192 shots) ... done (qpu 4.00s)
  seed 104 [  quantum]  C0 0.1123  c(1..6): -0.04, +0.01, -0.00, +0.01, +0.02, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_quantum_ibm_fez_seed104_20260824-113348_run.json
  seed 104 [classical]  C0 0.0791  c(1..6): +0.51, +0.24, +0.11, +0.05, +0.04, +0.03
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_classical_ibm_fez_seed104_20260824-113349_run.json

--- DONE ---
  g     C_quan   C_clas
    0   +1.0000   +1.0000
    1   -0.0587   +0.4991
    2   -0.0115   +0.2566
    3   -0.0119   +0.1219
    4   -0.0150   +0.0595
    5   -0.0065   +0.0301
    6   -0.0027   +0.0145

g* (k=2) = 4    g* (k=3) = 4
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_signal_ibm_fez_20260824-113349_summary.json
(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ 


### 1b — EXPERIMENTAL: mid-circuit / multiple measurements per shot (~140s)
The month-1 fix DEFERS readout. The original ambition (CD-3) reads every generation mid-circuit —
many measurements in one shot, one lineage per shot. Only worth it if Heron r2 mid-circuit
measurement is faithful enough not to destroy the signal. **Measure that, head-to-head, same chip.**
```
python stage1_temporal.py --no-sim --arm quantum --trait-basis 0.785 --readout deferred   --generations 8 --shots 8192 --repeats 2 --name qdep_m2_s1_deferred
python stage1_temporal.py --no-sim --arm quantum --trait-basis 0.785 --readout midcircuit --generations 8 --shots 8192 --repeats 2 --name qdep_m2_s1_midcirc
```
**Record:** c(g) deferred vs mid-circuit; measurements per shot; mid-circuit vs terminal readout error
(`meta.calibration`); QPU/wall time delta (feed-forward latency).
**Best case:** mid-circuit tracks deferred c(g) within σ → multi-measure-per-shot VIABLE → next study
can run true one-lineage-per-shot C(g). **Worst-but-useful:** mid-circuit visibly degrades → quantify
the collapse cost, stay deferred. Either is a real result — this is the experiment.


RUN  : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage1_temporal.py --no-sim --arm quantum --trait-basis 0.785 --readout deferred   --generations 8 --shots 8192 --repeats 2 --name qdep_m2_s1_deferred
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2444076 bytes
Backend : ibm_marrakesh  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [82, 94, 113, 130, 145], 'twoq_err_mean': 0.00326, 'twoq_err_max': 0.00472, 'readout_max': 0.03198, 'sx_max': 0.000804}

=== repeat 1/2  (seed 100) ===
  job 1: da615rk3jnrc73ahsa5g (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1181  c(1..8): -0.07, -0.00, -0.00, +0.02, +0.02, -0.00, -0.02, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_deferred_quantum_ibm_marrakesh_seed100_20260824-114630_run.json

=== repeat 2/2  (seed 101) ===
  job 1: da6160u1vhnc73fmlhfg (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1178  c(1..8): -0.07, +0.00, +0.02, -0.02, -0.02, -0.03, -0.02, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_deferred_quantum_ibm_marrakesh_seed101_20260824-114652_run.json

--- DONE ---
  g     C_quan
    0   +1.0000
    1   -0.0695
    2   +0.0012
    3   +0.0084
    4   -0.0005
    5   +0.0003
    6   -0.0139
    7   -0.0236
    8   -0.0181

g*: needs both quantum and classical arms (--arm both).
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_deferred_ibm_marrakesh_20260824-114652_summary.json
(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage1_temporal.py --no-sim --arm quantum --trait-basis 0.785 --readout midcircuit --generations 8 --shots 8192 --repeats 2 --name qdep_m2_s1_midcirc
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2444044 bytes
Backend : ibm_kingston  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00695, 'twoq_err_max': 0.03453, 'readout_max': 0.01392, 'sx_max': 0.000509}

=== repeat 1/2  (seed 100) ===
  job 1: da6169u1vhnc73fmlhug (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1411  c(1..8): -0.03, -0.00, +0.00, -0.01, -0.00, -0.01, -0.00, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_midcirc_quantum_ibm_kingston_seed100_20260824-114727_run.json

=== repeat 2/2  (seed 101) ===
  job 1: da616ee1vhnc73fmli70 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1279  c(1..8): -0.01, +0.00, -0.03, -0.02, -0.01, -0.01, -0.01, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_midcirc_quantum_ibm_kingston_seed101_20260824-114744_run.json

--- DONE ---
  g     C_quan
    0   +1.0000
    1   -0.0218
    2   -0.0002
    3   -0.0131
    4   -0.0118
    5   -0.0082
    6   -0.0110
    7   -0.0067
    8   -0.0003

g*: needs both quantum and classical arms (--arm both).
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s1_midcirc_ibm_kingston_20260824-114744_summary.json
(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ 

---

## Stage 2 — Locate the coherence / SWAP ceiling  (`stage2_scale.py`, HW)  ~120s

Sweep G to find where the quantum-vs-surrogate gap dies (the ceiling S3 must lift).

```
python stage2_scale.py --no-sim --arm both --gmin 4 --gmax 10 --trait-basis 0.785 --shots 8192 --repeats 3 --name qdep_m2_s2_sweep
```

**Record:** per-G `gstar`, c(g) bands, ideal-clone confound curve.
**Best case:** a clear ceiling G where the gap collapses → sizes `--gmax`/`--bond-dist` for the finale.

(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage2_scale.py --no-sim --arm both --gmin 4 --gmax 10 --trait-basis 0.785 --shots 8192 --repeats 3 --name qdep_m2_s2_sweep
Q-EaaS  : https://api.qeaas.eu/  (fail-closed, no PRNG fallback)
          health: ok / entropy healthy / pool 2444076 bytes
Backend : ibm_kingston  (156 qubits)
WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00587, 'twoq_err_max': 0.03453, 'readout_max': 0.01978, 'sx_max': 0.000509}
Sweep   : G in [4..10]  arms=['quantum', 'classical', 'ideal']  pheno_coupling=0.5  width=1  repeats=3

=== G = 4  (5 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da6115k3jnrc73ahs3l0 (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1245  c(1..4): -0.02, +0.00, +0.00, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G4_ibm_kingston_seed100_20260824-113630_run.json
  seed 100 [classical]  C0 0.1122  c(1..4): +0.50, +0.22, +0.12, +0.06
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G4_ibm_kingston_seed100_20260824-113630_run.json
  seed 100 [    ideal]  C0 0.1207  c(1..4): -0.05, -0.03, -0.03, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G4_sim_seed100_20260824-113631_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da61186aa69c739le7qg (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1180  c(1..4): +0.01, +0.02, +0.01, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G4_ibm_kingston_seed101_20260824-113640_run.json
  seed 101 [classical]  C0 0.1217  c(1..4): +0.48, +0.25, +0.14, +0.09
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G4_ibm_kingston_seed101_20260824-113640_run.json
  seed 101 [    ideal]  C0 0.1212  c(1..4): -0.00, +0.00, -0.01, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G4_sim_seed101_20260824-113640_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da611am1vhnc73fmlaq0 (8,192 shots) ... done (qpu 4.00s)
  seed 102 [  quantum]  C0 0.1202  c(1..4): -0.06, -0.01, +0.00, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G4_ibm_kingston_seed102_20260824-113649_run.json
  seed 102 [classical]  C0 0.0960  c(1..4): +0.49, +0.23, +0.14, +0.05
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G4_ibm_kingston_seed102_20260824-113650_run.json
  seed 102 [    ideal]  C0 0.1125  c(1..4): -0.10, -0.04, -0.04, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G4_sim_seed102_20260824-113650_run.json
  g*(G=4) : k2=4  k3=4

=== G = 5  (6 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da611crotlns739cg300 (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1174  c(1..5): -0.03, -0.00, -0.03, -0.01, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G5_ibm_kingston_seed100_20260824-113659_run.json
  seed 100 [classical]  C0 0.1107  c(1..5): +0.51, +0.22, +0.10, +0.04, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G5_ibm_kingston_seed100_20260824-113659_run.json
  seed 100 [    ideal]  C0 0.1130  c(1..5): -0.04, -0.02, -0.02, -0.02, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G5_sim_seed100_20260824-113659_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da611f61vhnc73fmlav0 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1246  c(1..5): -0.04, +0.00, +0.02, +0.01, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G5_ibm_kingston_seed101_20260824-113708_run.json
  seed 101 [classical]  C0 0.1240  c(1..5): +0.45, +0.26, +0.14, +0.07, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G5_ibm_kingston_seed101_20260824-113709_run.json
  seed 101 [    ideal]  C0 0.1239  c(1..5): -0.01, -0.01, -0.02, -0.02, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G5_sim_seed101_20260824-113709_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da611hmaa69c739le850 (8,192 shots) ... done (qpu 4.00s)
  seed 102 [  quantum]  C0 0.1169  c(1..5): -0.05, -0.00, +0.00, -0.01, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G5_ibm_kingston_seed102_20260824-113720_run.json
  seed 102 [classical]  C0 0.0974  c(1..5): +0.48, +0.22, +0.12, +0.05, +0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G5_ibm_kingston_seed102_20260824-113720_run.json
  seed 102 [    ideal]  C0 0.1121  c(1..5): -0.07, -0.04, -0.03, -0.02, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G5_sim_seed102_20260824-113720_run.json
  g*(G=5) : k2=5  k3=4

=== G = 6  (7 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da611ks3jnrc73ahs46g (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1209  c(1..6): -0.01, -0.01, -0.03, -0.03, -0.01, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G6_ibm_kingston_seed100_20260824-113731_run.json
  seed 100 [classical]  C0 0.1078  c(1..6): +0.49, +0.23, +0.11, +0.04, +0.03, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G6_ibm_kingston_seed100_20260824-113731_run.json
  seed 100 [    ideal]  C0 0.1182  c(1..6): -0.02, -0.01, -0.02, +0.01, +0.00, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G6_sim_seed100_20260824-113731_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da611n3otlns739cg3bg (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1267  c(1..6): +0.02, +0.03, +0.03, +0.01, -0.00, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G6_ibm_kingston_seed101_20260824-113740_run.json
  seed 101 [classical]  C0 0.1167  c(1..6): +0.45, +0.24, +0.14, +0.08, +0.04, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G6_ibm_kingston_seed101_20260824-113741_run.json
  seed 101 [    ideal]  C0 0.1262  c(1..6): -0.02, -0.01, -0.01, +0.02, -0.00, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G6_sim_seed101_20260824-113741_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da611pm1vhnc73fmlba0 (8,192 shots) ... done (qpu 4.00s)
  seed 102 [  quantum]  C0 0.1133  c(1..6): -0.05, -0.00, -0.03, +0.00, +0.00, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G6_ibm_kingston_seed102_20260824-113750_run.json
  seed 102 [classical]  C0 0.0997  c(1..6): +0.46, +0.19, +0.08, +0.04, +0.03, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G6_ibm_kingston_seed102_20260824-113750_run.json
  seed 102 [    ideal]  C0 0.1175  c(1..6): -0.09, -0.05, -0.02, -0.03, -0.03, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G6_sim_seed102_20260824-113750_run.json
  g*(G=6) : k2=5  k3=5

=== G = 7  (8 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da611rs3jnrc73ahs4dg (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1261  c(1..7): -0.03, +0.00, -0.00, -0.01, -0.00, -0.02, -0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G7_ibm_kingston_seed100_20260824-113759_run.json
  seed 100 [classical]  C0 0.1101  c(1..7): +0.52, +0.24, +0.12, +0.07, +0.04, +0.02, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G7_ibm_kingston_seed100_20260824-113759_run.json
  seed 100 [    ideal]  C0 0.1170  c(1..7): -0.04, -0.01, +0.00, +0.01, +0.00, -0.03, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G7_sim_seed100_20260824-113759_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da611u43jnrc73ahs4h0 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1289  c(1..7): -0.03, -0.00, -0.01, +0.00, -0.01, -0.01, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G7_ibm_kingston_seed101_20260824-113807_run.json
  seed 101 [classical]  C0 0.1187  c(1..7): +0.44, +0.22, +0.13, +0.08, +0.04, +0.01, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G7_ibm_kingston_seed101_20260824-113808_run.json
  seed 101 [    ideal]  C0 0.1264  c(1..7): -0.02, +0.01, +0.00, -0.00, +0.00, -0.00, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G7_sim_seed101_20260824-113808_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da6120eaa69c739le8mg (8,192 shots) ... done (qpu 4.00s)
  seed 102 [  quantum]  C0 0.1193  c(1..7): -0.08, -0.02, +0.00, +0.01, -0.01, -0.02, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G7_ibm_kingston_seed102_20260824-113816_run.json
  seed 102 [classical]  C0 0.0900  c(1..7): +0.49, +0.25, +0.14, +0.05, +0.03, +0.00, +0.03
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G7_ibm_kingston_seed102_20260824-113816_run.json
  seed 102 [    ideal]  C0 0.1116  c(1..7): -0.04, -0.03, -0.05, -0.03, -0.03, -0.01, -0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G7_sim_seed102_20260824-113817_run.json
  g*(G=7) : k2=7  k3=5

=== G = 8  (9 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da6122e1vhnc73fmlbqg (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1176  c(1..8): -0.03, +0.00, -0.01, -0.01, -0.01, -0.00, +0.01, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G8_ibm_kingston_seed100_20260824-113825_run.json
  seed 100 [classical]  C0 0.1088  c(1..8): +0.50, +0.25, +0.13, +0.05, +0.01, +0.01, +0.00, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G8_ibm_kingston_seed100_20260824-113826_run.json
  seed 100 [    ideal]  C0 0.1178  c(1..8): -0.05, -0.02, -0.01, -0.04, -0.02, -0.03, -0.02, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G8_sim_seed100_20260824-113826_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da6124uaa69c739le8u0 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1223  c(1..8): -0.02, +0.01, -0.00, +0.00, -0.03, -0.04, -0.02, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G8_ibm_kingston_seed101_20260824-113834_run.json
  seed 101 [classical]  C0 0.1164  c(1..8): +0.46, +0.24, +0.12, +0.06, +0.02, -0.01, -0.02, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G8_ibm_kingston_seed101_20260824-113835_run.json
  seed 101 [    ideal]  C0 0.1209  c(1..8): -0.01, -0.01, -0.01, -0.02, +0.01, -0.00, -0.01, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G8_sim_seed101_20260824-113835_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da61273otlns739cg42g (8,192 shots) ... done (qpu 4.00s)
  seed 102 [  quantum]  C0 0.1144  c(1..8): -0.08, -0.03, -0.04, -0.01, -0.01, -0.00, +0.00, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G8_ibm_kingston_seed102_20260824-113844_run.json
  seed 102 [classical]  C0 0.0933  c(1..8): +0.49, +0.22, +0.14, +0.07, +0.02, -0.02, -0.00, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G8_ibm_kingston_seed102_20260824-113844_run.json
  seed 102 [    ideal]  C0 0.1139  c(1..8): -0.07, -0.03, -0.02, +0.00, -0.03, -0.03, -0.03, -0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G8_sim_seed102_20260824-113844_run.json
  g*(G=8) : k2=5  k3=4

=== G = 9  (10 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da6129m1vhnc73fmlc6g (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1191  c(1..9): -0.02, -0.02, +0.01, +0.01, +0.02, +0.01, +0.01, +0.00, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G9_ibm_kingston_seed100_20260824-113854_run.json
  seed 100 [classical]  C0 0.1075  c(1..9): +0.48, +0.20, +0.10, +0.04, -0.00, -0.01, -0.03, -0.01, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G9_ibm_kingston_seed100_20260824-113855_run.json
  seed 100 [    ideal]  C0 0.1203  c(1..9): -0.02, -0.01, -0.02, -0.02, -0.04, -0.01, +0.01, +0.01, +0.03
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G9_sim_seed100_20260824-113855_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da612c3otlns739cg480 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1225  c(1..9): -0.00, +0.00, +0.00, +0.01, +0.01, -0.01, +0.00, +0.01, -0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G9_ibm_kingston_seed101_20260824-113904_run.json
  seed 101 [classical]  C0 0.1195  c(1..9): +0.46, +0.23, +0.10, +0.07, +0.03, +0.02, +0.01, +0.01, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G9_ibm_kingston_seed101_20260824-113905_run.json
  seed 101 [    ideal]  C0 0.1222  c(1..9): -0.06, -0.04, +0.02, -0.01, +0.01, +0.02, +0.02, +0.04, +0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G9_sim_seed101_20260824-113905_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da612em1vhnc73fmlccg (8,192 shots) ... done (qpu 4.00s)
  seed 102 [  quantum]  C0 0.1143  c(1..9): -0.04, -0.01, +0.00, -0.00, -0.00, -0.02, -0.00, +0.00, -0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G9_ibm_kingston_seed102_20260824-113915_run.json
  seed 102 [classical]  C0 0.0906  c(1..9): +0.48, +0.21, +0.10, +0.03, +0.01, +0.01, -0.01, -0.02, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G9_ibm_kingston_seed102_20260824-113916_run.json
  seed 102 [    ideal]  C0 0.1144  c(1..9): -0.07, -0.04, -0.03, -0.00, -0.02, -0.00, -0.02, +0.01, +0.00
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G9_sim_seed102_20260824-113916_run.json
  g*(G=9) : k2=4  k3=3

=== G = 10  (11 generation slots) ===
  -- repeat 1/3  (seed 100) --
  job 1: da612hm1vhnc73fmlch0 (8,192 shots) ... done (qpu 4.00s)
  seed 100 [  quantum]  C0 0.1208  c(1..10): -0.04, -0.02, -0.02, -0.02, -0.01, -0.03, +0.00, +0.00, -0.01, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G10_ibm_kingston_seed100_20260824-113929_run.json
  seed 100 [classical]  C0 0.1073  c(1..10): +0.50, +0.23, +0.09, +0.05, +0.01, +0.01, +0.00, +0.00, +0.02, +0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G10_ibm_kingston_seed100_20260824-113930_run.json
  seed 100 [    ideal]  C0 0.1217  c(1..10): -0.02, -0.01, +0.01, +0.03, -0.00, +0.00, -0.01, -0.01, +0.00, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G10_sim_seed100_20260824-113930_run.json
  -- repeat 2/3  (seed 101) --
  job 1: da612ks3jnrc73ahs5k0 (8,192 shots) ... done (qpu 4.00s)
  seed 101 [  quantum]  C0 0.1294  c(1..10): +0.01, +0.02, +0.01, +0.04, +0.03, -0.00, +0.01, -0.00, +0.03, +0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G10_ibm_kingston_seed101_20260824-113955_run.json
  seed 101 [classical]  C0 0.1162  c(1..10): +0.46, +0.21, +0.11, +0.05, +0.02, +0.01, -0.01, -0.03, -0.01, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G10_ibm_kingston_seed101_20260824-113957_run.json
  seed 101 [    ideal]  C0 0.1219  c(1..10): -0.01, -0.00, -0.01, -0.03, -0.00, -0.01, -0.01, -0.01, -0.01, -0.02
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G10_sim_seed101_20260824-113957_run.json
  -- repeat 3/3  (seed 102) --
  job 1: da612rmaa69c739le9pg (8,192 shots) ... done (qpu 4.00s)
  seed 102 [  quantum]  C0 0.1252  c(1..10): -0.06, -0.01, -0.03, -0.04, -0.01, -0.02, -0.03, -0.02, -0.01, -0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_quantum_G10_ibm_kingston_seed102_20260824-114029_run.json
  seed 102 [classical]  C0 0.0917  c(1..10): +0.49, +0.25, +0.13, +0.07, +0.04, +0.03, +0.03, +0.02, +0.02, +0.01
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_classical_G10_ibm_kingston_seed102_20260824-114031_run.json
  seed 102 [    ideal]  C0 0.1085  c(1..10): -0.09, -0.04, -0.03, -0.00, -0.01, -0.02, -0.02, -0.02, -0.03, -0.04
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ideal_G10_sim_seed102_20260824-114031_run.json
  g*(G=10) : k2=6  k3=3

--- DONE (sweep) ---
    G   g*(k2)  g*(k3)
    4       4       4
    5       5       4
    6       5       5
    7       7       5
    8       5       4
    9       4       3
   10       6       3

Headline g* @ G=10 (k=2) = 6    (k=3) = 3
Summary file : /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qdep_m2_s2_sweep_ibm_kingston_20260824-114031_summary.json
(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ 


---

## Stage 3 — FINALE: teleport clear-win vs SWAP  (`stage3_teleport.py`, HW)  ~140s + backup

The whole point. At the bond-dist that gave the biggest depth gap (start `--bond-dist 5` for a larger
SWAP penalty), run BOTH routings head-to-head with the fixed metric and the most repeats the clock
allows. Run LAST so it eats leftover budget; if short, drop `--bond-dist 5` → `3`.

```
python stage3_teleport.py --no-sim --routing both --herald --gmin 6 --gmax 8 --bond-dist 5 --shots 8192 --repeats 5 --name qdep_m2_s3_FINALE
```

**Record:** `delta_gstar` (k2/k3) with σ, per-gen `logical_depth` both routings, `herald_frac`, c(g)
swap vs teleport vs classical.
**CLEAR WIN (success criterion):**
- `Δg* > 0` with **non-overlapping error bars** (teleport sustains coherent inheritance more
  generations than SWAP on the same chip), AND
- `logical_depth`: teleport flat (~7) while SWAP grows (~33 at bond-dist 3, more at 5), AND
- `herald_frac` healthy (the teleported bond actually lands).
- Honesty line (AC-S3.3): *constant-depth long-range interaction at the cost of ancillas + classical
  latency*, not a free bypass.

---

## Time budget (~600s, ~90s backup)

| stage | file | ~s | cumulative |
|-------|------|----|-----------|
| S0 gate (sim) | stage0_reproduce.py | free | — |
| S1a signal (R=5) | stage1_temporal.py | 60 | 60 |
| S1b experimental mid-circuit | stage1_temporal.py | 140 | 200 |
| S2 ceiling sweep | stage2_scale.py | 120 | 320 |
| S3 FINALE both routings | stage3_teleport.py | 140 | 460 |
| backup / requeue | — | ~90 | 550 |

**Abort priority if the clock slips:** protect S3 (finale) and S1a (anchor). Trim S2's sweep range
first, then S1b's repeats. Never skip S3 — it is the deliverable.

---










--------------------------------------------------------------------------------------------------------------------------------------------------------------------
## Results (2026-08-24 — run ABORTED early, see below)

| Stage | Key number | Value | σ / notes |
|-------|-----------|-------|-----------|
| S0 | η ratios; fidelity | η≈0.932–0.974; fidelity ≥0.9967 to g=8 | sim gate **PASS** |
| S1a | g*(k2) | **not run** | aborted before S1a |
| S1b | c(g) deferred vs midcircuit | **not run** | `--readout` switch never built |
| S2 | ceiling G; g* per G | **not run** | aborted before S2 |
| S3 | **Δg* (k2/k3)**; depth flat vs grow; herald_frac | **Δg*=0 / 0** @ bd9; depth swap **74** / tel **39**; herald **not run** | **NULL — no win** |

---

## ACTUAL RUN — 2026-08-24 (aborted by user: NO MORE LIVE HARDWARE)

**What we tried.** The "clear teleport win" recipe: keep teleport depth flat (constant in routed
distance) and blow up the SWAP ladder by pushing `--bond-dist` big, so the SWAP arm's extra 2-qubit
error would kill the diagonal correlation while teleport preserved it → Δg* > 0 growing with distance.
Win-first order: bond-dist 9 → 7 → 5 → 3, G=6, both routings, R=8, feed-forward, `ibm_fez`.

**What actually ran on the chip (~24 HW jobs, ~110s QPU) before the abort:**

| item | status | on disk |
|------|--------|---------|
| S0 gate (sim, free) | ✅ complete, PASS | `qdep_m2_s0_*_run.json` |
| S3 bond-dist **9** (R=8, both routings) | ✅ complete + summary | 32 run.json + summary |
| S3 bond-dist **7** (both routings) | ⚠️ partial (~4 repeats), no summary | 16 run.json |
| S3 bond-dist 5, 3 | ❌ not run | — |
| S1a anchor, S1b midcircuit, herald | ❌ not run | — |

**Depth mechanism — CONFIRMED (M6).** Deterministic and exactly as predicted in free sim:
`logical_depth(bd9) = swap 74, teleport 39`; `logical_depth(bd7) = swap 60, teleport 39`. SWAP grows
O(distance) (33 @ bd3 month1 → 60 @ bd7 → 74 @ bd9); teleport is flat at 39 regardless of distance.
The constant-depth claim holds on the real routed circuits.

**The win — DID NOT HAPPEN. Δg* = 0.** Aggregated connected `C(g)` at bd9 (R=8, the authoritative
number; the per-seed normalized `c(g)` printed in stdout is `C(g)/C0` with `C0≈0.003` for the
surrogate → pure ratio noise, ignore it):

| gen | swap C(g) | teleport C(g) | classical C(g) | ideal C(g) |
|----:|----------:|--------------:|---------------:|-----------:|
| 0 | +0.2496 | +0.2470 | +0.0027 | +0.0015 |
| 1 | −0.0015 | +0.0000 | +0.0024 | +0.0006 |
| 2 | −0.0006 | +0.0004 | +0.0022 | +0.0005 |
| 3 | +0.0007 | −0.0024 | +0.0020 | +0.0004 |
| 4 | +0.0004 | −0.0010 | +0.0017 | +0.0005 |

`g*(swap)=1`, `g*(teleport)=1` → **Δg* = 0 (k2 and k3).**

**Why no win (honest read).** The temporal correlation is **≈0 for g≥1 on every arm, including both
quantum routings.** The lineage carries a self-term at g=0 (C0≈0.25 for the quantum arms) and then
**nothing** propagates down the generations. There was no live diagonal signal for teleport's shallower
depth to preserve — you cannot buy Δg* by making SWAP deeper if the correlation is already dead on
*both* routings. Bigger circuit confirmed the depth scaling; it did **not** manufacture a signal.

This is the **same verdict Month 1 reached, now nailed down at scale:** the `Ry+CX` clone is a classical
copier and the diagonal `C(g)` it produces does not survive Heron-r2 depth at G=6. Month 1's "teleport
preserved the short-range bonded correlation ~1.7× better" was a bond-fidelity edge at bd3 (depth 33 vs
39) — it did **not** translate into g*, and it does not survive at bd9. **More routing / more distance
is not the lever. The cloner is.** (Month-1 reflection bullet was right.)

**Chain-quality caveat.** The bd9/bd7 auto-chains reported `twoq_err_max = 1.0` and
`readout_max ≈ 0.155` (a dead/maxed edge in the long strided chain) vs Month-1's clean
`twoq_err_max ≈ 0.005`. A 62-qubit (bd9) strided spine on a 156-qubit chip drags in bad edges — so
even if a signal existed, this chain is far noisier than Month 1's. Bigger SWAP circuit = worse chain,
compounding the null.

---

## Conclusion hooks (write-up after) — updated 2026-08-24

- **Reproduction:** 2018 lifetime holds in sim gate to g=8 (fidelity ≥0.9967, η≈0.9). ✅
- **Ceiling:** not swept (S2 not run). But bd9/G6 shows connected `C(g≥1) ≈ 0` on both quantum arms →
  the diagonal lineage correlation is already dead by G=6 on Heron-r2 with the current clone.
- **Teleport:** **Δg* = 0. No win.** Depth mechanism confirmed (swap 74 O(d) vs teleport 39 flat) but
  no live signal to preserve → deeper SWAP bought nothing. Pushing `--bond-dist` bigger did not create
  the win; it confirmed Month-1's verdict and added a noisier chain (`twoq_err_max=1.0`).
- **Experimental verdict (S1b):** `--readout {deferred,midcircuit}` switch now **built + verified in
  sim** (`stage1_temporal.py`: `build_lineage_quantum_midcircuit`; deferred≡midcircuit under `--sim`,
  max Δc(g)=0.007 shot-noise; midcircuit genuinely interleaves measures before later entangling gates).
  Records `readout`, `num_measurements_per_shot`, `mid_circuit_measurements`, `qpu_seconds` in run
  meta. **Ready to run on hardware (by user — not in this session).** S1b still not executed.
- **The real lever (confirmed twice now):** the `Ry+CX` clone is a classical copier; it propagates no
  coherence, so `C(g≥1)≈0` and both routings tie. **Month-3 must replace the cloner with a
  coherence-propagating approximate cloner** — that, not more routing/distance, is the only path to a
  quantum-favoured deep g* and a meaningful teleport Δg*. Do this in **simulation** (noiseless +
  `--noise-model` FakeFez) first; no live hardware.

## Directive (2026-08-24)

**NO MORE LIVE HARDWARE runs** until further notice. All future S1–S3 work stays in `--sim` /
`--noise-model`. The depth claim (M6) and the cloner redesign are both fully testable off-chip.
