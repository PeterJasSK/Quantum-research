"""Port-stats-driven metrics collection (P4): per-link utilisation, Jain's
fairness index, victim throughput, saturation timing -- all written to the
run-tagged CSV (epic §4)."""
from __future__ import annotations

from testbed.metrics.collector import MetricsCollector
from testbed.metrics.fairness import jains_index
from testbed.metrics.run_context import RunContext

__all__ = ["MetricsCollector", "jains_index", "RunContext"]
