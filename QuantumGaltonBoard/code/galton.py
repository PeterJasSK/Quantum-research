#!/usr/bin/env python3
"""
galton.py — Quantum Galton Board: CLI entry (arg wiring only).

P2 replaces P1's placeholder 2-bin reference walk with the real DTQW: the
circuit lives in walk.build_walk and the three execution arms in arms.run_arm.
This file is arg wiring only — it parses flags, builds the Config, and drives
run_arm; it holds no circuit or execution logic.

Arms (epic §3.2, one circuit, backend-only difference):
  --arm ideal   root-free exact Statevector (default; no IBM account, no QPU)
  --arm noisy   AerSimulator.from_backend device noise model (needs qiskit-aer
                and a saved IBM account for the backend's calibration)
  --arm hw      live Heron r2 (consumes QPU). Loops config.hw_depths ×
                config.seeds (AC-2.3), re-picking best_chain on live calibration
                per submission; --steps is ignored for hw.

  --sweep       ideal/noisy convenience: loop steps 2..config.n_max at one seed
                (manual inspection only; the full sweep matrix + summary.json are
                P4, not aggregated here).

Every tunable is read through config.py (AC-1.2).
"""

from __future__ import annotations

import argparse

import arms
import config


def _run_hw_matrix(cfg: config.Config) -> list[str]:
    """AC-2.3: one hw run per (depth, seed); best_chain re-picked live each time."""
    paths: list[str] = []
    for depth in cfg.hw_depths:
        for seed in cfg.seeds:
            path, _ = arms.run_arm("hw", depth, cfg, seed)
            print(path)
            paths.append(path)
    return paths


def _run_sweep(arm: str, cfg: config.Config) -> list[str]:
    """ideal/noisy manual sweep 2..n_max at cfg.seed (P4 owns the real matrix)."""
    paths: list[str] = []
    for depth in range(2, cfg.n_max + 1):
        path, _ = arms.run_arm(arm, depth, cfg, cfg.seed)
        print(path)
        paths.append(path)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="Quantum Galton Board (P2 arms)")
    ap.add_argument("--steps", type=int, default=2)
    ap.add_argument("--shots", type=int, default=None)
    ap.add_argument("--backend", type=str, default=None)
    ap.add_argument("--sim", action="store_true",
                    help="root-free ideal arm (informational; --arm ideal is root-free)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--arm", type=str, default="ideal",
                    choices=["ideal", "noisy", "hw"])
    ap.add_argument("--sweep", action="store_true",
                    help="ideal/noisy: loop steps 2..N (manual; P4 owns the matrix)")
    args = ap.parse_args()

    cfg = config.load(args)

    if args.arm == "hw":
        _run_hw_matrix(cfg)
    elif args.sweep:
        _run_sweep(args.arm, cfg)
    else:
        path, _ = arms.run_arm(args.arm, args.steps, cfg, cfg.seed)
        print(path)


if __name__ == "__main__":
    main()
