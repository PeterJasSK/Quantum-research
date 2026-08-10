#!/usr/bin/env python3
"""
config.py — Quantum Galton Board: the single environment/arg source of truth.

Every tunable (backend, IBM account env, depth range N, shots, seeds, hw-depth
subset, shots-per-job) is read here from os.environ and/or argparse only. No
business-logic module hardcodes these values (epic §4, AC-1.2). Mirrors the
env/arg handling role of QuantumLife's qtree.py without copying its flags.

Precedence for every field: explicit CLI arg > environment variable > default.

IBM account: the saved QiskitRuntimeService account (same one QuantumLife /
CalibrationGuidedHighYieldQRNG use) is picked up by qiskit-ibm-runtime itself.
This module only records the non-secret channel/instance hints if present; it
never reads or stores a token.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Offline default for the max walk depth when no live backend is available
# (OQ-1.4). The hw/noisy arms in P2 override this from the live best_chain
# length; P1's root-free path only needs it to size a smoke run.
DEFAULT_N_MAX = 20
DEFAULT_SHOTS = 4096
DEFAULT_SEEDS = [100, 101, 102]
DEFAULT_HW_DEPTHS = [2, 6, 10, 14]
# Mirror pipeline_common.SHOTS_PER_JOB so the hw arm chunks identically (P2).
DEFAULT_SHOTS_PER_JOB = 50_000


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw not in (None, "") else default


def _env_int_list(name: str, default: list[int]) -> list[int]:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return list(default)
    return [int(x) for x in raw.replace(",", " ").split()]


@dataclass
class Config:
    """Frozen-at-load view of every tunable for one process (AC-1.2)."""

    backend: str | None
    n_max: int
    shots: int
    seeds: list[int]
    hw_depths: list[int]
    shots_per_job: int
    seed: int
    ibm_channel: str | None = None
    ibm_instance: str | None = None
    # non-secret environment hints recorded in run.json.meta.environment
    environment: dict = field(default_factory=dict)


def load(args: object | None = None) -> Config:
    """Merge argparse Namespace (if any) over environment over defaults.

    `args` may expose any of: backend, shots, seed, n_max. Missing/None
    attributes fall back to the matching env var, then the module default.
    """

    def arg(name: str):
        return getattr(args, name, None) if args is not None else None

    backend = arg("backend") or os.environ.get("BACKEND") or None
    n_max = arg("n_max") or _env_int("N_MAX", DEFAULT_N_MAX)
    shots = arg("shots") or _env_int("SHOTS", DEFAULT_SHOTS)
    seeds = _env_int_list("SEEDS", DEFAULT_SEEDS)
    hw_depths = _env_int_list("HW_DEPTHS", DEFAULT_HW_DEPTHS)
    shots_per_job = _env_int("SHOTS_PER_JOB", DEFAULT_SHOTS_PER_JOB)

    seed = arg("seed")
    if seed is None:
        seed = _env_int("SEED", seeds[0] if seeds else DEFAULT_SEEDS[0])

    ibm_channel = os.environ.get("QISKIT_IBM_CHANNEL")
    ibm_instance = os.environ.get("QISKIT_IBM_INSTANCE")

    environment = {
        "BACKEND": os.environ.get("BACKEND"),
        "N_MAX": os.environ.get("N_MAX"),
        "SHOTS": os.environ.get("SHOTS"),
        "SEEDS": os.environ.get("SEEDS"),
        "HW_DEPTHS": os.environ.get("HW_DEPTHS"),
        "SHOTS_PER_JOB": os.environ.get("SHOTS_PER_JOB"),
        "QISKIT_IBM_CHANNEL": ibm_channel,
        "QISKIT_IBM_INSTANCE": ibm_instance,
    }

    return Config(
        backend=backend,
        n_max=n_max,
        shots=shots,
        seeds=seeds,
        hw_depths=hw_depths,
        shots_per_job=shots_per_job,
        seed=seed,
        ibm_channel=ibm_channel,
        ibm_instance=ibm_instance,
        environment=environment,
    )
