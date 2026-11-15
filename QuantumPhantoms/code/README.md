# Quantum Phantoms — code

One command, one line through the pipeline. Run from `code/` with `/home/peter/anaconda3/bin/python3`.

```bash
python main.py                          # dry run: small sizes on the local fake backend (FakeMarrakesh, not hardware)
python main.py --backend ibm_aachen     # live: real hardware ("auto" = least busy). Peter only.
python main.py --shots 2000             # shots per circuit (default 4000 live, 400 dry)
python main.py --run <run directory>    # continue a stopped run (finished sections skipped, submitted jobs fetched)
```

Every run lives in `../research_runs/run_<dry|live>_<timestamp>/`; the page is `../web/<run>.html`.

## Sections

`main.py` calls each section's `main.py` → `run(ctx)` in this order. Sections exchange files only.

| Section | Files | Does | Writes |
|---|---|---|---|
| `C_certificate` | `main.py`, `bell_map.py`, `pbr.py`, `graph_bell.py` | Bell map, one job: CHSH on many disjoint pairs → certificate, bit pool, pair map. Too weak stops the run (no retry). Optional `GRAPH-BELL` | `commit.json`, `certificate.json`, `certified_bits.bin` |
| `B_mapping` | `main.py`, `roll.py`, `rac.py`, `xeb.py`, `games.py`, `iqp.py` (+ `iqp_params.json`) | rulebook + pool bits → tumour parameters (no job); then B's hypothesis circuit | `cohort_params.json`, `quantum_run.json`, `rulebook.json` |
| `D_quantum_growth` | `main.py`, `dscale.py` (+ `ghz_spine`, `ch_qca`, `pmd_bank`, `causal_states`, `seedlift`), `clock.py`, `pairs.py`, `ring_l2.py`, `graph_state.py`, `checks.py`, `du_meter.py`, `dtc.py` | quantum growth: per-tumour seed shapes or a hypothesis circuit | `dscale/` |
| `A_placement` | `main.py` | a 3-D site per tumour in the host lung | `sites.json` |
| `E_classical_growth` | `main.py`, `params_lung.json` | Kansal–Torquato + Pixel2Cancer growth from the seed | `growth.json`, `_roi/` |
| `F_render` | `main.py`, `lesion_fitted.py`, `lesion.py`, `insert.py`, `noise.py`, `fingerprint.py` | render into the host CT with its own blur and noise | `tiles.json`, `tiles/*.png` |
| `G_provenance` | `main.py` | lineage record + hash-chained ledger | `lineage_record.json`, `ledger.jsonl` |
| `H_analysis` | `main.py` | what the run shows, with its limits | `analysis.json` |
| `webpage` | `main.py`, `template.html` | one self-contained HTML page | `../web/<run>.html` |
| `common` | `runio`, `quantum`, `targets`, `allocate`, `lint`, `pauli_noise`, `witness`, `qhard`, `game`, `host`, `lidc_fetch`, `datamodel` | shared code | — |

Constants live where they are used, one place each: `common/__init__.py` (`HOST`, `FAKE_BACKEND`,
`MAX_QPU_SECONDS`), `C_certificate/main.py` (`MIN_PAIRS`), `C_certificate/bell_map.py` (`BELL_SHOTS`, `MATCHINGS`),
`B_mapping/roll.py` (`TILES`, `PAIRS`, `BITS`), `D_quantum_growth/dscale.py` (`BUDGET`),
`E_classical_growth/main.py` (`FRAMES`), `A_placement/main.py` (`SEED`).

## C: the certificate the run spends

C runs first. One job measures CHSH on up to 3 edge matchings of the chip (12 circuits, 1,024 shots; dry: 6 pairs,
200 shots).

- **Certificate:** one row per pair (S, sigma, certified = S > 2 by 3 sigma after Bonferroni) and a pooled verdict
  over the certified pairs: `S_low` = pooled S − 3 sigma, min-entropy per round f(`S_low`) (Pironio's analytic
  rate), `certified_bits` = rounds × f.
- **Stop rule:** fewer than `MIN_PAIRS` = 8 certified pairs (dry: 4), or `S_low` ≤ 2, or `p_value_local` ≥ 1e-6
  → exit code 7, no bits, no tumours, no retry. Both conditions must hold.
- **`p_value_local`** (`pbr.py`): a p-value that does not assume independent rounds. A CHSH-game test factor is
  fixed on the first third of each circuit's rounds and multiplied over the rest; p ≤ 1 / product. Its proof needs
  random settings per round; ours are fixed per circuit, so it carries the certificate's scope. Each pair row also
  has `p_no_signalling` and `cross_talk` (marginal of one qubit against the other qubit's setting).
- **Bit pool:** `certified_bits.bin` = Toeplitz hash of the raw outcomes, min(4096, certified_bits / 2) bits.
  `runio.draw_bits(ctx, label, n)` hands out the next n bits and records them in `certificate.json` →
  `budget.spent`. B draws the cohort from it (label `roll`, 64 bits per tumour). Every `Q.rng(ctx, name, label)`
  of a B or D circuit takes 64 pool bits as its seed and expands them with PCG64. A draw beyond the budget raises.
  A continued run gets the same bits for the same label.
- **Pair map:** S per measured coupler. Ring and tile ranking add Σ(2√2 − S) over the couplers (an unmeasured
  coupler counts as the map's median); pair tiles are the measured pairs, best S first; `R3-TEST` uses certified
  pairs only. Calibration pruning is unchanged and ranks what the map did not measure.
- **Replay key:** SHA-256 of `certified_bits.bin` (every per-tumour seed derives from it).
- **Chain:** before the job, SHA-256 of the circuits and the run name goes to `commit.json`. After it, the first
  pulse of the public drand beacon emitted after the commit (one GET) seeds the Toeplitz extractor; the response
  is stored verbatim (`beacon`, `pulse`). No network: note "beacon skipped", seed = `os.urandom`. Section G
  records commit → pulse → certificate hash and `python -m G_provenance.main <run>` checks it.
- **Switch:** `CIRCUIT = "BELL-MAP"` (default) or `"GRAPH-BELL"` at the top of `C_certificate/main.py`.
  `GRAPH-BELL` adds one Bell inequality over the graph state of the chip region (4 circuits; entry `graph_bell`
  with value, local bound, graph-state value and its own verdict; own derivation after Baccari et al., not
  transcribed from 2101.10307 [verify]) and runs one matching of the Bell map. The pool always comes from the
  Bell map, and the stop rule does not depend on `graph_bell`.

Scope, to state with every use: settings are fixed per circuit and the pairs sit on one chip, so this is
job-level and not device-independent; pairs are selected on the data that is pooled; f(`S_low`) is not a
composable security proof; the extractor seed is 32 bytes (beacon pulse or `os.urandom`) expanded with SHAKE-256;
the beacon is public, it dates the seed and is not a secret. Pool wording:
"bits extracted from Bell-test outcomes on one chip". Inputs of a hypothesis circuit come from the same device
before the circuit ran: the setting-independence loophole is open.

## Switching the circuit in B and D (C has its own switch, above)

One constant at the top of the section's `main.py`. The table of circuits (sizes, bound, pass rule, refusals) is
right below it.

```python
# B_mapping/main.py
CIRCUIT = "R5-H12"    # ROLL | R2-Q2 | R2-Q3 | R2-D4 | R2-MAP | R4-HEX | R5-H12 | R5-MAP8 | R5-D20 | R5-Y18
                      # | B-GHZ | B-MSQ | B-KS | B-IQP

# D_quantum_growth/main.py
CIRCUIT = "R3-TEST"   # DSCALE | GHZ-SPINE | CH-QCA | PMD-BANK | R1-STAR-001 | R1-TILE24 | R1-M2-00001 | R3-LADDER | R3-TEST | R3-CHIP64 | R3-INTRINSIC
                      # | R5-LADDER | R6a-S36 | R6a-S44 | R6b-LEAN64 | R6b-PUB64 | L2-BAND
                      # | D-GRAPH | D-STC | D-DU | D-DTC
```

- **B:** the cohort is always drawn from the pool (`ROLL` stops there). Any other value adds that hypothesis
  circuit on the same backend; its claim is about the device, never the tumour. The cohort's level is L0: a
  sibling pair is a classical copy with mutation (the 642-CZ roll circuit is gone).
- `R2-MAP` is `R2-Q2` on 24 qubits at once (the best readouts of the pruned chip), 8 circuits; pass = at least 20
  qubits above 0.75 by 3 sigma after Bonferroni.
- The hexagon game (`R5-*`) stores the pass rate of every parity per input (`parities_per_input`); the claim value
  stays the all-parities win rate and the note gives the single-parity rates.
- **D:** `DSCALE` is today's composite (GHZ spine + QCA + PMD); its QCA snapshots are the seed shapes. `GHZ-SPINE`,
  `CH-QCA`, `PMD-BANK` run one of its families alone (first pick of the qubits, nothing running next to it; the
  spine tree is then chosen by qubit quality, not depth). `CH-QCA` and the R6 rings also give seed shapes. With any other circuit the tumours grow from the 2 mm ball.
- `R3-TEST` is the hypothesis test of Seif et al. (2408.03376 Sec. III): name a hidden Pauli channel with a sister
  memory; without a quantum memory the success rate is at most 1/2 + 0.43 M 2^-n. One pool of 2,000 circuits at 10
  shots each serves every size (multiples of 8 up to the certified pairs of the Bell map) and every trial.
- `R1-TILE24` runs both arms (identical steps, and first step compiled): two claims.
- `R5-LADDER` has rungs (n, k): the cluster ring of n qubits plus k identity pairs of its CZ layers, one job per
  rung. Fit −ln F = a·n + lam·N_CZ; `qhard/loss_per_cz.json` holds `loss_per_cz` (lam), `readout_loss_per_qubit`
  (a) and both sigmas.
- The R6 rings read that file when it is in the run directory: they log a forecast (accepted fraction, fidelity,
  signal in sigma) and are refused when the signal is below 3 sigma at the shot budget. Section H prints
  "L2 distance". To have both in one run: run D with `R5-LADDER`, delete `dscale/dscale_run.json`, set the ring,
  `--run <dir>`.
- **Candidates (QCAND, `../plans/feature-QCAND-candidate-circuits-B-C-D.md`), all additive, dry runs only so far:**
  - `B-GHZ`: N-player GHZ parity game on a breadth-first tree, sizes 8 to 40 (dry 4, 6), 32 even-weight inputs per
    size; pass per size = win above 1/2 + 2^-ceil(N/2); the claim is the largest passing N. Locality assumed.
  - `B-MSQ`: magic square game on two Bell pairs per 4-qubit path, 16 tiles, all 9 inputs; bound 8/9.
  - `B-KS`: sequential Peres–Mermin test, 2 qubits + ancilla, mid-circuit readout and reset; chi against 4. Live it
    is refused until `MID_CIRCUIT_LIVE = True` in `B_mapping/games.py` (the option is off by default on the plan).
    It does not go through `quantum.execute` (which refuses dynamic circuits); same transpile and spend guard.
  - `B-IQP`: a classically trained IQP circuit (9 qubits per tumour) samples the property words; the cohort of the
    run is then decoded from its shots and replaces the pool's roll (no sibling pairs). Parameters are trained once
    per region shape and cached in `B_mapping/iqp_params.json`. Level L0, no hardness claim.
  - `D-GRAPH`: graph state of the region; per coupler, pair tomography with the neighbours read in Z; negativity.
    Pass = entangled couplers connect 90 % of the qubits. A dry run measures 1 batch of 4, so it cannot pass.
    Also writes seed shapes (one all-X snapshot).
  - `D-STC`: Clifford ring with spacetime checks from an own minimal finder; fidelity with and without
    post-selection, gain. On a random ring the finder only reaches one-layer links on the ancilla's qubit (4 to 9 %
    of first-order faults); the ancilla checks of `ring_l2.py` reach further.
  - `D-DU`: kicked-Ising chain at the dual-unitary point; the operator Z_x Y_(x+1) moves one site per step with
    exact value cos^t(2h). Fit gives the loss per CZ layer, merged into `qhard/loss_per_cz.json`
    (`loss_per_layer`); the ring forecast uses it in place of the ladder's lam when present.
  - `D-DTC`: Floquet time-crystal cycle on a patch; Delta(t) and one seed shape per tumour per circuit
    (`<tile id>/f<k>` in `dscale/seed_shapes.npz`). Section E seeds from frame 0 and records the frames' cell
    counts (`seed_frames`); the growth law stays classical. Level L0.
  - Kill rule: two live runs below the bound on the best backend → marked dropped in `RUNLOG.md`.
- Rings (R5, R6) are picked on the calibration-pruned chip; when pruning leaves no ring (one pruned qubit removes
  a hexagon) every ring is ranked by pruned qubits, then measured CZ + readout error, and the claim note says so.
- Claims go to `claims.json` and to the page. A dry-run pass is labelled "(dry run: not a claim)".
- A dry run tests the pipeline, not the science: 4 tumours of at most 7 mm (`DRY_*` in `B_mapping/roll.py`), 400
  shots, each circuit's `dry` sizes from its `CIRCUITS` row, no do-not-build refusals. About 2 to 3 minutes.
- Circuits on the plans' "do not build" list for a backend are refused (`refuse` in the table).
- Scores are raw counts: no readout mitigation in a hypothesis job.
- Sizes are first-run sizes; the plan's published size is in the comment next to it.

Plans: `../plans/qhard-D-L2-ring-configurations.md`, `../plans/qhard-R1-R5-configurations-and-BD-flagship.md`.

## Live runs

- Pre-saved `QiskitRuntimeService()` account, never a token. One backend per run (`backend.json`).
- Every job id is written to `jobs/<key>.json` before waiting. `--run <dir>` fetches it instead of resubmitting.
- Raw counts of every job that goes through `quantum.execute` are kept in `jobs/<key>.npz` (`c0000`, ... =
  `np.packbits` per circuit, `shapes` = (shots, classical bits) per circuit).
- Spend guard: the estimate over all jobs of a run stays under `MAX_QPU_SECONDS` (45); shots are cut to fit, below
  300 the job is refused.
- To redo a section, delete its output file and run `--run <dir>` again.

```bash
python -m common.lidc_fetch LIDC-IDRI-0481       # once: the public host CT (~136 MB)
python -m G_provenance.main <run directory>      # does every file still match the lineage record?
```

## Not run yet

Dry runs pass (2026-11-15, after QSCALE and QCAND); the live log is `RUNLOG.md`. The Bell map, the pool draw,
`R2-MAP`, the (n, k) ladder, the ring forecast and every QCAND candidate have not run on hardware. First places to look when a run fails:

| Where | Open point |
|---|---|
| `common/quantum.py` | Single path for every job. Dry run of wide Clifford jobs uses the Pauli-twirled model. |
| `C_certificate/bell_map.py` | Live: 3 matchings of about 70 pairs each in parallel, never run at that width. Toeplitz by FFT. |
| `common/game.py` ladder | An identity CZ pair can echo coherent errors, so lam may read low. The ring forecast is a desk model: on the dry backend it gave fidelity 0.75 where the ring measured 0.29. |
| `D_quantum_growth/dscale.py` | Same logic as the old live job, re-plumbed. Default `BUDGET = 100` live; a dry run uses `DRY_BUDGET = 40`. |
| `common/game.py` | Win rule derived (all deterministic parities), not transcribed from 2110.04277. |
| `D_quantum_growth/ring_l2.py` | Own check construction; doping loss is a placeholder; doped circuits are sampled live only. |
| QCAND candidates | Bounds are [verify]. `GRAPH-BELL` and `D-DU` use own derivations (checked on the ideal simulator), not the papers' equations. `B-GHZ` and `D-DU` layouts rank by calibration, not the Bell map. Live sizes above the pruned chip are refused or cut. |
| `B_mapping/xeb.py` | bits(ε) is a two-point line (gap G9), so it cannot pass as coded. Inputs: 64 pool bits expanded with PCG64. |
| Pruned files | `ghz_spine`, `ch_qca`, `pmd_bank`, `causal_states`, `seedlift`, `allocate`, `lint` were cut to what the pipeline calls. |

## Honest claim

Tumour parameters are drawn from bits extracted from a Bell test on one chip; growth and image are classical. A
pooled CHSH above 2 by 3 sigma on hardware is a job-level Bell violation, not device-independent; a dry run
certifies nothing. Every other quantum number carries its level, its
classical bound, the rigour of that bound and its label.
