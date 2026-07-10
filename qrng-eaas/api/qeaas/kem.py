"""EPIC 4: ML-KEM-768 (FIPS 203, post-quantum) keypair + encapsulation.

Honest framing (repeat everywhere): QRNG does not "defeat quantum attackers."
It supplies entropy that seeds a standards DRBG (`generation.random_bytes`,
never raw pool bits -- decision #2), which in turn seeds ML-KEM. The quantum
part is the *entropy source*; the quantum *resistance* comes from ML-KEM
itself.

Uses `kyber-py==1.2.0` (pure Python, pinned in `requirements.txt`). It is
educational and **not constant-time** -- correct for a thesis demo, not
production (S4.3); production would swap to `liboqs` on a persistent host.

Both `key_derive` and `_encaps_internal` are the deterministic,
seed-injecting entry points confirmed against `kyber-py==1.2.0` (see
`shared/spikes/mlkem_seed_spike.py` for the public-API proof of the same
call chain). `_encaps_internal` is a private method of `ML_KEM_768`; it is
used here (Q2) so that encapsulation randomness is *also* QRNG-seeded rather
than falling back to `encaps()`'s internal `os.urandom` call. A `kyber-py`
version bump should treat this as a conscious compatibility check, not a
silent break.
"""

from __future__ import annotations

from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from kyber_py.ml_kem import ML_KEM_768

from qeaas import generation
from qeaas.errors import ApiError

ALGORITHM = "ML-KEM-768"

KEYGEN_SEED_BYTES = 64
ENCAPS_SEED_BYTES = 32
EK_BYTES = 1184

# Q5: configurable quota-cost knobs, alongside the reseed constants in
# `keyed_drbg.py` (same convention). Set either to `0` to run that KEM
# endpoint as a free, quota-exempt service -- the per-key rate limit still
# applies as abuse protection, and `usage_log` still records the real seed
# bytes for visibility.
KEYGEN_QUOTA_COST = KEYGEN_SEED_BYTES
ENCAPS_QUOTA_COST = ENCAPS_SEED_BYTES


def generate_keypair() -> tuple[bytes, bytes]:
    """AC-1: QRNG-seeded ML-KEM-768 keygen. Returns `(ek, dk)`."""
    seed = generation.random_bytes(KEYGEN_SEED_BYTES)
    ek, dk = ML_KEM_768.key_derive(seed)
    return ek, dk


def encapsulate(ek: bytes) -> tuple[bytes, bytes]:
    """AC-4: QRNG-seeded encapsulation against a supplied `ek`.

    Returns `(shared_secret, ciphertext)`. Raises `ApiError(422, "bad_request")`
    for a malformed or wrong-length `ek`.
    """
    if len(ek) != EK_BYTES:
        raise ApiError(422, "bad_request")
    m = generation.random_bytes(ENCAPS_SEED_BYTES)
    try:
        shared_secret, ciphertext = ML_KEM_768._encaps_internal(ek, m)
    except ValueError:
        raise ApiError(422, "bad_request")
    return shared_secret, ciphertext


def derive_demo_key(shared_secret: bytes) -> bytes:
    """Q6: HKDF-SHA256(shared_secret) -> 32-byte AES-GCM-shaped key.

    Purely illustrative of the key EPIC 8's networking demo will derive from
    the shared secret; not used for any cryptographic operation here.
    """
    return HKDF(shared_secret, 32, b"", SHA256)
