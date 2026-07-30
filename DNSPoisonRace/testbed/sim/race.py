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


def _accepts(guess_index: int, target_index: int, event_time: float, t_authoritative: float) -> bool:
    """The one canonical epic ss5 acceptance rule, shared by `run_race`
    (literal `(txid, port)` match, above) and `run_attack_race` (effective-
    index match, below) so the two paths cannot drift (epic Risks)."""
    return guess_index == target_index and event_time < t_authoritative


@dataclass(frozen=True)
class AttackRaceResult:
    outcome: RaceOutcome
    t_outcome: float
    forged_packets: int
    poisoned_window: int | None


def run_attack_race(
    windows_spec: list[list[tuple[int, float, float]]],
    guess_stream: object,
    send_rate_pps: int,
    rtt: float,
    retransmit: float,
    parallel_queries: int,
    seed: int,
) -> AttackRaceResult:
    """P3's flood race (epic ss5). `windows_spec` is one list per parallel
    query of `(target_index, t_open, t_authoritative)` rounds -- the initial
    window plus any retransmit-spawned windows, each with its own fresh
    target index and its own (already-jittered) authoritative arrival --
    computed upstream by `attacker/attack.py` via the portable PRNG, so this
    engine stays source-agnostic (no `draw`/`attacker` imports beyond
    `types`). `guess_stream` need only expose `.next() -> int`. `rtt`,
    `retransmit`, `parallel_queries`, `seed` are accepted for the documented
    signature contract (epic ss9 P3) -- their effect is already baked into
    `windows_spec`/`guess_stream` by the caller, mirroring `run_race`'s
    unused `seed` (P1).
    """
    del rtt, retransmit, parallel_queries, seed  # baked into windows_spec/guess_stream by the caller

    queue = EventQueue()
    window_target: dict[int, int] = {}
    window_t_auth: dict[int, float] = {}
    open_windows: set[int] = set()

    window_id = 0
    max_t_authoritative = 0.0
    for query_windows in windows_spec:
        for target_index, t_open, t_authoritative in query_windows:
            queue.push(t_open, "window_open", (window_id, target_index, t_authoritative))
            max_t_authoritative = max(max_t_authoritative, t_authoritative)
            window_id += 1
    total_windows = window_id

    forged_count = int(max_t_authoritative * send_rate_pps)
    if forged_count > 0:
        step = max_t_authoritative / forged_count
        for i in range(forged_count):
            t = step * (i + 0.5)
            queue.push(t, "forged", guess_stream.next())

    forged_packets = 0
    closed_count = 0

    while not queue.empty():
        event = queue.pop()
        if event.kind == "window_open":
            wid, target_index, t_authoritative = event.payload
            window_target[wid] = target_index
            window_t_auth[wid] = t_authoritative
            open_windows.add(wid)
            queue.push(t_authoritative, "authoritative", wid)
        elif event.kind == "forged":
            forged_packets += 1
            guess = event.payload
            for wid in open_windows:
                if _accepts(guess, window_target[wid], event.time, window_t_auth[wid]):
                    return AttackRaceResult("poisoned", event.time, forged_packets, wid)
        elif event.kind == "authoritative":
            wid = event.payload
            if wid in open_windows:
                open_windows.discard(wid)
                closed_count += 1
                if closed_count >= total_windows:
                    return AttackRaceResult("resolved_legit", event.time, forged_packets, None)

    return AttackRaceResult("window_closed", queue.clock.now, forged_packets, None)
