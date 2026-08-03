"""The experiment matrix as frozen data (epic §9 P5 Design "experiments/matrix.py"): the
sweep axes over `collect_cell`'s `(kind, effective_bits, send_rate_pps, parallel_queries)`
cell tuple. Data only, no argparse -- `run_experiments.py` only selects and iterates.
Mirrors the ECMP twin's `experiments/matrix.py` shape; deliberate divergence (plan-5
header): no `csv_path` property here -- DNS uses one append-only CSV
(`config.RESULTS_CSV_PATH`), not ECMP's per-cell CSVs.
"""
from __future__ import annotations

from dataclasses import dataclass

from testbed import config
from testbed.draw.sources import DrawKind


@dataclass(frozen=True)
class ExperimentCell:
    """One `collect_cell` invocation's worth of sweep parameters."""

    group: str  # "cliff" | "collapse" | "birthday"
    cell_id: str
    kind: DrawKind
    effective_bits: int
    send_rate_pps: int
    parallel_queries: int

    @property
    def k(self) -> int:
        """Frozen effective-bits <-> k identity (`testbed/resolver/run_metrics.py`): hold
        `TXID_BITS`/`PORT_BITS` fixed, solve `k`."""
        return max(0, config.TXID_BITS + config.PORT_BITS - self.effective_bits)


_BIT_SWEEP = range(config.EFF_BITS_MIN, config.EFF_BITS_MAX + 1, config.EFF_BITS_STEP)
# OQ-P5.1: one fixed send-rate, chosen so g_live ≈ 2^CLIFF_KNEE_BITS puts the
# cliff knee mid-axis (see config.CLIFF_SEND_RATE_PPS). The old 10000 pps left
# g_live ~200 -- three orders below the 2^16 axis floor, so every cell read ≈0.
CLIFF_SEND_RATE = config.CLIFF_SEND_RATE_PPS

# --- M1: entropy cliff -- four sources x the OQ-2 bit sweep (AC-5.1) ---

CLIFF: list[ExperimentCell] = [
    ExperimentCell(
        group="cliff",
        cell_id=f"cliff-{kind}-{eff}",
        kind=kind,
        effective_bits=eff,
        send_rate_pps=CLIFF_SEND_RATE,
        parallel_queries=1,
    )
    for kind in ("fixed", "prng", "csprng", "qrng")
    for eff in _BIT_SWEEP
]

# --- M4: SAD-DNS collapse -- csprng x the SAD-DNS k sweep (AC-5.2) ---

COLLAPSE: list[ExperimentCell] = [
    ExperimentCell(
        group="collapse",
        cell_id=f"collapse-csprng-k{k}",
        kind="csprng",
        effective_bits=config.TXID_BITS + config.PORT_BITS - k,
        send_rate_pps=CLIFF_SEND_RATE,
        parallel_queries=1,
    )
    for k in range(0, config.PORT_BITS + 1)
]

# --- M3: birthday amplification -- data only, no headline figure (OQ-P5.3) ---

BIRTHDAY: list[ExperimentCell] = [
    ExperimentCell(
        group="birthday",
        cell_id=f"birthday-csprng-q{q}",
        kind="csprng",
        effective_bits=config.BIRTHDAY_EFF_BITS,
        send_rate_pps=CLIFF_SEND_RATE,
        parallel_queries=q,
    )
    for q in config.PARALLEL_QUERIES_SWEEP
]

MATRIX: dict[str, list[ExperimentCell]] = {
    "cliff": CLIFF,
    "collapse": COLLAPSE,
    "birthday": BIRTHDAY,
}


def cells_for(group: str) -> list[ExperimentCell]:
    """`group` is one of `cliff`/`collapse`/`birthday`, or `all` for the concatenation."""
    if group == "all":
        return [*CLIFF, *COLLAPSE, *BIRTHDAY]
    if group not in MATRIX:
        raise ValueError(f"unknown experiment group: {group!r}")
    return MATRIX[group]
