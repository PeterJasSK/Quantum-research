"""HMAC-DRBG per NIST SP 800-90A section 10.1.2 (SHA-256).

QRNG bits are entropy that *seeds* this standard DRBG; the DRBG's output-
uniqueness and forward-secrecy guarantees come from HMAC-SHA256, not from
any quantum property. Nothing here "defeats quantum attackers" — it is an
ordinary, well-studied deterministic random bit generator.
"""

from __future__ import annotations

import hmac
from hashlib import sha256

_OUTLEN = 32  # SHA-256 digest length in bytes


class HmacDrbg:
    """SP 800-90A HMAC_DRBG instantiated with SHA-256.

    Holds the working state (`K`, `V`) described in §10.1.2. Not thread-safe
    and not safe to reuse across concurrent requests — each caller must hold
    its own instance (see `qeaas.keyed_drbg` for the serverless-safe wrapper).
    """

    def __init__(self) -> None:
        self._k = bytearray(_OUTLEN)
        self._v = bytearray(_OUTLEN)
        self._instantiated = False

    def _hmac(self, key: bytes, data: bytes) -> bytes:
        return hmac.new(bytes(key), data, sha256).digest()

    def _update(self, provided_data: bytes) -> None:
        self._k = bytearray(self._hmac(self._k, bytes(self._v) + b"\x00" + provided_data))
        self._v = bytearray(self._hmac(self._k, bytes(self._v)))
        if provided_data:
            self._k = bytearray(self._hmac(self._k, bytes(self._v) + b"\x01" + provided_data))
            self._v = bytearray(self._hmac(self._k, bytes(self._v)))

    def instantiate(self, seed: bytes, personalization: bytes = b"") -> None:
        """§10.1.2.3 Instantiate: seed material must already include entropy + nonce."""
        self._k = bytearray(_OUTLEN)
        self._v = bytearray(b"\x01" * _OUTLEN)
        self._update(seed + personalization)
        self._instantiated = True

    def reseed(self, seed: bytes, additional: bytes = b"") -> None:
        """§10.1.2.4 Reseed."""
        if not self._instantiated:
            raise RuntimeError("reseed() called before instantiate()")
        self._update(seed + additional)

    def generate(self, n: int, additional: bytes = b"") -> bytes:
        """§10.1.2.5 Generate: return `n` pseudorandom bytes."""
        if not self._instantiated:
            raise RuntimeError("generate() called before instantiate()")
        if additional:
            self._update(additional)

        output = bytearray()
        while len(output) < n:
            self._v = bytearray(self._hmac(self._k, bytes(self._v)))
            output.extend(self._v)

        self._update(additional)
        return bytes(output[:n])
