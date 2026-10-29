# C — Certificate: CHSH → certified bits → seed

> Letter folder `C_certificate/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/C_certificate/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
Make "certified" a number: CHSH value → min-entropy bound H_min ≥ 1 − log₂(1 + √(2 − S²/4)) → certified-bit count → Toeplitz-extracted seed, with hidden test rounds whose choice is seeded from CURBy, and a ledger format modelled on the beacon chain. The extracted seed seeds every PRNG downstream (shared.seedhash.rng).

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #4 | [Entropy accounting from Bell tests (Pironio; Liu 2025; Vazirani–Vidick)](dossiers/04-bell-entropy-accounting.md) | ★★★ | quantum | adapted |
| #5 | [CURBy / NIST beacon chain (Kavuri)](dossiers/05-curby-beacon-chain.md) | ★★ | classical | adapted |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `quantum_job_record` — own CHSH runs; stub: [`shared/stubs/quantum_job_record/quantum_job_record.json`](../shared/stubs/quantum_job_record/quantum_job_record.json) · schema: [`quantum_job_record.schema.json`](../shared/contracts/quantum_job_record.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `certificate` — schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json) · stub example: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json)
- `quantum_job_record` — schema: [`quantum_job_record.schema.json`](../shared/contracts/quantum_job_record.schema.json) · stub example: [`shared/stubs/quantum_job_record/quantum_job_record.json`](../shared/stubs/quantum_job_record/quantum_job_record.json)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to C_certificate/runs/ via shared.runrecord. -->
All commands run with cwd `reverse-engineering/` and the conda base `python`. Only `fetch_pulses` uses the network.

```bash
# certificate runs → C_certificate/runs/<ts>-chsh-<mode>[-classical]/
python -m C_certificate.src.certify --mode ideal      # simulated: ideal
python -m C_certificate.src.certify --mode heron      # simulated: Heron-class noise (FakeMarrakesh)
python -m C_certificate.src.certify --mode ideal --settings classical   # fail path: S ≤ 2 → rejected + logged
#   options: --rounds 100000 --test-frac 0.2 --pulse-index -1 --eps-est 1e-6 --eps-ext 1e-6 --out-len 256

# reproductions → figures/
python -m C_certificate.repro.pironio        # #4: Pironio 42 bits + H_min-vs-S curve with our latest runs
python -m C_certificate.repro.beacon_chain   # #5: verify cached beacon chain + tamper test

# one-off: refresh the committed pulse cache repro/data/beacon_pulses.json (network)
python -m C_certificate.repro.fetch_pulses --n 12

# check outputs against the frozen contracts
python -m shared.validate C_certificate/runs/<run>/certificate.json C_certificate/runs/<run>/quantum_job_record.json
```

**Run directory contents:**
- `run.json`, `counts_<job>.json`;
- `quantum_job_record.json`, with counts keyed `"xy ab"` and `test_round_mask` as a file_ref;
- `certificate.json`;
- `accounting.json`, with every number used: Ŝ, E_xy, n_xy, δ_xy, S_low, ε values, h, bits, pulse and circuit hashes;
- `rounds.npz` (x, y, a, b, test), `test_round_mask.json`;
- `extracted.bin` (pass only).

Rejections are appended to `runs/rejections.jsonl`. Runs are deterministic for a given cached pulse and mode: the test mask, the Aer seeds and the Toeplitz seed are all derived from the pulse.

## Reproduced result vs. paper

| Target | Paper | Ours | Agreement |
|---|---|---|---|
| #4 Pironio C01: certified bits, n = 3016, Î = 2.414, 99 % | 42 bits | 40.8 bits (Î from Table 1 = 2.4145) | −2.8 % (analytic vs SDP f) |
| #5 beacon chain format (C04 / NIST Beacon 2.0) | tamper-evident chain | 11/11 links, 12/12 signatures + outputs verify; 1-bit edit caught at its pulse | exact |
| #5 CURBy protocol parameters | 512 out / 820 threshold | 512 / 820 (cached request block) | exact |

Applied to our simulated CHSH (N = 100 000, q = 0.2, pulse `nist:2:2003321`):

| Sim mode | Ŝ | S_low | h | certified bits | status |
|---|---|---|---|---|---|
| simulated: ideal | 2.8058 | 2.4868 | 0.2569 | 20 551 | pass |
| simulated: Heron-class noise (FakeMarrakesh) | 2.7037 | 2.3847 | 0.1841 | 14 726 | pass |
| simulated: ideal, classical settings | 2.0000 | 1.6810 | 0 | 0 | fail (rejected, logged) |

Figures: [`figures/hmin_vs_S.png`](figures/hmin_vs_S.png), [`figures/beacon_chain.png`](figures/beacon_chain.png).

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
L0 only. **Simulated CHSH certifies nothing**: the deliverable is the accounting pipeline validated on simulated data — every certificate says "certification-ready, not certified (simulated)". S ≤ 2 ⇒ status fail, no seed, draw rejected and logged (no retry, no fallback).

- **Pass/fail rule.** Pass requires the *lower confidence bound* S_low > 2, not only Ŝ > 2. Too little entropy for a 256-bit seed is a second fail reason.
- **Statistical model.** The accounting is i.i.d. with Hoeffding finite statistics, not the EAT. It is fine for a pipeline validated on simulated data; a real hardware claim needs an EAT-style bound [C06, C07].
- **The simulator knows the mask.** Hidden test rounds only matter against a real device.
- **External seed source.** The external pulse is **NIST Beacon 2.0**, fully verified offline. CURBy [C04] is dissected only: its CIDs are not recomputed, and its latest round (2025-08-22) is flagged `isQuantum: False`.
- **Not reachable.** Liu 2025 [C02] (XEB certified randomness) is an L2-type claim and is read only.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[C01], [C02], [C04], [C05] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
- **CCR-C1: `quantum_job_record`, multi-circuit jobs.**
  - *Need:* one logical CHSH job runs 4 setting circuits, but `transpiled_hash` holds one hash.
  - *Request:* add an optional `transpiled_hashes[]`, one per circuit.
  - *Local workaround:* `transpiled_hash` = sha256(canonical_json([4 circuit hashes])). The list is in `accounting.json` as `circuit_hashes`. `sim_seed` is the base Aer seed; setting k (00, 01, 10, 11) uses `sim_seed + k`.
- **CCR-C2: `certificate`, recomputable entropy.**
  - *Need:* `h_min_per_round` = f(S_low), not f(chsh_S), so a consumer cannot recompute it from the certificate.
  - *Request:* add `chsh_S_lower` and `eps {est, ext}`. The validator could then check h = f(chsh_S_lower) and `certified_bits` = ⌊n_gen · h⌋.
  - *Related:* the schema caps `chsh_S` at 2.8285, but a statistical Ŝ can exceed 2√2 (we saw 2.8365 on one ideal run). We clip `chsh_S` to 2.8284 and keep the raw Ŝ in `accounting.json`. Consider `maximum: 4` (the algebraic CHSH bound).
  - *Local workaround:* everything is in `accounting.json`.
- **CCR-C3: `certificate.curby_pulse_id`, naming.** The pulse comes from the NIST Beacon (`nist:<chain>:<index>`), not CURBy. Consider renaming the field to `beacon_pulse_id`. *Local workaround:* the field name is kept, and the value carries the source prefix.
