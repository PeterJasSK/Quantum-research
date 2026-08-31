# Feature Plan — F4: Interactive poke + inter-batch state persistence (`session.py`)

**Status:** Complete (implemented + manually verified 2026-08-31)
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F4 (depends on F0; develops alongside F2/F3; gates F5's between-batch interactivity)
**Artifact:** `THESIS/CriticalQuantumLife/code/session.py` (new)
**Reuses:** `closed_loop.py` (F0) runners + run-JSON schema
**Author:** Claude (Opus) · **Date:** 2026-08-31

> No GitHub issue (F-ids). No tests (project directive): production code + manual verification only.

---

## 1. Context & goal

F4 is the **"life you can poke" spine**. It gives F0's closed loop two capabilities the 2018 model never had:
(1) a human-triggered **`poke()` API** that changes contingency / selection pressure or injects a stimulus
**mid-session** (not a scripted default-gen poke), and (2) **inter-batch state persistence** — the inherited
quantum+classical population state (genomes, running distribution, generation counter, RNG state) persists to
disk between runs so a session continues across batches as the **same** population.

This is the class-above-2018 interactivity: a poke between hardware batches (F5) or a live web POKE button (F6)
continues the *same* population, so the spike-then-relax you watch is a true session, not independent runs
stitched together. F4 defines the **one poke semantics** both F5 and F6 call, so their results are comparable.

### What already exists (integration points)
- F0 `closed_loop.py` — `run_closed_loop(args, client)`, per-gen observables, the `stimulation[]` trace, the
  scripted-poke hook (`--poke-gen`), `write_run`, `OUTPUT_DIR`, `meta` schema. F0 already carries a `poke_gen` +
  per-gen `poke` bool; F4 makes the poke *interactive* and *stateful*.
- `stage5_fliptest.py` `entropy_provenance` accumulation — the pattern for carrying provenance across a session.
- Epic §3 (poke is interactive, not scripted; persistence is real state, not a redraw) + §9 F4 ACs.

---

## 2. Acceptance criteria

Verbatim from epic §9 (F4). IDs added.

- **AC-F4.1** (verbatim): "`poke()` API: change which outcomes count as 'expected', alter selection pressure, or
  inject a stimulus — callable mid-session, not scripted; records a poke event in the run JSON."
- **AC-F4.2** (verbatim): "Persist inherited state (population genomes, running distribution, generation counter,
  RNG state) to disk between runs; a new run resumes the *same* population from it."
- **AC-F4.3** (verbatim): "A session driver: run a batch → allow a poke → run the next batch continuing from
  persisted state, demonstrating a spike-then-relax across the batch boundary."
- **AC-F4.4** (verbatim): "The API is the one both F5 (between hardware batches) and F6 (web POKE button) call."

Each AC maps to a manual check in §8.

**Coverage (file:line evidence, verified 2026-08-31):**

| AC | Covered by |
|----|------------|
| AC-F4.1 poke() API, records event | `session.py:113` `Session.poke` (validates `kind ∈ POKE_KINDS`, queues, appends to `poke_log` `session.py:119`); interactive effects applied in `closed_loop.py:283-303` (first-gen-of-batch); event lands in run-JSON `meta.poke_events` `closed_loop.py:248`. Verified: `poke_log` = `[(8,'flip_expected')]`, b1 `meta.poke_events` = `[{at_generation:8,kind:flip_expected}]`, per-gen `poke` bool True at gen 8. |
| AC-F4.2 persist + resume SAME population | `session.py:141` `save` / `session.py:158` `load`; carry-over `final_state` built `closed_loop.py:363` and seeded back `closed_loop.py:296-300`. Verified: state file has `generation`=16, `running_dist`(4 bins), `recent`/`active_hist`(len 16), NO `genome_thetas`/`rng_state`; `--resume` starts at gen 16 (not 0); `draw_thetas(seed,gen)` bit-reproducible. |
| AC-F4.3 session driver, spike-then-relax | `session.py:203` `main` (batch → `poke()` at boundary → batch from persisted state → `_print_boundary_trace`). Verified: continuous gen counter 0..15 across the boundary, surprise spike at poked gen 8. |
| AC-F4.4 one poke API for F5 + F6 | `session.py:62` `POKE_KINDS` (shared vocabulary) + `session.py:124` `run_batch` (the single call path); all three kinds record `poke_events`. Verified: flip_expected / inject_stimulus / alter_selection all run and log. |

---

## 3. Scope

### In scope
- New file `session.py`: a `Session` object wrapping F0's loop with (a) a `poke(kind, **params)` method callable
  between batches, (b) `save(path)` / `load(path)` of the full inherited state, (c) a `run_batch(n_gens)` that
  continues the persisted population, (d) a `session_id` threading batches into one run-JSON lineage.
- The poke **semantics** (the three kinds: flip-expected, alter-selection, inject-stimulus) — the canonical
  definition F5 and F6 both call.
- Session state format (reuses the run-JSON schema fields; §4).

### Out of scope (deferred)
- The hardware submission itself — **F5** (F4 provides the persistence/poke machinery F5 drives; F5 wires the
  circuits to real backends). The web UI / in-browser JS poke — **F6** (F6's JS mirrors F4's semantics; F4 is the
  Python reference). The metrics that read the poke trace (τ) — **F2**.

---

## 4. Data model — session state + poke events

**Session state file** `<session_id>_state.json` (in `research_runs/`) — the inherited state that makes a resume
the *same* population, not a redraw:

```jsonc
{
  "session_id": "sess_a1b2",
  "meta": { ... },                      // F0 meta (arm, width, backend, mut_scale, entropy_source)
  "state": {
    "generation": 12,                   // next-batch generation counter (thetas rebuild from seed+generation)
    "running_dist": {"1011": 0.4, ...}, // the population's running outcome distribution (classical memory)
    "mut_scale": 0.07,                  // current mutation pressure (feedback-adapted)
    "recent": [0.8, 1.1, ...],          // surprise history — is_surprising() baseline, MUST carry the boundary
    "active_hist": [true, false, ...]   // per-gen surprising bools — running_sigma() window, MUST carry the boundary
  },
  "poke_log": [                         // AC-F4.1  every poke, in order
    {"at_generation": 8, "kind": "flip_expected", "params": {}, "wall_clock": "..."}
  ]
}
```

**Poke event** also lands in each batch's F0 run-JSON: `meta.poke_events: [{at_generation, kind, params}]`, and the
per-gen `poke` bool flips true on the poked generation. (Extends F0's single `poke_gen` to a list — Q1.)

- **State-model correction (Q_STATE, resolved):** F0's `draw_thetas` is a pure function of `(seed, generation,
  mut_scale)` — there is NO genome carried gen-to-gen, and the PRNG path is stateless (QRNG is external and not
  reproducible). So the genealogy is reconstructed from `seed` + `generation`, NOT from a persisted `genome_thetas`
  or `rng_state`. Those fields are dropped. The real carry-over state that makes a resume the SAME population is
  `running_dist` (classical memory) + `mut_scale` (feedback-adapted pressure) + `generation` (counter) + `recent`
  (surprise baseline) + `active_hist` (sigma window).
- `recent` and `active_hist` MUST persist (Q_BASELINE, resolved): dropping them resets `is_surprising()`'s baseline
  and `running_sigma()` at the boundary, which would make the boundary spike partly a reset artifact rather than the
  poke's effect. Carry both.
- Field names are the F4 contract; F5 and F6 both read/write this shape.

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **The poke is INTERACTIVE, not scripted** (epic §3) — `poke()` is a method a human calls mid-session; the
  scripted `--poke-gen` stays only for F1's non-interactive gate. F4's poke has no default generation.
- **Persistence is real state, not a redraw** (epic §3) — a resumed session continues the SAME population:
  genome angle-lineage, running distribution, generation counter, RNG state all persist. A fresh redraw is a bug.
- **One poke semantics across web + hardware** (epic §3/§9) — F5 (between batches) and F6 (web button) call the
  SAME `poke()` definition so their spike-then-relax traces are comparable.
- **State format reuses the run-JSON schema fields** (epic §4) — no parallel schema; the session state is F0's
  `meta` + a `state`/`poke_log` extension.

---

## 6. File plan (concrete paths)

Python: `from __future__ import annotations`, full type hints, flush-print, numpy. One new file.

### `THESIS/CriticalQuantumLife/code/session.py` (new)

1. **Module docstring** — the poke API + persistence; the "same population across batches" contract.
2. **Imports** — `import os, sys, json, argparse, functools`; `import numpy as np`; `sys.path.insert(0, <code dir>)`;
   `import closed_loop as cl`. `POKE_KINDS = ("flip_expected", "alter_selection", "inject_stimulus")`.
3. **`def new_session_id() -> str`** — short deterministic id from seed + name (no wall-clock in the id so runs
   are reproducible; wall-clock only inside the poke log).
4. **`class Session:`**
   - `__init__(self, args) -> None` — hold `args`, an empty/seeded `state` (generation 0, empty `running_dist`,
     `mut_scale` = `args.mut_scale`, empty `recent`, empty `active_hist`), an empty `poke_log`, a `session_id`.
     No `genome_thetas`/`rng_state` — thetas rebuild from `seed`+`generation` (Q_STATE).
   - `def poke(self, kind: str, **params) -> None` (AC-F4.1) — validate `kind ∈ POKE_KINDS`; apply the semantic
     (§7): `flip_expected` inverts the expected/surprising split for the next batch; `alter_selection` changes the
     alive-threshold / selection pressure; `inject_stimulus` injects a scramble rotation on the next built
     generation. Append `{at_generation, kind, params, wall_clock}` to `poke_log`. Does NOT itself run circuits.
   - `def run_batch(self, n_gens: int) -> dict` (AC-F4.3) — continue `cl.run_closed_loop` from `self.state`
     (seed the loop with the persisted `running_dist`, `mut_scale`, `generation`, `recent`, `active_hist`; thetas
     rebuild from `seed`+`generation`),
     apply any pending poke on the first generation of the batch, run `n_gens`, update `self.state`, return the
     batch's F0 run-JSON (`meta.session_id`, `meta.poke_events`).
   - `def save(self, path: str | None = None) -> str` (AC-F4.2) — dump the state file (§4).
   - `@classmethod def load(cls, path: str, args=None) -> "Session"` (AC-F4.2) — reconstruct a Session from a
     state file; a subsequent `run_batch` resumes the SAME population.
5. **`def run_batch_from_loop(args, state) -> tuple[dict, dict]`** — the thin adapter that lets `cl.run_closed_loop`
   start from a supplied `state` instead of gen 0 (small F0 hook: `run_closed_loop(args, client, resume_state=None)`
   — Q2). Returns `(run_json, new_state)`.
6. **`def main() -> None`** — a demo/CLI session driver (AC-F4.3): argparse `--generations`(per batch, default 8)
   `--batches`(2) `--poke`("flip_expected@boundary") `--width`(4) `--seed`(100) `--name`("cql_f4") `--resume <state.json>`.
   Runs batch 1 → `poke()` at the boundary → runs batch 2 from persisted state → prints the surprise trace across the
   boundary showing spike-then-relax; saves state + both batch run-JSONs.
7. **`if __name__ == "__main__": main()`**.

No other files. (Needs one F0 hook: `run_closed_loop(..., resume_state=None)` — flag Q2.)

---

## 7. Poke semantics + persistence contract (what F4 must fix; F5/F6 depend on it)

- **`flip_expected`** — invert which outcomes count as "expected" vs "surprising" (change the contingency). A
  population that had learned to predict itself is suddenly wrong about everything → surprise spikes → it
  reorganizes to the new contingency over the next generations. This is the primary "poke".
- **`alter_selection`** — change selection pressure (raise/lower the alive-threshold, or the tighten/explore
  feedback magnitudes). Shifts the fitness landscape mid-session.
- **`inject_stimulus`** — inject a scramble rotation (the POC `ry(pi/2)` on a genome qubit) on the next built
  generation — the coherence-breaking "prod" the POC used; witness dips, then selection recovers it.
- **Persistence = same population (AC-F4.2).** The resumed batch must reconstruct the SAME genealogy. Because F0's
  `draw_thetas` is deterministic in `(seed, generation, mut_scale)`, the genealogy circuit rebuilds from `seed` +
  the persisted `generation` counter — no statevector, no `genome_thetas` snapshot, no RNG state to carry (Q_STATE).
  What MUST persist: `running_dist` (classical memory), `mut_scale` (feedback-adapted pressure), `generation`, and —
  critically — `recent` (surprise baseline) + `active_hist` (sigma window). A resume that resets `running_dist`,
  `mut_scale`, `recent`, or `active_hist` is a redraw, not a continuation — a bug per epic §3.
- **Spike-then-relax across the boundary (AC-F4.3)** — because the population state carried over, a poke at the
  batch boundary produces a surprise spike in the first generations of batch 2 that relaxes over the following
  generations — the same signature F1 shows within one run, now proven across a persisted boundary.

---

## 8. Manual verification (no automated tests)

```bash
cd THESIS/CriticalQuantumLife/code
python session.py --batches 2 --generations 8 --poke flip_expected@boundary --width 4 --seed 100 --name cql_f4
# then resume from the saved state and confirm continuation, not redraw:
python session.py --resume ../research_runs/sess_*_state.json --generations 8 --name cql_f4b
```

- **AC-F4.1** — `poke_log` in the state file records the poke `{at_generation, kind}`; the batch run-JSON
  `meta.poke_events` + the per-gen `poke` bool flip true at the boundary.
- **AC-F4.2** — the state file carries `state.running_dist`, `mut_scale`, `generation`, `recent`, `active_hist`; a
  `--resume` run starts from `generation` = the saved counter (not 0) and reproduces the SAME genome angles from
  `seed`+`generation` (diff the first resumed gen against a fresh continuation of the un-interrupted run — identical
  within shot noise). Confirm `running_dist`/`recent`/`active_hist` are the saved values, not empty.
- **AC-F4.3** — the printed surprise trace across the batch boundary shows a spike at the poked generation then a
  descent over the next gens (F2's τ can be fit on it).
- **AC-F4.4** — the poke kinds + params written by `session.py` match what F5's batch driver and F6's JS call
  (grep: `POKE_KINDS` is the shared vocabulary; F6's button labels map 1:1).
- **Determinism** — same seed + same poke schedule → same trace (RNG state persistence makes resume deterministic).

---

## 9. Out-of-context risks / notes

- **Statevector does not survive a batch boundary.** On real hardware the quantum population is re-prepared each
  batch; "persisting the quantum state" means the genealogy circuit is **rebuilt from `seed`+`generation`** (F0's
  `draw_thetas` is deterministic in those), NOT a raw statevector and NOT even a persisted `genome_thetas` snapshot.
  Call this out explicitly in the state-file docstring so F5/F7 don't overclaim a teleported statevector. (Q_STATE/Q2.)
- **`recent`/`active_hist` are load-bearing state.** They are not decoration: `recent` sets the `is_surprising()`
  baseline and `active_hist` is the `running_sigma()` window. Omitting them from the persisted state silently turns
  the boundary spike into a reset artifact. Both persist (Q_BASELINE, resolved).
- **Poke-event list vs F0's single `poke_gen`.** F4 generalizes F0's single scripted `poke_gen` to a `poke_events`
  list. Keep F0's field readable (a scripted single poke = a one-element list) so F1 still works. (Q1.)
- **Session id must be reproducible** — derive it from seed+name, not wall-clock, or resume/verify breaks. Wall-clock
  belongs only in the poke log's audit trail.
- **F0 hook** — `run_closed_loop` needs a `resume_state` param to start mid-lineage. Small, additive; flag before
  implementing so F0 and F4 land compatibly.

---

## 10. Ground rules honored

- Every AC (F4.1–F4.4) verbatim from epic §9, mapped to a §8 manual check.
- Concrete paths; one new file (plus one additive F0 `resume_state` hook, flagged Q2). Reuses the run-JSON schema
  fields; no parallel schema.
- No tests / no test sections. Strict typing; numpy; no raw SQL. Honest "angle-lineage not statevector" persistence.

---

## 11. Open questions — RESOLVED 2026-08-31

- **Q_STATE (new, from F0 read) — state model.** RESOLVED: **fix to real carry-over.** F0's `draw_thetas` is a pure
  function of `(seed, generation, mut_scale)` — no genome gen-to-gen, PRNG stateless, QRNG external. Drop
  `genome_thetas` and `rng_state`; persist `running_dist` + `mut_scale` + `generation` + `recent` + `active_hist`.
  Thetas rebuild from `seed`+`generation`. (§4, §7, §9.)
- **Q_BASELINE (new) — surprise/sigma state.** RESOLVED: **persist both** `recent` and `active_hist`. Resetting them
  at the boundary would make the spike partly a reset artifact, not the poke. (§4, §7, §9.)
- **Q1 — Poke-event representation.** RESOLVED: **accept.** Generalize F0's single `poke_gen` to a `meta.poke_events`
  list (scripted single poke = one element), keeping F1 working.
- **Q2 — "Inherited quantum state" persistence + F0 hook.** RESOLVED: **accept both.** Honest interpretation is
  rebuild-from-seed+generation (see Q_STATE, supersedes the earlier `genome_thetas` framing). Add
  `run_closed_loop(..., resume_state=None)` to F0 (additive).
- **Q3 — Boundary poke default in the demo.** RESOLVED: **`flip_expected`** at the batch boundary (clearest
  spike-then-relax).

---

## 12. Post-implementation notes (2026-08-31)

**Built.** `code/session.py` (new) — `Session` (poke/run_batch/save/load) + a CLI session driver. Two additive
F0 hooks in `code/closed_loop.py`: `run_closed_loop(..., resume_state=None)` and a `meta.poke_events` list.

**F0 changes are backward-compatible.** `run_closed_loop` gained a private `run["final_state"]` (stripped by
`write_run` before it hits disk) and the loop now indexes a GLOBAL generation `g = start_gen + i`. For a fresh run
(`start_gen=0`, no poke, no alter_selection) behaviour is identical to before — F1's scripted `--poke-gen` still
scrambles+flips on the same gen, and `meta.poke_gen` is retained. F0 smoke-run reproduced the prior table shape.

**Poke-kind → effect mapping (F5/F6 must mirror this).** F0's single `poke` bool was split into two orthogonal
effects so the three kinds are distinct:
- `flip_expected` → invert the contingency only (per-gen `poke` bool True). *The demo default.*
- `inject_stimulus` → POC `ry(π/2)` scramble on the founder only (per-gen `poke` bool True).
- `alter_selection` → scale the explore-pressure baseline by `params["factor"]` (default 2.0); it does NOT set the
  per-gen `poke` bool (no scramble/flip), but it IS recorded in `meta.poke_events`. F6's button for this kind must
  read `poke_events`, not the per-gen `poke` flag.

**State file carries `resume_args`** (beyond the plan §4 shape) — the F0 knobs (width/seed/shots/mut_scale/death/…)
so `--resume` needs no re-supply. `meta` + `state` + `poke_log` are exactly as §4; `resume_args` is additive.

**Follow-ups for F5/F6.**
- F5 (`hardware_batches.py`) drives `Session.run_batch` with a real backend; `run_counts` still raises
  `NotImplementedError` for non-None backends — F5 wires the sampler. QRNG resume is non-reproducible (external
  entropy); only the sim/PRNG path is bit-deterministic. Flag in F5 output.
- F6's JS POKE buttons map 1:1 to `POKE_KINDS`; the `alter_selection` caveat above (read `poke_events`) applies.
- τ (F2) fits on the surprise trace across the boundary — the `_print_boundary_trace` output is the shape it reads.
