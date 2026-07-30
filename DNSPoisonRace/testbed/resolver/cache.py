"""Resolver cache wrapper (epic §5). A thin, source-agnostic mapping from a
`PoisonRaceResult.outcome` to a named cache state plus the TTL bookkeeping
the epic §5 diagram shows after `RESOLVED-LEGIT`. Does not decide any
outcome -- the race decision is P3's `PoisonRaceResult.outcome` alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from testbed import config
from testbed.attacker.attack import PoisonRaceResult

CacheState = Literal["poisoned", "resolved_legit", "window_closed"]


@dataclass(frozen=True)
class CacheEntry:
    """What actually ends up cached: the forged answer if `poisoned`, the
    real authoritative answer if `resolved_legit`, nothing if
    `window_closed`."""

    state: CacheState
    ttl_expires_at: float | None  # None for window_closed (nothing cached)


def resolve_cache(
    result: PoisonRaceResult, *, ttl_seconds: float = config.CACHE_TTL_SECONDS
) -> CacheEntry:
    """Pure, three-branch mapping over `result.outcome` -- no new decision
    logic (epic §5's `RESOLVED-LEGIT --cache TTL--> WINDOW CLOSED` edge,
    generalised to the poisoned case since a poisoned answer is cached too)."""
    if result.outcome == "window_closed":
        return CacheEntry(state="window_closed", ttl_expires_at=None)
    return CacheEntry(state=result.outcome, ttl_expires_at=result.t_outcome + ttl_seconds)
