"""D-SCALE run budget (AC-7): the 20-minute wall-clock cap and the first-run sampling caps.

Every CLI adds `add_args(ap)` and calls `check(args)` before doing work. `Deadline` is checked between jobs and
sweep cells; when it fires the caller stops launching work, writes what it has with `truncated: true`, exits 0 and
prints what was skipped (`Deadline.report()`).

    --max-minutes 20  (default; Q6)      --max-minutes 0 = unlimited, accepted only with --full (runbook)
    --shots 4000      (default and cap)  --repeats 15 (default and cap)    (Q9: unlimited later, --full)
"""
from __future__ import annotations

import argparse
import time

MAX_MINUTES = 20.0
SHOTS = 4000
REPEATS = 15


class DeadlineHit(Exception):
    """Raised between circuits of one job when the deadline has passed (a single simulator call is not
    interruptible, so jobs run circuit by circuit)."""


class Deadline:
    def __init__(self, max_minutes: float = MAX_MINUTES):
        self.max_s = float(max_minutes) * 60.0
        self.t0 = time.monotonic()
        self.skipped: list[str] = []

    @property
    def unlimited(self) -> bool:
        return self.max_s <= 0

    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    def remaining(self) -> float:
        return float("inf") if self.unlimited else self.max_s - self.elapsed()

    def expired(self) -> bool:
        return not self.unlimited and self.elapsed() >= self.max_s

    def check(self, what: str) -> None:
        """Raise DeadlineHit (recording `what` as skipped) if the deadline has passed."""
        if self.expired():
            self.skip(what)
            raise DeadlineHit(what)

    def skip(self, what: str) -> None:
        self.skipped.append(what)

    @property
    def truncated(self) -> bool:
        return bool(self.skipped)

    def report(self) -> str:
        if not self.skipped:
            return f"deadline: finished in {self.elapsed():.0f} s (cap {self.max_s / 60:.0f} min)"
        head = ", ".join(self.skipped[:12]) + (f", ... (+{len(self.skipped) - 12})" if len(self.skipped) > 12 else "")
        return (f"deadline: cap {self.max_s / 60:.1f} min reached after {self.elapsed():.0f} s; truncated: true; "
                f"skipped {len(self.skipped)}: {head}")


def add_args(ap: argparse.ArgumentParser, smoke: bool = True) -> None:
    ap.add_argument("--max-minutes", type=float, default=MAX_MINUTES,
                    help="wall-clock cap (default 20; 0 = unlimited, only with --full)")
    ap.add_argument("--shots", type=int, default=SHOTS, help=f"shots per circuit (default and cap {SHOTS})")
    ap.add_argument("--repeats", type=int, default=None,
                    help=f"repeats per result (cap {REPEATS}; default: the command's own, at most {REPEATS})")
    ap.add_argument("--full", action="store_true", help="lift the caps (runbook only)")
    if smoke:
        ap.add_argument("--smoke", action="store_true", help="first cells only, until the deadline")


def check(args: argparse.Namespace, default_repeats: int = REPEATS) -> Deadline:
    """Validate the caps (exit 2 with a message on refusal) and return the run's Deadline."""
    if args.repeats is None:
        args.repeats = min(default_repeats, REPEATS) if not args.full else default_repeats
    if args.max_minutes <= 0 and not args.full:
        raise SystemExit("refused: --max-minutes 0 (unlimited) needs --full (runbook only)")
    if args.max_minutes < 0:
        raise SystemExit("refused: --max-minutes must be >= 0")
    if not args.full and args.shots > SHOTS:
        raise SystemExit(f"refused: --shots {args.shots} > {SHOTS} needs --full (Q9 first-run cap)")
    if not args.full and args.repeats > REPEATS:
        raise SystemExit(f"refused: --repeats {args.repeats} > {REPEATS} needs --full (Q9 first-run cap)")
    if args.shots < 1 or args.repeats < 1:
        raise SystemExit("refused: --shots and --repeats must be >= 1")
    return Deadline(args.max_minutes)
