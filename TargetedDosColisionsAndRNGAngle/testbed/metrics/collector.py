"""MetricsCollector (P4, AC-4/5/6/7): stateful over a run.

Pure delta/utilisation/Jain/saturation maths lives here as plain methods
with no OpenFlow types -- it takes plain `(port_no, tx_bytes, tx_packets,
t)` samples, so it is checkable offline with synthetic data (see
`metrics_check.py`). The controller's `EventOFPPortStatsReply` handler is
the only caller that touches real OpenFlow objects, converting them to this
plain shape first.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from testbed.metrics.csv_writer import CsvWriter
from testbed.metrics.fairness import jains_index
from testbed.metrics.run_context import RunContext


@dataclass(frozen=True)
class _PortSample:
    tx_bytes: int
    tx_packets: int
    t: float


@dataclass(frozen=True)
class PollResult:
    per_link_util: list[float]
    max_link_util: float
    jains_index: float
    saturated_now: bool


class MetricsCollector:
    """Consumes one port-stats poll at a time; writes one CSV row per poll
    (AC-4/5/6/7) plus an always-current `*.summary.csv` sidecar."""

    def __init__(
        self,
        *,
        egress_ports: list[int],
        target_link: int,
        link_capacity_mbps: float,
        saturation_utilisation: float,
        run_context: RunContext,
        salt_source_tag: str,
        rotation_interval: float,
        csv_writer: CsvWriter,
        victim_mbps_reader=None,
    ) -> None:
        self._egress_ports = egress_ports
        self._target_link = target_link
        self._target_port = egress_ports[target_link]
        self._link_capacity_bytes_per_sec = link_capacity_mbps * 1_000_000 / 8
        self._saturation_utilisation = saturation_utilisation
        self._run_context = run_context
        self._salt_source_tag = salt_source_tag
        self._rotation_interval = rotation_interval
        self._csv_writer = csv_writer
        self._victim_mbps_reader = victim_mbps_reader

        self._last_samples: dict[int, _PortSample] = {}
        self._saturated = False
        self._time_to_saturation_s: float | None = None
        self._packets_to_saturation: int | None = None
        self._flows_to_saturation: int | None = None
        self._final_jains_index = 1.0
        self._min_victim_mbps: float | None = None

    @property
    def saturated(self) -> bool:
        return self._saturated

    @property
    def time_to_saturation_s(self) -> float | None:
        return self._time_to_saturation_s

    @property
    def packets_to_saturation(self) -> int | None:
        return self._packets_to_saturation

    @property
    def flows_to_saturation(self) -> int | None:
        return self._flows_to_saturation

    @property
    def final_jains_index(self) -> float:
        return self._final_jains_index

    @property
    def min_victim_mbps(self) -> float | None:
        return self._min_victim_mbps

    def on_port_stats(
        self, samples: list[tuple[int, int, int, float]], *, tracked_flows: int
    ) -> PollResult | None:
        """`samples` is `(port_no, tx_bytes, tx_packets, t)` tuples. Returns
        `None` until every egress port has at least two samples (need a
        delta to compute throughput)."""
        deltas_by_port: dict[int, float] = {}
        target_tx_packets = 0
        now = 0.0

        for port_no, tx_bytes, tx_packets, t in samples:
            if port_no not in self._egress_ports:
                continue
            if port_no == self._target_port:
                target_tx_packets = tx_packets
            now = max(now, t)
            prev = self._last_samples.get(port_no)
            self._last_samples[port_no] = _PortSample(tx_bytes, tx_packets, t)
            if prev is None:
                continue
            dt = t - prev.t
            if dt <= 0:
                continue
            deltas_by_port[port_no] = (tx_bytes - prev.tx_bytes) / dt

        if len(deltas_by_port) < len(self._egress_ports):
            return None

        per_link_util = [
            deltas_by_port[port_no] / self._link_capacity_bytes_per_sec
            for port_no in self._egress_ports
        ]
        max_util = max(per_link_util)
        jains = jains_index(per_link_util)
        self._final_jains_index = jains

        victim_mbps = self._victim_mbps_reader() if self._victim_mbps_reader else None
        if victim_mbps is not None and (self._min_victim_mbps is None or victim_mbps < self._min_victim_mbps):
            self._min_victim_mbps = victim_mbps

        saturated_now = max_util >= self._saturation_utilisation
        if saturated_now and not self._saturated:
            self._saturated = True
            self._time_to_saturation_s = now - self._run_context.start_time
            self._packets_to_saturation = target_tx_packets
            self._flows_to_saturation = tracked_flows

        elapsed = now - self._run_context.start_time
        row = {
            "timestamp": _iso(now),
            "elapsed_seconds": f"{elapsed:.3f}",
            "salt_source": self._salt_source_tag,
            "knowledge_level": self._run_context.knowledge_level,
            "rotation_interval": self._rotation_interval,
            "attack_mode": self._run_context.attack_mode,
            "max_link_util": f"{max_util:.6f}",
            "jains_index": f"{jains:.6f}",
            "victim_mbps": "" if victim_mbps is None else f"{victim_mbps:.3f}",
            "target_link": self._target_link,
            "target_tx_packets": target_tx_packets,
            "tracked_flows": tracked_flows,
        }
        for i, util in enumerate(per_link_util):
            row[f"link{i}_util"] = f"{util:.6f}"
        self._csv_writer.write_row(row)
        self._write_summary()

        return PollResult(
            per_link_util=per_link_util, max_link_util=max_util, jains_index=jains, saturated_now=saturated_now
        )

    def _write_summary(self) -> None:
        self._csv_writer.write_summary(
            {
                "salt_source": self._salt_source_tag,
                "knowledge_level": self._run_context.knowledge_level,
                "rotation_interval": self._rotation_interval,
                "attack_mode": self._run_context.attack_mode,
                "time_to_saturation_s": "" if self._time_to_saturation_s is None else f"{self._time_to_saturation_s:.3f}",
                "packets_to_saturation": "" if self._packets_to_saturation is None else self._packets_to_saturation,
                "flows_to_saturation": "" if self._flows_to_saturation is None else self._flows_to_saturation,
                "final_jains_index": f"{self._final_jains_index:.6f}",
                "min_victim_mbps": "" if self._min_victim_mbps is None else f"{self._min_victim_mbps:.3f}",
                "saturated": self._saturated,
            }
        )


def _iso(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc).isoformat()
