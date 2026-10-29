# #04 — Entropy accounting from Bell tests (Pironio; Liu 2025; Vazirani–Vidick)

**Letter:** C ([`C_certificate`](../README.md)) · **Priority:** ★★★ · **Kind:** quantum · **Papers:** C01, C02, C05 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

**The problem.** "CHSH > 2" is only a label. A Bell violation says the outputs cannot be pre-programmed, but it does not say *how much* randomness they contain.

**Pironio et al. 2010 [C01]** turn the CHSH value into a number. In a device-independent way, quantum theory plus no-signalling bound the min-entropy of the outputs (a, b) given the inputs (x, y) by a function f(I) of the CHSH expectation I.
- f(2) = 0: no violation, no certified randomness.
- f(2√2) = 1 bit per round of the pair.
- A martingale (Azuma–Hoeffding) argument extends this to n sequential uses of the same device, which may have memory: H∞ ≥ n f(Î − ε).
- Their ion-trap experiment certified **42 bits**.

**Vazirani–Vidick 2012 [C05]** add spot-checking. Most rounds use one fixed input pair ("generation rounds"). Only a small, secret, random subset are CHSH "test rounds". The device cannot tell which rounds are tested, so it must behave on all of them. This saves input randomness (they reach exponential expansion) and is the structure we use: **hidden test rounds**.

**Two-universal extraction.** Certified min-entropy H in a raw string becomes ≈ H − 2 log₂(1/ε) almost-uniform bits through a Toeplitz hash, by the leftover hash lemma. Toeplitz is used because it is cheap (m + L − 1 seed bits) and is the standard choice in QRNG post-processing. CURBy [C04] uses TMPS (Trevisan-type) instead.

**Liu et al. 2025 [C02]** is a different route: certified randomness from random-circuit sampling with XEB on a 56-qubit trapped-ion machine. They certify 71,313 bits against a restricted adversary, using 1.1 × 10¹⁸ FLOP/s of classical verification. That is an L2-type (classical-hardness) claim and is out of reach on Heron-class shallow circuits (see `../../analysis-stages-B-D-F.md` §0). We read it only.

## Equations

```text
CHSH estimator (C01 Eq. 2, uniform or biased inputs):
  E_xy = P(a = b | xy) − P(a ≠ b | xy)
  S = E00 + E01 + E10 − E11                          (local ≤ 2, quantum ≤ 2√2)

Analytic min-entropy bound per round on (a, b) given (x, y) (C01 Fig. 2, curve b; App. Eq. 6):
  f(S) = 1 − log₂(1 + √(2 − S²/4))                   f(2) = 0, f(2√2) = 1
No-signalling-only bound (C01 Fig. 2, curve c):
  f_NS(S) = −log₂(3/2 − S/4)

Pironio finite statistics (C01 App. A, Eqs. 10–12), q = min P(x, y), I_q = 2√2:
  δ = exp(−n ε² / (2 (1/q + I_q)²))  ⇔  ε = (1/q + I_q) √(2 ln(1/δ) / n)
  H∞(R|S) ≥ n f(Î − ε)  with probability ≥ 1 − δ

Our accounting (spot-checked, i.i.d. finite statistics):
  n_xy  = number of TEST rounds at setting xy
  δ_xy  = √(2 ln(8/ε_est) / n_xy)                    Hoeffding on E_xy ∈ [−1, 1], union over 4 × 2 sides
  S_low = Ŝ − Σ_xy δ_xy
  h     = f(S_low)                                     per generation round, on the pair (a, b)
  certified_bits = ⌊n_gen · h⌋                        raw input = 2 n_gen bits
  L ≤ certified_bits − 2 log₂(1/ε_ext)                 leftover hash lemma; we extract L = 256

Toeplitz extractor over GF(2): T[i, j] = s[i + m − 1 − j], out = T · raw (mod 2), |s| = m + L − 1
```

## Parameters

| Parameter | Value | Source |
|---|---|---|
| Pironio events n | 3016 | C01 main text, Table 1 |
| Pironio Î | 2.414 ± 0.058 | C01 Table 1 caption |
| Pironio input distribution | uniform, q = 1/4 | C01 main text |
| Pironio confidence 1 − δ | 99 % | C01 Fig. 3 |
| Pironio certified bits | 42 | C01 abstract |
| Our rounds N | 100 000 | plan Q6 |
| Our test fraction q | 0.2 (test settings uniform, so 0.05 per setting) | plan Q6 |
| Generation setting | (x, y) = (0, 0) | plan §4 |
| ε_est, ε_ext | 10⁻⁶, 10⁻⁶ | plan Q6 |
| Output length L | 256 bits (one seed) | plan AC-3 |
| Angles | Alice θ ∈ {0, π/2}, Bob θ ∈ {π/4, −π/4} on \|Φ⁺⟩ | CHSH-optimal |

## Paper's claimed result

**C01:** with n = 3016 events and Î = 2.414, "at least 42 new random bits are generated with a 99 % confidence level" (abstract; Fig. 3).

## Our reproduction (number + figure)

`python -m C_certificate.repro.pironio` ([figure](../figures/hmin_vs_S.png)):

| Quantity | Paper | Ours | Agreement |
|---|---|---|---|
| Î recomputed from Table 1 counts | 2.414 | 2.4145 (n = 3016) | exact |
| ε (Azuma–Hoeffding, δ = 0.01, q = 1/4) | — | 0.3773 ⇒ Î − ε = 2.0367 | — |
| Certified bits n f(Î − ε) | **42** | **40.8** | −2.8 % |
| f(2), f(2√2) | 0, 1 | 0, 1 | exact |

The −2.8 % is explained. The paper evaluates f with the tight **SDP** curve (Fig. 2 curve a). We use the **analytic** lower bound (curve b), which is never above it and almost coincides with it near S = 2. Without the finite-statistics penalty the same data would give n f(Î) ≈ 613 bits. The 1/q factor in ε is what makes small experiments expensive.

**Applied to our simulated runs** (N = 100 000, q = 0.2, pulse `nist:2:2003321`):

| Run | Ŝ | S_low | h = f(S_low) | certified bits | status |
|---|---|---|---|---|---|
| simulated: ideal | 2.8058 | 2.4868 | 0.2569 | 20 551 | pass |
| simulated: Heron-class noise (FakeMarrakesh) | 2.7037 | 2.3847 | 0.1841 | 14 726 | pass |
| simulated: ideal, `--settings classical` (all Z) | 2.0000 | 1.6810 | 0 | 0 | **fail**: rejected and logged |

In every passing run the extractable length is far above 256 + 40 bits. The Hoeffding penalty Σδ ≈ 0.32 is the main cost: it removes about 0.55 bits per round in the ideal case.

## Adaptation

The method is adapted to our certificate contract and the seed chain (`../src/`):
- **Rounds = shots.** The 4 setting circuits (|Φ⁺⟩ + `ry(−θ)` + Z measurement) are transpiled to `FakeMarrakesh` in both sim modes. Each runs once with `memory=True`, and the per-shot results are put back into round order (`chsh.py`).
- **Hidden test rounds.** The mask and the test settings come from `shared.seedhash.rng(sha256(pulse.outputValue), "C.test_mask")`, where the pulse is a verified NIST Beacon 2.0 pulse (#5). The mask is recorded in the job record as a file_ref (`test_round_mask.json`).
- **Conservative certification.** Pass requires **S_low > 2**, not just Ŝ > 2 (plan Q1). The certificate records `h_min_per_round = f(S_low)`. The point estimate goes in `chsh_S`, capped at 2.8284 because the schema maximum is 2.8285 and a statistical Ŝ can exceed 2√2.
- **Insufficient entropy** (extractable < 256) is a second fail reason (plan Q2). Both fail reasons give `status: fail`, no seed, and one line in `runs/rejections.jsonl`. There is no retry and no fallback (epic decision 6).
- **Extraction.** The raw generation outputs a₁b₁a₂b₂… (2 n_gen bits) go through the Toeplitz hash. The seed bits are SHAKE-256(pulse output ‖ `"C.toeplitz"`), which are public, as a strong extractor allows. The 256 output bits become `extracted_seed_hex`, the root of every downstream `shared.seedhash.rng`.

**Honesty notes:**
- **Simulated CHSH certifies nothing.** The simulator *is* the device and knows the mask. The deliverable is the accounting pipeline, "certification-ready, not certified (simulated)", at claim level L0.
- **Statistical model.** The accounting is i.i.d. with Hoeffding finite statistics. It is not the entropy accumulation theorem (EAT) used by modern device-independent randomness expansion [C06, C07], and it is not Pironio's full martingale bound for spot-checking.
- **Single chip.** Even on hardware, one chip is not loophole-free: there is no space-like separation and there are shared control electronics.

## Verdict

**Adapted (L0, simulated: ideal and Heron-class noise).**
- Reproduction: Pironio's 42 bits matched to −2.8 % (analytic vs SDP f), and Î from Table 1 matched exactly.
- The accounting pipeline produces contract-valid pass and fail certificates.
- The step to `integrated` belongs to INT, once E, F and G consume a real C certificate instead of the stub.

## What to reuse next

- **E, F, G, H:** take `extracted_seed_hex` from `C_certificate/runs/<ts>-chsh-heron/certificate.json`. Regenerate it with `python -m C_certificate.src.certify --mode heron`; it is deterministic for a given cached pulse. Seed every PRNG with `shared.seedhash.rng(seed, "<letter>.<purpose>")`.
- **D (D-2, one-job lineage):** reuse `entropy.f_hmin`, `chsh_estimate` and `s_lower_bound` on the interleaved CHSH rounds, and the mask construction from `chsh.make_schedule`. Copy them (letters do not import each other).
- **G:** `accounting.json` holds every number the receipt needs (Ŝ, S_low, ε values, pulse id, circuit hashes).
- **INT:** apply CCR-C1 and CCR-C2 (see the [README](../README.md)) so consumers can recompute h from the certificate alone.
- **Future (hardware):** replace the i.i.d. Hoeffding step by an EAT-style bound [C06, C07] before claiming real certification.
