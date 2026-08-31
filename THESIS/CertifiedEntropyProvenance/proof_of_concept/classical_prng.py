"""Classical baseline — the best classical random-number source: an OS CSPRNG.

Why this is the baseline
------------------------
A cryptographically secure PRNG (here Python's `secrets` / `os.urandom`, backed
by the kernel CSPRNG) is the strongest *classical* answer. Its output passes every
statistical test and is fine for keys — so the honest comparison is NOT "quantum
looks more random" (it doesn't; both pass SP 800-22). The comparison is about what
you can *certify*:

    - A CSPRNG's security rests on a COMPUTATIONAL HARDNESS ASSUMPTION (the
      underlying block/stream cipher is unbroken). Break the primitive and the
      "randomness" is predictable retroactively.
    - Its entropy is INHERITED from an OS pool you cannot audit per-batch. There
      is no per-output, model-conditional min-entropy number you can sign and
      hand to a verifier.
    - It ships NO provenance. You cannot prove which physical process produced a
      given byte, nor attach a quantified uniformity bound to it.

That is the gap the quantum arm fills — not "unbreakable cipher" (the one-time
pad already is, by Shannon), but a certified, signed, physical min-entropy floor
UNDER the key material.

Run:  python classical_prng.py
"""
from __future__ import annotations

import secrets
from collections import Counter
from math import log2, sqrt


def csprng_bytes(n: int) -> bytes:
    """Best classical source: OS CSPRNG."""
    return secrets.token_bytes(n)


def observed_min_entropy_per_byte(data: bytes) -> float:
    """SP 800-90B most-common-value estimate (same estimator the quantum arm
    uses) with a 99% upper confidence bound on p_max. Shown here to make the
    point: on a CSPRNG this returns ~8 bits/byte too — the number is NOT what
    distinguishes the sources. What the CSPRNG CANNOT do is tie this number to a
    physical process and a signed receipt with a stated device model."""
    n = len(data)
    p_max = max(Counter(data).values()) / n
    p_u = min(1.0, p_max + 2.576 * sqrt(p_max * (1 - p_max) / (n - 1)))
    return -log2(p_u)


if __name__ == "__main__":
    data = csprng_bytes(4096)
    h = observed_min_entropy_per_byte(data)
    print("source        : OS CSPRNG (secrets.token_bytes)")
    print(f"bytes drawn   : {len(data)}")
    print(f"min-entropy   : {h:.3f} bits/byte (most-common-value, 99% bound)")
    print("security basis: COMPUTATIONAL assumption (cipher unbroken)")
    print("provenance    : NONE  (no physical source, no signed per-batch floor)")
    print()
    print("=> Statistically fine. But nothing here is CERTIFIED or SIGNED against")
    print("   a stated physical device model. That is what quantum_certified_qrng.py adds.")
