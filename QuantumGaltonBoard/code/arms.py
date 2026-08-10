#!/usr/bin/env python3
"""
arms.py — Quantum Galton Board: the three-arm runner (`run_arm`).

`run_arm(kind, steps, cfg, seed)` builds `walk.build_walk(steps)` ONCE (AC-2.1)
and dispatches only on the execution backend (epic §3.2). No arm has bespoke
circuit logic.

  ideal : exact statevector of build_walk (qiskit.quantum_info.Statevector,
          .seed(seed), sample_counts). Root-free, QPU-free, aer-free (OQ-2.5).
  noisy : AerSimulator.from_backend(connect(cfg.backend)) — the device noise
          model off the *same* Heron r2 as the hw arm (OQ-5), seed_simulator=seed.
  hw    : live Heron r2 via connect(cfg.backend); best_chain on live calibration
          (AC-2.3), transpile in the caller (opt 3, initial_layout), submit via
          the reused pipeline_common.run_sampler (epic §3.3). Consumes QPU.

Each arm aggregates its raw measurement into a counts dict, decodes it with the
frozen `walk_spec.decode_counts` (P1 source of truth), fills the frozen meta
(pipeline.REQUIRED_META_KEYS), and writes one run.json via pipeline.write_run.

Endianness (OQ-2.2): run_sampler returns per-shot get_bitstrings() strings
(MSB-first); decode_counts reads little-endian as `bits[-(i+1)]`, which already
selects qubit i, so the raw strings are aggregated WITHOUT qtree's s[::-1]
reversal. Pinned by the round-trip assertion in walk_check.py. If a live hw run
ever shows a mirrored histogram, flip here in aggregation only — never edit the
frozen walk_spec.py.
"""

from __future__ import annotations

from collections import Counter

from qiskit.quantum_info import Statevector

import config
import pipeline
from walk import build_walk
from walk_spec import WALK_SPEC, decode_counts


def _base_meta(kind: str, backend: str, steps: int, cfg: config.Config,
               seed: int, sim: bool) -> dict:
    """The frozen meta common to every arm (pipeline.REQUIRED_META_KEYS).

    hw-only slots (qubit_list, chain_stats, calibration) default to None here and
    are filled by the hw branch.
    """
    return {
        "project": "QuantumGaltonBoard",
        "arm": kind,
        "backend": backend,
        "sim": sim,
        "timestamp": pipeline.timestamp(),
        "steps": steps,
        "n_position_qubits": steps + 1,     # n+1 under one-hot (OQ-1)
        "n_qubits": steps + 2,              # position + coin
        "qubit_list": None,                 # hw: best_chain result; else null
        "coin": WALK_SPEC["coin"],
        "shots": cfg.shots,
        "seed": seed,
        "walk_spec": dict(WALK_SPEC),       # embedded verbatim (AC-1.3/AC-2.5)
        "chain_stats": None,                # hw only
        "calibration": None,                # hw only (OQ-2.4)
        "environment": cfg.environment,
    }


def _calibration_snapshot(backend_name: str, stats: dict, timestamp: str) -> dict:
    """hw calibration snapshot built from readable data (OQ-2.4).

    The calibration_snapshot module QuantumLife imports does not exist, so the
    snapshot is assembled from what we can actually read: best_chain's live
    per-chain error stats plus the backend name and submission timestamp. No
    fuller snapshot is fabricated.
    """
    return {
        "backend": backend_name,
        "timestamp": timestamp,
        "chain_twoq_err_mean": stats.get("twoq_err_mean"),
        "chain_twoq_err_max": stats.get("twoq_err_max"),
        "readout_max": stats.get("readout_max"),
        "sx_max": stats.get("sx_max"),
    }


def _write(meta: dict, counts: dict[str, int], quantum_seconds: float,
           jobs_meta: object) -> tuple[str, dict]:
    """Decode, write run.json, return (path, payload)."""
    position_histogram = decode_counts(counts, meta["steps"])
    out_path = pipeline.write_run(
        meta, counts, position_histogram, quantum_seconds=quantum_seconds,
        jobs_meta=jobs_meta)
    payload = {
        "meta": meta,
        "counts": counts,
        "position_histogram": {str(p): v for p, v in position_histogram.items()},
        "quantum_seconds": quantum_seconds,
        "jobs_meta": jobs_meta,
    }
    return out_path, payload


def _run_ideal(qc, steps: int, cfg: config.Config, seed: int) -> tuple[str, dict]:
    """Exact ideal counts via Statevector (root-free, aer-free)."""
    unitary = qc.remove_final_measurements(inplace=False)
    sv = Statevector.from_instruction(unitary)
    sv.seed(seed)
    raw = sv.sample_counts(cfg.shots)
    counts = {str(k): int(v) for k, v in raw.items()}
    meta = _base_meta("ideal", "statevector", steps, cfg, seed, sim=True)
    return _write(meta, counts, quantum_seconds=0.0, jobs_meta=None)


def _run_noisy(qc, steps: int, cfg: config.Config, seed: int) -> tuple[str, dict]:
    """Device-noise-model counts via AerSimulator.from_backend (OQ-5)."""
    from qiskit import transpile           # local: keep ideal path aer-free
    from qiskit_aer import AerSimulator    # noisy arm only (OQ-2.1)

    backend = pipeline.connect(cfg.backend)
    sim = AerSimulator.from_backend(backend)
    isa = transpile(qc, sim, optimization_level=3, seed_transpiler=seed)
    result = sim.run(isa, shots=cfg.shots, seed_simulator=seed).result()
    counts = {str(k): int(v) for k, v in result.get_counts().items()}
    meta = _base_meta("noisy", backend.name, steps, cfg, seed, sim=False)
    return _write(meta, counts, quantum_seconds=0.0, jobs_meta=None)


def _run_hw(qc, steps: int, cfg: config.Config, seed: int) -> tuple[str, dict]:
    """Live Heron r2 submission via the reused pipeline (AC-2.3/AC-2.5)."""
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    from layout import best_chain          # per-study tooling (plan OQ-1.2)

    backend = pipeline.connect(cfg.backend)
    n_qubits = steps + 2
    qubit_list, stats = best_chain(backend, n_qubits)   # live calibration (§3.3)
    pm = generate_preset_pass_manager(
        optimization_level=3, backend=backend, initial_layout=qubit_list)
    isa = pm.run(qc)                                     # transpile in the caller
    bitstrings, jobs_meta, total_qs = pipeline.run_sampler(
        backend, isa, cfg.shots, shots_per_job=cfg.shots_per_job)
    # aggregate per-shot get_bitstrings() WITHOUT reversal (OQ-2.2)
    counts = {k: int(v) for k, v in Counter(bitstrings).items()}
    meta = _base_meta("hw", backend.name, steps, cfg, seed, sim=False)
    meta["qubit_list"] = list(qubit_list)
    meta["chain_stats"] = stats
    meta["calibration"] = _calibration_snapshot(
        backend.name, stats, meta["timestamp"])
    return _write(meta, counts, quantum_seconds=total_qs, jobs_meta=jobs_meta)


_ARMS = {"ideal": _run_ideal, "noisy": _run_noisy, "hw": _run_hw}


def run_arm(kind: str, steps: int, cfg: config.Config,
            seed: int) -> tuple[str, dict]:
    """Build build_walk(steps) once (AC-2.1) and dispatch on the execution arm.

    Returns (run.json path, in-memory payload). `kind` is one of
    ``ideal | noisy | hw``.
    """
    if kind not in _ARMS:
        raise ValueError(f"unknown arm {kind!r}; expected one of {sorted(_ARMS)}")
    qc = build_walk(steps, coin=WALK_SPEC["coin"], encoding=WALK_SPEC["encoding"])
    return _ARMS[kind](qc, steps, cfg, seed)
