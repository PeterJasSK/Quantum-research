"""Pure, scapy-free flow helpers (AC-2/AC-4): the blind-fallback tuple
generator and the traffic-mode label.

Split out of the former `traffic.py` (plan-10: the scapy real-packet sender
`send_flows`/`_build_packet`/`_send_*` and the whole Mininet transport are
deleted; the flow-level simulator replaces them). Everything here is stdlib
only, so `attack.py`, `collision_check.py`, and `testbed/sim/*` import it
without scapy or root.
"""
from __future__ import annotations

import random
from typing import Literal

from testbed.types import FiveTuple

TrafficMode = Literal["volumetric", "precision"]


def random_five_tuples(count: int, *, dst_ip: str, proto: int = 6) -> list[FiveTuple]:
    """Blind fallback (AC-2): uncrafted 5-tuples that spread ~uniformly
    across links -- the expected-failure baseline."""
    return [
        FiveTuple(
            src_ip=f"10.0.0.{random.randint(100, 250)}",
            dst_ip=dst_ip,
            src_port=random.randint(1024, 65535),
            dst_port=random.randint(1, 65535),
            proto=proto,
        )
        for _ in range(count)
    ]
