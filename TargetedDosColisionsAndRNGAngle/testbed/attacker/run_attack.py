#!/usr/bin/env python3
"""CLI launcher for `run_attack`, run from the Mininet `attacker` host
(mirrors `run_controller.py`/`run_topo.py`'s launcher style).

Run with:
    sudo .venv/bin/python3 testbed/attacker/run_attack.py \\
        --level full --mode precision --target-link 0

`--oracle-salt` simulates the placement-inference side channel (P7's
congestion/timing observation, stood in here as a direct read) needed to
validate partial-knowledge seed guesses; it is not the salt the crafter is
handed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from testbed.attacker.attack import run_attack  # noqa: E402
from testbed.attacker.oracle import LocalOracle  # noqa: E402
from testbed.config import (  # noqa: E402
    ATTACK_SOURCE_IPS,
    BRUTEFORCE_DRAW_WINDOW,
    HOSTS,
    N_LINKS,
    PRECISION_PER_SOURCE_PPS,
    PRNG_SEED_SPACE_BITS,
    SALT_KIND,
    TARGET_LINK,
    VOLUMETRIC_PPS,
)
from testbed.types import FiveTuple  # noqa: E402

_VICTIM_IP = HOSTS["victim"]["ip"]
_ATTACKER_IP = HOSTS["attacker"]["ip"]


def _build_probes(dst_ip: str) -> list[FiveTuple]:
    """Probe 5-tuples for the partial attacker's oracle validation --
    distinct src_port per probe, same dst. 6 probes at N_LINKS=4 gives a
    ~4^-6 false-positive rate per candidate seed."""
    return [
        FiveTuple(src_ip=_ATTACKER_IP, dst_ip=dst_ip, src_port=port, dst_port=80, proto=6)
        for port in (50000, 50001, 50002, 50003, 50004, 50005)
    ]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=["full", "partial", "blind"], required=True)
    parser.add_argument("--mode", choices=["volumetric", "precision"], required=True)
    parser.add_argument("--target-link", type=int, default=TARGET_LINK)
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--dst-ip", default=_VICTIM_IP)
    parser.add_argument("--dst-port", type=int, default=80)
    parser.add_argument("--proto", type=int, default=6, help="6=TCP, 17=UDP")
    parser.add_argument("--iface", default="attacker-eth0")
    parser.add_argument("--rate", type=int, default=VOLUMETRIC_PPS, help="volumetric pps")
    parser.add_argument("--per-source-cap", type=int, default=PRECISION_PER_SOURCE_PPS)
    parser.add_argument("--salt", help="hex salt handed to the full-knowledge attacker")
    parser.add_argument(
        "--oracle-salt",
        help="hex salt backing the partial attacker's placement oracle "
        "(simulates the side channel, not handed to the crafter)",
    )
    parser.add_argument("--seed-space-bits", type=int, default=PRNG_SEED_SPACE_BITS)
    parser.add_argument("--draw-window", type=int, default=BRUTEFORCE_DRAW_WINDOW)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    known_salt = bytes.fromhex(args.salt) if args.salt else None
    oracle = LocalOracle(bytes.fromhex(args.oracle_salt), N_LINKS) if args.oracle_salt else None
    probes = _build_probes(args.dst_ip) if oracle is not None else None

    record = run_attack(
        args.level,
        args.mode,
        args.target_link,
        dst_ip=args.dst_ip,
        salt_source_kind=SALT_KIND,
        known_salt=known_salt,
        oracle=oracle,
        probes=probes,
        seed_space_bits=args.seed_space_bits,
        draw_window=args.draw_window,
        count=args.count,
        proto=args.proto,
        src_ip_pool=ATTACK_SOURCE_IPS,
        dst_port=args.dst_port,
        rate_pps=args.rate,
        per_source_cap=args.per_source_cap,
        iface=args.iface,
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
