"""Race-engine skeleton (AC-1.1, epic §5 acceptance rule).

Source-agnostic: `run_race` treats `Draw` as an opaque `(txid, port)` for
acceptance and never inspects `provenance` (epic Risks -- keeps P2's four
arms from leaking into the engine). P1 wires this against
`config.STATIC_DRAW_*` and a one-shot stub forged guess; P3 adds the real
attacker flood, retransmit timers, and `q` parallel windows as scheduled
events on this same queue -- no new engine.
"""
from __future__ import annotations

from dataclasses import dataclass

from testbed.sim.event_queue import EventQueue
from testbed.types import Draw, RaceOutcome


@dataclass(frozen=True)
class RaceResult:
    outcome: RaceOutcome
    t_outcome: float
    forged_packets: int


def run_race(
    draw: Draw,
    forged_guess: tuple[int, int],
    rtt: float,
    send_schedule: list[float],
    seed: int,
) -> RaceResult:
    """Race one authoritative reply (arriving at `rtt`) against forged
    answers sent at each time in `send_schedule`, guessing `forged_guess =
    (txid, port)`. A forged answer is accepted iff it matches `draw` and
    arrives before the authoritative reply (epic §5). `seed` is accepted for
    forward compatibility with P3's randomised retransmit jitter; P1's
    schedule is fully deterministic and does not consume it.
    """
    del seed  # unused in P1; kept for the P3 signature contract

    queue = EventQueue()
    queue.push(rtt, "authoritative", None)
    for send_time in send_schedule:
        queue.push(send_time, "forged", forged_guess)

    forged_packets = 0
    while not queue.empty():
        event = queue.pop()
        if event.kind == "forged":
            forged_packets += 1
            guessed_txid, guessed_port = event.payload
            if guessed_txid == draw.txid and guessed_port == draw.port:
                return RaceResult("poisoned", event.time, forged_packets)
        elif event.kind == "authoritative":
            return RaceResult("resolved_legit", event.time, forged_packets)

    return RaceResult("window_closed", queue.clock.now, forged_packets)
