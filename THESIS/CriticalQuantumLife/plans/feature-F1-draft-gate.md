# Feature Plan — F1: DRAFT kill-gate (sim, toy scale) (`draft_gate.py`)

**Status:** Complete
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F1 (second; depends on F0 — gates F5 hardware)
**Artifact:** `THESIS/CriticalQuantumLife/code/draft_gate.py` (new)
**Drives:** `closed_loop.py` (F0)  ·  **Mirrors:** `artificial-life/code/stage5_fliptest.py` (kill-gate + `verify_run`)
**Author:** Claude (Opus) · **Date:** 2026-08-31

> No GitHub issue (F-ids). No tests (project directive): production code + manual verification only.

---

## 1. Context & goal

F1 is the **go/no-go before any hardware spend** — the same discipline as the virus `stage5_fliptest.py`
P0 kill-gate. On Aer at toy scale (W=4, ~15 generations) it must show all **three honesty-gate signals
exist**: (1) surprise falls under closed loop but NOT under yoked, (2) branching σ trends toward 1 (not 0),
(3) a scripted poke spikes-then-relaxes. It emits an explicit **GO / no-go** verdict into a `kill_gate`
JSON block and provides a `verify_run(path)` recompute-and-compare for reproducibility.

F1 writes **no new physics** — it drives F0's `run_closed_loop` / `run_yoked`, reads the `generations[]`
observables F0 logs, computes three boolean signals, reduces them to a verdict. The POC already showed the
witness + poke-recover on `ibm_kingston`; F1 completes the **surprise-vs-yoked** and **σ→1** signals the POC
did not cover.

### What already exists (integration points)
- `closed_loop.py` (F0) — `run_closed_loop(args, client)`, `run_yoked(args, stimulation, client)`,
  `run_both(args)`; per-gen `surprise`, `sigma`, `witness_signal`; `--poke-gen` scripted-poke hook;
  `write_run`, `OUTPUT_DIR`.
- `stage5_fliptest.py` — the verdict idiom to emulate: compute per-condition booleans → reduce to
  `"PASS"/"STOP"` → embed in a `kill_gate` block → `verify_run(path)` re-derives and checks against stored values.
- Epic §7 (F1 gate) + resolved Q2 (**scripted poke at gen 8**).

---

## 2. Acceptance criteria

Verbatim from epic §9 (F1). IDs added.

- **AC-F1.1** (verbatim): "Run closed-loop and yoked arms (F0) at W=4, ~15 generations, on Aer; show the
  surprise proxy falls under closed loop but NOT under yoked (the adaptation gate signal)."
- **AC-F1.2** (verbatim): "Log branching σ per generation and show a trend toward 1 (criticality signal), not
  toward 0."
- **AC-F1.3** (verbatim): "A single scripted poke (default gen per Q2) produces a surprise spike followed by
  relaxation over the following generations."
- **AC-F1.4** (verbatim): "Emit an explicit GO/no-go verdict: all three signals present → GO to hardware thesis;
  any absent → documented no-go with the toy-scale evidence."

Each AC maps to a manual check in §8.

**Coverage (file:line evidence):**
- **AC-F1.1** — `draft_gate.py:73` `signal_adaptation` (closed/yoked `surprise_drop` → `gap` → `pass = gap > adapt_min`); driven at W=4/15gens/Aer by `run_gate` `draft_gate.py:171`. Verified: seed 100 stdout shows `closed_drop`/`yoked_drop`/`gap`; adaptation fires (`pass=True`) at seed 13 (`gap=+0.259`).
- **AC-F1.2** — `draft_gate.py:87` `signal_criticality` (non-None σ early vs late window, `trends_to_one` + `> SIGMA_DEAD`). Verified: per-gen σ column trends to ~1; `pass=True` at seeds 1/13/42/101/202.
- **AC-F1.3** — `draft_gate.py:110` `signal_poke_recover` (baseline over 3 pre-poke gens, `spike`, relax within `RELAX_WIN`). Verified: poke@8 column; `pass=True` (positive spike + relax) at seeds 1/303.
- **AC-F1.4** — `draft_gate.py:130` `verdict_from` (AND-reduce) + banner `draft_gate.py:230`. Verified: NO-GO banner + named failing signals on seed 100; `verify_run` `draft_gate.py:253` reproduces exit 0.

---

## 3. Scope

### In scope
- New file `draft_gate.py`: a driver over F0's runners at W=4 / 15 gens / Aer, computing three boolean signals,
  a `GO/no-go` verdict, and `verify_run(path)`.
- The scripted poke at gen 8 (epic Q2).
- Signal definitions (§7): adaptation-gap, σ-trend, poke-spike-relax — deliberately *coarse* (this is a
  go/no-go, not the F2/F3 rigor).

### Out of scope (deferred)
- α power-law fit, entropy-plateau test, susceptibility peak, formal τ fit — **F2** (F1's poke-relax is a coarse
  "spike then lower", not a fitted time constant).
- Classical surrogate null-band certification — **F3** (F1 does not run the surrogate arm).
- Scaled width, hardware submission — **F5**. Interactive poke / persistence — **F4**.

---

## 4. Data model — `kill_gate` block (added to F0's run.json)

F1 runs F0's closed + yoked arms (each writes its own `generations[]` file per §4 of F0), then writes a
**gate summary** file `<name>_gate_sim_seed<seed>_<ts>_run.json` carrying `meta` (as F0) plus:

```jsonc
{
  "meta": { ... },                      // F0 meta, arm="gate"
  "signals": {
    "adaptation": {                     // AC-F1.1
      "closed_surprise_drop": 0.62,     // surprise[first_window_mean] - surprise[last_window_mean], closed
      "yoked_surprise_drop": 0.03,      // same, yoked
      "gap": 0.59,                      // closed_drop - yoked_drop
      "pass": true                      // gap > ADAPT_MIN
    },
    "criticality": {                    // AC-F1.2
      "sigma_final_window_mean": 0.94,  // mean σ over the last window
      "trends_to_one": true,            // |sigma_final - 1| < |sigma_early - 1| AND sigma_final not ->0
      "pass": true
    },
    "poke_recover": {                   // AC-F1.3
      "poke_gen": 8,
      "spike": 1.41,                    // surprise[poke_gen] - pre-poke baseline
      "relaxed": true,                  // surprise returns within RELAX_FRAC of baseline within RELAX_WIN gens
      "pass": true
    }
  },
  "kill_gate": {
    "verdict": "GO",                    // "GO" iff all three signals pass; else "NO-GO"
    "note": "GO -> proceed to F5 hardware; NO-GO -> documented no-go, revisit F0 knobs (Q2/Q3)."
  }
}
```

- The three `pass` booleans AND-reduce to the verdict — mirror `stage5_fliptest.verdict = "PASS" if flip_at else "STOP"`.
- `verify_run(path)` re-derives `signals.*.pass` and `kill_gate.verdict` from the referenced closed/yoked
  `generations[]` and asserts they match the stored values (reproducibility gate).

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **Three honesty gates are law** — F1 is precisely the toy-scale go/no-go on all three signals; an honest
  NO-GO with evidence is an acceptable outcome (epic §7, "honest no-go allowed").
- **Sim-first, W=4, ~15 gens** (epic §7 F1). No hardware in F1.
- **Scripted poke at gen 8** (resolved Q2) — inside the 15-gen window so spike + relaxation both fit.
- **Kill-gate discipline** — verdict block + `verify_run`, ported from `stage5_fliptest.py`.
- **Do not proceed to F5 unless GO** (epic §7 implementation order, step 2).

---

## 6. File plan (concrete paths)

Python: `from __future__ import annotations`, full type hints, flush-print idiom. One new file.

### `THESIS/CriticalQuantumLife/code/draft_gate.py` (new)

1. **Module docstring** — F1 is the go/no-go before hardware; the three signals; honest-NO-GO allowed.
2. **Imports** — `import os, sys, json, argparse, functools`; `sys.path.insert(0, <code dir>)`;
   `import closed_loop as cl`. Constants: `ADAPT_MIN` (min closed-minus-yoked drop, default 0.15),
   `RELAX_WIN` (gens, default 4), `RELAX_FRAC` (default 0.5), window sizes `EARLY_WIN`/`LATE_WIN` (default 3).
3. **`def surprise_drop(gens: list[dict]) -> float`** — mean surprise over first `EARLY_WIN` minus mean over
   last `LATE_WIN` (positive = it fell).
4. **`def signal_adaptation(closed: dict, yoked: dict) -> dict`** — compute closed/yoked drops, gap, `pass = gap > ADAPT_MIN`.
5. **`def signal_criticality(closed: dict) -> dict`** — σ early-window vs late-window; `trends_to_one` = late is
   closer to 1 than early AND late-window mean > `SIGMA_DEAD` (default 0.3, i.e. not collapsing to 0).
6. **`def signal_poke_recover(closed: dict, poke_gen: int) -> dict`** — pre-poke baseline (mean surprise over the
   3 gens before poke); `spike = surprise[poke_gen] - baseline`; `relaxed` = surprise returns within
   `RELAX_FRAC*spike` of baseline within `RELAX_WIN` gens after the poke.
7. **`def run_gate(args) -> dict`** — set `args.width=4`, `args.arm="both"`, `args.poke_gen=args.poke_gen or 8`;
   call `cl.run_closed_loop` + `cl.run_yoked` (shared stimulation); compute the three signals; AND-reduce to
   `verdict`; assemble the gate dict (§4); return it. Prints the per-gen closed/yoked surprise + σ table and a
   `KILL-GATE VERDICT: {verdict}` banner (honest-NO-GO banner when NO-GO).
8. **`def verify_run(path: str) -> int`** — load a gate JSON + its referenced closed/yoked runs, re-derive the
   signals + verdict, assert equality with stored; nonzero exit on mismatch (mirror `stage5_fliptest.verify_run`).
9. **`def write_gate(gate: dict, args) -> str`** — `<name>_gate_sim_seed<seed>_<ts>_run.json` into `cl.OUTPUT_DIR`.
10. **`def main() -> None`** — argparse `--generations`(15) `--seed`(100) `--name`("cql_f1") `--poke-gen`(8)
    `--verify <path>` (exits after verify) `--adapt-min`(0.15). Runs the gate, writes it, prints verdict + path.
11. **`if __name__ == "__main__": main()`**.

No other files.

---

## 7. Signal definitions (coarse by design — this is a gate, not F2/F3 rigor)

- **Adaptation (AC-F1.1).** `gap = drop(closed) - drop(yoked)`; pass if `gap > ADAPT_MIN`. A real closed loop
  learns to predict its own outcomes (surprise falls); the yoked control gets the same stimulation energy with no
  contingency, so its surprise should not fall. No gap → not learning → NO-GO.
- **Criticality (AC-F1.2).** σ (descendants per active individual) should trend toward 1: `late_window` closer to
  1 than `early_window`, and not collapsing toward 0 (dead). This is the *signal*, not the fitted α/susceptibility
  proof (F2). σ→0 (population dying out) is a NO-GO even if surprise fell.
- **Poke-recover (AC-F1.3).** At `poke_gen=8`, surprise spikes above its pre-poke baseline, then relaxes back
  within `RELAX_WIN` gens. Coarse relaxation check (returns within `RELAX_FRAC` of the spike); the fitted τ is F2.
- **Verdict (AC-F1.4).** `GO` iff all three `pass`; else `NO-GO` with the failing signal(s) named in `note`.
  An honest NO-GO ships with the toy-scale evidence (the three signal blocks) — that IS the deliverable when the
  signals aren't there, per epic §7.

---

## 8. Manual verification (no automated tests)

```bash
cd THESIS/CriticalQuantumLife/code
python draft_gate.py --generations 15 --seed 100 --name cql_f1        # runs closed + yoked + poke@8, prints verdict
python draft_gate.py --verify ../research_runs/cql_f1_gate_sim_seed100_sim_run.json   # reproducibility
```

- **AC-F1.1** — stdout shows closed surprise falling, yoked flat; `signals.adaptation.gap > 0.15`, `pass=true`.
- **AC-F1.2** — per-gen σ column trends toward 1 (not 0); `signals.criticality.pass=true`.
- **AC-F1.3** — surprise column jumps at gen 8 then descends over gens 9–12; `signals.poke_recover.spike>0`,
  `relaxed=true`.
- **AC-F1.4** — banner prints `KILL-GATE VERDICT: GO` (or `NO-GO` + which signal failed); `kill_gate.verdict`
  in JSON matches; `--verify` exits 0.
- **Honest-NO-GO path** — force it (`--adapt-min 5.0`) → verdict `NO-GO`, note names `adaptation`, evidence blocks present.

---

## 9. Out-of-context risks / notes

- Thresholds (`ADAPT_MIN`, `SIGMA_DEAD`, `RELAX_FRAC`) are the gate's judgment calls — keep them in module
  constants + CLI so a marginal run can be re-judged without editing logic. Document the chosen values in the run note.
- F1 depends entirely on F0's outcome/surprise definition (F0 Q1/Q2). If F0 defaults produce no closed–yoked gap,
  the honest fix is F0's knobs, not loosening F1's threshold — say so in the NO-GO note.
- The poke at gen 8 needs ≥4 gens after it inside a 15-gen run for the relaxation window — fine at defaults;
  guard `poke_gen + RELAX_WIN < generations`.

---

## 10. Ground rules honored

- Every AC (F1.1–F1.4) verbatim from epic §9, mapped to a §8 manual check.
- Concrete paths; one new file. Kill-gate + `verify_run` idiom ported from `stage5_fliptest.py`.
- No tests / no test sections. Strict typing; no raw SQL. Honest-NO-GO is a first-class outcome.

---

## 11. Open questions (RESOLVED 2026-08-31)

- **Q1 — `ADAPT_MIN` (adaptation-gap threshold).** **RESOLVED: 0.15 nats** of closed-minus-yoked surprise
  drop. Fixed default in module constant + `--adapt-min` CLI (re-judge a marginal run without editing logic).
- **Q2 — σ "trends to 1" test.** **RESOLVED: closer-and-not-dead.** Late-window mean strictly closer to 1 than
  early-window mean AND late-window mean > `SIGMA_DEAD` (0.3). Not the fixed-band variant.
- **Q3 — poke relaxation criterion.** **RESOLVED: coarse 50% / 4 gens.** Surprise returns within `RELAX_FRAC`
  (0.5) of the spike toward baseline within `RELAX_WIN` (4) gens. Fitted τ deferred to F2.

---

## 13. Post-implementation

**Built.** One new file `THESIS/CriticalQuantumLife/code/draft_gate.py` (~300 lines). Drives F0's
`run_closed_loop` + `run_yoked` at W=4/15gens/Aer with a shared stimulation trace and scripted poke@8,
computes the three coarse signals (`signal_adaptation` / `signal_criticality` / `signal_poke_recover`),
AND-reduces to a GO/NO-GO `kill_gate` verdict, writes the `<name>_gate_sim_seed<seed>_sim_run.json`
summary, and provides `verify_run(path)` (reloads the referenced closed/yoked runs, re-derives every
signal + verdict, asserts match). No new physics; no tests (project directive).

**Schema note (extension beyond §4).** The gate JSON also carries a top-level `runs` block (basenames of
the closed/yoked run files) and a `thresholds` block (records `adapt_min` etc. as used) so `verify_run` is
self-contained and faithful even when `--adapt-min` was overridden. `signal_criticality` adds
`sigma_early_window_mean` alongside the planned `sigma_final_window_mean`.

**Verification result — honest NO-GO at F0 defaults.** Seed 100 → verdict `NO-GO`; `verify_run` reproduces
(exit 0). An 8-seed sweep (1/7/13/42/101/202/303/777) shows every signal *can* fire in isolation
(criticality 6/8, poke_recover 2/8, adaptation only 1/8 at seed 13), but **no seed passes all three at
once**. The gate mechanism is correct; the weak signal is **adaptation** — the closed arm rarely beats the
yoked control's surprise drop at F0's current defaults. Per plan §9 + epic §7 the honest fix is **F0's
knobs (feedback contingency, DECAY, mut_scale — F0 Q2/Q3)**, not loosening F1's `ADAPT_MIN`. This is a
first-class NO-GO deliverable, not an F1 defect.

**Follow-ups for the developer.**
- Before F5 hardware spend, revisit F0's contingency/decay so the closed–yoked adaptation gap goes positive;
  re-run the gate for a GO. Do **not** proceed to F5 until GO (epic §7 step 2).
- `poke_recover` depends on the poke actually spiking surprise; at some seeds the founder scramble *lowers*
  surprise (negative spike) — another symptom to weigh when tuning F0.
- Kept only the seed-100 run artifacts (`cql_f1_{closed,yoked,gate}_sim_seed100_sim_run.json`); sweep files
  removed.
