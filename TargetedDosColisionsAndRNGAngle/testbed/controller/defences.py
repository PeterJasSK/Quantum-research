"""Per-source defence policy (P4, AC-1/AC-2): connection throttling counter
and stable per-source meter-id assignment. Pure -- no OpenFlow imports; the
controller sends the actual `OFPMeterMod`/`OFPFlowMod` using the ids/specs
this module returns (plan-4 Design). Stdlib only, so it stays importable
without os_ken.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable


@dataclass(frozen=True)
class ThrottleDecision:
    src_ip: str
    connection_count: int
    over_limit: bool


class DefencePolicy:
    """Tracks per-`src_ip` new-flow timestamps over a sliding window and
    assigns a stable per-source meter id. Wall-clock is injected (`now`) so
    this stays deterministic and clock-free at its core."""

    def __init__(
        self,
        *,
        throttle_max_connections: int,
        throttle_window_seconds: float,
        meter_id_range: int = 4096,
    ) -> None:
        self._throttle_max_connections = throttle_max_connections
        self._throttle_window_seconds = throttle_window_seconds
        self._meter_id_range = meter_id_range
        self._flow_timestamps: dict[str, list[float]] = {}
        self._meter_ids: dict[str, int] = {}
        self._throttled: set[str] = set()
        self._seen_flows: set[Hashable] = set()

    def note_flow(self, src_ip: str, flow_key: Hashable, now: float) -> ThrottleDecision:
        """Record a new `(src_ip, 5-tuple)` flow at `now`; return whether
        `src_ip` is now over `throttle_max_connections` within the sliding
        window. A `flow_key` already seen (a rotation-driven re-install of
        an existing flow, not a genuinely new one) is not counted twice."""
        timestamps = self._flow_timestamps.setdefault(src_ip, [])
        if flow_key not in self._seen_flows:
            self._seen_flows.add(flow_key)
            timestamps.append(now)
            cutoff = now - self._throttle_window_seconds
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)

        over_limit = len(timestamps) > self._throttle_max_connections
        if over_limit:
            self._throttled.add(src_ip)
        return ThrottleDecision(src_ip=src_ip, connection_count=len(timestamps), over_limit=over_limit)

    def is_throttled(self, src_ip: str) -> bool:
        return src_ip in self._throttled

    def meter_id_for(self, src_ip: str) -> int:
        """Stable small integer per source: the last IP octet folded into a
        bounded meter-id range (0 is reserved), so one meter per source is
        installed once by the controller and reused thereafter."""
        meter_id = self._meter_ids.get(src_ip)
        if meter_id is None:
            last_octet = int(src_ip.rsplit(".", 1)[-1])
            meter_id = (last_octet % (self._meter_id_range - 1)) + 1
            self._meter_ids[src_ip] = meter_id
        return meter_id
