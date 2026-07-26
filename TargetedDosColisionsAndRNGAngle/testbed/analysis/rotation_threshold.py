"""The Exp 5 core (AC-5, AC-7, plan-5 Design "2. Analysis + graphs"):
analytical brute-force reconstruction time vs the empirical crossover from
the rotation-interval sweep. Pure, importable without matplotlib/pandas so
it is offline-checkable (`analysis_check.py`).
"""
from __future__ import annotations

from dataclasses import dataclass


def _saturated(row: dict) -> bool:
    value = row.get("saturated", False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1")


@dataclass(frozen=True)
class RotationThreshold:
    analytical_t_bf_seconds: float
    empirical_threshold_seconds: float | None
    recommendation: str


def t_try_from_reconstruction(elapsed_seconds: float, attempts: int) -> float:
    """Per-attempt cost, calibrated from one partial attacker run-record's
    measured `reconstruction.{elapsed_seconds, attempts}`."""
    if attempts <= 0:
        raise ValueError(f"attempts must be positive, got {attempts}")
    return elapsed_seconds / attempts


def analytical_t_bf(seed_space_bits: int, t_try: float) -> float:
    """Expected brute-force reconstruction time: half the seed space (the
    expected number of attempts to find a match), times the per-attempt cost."""
    return (2**seed_space_bits / 2) * t_try


def empirical_crossover(sweep_rows: list[dict]) -> float | None:
    """`sweep_rows` are Exp 5 summary rows (`rotation_interval`, `saturated`),
    any order. The measured threshold is the largest rotation interval at
    which the attacker still failed (`saturated=False`) -- the slowest
    rotation that still defeats it. `None` if no cell in the sweep failed
    (the attacker always succeeded, no crossover was reached)."""
    failed_intervals = [float(row["rotation_interval"]) for row in sweep_rows if not _saturated(row)]
    return max(failed_intervals) if failed_intervals else None


def rotation_threshold(
    sweep_rows: list[dict], *, seed_space_bits: int, t_try: float
) -> RotationThreshold:
    """Combine the analytical `T_bf` with the sweep's empirical crossover
    into the practitioner one-liner P7 embeds."""
    t_bf = analytical_t_bf(seed_space_bits, t_try)
    crossover = empirical_crossover(sweep_rows)
    recommendation = (
        f"rotate faster than {t_bf:.3g} s given a {seed_space_bits}-bit seed space "
        f"(measured crossover: {'n/a' if crossover is None else f'{crossover:.3g} s'})"
    )
    return RotationThreshold(
        analytical_t_bf_seconds=t_bf, empirical_threshold_seconds=crossover, recommendation=recommendation
    )
