#!/usr/bin/env python3
"""CLI entry point / smoke driver (AC-1.1 done-when). Runs one or more races
through `sim.race.run_race` and prints per-run outcomes plus a final
PASS/FAIL. Requires no root, no network."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testbed import config  # noqa: E402
from testbed.sim.race import run_race  # noqa: E402
from testbed.types import Draw, DrawProvenance  # noqa: E402

# P1's stub forged guess: a lone off-target guess against the static
# full-entropy draw -- deliberately not equal to config.STATIC_DRAW_*, so
# the authoritative reply wins (epic §5, verification step 1).
STUB_FORGED_GUESS = (1, 1)
STUB_SEND_SCHEDULE = [0.001]


def run_one(trial_seed: int) -> str:
    draw = Draw(config.STATIC_DRAW_TXID, config.STATIC_DRAW_PORT, DrawProvenance())
    result = run_race(
        draw=draw,
        forged_guess=STUB_FORGED_GUESS,
        rtt=config.RTT_SECONDS,
        send_schedule=STUB_SEND_SCHEDULE,
        seed=trial_seed,
    )
    print(
        f"trial={trial_seed} outcome={result.outcome} "
        f"t_outcome={result.t_outcome:.6f} forged_packets={result.forged_packets}"
    )
    return result.outcome


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the DNS poison race (plan-1 skeleton).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true", help="run a single race")
    group.add_argument("--trials", type=int, help="run N races")
    args = parser.parse_args()

    trial_count = 1 if args.smoke else args.trials
    outcomes = [run_one(seed) for seed in range(trial_count)]

    print("PASS" if outcomes else "FAIL")
    return 0 if outcomes else 1


if __name__ == "__main__":
    raise SystemExit(main())
