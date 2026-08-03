#!/usr/bin/env python3
"""Offline correctness gate for `testbed/attacker/` (project directive -- no
`pytest`). Mirrors the ECMP twin's `collision_check.py` discipline (epic
ss3.6). Root-free, network-free -- no `qrng` kind used here (that's the
opt-in manual-verification step 7)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testbed import config  # noqa: E402
from testbed.attacker.attack import run_poison_race  # noqa: E402
from testbed.attacker.guessing import GuessStream  # noqa: E402
from testbed.draw import sources as sources_mod  # noqa: E402
from testbed.sim.race import _accepts, run_attack_race  # noqa: E402
from testbed.vectors.gen_race_vectors import generate as generate_vectors  # noqa: E402

_checks_run = 0
_checks_failed = 0


def _check(name: str, condition: bool) -> None:
    global _checks_run, _checks_failed
    _checks_run += 1
    if condition:
        print(f"PASS  {name}")
    else:
        _checks_failed += 1
        print(f"FAIL  {name}")


class _ConstGuessStream:
    """Test double: pins the target's rank in the flood's guess order. The
    analytic engine poisons a window iff this rank falls within the `g_live`
    guesses fired -- so a small constant lands inside the budget (poison) and a
    large one falls outside it (miss). `space_size` is large enough here that
    `g_live` is set by the send-rate, not clamped to the space."""

    def __init__(self, value: int, space_size: int = 1 << 20) -> None:
        self.value = value
        self.space_size = space_size

    def reset_round(self) -> None:
        pass

    def next(self) -> int:
        return self.value


def _reset_prng_state() -> None:
    sources_mod._prng_rng = None
    sources_mod._prng_seed = None
    sources_mod._prng_draw_index = 0


def _check_acceptance_rule() -> None:
    # One window, 1s live, 1000 pps => g_live = 1000 guesses fired into it.
    windows_spec = [[(5, 0.0, 1.0)]]

    hit_result = run_attack_race(
        windows_spec=windows_spec,
        guess_stream=_ConstGuessStream(5),  # target rank 5 < g_live=1000 -> fired
        send_rate_pps=1000,
        rtt=1.0,
        retransmit=0.5,
        parallel_queries=1,
        seed=0,
    )
    _check(
        "(a) target within the fired-guess budget poisons",
        hit_result.outcome == "poisoned" and hit_result.poisoned_window == 0,
    )

    miss_result = run_attack_race(
        windows_spec=windows_spec,
        guess_stream=_ConstGuessStream(5000),  # target rank 5000 >= g_live -> never fired
        send_rate_pps=1000,
        rtt=1.0,
        retransmit=0.5,
        parallel_queries=1,
        seed=0,
    )
    _check("(b) target beyond the fired-guess budget never poisons", miss_result.outcome == "resolved_legit")

    _check(
        "(b) run_race's exact-match rule still requires beating the reply (timing, not just match)",
        _accepts(5, 5, 2.0, 1.0) is False and _accepts(5, 5, 0.5, 1.0) is True,
    )


def _check_send_rate_monotonic() -> None:
    common = dict(kind="csprng", port_bits=8, k=8, rtt=0.001, retransmit=0.001, parallel_queries=1)
    low = sum(
        1
        for trial in range(500)
        if run_poison_race(seed=trial, send_rate_pps=2000, **common).outcome == "poisoned"
    )
    high = sum(
        1
        for trial in range(500)
        if run_poison_race(seed=trial, send_rate_pps=300000, **common).outcome == "poisoned"
    )
    _check(
        f"(c) poison count non-decreasing in send-rate (low={low}, high={high})",
        high >= low,
    )


def _check_retransmit_adds_window() -> None:
    """Superset-in-probability argument for the analytic model: a second
    (retransmit) window is an extra independent Bernoulli(g_live/S) trial, so
    across seeds the two-window flood must poison at least as often as the
    one-window flood. Per-window `g_live` is kept well below `S` (65536) so a
    single window's success is far from certain and the extra window's lift is
    visible."""
    common = dict(send_rate_pps=200000, rtt=0.02, retransmit=0.5, parallel_queries=1, seed=0)
    one_window = [[(0, 0.0, 0.02)]]
    two_windows = [[(0, 0.0, 0.02), (0, 0.5, 0.52)]]

    def _count(windows_spec: list) -> int:
        return sum(
            1
            for trial in range(800)
            if run_attack_race(
                windows_spec=windows_spec,
                guess_stream=GuessStream(space_size=65536, state=trial),
                **common,
            ).outcome
            == "poisoned"
        )

    single = _count(one_window)
    double = _count(two_windows)
    _check(
        f"(d) a retransmit round only raises success (one_window={single}, two_windows={double})",
        double >= single,
    )


def _check_birthday_amplification() -> None:
    common = dict(
        kind="csprng", port_bits=0, k=0, rtt=0.001, retransmit=0.001, send_rate_pps=50000
    )
    q1 = sum(
        1
        for trial in range(500)
        if run_poison_race(seed=trial, parallel_queries=1, **common).outcome == "poisoned"
    )
    q8 = sum(
        1
        for trial in range(500)
        if run_poison_race(seed=trial, parallel_queries=8, **common).outcome == "poisoned"
    )
    _check(f"(e) q=8 success exceeds q=1 (q1={q1}, q8={q8})", q8 > q1)


def _check_reproducibility_and_idempotence() -> None:
    _reset_prng_state()
    first = run_poison_race(kind="prng", seed=123, port_bits=8, k=0)
    _reset_prng_state()
    second = run_poison_race(kind="prng", seed=123, port_bits=8, k=0)
    _check("(f) two same-seed run_poison_race calls are byte-identical", first == second)

    vectors_a = generate_vectors()
    vectors_b = generate_vectors()
    _check("(f) gen_race_vectors.py generate() is idempotent", vectors_a == vectors_b)


def main() -> int:
    _check_acceptance_rule()
    _check_send_rate_monotonic()
    _check_retransmit_adds_window()
    _check_birthday_amplification()
    _check_reproducibility_and_idempotence()

    print(f"\n{_checks_run - _checks_failed}/{_checks_run} checks passed")
    if _checks_failed:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
