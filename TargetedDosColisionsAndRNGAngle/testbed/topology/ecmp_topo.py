"""Mininet topology: leaf switch (s1) with attacker + bg hosts and N parallel
links to a spine switch (s2); victim attaches to the spine. Reads N_LINKS,
port map, and host placement from config.py.

Second-victim slot is cheap to add later (epic Q1): add a HOSTS entry with
location="spine" in config.py plus one addLink call here, no restructuring.
"""
from __future__ import annotations

import sys
from pathlib import Path

from mininet.topo import Topo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from testbed.config import HOSTS, N_LINKS  # noqa: E402


class ECMPTopo(Topo):
    def build(self, **_opts):
        leaf = self.addSwitch("s1", protocols="OpenFlow15")
        spine = self.addSwitch("s2", protocols="OpenFlow15")

        # Order matters: config.LEAF_LOCAL_PORTS assumes leaf-attached hosts
        # are linked in HOSTS iteration order, before the spine links.
        for name, h in HOSTS.items():
            host = self.addHost(name, ip=f"{h['ip']}/24", mac=h["mac"])
            switch = leaf if h["location"] == "leaf" else spine
            self.addLink(host, switch)

        # N parallel links, the leaf's equal-cost paths to the spine.
        for _ in range(N_LINKS):
            self.addLink(leaf, spine)


topos = {"ecmptopo": lambda: ECMPTopo()}
