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


## Pipeline readiness

<!-- readiness: caveats -->

C is the only quantum stage that ran inside the chain: four `commit → certify` prefixes in Heron mode all passed
(Ŝ 2.722–2.762, S_low 2.403–2.442, 15 668–17 869 certified bits; `C_certificate/runs/20261029-18*-chsh-heron`).
No chain obtained a beacon pulse later than its commit: NIST `/pulse/last` lagged 2–3 min and then timed out, so the
runner fell back to the cache (`beacon_fresh: false`). Reusing that pulse reproduced the **identical** certificate and
seed (`7dfb4d50…`) in two chains with different commits. "Usable with caveats" means inside this simulated pipeline:
simulated CHSH certifies nothing.

**Weak links**

| Weak link | Kind | Why it limits reliability | Evidence | To strengthen |
|---|---|---|---|---|
| Beacon freshness | integration | the test-round choice is not provably post-commit | `runs/20261029-1851*-e2e-probe-prefix3/4` `chain.json` `beacon_fetch` | fetch only the newest pulse with backoff; select "first pulse after `committed_utc`" in `beacon.py` |
| Same pulse ⇒ same seed | assumption | the simulator is seeded from the public pulse, so two chains (or anyone holding the pulse) reproduce the "certified" seed | prefix3 vs prefix4: byte-identical `certificate.json` | refuse a pulse already used (the runner warns); real device randomness on hardware |
| `fetch_pulses` overwrites the tracked cache | integration | every chain run dirties git and mixes repro and chain pulses | probe `C.fetch` | write chain pulses into the run dir |
| `certify` exits 0 on S ≤ 2 | integration | callers must parse `status`; B, D and E exit 2 | `certify.py` `main` | exit 2 on fail |
| i.i.d. Hoeffding, not EAT | assumption | not valid for a hardware claim | honesty notes above | EAT bound (post-epic) |
| Certificate fields | contract | no `beacon_pulse_id`, `chsh_S_lower`, `eps`; entropy not recomputable | runner check `_post_certify` | CCR-C2, CCR-C3 |

**Used as-is in the chain?** Yes. It works end to end in the prefix chain; freshness and seed reuse are the caveats. Full gap list: [INT](../INT_integration/README.md); whole chain: [index](../index.html).


## Future

Shared, pipeline-wide context (end goal, digital-twin path, cross-letter risks) lives once in the
[whole-pipeline Future](../future.md). This section covers only what this letter adds. Every claim carries a label:
<span class="chip evidence">evidence-based</span> (a number in this repo or a cited paper), <span class="chip extrapolation">extrapolation</span> (a reasoned step beyond the evidence),
<span class="chip speculative">speculative</span> (possible, not supported yet).

### 1. Aim of the paper(s)

- **[C01] Pironio et al. 2010:** randomness **certified by a Bell-inequality violation**. A CHSH value above 2
  bounds how predictable the outputs can be, without trusting the device.
- **[C05] Vazirani–Vidick:** "certifiable quantum dice": randomness expansion with untrusted devices.
- **[C02] Liu 2025:** certified randomness from random-circuit sampling on a trapped-ion processor (a classical-
  hardness-based claim; read only here).
- **[C04] Kavuri (CURBy):** traceable public random numbers published in a hash-chained beacon.

Why it matters: "random" becomes **auditable**. You get a number of certified bits with a proof, plus a public
timestamp that shows the randomness was not chosen after the fact.

### 2. Contribution

- The accounting pipeline reproduced: 40.8 certified bits against Pironio's 42 (−2.8 %). <span class="chip evidence">evidence-based</span>
- A beacon chain verified offline: 11/11 links and 12/12 signatures; a 1-bit edit is caught at its pulse. <span class="chip evidence">evidence-based</span>
- In the INT chain prefix (Heron-class noise): Ŝ 2.722–2.762, S_low 2.403–2.442, 15 668–17 869 certified bits; the
  S ≤ 2 path is rejected and logged. <span class="chip evidence">evidence-based</span>
- INT findings: no post-commit pulse was obtained (beacon lag), and a reused pulse reproduces the same seed. <span class="chip evidence">evidence-based</span>

### 3. Role in cancer detection

**End goal:** every synthetic cohort used to train or test a cancer detector carries a certificate proving its
random choices were fixed by an external, timestamped source, **not hand-picked** (no cherry-picking of easy or
hard cases after seeing results). This is data credibility for audits and regulators. It does not raise
detection accuracy by itself. <span class="chip extrapolation">extrapolation</span>

### 4. Beyond lungs

- **Any randomized step in medicine:** virtual-trial arm assignment, Monte Carlo dose simulation (how the PRNG
  affects radiotherapy simulations is studied in [E05]), and audit of trial randomization. <span class="chip extrapolation">extrapolation</span>
- **Other synthetic data.** MR, pathology and genomics generators need the same "not cherry-picked" guarantee. <span class="chip extrapolation">extrapolation</span>

### 5. Long-term vision: toward a digital twin

<div class="callout speculative">

<span class="chip speculative">speculative</span> A digital twin runs many stochastic simulations (growth, response, imaging). C's role is to make each one
**replayable and trustworthy**: every random input is traceable to a certified, timestamped source. Path:
(1) a simulated certificate + public beacon (now) → (2) a hardware certificate per cohort →
(3) device-independent certified randomness as a service that twin platforms call for every simulation batch.

</div>

### 6. Predictions

**5 years**
*Assumptions:* superconducting hardware without loophole-free conditions; i.i.d. finite statistics; NIST Beacon available.
- Accounting is validated on simulated data; **simulated CHSH certifies nothing**. <span class="chip evidence">evidence-based</span>
- Loophole-free Bell tests on superconducting circuits exist in the lab [C03]. Device-independent randomness
  expansion has been shown with photons [C06]. <span class="chip evidence">evidence-based</span>
- One Heron hardware CHSH run gives a real (not loophole-free) certificate for a small cohort. <span class="chip extrapolation">extrapolation</span>

**10 years**
*Assumptions:* entropy-accumulation (EAT) finite statistics [C06, C07]; service-grade public beacons.
- Certified-randomness services become a standard provenance stamp for regulated synthetic datasets. <span class="chip extrapolation">extrapolation</span>

<div class="callout speculative">

**15 years**
*Assumptions:* fault-tolerant hardware.
- <span class="chip speculative">speculative</span> Certified randomness from random-circuit sampling at scale [C02], where the guarantee rests on classical
  hardness (claim level L2), becomes cheap enough to stamp every simulation batch of a twin platform.

</div>

### 7. Risks and obstacles

| Risk | Kind | Why it matters | Mitigation |
|---|---|---|---|
| Simulation certifies nothing | validation | the current certificates are a pipeline test only | hardware run (post-epic) |
| i.i.d. vs EAT | technical | i.i.d. bounds are not valid against an adversarial device | EAT bound [C06, C07] |
| Beacon dependency | technical | NIST lag 2–3 min and timeouts were observed in INT | backoff; first pulse after commit |
| Pulse reuse ⇒ same seed | technical | two cohorts can be identical | refuse used pulses |
| No standard for "certified" medical data | regulatory | certificates may carry no legal weight | position as traceability evidence, not compliance |

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
