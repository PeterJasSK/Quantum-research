# Feature C — Certificate: CHSH → certified bits → extracted seed (targets #4, #5)

**Epic:** [`epic-reverse-engineering.md`](./epic-reverse-engineering.md) (Approved, 2026-10-28). C is a wave-1 letter (epic §7), built in its own worktree `re-C`. It depends only on W (complete, committed at `a2ff3dc`).
**Feature ID:** C
**Author:** Claude (Opus)
**Date:** 2026-10-28
**Status:** Complete (implemented 2026-10-28 in worktree `../qp-re-C`, branch `re-C`; approved with all Q1–Q7 defaults)

> **Technical constraints / core directive.**
> - **Stack.** Python 3.13 (conda base) with the libraries already installed: qiskit 2.3.1, qiskit-aer 0.17.2, numpy 2.4, scipy 1.15, matplotlib 3.10, cryptography 44, requests 2.34, jsonschema 4.23. **No new installs.**
> - **Simulation only.** Use `AerSimulator`, ideal and `FakeMarrakesh` noise, both through `shared.simbackend`. No IBM jobs.
> - **Scope of writes.** The session writes only inside `RE/C_certificate/` and this plan, where `RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`. `shared/` is frozen and is imported, never edited. Nothing is imported from `QuantumPhantoms/code/` (the MVP) or from any other letter.
> - **Commands** run with `RE/` as the working directory.
> - **Honesty label.** Every certificate is "certification-ready, not certified (simulated)", claim level L0.
> - **No automated tests.** Verification is manual, plus the paper reproductions.

---

## 1. Why (Step Goal)

**Before.**
- `C_certificate/` is a W skeleton: a pre-filled README, `status.json` with #4 and #5 at `listed`, and two empty dossiers.
- Downstream letters (D, E, F, G, H) can only read the **stub** certificate. Its S = 2.7, H_min and seed are placeholders, and nothing computes them.
- "CHSH > 2" is still only a label, as in the MVP. Nothing turns a Bell value into a *number of certified bits* or into an *extracted seed*. Test-round choice has no external source, and there is no studied template for the G ledger.

**After.** C provides a standalone, reproducible accounting pipeline. It is validated on simulated data only:
1. **Target #4, Bell entropy accounting (Pironio C01; Vazirani–Vidick C05; Liu C02 read-only).**
   - Generate a spot-checked CHSH round schedule with hidden test rounds.
   - Run it on Aer (ideal and Heron-class noise).
   - Estimate S and a finite-statistics lower bound S_low.
   - Compute H_min per round from Pironio's bound f(S) = 1 − log₂(1 + √(2 − S²/4)), then the number of certified bits.
   - Run a Toeplitz (two-universal) extractor into a 256-bit seed.
   - Write a contract-valid `certificate.json` + `quantum_job_record.json`.
   - S ≤ 2 gives a `fail` certificate with no seed, logged, with no retry and no fallback (epic decision 6).
   - **Reproduce:** the Pironio H_min-vs-S curve and Pironio's published finite-statistics result (certified bits from their measured events), then the same accounting applied to our simulated S.
2. **Target #5, CURBy / NIST beacon chain (Kavuri C04).**
   - Dissect the hash-chained, signed pulse format.
   - Verify a cached chain of real public pulses offline and show that tampering breaks it.
   - Use one pulse's output as the **external seed for the hidden test-round mask** (`curby_pulse_id` in the certificate).
   - Write the field-by-field mapping that G will reuse as its ledger template.
3. **Docs and status.** C's README, both dossiers, figures and `status.json` are updated, so the site shows #4 and #5 at their reached lifecycle state.

Every later seed in the epic (E's and F's PRNGs, G's receipt) can then come from a real C output instead of the stub. INT does that swap.

---

## 2. Acceptance Criteria

- [x] **AC-1** (C.1) — *Entropy bound + finite statistics.*
  - `f_hmin(S)` implements Pironio's bound. It returns 0 for S ≤ 2 and 1 at S = 2√2, and it is monotone in between.
  - `chsh_estimate(rounds)` returns Ŝ and the four correlators E_xy from the test rounds only.
  - `s_lower_bound(rounds, eps_est)` returns S_low = Ŝ − Σ_xy δ_xy, where δ_xy = √(2 ln(8/ε_est) / n_xy) (Hoeffding on each E_xy ∈ [−1, 1], union bound over 4 correlators × 2 sides).
  → `C_certificate/src/entropy.py`.
- [x] **AC-2** (C.2) — *Spot-checked CHSH rounds on Aer.*
  - **Schedule.** N rounds (default 100 000). Each round is a test round with probability q (default 0.2). A test round draws uniform settings (x, y) ∈ {0,1}². A generation round uses the fixed setting (0, 0).
  - **Source of the mask and test settings.** Both come from `shared.seedhash.rng(pulse_seed_hex, "C.test_mask")`. `pulse_seed_hex` = sha256 of the CURBy pulse output value (AC-7).
  - **Circuits.**
    - The 4 setting circuits are |Φ⁺⟩ with CHSH-optimal measurement angles (A: 0, π/2; B: π/4, −π/4).
    - Each is transpiled to `FakeMarrakesh` via `shared.simbackend.transpile_heron`.
    - Each runs once on `make_simulator(mode, seed=…)` with `shots` = number of rounds at that setting and `memory=True`.
    - The per-shot outcomes are re-assembled into round order.
  - **Run directory.** `rounds.npz` holds the arrays `x, y, a, b, test` (uint8, length N).
  - **Classical control.** A `--settings classical` flag measures all settings in Z, which gives S ≤ 2. It exists only to exercise the fail path.
  → `C_certificate/src/chsh.py`.
- [x] **AC-3** (C.3) — *Certified bits.*
  - Let n_gen = N − n_test.
  - h = f(S_low).
  - `certified_bits` = ⌊n_gen · h⌋, where the raw input is 2 bits (a, b) per generation round, so `extractor.input_bits` = 2·n_gen.
  - Toeplitz output length L = 256 (fixed seed size). The run requires `certified_bits − 2·log₂(1/ε_ext) ≥ 256`, with ε_ext = 1e-6.
  - The full accounting (Ŝ, E_xy, n_xy, δ, S_low, h, ε_est, ε_ext, n_gen, certified_bits, L) is written to `accounting.json` in the run directory.
  → `C_certificate/src/entropy.py` + `src/certify.py`.
- [x] **AC-4** (C.4) — *Toeplitz extraction.*
  - `toeplitz_extract(bits, out_len, seed_bits)` multiplies over GF(2) by an `out_len × m` Toeplitz matrix built from m + out_len − 1 seed bits. It uses `numpy.lib.stride_tricks.sliding_window_view` with an int matmul and `% 2`, so there is no dense m-wide Python loop.
  - The extractor seed bits are SHAKE-256 of `pulse_output_value ‖ b"C.toeplitz"`. The extractor seed is public (strong extractor). This is documented in dossier #4.
  - The 256 output bits become `extracted_seed_hex` (64 hex characters).
  → `C_certificate/src/toeplitz.py`.
- [x] **AC-5** (C.5) — *Contract outputs.*
  - `python -m C_certificate.src.certify --mode {ideal|heron}` writes a run dir `C_certificate/runs/<ts>-chsh-<mode>/` through `shared.runrecord.start_run`. It contains: `run.json`, `counts_<job>.json`, `quantum_job_record.json`, `certificate.json`, `accounting.json`, `rounds.npz`, `test_round_mask.json`.
  - `quantum_job_record.json`:
    - `counts` is keyed `"xy ab"` (for example `"01 10"`); the space-separated form is allowed by the schema pattern.
    - `test_round_mask` is a file_ref to `test_round_mask.json` = `{n, mask_hex}` (packbits).
    - `transpiled_hash` = sha256 of the canonical JSON list of the 4 per-setting `circuit_hash` values (documented, see Contract change requests).
    - `sim_label` and `hardware: null` as the envelope requires.
  - `certificate.json`:
    - `chsh_S` = Ŝ, `h_min_per_round` = f(S_low), `curby_pulse_id`, `job_record_ref` and `upstream` pointing at the job record.
    - `certification_status` and `claim_level` take the constant values.
  - Both files pass `python -m shared.validate <file>`.
- [x] **AC-6** (C.6) — *Fail path (epic decision 6).*
  - If S_low ≤ 2 (see Q1), the certificate is written with `status: "fail"` and `extracted_seed_hex: null`, and no extraction runs.
  - The same happens if the entropy is too small for 256 bits (see Q2).
  - The reason goes into `accounting.json` (`fail_reason`) and the `run.json` notes, and one line is appended to `C_certificate/runs/rejections.jsonl`.
  - There is no retry, no re-draw of the pulse and no fallback.
  - `--settings classical` demonstrates the fail path, and its certificate validates.
- [x] **AC-7** (C.7) — *CURBy / beacon pulses (target #5).*
  - `C_certificate/src/beacon.py` loads pulses from the committed cache `C_certificate/repro/data/beacon_pulses.json`.
  - It verifies the chain: each pulse's link to its predecessor, the output-value hash recomputation, and the signature where the source publishes the public key/certificate.
  - It exposes `pulse_seed_hex(pulse)` and `pulse_id(pulse)`.
  - `python -m C_certificate.repro.fetch_pulses` is the **only** network-touching command. It fetches ≥ 10 consecutive pulses once (CURBy if reachable, otherwise NIST Beacon 2.0, see Q3) and writes the cache. Every other command is offline.
- [x] **AC-8** (C.8) — *Reproduction #4 (Pironio).*
  - `python -m C_certificate.repro.pironio` writes `C_certificate/figures/hmin_vs_S.png`. It shows the f(S) curve on [2, 2√2], with our ideal and Heron Ŝ / S_low marked and each point labelled "simulated: ideal" or "simulated: Heron-class noise (FakeMarrakesh)".
  - It recomputes Pironio's finite-statistics certified-bit count from their published event count and CHSH estimate, using their own finite-statistics formula transcribed from C01 (Methods).
  - It prints paper value vs ours. Agreement: an exact integer match, or a deviation ≤ 20 % explained in dossier #4.
  - The result goes into `status.json` #4 `reproduced{}`.
- [x] **AC-9** (C.9) — *Reproduction #5 (beacon chain).*
  - `python -m C_certificate.repro.beacon_chain` verifies every link of the cached chain and prints `chain OK (n links)`.
  - It then flips one byte of one cached pulse in memory and shows that verification fails at that index.
  - It writes `C_certificate/figures/beacon_chain.png` (pulse index vs link-valid).
  - The result goes into `status.json` #5 `reproduced{}` (quantity "consecutive pulse links verified").
- [x] **AC-10** (C.10) — *Dossiers.*
  - `dossiers/04-bell-entropy-accounting.md` and `05-curby-beacon-chain.md` fill all 8 fixed sections.
  - Dossier #4 states the assumptions honestly:
    - i.i.d. / Hoeffding finite statistics, not the full entropy accumulation theorem (EAT);
    - a single chip is not loophole-free;
    - "simulated CHSH certifies nothing";
    - Liu C02 (XEB, L2) is read only.
  - Dossier #5 ends with the **ledger template for G**: a table that maps beacon/CURBy fields (index, previous-output hash, output hash, signature, timestamp, certificate id) to our `LedgerEntry` / `Receipt` fields.
- [x] **AC-11** (C.11) — *README + status.*
  - `C_certificate/README.md` fills "How to run", "Reproduced result vs. paper" (with sim labels), "Claim level" and "Contract change requests" (CCR-C1, CCR-C2, see §5).
  - `status.json` moves #4 and #5 to `adapted`, or to `reproduced` if adaptation stops short. Each gets `reproduced{}`, `claim_level` (#4 `L0`, #5 `n/a`), `sim_mode` (#4 `both`, #5 `n/a`), `figures[]`, and `updated`.
  - `python -m shared.validate --status` passes.
  - `python -m shared.site.build` previews locally. The generated site is **not** committed (only INT commits it).

---

## 3. Out of Scope (Postponed)

- **Dynamic-circuit CHSH interleaved with lineage generations in one job** (D-2): belongs to **D**. C validates the accounting on standalone CHSH rounds only.
- **Signing receipts, the Ed25519 ledger, the DICOM tag and the commit-before-draw flow:** these belong to **G**. C delivers only the format study and the mapping table (AC-10).
- **Feeding the extracted seed into E's and F's PRNGs, and the end-to-end chain:** **INT**. E and F keep using the stub certificate until then.
- **Certificate statistics across a cohort:** **H**.
- **Full entropy accumulation theorem / device-independent randomness expansion** (C06, C07) and **XEB certified randomness** (Liu C02, L2): read only. They are noted in dossier #4 as future work.
- **Real hardware CHSH (actual certification):** future work, outside the epic (decision 4).
- **Any change to `shared/`** (contracts, stubs, validator): requested through the README's Contract change requests and applied in **INT**.
- **Committing `index.html` / `site/`:** **INT** only.

---

## 4. Technical Decisions

Epic §3 and the frozen W decisions are adopted as-is: sim-only, the `FakeMarrakesh` reference, file-only contracts, the ownership rules, honesty gates, the seed chain, logging, and no tests.

| Component | Choice / Implementation |
|---|---|
| Entropy bound | Pironio C01: f(S) = 1 − log₂(1 + √(2 − S²/4)), applied to the pair (a, b) given (x, y) |
| Finite statistics (our pipeline) | Hoeffding per correlator, union bound, ε_est = 1e-6; certify with f(S_low), not f(Ŝ) |
| Finite statistics (reproduction) | Pironio's own formula from C01 Methods, used only in `repro/pironio.py` |
| Protocol | Spot-checking (Vazirani–Vidick C05 style): test probability q = 0.2, generation setting (0, 0) |
| Rounds model | One shot = one round. 4 setting circuits, `memory=True`, re-ordered by the schedule. N = 100 000 by default |
| Aer seeds | `derive_seed(pulse_seed_hex, f"C.aer.{mode}.{x}{y}")` |
| Extractor | GF(2) Toeplitz, L = 256, ε_ext = 1e-6 (leftover hash lemma: L ≤ H − 2 log₂(1/ε)); seed from SHAKE-256 of the pulse |
| External randomness | Committed cache of real public beacon pulses. One explicit fetch command; everything else offline |
| Run records | `shared.runrecord.start_run("C_certificate", f"chsh-{mode}", sim_mode=mode, seed_hex=<extracted or None>)` |
| Figures | matplotlib → PNG in `C_certificate/figures/` (committed) |

**Conventions & Notes:**
- Only `shared.simbackend` is used for simulators and transpiling. C does not construct `FakeMarrakesh` itself.
- **Module split.** The modules `entropy`, `toeplitz` and `beacon` stay qiskit-free; only `chsh` imports qiskit.
- **Pattern-only analogues (read, never import):**
  - `THESIS/CertifiedEntropyProvenance/proof_of_concept/quantum_certified_qrng.py:92` `toeplitz_extract`;
  - `study-ideas/QuantumAlgorithmsExplained/code/11_chsh.py:43` CHSH angles.

  The MVP `QuantumPhantoms/code/f1_quantum/certify.py` is off-limits.
- **Scale check.** Re-assembling 100 k rounds and a 256 × 160 k GF(2) product (≈ 41 M int ops) is well within CPU and RAM. No Aer statevector width concern (2 qubits, transpiled onto the 156-qubit target).
- **Expected magnitudes**, for sanity, not as ACs:
  - ideal: Ŝ ≈ 2.83 and S_low ≈ 2.5, giving h ≈ 0.28 and ≈ 22 k certified bits;
  - Heron noise: Ŝ ≈ 2.6–2.7 and S_low ≈ 2.3, giving h ≈ 0.15 and ≈ 12 k bits.

  Both are far above 256 + 40.
- **Note for the epic (§4):** the epic's `QuantumJobRecord` has a single `transpiled_hash`, but C needs 4 setting circuits. C hashes the list (AC-5) and files CCR-C1.

---

## 5. Data Model (Additions/Modifications)

No contract is added or changed (`shared/` is frozen). C produces instances of the existing W contracts, plus letter-local run files. Those files are not contracts and are not consumed by other letters.

```text
[Existing contract — produced by C]  certificate.json        (shared/contracts/certificate.schema.json v1.0.0)
  chsh_S            = Ŝ (point estimate from test rounds)
  h_min_per_round   = f(S_low)                  (conservative; differs from f(chsh_S) — see CCR-C2)
  certified_bits    = floor(n_gen · h_min_per_round)
  extractor         = {kind "toeplitz", input_bits 2·n_gen, output_bits 256 | 0 on fail}
  curby_pulse_id    = "<source>:<chain>:<index>"   (e.g. "nist:2:1234567" or CURBy id)
  status / extracted_seed_hex per AC-6

[Existing contract — produced by C]  quantum_job_record.json (quantum_job_record.schema.json v1.0.0)
  counts            {"xy ab": int}              (settings + outcomes, test and generation pooled)
  test_round_mask   file_ref → test_round_mask.json
  transpiled_hash   sha256(canonical_json([circuit_hash(x,y) for xy in 00,01,10,11]))

[Letter-local, run dir only]
  accounting.json        {S_hat, E_xy{}, n_xy{}, delta_xy{}, S_low, eps_est, eps_ext, n_rounds, n_test,
                          n_gen, h_min_per_round, certified_bits, out_len, fail_reason|null,
                          pulse{source, id, output_sha256}, sim_label}
  rounds.npz             x, y, a, b, test   (uint8, length N)
  test_round_mask.json   {n, mask_hex}
  extracted.bin          256 bits (pass only)
  C_certificate/runs/rejections.jsonl   {run_id, created_utc, mode, S_hat, S_low, fail_reason}

[Letter-local, committed]
  C_certificate/repro/data/beacon_pulses.json   {source, fetched_utc, api_url, public_key|cert?, pulses[]}
```

**Contract change requests** (recorded in the README; INT decides):
- **CCR-C1:** `quantum_job_record` gets an optional `transpiled_hashes[]` (one per circuit) for multi-circuit jobs.
- **CCR-C2:** `certificate` gets `chsh_S_lower` and `eps` {est, ext}, so consumers can recompute `h_min_per_round` from the record itself. The validator could then check h = f(S_lower) and certified_bits.

---

## 6. File Plan (Concrete Changes)

`RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`. Everything is inside `RE/C_certificate/` except this plan.

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/C_certificate/src/entropy.py` | `f_hmin`, `chsh_estimate`, `s_lower_bound`, `certified_bits`, `extractable_len` (AC-1, AC-3); qiskit-free |
| New | `RE/C_certificate/src/toeplitz.py` | `expand_seed_bits(pulse_bytes, n)` (SHAKE-256), `toeplitz_extract` (AC-4) |
| New | `RE/C_certificate/src/chsh.py` | `setting_circuit(x, y, classical=False)`, `make_schedule(n, q, rng)`, `run_rounds(mode, schedule, pulse_seed_hex)` → rounds + 4 circuit hashes + counts (AC-2) |
| New | `RE/C_certificate/src/beacon.py` | `load_cache`, `verify_chain` (link + hash + signature where available), `pulse_id`, `pulse_seed_hex` (AC-7); qiskit-free |
| New | `RE/C_certificate/src/certify.py` | CLI `python -m C_certificate.src.certify --mode ideal\|heron [--rounds N] [--test-frac q] [--pulse-index i] [--settings quantum\|classical]`; orchestrates run → accounting → extract → writes contracts + run record; fail path + `rejections.jsonl` (AC-3, AC-5, AC-6) |
| New | `RE/C_certificate/repro/fetch_pulses.py` | one-shot network fetch of ≥ 10 consecutive pulses into the cache (AC-7) |
| New | `RE/C_certificate/repro/data/beacon_pulses.json` | committed pulse cache (generated once by `fetch_pulses`) |
| New | `RE/C_certificate/repro/pironio.py` | curve figure + Pironio finite-statistics reproduction; reads the latest ideal/heron `accounting.json` if present (AC-8) |
| New | `RE/C_certificate/repro/beacon_chain.py` | chain verification + tamper demonstration + figure (AC-9) |
| New | `RE/C_certificate/figures/hmin_vs_S.png` | generated by `repro/pironio.py`, committed |
| New | `RE/C_certificate/figures/beacon_chain.png` | generated by `repro/beacon_chain.py`, committed |
| Modify | `RE/C_certificate/dossiers/04-bell-entropy-accounting.md` | fill all 8 sections (AC-10) |
| Modify | `RE/C_certificate/dossiers/05-curby-beacon-chain.md` | fill all 8 sections + G ledger mapping table (AC-10) |
| Modify | `RE/C_certificate/README.md` | How to run, reproduced results (sim-labelled), honesty, CCR-C1/C2 (AC-11) |
| Modify | `RE/C_certificate/status.json` | #4/#5 lifecycle, `reproduced{}`, claim level, sim mode, figures (AC-11) |
| Modify | `RE/feature-C-certificate.md` | §9 Post-Implementation Notes only |

**Untouched:** `shared/`, the other letters, the epic, the targets list, `about.html`, `index.html`, `site/`, `.gitignore`, and the MVP.

---

## 7. Manual Verification (No Tests)

All commands run from `RE/` (inside the `re-C` worktree) with the conda base `python`.

- [x] **Verify AC-1:** run `python -c "from C_certificate.src.entropy import f_hmin; print(f_hmin(2.0), f_hmin(2.7), f_hmin(2*2**.5), f_hmin(1.5))"`. Expected output: `0.0 ≈0.4928 1.0 0.0`. The value 0.4928 matches the stub certificate's `h_min_per_round`.
- [x] **Verify AC-2:** after an ideal run, run `python -c "import numpy as n; d=n.load('<run>/rounds.npz'); print(len(d['a']), d['test'].mean())"`. Expected: `100000` and ≈ 0.20. In generation rounds, x = y = 0 everywhere.
- [x] **Verify AC-3 / AC-5 (ideal):** run `python -m C_certificate.src.certify --mode ideal`. Expected:
  - Ŝ ≈ 2.83, S_low > 2, status `pass`;
  - `python -m shared.validate <run>/certificate.json` and `<run>/quantum_job_record.json` both print OK;
  - `certified_bits == floor(n_gen*h)` when checked by hand from `accounting.json`.
- [x] **Verify AC-5 (heron):** run the same with `--mode heron`. Ŝ should be below the ideal value, the certificate should still pass, and `sim_label` should read `simulated: Heron-class noise (FakeMarrakesh)`.
- [x] **Verify AC-4:** re-run the same mode and pulse. The `extracted_seed_hex` is identical (deterministic). Run again with `--pulse-index` set to a different pulse: the seed differs. Flip one generation bit in a copy of `rounds.npz` and re-extract through `toeplitz_extract`: about half of the output bits change.
- [x] **Verify AC-6:** run `python -m C_certificate.src.certify --mode ideal --settings classical`. Expected:
  - Ŝ ≤ 2, `status: "fail"`, `extracted_seed_hex: null`;
  - the certificate validates;
  - one new line in `runs/rejections.jsonl`;
  - no `extracted.bin`;
  - the exit code is 0 (a rejection is a logged outcome, not a crash).
- [x] **Verify AC-7:** disconnect the network and run `certify`. It still works from the cache. `grep -rn "requests" C_certificate/src` prints nothing; only `repro/fetch_pulses.py` imports it.
- [x] **Verify AC-8:** run `python -m C_certificate.repro.pironio`. It prints Pironio's paper value vs ours with the deviation, and `figures/hmin_vs_S.png` shows the curve with the ideal and Heron points labelled.
- [x] **Verify AC-9:** run `python -m C_certificate.repro.beacon_chain`. It prints `chain OK (n links)`, then reports a failure at the tampered index.
- [x] **Verify AC-10 / AC-11:** open both dossiers: all 8 sections are filled and the G mapping table is present. Run `python -m shared.validate --status`: 8 × OK. Run `python -m shared.site.build` and open `index.html` locally: #4 and #5 show the new badges. Then run `git status --short index.html site/` and discard the changes; nothing from the site is committed.
- [x] **Edge case — isolation:** `grep -rnE "QuantumPhantoms/code|from (A|B|D|E|F|G|H)_" C_certificate/` prints nothing. `git diff --stat main -- shared/` is empty.
- [x] **Edge case — honesty:** `grep -c "simulated" C_certificate/README.md` is non-zero. No file says "certified" without "not certified (simulated)" or "certification-ready" nearby.

---

## 8. Open Questions

- [x] **Q1: Should pass/fail be gated on Ŝ or on S_low?** Decision 6 says "S ≤ 2 → reject". The schema checks only `chsh_S > 2` for a pass. *Resolved (accepted default):* gate on **S_low > 2**, the conservative finite-statistics bound. `chsh_S` stays the point estimate Ŝ, so a pass always also satisfies the schema.
- [x] **Q2: What happens if S_low > 2 but there is too little entropy for a 256-bit seed?** *Resolved (accepted default):* treat it as a second fail reason, `"insufficient entropy"`, with the same rejected-and-logged handling and no retry. With the default N = 100 000 it should not occur in either sim mode.
- [x] **Q3: May C touch the network at all (one fetch of public beacon pulses)?** Is CURBy preferred over NIST? *Resolved (accepted default):* yes, once, through `repro/fetch_pulses.py`, with the result committed as a small JSON cache. Try CURBy (random.colorado.edu, endpoint taken from C04 and the site) first. Fall back to NIST Beacon 2.0 (`https://beacon.nist.gov/beacon/2.0/…`), whose chained and signed format is fully documented. Record which source was used. If the developer prefers zero network access, the cache is built by hand from pulses the developer downloads.
- [x] **Q4: Should the C outputs that downstream letters need be committed?** `runs/` is gitignored. *Resolved (accepted default):* no. Outputs are deterministic from the cached pulse and the sim seeds, and INT regenerates them by running the README commands.
- [x] **Q5: How exact must the Pironio reproduction be?** *Resolved (accepted default):* transcribe their finite-statistics formula from C01 Methods. The target is their published certified-bit count from their event count and CHSH estimate (the implementer confirms these numbers in the PDF). Accept an exact match, or a deviation ≤ 20 % explained in the dossier. The analytic curve itself must match to floating-point precision.
- [x] **Q6: Which default parameters?** *Resolved (accepted default):* N = 100 000, q = 0.2, ε_est = ε_ext = 1e-6, L = 256, generation setting (0, 0). All are CLI-overridable and recorded in `accounting.json`.
- [x] **Q7: Where should this plan live?** *Resolved (accepted default):* `RE/feature-C-certificate.md`, following the epic §3 layout and the W precedent, not `tasks/plans/`. It is written on `main` now. Create the worktree with `git worktree add ../qp-re-C -b re-C` after committing this plan, or carry it over uncommitted, before `/implement-feature`.

---

## 9. Post-Implementation Notes

**Built (2026-10-28, worktree `../qp-re-C`, branch `re-C`, uncommitted at hand-back).**
- 5 source modules in `src/`.
- 3 repro scripts + 1 fetch script in `repro/`.
- A committed pulse cache (60 KB).
- 2 figures.
- Both dossiers, the README and `status.json` (#4 and #5 → `adapted`).

Nothing outside `C_certificate/` was touched except this plan. `shared/` is unchanged and the site preview was discarded.

**AC evidence** (paths relative to `RE/C_certificate/`):

| AC | Evidence |
|---|---|
| AC-1 | `src/entropy.py:21` `f_hmin`, `:34` `chsh_estimate`, `:47` `s_lower_bound` |
| AC-2 | `src/chsh.py:26` `setting_circuit`, `:37` `make_schedule`, `:45` `run_rounds` (memory=True, round re-assembly); `src/certify.py:68` mask RNG from the pulse |
| AC-3 | `src/entropy.py:54` `certified_bits`, `:58` `extractable_len`; `src/certify.py:91-103` accounting + `accounting.json` |
| AC-4 | `src/toeplitz.py:17` `expand_seed_bits` (SHAKE-256), `:23` `toeplitz_extract` (sliding_window_view, int32 matmul % 2); `src/certify.py:106-112` |
| AC-5 | `src/certify.py:62` `certify`; job record `:79-87`, certificate `:127-134`, contract check `:137-138` |
| AC-6 | `src/certify.py:99-103` fail reasons, `:144` `rejections.jsonl`; `--settings classical` → `src/chsh.py:30` |
| AC-7 | `src/beacon.py:42` `serialize`, `:58` `verify_pulse`, `:70` `verify_chain`, `:101` `select_verified_pulse`; `repro/fetch_pulses.py:27`; `repro/data/beacon_pulses.json` |
| AC-8 | `repro/pironio.py:34` Table 1 Î, `:53` main; `src/entropy.py:63` `pironio_epsilon`, `:68` `pironio_bits`; `figures/hmin_vs_S.png` |
| AC-9 | `repro/beacon_chain.py:32` (chain OK + tamper + CURBy check); `figures/beacon_chain.png` |
| AC-10 | `dossiers/04-bell-entropy-accounting.md`, `dossiers/05-curby-beacon-chain.md` (§Adaptation "Ledger template for G") |
| AC-11 | `README.md` (How to run, Reproduced, honesty, CCR-C1..C3); `status.json` |

**Manual verification run (all passed):**
- `f_hmin` gives 0 / 0.492781 / 1 / 0 for S = 2 / 2.7 / 2√2 / 1.5. The 0.492781 matches the stub certificate.
- The ideal run gives Ŝ 2.8058, S_low 2.4868 and 20 551 bits, pass.
- The Heron run gives Ŝ 2.7037, S_low 2.3847 and 14 726 bits, pass. It takes about 20 s; the ideal run takes about 3 s.
- The classical run gives Ŝ 2.0000 and S_low 1.681: fail, null seed, one `rejections.jsonl` line, exit 0.
- All `certificate.json`, `quantum_job_record.json` and `run.json` files print `OK` under `shared.validate`. `--status` passes for all 8 letters.
- `rounds.npz` holds 100 000 rounds with test fraction 0.200, and every generation round is at (0, 0). `certified_bits == ⌊n_gen·h⌋`.
- The same pulse gives an identical seed `2acab707…`; `--pulse-index 5` gives a different one. A 1-bit input flip changes 136/256 output bits.
- Pironio: Î from Table 1 = 2.4145. We get 40.8 bits vs the paper's 42 (−2.8 %), within the 20 % bound of Q5.
- Beacon: 12 pulses / 11 links OK. The tamper is caught at pulse #6 (signature, output, precommit).
- `src/` contains no `requests`. The isolation grep is clean, and `git diff HEAD -- shared/` is empty. pyflakes is clean.

**Deviations from the plan:**
1. **Beacon source is NIST Beacon 2.0, not CURBy** (Q3's fallback branch). CURBy is reachable, but:
   - its blocks are IPLD dag-cbor, so recomputing a CID needs a library that is not installed;
   - its latest round is dated 2025-08-22 and its request block is flagged `isQuantum: False`.

   CURBy is cached as a format sample, and its link-by-CID and parameters (512 / 820) are checked. The NIST pulses are fully verified: RSA signature, SHA-512 output, previous link and precommitment. The serialization was confirmed against live pulses. `curby_pulse_id` holds `nist:2:<index>` (CCR-C3).
2. **Aer seeds.** We use `sim_seed = derive_seed(pulse_seed, "C.aer.<mode>") mod 2³¹`, and setting k uses `sim_seed + k`, instead of one derived seed per setting. The job record has a single `sim_seed` field, so the per-setting seeds can be reconstructed from it (CCR-C1 note).
3. **`chsh_S` clipping.** It is clipped to 2.8284 because the schema maximum is 2.8285 and an ideal-run Ŝ reached 2.8365 on another pulse. The raw Ŝ is in `accounting.json` (CCR-C2).
4. **Foreground exploration agent skipped.** The planning-time survey covered all integration points; every C file is new and only `shared/` APIs are consumed. The `shared/` modules were re-read directly before coding.

**Follow-ups:**
- Commit on `re-C` and merge to `main`. The C folder is disjoint from A, E and F.
- INT decides on CCR-C1 (multi-circuit `transpiled_hashes[]`), CCR-C2 (`chsh_S_lower`, `eps`, `chsh_S` maximum) and CCR-C3 (rename `curby_pulse_id`). Then E, F and G switch from the stub certificate to `python -m C_certificate.src.certify --mode heron`.
- D-2 should copy `entropy.py` and the mask construction for its interleaved CHSH rounds.
- Real certification needs a hardware run plus an EAT-style bound (future work).
