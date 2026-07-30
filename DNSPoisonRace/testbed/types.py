"""Frozen shared types (epic §4, AC-1.3).

`Draw`/`DrawProvenance`'s field order and `Draw.to_bytes()`/`to_dict()` key
order are load-bearing for the P6 JS<->Python parity gate (epic §3.6) --
fixed here and must not change once P2 starts filling provenance payloads.
Imports stdlib only so this module loads anywhere (P2/P3/P6).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Literal

RaceOutcome = Literal["poisoned", "resolved_legit", "window_closed"]


@dataclass(frozen=True)
class DrawProvenance:
    """Base shape (P1). P2 fills `detail` per arm: QRNG receipt / PRNG
    seed+index / CSPRNG source note. `kind` is one of
    `fixed`|`prng`|`csprng`|`qrng`, unset (`""`) until P2 assigns it."""

    kind: str = ""
    detail: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Draw:
    """The resolver's randomised outbound query state: transaction ID and
    UDP source port. Field order (txid, port) is canonical for
    `to_bytes()`/`to_dict()` -- P6's JS mirror must match it exactly."""

    txid: int
    port: int
    provenance: DrawProvenance

    def to_bytes(self) -> bytes:
        """Canonical byte encoding: txid (2 bytes, big-endian), port (2
        bytes, big-endian). Provenance is metadata, not part of the acceptance
        rule, so it is excluded."""
        return struct.pack("!HH", self.txid, self.port)

    def to_dict(self) -> dict[str, int]:
        """Canonical JSON key order: txid, port. Provenance is rendered
        separately (P6 provenance panel), not embedded here."""
        return {"txid": self.txid, "port": self.port}


@dataclass(frozen=True)
class Event:
    """One entry in the discrete-event queue (`sim/event_queue.py`).
    `seq` is a monotonic tie-breaker so equal-time events order
    deterministically without ever comparing `payload` (epic Risks)."""

    time: float
    seq: int
    kind: str
    payload: object
