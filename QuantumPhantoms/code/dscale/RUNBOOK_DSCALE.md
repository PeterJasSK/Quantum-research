# D-SCALE runbook (Peter only)

Everything in `code/dscale/` was verified with `--smoke` runs capped at 20 minutes (plan Q6). This runbook holds
the runs that are deliberately **not** done during implementation: **(A)** full simulation sweeps and **(B)**
hardware. Run all commands from `QuantumPhantoms/code/` with `/home/peter/anaconda3/bin/python3`.

`--full` lifts the first-run caps (4,000 shots, 15 repeats, 20 minutes; plan Q9). Use `--max-minutes 0` with it
for no deadline. Every CLI still writes partial results with `truncated: true` if you set a deadline and it fires.

Measured smoke speeds (8 cores, 2026-10-31), so you can size the runs:

| What | Speed |
|---|---|
| Pauli-twirled stabilizer sim (Aer, per 4,000-shot circuit) | ~3 s at 12 q, ~6 s at 30 q, ~70 s at 40 q with 400 CZ |
| heron mode (FakeMarrakesh full noise, MPS, per 4,000-shot circuit) | ~6 s at 12 q, ~40 s at 30 q |
| ghz-spine job (43 circuits) | ~2 min at N = 12, ~4 min at N = 30 per repeat (Pauli) |
| BP (QR copy) | 12-q hexagon < 0.2 s; 40-q kicked Ising 5 steps chi 8 ~ 1 s |

## Part A: full simulation sweeps

1. **Noise validation (AC-4) and back-test (AC-5).** ~30–60 min each.

   ```bash
   python -m dscale.validate_noise --pauli --full --max-minutes 0 --target marrakesh
   python -m dscale.validate_noise --backtest --full --max-minutes 0
   ```
   Output: `research_runs/_dscale/noise_validation.json`, `research_runs/_dscale/figures/hw_backtest.png`. If
   `passed` is false, every Pauli / twin verdict above 24 q stays labelled `unvalidated` in the maps.

2. **PMD re-tune (AC-11)** at full optimisation (24 starts per staircase model) and the target sample size.
   ~1–2 h for the whole 144-point grid. The floor scales as 1/n: more shots is the main lever for the L1′ gap.

   ```bash
   python -m dscale.families.pmd_bank --retune --full --max-minutes 0 --shots 4000 --repeats 15
   python -m dscale.families.pmd_bank --retune --full --max-minutes 0 --shots 20000 --repeats 15   # n = 300,000
   ```
   It writes `research_runs/_dscale/pmd_retune.json`; its `best` process is used by every later run.

3. **Survive-vs-simulable maps (AC-14)** for all three budgets. Several hours each at full grid (the QCA grid alone
   is up to 6 sizes x 5 depths x 4 angles); run overnight, one at a time.

   ```bash
   python -m dscale.survival --budget 40  --target boston    --full --max-minutes 0
   python -m dscale.survival --budget 100 --target boston    --full --max-minutes 0
   python -m dscale.survival --budget 120 --target nighthawk --full --max-minutes 0
   python -m dscale.survival --budget 120 --target marrakesh --families ghz-spine --full --max-minutes 0
   python -m dscale.survival --budget 100 --target helios-class --full --max-minutes 0     # optional
   ```
   Output per map: `research_runs/_dscale/survival_<budget>_<target>/survival_map.json` + figures. The Goldilocks
   zone (alive and BP-hard) is printed, or printed as "empty". An empty zone is a result, not a failure.

4. **D-SCALE on a cohort run** at full sampling (seed shapes + claims; then re-render and rebuild the page):

   ```bash
   python -m dscale.run --run ../research_runs/<run> --budget 40 --mode heron --full --max-minutes 0
   python -m imaging.build_tiles --run ../research_runs/<run>
   python -m f3_web.build_web --run ../research_runs/<run>
   ```

## Part B: hardware (Peter only)

Nothing in `code/dscale/` submits a job. These steps are yours.

1. **Build the pack** from the map of the matching budget (shots are sized from the alive cells' witness margins):

   ```bash
   python -m dscale.hw_pack --budget 40 --backend ibm_boston \
       --from-map ../research_runs/_dscale/survival_40_boston/survival_map.json
   ```
   Output: `research_runs/_dscale/hwpack-40-ibm_boston/manifest.json` + `circuits/*.qasm` (ISA transpiled to the
   fake stand-in) + the estimated QPU seconds. Add `--full` to lift the 4,000-shot cap when the k = 3 target needs
   more (the CLI says so).

2. **Order: 40 -> 100 -> 120.** Go up only when the smaller budget's claims came back as predicted.

3. **Account.** Use the pre-saved account only. Never paste, print or commit a token.

   ```python
   from qiskit_ibm_runtime import QiskitRuntimeService
   service = QiskitRuntimeService()                 # pre-saved account
   backend = service.backend("ibm_boston")
   ```

4. **Re-transpile against the live backend and re-check calibration.** The pack's ISA is a fake stand-in. Rebuild
   the logical circuits and transpile them on the live target with the pack's physical layout; drop the pack (and
   re-allocate with `python -m dscale.allocate`) if any allocated qubit now has readout > 0.06 or sx error >= 0.5,
   or any allocated coupler has a 2q error > 0.02 (`manifest.json` -> `calibration_gate`).

   ```python
   from qiskit import transpile
   isa = [transpile(c, backend=backend, initial_layout=c.metadata["layout"], optimization_level=1,
                    seed_transpiler=1) for c in logical_circuits]
   ```

5. **Submit with SamplerV2** (mitigation from `manifest.json`):

   ```python
   from qiskit_ibm_runtime import SamplerV2
   sampler = SamplerV2(mode=backend)
   sampler.options.dynamical_decoupling.enable = True
   sampler.options.dynamical_decoupling.sequence_type = "XX"
   sampler.options.twirling.enable_gates = True
   sampler.options.twirling.enable_measure = True
   job = sampler.run(isa, shots=SHOTS_FROM_MANIFEST)
   print(job.job_id())
   ```
   ZNE / PEA / PEC are EstimatorV2 runtime options only; D-SCALE's witnesses are sampled parities, so the pack
   does not use them by default.

6. **Label and record.** Every number from the device carries `hardware: <backend>, job <id>` and its claim level.
   Record the job id and the result in `QuantumPhantoms/README.md` -> Progress -> Quantum hardware and in the
   changelog, and keep the raw counts next to the pack (`hwpack-<budget>-<backend>/results/`). A failed witness is
   recorded as a result, not retried silently.

### Hardware ranking (web survey 2026-10-31; "(unverified)" = secondary sources only)

| Budget | Sim proxy | 1st choice (real) | Alternatives | Access for a student | Why |
|---|---|---|---|---|---|
| 40 | `boston`, `nighthawk` 5x8 | Heron r3: ibm_boston (2q ~2.15e-3 over 100 q), or ibm_aachen (EU; Heron r3 since 2026-03) (unverified) | Quantinuum Helios 98 q (institutional access only); IQM Emerald 54 q (EU, Braket); Nighthawk r2 ibm_phoenix | IBM Open Plan 10 min/month (kingston open since 2026-05, unverified); IBM Quantum Credits via supervisor; EuroHPC Quantum Access Pilot (<= 54 q, cut-offs 1 Nov / 1 Dec 2026, via supervisor) | GHZ scale proven on Heron; slack for pruning |
| 100 | `boston`, `kingston` | Heron r3 (boston / pittsburgh / aachen) | Nighthawk r1/r2; Helios (<= 98 q) | PAYG $96/min, Flex $72/min, or Credits | Big Cats: 100-q GHZ F = 0.55–0.70 on Heron |
| 120 | `nighthawk` (square), `marrakesh` (spine) | Nighthawk r2 ibm_phoenix for `ch-qca`; Heron r3 for `ghz-spine` (156 q leaves slack) | Nighthawk r1 ibm_berlin (EU, Premium/Flex early access) | Premium/Flex today; Open Plan access to Nighthawk unclear (unverified) | only the square lattice gives 4-loops natively |
| — | not recommended | Google Willow (no access), IonQ Tempo (no public 100-q cloud), Rigetti Cepheus 108 q (2q 99.1 %), neutral atoms | | | |
