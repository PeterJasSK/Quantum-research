"""The experiment matrix as data (plan-5 Design "1. Experiment orchestrator"):
a frozen list of `ExperimentCell`s, each carrying the env vector `harness.py`
sets before boot plus the attacker CLI args. Which cells run is inspectable
here without reading any orchestration code -- `run_experiments.py` only
selects and iterates.

Groups: `exp1`..`exp5` (the five experiments, AC-1-5) plus `graph1` (the
9-cell salt-source x knowledge-level grid, AC-6, OQ-3 -- `exp4`'s a/b/c cells
double as the three `full`-knowledge grid cells so nothing is minted twice).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from testbed.config import (
    KNOWLEDGE_LEVELS,
    PRNG_SEED,
    RESULTS_DIR,
    ROTATION_SWEEP_INTERVALS,
    SALT_SOURCES,
    TARGET_LINK,
)

AttackerLevel = Literal["full", "partial", "blind"]
AttackerMode = Literal["volumetric", "precision"]


@dataclass(frozen=True)
class ExperimentCell:
    """One live run = one fixed env vector -> one tagged CSV. `attack_mode`
    is `None` for the Exp 4d clean-background cells (no attacker launch)."""

    experiment: str  # "exp1".."exp5" | "graph1"
    cell_id: str
    salt_kind: str  # "prng" | "csprng" | "qrng"
    rotation_interval: float  # 0 = off
    defences_enabled: bool
    knowledge_level: str  # KNOWLEDGE_LEVELS entry, or "na" for exp4d/exp5
    attack_mode: str | None  # AttackerMode, or None = no attacker (exp4d)
    target_link: int = TARGET_LINK
    prng_seed: int = PRNG_SEED
    attacker_level: AttackerLevel | None = None
    attacker_count: int = 500
    needs_salt: bool = False  # full-knowledge attacker: --salt from salt_handoff
    needs_oracle: bool = False  # partial-knowledge attacker: --oracle-salt from salt_handoff
    expected_saturated: bool | None = None  # None = no PASS/FAIL classification (exp4d/exp5)
    notes: str = ""

    @property
    def csv_path(self) -> str:
        return os.path.join(RESULTS_DIR, self.experiment, f"{self.cell_id}.csv")


def _full_cell(experiment: str, cell_id: str, *, salt_kind: str, rotation_interval: float,
               defences_enabled: bool, expected_saturated: bool | None, notes: str) -> ExperimentCell:
    return ExperimentCell(
        experiment=experiment,
        cell_id=cell_id,
        salt_kind=salt_kind,
        rotation_interval=rotation_interval,
        defences_enabled=defences_enabled,
        knowledge_level="full",
        attack_mode="precision",
        attacker_level="full",
        needs_salt=True,
        expected_saturated=expected_saturated,
        notes=notes,
    )


def _partial_cell(cell_id: str, *, salt_kind: str, rotation_interval: float,
                   expected_saturated: bool | None) -> ExperimentCell:
    return ExperimentCell(
        experiment="graph1",
        cell_id=cell_id,
        salt_kind=salt_kind,
        rotation_interval=rotation_interval,
        defences_enabled=False,
        knowledge_level="partial",
        attack_mode="precision",
        attacker_level="partial",
        needs_oracle=True,
        expected_saturated=expected_saturated,
        notes="graph1 grid cell (AC-6)",
    )


def _blind_cell(cell_id: str, *, salt_kind: str, rotation_interval: float) -> ExperimentCell:
    return ExperimentCell(
        experiment="graph1",
        cell_id=cell_id,
        salt_kind=salt_kind,
        rotation_interval=rotation_interval,
        defences_enabled=False,
        knowledge_level="blind",
        attack_mode="precision",
        attacker_level="blind",
        expected_saturated=False,
        notes="graph1 grid cell -- expected-failure baseline (AC-6)",
    )


# --- Exp 1-3 (AC-1-3): defences ON, prng, rotation off ---

EXP1_VOLUMETRIC = ExperimentCell(
    experiment="exp1",
    cell_id="exp1_volumetric_baseline",
    salt_kind="prng",
    rotation_interval=0.0,
    defences_enabled=True,
    knowledge_level="full",
    attack_mode="volumetric",
    attacker_level="full",
    needs_salt=True,
    expected_saturated=False,
    notes="AC-1: naive flood degraded, defences fire",
)

EXP2_PRECISION_RATE_LIMIT = _full_cell(
    "exp2", "exp2_precision_vs_ratelimit",
    salt_kind="prng", rotation_interval=0.0, defences_enabled=True,
    expected_saturated=True, notes="AC-2: precision evades rate limiting",
)

EXP3_PRECISION_THROTTLE = _full_cell(
    "exp3", "exp3_precision_vs_throttle",
    salt_kind="prng", rotation_interval=0.0, defences_enabled=True,
    expected_saturated=True, notes="AC-3: precision evades throttling (5-tuples spread)",
)

# --- Exp 4 (AC-4): full attacker, defences off, three salt configs + clean bg ---

EXP4A_PRNG_NO_ROTATION = _full_cell(
    "exp4", "exp4a_prng_no_rotation",
    salt_kind="prng", rotation_interval=0.0, defences_enabled=False,
    expected_saturated=True, notes="weak PRNG, no rotation -- attack succeeds",
)

EXP4B_CSPRNG_ROTATION = _full_cell(
    "exp4", "exp4b_csprng_rotation",
    salt_kind="csprng", rotation_interval=5.0, defences_enabled=False,
    expected_saturated=False, notes="CSPRNG + rotation -- attack fails",
)

EXP4C_QRNG_ROTATION = _full_cell(
    "exp4", "exp4c_qrng_rotation",
    salt_kind="qrng", rotation_interval=5.0, defences_enabled=False,
    expected_saturated=False, notes="QRNG + rotation -- fails, identical to 4b (null result)",
)

EXP4D_CLEAN_BACKGROUND = [
    ExperimentCell(
        experiment="exp4",
        cell_id=f"exp4d_clean_{salt_kind}",
        salt_kind=salt_kind,
        rotation_interval=5.0,
        defences_enabled=False,
        knowledge_level="na",
        attack_mode=None,
        expected_saturated=False,
        notes="clean bg traffic only -- rotation cost-free when no attack",
    )
    for salt_kind in SALT_SOURCES
]

EXP4 = [EXP4A_PRNG_NO_ROTATION, EXP4B_CSPRNG_ROTATION, EXP4C_QRNG_ROTATION, *EXP4D_CLEAN_BACKGROUND]

# --- Exp 5 (AC-5): partial attacker, csprng, rotation-interval sweep ---

EXP5_SWEEP = [
    ExperimentCell(
        experiment="exp5",
        cell_id=f"exp5_rotation_{str(interval).replace('.', '_')}s",
        salt_kind="csprng",
        rotation_interval=interval,
        defences_enabled=False,
        knowledge_level="partial",
        attack_mode="precision",
        attacker_level="partial",
        needs_oracle=True,
        expected_saturated=None,  # the point of the sweep -- not a fixed expectation
        notes="Exp 5 rotation-frequency sweep (OQ-4)",
    )
    for interval in ROTATION_SWEEP_INTERVALS
]

# --- Graph 1 (AC-6, OQ-3): 9-cell salt-source x knowledge-level grid ---
# full-knowledge cells reuse exp4a/b/c (same env vector, same salt) so no
# cell is minted twice; partial/blind are the six new cells below.

GRAPH1_PARTIAL = [
    _partial_cell("graph1_prng_partial", salt_kind="prng", rotation_interval=0.0, expected_saturated=True),
    _partial_cell("graph1_csprng_partial", salt_kind="csprng", rotation_interval=5.0, expected_saturated=False),
    _partial_cell("graph1_qrng_partial", salt_kind="qrng", rotation_interval=5.0, expected_saturated=False),
]

GRAPH1_BLIND = [
    _blind_cell("graph1_prng_blind", salt_kind="prng", rotation_interval=0.0),
    _blind_cell("graph1_csprng_blind", salt_kind="csprng", rotation_interval=5.0),
    _blind_cell("graph1_qrng_blind", salt_kind="qrng", rotation_interval=5.0),
]

GRAPH1_FULL = [EXP4A_PRNG_NO_ROTATION, EXP4B_CSPRNG_ROTATION, EXP4C_QRNG_ROTATION]

GRAPH1 = [*GRAPH1_FULL, *GRAPH1_PARTIAL, *GRAPH1_BLIND]

assert set(KNOWLEDGE_LEVELS) == {"full", "partial", "blind"}
assert len(GRAPH1) == len(SALT_SOURCES) * len(KNOWLEDGE_LEVELS) == 9

MATRIX: dict[str, list[ExperimentCell]] = {
    "exp1": [EXP1_VOLUMETRIC],
    "exp2": [EXP2_PRECISION_RATE_LIMIT],
    "exp3": [EXP3_PRECISION_THROTTLE],
    "exp4": EXP4,
    "exp5": EXP5_SWEEP,
    "graph1": GRAPH1,
}


def cells_for(selector: str) -> list[ExperimentCell]:
    """`selector` is one of `1`..`5`, `all`, or (internal) `graph1`."""
    if selector == "all":
        seen_ids: set[str] = set()
        cells: list[ExperimentCell] = []
        for group in ("exp1", "exp2", "exp3", "exp4", "exp5", "graph1"):
            for cell in MATRIX[group]:
                if cell.cell_id in seen_ids:
                    continue
                seen_ids.add(cell.cell_id)
                cells.append(cell)
        return cells
    key = selector if selector.startswith("exp") else f"exp{selector}"
    if key not in MATRIX:
        raise ValueError(f"unknown experiment selector: {selector!r}")
    return MATRIX[key]
