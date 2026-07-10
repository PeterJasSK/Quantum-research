"""Serverless-safe keyed DRBG wrapper.

On stateless serverless you cannot safely read-modify-write DRBG state per
request (two concurrent requests could reuse state -> identical output).
Instead a monotonic Redis counter (atomic INCR) is mixed into a fresh
HMAC-DRBG instance per call: output(n) = HMAC-DRBG(root_key, counter, n).
`root_key` itself is rotated ("reseeded") from the QRNG pool on a fixed
schedule -- see the constants below. QRNG bits seed a standards DRBG; they
do not "defeat quantum attackers."

Served bytes are always DRBG output, never raw pool bits, so request volume
alone cannot drain the pool -- reseeds are additionally floored at
`RESEED_MIN_INTERVAL_SECONDS` (AC-7), so even unlimited traffic against the
output-count branch cannot accelerate pool drain below wall-clock time.
"""

from __future__ import annotations

import time

from qeaas import db, pool
from qeaas.drbg import HmacDrbg
from qeaas.redis_client import incr_counter

# Low-water mark on the pool -- below this, /health reports "degraded" (AC-9).
THRESHOLD = 64 * 1024

# Reseed fires on whichever comes first (AC-7), but the output-limit branch is
# additionally floored so heavy traffic alone cannot pull the schedule forward.
RESEED_INTERVAL_SECONDS = 15 * 60
RESEED_OUTPUT_LIMIT = 100_000
RESEED_MIN_INTERVAL_SECONDS = 5 * 60
RESEED_PULL_BYTES = 32

_cache: dict | None = None


def _bootstrap_root_key() -> None:
    material = pool.pull_reseed_material(RESEED_PULL_BYTES)
    db.save_root_key(bytes(material), reseed_counter=0, outputs_since_reseed=0)
    pool.burn(material)


def _load_cache(force: bool = False) -> dict:
    global _cache
    if _cache is None or force:
        row = db.get_root_key()
        if row is None:
            _bootstrap_root_key()
            row = db.get_root_key()
        assert row is not None
        _cache = {
            "root_id": row.id,
            "root_key": row.root_key,
            "reseed_counter": row.reseed_counter,
            "outputs_since_reseed": row.outputs_since_reseed,
            "rotated_at_ts": row.rotated_at.timestamp(),
        }
    return _cache


def maybe_reseed() -> None:
    """AC-7, AC-8: rotate `root_key` from the pool when the interval elapses."""
    cache = _load_cache()
    elapsed = time.time() - cache["rotated_at_ts"]
    output_limit_hit = (
        cache["outputs_since_reseed"] >= RESEED_OUTPUT_LIMIT
        and elapsed >= RESEED_MIN_INTERVAL_SECONDS
    )
    due = elapsed >= RESEED_INTERVAL_SECONDS or output_limit_hit
    if not due:
        return

    material = pool.pull_reseed_material(RESEED_PULL_BYTES)
    db.save_root_key(
        bytes(material),
        reseed_counter=cache["reseed_counter"] + 1,
        outputs_since_reseed=0,
    )
    pool.burn(material)
    _load_cache(force=True)


def output(n: int, additional: bytes = b"") -> bytes:
    """AC-3, AC-5: distinct Redis counter per call guarantees distinct output."""
    maybe_reseed()
    cache = _load_cache()

    counter = incr_counter()
    drbg = HmacDrbg()
    drbg.instantiate(cache["root_key"])
    result = drbg.generate(n, additional=counter.to_bytes(8, "big") + additional)

    db.bump_outputs_since_reseed(cache["root_id"])
    cache["outputs_since_reseed"] += 1
    return result
