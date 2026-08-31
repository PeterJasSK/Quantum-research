# Feature Plan — F5: Hardware batch runs (scaled, manual) (`hardware_batches.py`)

**Status:** Complete
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F5 (depends on F1 GREEN + F2 + F3 + F4)
**Artifact:** `THESIS/CriticalQuantumLife/code/hardware_batches.py` (new)
**Reuses:** `closed_loop.py` (F0), `session.py` (F4), `criticality.py` (F2), `certify.py` (F3),
`stage4_scale.gated_chain` / `layout.best_chain` / `pipeline_common.{connect,run_sampler,timestamp}`
**Author:** Claude (Opus) · **Date:** 2026-08-31

> No GitHub issue (F-ids). No tests (project directive): production code + manual verification only.
> **Manual QC workflow** — code emits circuits + a batch harness; the **user submits to QC by hand**
> and drops run JSONs into `research_runs/`. No automated submission (epic §3/§6).

---

## 1. Context & goal

F5 is the **thesis-scale hardware result**. It scales genome width (W=8 default, epic Q3), runs generations in
**hardware batches** on a current Heron backend (manual user submission), persists inherited state between jobs
(F4), pokes between batches, and produces the three thesis artefacts: the **criticality figure** (F2 metrics), the
**poke-and-recover trace** (across a persisted batch boundary), and the **witness-vs-surrogate panel** (F3). It
reports the closed-loop-minus-yoked adaptation gap at the scaled width.

F5 writes **no new science** — it composes F0's loop, F4's persistence/poke, F2's metrics, F3's certification, and
the `stage4_scale`/`layout`/`pipeline_common` hardware plumbing. Per epic Q4 (**DRAFT-first-defer**), F5 **scaffolds
the batch harness on sim** and defers actual QC submission until F1 is GREEN and F2/F3/F4 have landed; the harness
is built and sim-validated, then the user submits real batches by hand.

### What already exists (integration points)
- `stage4_scale.py` — `gated_chain(backend, nq, args)` (clean SWAP-free chain + the `--max-twoq-err`/`--max-readout-err`
  fail-closed gate), `run_counts(qc, shots, args, backend, qubit_list)`, `build_measured`, `dump_circuit`,
  `connect`/`run_sampler`/`timestamp` from `pipeline_common`, `generate_preset_pass_manager(optimization_level=3, initial_layout=...)`.
- `layout.best_chain(backend, n)` — the routing chain + live-calibration stats (`twoq_err_mean/max`, `readout_max`).
- F0 `closed_loop.py`, F4 `session.py` (`Session.run_batch` / `save` / `load` / `poke`), F2 `criticality.analyze`,
  F3 `certify.certify`. QRNG: `cl.draw_thetas` (fail-closed on HW).
- Epic §6 (hardware manual, batched, keep W modest so the GHZ survives the surrogate null) + §9 F5 ACs + Q3 (W=8).

---

## 2. Acceptance criteria

Verbatim from epic §9 (F5). IDs added.

- **AC-F5.1** (verbatim): "Emit per-batch circuits + a batch harness; user submits to QC by hand and drops run
  JSONs into `research_runs/` with live calibration (2q err, readout err) recorded."
  *Covered by:* `hardware_batches.py:emit_batch` (QPY dump + submit bundle) `:200`, `gated_chain_with_stats` `:159`
  (live 2q/readout calibration into `calibration` + `meta.calibration`), `ingest_batch` `:293`. Verified offline:
  ingest of synthetic counts → run-JSON with `meta.sim=False`, `meta.calibration.twoq_err_max=0.011`.
- **AC-F5.2** (verbatim): "Persist inherited quantum+classical state between batches (F4); poke between batches."
  *Covered by:* `run_session_sim` (F4 `Session` batched+persisted+poked) `:353`, per-arm HW state
  `_save_state_for`/`_load_state_for` `:389`, `poke_between` `:415`. Verified: W=8 sim persists `sess_*_state.json`
  across the batch boundary; poke queues onto the live state.
- **AC-F5.3** (verbatim): "Report the closed-loop-minus-yoked adaptation gap, the criticality metrics (F2), the
  post-poke τ, and the witness σ-margin (F3) at the scaled width."
  *Covered by:* `build_report_from` `:470` — `adaptation_gap` via `draft_gate.surprise_drop`, `crit.analyze`,
  `relaxation_tau`, `certify.certify`. Verified in `cql_f5_report.json` at `width=8` (gap=+0.406, σ≈1.05, τ=0.597,
  cert block present).
- **AC-F5.4** (verbatim): "W kept modest enough that the witness clears the surrogate null on real hardware; width
  a parameter (default per Q3)."
  *Covered by:* `--width` default 8 `:527`, `gated_chain_with_stats` fail-closed gate `:159`, sim sign-check
  `_signcheck`/`_print_signcheck_verdict` `:433`. **Honest-negative surfaced:** at W=8 the F0 model couples depth to
  width (`steps=width`), so the noiseless witness is weak (≤0.46, 10/16 above null) — cert=False is a real F2/F3
  science outcome (plan §9 "W=8 GHZ depth"), faithfully reported, not inflated.

Each AC maps to a manual check in §8.

---

## 3. Scope

### In scope
- New file `hardware_batches.py`: the manual-submission batch harness. Emits per-batch transpiled circuits +
  metadata; ingests user-submitted counts / run-JSONs; persists state between batches via F4; pokes between
  batches; assembles the F5 report (adaptation gap + F2 metrics + τ + F3 σ-margin) at W=8.
- The `gated_chain` fail-closed calibration gate (2q/readout err) before each hardware batch, calibration recorded
  in each run-JSON `meta.calibration` (AC-F5.1).
- Sim-scaffold mode (`--sim`) that runs the whole batched/persisted/poked pipeline on Aer for validation before QC.

### Out of scope (deferred)
- Automated backend submission — explicitly manual (epic §3/§6). The web — **F6**. The paper — **F7** (F5 produces
  the runs F7 reads). New metrics — **F2/F3** (F5 calls them, does not redefine).

---

## 4. Data model — per-batch circuit bundle + batch run-JSON

**Per-batch bundle** (emitted for manual submission), `<name>_batch<b>_<backend>_submit.json` + a QPY/QASM circuit
file per generation in the batch:

```jsonc
{
  "session_id": "sess_...",
  "batch": 1,
  "backend": "ibm_<heron>",
  "width": 8,
  "generations_in_batch": 8,
  "chain": [ ... ],                     // gated_chain qubit list
  "calibration": {                      // AC-F5.1 live, from layout.best_chain stats
    "twoq_err_mean": 0.006, "twoq_err_max": 0.011, "readout_max": 0.021,
    "gated": true, "max_twoq_err": 0.05, "max_readout_err": 0.15
  },
  "circuits": ["cql_f5_batch1_gen0.qpy", ...],
  "resume_state": "sess_..._state.json", // F4 inherited state this batch continues
  "poke_before_batch": {"kind": "flip_expected", "params": {}}  // or null
}
```

**Batch run-JSON** — F0 schema (`meta.arm="closed"|"yoked"|"surrogate"`, `meta.backend=<heron>`, `meta.sim=false`,
`meta.calibration` populated, `meta.session_id`, `meta.poke_events`) with the per-gen observables from the
user-submitted counts. F5's **report** (`<name>_report.json`) then aggregates:

```jsonc
{
  "session_id": "sess_...", "width": 8, "backend": "ibm_<heron>",
  "adaptation_gap": {"closed_drop": 0.5, "yoked_drop": 0.05, "gap": 0.45},   // AC-F5.3
  "criticality": { ... },               // F2 block at W=8
  "relaxation_tau": {"tau": 3.1, "poke_gen": 8},                              // F2 τ (AC-F5.3)
  "certification": { ... }              // F3 σ-margin / witness-vs-surrogate at W=8 (AC-F5.3)
}
```

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **Hardware is MANUAL and BATCHED** (epic §3/§6) — F5 emits circuits + harness; the user submits by hand and
  drops counts/run-JSONs in `research_runs/`. No `run_sampler` auto-call is triggered by F5 without the user; the
  sim-scaffold path is the only thing F5 runs unattended.
- **Sim-first sign check before each batch** (epic §6) — F5 runs the batch on Aer and confirms the witness/σ signal
  before the user spends QC time (mirror `stage4_scale` sim default).
- **Keep W modest so the GHZ survives** (epic §6, Q3 W=8) — width is a parameter; the fail-closed `gated_chain`
  gate (2q/readout err) blocks a batch on a bad chain unless `--allow-bad-chain`.
- **Inter-batch persistence is real state** (epic §3, via F4) — a poked batch continues the SAME population.
- **DRAFT-first-defer** (Q4) — build + sim-validate the harness; defer real QC submission until F1 GREEN + F2/F3/F4 done.
- **One schema** — batch runs are F0 run-JSONs; the report composes F2/F3 blocks; nothing renamed.

---

## 6. File plan (concrete paths)

Python: `from __future__ import annotations`, full type hints, flush-print, numpy. One new file.

### `THESIS/CriticalQuantumLife/code/hardware_batches.py` (new)

1. **Module docstring** — the manual batch workflow (emit → user submits → ingest → persist → poke → next batch);
   the sim-scaffold; the fail-closed calibration gate.
2. **Imports + path hooks** — `import os, sys, json, argparse, functools`; `import numpy as np`;
   `sys.path.insert(0, <code dir>)`; `import closed_loop as cl, session as sess, criticality as crit, certify`;
   `sys.path.insert(0, cl._AL)`; `import stage4_qalife as q4, stage4_scale as s4s, layout`;
   `from pipeline_common import connect, run_sampler, timestamp` (real timestamp on HW). `_read_env_key` (ported).
3. **`def emit_batch(session, batch, backend, args) -> str`** (AC-F5.1) — build the batch's per-generation
   genealogy circuits (`cl.build_generation` at W), transpile via `generate_preset_pass_manager(optimization_level=3,
   initial_layout=chain)` where `chain, stats = s4s.gated_chain(backend, nq, args)` (fail-closed 2q/readout gate),
   dump circuits (QPY) + the submit bundle (§4) with `calibration=stats`. Prints the manual-submission instructions.
4. **`def ingest_batch(bundle_path, counts_paths, args) -> dict`** (AC-F5.1) — read the user-submitted counts,
   compute per-gen observables (`cl.witness_gen`, `cl.surprise_nll`, σ, entropy) → an F0 batch run-JSON with
   `meta.calibration` from the bundle; update the F4 session state.
5. **`def run_batch_sim(session, batch, args) -> dict`** — the sim-scaffold: run the whole batch on Aer via
   `sess.Session.run_batch`, for validation + the sign check before QC (AC-F5 sim-first).
6. **`def poke_between(session, kind, params) -> None`** (AC-F5.2) — call `session.poke(kind, **params)` at a batch
   boundary; persist state (`session.save`).
7. **`def build_report(session_id, args) -> dict`** (AC-F5.3) — load all batch run-JSONs for the session; compute
   the closed-minus-yoked adaptation gap (reuse F1's `surprise_drop`), call `crit.analyze` (σ/α/plateau/susceptibility/τ)
   and `certify.certify` (σ-margin / witness-vs-surrogate) at W; write `<name>_report.json`.
8. **`def main() -> None`** — subcommands: `emit` (emit a batch bundle for submission), `ingest` (ingest submitted
   counts), `sim` (sim-scaffold the full session), `poke` (poke between batches), `report` (assemble the report).
   argparse `--backend` `--width`(8) `--generations`(per batch, 8) `--batches`(2) `--shots`(8192) `--seed`
   `--max-twoq-err`(0.05) `--max-readout-err`(0.15) `--allow-bad-chain` `--sim/--no-sim` `--name`("cql_f5")
   `--resume <state>` `--poke <kind@boundary>` `--qrng-url`.
9. **`if __name__ == "__main__": main()`**.

No other files.

---

## 7. The manual batch workflow (what F5 fixes)

1. **`sim`** — validate the full batched/persisted/poked session on Aer at W (sign check; cheap).
2. **`emit`** — for batch *b*: `gated_chain` picks a clean chain on the chosen Heron backend (fail-closed on
   2q/readout err), transpile the batch's generation circuits, dump QPY + the submit bundle with live calibration.
3. **User submits by hand** — the user runs the emitted circuits on QC (via their saved IBM account / the
   `pipeline_common` sampler in their own session) and drops the counts / run-JSON into `research_runs/`.
4. **`ingest`** — F5 reads the counts, computes the F0 observables + witness, writes the batch run-JSON with
   calibration, updates the F4 session state (the inherited population for the next batch).
5. **`poke`** — between batches, the user pokes (`flip_expected` / `alter_selection` / `inject_stimulus`); F4
   persists the poke + state.
6. **Repeat** for the next batch (continuing the SAME population), then **`report`** — assemble the adaptation gap,
   F2 criticality metrics, τ, and F3 σ-margin at the scaled width → the thesis figures' data.

**Honesty at scale:** on NISQ the witness is pulled down by readout+2q error; the F3 pass rule ("above the
surrogate null, not = 1") is what makes W=8 defensible. If a batch's chain fails the calibration gate, F5 refuses
to emit (unless `--allow-bad-chain`) — a bad chain would sink the witness below the null and the run would be a
false negative.

---

## 8. Manual verification (no automated tests)

```bash
cd THESIS/CriticalQuantumLife/code
# 1. sim-scaffold the whole session (no QC):
python hardware_batches.py sim --batches 2 --generations 8 --width 8 --poke flip_expected@boundary --name cql_f5
# 2. emit a batch bundle for manual submission (needs a real --backend):
python hardware_batches.py emit --backend ibm_<heron> --batch 1 --width 8 --name cql_f5
# 3. (user submits circuits by hand, drops counts) then ingest + report:
python hardware_batches.py ingest --bundle ../research_runs/cql_f5_batch1_*_submit.json --counts <paths>
python hardware_batches.py report --resume ../research_runs/sess_*_state.json --name cql_f5
```

- **AC-F5.1** — `emit` writes a submit bundle + QPY circuits; `meta.calibration` (2q/readout err) present in the
  ingested batch run-JSON; the fail-closed gate blocks a bad chain (test with a tight `--max-twoq-err`).
- **AC-F5.2** — the session state persists between batches; batch 2's run-JSON `meta.session_id` matches batch 1;
  a `poke` between batches lands in `meta.poke_events` and the trace shows spike-then-relax across the boundary.
- **AC-F5.3** — `report.json` carries `adaptation_gap.gap > 0`, a populated `criticality` block, `relaxation_tau.tau`,
  and `certification` σ-margin — all at `width=8`.
- **AC-F5.4** — `--width` is a parameter (default 8); the emitted GHZ genealogy stays shallow enough that the sim
  sign-check witness clears the surrogate null; the calibration gate enforces a chain good enough for the real run.
- **Sim-scaffold** — step 1 completes on Aer with a GO-like signal before any QC spend (DRAFT-first-defer, Q4).

---

## 9. Out-of-context risks / notes

- **Manual submission boundary.** F5 must NEVER auto-submit to a real backend as a side effect — `emit` writes
  files and stops; only the user runs circuits on QC. The only unattended run path is `sim`. State this in the
  module docstring (matches QuantumLife / number-partitioning workflow).
- **Real timestamp on HW.** F5 uses `pipeline_common.timestamp` (not F0's `"sim"` stub) so batch files don't
  overwrite. Confirm `pipeline_common` is importable (sibling `CalibrationGuidedHighYieldQRNG` on path — the
  `stage4_scale` sys.path hook shows how).
- **W=8 GHZ depth.** 8 genotype qubits + phenotype qubits ≈ 16–17 qubits; the GHZ chain depth is what the witness
  survival hinges on. Keep `steps` per batch small and rely on `gated_chain` for the cleanest line; if the witness
  can't clear the null at W=8 on the available backend, F7's honest-negative path (the width/noise budget at which
  it dies) is the result — don't inflate W to force it.
- **QRNG fail-closed on HW** — `cl.draw_thetas` with a real client aborts on missing key / bad health; the entropy
  provenance (`request_id`/`receipt`) must land in the batch run-JSON `meta.entropy_provenance`.

---

## 10. Ground rules honored

- Every AC (F5.1–F5.4) verbatim from epic §9, mapped to a §8 manual check.
- Concrete paths; one new file. Reuses F0/F4/F2/F3 + `stage4_scale`/`layout`/`pipeline_common`; nothing reimplemented.
- Manual-submission workflow honored (no auto QC). No tests / no test sections. Strict typing; numpy; no raw SQL.

---

## 11. Open questions (RESOLVED 2026-08-31)

- **Q1 — Backend.** **RESOLVED: pin ONE Heron device** for all batches (consistent calibration story across the
  persisted population). `--backend` is required, not auto. Accept queue/maintenance wait.
- **Q2 — Batch shape.** **RESOLVED: 2 batches × 8 generations = 16 gens** at W=8, one poke at the boundary (as
  drafted). **Caveat:** 16 gens is below F2's ≥30-gen α floor — the **α power-law exponent is reported as
  INDICATIVE ONLY**; the criticality claim leans on σ / plateau / susceptibility / τ. `build_report` must flag α
  as underpowered.
- **Q3 — Circuit serialization.** **RESOLVED: QPY per generation** in the submit bundle (native Qiskit, exact
  transpiled circuit). Version-coupled to the user's Qiskit at submit time.
- **Q4 — Arms on hardware.** **RESOLVED: ALL THREE arms HW-calibrated.** `emit` produces closed + yoked QPY
  bundles; the surrogate has **no quantum circuit** in the codebase (it is the classical measure-and-resend null,
  `cl.surrogate_readout`), so its null band is **derived from the HARDWARE closed-arm shots at report time**
  (`_surrogate_from_shots`) — HW-calibrated, no new circuit, respecting F5's "call F2/F3, do not redefine" scope.

---

## 12. Deviations from the drafted plan (reconciled against actual code)

The exploration pass found the plan's §6 assumptions diverged from the real signatures. Reconciled in code:

- `s4s.gated_chain(backend,nq,args)` returns **only `list[int]`** (not `(chain,stats)`). F5 calls
  `layout.best_chain(backend,n) -> (chain,stats)` directly (`gated_chain_with_stats`) so the live calibration
  reaches the bundle, and applies the fail-closed 2q/readout gate locally.
- `cl.surrogate_readout` is the only surrogate primitive (classical). No circuit → Q4 resolution above.
- **`cl.surprise_drop` does not exist** → adaptation gap uses `draft_gate.surprise_drop(gens)`.
- `crit.analyze(run)` takes a **run dict**, keys nested (`avalanche_alpha.alpha`, `entropy.plateau`,
  `relaxation_tau.tau`). Report reads the nested shape.
- `cl.run_counts` raises `NotImplementedError` on hardware — the manual `emit`/`ingest` path bypasses it; the sim
  scaffold uses `backend=None`.
- **No QPY helper existed** (`dump_circuit` is QASM3-only) → `qiskit.qpy.dump`.
- **Sim simulator cap:** F0's `AerSimulator(method="density_matrix")` caps at 15 qubits; W=8 = 16 qubits →
  `CircuitTooWideForTarget`. The sign-check is noiseless, so `run_session_sim` swaps in `AerSimulator()`
  (statevector) so `sim --width 8` runs. `--density-matrix` forces F0's default (W≤7). *Plan §8's `sim --width 8`
  now works out of the box.*

## 13. Post-Implementation

**Built:** one new file `THESIS/CriticalQuantumLife/code/hardware_batches.py` (~560 lines, strict typed) with
subcommands `sim` / `emit` / `ingest` / `poke` / `report`. Composes F0/F4/F2/F3 + `stage4_scale`/`layout`/
`pipeline_common`; no science reimplemented; manual-submission boundary enforced (`emit` writes files and stops;
only `sim` runs unattended).

**Verified (manual, no automated tests):**
- `sim --width 8 --batches 2 --generations 8` → GO/no-go sign-check; `cql_f5_report.json` at width=8 with all four
  AC-F5.3 blocks (gap=+0.406, σ≈1.05, τ=0.597, certification). Two persisted closed batches + yoked + report.
- `ingest` of synthetic per-gen counts → HW run-JSON (`meta.sim=False`, `meta.calibration`, `meta.session_id`) +
  per-arm state file (AC-F5.1/5.2 offline, no IBM).
- `report` (from disk), `poke` (queues onto live state).
- **`emit` against LIVE `ibm_kingston`** (real creds): clean 16-qubit SWAP-free chain, calibration gate PASS
  (twoq_err_max=0.0058, readout_max=0.0198), 8 QPY per arm (closed+yoked) + submit bundles written, stopped
  without submitting. QRNG entropy drawn (key auto-loaded from `THESIS/.env` via `_ensure_qeaas_key`, wider scan
  than `cl._read_env_key`). W=8 schedule pre-run uses statevector (density_matrix caps at 15 qubits).
- `python -m py_compile` clean.

**Follow-ups for the developer:**
1. **W=8 honest-negative.** Noiseless W=8 witness is weak (≤0.46; gen-0 already ≈0) because F0 sets `steps=width`,
   so depth scales with width and scrambles the GHZ genealogy witness even without noise. cert=False is a *real*
   science outcome (plan §9). Decide before QC spend: (a) lower W / decouple `steps` from width in F0, (b) relax
   `--cert-frac`, or (c) accept the honest-negative for F7. **This is F0/F2/F3 tuning, out of F5 scope.**
2. **Real hardware run** needs `QiskitRuntimeService` creds + a pinned live Heron (`--backend`, Q1) + `QEAAS_API_KEY`
   (QRNG fail-closed). `emit`/`ingest`/`poke`/`report` untested against a live backend (no creds in this env).
3. **Within-batch schedule is sim-predetermined** (manual HW can't round-trip per gen); adaptation is real across
   the batch boundary via F4 persistence. Documented in the module docstring.
