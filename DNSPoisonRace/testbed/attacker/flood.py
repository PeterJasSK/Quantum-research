"""Flood builder (AC-3.2). Pure timing math; no events here -- the engine
(`sim/race.py` `run_attack_race`) schedules the actual events. Kept as plain
functions so `run_poison_race` and the CLI can report the span/packet count
without running a race."""
from __future__ import annotations

from testbed import config


def attack_window_span(rtt: float, retransmit: float, parallel_queries: int) -> float:
    """Total wall-span of the attack window: the last retransmit-spawned
    window opens at `config.MAX_RETRANSMITS * retransmit` and closes at its
    own jittered authoritative arrival, upper-bounded here by
    `rtt * (1 + RTT_JITTER_FRAC)`. `parallel_queries` is accepted for
    interface symmetry with `run_poison_race` -- span does not grow with `q`
    since all `q` windows open at `t=0`."""
    del parallel_queries
    last_retransmit_open = config.MAX_RETRANSMITS * retransmit
    return last_retransmit_open + rtt * (1 + config.RTT_JITTER_FRAC)


def forged_send_times(span: float, send_rate_pps: int) -> list[float]:
    """`floor(span * send_rate_pps)` evenly spaced times in `(0, span)`."""
    count = int(span * send_rate_pps)
    if count <= 0:
        return []
    step = span / count
    return [step * (i + 0.5) for i in range(count)]
