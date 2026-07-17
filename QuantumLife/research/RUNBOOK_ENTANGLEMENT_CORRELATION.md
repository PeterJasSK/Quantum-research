# Runbook: entanglement-correlation study — where I am, what to run next

**Read this to resume.** Companion to `STUDY_ENTANGLEMENT_CORRELATION.md` (the
why + design). This file = the execution log + next steps.

- **Code:** `QuantumLife/code/research_qtree.py`
- **Output:** `QuantumLife/research_runs/`
- **Question:** does the hardware entangling chain imprint spatial correlation
  `C(d)` on the genome bits that the `--sim` (no-entanglement) surrogate cannot?
- **Metric:** `C(d) = <b_i b_{i+d}> - <b_i><b_{i+d}>`, normalised `c(d)`,
  integrated length `xi = sum_{d>=1} c(d)`. `xi≈0` = no correlation (null).

Always `cd /home/peter/PycharmProjects/Quantum-research/QuantumLife` first.

---

## Phase 0 — local sim validation  ✅ DONE (2026-07-15)

Ran smoke + shot-floor sweep (`--sim`, seed 100, repeats 5). Result:

| shots | xi_mean avg | xi_std avg |
|-------|-------------|------------|
| 256   | 0.012       | 0.028      |
| 1024  | 0.007       | 0.011      |
| **4096** | **-0.000** | **0.008** |
| 8192  | 0.000       | 0.005      |

**Both gates passed:** `xi_mean → 0` as shots rise (null confirmed); `xi_std`
falls ~`1/sqrt(shots)` (metric sound).

**NOISE FLOOR @ 4096 shots: sigma_xi ≈ 0.008 (worst gen 0.012).**
=> significance bar: a hardware signal counts only if
`xi(B) - xi(B0) > ~3*sigma ≈ 0.024`.

Decision: **use 4096 shots** (8192 only halves std for 2x cost). Proceed to
Phase 1.

---

## Phase 1 — hardware, cheap arms  ⏳ NEXT (do when QC maintenance ends)

Run in this order. Same `--seed 100` on all three => paired / identical
environment schedule, so differences are the backend, not luck.

```bash
cd /home/peter/PycharmProjects/Quantum-research/QuantumLife

# 1. A — sim baseline, FREE, run first (confirms pipeline + env)
python code/research_qtree.py --sim --generations 8 --shots 4096 --seed 100 --repeats 3 --name A_base

# 2. B0 — hardware CONTROL: layers=0, no entangling gates (readout/device floor)
python code/research_qtree.py --generations 8 --shots 4096 --seed 100 --repeats 3 --layers 0 --name B0_ctrl

# 3. B — hardware MAIN: entangling chain on
python code/research_qtree.py --generations 8 --shots 4096 --seed 100 --repeats 3 --layers 2 --name B_hw
```

- **A first** — free, catches pipeline breakage before spending QPU.
- **B0 before B** — B0 is the device/readout artefact floor. Real signal is
  `xi(B) - xi(B0)`, never raw `xi(B)`.
- Cost: B0 + B = 2 × 8 gens × 3 repeats = **48 hardware jobs @ 4096 shots** +
  Heron queue time. Confirm the right IBM instance is active before firing.

**Phase 1 gate:** if `xi(B) ≈ xi(B0)` (within scatter) => entanglement adds
nothing => **H0 answer reached, STOP.** Do not run Phase 2. Write up the
negative. Only continue to Phase 2 if `xi(B) - xi(B0) > ~0.024`.

---

## Phase 2 — sweeps  ⏸ ONLY IF Phase 1 shows signal

```bash
# C: entanglement dose-response (does xi grow with entangling depth?)
for L in 0 1 2 4 8; do
  python code/research_qtree.py --generations 6 --shots 4096 \
      --seed 100 --repeats 3 --layers $L --name C_L$L
done

#run after sometime
for L in 4 8; do
  python code/research_qtree.py --generations 6 --shots 4096 \
      --seed 100 --backend ibm_kingston  --repeats 3 --layers $L --name C_L$L
done

# D: coupling strength — edit CROSS_ANGLE constant in research_qtree.py
#    to each of 0, 0.35, 0.7, 1.57 and rerun, one --name per value:
#    python code/research_qtree.py --generations 6 --shots 4096 \
#        --seed 100 --repeats 3 --layers 2 --name D_ang070

# E: noise sensitivity — rerun B on a different day / backend
#    python code/research_qtree.py --generations 8 --shots 4096 \
#        --seed 100 --repeats 3 --layers 2 --backend ibm_<other> --name E_<backend>
```

---

## Evaluation (how to read the summaries)

Inputs = `research_runs/*_summary.json`. Each holds per-generation
`xi_mean`, `xi_std`, `C0_mean`, `diversity_mean`, and the mean `c(d)` curve.

Quick pull (per file):
```bash
jq -r '[.per_generation[].xi_mean] as $m |
  "xi avg \(([$m[]]|add)/($m|length))"' research_runs/<file>_summary.json
```

**Decision rule** (per hardware arm vs baseline):
```
signal = xi_hw_mean - xi_sim_mean        # or xi(B) - xi(B0) for artefact-subtracted
noise  = sqrt(xi_hw_std^2 + xi_sim_std^2)
z      = signal / noise
```
- `z < 2` and `xi(B) ≈ xi(B0)`  => **H0**: connection cosmetic. Honest negative.
- `z > 3`, `c(d)` decays with d, `xi` rises with layers (C) & angle (D)
  => **H1**: real, tunable entanglement signature.
- `xi` peaks at low layers then falls by L=8  => **H2**: NISQ noise-limited;
  report best depth.

**Cross-checks:**
- Diversity roughly equal across arms but `xi` differs => effect is
  *correlation*, not bias. This is the whole point — confirm it.
- Always subtract B0 from hardware `xi` before deciding.
- Never compare hardware `xi` to literal 0 — compare to the sim floor
  (sigma ≈ 0.008 @ 4096 shots) at the SAME shots.

---

## Threats (don't get fooled)

- **Finite shots:** `C(d)` has O(1/shots) noise; compare vs sim floor, not 0.
- **SWAPs:** correlation is nearest-neighbour only if logical chain maps to a
  physical chain. `layout.best_chain` picks SWAP-free; `qubit_list` recorded in
  each run file — don't compare across different chains.
- **Bias ≠ correlation:** connected `C(d)` subtracts `p_i p_j`, so deterministic
  per-slot bias can't fake `C(d)>0`. Good — but keep bias fixed across arms
  (paired seed does this).
- **Readout correlation** can mimic `C(d)` — that's exactly what B0 measures and
  what you subtract.

---

## Deliverables (end state)

1. Summary JSONs for A, B0, B (+ C/D/E if Phase 2 runs).
2. Plots: `c(d)` decay (sim vs hw overlaid); `xi` vs `--layers`; `xi` vs
   `CROSS_ANGLE`.
3. Short write-up: which hypothesis held, sim floor + z quoted.

**Open gap:** no analysis/plot script yet — evaluation is manual `jq` + the
decision rule above. Optional next build: `code/research_eval.py` to read the
summaries, do B0 subtraction + z-scores, emit the plots and a verdict line.

---

## TL;DR to resume tomorrow

Phase 0 done, metric validated, floor = 0.008 @ 4096 shots. When QC maintenance
ends: run the 3 Phase-1 commands above (A, B0, B — in that order). Then apply the
decision rule: `xi(B) - xi(B0)` beats 0.024 => signal, do Phase 2; else H0, stop
and write the negative.
