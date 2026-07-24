#!/usr/bin/env python3
"""S0.2 spike (AC-4): same 5-tuple, two salts -> two different egress links.

Runs standalone, imports only hash_core/types. Non-zero exit / equal ports
means the epic's core assumption is broken -- stop and reconsider before
building further.
"""
from __future__ import annotations

import sys

sys.path.insert(0, __file__.rsplit("/testbed/", 1)[0])

from testbed.config import N_LINKS
from testbed.hash_core import ecmp_link
from testbed.types import FiveTuple

FIXED_FLOW = FiveTuple(
    src_ip="10.0.0.1",
    dst_ip="10.0.0.2",
    src_port=51000,
    dst_port=80,
    proto=6,
)

SALT_A = b"salt-A-0000000000000000000000000000"
SALT_B = b"salt-B-1111111111111111111111111111"


def main() -> int:
    port_a = ecmp_link(FIXED_FLOW, SALT_A, N_LINKS)
    port_b = ecmp_link(FIXED_FLOW, SALT_B, N_LINKS)
    print(f"salt_A -> link {port_a}")
    print(f"salt_B -> link {port_b}")
    if port_a == port_b:
        print("FAIL: salt did not change the egress link", file=sys.stderr)
        return 1
    print("PASS: salt changed the egress link")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
