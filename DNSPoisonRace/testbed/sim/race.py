"""Race-engine skeleton (AC-1.1, epic §5 acceptance rule).

Source-agnostic: `run_race` treats `Draw` as an opaque `(txid, port)` for
acceptance and never inspects `provenance` (epic Risks -- keeps P2's four
arms from leaking into the engine). P1 wires this against
`config.STATIC_DRAW_*` and a one-shot stub forged guess; P3 adds the real
attacker flood, retransmit timers, and `q` parallel windows as scheduled
events on this same queue -- no new engine.
"""
from __future__ import annotations

import math
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
    guess_budget: int | None = None,
    attempts: int = 1,
) -> AttackRaceResult:
    """P3's flood race (epic ss5), evaluated per-window against the epic's
    analytic anchor instead of by enumerating every forged packet.

    `windows_spec` is one list per parallel query of `(target_index, t_open,
    t_authoritative)` rounds -- the initial window plus any retransmit-spawned
    windows, each with its own fresh target index and its own (already-
    jittered) authoritative arrival -- computed upstream by
    `attacker/attack.py`. `guess_stream` exposes `.space_size`, `.next() ->
    int` (a distinct uniform index in `[0, space_size)`) and `.reset_round()`.

    **Continuous-flood model (defect 1).** A window is *live* only during
    `[t_open, t_authoritative]`; the old model spread the flood evenly across
    the whole `[0, max_t_authoritative]` span, so with retransmits ~500ms apart
    and ~20ms windows almost every forged packet landed in dead time between
    windows and was wasted -- and at the send-rates where the cliff actually
    sits it enumerated billions of dead packets. Here the flood is continuous
    but only in-window guesses count: `g_live = send_rate_pps * duration`
    distinct guesses land inside each live window (capped by `guess_budget`
    and by `space_size` -- you cannot fire more distinct guesses than there are
    cells).

    **Analytic per-window hit.** With `g_live` *distinct* guesses (no
    replacement within a round) against a fresh uniform target, the window is
    poisoned with probability exactly `g_live / space_size` -- so the whole
    race is `P = 1 - prod_w (1 - g_live_w / S)`, the epic's anchor
    `1 - (1 - g_live/S)^(r*q)` when the windows are equal-sized. We Monte-Carlo
    that by drawing the target's rank in the flood's random distinct-guess
    order from the (seeded, portable) `guess_stream`: the window is poisoned
    iff that rank falls within the `g_live` guesses actually fired. This is
    O(windows), independent of send-rate, and tracks the anchor exactly.

    **Kaminsky campaign (`attempts`).** A single RTT window fires only
    `g_live = rate*RTT` guesses -- too few to poison modern entropy in one
    shot. A real off-path attacker re-triggers each query `attempts` times
    (fresh name -> fresh target -> an independent window), so each structural
    window here stands for `attempts` back-to-back live windows and poisons
    with probability `1 - (1 - g_live/S)**attempts`. Folded in closed form
    (O(1) per window), so a multi-thousand-attempt campaign costs nothing.
    `attempts=1` reduces exactly to the single-window case.

    `rtt`, `retransmit`, `parallel_queries`, `seed` are accepted for the
    documented signature contract (epic ss9 P3) -- their effect is already
    baked into `windows_spec`/`guess_stream` by the caller.
    """
    del rtt, retransmit, parallel_queries, seed  # baked into windows_spec/guess_stream by the caller

    space_size = guess_stream.space_size

    windows: list[tuple[float, float, int]] = []
    max_t_authoritative = 0.0
    window_id = 0
    for query_windows in windows_spec:
        for _target_index, t_open, t_authoritative in query_windows:
            windows.append((t_open, t_authoritative, window_id))
            max_t_authoritative = max(max_t_authoritative, t_authoritative)
            window_id += 1
    windows.sort(key=lambda w: w[0])  # resolve the earliest-opening window first

    forged_packets = 0
    for t_open, t_authoritative, wid in windows:
        guess_stream.reset_round()  # OQ-P3.2: distinct guesses reset per retransmit round
        duration = max(0.0, t_authoritative - t_open)
        g_live = int(send_rate_pps * duration)
        if guess_budget is not None:
            g_live = min(g_live, guess_budget)
        g_live = min(g_live, space_size)  # cannot fire more distinct guesses than cells
        if g_live <= 0:
            continue
        # Rank of the true target in the flood's random distinct-guess order;
        # uniform in [0, space_size), so P(rank < g_live) = g_live/space_size.
        target_rank = guess_stream.next()
        if attempts <= 1:
            # Single window: reduces to the plain g_live/S Bernoulli.
            if target_rank < g_live:
                forged_packets += target_rank + 1
                t_hit = t_open + (target_rank + 0.5) / g_live * duration
                return AttackRaceResult("poisoned", t_hit, forged_packets, wid)
            forged_packets += g_live
        else:
            # Campaign: `attempts` independent windows folded to
            # p_win = 1-(1-p1)**attempts; the target_rank/S uniform selects the
            # hit and (via the geometric inverse-CDF) which attempt landed it.
            p1 = g_live / space_size
            u = target_rank / space_size
            p_win = 1.0 - (1.0 - p1) ** attempts
            if u < p_win:
                attempt_no = 1 if p1 >= 1.0 else min(
                    attempts, 1 + int(math.log1p(-u) / math.log1p(-p1))
                )
                within = target_rank % g_live
                forged_packets += (attempt_no - 1) * g_live + within + 1
                t_hit = t_open + (attempt_no - 1 + (within + 0.5) / g_live) * duration
                return AttackRaceResult("poisoned", t_hit, forged_packets, wid)
            forged_packets += attempts * g_live

    return AttackRaceResult("resolved_legit", max_t_authoritative, forged_packets, None)
