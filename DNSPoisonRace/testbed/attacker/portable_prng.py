"""JS-portable deterministic PRNG (OQ-P3.3, epic parity contract for P6).

`splitmix64` is the exact algorithm the JS mirror vendors verbatim with
`BigInt` -- every reproducible random choice in the attacker package (guess
order, RTT jitter, parity-vector targets) flows through this module, never
`random.Random`/`os.urandom`."""
from __future__ import annotations

_MASK64 = (1 << 64) - 1
_GOLDEN_GAMMA = 0x9E3779B97F4A7C15


def splitmix64(state: int) -> tuple[int, int]:
    """One splitmix64 step. Returns `(value, next_state)`, both masked to 64
    bits. Pure integer ops only -- no floats in the core step (parity-safe)."""
    next_state = (state + _GOLDEN_GAMMA) & _MASK64
    z = next_state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK64
    z = z ^ (z >> 31)
    return z, next_state


def bounded(state: int, n: int) -> tuple[int, int]:
    """Unbiased index in `[0, n)`. `n` is always a power of two in this
    package (guess-space sizes, jitter buckets), so `value % n` is exactly
    unbiased -- 2**64 divides evenly by any n <= 2**64."""
    if n <= 0:
        raise ValueError("n must be positive")
    value, next_state = splitmix64(state)
    return value % n, next_state
