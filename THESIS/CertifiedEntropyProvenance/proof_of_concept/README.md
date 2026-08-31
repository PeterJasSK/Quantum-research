# Proof of Concept — Certified Quantum Entropy with Signed Provenance

Two files, one honest claim: not "unbreakable encryption" (the one-time pad is
already unbreakable by Shannon) but a **signed, physical, per-batch min-entropy
floor** under the key material.

| File | Role |
|---|---|
| `classical_prng.py` | Best *classical* source: an OS CSPRNG. Statistically perfect, but no physical source, no auditable per-batch floor, no signed provenance. |
| `quantum_certified_qrng.py` | *Quantum* source on real IBM hardware: raw bits → SP 800-90B min-entropy → LHL Toeplitz extractor → **Ed25519-signed receipt** → verify. |

## Why the quantum method is better

Not "more random" — both pass the statistical tests (the POC shows near-identical
per-bit min-entropy). Better because of what it can **certify and sign**:

| | Classical CSPRNG | Quantum certified QRNG |
|---|---|---|
| Entropy source | OS pool (unauditable) | physical measurement outcomes |
| Security basis | computational (cipher unbroken) | physics + stated device model |
| Per-batch min-entropy floor | none | SP 800-90B estimate, 99% bound |
| Uniformity guarantee | implicit | LHL extractor, explicit `eps = 2⁻³²` |
| Provenance | none | **Ed25519-signed receipt**, third-party verifiable |
| Retroactive break if primitive falls | yes | no (entropy already realized) |

The pipeline runs end to end and the receipt verifies (`receipt verifies: True`):
the signature is valid **and** the extractor output length is recomputed from the
signed min-entropy floor — so a verifier confirms the guarantee without ever
receiving the bits (`verify()` is not an oracle).

## The one honest caveat (do not skip)
The guarantee is **model-conditional**. Without a device-independent (loophole-free
Bell) apparatus, the floor holds under the *stated* noise model, not
unconditionally. Stating the model explicitly is the contribution, not a hole —
it is what the "provably unbreakable" pitch hand-waves past.

## Connection to the honest negative
The full study extends the repo's empirical result (error detection did **not**
reduce bias) into a *certification* statement: error detection does not raise the
certified floor, while calibration-guided qubit selection does. Plan:
`../../plans/thesis-3-certified-entropy-provenance.md`.

## Run
```bash
python classical_prng.py                          # classical baseline
python quantum_certified_qrng.py                  # full pipeline on Aer sim
python quantum_certified_qrng.py --backend auto   # raw bits from least-busy IBM device
python quantum_certified_qrng.py --backend ibm_fez
```
Deps: `qiskit`, `qiskit-aer`, `numpy`, `pynacl`; hardware also needs `qiskit-ibm-runtime` + saved IBM Quantum account.


RUN : (base) peter@home:~/PycharmProjects/Quantum-research/THESIS$ python CertifiedEntropyProvenance/proof_of_concept/quantum_certified_qrng.py --backend ibm_kingston
backend : ibm_kingston (156 qubits)
source        : quantum (IBM ibm_kingston, H-measure, readout+decoherence noise)
raw bits      : 32768
min-entropy   : 0.8173 bits/bit (SP 800-90B MCV, 99% bound)
extractor     : Toeplitz LHL, eps = 2^-32
certified out : 26718 near-uniform bits (eps-close to uniform)

signed provenance receipt:
{
  "raw_sha256": "8c5fe4db7609098e80db1e0ebabf20db7493abba6fb0428005ae6a9b43bd34b9",
  "n_raw_bits": 32768,
  "device_model": "IBM ibm_kingston, H-measure, readout+decoherence noise",
  "min_entropy_per_bit": 0.81733,
  "extractor": "toeplitz-LHL",
  "eps_uniformity_bound": 2.3283064365386963e-10,
  "n_output_bits": 26718,
  "out_sha256": "5b90b6381112cd1b96c0b4689e9078df21f1f37f1f77249a5f66587f34d19d3e",
  "ed25519_sig": "4f04bda746505235cabe74c3ddd8ab151ce226bb2fa9deca333ebe822699633380deea9fa91af6e21f3bd93eba12dd913e72d6af4a2d4de86e53b16c656f4707"
}

receipt verifies: True   (signature valid AND extractor bound recomputed)
=> a physical, per-batch, model-conditional, SIGNED min-entropy floor —
   the certificate the classical CSPRNG cannot produce.
(base) peter@home:~/PycharmProjects/Quantum-research/THESIS$ python CertifiedEntropyProvenance/proof_of_concept/classical_prng.py 
source        : OS CSPRNG (secrets.token_bytes)
bytes drawn   : 4096
min-entropy   : 6.622 bits/byte (most-common-value, 99% bound)
security basis: COMPUTATIONAL assumption (cipher unbroken)
provenance    : NONE  (no physical source, no signed per-batch floor)

=> Statistically fine. But nothing here is CERTIFIED or SIGNED against
   a stated physical device model. That is what quantum_certified_qrng.py adds.
