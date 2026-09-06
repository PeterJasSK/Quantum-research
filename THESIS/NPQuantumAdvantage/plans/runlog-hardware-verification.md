# RUN LOG — real-QC hardware verification, all algorithms, all problems

**One log to evaluate everything.** Runs every arm of every problem, submits the
runnable quantum circuits to a **real IBM backend**, and lays out a single comparison
matrix so you can judge each algorithm side by side. Run from the project root
`THESIS/NPQuantumAdvantage/`.

> **READ THIS FIRST — claim discipline (epic §3), non-negotiable.**
> A real-device run here is **FEASIBILITY only**, never a wall-clock advantage. On NISQ
> hardware the quantum arm **loses** in seconds — noise degrades amplitude
> amplification and the oracle depth is significant. The *advantage* claim lives in the
> **oracle-call count** (exact, device-independent), not on the device. The four
> qualifiers attach to every quantum line: **query model · over brute force · quadratic ·
> NOT wall-clock.** The hardware run only shows the marked state is amplified above the
> `1/|S|` floor on real silicon.

---

## 0. What actually runs on hardware (honest scope)

| Problem | search space | classical brute | best-classical hunt | Grover query-count | Grover **real HW** | QAOA appendix HW |
|---------|--------------|-----------------|---------------------|--------------------|--------------------|------------------|
| 3-SAT (reference) | 2^n | ✅ | (SETH, no code) | ✅ | ✅ `proof_of_concept/` | — |
| P1 Betweenness | n! | ✅ | ✅ DP | ✅ | ❌ **N/A** (no permutation-Grover oracle, OQ-5) | — |
| P2 Numerical Matching | n! | ✅ | ✅ DP | ✅ | ❌ **N/A** (same) | — |
| P3 Quadratic Congruences | 2^n | ✅ | ✅ sympy | ✅ | ✅ `--statevector --backend` | — |
| P4 Kernel of a Digraph | 2^n | ✅ | ✅ brancher | ✅ | ✅ `--statevector --backend` | ✅ (deferred by default) |
| P5 MinLA | n! | ✅ | ✅ DP | ✅ | ❌ **N/A** (same) | — |

**Why ordering problems have no HW Grover:** their certificate is a permutation, so a
Grover oracle would need a `n!`-index encoding + permutation-validity circuit — out of
scope (OQ-5). Their quantum claim is carried entirely by the **query-count theorem**
(exact, runs anywhere). Only the three **subset** problems (3-SAT, P3, P4) have a phase
oracle that marks the feasible bitstring, so only they submit a real Grover circuit.

**Net:** on real hardware you can directly compare **3-SAT vs P3 vs P4** (all subset,
all Grover-amplifiable). P1/P2/P5 are compared on the classical + query-count axes only,
which is exactly where their verdict is decided (structural collapse).

---

## 1. Preflight (once)

```bash
# deps
python -c "import qiskit, qiskit_aer, qiskit_ibm_runtime, sympy, numpy; print('deps ok')"

# save IBM Quantum account once (interactive — run in a ! shell, not headless)
python - <<'PY'
from qiskit_ibm_runtime import QiskitRuntimeService
QiskitRuntimeService.save_account(channel="ibm_quantum", token="PASTE_YOUR_TOKEN", overwrite=True)
print("account saved")
PY

# pick the least-busy real device and record its calibration NOW (drifts hourly)
python - <<'PY'
from qiskit_ibm_runtime import QiskitRuntimeService
svc = QiskitRuntimeService()
b = svc.least_busy(operational=True, simulator=False, min_num_qubits=8)
props = b.properties()
ro = sum(props.readout_error(q) for q in range(b.num_qubits)) / b.num_qubits
cx = [g.parameters[0].value for g in props.gates if g.gate in ("cx","ecr","cz") and g.parameters]
print("BACKEND      :", b.name, b.num_qubits, "qubits")
print("median readout err:", round(ro, 4))
print("median 2q err     :", round(sorted(cx)[len(cx)//2], 4) if cx else "n/a")
PY
```
Write the printed `BACKEND`, `readout err`, `2q err`, and UTC timestamp into the results
table (§5). Set it once for the session:
```bash
export QC=ibm_torino     # <- the name printed above; 'auto' = least-busy at submit time
export SEED=7
```

---

## 2. The classical + theorem sweep (all five, runs anywhere, no QC)

This is the headline evidence — deterministic, device-independent. Run it first so the
hardware runs have a baseline to sit against.

```bash
for p in p1_betweenness p2_numerical_matching p3_quadratic_congruences p4_kernel_digraph p5_minla; do
  echo "==================== $p ===================="
  # pick n: ordering brute is n!, keep small; subset can go bigger
  case $p in p3_*|p4_*) N=10 ;; *) N=7 ;; esac
  echo "--- classical brute force (query cost == |S|) ---"
  python -m problems.$p.classical_bruteforce --n $N --seed $SEED
  echo "--- Grover / Dürr–Høyer query count (the theorem) ---"
  python -m problems.$p.quantum_grover        --n $N --seed $SEED
  echo "--- best-known classical hunt → fitted c → √2 verdict ---"
  python -m problems.$p.best_classical         --seed $SEED --no-emit
done
```
**Record per problem:** classical slope (expect `1.000`), quantum slope (expect `0.500`),
`best-classical c`, and `VERDICT`. This reproduces the map:
3-SAT survivor · P4 borderline · P1/P2/P3/P5 collapse.

---

## 3. Real-hardware Grover — subset problems (3-SAT, P3, P4)

Each command submits an actual Grover circuit and reports the **marked-state probability
on the device** vs the **uniform `1/2^n` floor**. Keep `n` small (≤ 8–9) so the circuit
survives NISQ depth. Feasibility only.

### 3-SAT reference survivor
```bash
python proof_of_concept/quantum_grover.py --backend $QC --shots 4096
```
Expect on device: satisfying bitstring(s) above the `1/2^4` floor (POC hit 51.9% vs 6.2%
on `ibm_kingston`). This is the clean survivor and the sanity anchor.

### P3 Quadratic Congruences (subset, algebraic-collapse)
```bash
# ideal Aer first (baseline), then real device
python -m problems.p3_quadratic_congruences.quantum_grover --n 8 --seed $SEED --statevector
python -m problems.p3_quadratic_congruences.quantum_grover --n 8 --seed $SEED --statevector --backend $QC --shots 4096
```
Grover *works* here (solution amplified) — but recall P3's best classical is
sub-exponential (`c ≈ 0.075`): the honest quantum win is **Shor, not Grover**. The HW run
shows amplification; it does **not** beat the classical number-theory solver.

### P4 Kernel of a Digraph (subset, the star)
```bash
python -m problems.p4_kernel_digraph.quantum_grover --n 8 --seed $SEED --statevector
python -m problems.p4_kernel_digraph.quantum_grover --n 8 --seed $SEED --statevector --backend $QC --shots 4096
```
Amplifies the kernel state. Its best-classical exponent sits *on* the √2 line
(c ≈ 0.44–0.56 across seeds — see `problems/p4_kernel_digraph/RUNLOG.md` §4), so this is
the one problem where the query-model advantage is genuinely borderline.

> **Ordering problems (P1/P2/P5):** no HW Grover command exists — see §0. Running
> `... .quantum_grover --n 6 --statevector` prints the out-of-scope note; that is
> expected, not a failure.

**For each device run, record:** backend, shots, `Grover iterations`, marked-state
probability on device, `1/|S|` floor, and the ideal-Aer probability for the same `n` — so
the noise penalty (Aer prob − device prob) is explicit.

---

## 4. The NISQ-heuristic datapoint — P4 QAOA appendix on hardware (optional, obstruction)

The QAOA appendix is **deferred by design** (AC-T1.10 / QDEP obstruction): `--backend`
prints a deferral notice and does **not** submit. Two ways to use it:

```bash
# (a) the intended feasibility run — noiseless Aer, sign/correctness gate only
python -m problems._hardware.qaoa_appendix --n 8 --seed $SEED

# (b) confirm the deferral guard (prints the QDEP obstruction notice, no submission)
python -m problems._hardware.qaoa_appendix --n 8 --seed $SEED --backend $QC
```
If you *choose* to force a real Heron run for the thesis's obstruction datapoint, do it
manually (edit the appendix to route `--backend` through a `SamplerV2`, mirroring
`quantum_grover.py:_counts_hw`) and record calibration + wall-clock — it is **expected to
lose** (readout error ≫ 2q error on modern hardware; Farhi–Gamarnik–Gutmann 2020 locality
obstruction). Report it as obstruction, never advantage.

---

## 5. Results table — fill this in

Backend: `__________`  ·  readout err: `______`  ·  2q err: `______`  ·  UTC: `__________`

### Query-model / theorem axis (device-independent — from §2)
| problem | space | classical slope | quantum slope | best-classical c | VERDICT |
|---------|-------|-----------------|---------------|------------------|---------|
| 3-SAT   | 2^n | 1.000 | 0.500 | 1.000 (SETH) | SURVIVES |
| P1      | n! | | | — | |
| P2      | n! | | | — | |
| P3      | 2^n | | | | |
| P4      | 2^n | | | | |
| P5      | n! | | | — | |

### Hardware feasibility axis (subset only — from §3)
| problem | n | Grover iters | Aer marked-prob | **device marked-prob** | 1/\|S\| floor | noise penalty |
|---------|---|--------------|-----------------|------------------------|--------------|---------------|
| 3-SAT   | 4 | | | | 0.0625 | |
| P3      | 8 | | | | 0.0039 | |
| P4      | 8 | | | | 0.0039 | |
| P1/P2/P5| — | N/A (no HW Grover oracle) | | | | |

---

## 6. How to read it (evaluation guide)

1. **Theorem axis is the point.** Every problem shows classical slope `1.0` / quantum
   slope `0.5` — the BBBV-optimal quadratic **query** speedup, exact by counting, true on
   any hardware or none. If a device run is noisy, the theorem is unaffected.
2. **The √2 line decides survival, not the device.** `best-classical c > 0.5` ⇒ the
   advantage survives *over the best known classical method*; `c ≤ 0.5` ⇒ it collapses.
   Only 3-SAT (c=1.0) clearly survives; P4 is on the line; P1/P2/P3/P5 collapse (structural
   ×3, algebraic ×1).
3. **Device marked-prob ≫ floor = feasibility, not victory.** A high device probability
   proves Grover amplifies the right state on real silicon. It says nothing about wall-clock
   — the classical brute force still finishes faster on these `n`. Do not upgrade this to an
   advantage claim.
4. **P3 is the trap.** Grover amplifies beautifully on hardware, yet the problem
   *collapses* — classical number theory (factor + Tonelli–Shanks + CRT) is sub-exponential.
   The real quantum win is Shor. This is the "where Grover does NOT win" exemplar.
5. **P4 is the star.** Borderline both ways: its exact classical solver runs at ≈`2^{n/2}`,
   so the query advantage neither cleanly survives nor collapses. Trust the seed sweep
   (`problems/p4_kernel_digraph/RUNLOG.md`), not one seed.

---

## 7. One-shot reproduce (no hardware)
```bash
# full classical + theorem + verdict map, then re-render the figure
bash -c 'for p in p1_betweenness p2_numerical_matching p3_quadratic_congruences p4_kernel_digraph p5_minla; do python -m problems.$p.best_classical --seed 7; done'
python -c "from framework.ledger import load,validate,render_markdown; from framework import map_figure; l=load(); validate(l); render_markdown(l); map_figure.render('research_runs/ledger.json', out='research_runs/map'); print('map re-rendered')"
```
Hardware adds the §3 feasibility rows on top; it never changes the verdict.
