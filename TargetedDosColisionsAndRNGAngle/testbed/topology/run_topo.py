#!/usr/bin/env python3
"""Launcher: build the net, start OVS in OpenFlow15 mode, point it at the
os_ken controller, drop into the Mininet CLI. Manual-verification entry point.

Run with sudo (Mininet needs root to create network namespaces):
    sudo python3 testbed/topology/run_topo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from testbed.config import CONTROLLER_LISTEN_ADDR, CONTROLLER_LISTEN_PORT  # noqa: E402
from testbed.topology.ecmp_topo import ECMPTopo  # noqa: E402


def main() -> None:
    setLogLevel("info")
    topo = ECMPTopo()
    controller = RemoteController(
        "c0", ip=CONTROLLER_LISTEN_ADDR, port=CONTROLLER_LISTEN_PORT
    )
    net = Mininet(topo=topo, switch=OVSSwitch, controller=controller, autoSetMacs=False)
    net.start()
    CLI(net)
    net.stop()


if __name__ == "__main__":
    main()
