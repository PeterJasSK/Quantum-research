"""Victim-throughput contention model (plan-10 §4) -- replaces the deleted
`metrics/victim_throughput.py` iperf3 reader.

The victim's background flow shares the target link. Its throughput is its
fair share of residual capacity after the attacker's surviving load on that
link: full demand when no attack (or after a rotation disperses the crafted
set), collapsing toward zero as the target link saturates. This is the one
place the model asserts user-visible damage; it drives `min_victim_mbps` into
the same frozen `success.py` predicate (`saturated AND min_victim_mbps <=
VICTIM_COLLAPSE_MBPS`).

It exposes the exact zero-arg `() -> float | None` callable
`MetricsCollector(victim_mbps_reader=...)` expects: the harness updates the
current target-link attacker load each poll, then feeds the collector, which
calls `reader()` for that same poll.
"""
from __future__ import annotations


class VictimModel:
    def __init__(self, *, link_capacity_mbps: float, victim_demand_mbps: float) -> None:
        self._link_capacity_mbps = link_capacity_mbps
        self._victim_demand_mbps = victim_demand_mbps
        self._target_attacker_mbps = 0.0

    def update(self, target_attacker_mbps: float) -> None:
        """Record the attacker's surviving load on the target link for the
        current poll (Mbps)."""
        self._target_attacker_mbps = target_attacker_mbps

    def current_mbps(self) -> float:
        residual = self._link_capacity_mbps - self._target_attacker_mbps
        return max(0.0, min(self._victim_demand_mbps, residual))

    def reader(self):
        """The `() -> float | None` callable the collector polls."""
        return self.current_mbps
