#!/usr/bin/env python3
"""F5 one-shot hardware study driver — runs ALL steps end to end.

You run this ONE command and walk away. It sequences the tested tools (hardware_batches.py +
submit_batch.py) for you:

    for each batch b in 0..B-1:
        emit b   (both arms: QPY + bundle, fail-closed calibration gate)      [hardware_batches emit]
        submit b (each QPY on the backend -> per-gen counts JSON)             [submit_batch]
        ingest b (counts -> observables run-JSON + persisted state)           [hardware_batches ingest]
        if not last batch: poke                                               [hardware_batches poke]
    report       (adaptation gap + criticality + tau + witness certification) [hardware_batches report]

Nothing here is a hidden auto-submit: YOU launched the whole study. Each underlying tool still
writes-and-stops on its own; this driver just presses the buttons in order.

Run (the thesis config — W=6, mut_scale=0.30, 2 batches x 8 gens, poke at the boundary):
    cd THESIS/CriticalQuantumLife/code
    python run_research.py --backend ibm_kingston

Resume a study that died mid-way (e.g. queue timeout): re-run the SAME command with --start-batch N
to skip batches already ingested (their run-JSONs are on disk).
"""
from __future__ import annotations

import argparse
import functools
import os
import subprocess
import sys

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import session as sess                            # deterministic session id (seed+name)

_RUNS = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))
PY = sys.executable


def _run(cmd: list[str], label: str) -> None:
    """Run a child command, echo it, abort the whole study on any non-zero exit."""
    print(f"\n>>> [{label}] {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=_HERE)
    if res.returncode != 0:
        print(f"[ABORT] step '{label}' failed (exit {res.returncode}); study stopped.")
        raise SystemExit(res.returncode)


def _bundle(name: str, batch: int, arm: str, backend: str) -> str:
    return os.path.join(_RUNS, f"{name}_batch{batch}_{arm}_{backend}_submit.json")


def _counts_paths(prefix: str, n: int) -> list[str]:
    return [f"{prefix}{i}.json" for i in range(n)]


def main() -> None:
    ap = argparse.ArgumentParser(description="F5 one-shot hardware study driver")
    ap.add_argument("--backend", required=True, help="pinned Heron device (e.g. ibm_kingston)")
    ap.add_argument("--width", type=int, default=6)
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=0.30)
    ap.add_argument("--batches", type=int, default=2)
    ap.add_argument("--generations", type=int, default=8, help="per batch")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default="cql_f5")
    ap.add_argument("--poke", type=str, default="inject_stimulus",
                    help="poke kind applied between batches (inject_stimulus|flip_expected|alter_selection)")
    ap.add_argument("--start-batch", dest="start_batch", type=int, default=0,
                    help="skip batches already ingested (resume a died study)")
    args = ap.parse_args()

    session_id = sess.new_session_id(args.seed, args.name)
    hb = ["hardware_batches.py"]
    common = ["--width", str(args.width), "--mut-scale", str(args.mut_scale),
              "--shots", str(args.shots), "--seed", str(args.seed), "--name", args.name]

    print(f"=== F5 study {session_id}: backend={args.backend} W={args.width} "
          f"mut_scale={args.mut_scale} batches={args.batches}x{args.generations}gens "
          f"poke={args.poke} ===")

    for b in range(args.start_batch, args.batches):
        # 1) EMIT both arms (QPY + bundle, calibration gate)
        _run([PY, *hb, "emit", "--backend", args.backend, "--batch", str(b),
              "--arm", "both", *common], f"emit b{b}")

        # 2+3) SUBMIT each arm to QC, then INGEST its counts
        for arm in ("closed", "yoked"):
            bundle = _bundle(args.name, b, arm, args.backend)
            prefix = os.path.join(_RUNS, f"b{b}_{arm}_gen")
            _run([PY, "submit_batch.py", "--bundle", bundle, "--shots", str(args.shots),
                  "--out-prefix", prefix], f"submit b{b} {arm}")
            counts = _counts_paths(prefix, args.generations)
            _run([PY, *hb, "ingest", "--bundle", bundle, "--counts", *counts, *common],
                 f"ingest b{b} {arm}")

        # 4) POKE between batches (not after the last one)
        if b < args.batches - 1 and args.poke.lower() not in ("none", "off"):
            _run([PY, *hb, "poke", "--session", session_id, "--poke", args.poke, *common],
                 f"poke after b{b}")

    # 5) REPORT
    _run([PY, *hb, "report", "--session", session_id, *common], "report")
    print(f"\n=== DONE. Report: {os.path.join(_RUNS, args.name + '_report.json')} ===")
    print("  Read: adaptation_gap.gap (>0 = learning), certification.certified (witness above null),")
    print("        criticality.sigma.mean (->1), relaxation_tau.tau (poke recovery).")


if __name__ == "__main__":
    main()
