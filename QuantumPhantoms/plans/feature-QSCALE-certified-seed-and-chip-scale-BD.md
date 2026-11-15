# Feature QSCALE — Certified seed (C) that the pipeline consumes, and chip-scale B and D

**Epic:** [epic-quantum-phantoms-mvp.md](epic-quantum-phantoms-mvp.md) (Approved); parents
[qhard-R1-R5-configurations-and-BD-flagship.md](qhard-R1-R5-configurations-and-BD-flagship.md),
[qhard-D-L2-ring-configurations.md](qhard-D-L2-ring-configurations.md). The epic has no row for this step: it is
planned as a standalone feature on top of the minimal pipeline of 2026-11-11.
**Feature ID:** QSCALE
**Author:** Claude (Opus)
**Date:** 2026-11-14
**Status:** Complete (2026-11-15; approved 2026-11-14, Peter: all proposed defaults accepted). Dry runs only: nothing here has run on hardware

> Stack locked: Python 3.13 (conda base), Qiskit, the minimal pipeline in `code/` (one `main.py` per section, one
> `CIRCUIT` constant in B and D, four CLI flags, no new flags). No automated tests, manual verification only. Dry
> runs stay small (2 to 3 minutes). Hardware jobs are run by Peter only. A bound marked `[verify]` never becomes a
> claim; L2 stays blocked.

---

## 1. Why (Step Goal)

**Before.** Eleven live runs on `ibm_fez` (see `code/RUNLOG.md`):

| Finding | Evidence |
|---|---|
| Small circuits pass and repeat | R1-STAR-001 4 of 4 runs (0.38 to 0.40 vs 0.296), R2-Q2 3 of 3 (0.85 vs 0.75), R2-Q3, R2-D4, R3-TEST up to 40 pairs |
| Anything deep or wide in one state fails | DSCALE 0 claims in 5 runs; hexagon game 0.684 vs 0.80; ring state F about 0.58 at depth 2 |
| Section C does nothing for the rest | S is computed, printed, and gates the run. No section consumes it. The tumour parameters come from a separate 642-CZ roll circuit that is noise-dominated |
| Layout uses a stale calibration | Every run used the snapshot of 2026-11-13 17:27; pruning removed every hexagon |
| The loss meter cannot split readout from gate loss | R5-LADDER has N_CZ = n at every rung |
| Raw counts are not stored | The Run02 to Run03 GHZ drop (0.457 to 0.258) could not be explained |

**What the literature search of 2026-11-14 adds** (partial reads through summaries; every number here is `[verify]`):

| Idea | Source | Verdict for this project |
|---|---|---|
| Peaked circuits as verifiable advantage | 2510.25838; IBM advantage tracker blog 2026-02-23 | **Do not build as L2.** Ran on `ibm_boston` at about 5,000 gates, then new classical methods solved them in seconds (Feb 2026). Heuristic hardness did not hold. Useful only as proof that Heron keeps a detectable signal at that depth |
| Unconditional separation, 12 qubits vs 62 bits | 2509.07255 | Already our R4. Needs true-random inputs (the paper is explicit), about 2.5e-3 two-qubit infidelity for a 2n-vs-n result, and global Clifford measurements. Live trial Run05: eps = -0.21 ± 0.15 at 8 layers, no signal. Stays a stretch; **C can supply its random inputs** |
| 120-qubit GHZ with 8 check qubits | 2510.09520 | Same 100-qubit circuit: `ibm_kobe` 0.70, `ibm_kingston` 0.55, `ibm_fez` 0.46. **fez is the weakest of the three.** Post-selection keeps 14 to 36 % of shots, not 1e-4 |
| Bell correlations on 73 qubits, two settings per qubit | 2406.17841 | Link-wise CHSH on a honeycomb lattice, 48 sigma. Shows a Bell test can be chip-scale. Basis for the Bell map below |
| Noisy shallow 2-D circuits beat AC0 | 2609.40050 | Theory only, needs fault-tolerant encoding. Not usable |
| Certified randomness from a quantum computer | Liu et al., Nature 640, 343 (2025) | A certificate is useful when a later step **spends** the certified bits. That is the design for C |

**Where this leaves L2.** No cheap route exists. The only L2 reference that stands is the published depth-73 ring
(2607.25941), out of reach on our budget. What this feature does instead:

1. Makes the distance to L2 a **measured number** (gate loss and readout loss, separately, per backend), with an
   automatic go / no-go for `R6a-S36`.
2. Moves scale sideways: many qubits carrying a certified claim at once (Bell map on up to about 70 pairs, R1 and
   R2 on every good tile, R3 on every available pair) instead of one deep state.
3. Gives the unconditional rung (R4) the one input it lacks today, quantum-random inputs, without claiming it.

**After.**

- C runs first. One job measures CHSH on many disjoint pairs across the chip. It yields (a) the certificate,
  (b) a pool of extracted random bits with an entropy budget, (c) a fresh per-pair quality map.
- B draws the tumour parameters from those bits (the 642-CZ roll circuit is gone). No certificate, no bits, no
  tumours: C is now a dependency, not a stamp.
- Every random input of a B or D hypothesis circuit (R3 hidden Paulis, R5 inputs, R4 targets) comes from the same
  pool, and the ledger records bits certified against bits spent.
- B and D pick qubits from the Bell map of the same run, not from yesterday's calibration.
- D stores raw counts, measures gate loss and readout loss separately, and prints the distance to L2.

---

## 2. Acceptance Criteria

**C: certificate that is consumed**

- [x] **AC-1** (QSCALE.C1): C runs before B and submits one Bell-map job.
  Evidence: `code/main.py:23`, `code/C_certificate/bell_map.py:36` (matchings), `:54` (4 setting circuits), `:77` (one job)
  → `code/main.py` order becomes C, B, D, A, E, F, G, H, web. `C_certificate/bell_map.py` builds, for each of up
  to 3 edge matchings of the coupling graph, the 4 CHSH setting circuits with every pair of the matching in
  parallel (depth 1, one CZ per pair). 12 circuits, `BELL_SHOTS = 1024` each, through `common.quantum.execute`.
  Dry: 1 matching, 6 pairs, 200 shots.
- [x] **AC-2** (QSCALE.C2): `certificate.json` holds one row per pair and a pooled verdict with finite statistics.
  Evidence: `code/C_certificate/main.py:52` (per pair), `:56` (S_low), `:70` (hmin), `:33` (scope)
  → Per pair: qubits, S, sigma, `certified` = S - 3 sigma > 2 after Bonferroni over pairs. Pooled: rounds of
  certified pairs, S_pooled, S_low = S_pooled - 3 sigma, `hmin_per_round = f(S_low)` (existing Pironio formula),
  `certified_bits = rounds x hmin_per_round`. Scope text stays "job-level; not device-independent" and adds
  "settings fixed per circuit, pairs on one chip, no space-like separation".
- [x] **AC-3** (QSCALE.C3): the run stops when the certificate is too weak.
  Evidence: `code/C_certificate/main.py:31`, `:58`, `:88`; `code/B_mapping/roll.py:220` (no pool: exit 7)
  → Fewer than `MIN_PAIRS = 8` certified pairs, or S_low <= 2: status "FAILED", exit code 7, no bits written, no
  retry. Same rule as today, on the pooled value.
- [x] **AC-4** (QSCALE.C4): C writes the bit pool and its budget.
  Evidence: `code/C_certificate/bell_map.py:94` (toeplitz), `code/C_certificate/main.py:73-79`
  → Raw outcomes of certified pairs are compressed by Toeplitz hashing (numpy, GF(2)) to
  `min(4096, floor(certified_bits / 2))` bits, written to `certified_bits.bin`. The hashing seed comes from
  `os.urandom` and is stored in the certificate. `certificate.json` gets `budget: {available, spent: {}}`.
- [x] **AC-5** (QSCALE.C5): every seed of the run derives from the pool, and spending is recorded.
  Evidence: `code/common/runio.py:62` (run_key), `:84` (draw_bits); `code/common/quantum.py:228` (rng seeded from the pool)
  → `common/runio.py`: `run_key(ctx)` returns the SHA-256 of `certified_bits.bin` when it exists;
  `draw_bits(ctx, label, n)` hands out the next n bits and appends `{label: n}` to `budget.spent`. A draw beyond
  the budget raises. `quantum.rng(ctx, ...)` is unchanged for callers.
- [x] **AC-6** (QSCALE.C6): the Bell map is the layout input of the run.
  Evidence: `code/C_certificate/main.py:64`, `code/common/qhard.py:164` (bell_deficit), `:179`, `:287`, `:294`; `code/D_quantum_growth/pairs.py:109`
  → `certificate.json` field `pair_map` (edge → S). `common/qhard.py`: ring and tile ranking add
  `sum(2 sqrt(2) - S_e)` over measured edges when a map exists; `D_quantum_growth/pairs.py` takes its Bell pairs
  in descending S. Calibration pruning stays as the fallback when an edge was not measured.
- [x] **AC-7** (QSCALE.C7): the page and the analysis show the certificate as a resource.
  Evidence: `code/H_analysis/main.py:53`, `code/webpage/template.html:214`, `code/webpage/main.py:70`, `code/G_provenance/main.py:23`
  → `H_analysis/main.py`: pairs certified, bits available, bits spent by consumer. `webpage/template.html`: one
  line "N of M pairs certified, B bits certified, b spent" in place of the bare S value. `G_provenance/main.py`
  hashes `certified_bits.bin`.

**B: parameters from certified bits, claims on many tiles**

- [x] **AC-8** (QSCALE.B1): tumour parameters are drawn from the pool with the rulebook distribution.
  Evidence: `code/B_mapping/roll.py:181` (draw_tumour, inverse CDF), `:211` (roll, no job)
  → `B_mapping/roll.py`: `roll(ctx)` draws 16 bits per property through `runio.draw_bits`, maps them by inverse
  CDF on the existing `Rulebook` probabilities, and builds sibling pairs by the existing mutation probability.
  No circuit, no job. `quantum_run.json` keeps its fields; `job_id` is the Bell-map job. The amplitude-tree
  circuit builders are removed.
- [x] **AC-9** (QSCALE.B2): new B circuit `R2-MAP`: the random access code on every good qubit at once.
  Evidence: `code/B_mapping/main.py:31`, `code/B_mapping/rac.py:66`
  → `B_mapping/main.py` row `R2-MAP` (`tiles: 24`, `min_pass: 20`, dry `tiles: 3`), `B_mapping/rac.py` runs the
  8 circuits of R2-Q2 with all tiles in parallel, Bonferroni over tiles. Pass rule: at least 20 of 24 qubits above
  0.75 by 3 sigma.
- [x] **AC-10** (QSCALE.B3): the hexagon game reports each parity separately.
  Evidence: `code/common/game.py:185`, `:219`, `:224`
  → `common/game.py` `play` returns the pass rate of each deterministic parity per input; `result.json` stores
  them. The claim value stays the all-parities win rate; the single input-dependent parity is reported in the
  note. Which one the 0.80 bound refers to is decided by the PDF check (Q3).

**D: raw data, a meter that separates losses, distance to L2**

- [x] **AC-11** (QSCALE.D1): every hypothesis job keeps its raw counts.
  Evidence: `code/common/quantum.py:209` (`_keep`), called at `:200`, `:205`
  → `common/quantum.py` `execute` writes `jobs/<key>.npz` (packed bit arrays per circuit) next to the job id file.
- [x] **AC-12** (QSCALE.D2): `R5-LADDER` separates readout loss from gate loss.
  Evidence: `code/common/game.py:232-274`, `code/common/qhard.py:445` (barrier), `code/D_quantum_growth/main.py:73`
  → Rungs become (n, k): the ring cluster circuit plus k identity pairs of its CZ layers (CZ twice = identity),
  `k` in (0, 2, 4), `n` in (12, 20). Fit `-ln F = a n + lam N_CZ`. `loss_per_cz.json` gets `lam`, `a`, both sigmas.
  Dry: n = 12, k in (0, 2).
- [x] **AC-13** (QSCALE.D3): the run states its distance to L2.
  Evidence: `code/D_quantum_growth/ring_l2.py:184` (forecast), `:242-251` (log + refusal), `:202` (l2_distance); `code/H_analysis/main.py:73`
  → `D_quantum_growth/ring_l2.py` reads `a` and `lam`, forecasts fidelity and accepted-shot fraction of the
  configured ring, and refuses (`Refused`, logged) when the forecast signal is below 3 sigma at the shot budget.
  `H_analysis/main.py` prints "L2 distance: R6a-S36 needs loss per CZ <= x; measured y on <backend>".
- [x] **AC-14** (QSCALE.D4): `R1-TILE24` runs both arms.
  Evidence: `code/D_quantum_growth/main.py:45`
  → `D_quantum_growth/main.py`: `identical_steps: [True, False]` (the identical-steps arm is the one that matches
  the time-independent machine of 2005.04241).
- [x] **AC-15** (QSCALE.D5): `R3-TEST` uses the best pairs and fewer shots per inserted Pauli.
  Evidence: `code/D_quantum_growth/pairs.py:42-43`, `:109-110`, `:120`; `code/D_quantum_growth/main.py:61`
  → `SHOTS_DIV` raised so each circuit gets 10 shots (pool 2,000 circuits live, dry 24); pairs from the Bell map
  (AC-6); sizes extend to every multiple of 8 up to the certified pairs available.

**Docs**

- [x] **AC-16** (QSCALE.X1): documents match the code.
  Evidence: `code/README.md` (sections table, "C: the certificate the run spends", circuit list), `CLAUDE.md:17`, `:28`, `README.md` changelog 2026-11-15, `code/RUNLOG.md` Next item 0
  → `code/README.md` (section table, order, C description, new circuits), `CLAUDE.md` (order C B D), `README.md`
  progress and changelog, `code/RUNLOG.md` "Next".

---

## 3. Out of Scope (Postponed)

- Peaked or obfuscated-mirror circuits as an L2 claim → not planned; classical methods overtook them in Feb 2026.
- R4-HEX as a claim → stays blocked until the bound's constants are transcribed from 2509.07255 (gap G9) and a
  backend reaches the needed gate error. This feature only removes the pseudo-random-input blocker's cause.
- A device-independent certificate (random setting per shot, separated devices) → not possible on one chip.
- The honeycomb Bell-energy witness of 2406.17841 (needs a variational low-energy state) → later feature if the
  Bell map works.
- The published 64-ring (`R6b-PUB64`) and any L2 claim → blocked by the hard rules.
- Feeding quantum outcomes into growth dynamics (division times from the R1 clock) → CLAUDE.md priority 1,
  separate feature.
- Rework of the old DSCALE families → dropped on 2026-11-14.
- Readout mitigation in hypothesis jobs → scores stay raw counts.

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Bell-map pairs | Greedy edge matchings of the backend coupling graph (networkx), up to 3, so most edges are measured once |
| CHSH settings | The existing `CHSH_SETTINGS` of `B_mapping/roll.py`, moved to `C_certificate/bell_map.py` |
| Certified pair rule | S - 3 sigma > 2 with Bonferroni over measured pairs |
| Entropy estimate | Pironio f(S) at S_low of the pooled certified rounds; labelled "analytic rate at a 3-sigma lower value, not a composable security proof" |
| Extractor | Toeplitz matrix over GF(2) in numpy, output at most half the estimated entropy, capped at 4,096 bits |
| Seed chain | `certified_bits.bin` → SHA-256 → `run_key`; all existing `rng(ctx, label)` calls inherit it |
| Bits to parameters | Inverse CDF with 16 bits per property on the rulebook probabilities |
| Raw counts | `numpy.savez_compressed` of `np.packbits` arrays, one file per job |
| Loss fit | Two-parameter least squares on (n, N_CZ), white-noise reading of the game score |

**Conventions & Notes:**
* One job per section call through `common/quantum.py`; no new CLI flag; constants where they are used.
* `--run <dir>` resume must still work: C's job id is written before waiting, and `draw_bits` is deterministic
  in the order of labels.
* Labels: a dry run writes "certification-ready, not certified (simulated)" and the pool is marked simulated.
* Honest wording for the pool: "bits extracted from Bell-test outcomes on one chip; job-level; not
  device-independent". Never "certified random" without that scope.
* Input randomness for D claims: note "inputs drawn from the run's Bell-test bits (same device, drawn before the
  circuit ran: the setting-independence loophole is open)".
* Removing the roll circuit ends the entangled sibling pair on hardware. The claim level of the cohort stays L0.

---

## 5. Data Model (Additions/Modifications)

```text
[Existing file - Modifying]  <run>/certificate.json
  chsh_S, classical_bound, tsirelson_bound, backend, job_id, passed, status      (kept; chsh_S = pooled value)
  pairs            list of {qubits [a, b], S, sigma, certified}
  rounds           int      rounds of certified pairs
  S_low            float    pooled S minus 3 sigma
  hmin_per_round   float    f(S_low)
  certified_bits   float
  extractor        {kind "toeplitz", seed_hex, output_bits}
  budget           {available int, spent {label: bits}}
  pair_map         {"a-b": S}

[New file]  <run>/certified_bits.bin        extracted bits, hashed by G

[New file]  <run>/jobs/<key>.npz            raw bit arrays of every job

[Existing file - Modifying]  <run>/quantum_run.json
  job_id           the Bell-map job (no roll job any more)
  raw_bits         the pool bits spent per tumour

[Existing file - Modifying]  <run>/qhard/loss_per_cz.json
  loss_per_cz (kept), readout_loss_per_qubit, sigma_lam, sigma_a

[Existing file - Modifying]  <run>/analysis.json
  certificate_budget {available, spent}, l2_distance {config, needed, measured, backend}
```

No migration: older run directories stay readable by the page builder (missing fields shown as "n/a").

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| Modify | `code/main.py` | Section order C, B, D, A, E, F, G, H, web |
| New | `code/C_certificate/bell_map.py` | Matchings, CHSH circuits on parallel pairs, per-pair S and sigma, Toeplitz extraction |
| Modify | `code/C_certificate/main.py` | Run the Bell map, pooled verdict, stop rule, write `certificate.json` and `certified_bits.bin` |
| Modify | `code/common/runio.py` | `run_key` from the pool, `draw_bits(ctx, label, n)`, budget bookkeeping |
| Modify | `code/common/quantum.py` | `execute` stores `jobs/<key>.npz` |
| Modify | `code/common/qhard.py` | Ring, tile and pair ranking read `pair_map` when present |
| Modify | `code/common/game.py` | Per-parity pass rates; ladder rungs (n, k) and the two-parameter fit |
| Modify | `code/B_mapping/roll.py` | Parameters by inverse CDF from `draw_bits`; circuit builders and CHSH code removed |
| Modify | `code/B_mapping/main.py` | Row `R2-MAP`; `CIRCUIT` comment |
| Modify | `code/B_mapping/rac.py` | Parallel tiles for `R2-MAP` (mirror the tile loop of `D_quantum_growth/clock.py`) |
| Modify | `code/D_quantum_growth/main.py` | `R1-TILE24` both arms; `R3-TEST` sizes and pool; `R5-LADDER` rungs |
| Modify | `code/D_quantum_growth/pairs.py` | Pairs by Bell-map S; 10 shots per inserted Pauli |
| Modify | `code/D_quantum_growth/ring_l2.py` | Forecast from `a` and `lam`, automatic refusal |
| Modify | `code/G_provenance/main.py` | Hash `certified_bits.bin` |
| Modify | `code/H_analysis/main.py` | Certificate budget, L2 distance |
| Modify | `code/webpage/main.py`, `code/webpage/template.html` | Certificate line with pairs and bits |
| Modify | `code/README.md`, `CLAUDE.md`, `README.md`, `code/RUNLOG.md` | Order, C description, new circuits, changelog |

Build order: C (AC-1 to AC-7) → B1 (AC-8) → D1, D2, D3 (AC-11 to AC-13) → the rest.

---

## 7. Manual Verification (No Tests)

- [x] **Verify AC-1, AC-2:** `python main.py` (dry). Log shows `[C_certificate]` first, one job of 4 circuits;
  `certificate.json` has 6 pair rows with S and sigma, status "certification-ready, not certified (simulated)".
- [x] **Verify AC-3:** set `MIN_PAIRS = 99`, dry run → exit code 7, no `certified_bits.bin`, no `cohort_params.json`.
  Restore the constant.
- [x] **Verify AC-4, AC-5:** `certified_bits.bin` exists; `budget.spent` lists `roll` and the D circuit's labels;
  the sum is at most `budget.available`. Run again with `--run <dir>` → identical cohort.
- [x] **Verify AC-6:** dry run of D `R3-TEST`: the pairs in `result.json` are the highest-S pairs of `pair_map`.
- [x] **Verify AC-7:** open the page: certificate line shows pairs, bits available, bits spent.
  `python -m G_provenance.main <run>` passes; flip one byte of `certified_bits.bin` → it fails.
- [x] **Verify AC-8:** dry run: no "roll: SUBMITTED" line; `cohort_params.json` has 4 tumours. With 2,000 draws in
  a Python shell the type frequencies match the rulebook within sampling error.
- [x] **Verify AC-9:** B `CIRCUIT = "R2-MAP"`, dry → 3 tiles, claim "(dry run: not a claim)".
- [x] **Verify AC-10:** B `R5-H12`, dry → `result.json` has per-parity pass rates; only even-weight inputs.
- [x] **Verify AC-11:** `jobs/*.npz` present for every job; shapes equal (shots, qubits).
- [x] **Verify AC-12, AC-13:** D `R5-LADDER`, dry → `loss_per_cz.json` has `lam` and `readout_loss_per_qubit`;
  then D `R6a-S36`, dry → log shows the forecast line; `analysis.json` has `l2_distance`.
- [x] **Verify AC-14, AC-15:** D `R1-TILE24` dry → two claims; D `R3-TEST` dry → 10 shots per circuit.
- [x] Whole pipeline dry run stays under 3 minutes (2 min 3 s, `research_runs/run_dry_20261115-084305`).
- [ ] Live (Peter): one run with B `R2-MAP`, D `R5-LADDER` on the best backend available; compare the Bell map
  with the ring the layout picked.

---

## 8. Open Questions

- [x] **Q1:** Remove the quantum roll circuit, or keep it as a legacy choice? *Proposed:* remove. It is 642 CZ,
  noise-dominated, and its sibling-pair entanglement was never certified.
- [x] **Q2:** Is changing the section order to C, B, D acceptable (CLAUDE.md says B C D)? *Proposed:* yes; C
  cannot feed B otherwise.
- [x] **Q3:** Hexagon game score: all parities (strict, today) or the single published parity? *Proposed:* keep
  strict as the claim until 2110.04277 Sec. III is read in the PDF; report both.
- [x] **Q4:** Which backends are open to you besides `ibm_fez` (kobe, aachen, kingston, boston)? *Proposed:* run
  the ring circuits on the best of them; keep R1, R2, R3 on fez for continuity with the log.
- [x] **Q5:** May R4's blocker `true_random_inputs` be lifted when inputs come from the Bell-test pool of the same
  chip? *Proposed:* rename it to "inputs: Bell-test bits of the same device (setting-independence loophole open)";
  R4 stays unable to pass until G9 is closed.
- [x] **Q6:** Bell-map size: 3 matchings (most edges, 12 circuits, about 4 QPU-s) or 1 matching (4 circuits)?
  *Proposed:* 3, because the edge coverage is what makes the map useful for rings.
- [x] **Q7:** One feature or three (C, B, D)? *Proposed:* one plan, implemented in the build order of section 6,
  with a stop after C + B1 for a first live run.

---

Resolved 2026-11-14: every *Proposed* answer above is the decision. Q4 stays open as a fact to supply (which
backends are available); the default holds until then. Further candidate circuits for B, C and D are planned
additively in [feature-QCAND-candidate-circuits-B-C-D.md](feature-QCAND-candidate-circuits-B-C-D.md).

---

## 9. Post-Implementation Notes

Built 2026-11-15, on `main`, verified by dry runs on FakeMarrakesh only (run `run_dry_20261115-084305` plus
hand runs of `R2-MAP`, `R1-TILE24`, `R5-LADDER`, `R6a-S36`, the stop rule and a continued run). No hardware job.

Deviations from the plan, each small:

- **Dry stop rule.** The dry Bell map has 6 pairs, so `MIN_PAIRS = 8` could never pass there. Added
  `DRY_MIN_PAIRS = 4`. Verification of AC-3 set both constants to 99.
- **Extractor seed.** 32 bytes of `os.urandom`, expanded with SHAKE-256 to the Toeplitz length, in place of a
  full-length random seed (which would be about 70 kB of hex in the certificate on a live run). The certificate
  says so. This is a computational expansion.
- **`Q.rng` and the pool.** Each `Q.rng(ctx, name, label)` draws 64 pool bits (budget label `<name>/<label>`) and
  expands them with PCG64. Random inputs are therefore a pseudo-random expansion of a quantum seed, not pool bits
  one for one: R3-TEST alone would need about 160,000 bits against a pool of 4,096.
- **Unmeasured couplers in a ranking** count as the map's median S, so a ring is not preferred for avoiding the
  map. A measured coupler with S <= 2 is never a pair tile.
- **Pruning unchanged.** `common/allocate.prune` still uses calibration; the Bell map changes ranking only.
- **Ladder: one job per rung** (6 live), not one job for the section.
- **R2-MAP qubits** are the best readouts of the pruned chip (no CZ in the circuit, so the pair map does not rank
  them).
- **Sibling pair.** The daughter copies each property and redraws it with probability 0.044 (what a 2-qubit
  field of the old division circuit gave at theta = 0.3).
- **Selection bias.** The pooled S is taken over pairs selected on the same data. The scope text says so; no
  correction is applied.
- Extra, not in the file plan: `B_mapping/xeb.py` (inputs from the pool, Q5), `F_render/main.py` (honest label),
  `G_provenance` also hashes `jobs/*.npz`, the page labels a dry run as simulated (it showed "real hardware").
  `bits_to_params` is kept unused for QCAND's B-IQP.

Found while verifying:

- The ring forecast is optimistic: on the dry backend it gave fidelity 0.75 for the 12-ring at depth 6 and the
  ring measured 0.29. The ladder's lam read 0.004 there. Treat "go" as necessary, not sufficient.
- Dry `R3-TEST` now runs on 4 pairs (6 certified pairs, size 8 left out) and cannot pass at that size (bound 1).
- `ctx.qpu_spent` is still not persisted across `--run` (unchanged, noted by the exploration).

Follow-ups: first live run (RUNLOG "Next" item 0); QCAND builds on `runio.draw_bits`, `tg.meta["pair_map"]`,
`qhard.bell_deficit`, `jobs/*.npz` and `qhard/loss_per_cz.json` as they now exist.

---

## Sources (read through summaries on 2026-11-14; verify in the PDFs before citing)

- 2509.07255, Demonstrating an unconditional separation between quantum and classical information resources
- 2510.25838, Heuristic Quantum Advantage with Peaked Circuits; IBM blog "Quantum Advantage Tracker" (2026-02-23)
- 2510.09520, Big cats: entanglement in 120 qubits and beyond
- 2406.17841, Probing many-body Bell correlation depth with superconducting qubits
- 2609.40050, Unconditional quantum advantage with noisy planar architectures
- Liu et al., Certified randomness using a trapped-ion quantum processor, Nature 640, 343 (2025)
- Pironio et al., Random numbers certified by Bell's theorem, Nature 464, 1021 (2010)
