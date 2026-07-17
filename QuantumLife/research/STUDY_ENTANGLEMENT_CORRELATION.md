# Study: Does the entangling chain imprint measurable spatial correlation on the quantum-grown genome?

**Status:** design (reference doc for building the study)
**Code:** `QuantumLife/code/research_qtree.py`
**Output:** `QuantumLife/research_runs/`
**Fork of:** `QuantumLife/code/qtree.py` (art project — untouched)

---

## 1. One-line question

When we grow the tree on real hardware, does the neighbour-entangling layer
(CX + controlled-Rx down a qubit chain) leave a **spatial correlation
signature** in the measured genome bits that the classical, no-entanglement
surrogate **cannot** reproduce?

If yes: the "quantum connection" is doing real, measurable work, not just
supplying randomness a PRNG could fake. If no: the pipeline is a
random-number-driven L-system with a quantum-flavoured logo, and we should say
so plainly.

---

## 2. Why this is worth doing

The art project already runs a genuine 108-qubit circuit every generation, but
the only thing it ever measured was **per-qubit diversity** (mean binary
entropy). That number is *blind to entanglement*: 108 independent biased coins
give the exact same diversity as 108 maximally-entangled qubits. So nothing in
the current pipeline can distinguish "quantum" from "classical noise dressed up
as quantum."

The circuit has one ingredient a product state (and the `--sim` surrogate) does
**not**: an entangling chain of depth `--layers`, each layer a CX ladder plus a
controlled-Rx of angle `CROSS_ANGLE`. Entanglement + shared gates create
**correlations between neighbouring qubits**. Correlations survive measurement
as statistical dependence between bit positions. That dependence is directly
measurable from the shot record — and it is exactly what the classical
surrogate lacks by construction (`run_sim` draws each qubit from its own
marginal, with only a hand-coded 3-tap smoothing).

This is the smallest honest, falsifiable claim the existing hardware pipeline
can actually support. It is also a real theme in NISQ-era work: showing that a
device produces structure a cheap classical model does not.

---

## 3. What we measure

For a shot record of bitstrings `b` (length `n = 108`), define the **connected
two-point correlation** along the chain:

```
C(d) = mean over positions i of [ <b_i b_{i+d}> - <b_i> <b_{i+d}> ]
c(d) = C(d) / C(0)                      (normalised; c(0)=1)
xi   = sum_{d>=1} c(d)                  (integrated correlation length)
```

- `<...>` averages over shots; the outer mean averages over chain positions
  (open chain, no wrap).
- `C(0) = mean_i p_i(1-p_i)` is just the average per-bit variance.
- **`C(d)=0` for all `d>0` is the null model** — statistically independent
  qubits, i.e. exactly what a product state / classical surrogate gives (up to
  finite-shot noise ~ `1/sqrt(shots)`).
- **`C(d) > noise`, decaying with `d`, is the entanglement fingerprint.** `xi`
  compresses the whole curve into one number: ~0 = no structure, larger = longer
  correlations.

Implemented in `research_qtree.py::two_point_correlation`. Recorded per
generation in every run file, and aggregated (mean ± std across repeats) in the
summary file.

Secondary (already present): per-qubit **diversity**, kept so we can confirm the
correlation effect is *not* just a diversity artefact.

---

## 4. Design (independent variables)

Everything is driven off `research_qtree.py` flags. Nothing needs new circuit
code.

| Arm | Command sketch | Role |
|-----|----------------|------|
| **A. Classical null** | `--sim --seed 100 --repeats 8` | no entanglement -> predicts `xi ≈ 0`. The baseline. |
| **B. Hardware, matched** | `--seed 100 --repeats 8 --layers 2` | same seeds/env as A -> paired comparison. |
| **C. Entanglement sweep** | `--layers 0,1,2,4,8` (one run each, hw) | dose–response: does `xi` grow with entangling depth? |
| **D. Coupling sweep** | vary `CROSS_ANGLE` = 0, 0.35, 0.7, π/2 (edit constant) | does correlation strength track the controlled-Rx angle? |
| **E. Noise probe** | run B on two different `--backend` / calibration days | how much correlation does device noise erase? |

Controls / good practice baked into the tool:

- **Paired seeds.** Repeat `r` uses `seed + r`, and the environment schedule is
  seeded, so an A run and a B run launched with the same `--seed` see the
  *identical* environment. Differences are then attributable to the backend, not
  to a different random tree.
- **Repeats.** `--repeats R` -> mean ± std per generation, so any sim-vs-hw gap
  can be checked against its own scatter (later: a two-sample / KS test on the
  per-repeat `xi` values).
- **Shots.** `--shots` sets the noise floor `~1/sqrt(shots)`. Use ≥4096 so a
  small true `C(d)` isn't buried. Arm F (below) pins this down empirically.

Optional **Arm F (shot floor):** `--sim` at `--shots` 256→8192. `xi` should sit
at the finite-shot noise level and shrink as `1/sqrt(shots)`. This calibrates
"how big must hardware `xi` be to count as real."

---

## 5. Hypotheses

- **H0 (null):** hardware `xi` is statistically indistinguishable from the
  `--sim` baseline at matched shots — i.e. entanglement leaves no surviving
  correlation signature after device noise. The quantum connection is
  decorative.
- **H1 (main):** hardware `xi` is significantly above the sim baseline, decays
  with distance `d`, and **increases with `--layers` and with `CROSS_ANGLE`**.
  The entangling chain imprints real, tunable structure.
- **H2 (partial):** a signature exists at `--layers 1` but **saturates or
  collapses** as layers grow, because deeper circuits accumulate more two-qubit
  gate error than added correlation — the NISQ sweet-spot story.

---

## 6. Expected results & how we read them

| Observation | Reading |
|-------------|---------|
| `--sim` `xi ≈ 0 ± 1/sqrt(shots)`, flat `c(d)` | baseline behaves as designed (sanity check) |
| hw `xi` > sim by many sigma, `c(d)` decays with `d` | **H1 supported** — entanglement signature present |
| hw `xi` rises with `--layers` then D-arm rises with `CROSS_ANGLE` | dose–response -> effect is causal, not an artefact |
| hw `xi` peaks at low layers, falls by `--layers 8` | **H2** — noise-limited; report the optimal depth |
| hw `xi` ≈ sim within scatter | **H0** — honest negative; say the connection is cosmetic |
| diversity identical across arms but `xi` differs | confirms the effect is *correlation*, not bias — the whole point |

All four qualitative outcomes (clean positive, dose–response, NISQ-limited,
clean negative) are publishable/reportable. A negative is a real result here,
not a failure.

---

## 7. Threats to validity

- **Finite-shot bias.** `C(d)` has O(1/shots) noise; always compare against the
  sim baseline at the *same* shots, never against literal 0.
- **Transpilation / SWAPs.** Correlation is only "nearest-neighbour" if the
  logical chain maps to a physical chain. `qtree` already picks a SWAP-free
  chain via `layout.best_chain`; record `qubit_list` (done) and don't compare
  across different chains.
- **Environment bias masquerading as correlation.** The per-slot Rx/Ry biases
  are deterministic, so they shift marginals `p_i` but the *connected* `C(d)`
  subtracts `p_i p_j` — bias alone cannot create `C(d)>0`. Good, but keep the
  bias fixed across A vs B (paired seeds handle this).
- **Readout correlation.** Correlated measurement error can mimic `C(d)`.
  Mitigation for a later pass: compare against a `--layers 0` hardware arm
  (encode + measure, no entangling gates) — any `xi` there is pure
  device/readout artefact and should be subtracted.

---

## 8. Deliverables

1. Summary JSONs in `research_runs/` for arms A–E (F optional).
2. A `c(d)` decay plot (sim vs hw, overlaid) and an `xi` vs `--layers` plot.
3. A short write-up stating which hypothesis held, with the sim baseline and
   sigma levels quoted.

## 9. How to run (reference)

```bash
# A: classical baseline
python code/research_qtree.py --sim --generations 14 --shots 4096 \
    --seed 100 --repeats 8 --name A_baseline

# B: hardware, paired
python code/research_qtree.py --generations 14 --shots 4096 \
    --seed 100 --repeats 8 --layers 2 --name B_hw

# C: entanglement sweep (repeat per layer count)
for L in 0 1 2 4 8; do
  python code/research_qtree.py --generations 8 --shots 4096 \
      --seed 100 --repeats 3 --layers $L --name C_layers$L
done
```

Every run writes per-repeat `*_run.json` (with a `correlation` block per
generation) and one `*_summary.json` (mean ± std of `diversity`, `C0`, `xi`,
and the mean `c(d)` curve). None of it touches the art project's `runs/` or the
web viewer.
