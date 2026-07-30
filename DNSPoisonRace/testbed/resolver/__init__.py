"""Resolver-shaped frame + metrics collector (epic §9 P4).

Sibling package to `testbed/attacker/`, `testbed/draw/`, `testbed/sim/`.
Re-exports the P4 surface P5/P6 read as frozen interfaces.
"""
from __future__ import annotations

from .cache import CacheEntry, resolve_cache
from .metrics import CellRecord, amplification_factor, collect_cell

__all__ = [
    "CacheEntry",
    "resolve_cache",
    "CellRecord",
    "amplification_factor",
    "collect_cell",
]
