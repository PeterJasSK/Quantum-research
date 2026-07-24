"""AC-1 collision crafter: enumerate 5-tuples that hash to a target link
under the real, frozen `hash_core.ecmp_link` (epic ss3.5). Dependency-free
so it runs without scapy/root (`collision_check.py`, P5)."""
from __future__ import annotations

from dataclasses import dataclass

from testbed.hash_core import ecmp_link
from testbed.types import FiveTuple


@dataclass(frozen=True)
class CollisionCrafter:
    """Crafts `FiveTuple`s whose `ecmp_link(..., salt, n_links)` equals
    `target_link`. Computes against the real hash -- never re-implements it
    (epic ss3.5: a drift here silently invalidates Experiments 2-5)."""

    salt: bytes
    target_link: int
    n_links: int

    def is_collision(self, five_tuple: FiveTuple) -> bool:
        """Single-tuple membership test, used by the check script."""
        return ecmp_link(five_tuple, self.salt, self.n_links) == self.target_link

    def craft(
        self,
        count: int,
        *,
        dst_ip: str,
        proto: int,
        src_ip_pool: list[str],
        src_port_range: range,
        dst_port: int,
    ) -> list[FiveTuple]:
        """Walk `(src_ip, src_port)` combinations, keep those that collide
        onto `target_link`, stop at `count`. Each kept tuple varies
        `src_ip`/`src_port` so the flows look individually distinct."""
        collisions: list[FiveTuple] = []
        for src_ip in src_ip_pool:
            for src_port in src_port_range:
                candidate = FiveTuple(
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    proto=proto,
                )
                if self.is_collision(candidate):
                    collisions.append(candidate)
                    if len(collisions) >= count:
                        return collisions
        return collisions
