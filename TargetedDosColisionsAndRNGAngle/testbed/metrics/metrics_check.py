#!/usr/bin/env python3
"""P4 spike (AC-4, AC-5, AC-7): manual check, no test suite (project directive).

Runs standalone without os_ken/root -- imports only the metrics package's
pure-maths modules, feeding synthetic port-stats samples. Non-zero exit
means one of:
  1. per-link utilisation / max_link_util don't match a hand-computed
     delta-over-capacity calculation;
  2. jains_index doesn't match a known closed-form case (idle, fair,
     single-link concentration);
  3. saturation (time/packets/flows-to-saturation) doesn't latch on the
     correct poll of a rising series.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, __file__.rsplit("/testbed/", 1)[0])

from testbed.metrics.collector import MetricsCollector  # noqa: E402
from testbed.metrics.csv_writer import CsvWriter  # noqa: E402
from testbed.metrics.fairness import jains_index, polarization_index  # noqa: E402
from testbed.metrics.run_context import RunContext  # noqa: E402

_EGRESS_PORTS = [10, 11, 12, 13]
_N_LINKS = len(_EGRESS_PORTS)
_LINK_CAPACITY_MBPS = 10.0
_LINK_CAPACITY_BYTES_PER_SEC = _LINK_CAPACITY_MBPS * 1_000_000 / 8
_SATURATION_UTILISATION = 0.9


def _make_collector(csv_path: str) -> MetricsCollector:
    run_context = RunContext(knowledge_level="na", attack_mode="na", csv_path=csv_path, start_time=0.0)
    return MetricsCollector(
        egress_ports=_EGRESS_PORTS,
        target_link=0,
        link_capacity_mbps=_LINK_CAPACITY_MBPS,
        saturation_utilisation=_SATURATION_UTILISATION,
        run_context=run_context,
        salt_source_tag="prng",
        rotation_interval=0.0,
        csv_writer=CsvWriter(csv_path, _N_LINKS),
    )


def _check_utilisation_and_max() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        collector = _make_collector(str(Path(tmp) / "metrics.csv"))
        collector.on_port_stats([(p, 0, 0, 0.0) for p in _EGRESS_PORTS], tracked_flows=0)

        known_bytes = int(_LINK_CAPACITY_BYTES_PER_SEC * 0.5)  # -> 0.5 utilisation over 1s
        samples = [(_EGRESS_PORTS[0], known_bytes, 100, 1.0)] + [
            (p, 0, 0, 1.0) for p in _EGRESS_PORTS[1:]
        ]
        result = collector.on_port_stats(samples, tracked_flows=1)
        if result is None:
            print("FAIL: expected a PollResult on the second poll", file=sys.stderr)
            return False
        if abs(result.per_link_util[0] - 0.5) > 1e-6:
            print(f"FAIL: link0 utilisation {result.per_link_util[0]} != 0.5", file=sys.stderr)
            return False
        if abs(result.max_link_util - 0.5) > 1e-6:
            print(f"FAIL: max_link_util {result.max_link_util} != 0.5", file=sys.stderr)
            return False
        print(f"PASS: link0 utilisation and max_link_util both 0.5 for a known {known_bytes}-byte/1s delta")
        return True


def _check_jains_edge_cases() -> bool:
    cases = [([0, 0, 0, 0], 1.0), ([1, 1, 1, 1], 1.0), ([4, 0, 0, 0], 0.25)]
    for values, expected in cases:
        got = jains_index(values)
        if abs(got - expected) > 1e-9:
            print(f"FAIL: jains_index({values}) = {got} != {expected}", file=sys.stderr)
            return False
    print("PASS: jains_index matches idle (1.0), fair (1.0), and single-link concentration (0.25)")
    return True


def _check_saturation_latch() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        collector = _make_collector(str(Path(tmp) / "metrics.csv"))
        collector.on_port_stats([(p, 0, 0, 0.0) for p in _EGRESS_PORTS], tracked_flows=0)

        # Rising series on link0: 0.5, 0.7, 0.95 utilisation -- crosses
        # SATURATION_UTILISATION=0.9 on the third poll.
        cumulative_bytes = 0
        cumulative_packets = 0
        last_result = None
        for i, util in enumerate((0.5, 0.7, 0.95), start=1):
            cumulative_bytes += int(_LINK_CAPACITY_BYTES_PER_SEC * util)
            cumulative_packets += 50
            samples = [(_EGRESS_PORTS[0], cumulative_bytes, cumulative_packets, float(i))] + [
                (p, 0, 0, float(i)) for p in _EGRESS_PORTS[1:]
            ]
            last_result = collector.on_port_stats(samples, tracked_flows=i)

        if last_result is None or not last_result.saturated_now:
            print("FAIL: expected saturation to latch on the third poll", file=sys.stderr)
            return False
        if collector.time_to_saturation_s != 3.0:
            print(f"FAIL: time_to_saturation_s {collector.time_to_saturation_s} != 3.0", file=sys.stderr)
            return False
        if collector.packets_to_saturation != cumulative_packets:
            print(
                f"FAIL: packets_to_saturation {collector.packets_to_saturation} != {cumulative_packets}",
                file=sys.stderr,
            )
            return False
        if collector.flows_to_saturation != 3:
            print(f"FAIL: flows_to_saturation {collector.flows_to_saturation} != 3", file=sys.stderr)
            return False
        print(f"PASS: saturation latched at poll 3 (t=3.0s, packets={cumulative_packets}, flows=3)")
        return True


def _check_polarization_edge_cases() -> bool:
    cases = [([1, 1, 1, 1], 1.0), ([4, 0, 0, 0], 4.0), ([0, 0, 0, 0], 1.0)]
    for values, expected in cases:
        got = polarization_index(values)
        if abs(got - expected) > 1e-9:
            print(f"FAIL: polarization_index({values}) = {got} != {expected}", file=sys.stderr)
            return False
    print("PASS: polarization_index matches fair (1.0), single-link concentration (4.0), and idle (1.0)")
    return True


def main() -> int:
    checks = (
        _check_utilisation_and_max(),
        _check_jains_edge_cases(),
        _check_saturation_latch(),
        _check_polarization_edge_cases(),
    )
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
