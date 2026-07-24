#!/usr/bin/env python3
"""Standalone launcher for ecmp_controller.py.

os-ken ships no `os-ken-manager` console script (it's used as a library by
OpenStack Neutron, not as a standalone controller like ryu-manager was).
This mirrors ryu.cmd.manager.main(): patch the hub, load the OpenFlow
listener (`os_ken.controller.ofp_handler`) plus our app, run until killed.

Run with:
    .venv/bin/python3 testbed/controller/run_controller.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from os_ken.lib import hub

hub.patch()

from os_ken.base.app_manager import AppManager  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

APP_LISTS = [
    "os_ken.controller.ofp_handler",
    "testbed.controller.ecmp_controller",
]


def main() -> None:
    AppManager.run_apps(APP_LISTS)


if __name__ == "__main__":
    main()
