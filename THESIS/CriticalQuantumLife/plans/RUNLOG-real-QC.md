# RUNLOG — running the Quantum Canary on real QC

**Purpose.** How to run the Canary against a real IBM backend, split by cost. Two layers:
- **FREE layer** — the calibration poller. Real backend, **zero credits** (metadata only).
  Works NOW.
- **COST layer** — the witness heartbeat. Runs real circuits = **shots billed**. Run on an
  allocation when the free tier resets.

Target backend (Run-1): **`ibm_kingston`** — 156-qubit Heron r2. Any operational Heron works.

Prerequisite for both: a configured `QiskitRuntimeService` account (already set up — verified
`ibm_kingston` reachable 2026-09-06). If not: `QiskitRuntimeService.save_account(channel=..., token=...)`.

---

## Layer 1 — FREE calibration poller (zero credits, works now)

Reads `backend.target` / `.properties()` / `.status()` — published metadata. **No job is
submitted, no shots billed.** Gives the incumbent RB/coherence numbers: 2q error, readout
error, T1/T2, operational flag, queue depth.

```bash
cd THESIS/CriticalQuantumLife/code

# single poll
python calibration_poller.py --backend ibm_kingston --once --chain 6

# time-series: every 15 min for a day (still zero credits)
python calibration_poller.py --backend ibm_kingston --interval 900 --cycles 96 --chain 6

# offline synthetic sample (no account, for wiring the web)
python calibration_poller.py --demo
```

Output → `research_runs/canary_calibration_<backend>.json` (a growing `samples[]` series).

**Verified real pull (2026-09-06, ibm_kingston, zero credits):**
```
operational=True  queue=10
global : 2q_err mean 0.00548  max_live 0.15343  (dead edges 8)
         readout mean 0.01941  (dead qubits 0)
chain-6: twoq_err_mean 0.00196  twoq_err_max 0.00223  readout_max 0.00745
coherence: T1 189.8µs  T2 122.7µs   credits=0
```

**Show it in the web:** open `web/ops_console.html` → "Load calibration" → pick
`canary_calibration_ibm_kingston.json`. The free layer (real backend, zero credits) renders
above the witness heartbeat (cost layer).

---

## Layer 2 — COST witness heartbeat (shots billed — run on allocation)

This is the new signal: the entanglement witness `⟨X^⊗W⟩` above the classical null. It
**requires running a circuit** (that is *why* it can't be faked). Each cycle = one short
GHZ-genealogy circuit submitted to the QPU.

### ⚠ Plumbing not yet wired
`CanaryProbe(backend=...)` currently routes through `closed_loop.run_counts`, which raises
`NotImplementedError("hardware backend is F5")`. Before a real heartbeat run, wire the probe's
`_run()` to the hardware submission path in `hardware_batches.py` (the F5 sampler +
`gated_chain_with_stats` calibration gate). One focused change; do it first.

Intended once wired:
```bash
# pin the low-error chain the free poller already identified, small W, low shots, slow cadence
python canary_exporter.py --backend ibm_kingston --w 4 --shots 1024 --cycles 24 --session live_kingston
# → research_runs/canary_live_kingston.json  +  OpenMetrics on :9797
```

### Cost control (keep the heartbeat cheap)
- **Small W** (4) — the witness must clear the null on NISQ; small width survives readout+2q err.
- **Low shots** (1024–2048) — the null band widens to `3/√shots` but a healthy chain clears it.
- **Slow cadence** — one cycle per N minutes, not continuous. Interleave with the provider's
  calibration jobs if you own the chip.
- **Sim-first sign check** — run `canary_exporter.py --w 4 --cycles 5` on Aer before spending shots.
- Budget estimate: dynamic-free static circuits are cheap; a 24-cycle W=4 heartbeat at 1024 shots
  is a few tens of seconds of QPU time. Calibrate against one timed job before a long run.

### The honest split (why the buyer is the provider)
- Free tier / renter: run the **poller continuously** (zero credits) + the **heartbeat in short
  bursts** on whatever allocation you have.
- Provider (the real product): run the heartbeat on **idle spare qubits** at marginal cost ≈ 0,
  always-on. That is the deployment the thesis targets.

---

## Full sequence when the free tier resets

1. `python calibration_poller.py --backend ibm_kingston --interval 900 --cycles 96` — free
   baseline running (zero credits).
2. Wire `CanaryProbe._run` → `hardware_batches` submission (the one deferred plumbing change).
3. Aer sign check: `python canary_exporter.py --w 4 --cycles 5` (free).
4. One timed hardware smoke: `python canary_exporter.py --backend ibm_kingston --w 4 --shots 1024
   --cycles 3 --session smoke_kingston` — confirm the witness clears the null on the real chain,
   note the QPU seconds.
5. Short heartbeat burst on allocation (cycles 24, cadence to taste).
6. Web: load both `canary_calibration_ibm_kingston.json` (free layer) and
   `canary_live_kingston.json` (cost heartbeat) into `ops_console.html`.

**One line:** the poller gives you a real QC on the web for free forever; the witness heartbeat
is the paid layer — cheap in short bursts, free only if you own the chip.
