"""Off-path attacker package (epic ss9 P3): dependency-free (stdlib only, no
scapy/root/network), sibling of `testbed/draw/` and `testbed/sim/`."""
from __future__ import annotations

from .attack import PoisonRaceResult, run_poison_race

__all__ = ["PoisonRaceResult", "run_poison_race"]
