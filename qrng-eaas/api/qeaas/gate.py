"""Low-entropy gate: reports pool health and blocks premium routes when the
pool is running low, so the DRBG never reseeds from an exhausted pool.

`entropy_level()` is called on *every* response (the `X-Quantum-Entropy`
middleware) and on every gated route (`require_entropy`), so it is backed by a
short in-process TTL cache: a warm serverless instance answers from memory
instead of hitting Postgres per request. Staleness is safe -- the pool only
moves by -32 bytes per reseed (>= 5 min apart) or upward on admin ingest, both
far slower than `_LEVEL_TTL_SECONDS`."""

from __future__ import annotations

import time
from typing import Literal

from fastapi import HTTPException

from qeaas import db
from qeaas.keyed_drbg import THRESHOLD

Level = Literal["healthy", "degraded"]

# In-process cache TTL for the entropy level (module constant, like the reseed
# knobs in keyed_drbg.py). Per warm instance; cold starts re-query once.
_LEVEL_TTL_SECONDS = 10
_cache: tuple[float, Level] | None = None


def _level_for(pool_bytes: int) -> Level:
    """AC-9: below `THRESHOLD` pool bytes remaining, health is 'degraded'."""
    return "degraded" if pool_bytes < THRESHOLD else "healthy"


def prime_cache(pool_bytes: int) -> Level:
    """Refresh the TTL cache from an already-fetched pool byte count and return
    the level. `/health` uses this so its own `pool_bytes_remaining` read doubles
    as the authoritative cache refresh (no extra query)."""
    global _cache
    level = _level_for(pool_bytes)
    _cache = (time.time() + _LEVEL_TTL_SECONDS, level)
    return level


def entropy_level() -> Level:
    """Cached entropy level. Avoids a Postgres hit on the per-response middleware
    and every gated route within the TTL window."""
    if _cache is not None and _cache[0] > time.time():
        return _cache[1]
    return prime_cache(db.pool_bytes_remaining())


def require_entropy() -> None:
    """AC-10: FastAPI dependency that 503s premium routes while degraded."""
    if entropy_level() == "degraded":
        raise HTTPException(status_code=503, detail={"error": "low_quantum_entropy"})
