# Feature Plan — F3: Quantum certification vs classical surrogate (`certify.py`)

**Status:** Complete (2026-08-31 — implemented + manually verified; all defaults confirmed)
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F3 (depends on F0; parallel with F2)
**Artifact:** `THESIS/CriticalQuantumLife/code/certify.py` (new)
**Reuses:** `stage4_qalife.xbasis_witness_from_counts` / `entanglement_depth`, `classical_surrogate_z`
**Mirrors:** `proof_of_concept/classical_life.py` (the measure-and-resend null band)
**Author:** Claude (Opus) · **Date:** 2026-08-31

> No GitHub issue (F-ids). No tests (project directive): production code + manual verification only.

---

## 1. Context & goal

F3 is the **quantum honesty gate**: it holds the `⟨X^⊗W⟩` genealogical entanglement witness above a **matched
classical measure-and-resend surrogate** null band throughout the run. This is the certificate that the aliveness
is quantum, not classical stochastic dynamics wearing a quantum costume. The POC already showed this at toy scale
(quantum witness `+0.87` on `ibm_kingston`, classical null `±0.047`, 29/30 gens above band); F3 productionizes it:
a surrogate arm running the **identical closed loop**, its null band computed, and the witness σ-margin reported
per generation with a pass/fail (pass = "above the band", allowing NISQ degradation — NOT "= 1").

F3 reuses the single-sourced witness math from `stage4_qalife.py` — it does **not** reimplement it. New code =
the classical surrogate arm running F0's closed loop, the null-band computation, the σ-margin report, and the
witness-vs-surrogate panel data for F6/F7.

### What already exists (integration points)
- `stage4_qalife.xbasis_witness_from_counts(counts, qubits) -> (joint, separable)` — the canonical witness;
  entanglement signal = `joint - separable`. `entanglement_depth(witness_by_gen, sep_by_gen, sigma, k=2.0)` —
  deepest gen clearing `k*sigma`. Null band = `sigma = sqrt(std**2 + 1/shots)`.
- `stage4_qalife.classical_surrogate_z(...)` — the classical (separable / measure-and-resend) baseline series.
- `proof_of_concept/classical_life.py` — `witness_classical(rng, shots)`: measure-and-resend gives X-parity → 0,
  null band `3/sqrt(shots)` (the "±0.047" the POC quotes at 4096 shots).
- F0 `closed_loop.py` — `run_closed_loop`; per-gen `witness_joint`, `witness_separable`, `witness_signal`,
  `witness_sigma`. F3 adds the `surrogate` arm and the `certification` summary.

---

## 2. Acceptance criteria

Verbatim from epic §9 (F3). IDs added.

- **AC-F3.1** ✅ (verbatim): "Compute `⟨X^⊗W⟩` per generation for the quantum population (reuse the `stage4`
  witness)." — `certify.py:109,120` reads F0's per-gen `witness_signal` (logged via
  `q4.xbasis_witness_from_counts`); no local witness math (grep: only reads, plus `cl.surrogate_readout`).
- **AC-F3.2** ✅ (verbatim): "Implement the matched classical measure-and-resend surrogate running the identical
  closed loop, and compute its null band (`|W| < k/√shots`)." — `closed_loop.py:139` `surrogate_readout` +
  `closed_loop.py:256` `run_closed_loop(surrogate=True)` (identical loop, readout swapped); band at
  `certify.py:80` `null_band` = `k/√shots` = **0.047** at 4096/k=3. Surrogate stayed within ±0.047 all 15 gens.
- **AC-F3.3** ✅ (verbatim): "Report the witness σ-margin above the surrogate null across the run; the gate passes
  iff the witness stays above the band (allowing for NISQ degradation — pass = 'above null', not '= 1')." —
  `certify.py:99` `certify` + `:184` `_print_report`: per-gen margin table, `certified = frac ≥ cert_frac`.
  Verified **CERTIFIED: yes** (14/15, 0.93≥0.8, one dip) at low mut_scale AND **CERTIFIED: NO** at mut_scale 0.6.
- **AC-F3.4** ✅ (verbatim): "Produce the witness-vs-surrogate panel data for F6/F7." — `certify.py:114` panel
  = 15 rows, fields `{gen, quantum_signal, surrogate_signal, null_band, poke}` (verified).

Each AC maps to a manual check in §8.

---

## 3. Scope

### In scope
- New file `certify.py`: the classical measure-and-resend **surrogate arm** running F0's identical closed loop,
  the null-band computation, the per-gen σ-margin report, the pass/fail certification, and the panel data.
- Reuse of `stage4_qalife` witness math (AC-F3.1) — imported, not reimplemented.
- Writes a `certification` summary block + a `panel` array (quantum vs surrogate witness per gen) for F6/F7.

### Out of scope (deferred)
- Criticality metrics (σ/α/τ) — **F2** (separate gate). Hardware submission — **F5** (F3's surrogate runs on
  sim; F5 runs the quantum arm on hardware and re-uses F3's null band). Web panel rendering — **F6** (reads F3's
  `panel`). Paper — **F7**.

---

## 4. Data model — `certification` block + `panel` (added to F0's run.json)

F3 writes a sidecar `<name>_certification.json`:

```jsonc
{
  "quantum_run": "cql_f5_closed_ibm_..._run.json",
  "surrogate_run": "cql_f3_surrogate_sim_..._run.json",
  "certification": {
    "null_band": 0.047,                 // AC-F3.2  k/sqrt(shots) (k=3 default) OR surrogate empirical band
    "k": 3.0,
    "shots": 4096,
    "gens_total": 15,
    "gens_above_band": 14,              // AC-F3.3  count of gens with quantum witness_signal > null_band
    "witness_margin_mean": 0.82,        // mean (quantum_signal - null_band) over the run
    "witness_margin_min": -0.02,        // worst gen (e.g. the poke gen dipping into the band)
    "certified": true                   // AC-F3.3  gens_above_band / gens_total >= CERT_FRAC
  },
  "panel": [                            // AC-F3.4  one row per generation for F6/F7
    {"gen": 0, "quantum_signal": 0.86, "surrogate_signal": 0.01, "null_band": 0.047, "poke": false}
    // ...
  ]
}
```

- `certified` = quantum witness clears the null band in ≥ `CERT_FRAC` of generations (default 0.8; allows the
  poke gen + NISQ dips). This is the "above the band, not = 1" pass rule (AC-F3.3).
- `panel` is the F6 ghost-panel / F7 witness-vs-surrogate figure source. Field names are the F3 contract.

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **Quantum gate is law** (epic honesty gate 3). Below the surrogate band → classical dynamics in a quantum
  costume → the aliveness claim fails. F3 is the certificate that keeps "quantum-alive" honest.
- **Pass = "above the band", not "= 1"** (epic §9 F3; POC caveat) — NISQ readout + 2q error pull the witness down;
  the surrogate defines what "0" looks like, and the quantum arm must beat it, not saturate at 1.
- **Reuse the single-sourced witness** (`stage4_qalife.xbasis_witness_from_counts`) — the epic forbids
  reimplementing it. Null band via the uniform `sigma = sqrt(std**2 + 1/shots)` / `k/sqrt(shots)` idiom.
- **Matched surrogate = identical closed loop** — the surrogate runs the SAME mutate/select/reproduce/feedback
  loop and the SAME readout as F0's quantum arm; the ONLY difference is the quantum resource (measure-and-resend
  collapses coherence). Mirror `classical_life.py`.
- **One schema** — F3 reads F0's `witness_*` fields, adds a sibling `certification`/`panel`, renames nothing.

---

## 6. File plan (concrete paths)

Python: `from __future__ import annotations`, full type hints, flush-print, numpy. One new file.

### `THESIS/CriticalQuantumLife/code/certify.py` (new)

1. **Module docstring** — the quantum honesty gate; measure-and-resend defines the null; pass = above band.
2. **Imports** — `import os, sys, json, argparse, functools`; `import numpy as np`; `sys.path.insert(0, <code dir>)`;
   `import closed_loop as cl`; `sys.path.insert(0, cl._AL); import stage4_qalife as q4`. Constants `CERT_FRAC`(0.8),
   `K_BAND`(3.0).
3. **`def surrogate_witness(rng, width, shots) -> tuple[float,float,float]`** — measure-and-resend witness
   (mirror `classical_life.witness_classical`): independent ±1 per genome qubit → X-parity ~0; return
   `(joint≈0, separable≈0, null_band = K_BAND/sqrt(shots))`. (Or call `q4.classical_surrogate_z` for a matched
   separable-state readout — Q1.)
4. **`def run_surrogate_loop(args) -> dict`** — run F0's **identical closed loop** but with the surrogate readout
   (measure-and-resend) substituted for the entangled genome: same `run_closed_loop` control flow, `meta.arm="surrogate"`,
   per-gen `witness_signal ≈ 0`. Implemented by passing a `surrogate=True` flag through `cl.run_closed_loop` (small
   F0 hook — Q2) OR by a thin re-driver here that reuses `cl`'s feedback/selection with the classical witness.
5. **`def null_band(shots: int, surrogate_gens: list[dict] | None) -> float`** (AC-F3.2) — `K_BAND/sqrt(shots)`,
   or the empirical `max |surrogate_signal|` if a surrogate run is supplied (whichever is the honest band — Q3).
6. **`def certify(quantum: dict, surrogate: dict | None, args) -> dict`** (AC-F3.1/3.3) — pull quantum
   `witness_signal` per gen (already logged by F0 via `q4.xbasis_witness_from_counts`), compute the band, count
   `gens_above_band`, `witness_margin_mean/min`, `certified = above/total >= CERT_FRAC`. Assemble `certification` + `panel`.
7. **`def write_certification(block: dict, args) -> str`** — sidecar `<name>_certification.json` into `cl.OUTPUT_DIR`.
8. **`def main() -> None`** — argparse `--quantum-run <path>` (F0/F5 closed run) `--surrogate-run <path>` (optional;
   else run the surrogate loop here) `--shots`(4096) `--k`(3.0) `--cert-frac`(0.8) `--width`(4) `--generations`(15)
   `--name`("cql_f3"). Prints the per-gen `gen quantum surrogate band margin` table + a `CERTIFIED: yes/no` banner;
   writes the block.
9. **`if __name__ == "__main__": main()`**.

No other files. (If step 4 needs an F0 hook, that is a one-line `surrogate` branch in `cl.run_closed_loop` — flag Q2.)

---

## 7. The certification logic (the physics F3 must fix)

- **Witness (AC-F3.1).** `⟨X^⊗W⟩` over the genotype qubits, X-basis (H before Z-readout), via
  `q4.xbasis_witness_from_counts(counts, geno_c_qubits) -> (joint, separable)`; signal = `joint - separable`.
  GHZ genealogy → joint→1, separable→0; separable/classical → both →0.
- **Surrogate (AC-F3.2).** The classical arm runs the identical loop but each readout collapses to a classical
  bit (measure-and-resend), so the X-basis parity averages to 0. Its null band is `k/sqrt(shots)` (k=3 → ±0.047
  at 4096 shots, matching the POC), optionally corroborated by the empirical max|signal| over a surrogate run.
- **σ-margin + pass (AC-F3.3).** Per gen, `margin = quantum_signal - null_band`. The gate passes iff the quantum
  witness stays above the band in ≥ `CERT_FRAC` of generations. A poke gen (and NISQ noise on F5) may dip into the
  band; the run still certifies if it clears the band the rest of the time. Pass ≠ "witness = 1".
- **Panel (AC-F3.4).** Per-gen `(quantum_signal, surrogate_signal, null_band, poke)` — the F6 ghosted-yoked panel
  overlay and the F7 witness-vs-surrogate figure read this directly.

---

## 8. Manual verification (no automated tests)

```bash
cd THESIS/CriticalQuantumLife/code
python closed_loop.py --arm closed --generations 15 --width 4 --poke-gen 8 --name cql_f3q   # quantum arm (sim)
python certify.py --quantum-run ../research_runs/cql_f3q_closed_*_run.json --name cql_f3     # surrogate + certify
```

- **AC-F3.1** — grep: witness comes from `q4.xbasis_witness_from_counts`; no local witness math. Panel
  `quantum_signal` matches the source run's `witness_signal`.
- **AC-F3.2** — `certification.null_band ≈ 0.047` at 4096 shots (k=3); surrogate `panel[*].surrogate_signal` all
  within ±band.
- **AC-F3.3** — banner `CERTIFIED: yes`; `gens_above_band/gens_total >= 0.8`; the poke gen shows a dip (margin<0)
  but the run still certifies. Force noise/small W to see an honest `CERTIFIED: no`.
- **AC-F3.4** — `panel` has one row per gen with the four fields; `python -c "import json;d=json.load(open('<path>'));print(len(d['panel']),sorted(d['panel'][0]))"`.

---

## 9. Out-of-context risks / notes

- **Classical-bit indices.** The `qubits` arg to `xbasis_witness_from_counts` indexes the measured classical
  register, not physical qubits — F0 already fixes the ordering; F3 must pass the SAME genotype classical-bit
  indices or the witness reads garbage.
- **Surrogate must be genuinely matched** — same loop, same shots, same readout; the ONLY difference is the
  quantum resource. If the surrogate accidentally differs in the loop (e.g. different selection), the null band is
  not a valid control. Reuse `cl`'s loop, swap only the readout (Q2).
- **On sim the quantum witness is ~0.87–1.0** (POC); the real test of "above band, not =1" is F5's hardware run,
  which reuses F3's exact null band and `certify()`. F3 on sim proves the machinery + the surrogate ≈0.
- **k choice.** POC uses k=3 (`3/sqrt(shots)`); F0's per-gen `witness_sigma` uses k=2 for entanglement-depth.
  Keep F3's certification band explicit (`--k`, default 3, the POC convention) and record it in JSON.

---

## 13. Post-implementation notes

- **Built:** `certify.py` (new) — surrogate arm driver, `null_band`, `certify`, panel, sidecar writer, CLI.
  One-line F0 hook in `closed_loop.py`: `surrogate_readout` (measure-and-resend, mirrors
  `classical_life.witness_classical`) + `surrogate=True` branch in `run_closed_loop` (swaps ONLY the readout;
  arm label conditional). Q1–Q4 all built at plan defaults.
- **Verified (sim, W=4, 15 gens):** surrogate ≈0 within ±0.047 every gen; null band = analytic 3/√4096 = 0.047,
  corroborated by empirical surrogate max|signal| = 0.038; panel 15 rows × 4 fields. Two banners exercised:
  `CERTIFIED: yes` (mut_scale 0.12 → GHZ intact, 14/15 above, poke/warmup dip) and `CERTIFIED: NO`
  (mut_scale 0.6 → explore-gens scramble the GHZ, 8/15) — the honest "force it to fail" case.
- **Design note:** the matched surrogate args are built FROM the quantum run's `meta` (`_surrogate_args_from`),
  so the loop is parametrically identical by construction. `delta`/`gamma` are not in `meta`; defaulted to
  `q4.AGING_DELTA`/`q4.DAMP_GAMMA` (F0 defaults). If a run overrode them, pass a precomputed `--surrogate-run`.
- **Follow-ups:** F5 re-uses `certify()` + this null band on the hardware witness (the real "above band, not =1"
  test; sim gives ~1.0). F6/F7 read the `panel` + `certification` block directly. `--quantum-run` accepts a glob.
- **No new deps; no tests (repo directive).**

## 10. Ground rules honored

- Every AC (F3.1–F3.4) verbatim from epic §9, mapped to a §8 manual check.
- Concrete paths; one new file (plus a possible one-line F0 `surrogate` hook, flagged Q2). Witness reused, not
  reimplemented. Reads the one schema, adds a sibling block.
- No tests / no test sections. Strict typing; numpy; no raw SQL.

---

## 11. Open questions (RESOLVED 2026-08-31 — all plan defaults)

- **Q1 — Surrogate readout.** ✅ **Measure-and-resend** independent ±1 per qubit (mirror
  `classical_life.witness_classical`) — strongest "cannot forge the witness" control.
- **Q2 — Where the surrogate loop lives.** ✅ **F0 hook**: add `surrogate: bool = False` branch to
  `cl.run_closed_loop` (swap only the readout) so the loop is provably identical.
- **Q3 — Null band.** ✅ **Analytic `k/sqrt(shots)`** with k=3 (POC's ±0.047), corroborated by empirical
  surrogate max|signal|.
- **Q4 — `CERT_FRAC`.** ✅ **0.8** of generations above band (allows poke dip + NISQ degradation).
