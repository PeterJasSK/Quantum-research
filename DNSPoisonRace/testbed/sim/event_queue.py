"""The discrete-event core (D1, epic §4). A `heapq`-backed priority queue
keyed by `(time, seq)` -- the monotonic `seq` counter breaks ties
deterministically and means `Event.payload` never participates in
comparison (epic Risks: non-deterministic event ordering would break JS
parity). Pure, stdlib only. Reusable unchanged by P3 (retransmit timers, `q`
parallel windows) as scheduled events on this same queue.
"""
from __future__ import annotations

import heapq

from testbed.types import Event


class Clock:
    """Virtual clock. Advances only when `EventQueue.pop()` returns an event
    -- there is no wall-clock and no `sleep()` anywhere in the core."""

    def __init__(self) -> None:
        self.now: float = 0.0


class EventQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[float, int, Event]] = []
        self._seq = 0
        self.clock = Clock()

    def push(self, time: float, kind: str, payload: object) -> Event:
        event = Event(time=time, seq=self._seq, kind=kind, payload=payload)
        heapq.heappush(self._heap, (event.time, event.seq, event))
        self._seq += 1
        return event

    def pop(self) -> Event:
        _, _, event = heapq.heappop(self._heap)
        self.clock.now = event.time
        return event

    def empty(self) -> bool:
        return not self._heap
