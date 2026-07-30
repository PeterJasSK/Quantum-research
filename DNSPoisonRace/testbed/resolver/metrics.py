"""Five-metric collector (epic §9 P4, AC-4.1-4.4). The only module that
calls `run_poison_race` -- P4 never re-implements the draw/race (epic §3.5),
it loops and aggregates.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from testbed import config
from testbed.attacker.attack import run_poison_race
from testbed.draw.sources import DrawKind
from testbed.types import DrawProvenance


@dataclass(frozen=True)
class CellRecord:
    """One row's worth of data for one `(kind, effective_bits, send_rate_pps,
    parallel_queries)` cell -- frozen for P5 (epic §9 P4 Interfaces)."""

    kind: str
    effective_bits: int
    k: int
    send_rate_pps: int
    parallel_queries: int
    trials: int
    poison_rate: float
    mean_forged_packets: float
    mean_time_to_poison: float | None
    amplification_factor: float | None
    provenance: DrawProvenance


def collect_cell(
    kind: DrawKind,
    *,
    txid_bits: int = config.TXID_BITS,
    port_bits: int = config.PORT_BITS,
    k: int,
    send_rate_pps: int,
    parallel_queries: int,
    trials: int = config.TRIALS_PER_CELL,
    seed: int,
) -> CellRecord:
    """Run `run_poison_race` `trials` times at one cell and aggregate M1
    (poison probability), M2 (mean forged packets / mean time-to-poison
    among poisoned trials), carrying `k`/`effective_bits` and the first
    trial's provenance through unchanged (AC-4.4/AC-4.5). Distinct seed per
    trial (`seed + trial_index`) -- reproducible as a whole cell, never
    repeating one race `trials` times (OQ-P4.1). `amplification_factor` is
    left `None` here -- filled in by the caller once a baseline cell's
    `poison_rate` is known."""
    forged_packets: list[int] = []
    times_to_poison: list[float] = []
    poisoned_count = 0
    first_provenance: DrawProvenance | None = None

    for trial_index in range(trials):
        result = run_poison_race(
            kind,
            txid_bits=txid_bits,
            port_bits=port_bits,
            k=k,
            send_rate_pps=send_rate_pps,
            parallel_queries=parallel_queries,
            seed=seed + trial_index,
        )
        if first_provenance is None:
            first_provenance = result.provenance
        forged_packets.append(result.forged_packets)
        if result.outcome == "poisoned":
            poisoned_count += 1
            times_to_poison.append(result.t_outcome)

    assert first_provenance is not None  # trials >= 1 guarantees at least one call

    return CellRecord(
        kind=kind,
        effective_bits=result.effective_bits,
        k=k,
        send_rate_pps=send_rate_pps,
        parallel_queries=parallel_queries,
        trials=trials,
        poison_rate=poisoned_count / trials,
        mean_forged_packets=statistics.fmean(forged_packets),
        mean_time_to_poison=statistics.fmean(times_to_poison) if times_to_poison else None,
        amplification_factor=None,
        provenance=first_provenance,
    )


def amplification_factor(
    poison_rate_q: float, poison_rate_baseline: float
) -> float | None:
    """M3 birthday amplification factor vs a `parallel_queries=1` baseline
    cell (AC-4.3). `None` guard on a zero baseline -- division-by-zero
    guard, not a crash."""
    if poison_rate_baseline == 0.0:
        return None
    return poison_rate_q / poison_rate_baseline
