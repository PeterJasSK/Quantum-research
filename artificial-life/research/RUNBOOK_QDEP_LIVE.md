# RUNBOOK — QDEP Live Tests (Coherence Depth of an Inherited-Entanglement Genealogy)

Live-hardware run plan for the QDEP epic (`plans/epic-qdep-coherence-depth-genealogy.md`).
Modelled on `QuantumLife/research/RUNBOOK_TELEPORT_LONGRANGE.md`. Each phase lists the
exact command, **the best case that can happen**, and what to record — so a conclusion can
be written by filling the expected-vs-observed table in §Conclusion.

```
cd artificial-life/code
```

**Headline number:** `g*` = max generation where the coherent quantum lineage beats a
matched classical measure-and-resend surrogate by `> k·σ` (k=2 headline, k=3 reported).
Stage-3 extension: `Δg* = g*(teleport) − g*(swap)` at matched settings.

---

## Preconditions (do not skip — live time is expensive)

- **`QEAAS_API_KEY` set** in env (CD-7). S1+ is **fail-closed**: `QRNGUnavailable` aborts
  the run rather than silently PRNG-falling-back. Verify the key resolves *before* booking.
- **IBM account reachable**; `pipeline_common.connect` auto-selects least-busy **Heron r2**.
  Named epic risk — confirm access the day of the run.
- **`pipeline_common` on `sys.path`** (lives in `CalibrationGuidedHighYieldQRNG/code`, not
  copied — CD-2). Each stage file already adds it; confirm no `ImportError` under `--sim`.
- **Pin the backend** for cross-arm comparability: every arm of a stage MUST run on the
  **same backend + same register size + same seeds/schedule/shots** (comparison rule from
  the teleport runbook). Do not mix a fresh arm against an old-backend arm.

---

## Phase 0 — Pre-flight sim gate (free, MANDATORY before any HW)

Current sim baseline is **g\*=1** (`qdep_s1_sim_*_summary.json`): quantum ≈ classical,
`C(g)≈0.002–0.004`, i.e. on the shot-noise floor. **Noise only makes hardware worse**, so
if the *noiseless* sim cannot separate the arms, hardware cannot either — you would buy a
`g*=1` result at full QPU cost. Resolve this on the simulator first.

```
# S0 toolchain gate — fidelity vs ideal must be ~1.0 per generation (M1)
python stage0_reproduce.py --generations 6 --shots 4096 --seed 100 --name qdep_s0

# S1 separation check — sweep mut-scale until the ideal arms separate above σ
python stage1_temporal.py --sim --arm both --generations 8 --repeats 5 --shots 8192 --mut-scale 0.1 --name qdep_s1_scan01
python stage1_temporal.py --sim --arm both --generations 8 --repeats 5 --shots 8192 --mut-scale 0.5 --name qdep_s1_scan05
python stage1_temporal.py --sim --arm both --generations 8 --repeats 5 --shots 8192 --mut-scale 1.0 --name qdep_s1_scan10
```

**Best case (Phase 0):** some `--mut-scale` (and/or larger `--shots`) lifts `C_q(0)` well
above the floor and makes the noiseless quantum arm ride **above** the classical surrogate
by `> 2σ` for several generations → sim `g* ≥ 3`. That is the green light: hardware has
headroom to spend. **If no setting beats `g*=1` in noiseless sim, STOP** — the observable
is degenerate; do not book hardware. Record the chosen `--mut-scale`/`--shots` and carry
them **identically** into every live phase below.

---

## Phase 1 — S0/S1 live confirm (small G, cheap HW)

Bank the toolchain and a small-scale hardware `g*` before scaling. Pin the backend.

```
# Classical surrogate control — must stay g*-flat (proves the surrogate is honest)
python stage1_temporal.py --arm classical --backend ibm_kingston --generations 8 --repeats 5 --shots 8192 --name qdep_s1_cl_hw

# Quantum coherent-clone arm — same backend, seeds, schedule, shots
python stage1_temporal.py --arm quantum   --backend ibm_kingston --generations 8 --repeats 5 --shots 8192 --name qdep_s1_q_hw
```

**Best case (Phase 1):**
- **M1** — per-generation `fidelity_vs_ideal ≈ 1.0` at g=1 (2018-level agreement holds on
  chip); mild honest decline as g grows.
- Quantum `C_q(g)` sits **above** classical `C_cl(g)` by `> 2σ` at small g → small-scale
  **`g* ≥ 2`** confirmed on real hardware, matching the sim headroom from Phase 0.
- `meta.entropy_provenance` present on every mutation (request_id + receipt + entropy_epoch)
  — M7 satisfied, no `QRNGUnavailable`.

Worst-acceptable: `g*=1` on HW even though sim showed headroom → decoherence eats the whole
budget at this backend/calibration; still publishable as a hard coherent-generation number.

---

## Phase 2 — S2 scale sweep (the core result: g* with error bars)

Grow G to find where the quantum-vs-surrogate gap dies. `--width 1` (single lineage)
unless σ is too loose to resolve `g*` after the sweep.

```
# Three arms on the SAME backend: quantum, classical surrogate, ideal-clone confound curve
python stage2_scale.py --arm both  --backend ibm_kingston --gmin 2 --gmax 12 --repeats 8 --shots 8192 --k 2 --name qdep_s2_hw
python stage2_scale.py --arm ideal --sim                  --gmin 2 --gmax 12 --repeats 8 --shots 8192 --k 2 --name qdep_s2_ideal
```

**Best case (Phase 2):**
- Three separated curves: **ideal-clone `C(g)`** (top, noiseless approximate-clone decay
  only) **> quantum HW `C_q(g)`** (middle) **> classical surrogate `C_cl(g)`** (bottom,
  ≈flat near 0). The gap between ideal and quantum-HW is *pure decoherence*; the gap between
  quantum-HW and classical is the *inherited-quantum signal* (M4 confound cleanly separated).
- Headline **`g*` with tight ±σ error bars** at the largest resolvable G — the paper's core
  integer. Best realistic case: `g*` in the mid-single-digits before the bands overlap.
- `g*` stable across `--repeats 8` (σ small enough that k=2 and k=3 give the same or
  adjacent integers). Every mutation entropy-traced (M7 carried forward), no fail-closed abort.

Falsification-still-valuable: if classical matches quantum within k·σ at every G, `g*=1` —
report as a hard "coherent inheritance is classically fakeable on this device" bound.

---

## Phase 3 — S3 break the SWAP ceiling (Δg*)

Only after `g*` is banked (Phase 2). Changes exactly one thing vs S2: how the inheritance
CX is routed. Teleport needs a 2-qubit corridor → `--bond-dist ≥ 3`. Run both routings at
matched settings on the **same** backend.

```
# Both routings, matched — swap ladder (O(distance) depth) vs teleported CNOT (constant depth)
python stage3_teleport.py --routing both --backend ibm_kingston --gmin 2 --gmax 12 --bond-dist 3 --herald --repeats 8 --shots 8192 --k 2 --name qdep_s3_hw

# Sim parity check (validates pipeline + logical_depth claim only; swap≡teleport logically noiseless)
python stage3_teleport.py --routing both --sim --gmin 2 --gmax 6 --bond-dist 3 --name qdep_s3_sim
```

**Best case (Phase 3):**
- **`Δg* = g*(teleport) − g*(swap) > 0`** — teleport routing buys ≥ 1 extra coherent
  generation on the same chip (M5). Bigger `--bond-dist` → bigger `Δg*` (SWAP pays more depth).
- **`logical_depth`** per generation: teleport ≈ **constant** vs swap **∝ routed distance**
  (M6) — the mechanism, visible directly in `qc.depth()`.
- Honesty caveat recorded (AC-S3.3): teleport is *constant-depth long-range interaction at
  the cost of ancillas + classical latency*, **not** a free bypass. Must appear in run.json
  and console for every teleport arm.

Worst-acceptable: `Δg* = 0` but `logical_depth` still shows the constant-vs-growing split —
the depth advantage exists but is swamped by ancilla/feed-forward overhead at this scale;
report honestly.

---

## Phase 4 — S4 aggregate + write-up (NOT YET BUILT)

`stage4_evaluate.py` does not exist yet — build it before this phase (epic §14). It reads
`research_runs/*_summary.json` and emits:

```
python stage4_evaluate.py   # reads research_runs/*, writes figures/ + research/CONCLUSION_QDEP_COHERENCE_DEPTH.md
```

**Best case (Phase 4):** THE figure — `C_q(g)` solid above `C_cl(g)` dashed, ideal-clone as
a third reference curve, shaded ±σ bands, a single vertical marker at `g*` where "still
quantum" becomes "classically fakeable"; plus the fidelity table (M1), the g* summary
(k=2,k=3), and the S3 `Δg*` / `logical_depth` panel. One defended claim (AC-S4.4).

---

## Read (how to score each run)

- `summary.json → per_generation[g].C_g_mean.{quantum,classical}` (signal) and `.C_g_std`
  (bands); `gstar.{k2,k3}` (headline). Teleport phase: `delta_gstar` + per-gen `logical_depth`.
- `run.json → generations[g].fidelity_vs_ideal` (M1), `generations[g].trait_sigmaz` (the
  2018 lifetime observable), `meta.entropy_provenance` (M7), `meta.calibration` (backend snapshot).
- **Rule:** the quantum arm counts as "still quantum" at generation g only if
  `|C_q(g) − C_cl(g)| > k·σ`. Everything at/below that boundary the surrogate matches is
  **plumbing, not inherited quantum life** (honesty invariant AC-S4.3).

---

## Conclusion template (fill after the live runs)

For each phase: best-case above vs what actually happened. Conclusion = where the two diverge.

| Stage | Metric | Best case | Observed | Verdict |
|-------|--------|-----------|----------|---------|
| S0 | `fidelity_vs_ideal` @ g=1 (M1) | ≈ 1.0, 2018-level | | |
| S1 | small-scale `g*` on HW | `≥ 2`, quantum > classical `>2σ` | | |
| S1 | `meta.entropy_provenance` (M7) | every mutation signed | | |
| S2 | headline `g*` ± σ (M3) | mid-single-digits, tight bands | | |
| S2 | ideal-clone confound (M4) | ideal > quantum-HW > classical, cleanly split | | |
| S3 | `Δg*` (M5) | `> 0`, grows with `--bond-dist` | | |
| S3 | `logical_depth` (M6) | teleport const, swap ∝ distance | | |
| S4 | THE figure + claim (AC-S4.4) | g* marker where quantum→fakeable | | |

**Single defended claim to test (AC-S4.4):** *On Heron r2, coherent inheritance beats a
matched classical measure-and-resend surrogate up to a measurable generation `g*`, reported
as an integer with error bars and a cloning-confound control — and teleport routing extends
it by `Δg*`.* If the surrogate matches at every accessible G, the claim is falsified for
current devices and the result is the hard `g*=1` coherent-generation bound (still publishable).
