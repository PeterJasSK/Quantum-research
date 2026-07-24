"""The frozen link = hash(5tuple, salt) mod N core.

Pure function, no Mininet/Ryu imports — P2 lifts this unchanged into the
shared module; P3 (attacker) and P6 (JS mirror) consume it. Keep it
dependency-free so it imports anywhere (epic ss3.5, s4).
"""
from __future__ import annotations

import hashlib

from .types import FiveTuple


def ecmp_link(five_tuple: FiveTuple, salt: bytes, n_links: int) -> int:
    """Return the egress link index in [0, n_links) for five_tuple under salt."""
    digest = hashlib.sha256(five_tuple.to_bytes() + salt).digest()
    return int.from_bytes(digest[:8], "big") % n_links
