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

---

## Stage 1 — Signal with error bars + EXPERIMENTAL readout  (`stage1_temporal.py`, HW)  ~200s

### 1a — g* with error bars (~60s)
```
python stage1_temporal.py --no-sim --arm both --trait-basis 0.785 --generations 6 --shots 8192 --repeats 5 --name qdep_m2_s1_signal
```
**Best case:** quantum vs classical c(g) separated with **non-overlapping error bands** → a defended
small-G g* on hardware. Diagonal `trait_sigmaz` also gives the HW lifetime with σ.

### 1b — EXPERIMENTAL: mid-circuit / multiple measurements per shot (~140s)
The month-1 fix DEFERS readout. The original ambition (CD-3) reads every generation mid-circuit —
many measurements in one shot, one lineage per shot. Only worth it if Heron r2 mid-circuit
measurement is faithful enough not to destroy the signal. **Measure that, head-to-head, same chip.**
```
python stage1_temporal.py --no-sim --arm quantum --trait-basis 0.785 --readout deferred   --generations 8 --shots 8192 --repeats 3 --name qdep_m2_s1_deferred
python stage1_temporal.py --no-sim --arm quantum --trait-basis 0.785 --readout midcircuit --generations 8 --shots 8192 --repeats 3 --name qdep_m2_s1_midcirc
```
**Record:** c(g) deferred vs mid-circuit; measurements per shot; mid-circuit vs terminal readout error
(`meta.calibration`); QPU/wall time delta (feed-forward latency).
**Best case:** mid-circuit tracks deferred c(g) within σ → multi-measure-per-shot VIABLE → next study
can run true one-lineage-per-shot C(g). **Worst-but-useful:** mid-circuit visibly degrades → quantify
the collapse cost, stay deferred. Either is a real result — this is the experiment.

---

## Stage 2 — Locate the coherence / SWAP ceiling  (`stage2_scale.py`, HW)  ~120s

Sweep G to find where the quantum-vs-surrogate gap dies (the ceiling S3 must lift).

```
python stage2_scale.py --no-sim --arm both --gmin 4 --gmax 10 --trait-basis 0.785 --shots 8192 --repeats 3 --name qdep_m2_s2_sweep
```

**Record:** per-G `gstar`, c(g) bands, ideal-clone confound curve.
**Best case:** a clear ceiling G where the gap collapses → sizes `--gmax`/`--bond-dist` for the finale.

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

## Results (paste after the run)

| Stage | Key number | Value | σ / notes |
|-------|-----------|-------|-----------|
| S0 | η ratio; fidelity | | sim gate |
| S1a | g*(k2) | | error bars |
| S1b | c(g) deferred vs midcircuit; mid-circuit viable? | | experimental |
| S2 | ceiling G; g* per G | | |
| S3 | **Δg* (k2/k3)**; depth flat vs grow; herald_frac | | **the win** |

---

## Conclusion hooks (write-up after)

- Reproduction: 2018 lifetime holds (sim gate + HW `trait_sigmaz`) to g=? within σ.
- Ceiling: coherent inheritance survives to G=? before depth-noise kills the gap.
- Teleport: Δg* = ? extra generations at constant depth — clear win iff bars don't overlap.
- Experimental verdict: mid-circuit multi-measure per shot viable / not — decides the next study's
  readout design.
- Still open (flag honestly): with the `Ry+CX` classical-copier clone the off-diagonal separation runs
  *classical > quantum*; a coherence-propagating cloner is the lever for a quantum-favoured deep g*.
  Month-3 candidate.
