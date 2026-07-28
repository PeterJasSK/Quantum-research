"""Flow-level simulation backend (plan-10): a self-contained, deterministic,
root-free replacement for the deleted Mininet/OVS/scapy transport.

Drives the real, frozen mechanism (hash core, collision crafter, seed
brute-forcer, salt sources, defence policy, metrics collector) through a
documented flow-level transport model, producing byte-schema-identical CSVs
so `testbed/analysis/*` and the P6 web demo consume the output unchanged.
"""
from __future__ import annotations

from testbed.sim.sim_harness import CellResult, run_cell

__all__ = ["CellResult", "run_cell"]
