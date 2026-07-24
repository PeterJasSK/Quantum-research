"""AC-2 placement oracle (OQ-1): the brute-force validation channel.

Models the attacker's real-world placement-inference side channel (a
congestion/timing observation -- P7's honest framing) as a first-class
object so `reconstruct.py` can validate a seed guess against it. Real
inference is congestion/timing-based, not a direct read; `LocalOracle` is
the testbed's direct-read stand-in used offline for crafting and checking.
"""
from __future__ import annotations

from typing import Protocol

from testbed.hash_core import ecmp_link
from testbed.types import FiveTuple


class PlacementOracle(Protocol):
    """Returns the true egress link for a probe 5-tuple under the
    controller's current salt."""

    def link_for(self, five_tuple: FiveTuple) -> int: ...


class LocalOracle:
    """Direct-read oracle computing placement via the real hash. Used
    offline for crafting and by `collision_check.py`; not a model of the
    real inference channel (that's a P7 concern)."""

    def __init__(self, salt: bytes, n_links: int) -> None:
        self._salt = salt
        self._n_links = n_links

    def link_for(self, five_tuple: FiveTuple) -> int:
        return ecmp_link(five_tuple, self._salt, self._n_links)
