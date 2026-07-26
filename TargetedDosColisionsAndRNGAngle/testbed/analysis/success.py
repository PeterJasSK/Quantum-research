"""The single, frozen success predicate (OQ-2, plan-5 Design "2. Analysis +
graphs"): `attacker_succeeded(summary_row)` = `saturated AND min_victim_mbps
<= VICTIM_COLLAPSE_MBPS`. Reused by Graph 1, the orchestrator's PASS/FAIL,
and P6 -- one definition of "attacker succeeded", never re-derived.

Pure function over a summary dict / CSV `DictReader` row (string values) or
a `DataFrame` row (already-typed) -- both are handled the same way.
"""
from __future__ import annotations

from typing import Any

from testbed.config import VICTIM_COLLAPSE_MBPS


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1")


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def attacker_succeeded(summary_row: dict, *, victim_collapse_mbps: float = VICTIM_COLLAPSE_MBPS) -> bool:
    """`saturated` and `min_victim_mbps` in `summary_row` may be raw CSV
    strings or already-typed values (bool/float) -- both parse the same."""
    if not _parse_bool(summary_row.get("saturated", False)):
        return False
    min_victim_mbps = _parse_float(summary_row.get("min_victim_mbps"))
    if min_victim_mbps is None:
        return False  # no victim-throughput signal -- can't confirm collapse
    return min_victim_mbps <= victim_collapse_mbps
