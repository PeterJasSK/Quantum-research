# F8 Quantum Sandpile — Run Log (real QC)

**Driver:** `THESIS/CriticalQuantumLife/code/sandpile_batches.py` (builds on `sandpile.py` +
`sandpile_analysis.py`, reuses F5 `hardware_batches.py` chain picker + calibration gate)
**Study:** the self-ORGANIZED (self-tuned) absorbing-state / directed-percolation critical point —
the counterpart to the *hand-tuned* transition of arXiv:2512.07966 (30 q) / IBM 2509.18259 (100 q).
Fixes the failed Run-1 criticality gate (σ=0.44) **by design**: SOC reaches criticality via
drive-when-quiet (slow drive + fast dissipation, Dickman et al. 1998), not by luck.
**Backend (target):** any operational Heron (Run-1 used `ibm_kingston`, 156-q Heron r2).

Run everything from the code directory:
```bash
cd /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/code
```

> **Plan:** `plans/feature-F8-quantum-sandpile.md`. **Tiers:** `LEAP-candidates-ranked.md` §10.7.
> **MANUAL SUBMISSION IS LAW (epic §3).** `emit` writes transpiled QPY + a submit bundle and STOPS;
> the user submits on QC by hand and drops the per-shot memory back. The ONLY unattended path is the
> Aer `signcheck` — **mandatory before any hardware artifact is emitted** (AC-F8.7).

---

## Budgets are counted in SHOTS

Every budget in this log is a **shot count**, not a wall-clock or QPU-second estimate. A run costs
`circuits × shots/circuit` (× ZNE factors when on) — nothing more. QC queue and allocation time is
whatever the device gives you at submit time; it is not modelled here. Print any pass's shot
arithmetic without touching QC:

```bash
python sandpile_batches.py budget --tier verify                # 6 circuits x 4000 = 24,000 shots
python sandpile_batches.py budget --tier 10min                 # 6 circuits x 8192 = 49,152 shots
python sandpile_batches.py budget --tier 180min                # 170 x 8192 x3 ZNE = 4,177,920 shots
```

## The three run logs at a glance

The three logs are **one chain**, not three separate studies. Run log 1 is the cheap verify pass —
the same six circuits Run log 2 uses, submitted at reduced shots — that gives a first indication the
mechanism runs and closed differs from yoked before any full-shot spend. Run log 2 is the full-shot
go/no-go that decides whether Run log 3 is worth the big allocation.

| Run log | Shot budget | What it buys | Gate it clears |
|---|---|---|---|
| **1 — verify** | **6 × 4,000 = 24,000 shots** | mechanism transpiles + runs on Heron; a first eyeball that closed ≠ yoked | wiring / does-it-work |
| **2 — 10-min** | **6 × 8,192 = 49,152 shots** | activity self-parks nonzero **and** beats the yoked control (existence + the decisive contrast) | go/no-go for Run log 3 |
| **3 — 180-min** | **170 × 8,192 × 3 = 4,177,920 shots** | DP universality (α, z=1.58, β via finite-size scaling), certified quantum, robust, beats both controls | PRL/PRX-grade headline |

Run log 1 (`--tier verify`) and Run log 2 (`--tier 10min`) emit the **same six W=14 circuits**
(closed/yoked × T∈{40,60,80}). The only difference is shots: the `verify` tier is 4,000/circuit for
the eyeball, `10min` is 8,192/circuit for the statistical go/no-go. So Run log 1 is cheap and
throwaway — if it looks right, re-emit the same six under `--tier 10min` for Run log 2.

---

## RUN LOG 1 — verify (does it work? 24,000 shots)

**Goal.** Cheap first indication. Run the six `verify`-tier circuits on Heron at 4000 shots each and
confirm two things only: (a) the dynamic circuit (mid-circuit measure + feed-forward conditional
reset + drive-when-quiet `if_test`) actually **transpiles and executes** on the device, and (b) a
first eyeball that the **closed arm parks at a different density than the yoked control**. No
exponents, no statistics — just "is what I'm doing working".

### Step 1 — Aer go/no-go (free, mandatory)
```bash
python sandpile_batches.py signcheck --tier verify
```
Runs a **laptop-cheap smoke config (W=8, T≤40)** closed-cold + matched-rate yoked **+ closed-hot**
on Aer's dynamic simulator — NOT the W=14 hardware width. Self-organization is width-independent, so
the gate is checked small (a statevector dynamic sim at W≥12 is too heavy for a workstation; the
hardware circuits `emit` are still W=14). It prints the density / σ / avalanche contrast, the
**both-basins convergence** (cold rises + hot falls to the same set-point), and a GO / NO-GO. GO
requires **both** `self_organized` (beats yoked) **and** `converged` (both basins meet). **Do not
emit hardware unless this says GO** (epic §3, sim-first). If the sim is still too heavy, shrink it:
`signcheck --tier verify --width 6 --steps 30`. Paste output:
```
(base) peter@home:~/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/code$ python sandpile_batches.py signcheck --tier verify
=== F8 Sandpile signcheck [verify] on Aer (smoke W=8 steps=40 shots=2048; hardware width=14) ===
    hardware budget: 6 circuits x 4000 shots = 24,000 shots total
            density   sigma    alpha   n_av
  closed     0.097   0.721   5.887  18577
  yoked      0.247   1.114   4.941   5735

  density gap (closed-yoked): -0.149
  closed self-parks nonzero : True
  closed sigma nearer 1     : False

  SELF-ORGANIZED (AC-F8.3): NO  (drive-when-quiet self-tunes; yoked does not)

  both-basins: cold rho=0.09728698730468752 (flat) vs hot rho=0.0969696044921875 (fell)  converged=True  (self-organized set-point is an attractor reached from BOTH sides)

  SIGN-CHECK [verify]: NO-GO (fix before QC)
  -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/sandpile_signcheck_verify_sandpile_report.json```

```

### Step 2 — emit the six verify circuits
```bash
python sandpile_batches.py emit --tier verify --backend ibm_kingston
# -> research_runs/sandpile_verify_ibm_kingston_submit.json  (+ 6 QPY circuits, bundle records shots=4000)
```
`emit` picks the low-error chain, records the live calibration into the bundle, transpiles all six
circuits to QPY, and **STOPS**. The `verify` tier bakes in 4000 shots so `ingest` normalises against
the real shot count. The six QPY files are:
```
sandpile_verify_closed_cold_W14_T40_s100.qpy   sandpile_verify_yoked_cold_W14_T40_s100.qpy
sandpile_verify_closed_cold_W14_T60_s100.qpy   sandpile_verify_yoked_cold_W14_T60_s100.qpy
sandpile_verify_closed_cold_W14_T80_s100.qpy   sandpile_verify_yoked_cold_W14_T80_s100.qpy
```
Paste the emit output (chain + calibration + budget line):
```
<PASTE emit OUTPUT HERE>
```

### Step 3 — submit all six on QC by hand
Submit each of the six QPY circuits on the device at **4000 shots, WITH per-shot memory** (memory is
required — A(t) is rebuilt from each shot's per-step registers; see Recovery/gotchas). Save one
memory JSON per circuit (a raw list of shot bitstrings, or `{"memory": [...]}`). Note the
QPU-execution time if you like, but it is not a budget input — the budget is the 24,000 shots.
```
<PASTE the six submissions HERE — 4000 shots each, memory ON>
```

### Step 4 — ingest + eyeball the contrast
```bash
python sandpile_batches.py ingest --bundle ../research_runs/sandpile_verify_ibm_kingston_submit.json \
    --memory <closed_T40.json> <yoked_T40.json> <closed_T60.json> <yoked_T60.json> \
             <closed_T80.json> <yoked_T80.json>
python sandpile_batches.py analyze --tier verify
# -> research_runs/sandpile_verify_sandpile_report.json
```
`ingest` maps each memory file onto its trajectory bundle entry (in bundle order) and writes one
run-JSON per circuit. `analyze` pairs closed/yoked by (W, T, seed) and prints `self_organized` per
config.
```
<PASTE ingest + analyze OUTPUT HERE>
```

**Budget (Run log 1).** 6 circuits × 4000 shots = **24,000 shots**.

**What it can claim:** the dynamic-circuit mechanism transpiles and runs on Heron; a first
closed-vs-yoked density difference in the predicted direction.
**What it can't:** nothing statistical — 4000 shots on six short trajectories has no clean avalanche
power-law, no exponents, no witness statistics.

**Verdict / notes:**
```
<did all six transpile + run? closed vs yoked density gap visible? any circuit fail to submit?>
```

---

## RUN LOG 2 — 10-min go/no-go (existence + the decisive contrast, 49,152 shots)

**Goal.** The full-shot binary: does the activity **self-park at a nonzero steady density** under
drive-when-quiet, and does the **yoked control differ**? Same six circuits as Run log 1, now at
8192 shots for real error bars. This is the existence-of-self-organization result — a real yes/no,
and the gate for Run log 3.

### Sequence
```bash
python sandpile_batches.py signcheck --tier 10min                       # laptop-cheap W=8 smoke, must be GO
python sandpile_batches.py emit      --tier 10min --backend ibm_kingston # 6 QPY + bundle at 8192, STOP
#   submit all 6 QPY on QC by hand, 8192 shots each, WITH per-shot memory, save 6 memory JSONs
python sandpile_batches.py ingest   --bundle ../research_runs/sandpile_10min_ibm_kingston_submit.json \
    --memory <m0.json> <m1.json> <m2.json> <m3.json> <m4.json> <m5.json>
python sandpile_batches.py analyze  --tier 10min
# -> research_runs/sandpile_10min_sandpile_report.json
```
The 6 circuits are **W=14 × T∈{40,60,80} × {closed, yoked}** (seed 100) — the same six as the
`verify` tier, now at 8192 shots. The yoked schedule is baked at the closed loop's *measured* drive
rate (matched injection energy, AC-F8.3). The `10min` bundle
(`sandpile_10min_..._submit.json`) is separate from the `verify` bundle, so nothing is overwritten.

**Output:**
```
<PASTE emit + ingest + analyze OUTPUT HERE>
```

### Budget (Run log 2)
| item | value |
|---|---|
| circuits | 6 (W14 × T{40,60,80} × {closed,yoked}) |
| shots / circuit | 8192 |
| **total shots** | 6 × 8192 = **49,152** |

**Optional rigor if you have the shots to spare:** raise to 3 seeds (100/101/102) → 18 circuits →
**147,456 shots**, tightening the density/σ error bars before you decide on Run log 3. (Bump
`seeds` to 3 in the 10min `TIERS` entry, then re-`budget`/`emit`.)

### Read the report (`sandpile_10min_sandpile_report.json`)
- `contrasts[i].contrast.closed.density.density` **> 0** and steady → activity self-parks. *AC-F8.4a*
- `contrasts[i].contrast.self_organized` **true** → closed parks nonzero **and** its σ is nearer 1
  than yoked's. *AC-F8.3 — the whole claim.*
- `contrasts[i].contrast.density_gap` → closed-minus-yoked steady density (the decisive number).

**What it can claim:** "under drive-when-quiet the activity self-organizes to a nonzero steady
density, and the yoked control does not." Existence + the decisive contrast.
**What it can't:** no clean avalanche power-law (too few avalanches), no exponents, no finite-size
scaling, weak witness statistics.

> **Go/no-go rule:** `self_organized == true` on hardware → fund Run log 3. `false` → stop; report
> the honest negative (the width/noise budget at which SOC dies), do **not** spend the 180-min
> allocation.

**Verdict / notes:**
```
<self_organized? density gap? did closed self-park where yoked drifted?>
```

---

## RUN LOG 3 — 180-min full paper (DP universality, certified quantum, 4,177,920 shots)

**Goal.** Upgrade "it self-organizes" to "it self-organizes to a **certified directed-percolation
critical point**": avalanche exponent α, dynamic exponent z=1.58, order-parameter finite-size
scaling across widths, the cluster-witness certification, robustness to grain/relaxation, and both
classical controls — with error mitigation.

### Sequence
```bash
python sandpile_batches.py signcheck --tier 180min                       # Aer GO (incl. witness cert)
python sandpile_batches.py emit      --tier 180min --backend ibm_kingston # 170 QPY + bundle, then STOP
#   submit all QPY on QC by hand, 8192 shots, per-shot memory, TREX readout + ZNE (3 noise factors)
python sandpile_batches.py ingest   --bundle ../research_runs/sandpile_180min_ibm_kingston_submit.json \
    --memory <m0.json> ... <mN.json>            # the trajectory circuits (witness handled separately)
python sandpile_batches.py analyze  --tier 180min
# -> research_runs/sandpile_180min_sandpile_report.json  (includes finite_size_scaling)
```
Emits **3 widths (W∈{12,20,30}) × 3 T-values × 5 seeds × {closed-cold, closed-hot, yoked}** = 135
trajectory circuits, **+15 cluster-witness circuits** (5 seeds × 3 widths), **+20 grain×relaxation
robustness circuits** (grain∈{1,2} × relax∈{0.25,0.45} × 5 seeds at W=20) = **170 circuits**. The
**closed-hot** arm is the chaotic-side basin (saturated start): the pile must relax DOWN to the same
self-organized set-point the **closed-cold** arm climbs UP to — the both-basins convergence proof
that the critical point is a genuine attractor, not an initial-condition artefact. Error mitigation:
TREX readout twirling + ZNE (each circuit run at 3 noise factors → ×3 executions).

**Output:**
```
<PASTE emit + ingest + analyze OUTPUT HERE>
```

### Budget (Run log 3)
| item | value |
|---|---|
| trajectory circuits | 135 (3W × 3T × 5seed × 3 = closed-cold + closed-hot + yoked) |
| witness circuits | 15 (3W × 5seed) |
| robustness circuits | 20 (2 grain × 2 relax × 5 seed @ W20) |
| **total circuits** | **170** |
| ZNE noise factors | ×3 |
| executions | 170 × 3 = **510** |
| shots / execution | 8192 |
| **total shots** | 510 × 8192 = **4,177,920** |

> If the device allocation is tight, drop a width or a seed before dropping shots — statistics per
> config matter more than the third width. Re-`budget --tier 180min` after editing the `TIERS`
> entry to see the new shot total.

### Read the report (`sandpile_180min_sandpile_report.json`)
- `contrasts[i].contrast.self_organized` **true** across configs → SOC is not a single-seed fluke.
- `contrasts[i].contrast.closed.avalanche_alpha.alpha` **≈ 1.5** with `n_avalanches ≥ 20` and a KS
  `gof_pvalue` that doesn't reject → the DP avalanche signature. *AC-F8.4b/c*
- `contrasts[i].contrast.closed.sigma.mean` **→ 1** (ci95 spanning 1) → branching criticality.
- `finite_size_scaling.per_width` → density/σ/α vs W; `universality_ready` **true** only when every
  width has ≥ 20 avalanches. `dp_reference` = {α 1.5, z 1.58} for comparison. *AC-F8.4*
- `contrasts[i].convergence.converged` **true** → the cold basin (`transient="rose"`) and the hot
  basin (`transient="fell"`) reach the **same** steady density/σ under the identical drive-when-quiet
  rule → the critical point is a **self-organized attractor**, not an initial-condition artefact.
  This is the load-bearing "self-organized" evidence, above and beyond the yoked contrast.
- Cluster-witness certification (from the witness circuits, `certify_steady_state`): witness signal
  **above** the `k/√shots` null → the self-organized critical state is certified quantum. *AC-F8.5*
  — reported as **margin-above-null** (the certification layer), the DP result stays the headline.

**What it can claim (if it lands):** "the self-organized critical point is in the directed-
percolation universality class (α, z=1.58, β via finite-size scaling), reached without fine-tuning,
certified quantum, robust to grain/relaxation, and beats both classical controls." PRL/PRX-grade.

**Honest-negative caveat (plan §9).** NISQ noise adds *uncontrolled* dissipation that can push the
pile subcritical (the Run-1 failure mode). If α won't fit or σ sits well below 1 on hardware even
with mitigation, that is the width/noise budget at which SOC dies — report it, lead with the
avalanche/σ result at the widths that *did* self-organize, and treat the witness as the certification
layer, not the headline. **A single subcritical run does not establish SOC** (honesty gate, §7).

**Verdict / notes:**
```
<α per width? σ→1? finite-size scaling consistent with DP? witness above null? robustness holds?>
```

---

## Recovery / gotchas

- **Per-shot memory is required.** The activity time-series A(t) is reconstructed from each shot's
  per-step classical registers (`sandpile.assemble_run`), so every QC submission must return **memory
  (per-shot bitstrings)**, not just aggregated counts. `ingest --memory` expects one JSON per
  trajectory circuit: a raw list of shot strings, or `{"memory": [...]}`.
- **Aer signcheck is the kill-gate, run small.** `signcheck` must print GO before `emit`. It runs a
  W=8 smoke sim (not the hardware width) so a workstation can run it; `--width`/`--steps` shrink it
  further. NO-GO = the mechanism isn't self-organizing on noiseless sim; fix `SPREAD_THETA` /
  `RELAX_P` (the branching/dissipation balance) before spending any QC (plan §9 grain/relaxation
  sweep). The current defaults (θ=1.20, relax_p=0.35) print NO-GO at W=8 — the σ criterion, not the
  density — so tune before hardware.
- **Verify vs full shots.** Run log 1 is `--tier verify` (4000 shots, baked into the tier and the
  bundle); Run log 2 is `--tier 10min` (8192 shots). Submit each at the shots its bundle records. A
  one-off `--shots N` override still works on any tier's `emit`/`budget` if you need it.
- **Ingest order + memory-file count.** `ingest` maps memory files to trajectory circuits **in
  bundle order** and aborts if the count mismatches. Keep the memory JSONs named/ordered to match the
  QPY list the emit output prints.
- **Ingest each circuit once.** A second ingest of the same circuit overwrites its run-JSON (keyed by
  `name_tier_arm_init_W_T_seed`) — harmless (idempotent), but don't double-count in a hand tally.
- **Calibration gate is fail-closed.** `emit` aborts if the best chain breaches the 2q/readout
  thresholds (a bad chain sinks the witness below the null → false negative). `--allow-bad-chain`
  overrides (NOT for thesis runs).
