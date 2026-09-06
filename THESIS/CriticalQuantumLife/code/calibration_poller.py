#!/usr/bin/env python3
"""Critical Quantum Life — F7: the zero-credit calibration poller.

The FREE health layer. Reads a real IBM backend's PUBLISHED calibration metadata
(`backend.target` / `.properties()` / `.status()`) — two-qubit gate error, readout error,
T1/T2, operational flag, queue depth — and writes a time-series to research_runs/. This is
the incumbent RB/coherence dashboard: it costs NOTHING because no circuit is submitted, no
shots are billed. It is metadata only.

What it CANNOT give (by design): the entanglement witness heartbeat. That needs a real
circuit run = shots billed (the COST layer, run on an allocation — see plans/RUNLOG-real-QC.md).
The whole thesis is that the witness is the blind spot the free numbers miss; this poller is
the honest free baseline beside it, not a substitute.

Run (real, zero credits — needs a configured QiskitRuntimeService account):
    python calibration_poller.py --backend ibm_kingston --once
    python calibration_poller.py --backend ibm_kingston --interval 900 --cycles 96   # every 15m for a day
    python calibration_poller.py --demo                                              # offline synthetic sample
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import statistics
import sys
import time
from datetime import datetime
from typing import Any

import closed_loop as cl                          # for OUTPUT_DIR + the artificial-life path (_AL)
if cl._AL not in sys.path:
    sys.path.insert(0, cl._AL)
import layout                                      # best_chain: reuse the low-error chain picker

print = functools.partial(print, flush=True)

DEAD_EDGE_ERR = 1.0        # a 2q error of exactly 1.0 = a broken / non-calibrated edge
DEAD_READOUT = 0.5         # readout error >= 0.5 = a dead qubit (coin flip)


def connect(name: str) -> Any:
    """Live QiskitRuntimeService backend handle. Metadata only — no job is ever submitted."""
    from qiskit_ibm_runtime import QiskitRuntimeService
    return QiskitRuntimeService().backend(name)


def _two_qubit_errors(backend: Any) -> tuple[str, list[float], int]:
    """Per-edge 2q gate errors from the target. Returns (gate_name, live_errors, n_dead)."""
    tgt = backend.target
    gate = next((g for g in ("cz", "ecr", "cx") if g in tgt.operation_names), None)
    if gate is None:
        return "none", [], 0
    live: list[float] = []
    dead = 0
    for qargs, props in tgt[gate].items():
        if not qargs or len(qargs) != 2:
            continue
        e = getattr(props, "error", None)
        if e is None:
            continue
        if e >= DEAD_EDGE_ERR:
            dead += 1
        else:
            live.append(float(e))
    return gate, live, dead


def _readout_errors(backend: Any) -> tuple[list[float], int]:
    """Per-qubit readout (measure) errors from the target. Returns (live_errors, n_dead)."""
    tgt = backend.target
    live: list[float] = []
    dead = 0
    for q in range(backend.num_qubits):
        try:
            e = getattr(tgt["measure"][(q,)], "error", None)
        except Exception:
            e = None
        if e is None:
            continue
        if e >= DEAD_READOUT:
            dead += 1
        else:
            live.append(float(e))
    return live, dead


def _coherence(backend: Any, qubits: list[int]) -> dict[str, float | None]:
    """Mean T1/T2 (µs) over `qubits` from backend.properties(). None if unavailable."""
    props = backend.properties()
    if props is None:
        return {"t1_us_mean": None, "t2_us_mean": None}
    t1s, t2s = [], []
    for q in qubits:
        try:
            t1s.append(props.t1(q) * 1e6)
            t2s.append(props.t2(q) * 1e6)
        except Exception:
            continue
    return {"t1_us_mean": round(statistics.fmean(t1s), 1) if t1s else None,
            "t2_us_mean": round(statistics.fmean(t2s), 1) if t2s else None}


def poll(backend: Any, chain_n: int) -> dict[str, Any]:
    """One zero-credit calibration sample (metadata only). Reports GLOBAL live-edge/qubit
    aggregates plus CHAIN-scoped numbers over the best length-`chain_n` chain (what the Canary
    would actually run on) so dead-qubit outliers don't dominate the health signal."""
    st = backend.status()
    gate, two_live, two_dead = _two_qubit_errors(backend)
    ro_live, ro_dead = _readout_errors(backend)

    chain: list[int] = []
    chain_stats: dict[str, Any] = {}
    coherence: dict[str, Any] = {"t1_us_mean": None, "t2_us_mean": None}
    try:
        chain, cstats = layout.best_chain(backend, chain_n)
        chain_stats = {"twoq_err_mean": cstats.get("twoq_err_mean"),
                       "twoq_err_max": cstats.get("twoq_err_max"),
                       "readout_max": cstats.get("readout_max")}
        coherence = _coherence(backend, chain)
    except Exception as exc:
        chain_stats = {"_error": str(exc)}

    return {
        "timestamp": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "backend": backend.name,
        "num_qubits": backend.num_qubits,
        "operational": bool(st.operational),
        "pending_jobs": int(st.pending_jobs),
        "twoq_gate": gate,
        "twoq_err_mean": round(statistics.fmean(two_live), 5) if two_live else None,
        "twoq_err_max_live": round(max(two_live), 5) if two_live else None,
        "twoq_dead_edges": two_dead,
        "readout_err_mean": round(statistics.fmean(ro_live), 5) if ro_live else None,
        "readout_err_max_live": round(max(ro_live), 5) if ro_live else None,
        "readout_dead_qubits": ro_dead,
        "chain_n": chain_n,
        "chain": chain,
        "chain_stats": chain_stats,
        "t1_us_mean": coherence["t1_us_mean"],
        "t2_us_mean": coherence["t2_us_mean"],
        "credits": 0,
        "source": "backend.target/properties/status (metadata only, no job submitted)",
    }


def demo_sample(chain_n: int) -> dict[str, Any]:
    """Offline synthetic sample (no account needed) so the web wiring can be exercised."""
    return {
        "timestamp": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "backend": "demo_heron", "num_qubits": 156, "operational": True, "pending_jobs": 7,
        "twoq_gate": "cz", "twoq_err_mean": 0.0072, "twoq_err_max_live": 0.031,
        "twoq_dead_edges": 3, "readout_err_mean": 0.0138, "readout_err_max_live": 0.089,
        "readout_dead_qubits": 1, "chain_n": chain_n, "chain": list(range(chain_n)),
        "chain_stats": {"twoq_err_mean": 0.0061, "twoq_err_max": 0.0102, "readout_max": 0.0152},
        "t1_us_mean": 271.0, "t2_us_mean": 188.0, "credits": 0,
        "source": "DEMO synthetic sample (no backend contacted)",
    }


def artifact_path(backend_name: str) -> str:
    return os.path.join(cl.OUTPUT_DIR, f"canary_calibration_{backend_name}.json")


def append_sample(sample: dict[str, Any]) -> str:
    """Append the sample to the backend's calibration time-series in research_runs/."""
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    path = artifact_path(sample["backend"])
    series: dict[str, Any] = {"backend": sample["backend"], "samples": []}
    if os.path.exists(path):
        try:
            with open(path) as f:
                series = json.load(f)
        except Exception:
            pass
    series["samples"].append(sample)
    with open(path, "w") as f:
        json.dump(series, f, indent=2, default=str)
    return path


def _print_sample(s: dict[str, Any]) -> None:
    print(f"  [{s['timestamp']}] {s['backend']} ({s['num_qubits']}q)  "
          f"operational={s['operational']}  queue={s['pending_jobs']}")
    print(f"    global : 2q_err mean {s['twoq_err_mean']}  max_live {s['twoq_err_max_live']}  "
          f"(dead edges {s['twoq_dead_edges']})")
    print(f"             readout mean {s['readout_err_mean']}  max_live {s['readout_err_max_live']}  "
          f"(dead qubits {s['readout_dead_qubits']})")
    print(f"    chain-{s['chain_n']}: {s['chain_stats']}")
    print(f"    coherence: T1 {s['t1_us_mean']}µs  T2 {s['t2_us_mean']}µs   credits={s['credits']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F7 — zero-credit calibration poller")
    ap.add_argument("--backend", type=str, default=None, help="e.g. ibm_kingston")
    ap.add_argument("--chain", dest="chain_n", type=int, default=6,
                    help="length of the best-chain the Canary would run on (chain-scoped stats)")
    ap.add_argument("--interval", type=int, default=None, help="seconds between polls (repeat mode)")
    ap.add_argument("--cycles", type=int, default=1, help="number of polls (ignored if --once)")
    ap.add_argument("--once", action="store_true", help="single poll and exit")
    ap.add_argument("--demo", action="store_true", help="offline synthetic sample (no account)")
    args = ap.parse_args()

    if args.demo:
        s = demo_sample(args.chain_n)
        _print_sample(s)
        print(f"  -> {append_sample(s)}")
        return

    if not args.backend:
        print("[ABORT] --backend NAME required (or use --demo). e.g. --backend ibm_kingston")
        raise SystemExit(1)

    backend = connect(args.backend)
    n = 1 if args.once else args.cycles
    for i in range(n):
        s = poll(backend, args.chain_n)
        _print_sample(s)
        print(f"  -> {append_sample(s)}")
        if args.interval and i < n - 1:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
