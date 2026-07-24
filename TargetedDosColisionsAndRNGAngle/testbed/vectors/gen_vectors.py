#!/usr/bin/env python3
"""Generate `hash_vectors.json` from the Python `hash_core` (source of truth,
AC-5). Standalone; imports only `hash_core`/`types`."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from testbed.hash_core import ecmp_link  # noqa: E402
from testbed.types import FiveTuple  # noqa: E402

N_LINKS = 4

FIVE_TUPLES = [
    FiveTuple("10.0.0.1", "10.0.0.2", 51000, 80, 6),
    FiveTuple("10.0.0.1", "10.0.0.2", 51001, 80, 6),
    FiveTuple("10.0.0.3", "10.0.0.2", 12345, 443, 6),
    FiveTuple("10.0.0.1", "10.0.0.2", 53, 53, 17),
    FiveTuple("10.0.0.3", "10.0.0.2", 0, 0, 1),  # ICMP: ports 0/0
    FiveTuple("192.168.1.1", "192.168.1.2", 1, 65535, 6),
    FiveTuple("255.255.255.255", "0.0.0.0", 65535, 1, 17),
]

SALTS = [
    b"salt-A-0000000000000000000000000000",
    b"salt-B-1111111111111111111111111111",
    b"\x00" * 32,
    b"\xff" * 32,
]

OUTPUT_PATH = Path(__file__).with_name("hash_vectors.json")


def generate() -> list[dict]:
    vectors = []
    for five_tuple in FIVE_TUPLES:
        for salt in SALTS:
            vectors.append(
                {
                    "five_tuple": {
                        "src_ip": five_tuple.src_ip,
                        "dst_ip": five_tuple.dst_ip,
                        "src_port": five_tuple.src_port,
                        "dst_port": five_tuple.dst_port,
                        "proto": five_tuple.proto,
                    },
                    "salt_hex": salt.hex(),
                    "n_links": N_LINKS,
                    "link": ecmp_link(five_tuple, salt, N_LINKS),
                }
            )
    return vectors


def main() -> int:
    vectors = generate()
    OUTPUT_PATH.write_text(json.dumps(vectors, indent=2) + "\n")
    print(f"wrote {len(vectors)} vectors to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
