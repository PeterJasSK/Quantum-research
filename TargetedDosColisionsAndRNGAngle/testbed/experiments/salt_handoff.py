"""Supplies the full/partial-knowledge attacker the salt it needs (plan-5
Design "1. Experiment orchestrator", OQ-1): a pure read of the controller's
rotation log, never a re-mint -- the attacker always uses the salt the
controller is *actually* live on.

OQ-1 made this uniform: the controller logs its initial minted salt at
startup (`old_salt=b""`), so even a prng-no-rotation cell has a logged
event, and this is always "read the latest `new_salt`", never a special case.
"""
from __future__ import annotations

from testbed.salt.rotation_log import read_events


def current_salt_hex(rotation_log_path: str) -> str:
    """Latest `new_salt` in the rotation log, as hex (ready for the
    attacker CLI's `--salt`/`--oracle-salt`)."""
    latest: dict | None = None
    for event in read_events(rotation_log_path):
        latest = event
    if latest is None:
        raise RuntimeError(
            f"no rotation events in {rotation_log_path!r} -- controller has not started "
            "(OQ-1: it must log its initial salt at startup)"
        )
    return latest["new_salt"]
