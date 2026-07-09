"""S0.2 spike: prove DRBG bytes -> ML-KEM-768 keygen is deterministic and round-trips.

Run: api/venv/bin/python shared/spikes/mlkem_seed_spike.py
"""

import hashlib
import hmac

from kyber_py.ml_kem import ML_KEM_768


def placeholder_drbg_generate(seed: bytes, n: int) -> bytes:
    """Stand-in for the real EPIC 1 HMAC-DRBG.generate(n); deterministic for a fixed seed."""
    out = b""
    counter = 0
    while len(out) < n:
        out += hmac.new(seed, counter.to_bytes(4, "big"), hashlib.sha256).digest()
        counter += 1
    return out[:n]


def main() -> None:
    seed = b"fixed-test-seed-for-spike"

    drbg_output_a = placeholder_drbg_generate(seed, 64)
    drbg_output_b = placeholder_drbg_generate(seed, 64)
    assert drbg_output_a == drbg_output_b, "DRBG output must be deterministic for a fixed seed"

    # kyber-py's ML_KEM_768.key_derive(seed) takes exactly 64 bytes (d || z, FIPS 203)
    # and deterministically derives (ek, dk) -- this is the DRBG -> ML-KEM wiring the
    # whole project depends on. No fallback to the `mlkem` package is needed.
    ek_a, dk_a = ML_KEM_768.key_derive(drbg_output_a)
    ek_b, dk_b = ML_KEM_768.key_derive(drbg_output_b)
    assert (ek_a, dk_a) == (ek_b, dk_b), "keygen must be deterministic for identical DRBG output"

    shared_secret, ciphertext = ML_KEM_768.encaps(ek_a)
    recovered_secret = ML_KEM_768.decaps(dk_a, ciphertext)
    assert shared_secret == recovered_secret, "encaps/decaps must round-trip to the same shared secret"

    print("OK: DRBG(64) -> ML-KEM-768.key_derive is deterministic; encaps/decaps round-trips.")
    print(f"ek={len(ek_a)}B dk={len(dk_a)}B ciphertext={len(ciphertext)}B shared_secret={len(shared_secret)}B")


if __name__ == "__main__":
    main()
