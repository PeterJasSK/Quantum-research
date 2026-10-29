# #05 — CURBy / NIST beacon chain (Kavuri)

**Letter:** C ([`C_certificate`](../README.md)) · **Priority:** ★★ · **Kind:** classical · **Papers:** C04 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

**Kavuri et al. 2025 [C04]** run **CURBy**, the CU Randomness Beacon, a public beacon whose bits come from a loophole-free photonic Bell test at NIST.

Traceability comes from **Twine**, which intertwines hash chains into a hash graph:
- Every stage is a block on a hash chain. The stages are: request with pre-committed protocol parameters → Bell-test data hash → entropy check → seed from the DRAND beacon → extraction → output pulse.
- Each block includes the hash of its predecessor, and of blocks on other parties' chains (NIST, CU, DRAND, a time-stamping chain).
- Rewriting any stage would require rewriting every chain it is woven into.
- Pulses follow the NIST randomness-beacon standard format: 512-bit values, signed and time-stamped.

Two ideas matter for us:
1. **An external, public, unpredictable source** for choices the device must not know in advance. For us, that is the hidden test-round mask.
2. **Commit → act → publish, hash-chained and signed.** This is the template for G's receipt and ledger.

The NIST Beacon 2.0 format, which CURBy is "closely based on" (C04), is the documented, fully verifiable instance of the format. That is the one we reproduce.

## Equations

```text
NIST Beacon 2.0 pulse p (chain c, index i), all integers big-endian:
  M(p) = len‖uri ‖ len‖version ‖ u32 cipherSuite ‖ u32 period ‖ len‖certificateId ‖ u64 chainIndex
         ‖ u64 pulseIndex ‖ len‖timeStamp ‖ len‖localRandomValue ‖ len‖ext.sourceId ‖ u32 ext.statusCode
         ‖ len‖ext.value ‖ len‖previous ‖ len‖hour ‖ len‖day ‖ len‖month ‖ len‖year
         ‖ len‖precommitmentValue ‖ u32 statusCode                     (len = u32 byte length)
  signatureValue = RSA-PKCS#1 v1.5 / SHA-512 over M(p)                  (NIST certificate)
  outputValue    = SHA-512( M(p) ‖ signatureValue )                     (raw sig bytes, no length prefix)
Chain links:
  p_i.listValues[previous]   = p_{i−1}.outputValue
  p_{i−1}.precommitmentValue = SHA-512( p_i.localRandomValue )          (commit one minute ahead)
Our use:
  pulse_seed = SHA-256(outputValue) → rng(pulse_seed, "C.test_mask")    (hidden test rounds)
  Toeplitz seed bits = SHAKE-256(outputValue ‖ "C.toeplitz")
```

The serialization was confirmed empirically against live pulses: the signature verifies over M(p), and the output value matches only for `M ‖ raw signature`.

## Parameters

| Parameter | Value | Source |
|---|---|---|
| CURBy pulse size | 512 bits | C04 abstract |
| Min-entropy threshold per pulse | 820 bits (smooth) | C04 main text |
| Soundness error | 2⁻⁶⁴ | C04 main text |
| Protocol success | 7434 / 7454 attempts = 99.7 % over 40 days | C04 abstract |
| Extractor | TMPS, seeded from the DRAND beacon | C04 |
| NIST Beacon period | 60 000 ms | live pulses (`period`) |
| Our cache | 12 consecutive pulses `nist:2:2003310` … `nist:2:2003321` + 3 CURBy blocks | `../repro/data/beacon_pulses.json` |

## Paper's claimed result

**C04:** every stage of a randomness pulse is traceable through intertwined hash chains, so tampering with any block is detectable. The operational result is 7434 / 7454 pulses delivered (99.7 %), each 512 bits from ≥ 820 bits of certified min-entropy.

The Bell-test throughput cannot be reproduced without the photonic experiment. What we reproduce is the **format property**: a chain of real public pulses verifies end-to-end offline, and a one-bit edit is caught.

## Our reproduction (number + figure)

`python -m C_certificate.repro.beacon_chain` ([figure](../figures/beacon_chain.png)):
- **NIST Beacon 2.0, chain 2: `chain OK (11 links, 12 pulses)`.** All 12 signatures verify against the cached NIST certificate, all 12 output values recompute, all 11 previous-links match, and all 11 precommitments match.
- **Tamper test.** Flipping 1 bit of `localRandomValue` in pulse #6 makes pulse #6 fail on **signature**, **output** and **precommit**. Every other pulse still verifies, so the edit is localized.
- **CURBy (format sample, 3 blocks of round 28297).**
  - The request block publishes `nBitsOut = 512` and `nBitsThreshold = 820`, matching C04 exactly.
  - Each later block's `links[0]` is the previous block's CID: link-by-reference verified.
  - The CIDs themselves (IPLD dag-cbor + multihash) are **not recomputed**, because that needs a dag-cbor library that is not installed (no new installs).
  - Observation: the latest CURBy round is dated **2025-08-22** and its request is flagged `isQuantum: False`. CURBy is therefore not a live quantum source today. This is why the NIST Beacon (plan Q3 fallback) is our operational source.

As a cross-check of the C04 numbers against our own extractor: with the leftover hash lemma at ε = 2⁻⁶⁴, 512 output bits need only 512 + 128 = 640 bits of min-entropy. C04's 820 includes smoothing, the TMPS extractor's loss, and finite-statistics margins. The ratio 820 / 512 ≈ 1.6 is the "price" to compare with our 256 + 40.

## Adaptation

- **Test-round choice.** `certify` refuses any pulse that fails a chain check, then seeds the hidden test-round mask (and the Toeplitz seed) from the selected pulse. `certificate.curby_pulse_id` = `nist:<chain>:<index>`. The field name is kept from the contract; the source is recorded in `accounting.json`.
- **Offline by design.** Only `python -m C_certificate.repro.fetch_pulses` touches the network. The cache is committed, so every run is replayable.
- **No fallback on failure.** A failing certificate is never retried with another pulse (epic decision 6).

### Ledger template for G

How the beacon fields map onto our `Receipt` / `LedgerEntry` contracts (frozen in `shared/contracts/`):

| Beacon / CURBy field | Role | Our field |
|---|---|---|
| `pulseIndex` / Twine `index` | position in chain | `LedgerEntry.index` |
| `listValues[previous]` / `links[0]` (prev CID) | hash link to predecessor | `LedgerEntry.prev_hash` (64 × "0" at genesis) |
| `outputValue` = SHA-512(M ‖ sig) / block CID | identity of this entry | `LedgerEntry.entry_hash` = sha256(canonical(entry − entry_hash)) |
| signed message M(p) | what is signed | `Receipt` canonical_json({commit, fill}) |
| `signatureValue` + `certificateId` | signature + key id | `Receipt.signature{alg "Ed25519", public_key_b64, sig_b64}` |
| `precommitmentValue` (commit to next local random value) / CURBy request block with `parameters` | commit before act | `Receipt.commit{rulebook_hash, code_hash, committed_utc}` (written BEFORE the job) |
| `timeStamp` | time ordering | `LedgerEntry.created_utc`, `commit.committed_utc` |
| CURBy `dataHash` (hash of raw Bell data) | binds raw data | `Receipt.fill.counts_sha256` |
| CURBy `paramsHash` | binds protocol parameters | `Receipt.fill.params_sha256` |
| CURBy `randomness` | the output | `Receipt.fill.seed_hex` |
| intertwined external chains (DRAND, NIST) | cross-party anchoring | future: anchor our ledger head in a public beacon pulse (e.g. put `entry_hash` into a CURBy/Twine chain) |

What G should copy:
1. Commit (rulebook + code hash + parameters) is a separate, earlier, signed entry.
2. Verification recomputes the hash from canonical bytes; it never trusts a stored hash.
3. Verification reports *which* check failed at *which* index, as `verify_chain` does.

## Verdict

**Adapted (classical, claim level n/a).**
- Reproduction: the beacon chain format verifies end-to-end on real pulses (11/11 links), the tamper test is localized, and the CURBy parameters match C04.
- The pulse is used as the external seed for the hidden test rounds.
- CURBy itself is dissected only: its CIDs are not recomputed, and it is not live-quantum as of the cache date.

## What to reuse next

- **G:** the ledger mapping table above, and `beacon.verify_chain`'s per-check, per-index report style. Re-implement it; letters do not import each other.
- **INT / future:** to make the ledger externally anchored, publish the ledger head hash into a public chain (CURBy/Twine API or a beacon external value). If CURBy resumes quantum operation, add a dag-cbor CID check and switch `fetch_pulses` to it.
