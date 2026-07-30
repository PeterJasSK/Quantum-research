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
    """Test double: always returns the same guess index."""

    def __init__(self, value: int) -> None:
        self.value = value

    def next(self) -> int:
        return self.value


def _reset_prng_state() -> None:
    sources_mod._prng_rng = None
    sources_mod._prng_seed = None
    sources_mod._prng_draw_index = 0


def _check_acceptance_rule() -> None:
    windows_spec = [[(5, 0.0, 1.0)]]

    equal_result = run_attack_race(
        windows_spec=windows_spec,
        guess_stream=_ConstGuessStream(5),
        send_rate_pps=1000,
        rtt=1.0,
        retransmit=0.5,
        parallel_queries=1,
        seed=0,
    )
    _check(
        "(a) guess equal to draw poisons before the reply",
        equal_result.outcome == "poisoned" and equal_result.poisoned_window == 0,
    )

    unequal_result = run_attack_race(
        windows_spec=windows_spec,
        guess_stream=_ConstGuessStream(999),
        send_rate_pps=1000,
        rtt=1.0,
        retransmit=0.5,
        parallel_queries=1,
        seed=0,
    )
    _check("(b) guess unequal to draw never poisons", unequal_result.outcome == "resolved_legit")

    _check(
        "(b) correct guess arriving after the reply loses (timing, not just match)",
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
    """Deterministic superset argument: window0's deadline (10.0) dominates
    the span in both runs, so the forged flood (same `GuessStream` seed) is
    byte-identical in both -- the only difference is the extra retransmit
    window. It targets the very first guess the flood will send, with a
    deadline the first packet beats, so adding the retransmit round turns a
    `resolved_legit` into a `poisoned` (never the reverse)."""
    probe = GuessStream(space_size=16, state=42)
    first_guess = probe.next()

    common = dict(send_rate_pps=1000, rtt=0.02, retransmit=0.5, parallel_queries=1, seed=0)
    no_retransmit = run_attack_race(
        windows_spec=[[(999999, 0.0, 10.0)]],
        guess_stream=GuessStream(space_size=16, state=42),
        **common,
    )
    with_retransmit = run_attack_race(
        windows_spec=[[(999999, 0.0, 10.0), (first_guess, 0.0, 0.001)]],
        guess_stream=GuessStream(space_size=16, state=42),
        **common,
    )
    _check(
        f"(d) a retransmit round only raises success "
        f"(no_retransmit={no_retransmit.outcome}, with_retransmit={with_retransmit.outcome})",
        no_retransmit.outcome == "resolved_legit" and with_retransmit.outcome == "poisoned",
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
