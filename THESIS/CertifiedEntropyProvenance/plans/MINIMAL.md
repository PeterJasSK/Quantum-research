# MINIMAL — Certified Entropy Provenance

Absolute minimal proof of concept. One script, stored bits, no live hardware. Proves the core loop: raw quantum bits → min-entropy estimate → extractor → signed receipt → verify.

## Claim to demonstrate
A batch of quantum bits ships with a **signed, model-conditional min-entropy floor**, and error detection does **not** raise that floor vs raw bits.

## Inputs (reuse, do not regenerate)
- Stored raw-Hadamard bitstream from `../ErrorDetectionVSRawBits/`
- Stored Bell error-detected bitstream from same

## Minimal pipeline (single file `poc.py`, ~80 lines)
1. Load both bitstreams.
2. **Min-entropy** — SP 800-90B *most-common-value* estimate only (skip full IID/Markov battery): `H_min = -log2(p_max)` where `p_max` = frequency of most common byte. One function.
3. **Extractor** — Leftover Hash Lemma via one 2-universal hash: `out = SHA256(seed || bits)` truncated to `floor(H_min_total - 2*log2(1/eps))` bits. Fixed `eps = 2^-32`.
4. **Receipt** — Ed25519 sign the tuple `(batch_hash, n_in, H_min_per_bit, n_out, eps)`. Print JSON.
5. **Verify** — second function checks signature + recomputes output length. Never returns the bits (no oracle).

## Pass condition
- Receipt verifies.
- `H_min_per_bit(Bell) ≈ H_min_per_bit(raw)` within noise (reproduces the honest negative as a *certified* statement).

## Explicitly out of scope for POC
Full SP 800-90B suite, live IBM runs, calibration-guided selection, SP 800-22 battery, ML-KEM demo. All deferred to full study.

## Deps
`pip install pynacl` (Ed25519). Everything else stdlib (`hashlib`, `math`, `collections`, `json`).
