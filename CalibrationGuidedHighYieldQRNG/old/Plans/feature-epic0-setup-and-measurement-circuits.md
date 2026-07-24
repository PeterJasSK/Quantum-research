# Feature Plan — EPIC 0: Thesis setup & measurement circuits

**Status:** Complete (2026-07-14)
**Owning epic:** `CalibrationGuidedHighYieldQRNG/Plans/CALIBRATION_QRNG_BUILD_PLAN.md` → EPIC 0 `[MUST]`
**Source study:** `CalibrationGuidedHighYieldQRNG/Plans/1-calibration-guided-high-yield-qrng.md`
**Slug:** `setup-and-measurement-circuits`

> No automated tests (project directive). Production code + manual verification only.

---

## §1 Context

EPIC 0 is everything needed **before** running on hardware: the thesis folder scaffold and
README, the reused submission pipeline forked from `ErrorDetectionVSRawBits/`, one timestamped
calibration snapshot (including reset error), a mid-circuit measure-reset probe, and **both
measurement circuits built and runnable**. The epic ends when the circuits produce `bits:` +
`_raw.json` files; the developer then runs the jobs manually and collects the outputs. EPIC 1
(separate plan) scores those files.

Two existing files are the reuse base (decision #2, do not rebuild):

- `ErrorDetectionVSRawBits/qrng_bell_pairs.py` — the pipeline scaffold: `connect()` (live
  `QiskitRuntimeService`, `least_busy` Heron r2 pick), `backend.properties()` calibration reads,
  transpile via `generate_preset_pass_manager`, `SamplerV2` chunked run loop, `qpu_seconds()`
  accounting, `_safe()` metadata capture, and the `_raw.json` + `bits:...` `_processed.txt`
  output format.
- `ErrorDetectionVSRawBits/qrng_noise_hadamard.py` — the all-Hadamard-on-every-healthy-qubit
  circuit. **This is the closest analogue to Stage A** (1 bit/qubit/shot). Stage A extends it to
  the whole chip (no quality filter) and emits **per-qubit** streams.

This is a research study in Python, not the Symfony/GitHub-issue workflow the `/plan-feature`
template assumes and not the FastAPI+Next QRNG-EaaS project. There is no GitHub issue: the "ticket"
is EPIC 0, and ACs below are lifted verbatim from the epic's stories and Done-when clause. There is
no `_plan-template.md`; this plan mirrors the QRNG-EaaS feature-plan section layout.

---

## §2 Acceptance criteria (verbatim from EPIC 0)

Copied from the epic's stories (S0.1–S0.5) and Done-when. Each gets an ID.

**S0.1 — Thesis scaffold & README**
- **AC-1** Create the study folder layout (code, `qrng_output/` for bit files, `results/` for
  scores and PDFs, `paper/` for the write-up). ✅ Covered by `code/`, `qrng_output/.gitkeep`,
  `results/.gitkeep`, `paper/.gitkeep`.
- **AC-2** Write `README.md` explaining the study: the research question (does one calibration
  read predict qubit quality *and* usable harvest depth?), the hypothesis, the two stages, the
  baseline, the metrics, and how to run each step. State the honest framing (decision box). ✅
  Covered by `README.md:1-73`.

**S0.2 — Device pick & pipeline reuse**
- **AC-3** Fork `qrng_bell_pairs.py`'s scaffold (connect → transpile → `SamplerV2` loop →
  `quantum_seconds` accounting → `bits:` + `_raw.json` output). Do **not** rewrite it. ✅ Covered
  by `code/pipeline_common.py:29-107` (`connect`, `qpu_seconds`, `run_sampler`, `write_raw_json`,
  `write_processed_txt`); `ErrorDetectionVSRawBits/qrng_bell_pairs.py` untouched.

**S0.3 — Calibration snapshot**
- **AC-4** Pull the live per-qubit snapshot: `T1`, `T2`, `readout_error`, `sx` gate error, and
  **reset error**. Save as `calib_<backend>_<ts>.json` — every later run anchors to this. ✅
  Covered by `code/calibration_snapshot.py:34-73,106-124`.
- **AC-5** Tiny **measure-reset probe** job to confirm mid-circuit reset works on this device
  before committing the Stage B sweep. ✅ Covered by `code/calibration_snapshot.py:75-103`.

**S0.4 — Stage A circuit — calibration-aware selection (also the baseline)**
- **AC-6** Single-qubit Hadamard RNG applied to **every** qubit in parallel (one batch = whole
  chip). This is also the **naive baseline** (1 bit/qubit/shot, no selection). ✅ Covered by
  `code/stage_a_selection.py:60-89` (`select_qubits` `all` mode, `build_circuit`).
- **AC-7** Output writes **per-qubit** `bits:` streams + `_raw.json`, with the calibration
  snapshot attached. Print the shots needed for a meaningful per-qubit bitstream. ✅ Covered by
  `code/stage_a_selection.py:113-115,140-149` (D3: aggregate stream + `qubits_used` order for
  EPIC 1 per-qubit reconstruction, per resolved Q2/Q3).

**S0.5 — Stage B circuit — mid-circuit measure-reset yield**
- **AC-8** Loop circuit: prepare superposition → measure → reset → re-prepare → measure, repeated
  `k` times per qubit per shot, for `k = 1, 2, 4, 8, …` (depth sweep). ✅ Covered by
  `code/stage_b_yield.py:57-70` (`build_circuit`), depth sweep loop at
  `code/stage_b_yield.py:110-135`.
- **AC-9** Parametrised to run on a chosen subset of qubits (the top-ranked qubits from Stage A,
  chosen after you evaluate Stage A). Output writes interleaved per-qubit, per-depth `bits:`
  streams. ✅ Covered by `code/stage_b_yield.py:44-55,79-96` (`--qubits` CLI override / default
  3-lowest-readout-error subset) and rep-major slot layout recorded per depth at
  `code/stage_b_yield.py:127`.

**Done when (AC-10):** README explains the study; the device is chosen and its calibration snapshot
saved; the measure-reset probe passes; and both circuits (Stage A whole-chip, Stage B depth sweep)
run and produce `bits:` + `_raw.json` files. ✅ All scripts syntax- and import-verified
(`py_compile`, live import against installed qiskit/qiskit-ibm-runtime). Actual hardware
execution requires IBM Quantum credentials/network not available in this environment — run
manually per §6, per decision #4 (manual runs).

---

## §3 Scope

### In scope
- Folder scaffold + README under `CalibrationGuidedHighYieldQRNG/`.
- Shared pipeline helper forked from the scaffold (connect / accounting / metadata / output).
- Calibration snapshot script (incl. reset error) + measure-reset probe.
- Stage A whole-chip Hadamard circuit emitting per-qubit streams.
- Stage B mid-circuit measure-reset depth-sweep circuit, parametrised on a qubit subset.

### Out of scope (deferred to EPIC 1 / write-up)
- Any scoring / battery import (`qrng_compare.py`), correlation, predictor fit, usable-depth
  analysis, headline computation, or PDF generation — all EPIC 1.
- Choosing the actual top-5 Stage B qubits (produced by EPIC 1's Stage A evaluation, fed back in).
- Running the jobs and collecting bit files — manual (decision #4).
- The thesis/paper prose — write-up phase.
- Cross-device / temporal-drift repeats — Stretch `[COULD]`.

---

## §4 Decisions (this ticket)

Adopted from the epic's locked decisions without restating rationale (Heron r2 / Open plan;
reuse not rebuild; manual runs; timestamped-alongside-calibration outputs; naive baseline =
single-qubit Hadamard). New decisions this ticket needs:

- **D1 — Reuse by forking a shared helper, not by editing the originals.** `ErrorDetectionVSRawBits/`
  files stay untouched. A new `code/pipeline_common.py` holds the identical scaffold pieces
  (`connect`, `qpu_seconds`, `_safe`, chunked `run_sampler` loop, `write_outputs`), copied from
  `qrng_bell_pairs.py`. Stage scripts import from it. This satisfies "fork the scaffold, do not
  rewrite" while avoiding triplicated code.
- **D2 — Stage A qubit set is a selectable variation (manual runs).** A `--select` mode chooses the
  qubit set: `all` (every non-faulty qubit, full quality range — default and the naive baseline),
  `good` (the `qubit_is_good()` thresholds from `qrng_noise_hadamard.py`), or `list:q,q,…` (explicit
  subset). Only `props.faulty_qubits()` are always excluded (cannot run). The developer runs the
  variations they want by hand; the chosen mode is recorded in `_raw.json`.
- **D3 — Output format is unchanged from the scaffold:** `_raw.json` (full IBM result including
  `raw_measurements` one string per shot + the `qubits_used` order) plus `_processed.txt` holding
  the single aggregate `bits:…` stream. **No separate per-qubit file** — EPIC 1 reconstructs
  per-qubit (and, for Stage B, per-qubit-per-depth) streams from `raw_measurements` using the
  `qubits_used` / classical-register layout recorded in `_raw.json`. Stage B records its
  `(qubit, depth, creg-slot)` layout in `_raw.json` so the reconstruction is unambiguous.
- **D4 — Calibration snapshot is embedded in every run's `_raw.json`** and also written standalone
  as `calib_<backend>_<ts>.json`. Reset error is read via `props.gate_error("reset", q)` with a
  fallback scan of `props.to_dict()`; if the device exposes no reset error the field is recorded
  as `null` and flagged (see §11 Q1).
- **D5 — Stage B depth sweep default `k ∈ {1, 2, 4, 8}`**, qubit subset supplied via CLI/config
  (defaults to a small probe subset so the circuit is runnable in EPIC 0; the real top-5 subset is
  passed in after EPIC 1's Stage A evaluation).
- **D7 — Maximize bits/shot with Hadamard-only gates.** Stage A puts an `H` on every selected qubit
  in one whole-chip batch — max parallel bits/shot (1 bit/qubit/shot, no entangling gates). Stage B
  adds mid-circuit measure-reset to harvest `k` bits/qubit/shot, still Hadamard-only for preparation.
  No fixed per-qubit target; shots are chosen for the total-bits goal and the per-shot yield is
  reported (bits/shot = number of selected qubits × harvest depth).
- **D6 — Strict, fully-typed Python** with `from __future__ import annotations`, PSR-equivalent
  style (PEP 8), type hints on every function signature. No raw file-format surprises: JSON via
  `json.dump`. Matches the reuse-base idioms (Qiskit, `SamplerV2`).

---

## §5 File plan

All paths under `CalibrationGuidedHighYieldQRNG/`. New files unless noted.

| Path | Change | Purpose |
|------|--------|---------|
| `README.md` | new | AC-2. Study overview: research question, hypothesis, Stage A/B, baseline, metrics table, honest-framing box (copied from build plan), and step-by-step run instructions for each script. |
| `code/` | new dir | AC-1. All EPIC 0 Python. |
| `qrng_output/` | new dir | AC-1. Bit files (`_perqubit.json`, `_perqubit_perdepth.json`, `_processed.txt`, `_raw.json`) + calibration snapshots. Add a `.gitkeep`. |
| `results/` | new dir | AC-1. EPIC 1 scores/PDF land here (empty now, `.gitkeep`). |
| `paper/` | new dir | AC-1. Write-up lands here (empty now, `.gitkeep`). |
| `code/pipeline_common.py` | new | AC-3, D1. Forked scaffold: `connect(name)`, `qpu_seconds(job)`, `_safe(fn)`, `run_sampler(backend, isa, shots, shots_per_job)` (chunked loop returning `(raw_meas, jobs_meta, total_qs)`), `write_raw_json(stem, run_meta, jobs_meta, raw_meas, calib)`, `timestamp()`. Constants: `HERON_R2_CANDIDATES`, `SHOTS_PER_JOB`, `OUTPUT_DIR`, `PAYG_USD_PER_SEC`. Copied from `qrng_bell_pairs.py`, not imported across the `ErrorDetectionVSRawBits` boundary. |
| `code/calibration_snapshot.py` | new | AC-4, AC-5. `read_snapshot(backend)` → per-qubit dict `{q: {t1, t2, readout_error, sx_error, reset_error}}` for every qubit; writes `calib_<backend>_<ts>.json`. `reset_probe(backend)` builds a tiny 1-qubit prepare→measure→reset→re-prepare→measure dynamic circuit, runs a small job, and prints PASS/FAIL (reset produced a fresh independent bit). `main()` runs both. |
| `code/stage_a_selection.py` | new | AC-6, AC-7, D2, D3, D7. Forks `qrng_noise_hadamard.py`: H on every selected qubit (whole chip), measure. `--select` mode = `all` (default) / `good` / `list:…` (D2). `process(bitstrings)` reuses the scaffold's aggregate join. Writes `stagea_<backend>_<ts>_processed.txt` (`bits:…`) + `_raw.json` with `qubits_used` order + embedded calibration snapshot. Prints bits/shot and shots needed for the total-bits goal. **No per-qubit file** — reconstructed in EPIC 1 from `raw_measurements`. |
| `code/stage_b_yield.py` | new | AC-8, AC-9, D3, D5, D7. Builds the mid-circuit loop: for chosen qubits, `prepare(H) → measure → reset → re-prepare → measure` repeated `k` times, one classical bit per measurement. Depth sweep over `k ∈ {1,2,4,8}` (config). Writes `stageb_<backend>_<ts>_processed.txt` (aggregate `bits:…`) + `_raw.json` embedding the `(qubit, depth, creg-slot)` layout + snapshot, so EPIC 1 reconstructs per-qubit-per-depth streams. Qubit subset + depths via CLI args / config constants. |

No edits to any file under `ErrorDetectionVSRawBits/`.

### Key implementation notes
- **AC-3 fidelity:** `run_sampler` keeps the exact chunked structure from `qrng_bell_pairs.py`
  lines 186–204 (`SHOTS_PER_JOB` chunks, `job.job_id()` print, `res[0].data.c.get_bitstrings()`,
  `qpu_seconds`, `_safe` metadata). Do not re-derive.
- **AC-6 / D2:** `--select all` = `[q for q in range(backend.num_qubits) if q not in props.faulty_qubits()]`;
  `--select good` reuses `qubit_is_good()`; `--select list:…` parses an explicit set. `initial_layout`
  = the chosen list, so classical bit *i* maps to selected qubit *i*; keep the `s[::-1]` reversal from
  `qrng_noise_hadamard.py:91`. Record `qubits_used` (the ordered list) in `_raw.json` for EPIC 1
  per-qubit reconstruction (D3).
- **AC-8 mid-circuit:** use a single qubit register plus a classical register sized `len(qubits) * k`;
  emit `qc.h(q); qc.measure(q, c_slot); qc.reset(q)` in the loop, final measure after the last
  reset+re-prepare. Transpile with `generate_preset_pass_manager(optimization_level=1, backend=…)`.
  Confirm the device supports mid-circuit measurement + reset via the S0.3 probe first (AC-5).
- **AC-7 / D7 print:** report bits/shot = number of selected qubits (Hadamard-only, 1 bit/qubit/shot,
  max parallel) and the shots needed for the total-bits goal — mirrors `qrng_noise_hadamard.py:123-125`.
  No fixed per-qubit target; yield is maximised by selecting the whole chip.
- **No raw SQL / no DB** here — pure Qiskit + JSON files.

---

## §6 Manual verification

No automated tests. Verify by hand:

1. **Scaffold (AC-1):** confirm `code/`, `qrng_output/`, `results/`, `paper/` exist; `README.md`
   present and readable.
2. **README (AC-2):** read it — research question, hypothesis, both stages, baseline, metrics
   table, honest-framing box, and per-script run steps are all present.
3. **Calibration snapshot (AC-4):** run `python code/calibration_snapshot.py [backend]`; confirm
   `qrng_output/calib_<backend>_<ts>.json` exists with per-qubit `t1/t2/readout_error/sx_error/reset_error`.
   If `reset_error` is `null`, note it (§11 Q1).
4. **Reset probe (AC-5):** same script prints PASS — mid-circuit measure→reset→re-prepare returns a
   fresh, non-stuck bit. If FAIL, stop and record as the honest failure path (epic Risks).
5. **Stage A (AC-6/7):** run `python code/stage_a_selection.py <small_shots> [backend] --select all`
   (and try `good` / `list:…`); confirm `stagea_*_processed.txt` (`bits:…`) and `_raw.json` with
   `qubits_used` order + embedded snapshot; confirm bits/shot + shots-needed line printed.
6. **Stage B (AC-8/9):** run `python code/stage_b_yield.py <small_shots> [backend]` with a tiny
   default qubit subset + `k∈{1,2,4,8}`; confirm `stageb_*_processed.txt` (`bits:…`) and `_raw.json`
   carrying the `(qubit, depth, creg-slot)` layout + snapshot.
7. **Done-when (AC-10):** all of the above produced files under `qrng_output/`.

Use tiny shot counts for verification to stay within the free-tier ~10 min/month budget; full runs
are the manual hand-off after EPIC 0.

---

## §7 Carried decisions (from the epic)

- Hardware: IBM Heron r2 (`ibm_kingston` / `ibm_fez` / `ibm_marrakesh`), Open plan / free tier;
  whole study under ~10 min/month (decision #1).
- Reuse, do not rebuild the pipeline or battery (decisions #2, #3).
- Runs are manual; EPIC 0 only builds runnable circuits (decision #4).
- Every raw output saved timestamped alongside its calibration snapshot (decision #5).
- Baseline = naive single-qubit Hadamard, 1 bit/qubit/shot, no selection; headline = usable bits
  per free-tier minute vs baseline (decision #6) — computed in EPIC 1, but Stage A *is* the
  baseline, so build it baseline-faithful.
- `quantum_seconds` accounting reused from the scaffold to track the budget (Risks).

---

## §8 Troubleshooting

- **`least_busy` picks nothing / all candidates offline:** pass an explicit backend name arg;
  candidate list is `HERON_R2_CANDIDATES`.
- **Mid-circuit reset unsupported / noisy (AC-5 FAIL):** do not run the Stage B sweep; record as the
  epic's honest failure result. Stage A still stands alone.
- **`props.gate_error("reset", q)` raises:** fall back to scanning `props.to_dict()`; if absent,
  store `null` (§11 Q1) — do not fabricate a value.
- **Per-qubit index misalignment:** verify the `s[::-1]` reversal and that `initial_layout` order
  matches the qubit list order; spot-check one qubit's bias against the raw measurement.
- **Budget creep:** watch the `quantum_seconds` line each run; keep verification shots tiny.

---

## §11 Open questions — RESOLVED

All resolved by developer 2026-07-14; answers folded into §4/§5.

- **Q1 — Reset-error source.** ✅ Try `props.gate_error("reset", q)` → scan `props.to_dict()` →
  else record `null` and flag (D4).
- **Q2 — Output format.** ✅ Keep the scaffold format: `_raw.json` + aggregate `_processed.txt`
  (`bits:…`), same as before. No per-qubit file; EPIC 1 reconstructs per-qubit streams from
  `raw_measurements` + `qubits_used` (D3).
- **Q3 — Stage A qubit set.** ✅ Selectable variations for manual runs: `--select all` / `good` /
  `list:…`; developer runs the variations they want (D2).
- **Q4 — Stage A yield.** ✅ Maximise bits/shot, Hadamard-only gates; no fixed per-qubit target —
  whole-chip H, report bits/shot (D7).
- **Q5 — Stage B default subset + depth.** ✅ As proposed: 3 lowest-readout-error qubits from the
  snapshot, `k ∈ {1,2,4,8}`; real top-5 passed in after EPIC 1 (D5).

---

**Plan updated with answers — ready for approval.**
Do not run implementation from this command; after approval run
`/implement-feature CalibrationGuidedHighYieldQRNG/Plans/feature-epic0-setup-and-measurement-circuits.md`.

---

## §13 Post-implementation

Built: thesis scaffold (`code/`, `qrng_output/`, `results/`, `paper/` + `README.md`);
`code/pipeline_common.py` (forked scaffold: `connect`, `qpu_seconds`, `_safe`, `run_sampler`,
`write_raw_json`, `write_processed_txt`, `timestamp`); `code/calibration_snapshot.py`
(per-qubit snapshot incl. reset-error fallback scan + measure-reset probe);
`code/stage_a_selection.py` (whole-chip Hadamard, `--select all/good/list:...`);
`code/stage_b_yield.py` (mid-circuit depth-sweep, `--qubits`/`--depths`, rep-major creg layout
recorded per depth for EPIC 1 reconstruction).

No deviations from the plan. Follow-ups for the developer:
- Run `python code/calibration_snapshot.py` on a real backend first — this sandbox has no IBM
  Quantum credentials/network, so live execution could not be exercised here (verified instead
  via `py_compile` and live imports against the installed qiskit/qiskit-ibm-runtime env).
- Stage B's default qubit subset (3 lowest-readout-error qubits) is a placeholder until EPIC 1
  produces the real top-5 ranked list — pass it via `--qubits` at that point.
- If the reset probe FAILs on the chosen device, stop before running the Stage B sweep (§8,
  epic Risks) — that becomes the honest failure result.
