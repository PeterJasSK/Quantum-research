"""Mininet k=4 fat-tree topology (plan-8 AC-1). Mirrors `ecmp_topo.py`'s
style (`addSwitch(name, protocols="OpenFlow15")`, `sys.path` insert), but
switches/hosts/links come from the shared `testbed.topology.fabric` model so
Mininet dpids line up with `fabric.py`'s switch ids -- `dpid=str(i+1)` in
`fabric.all_switches` order (1-indexed; Mininet/OVS dpid 0 is reserved).

`FATTREE_K` (default 4) is the only knob -- leaf-spine/other k out of scope
(plan-8 Out of scope).
"""
from __future__ import annotations

import sys
from pathlib import Path

from mininet.topo import Topo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from testbed.config import FATTREE_K  # noqa: E402
from testbed.topology.fabric import build_fattree  # noqa: E402


class FatTreeTopo(Topo):
    def build(self, k: int = FATTREE_K, **_opts):
        fabric = build_fattree(k)

        dpid_by_switch = {
            switch_id: format(i + 1, "x") for i, switch_id in enumerate(fabric.all_switches)
        }
        for switch_id, dpid in dpid_by_switch.items():
            self.addSwitch(switch_id, dpid=dpid, protocols="OpenFlow15")

        for link_id in fabric.link_ids:
            switch_a, switch_b = link_id.split("-")
            self.addLink(switch_a, switch_b)

        for host_id in fabric.hosts:
            ip = fabric.host_to_ip[host_id]
            self.addHost(host_id, ip=f"{ip}/8")
            self.addLink(host_id, fabric.host_edge[host_id])


topos = {"fattreetopo": lambda: FatTreeTopo()}
