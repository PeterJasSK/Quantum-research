#!/usr/bin/env python3
"""Critical Quantum Life — F7: the fault-injection coverage study (AC-F7.4, AC-F7.7).

Runs the Canary probe across the labelled fault menu (fault_injection.FAULTS) and, for each
fault, measures how many cycles after onset the Canary raises an alert versus a simple
RB/coherence-style incumbent that thresholds only on the reported 2q/readout numbers. The
deliverable is an honest COVERAGE MAP: where the Canary wins (entanglement-visible faults the
incumbent's 2q/readout numbers miss), where it ties, and where it LOSES (readout drift the
incumbent catches at onset — RB territory). Losses are reported as loudly as wins (AC-F7.7).

No speed claim, no classical-hardness claim. The incumbent is a documented threshold proxy,
not a real RB run (plan §10 Q4).

Run:
    cd THESIS/CriticalQuantumLife/code
    python canary_coverage.py --cycles 24 --shots 4096 --width 6
"""
from __future__ import annotations

import argparse
import functools
import json
import os
from typing import Any

import closed_loop as cl
import fault_injection as fi
from canary_probe import CanaryProbe

print = functools.partial(print, flush=True)

# Incumbent RB/coherence proxy thresholds (what a gate-fidelity dashboard alarms on).
BASELINE_TWOQ_THRESHOLD = 0.02
BASELINE_READOUT_THRESHOLD = 0.05


def baseline_detector(record: dict[str, Any]) -> bool:
    """The incumbent alarm: fires when the REPORTED 2q or readout error breaches threshold.
    Blind to any fault that leaves those two numbers unchanged."""
    return (record["twoq_err"] > BASELINE_TWOQ_THRESHOLD
            or record["readout_err"] > BASELINE_READOUT_THRESHOLD)


def _latency(fired_cycle: int | None, onset: int) -> int | None:
    """Cycles from fault onset to first alarm; None if never fired."""
    return None if fired_cycle is None else max(0, fired_cycle - onset)


def run_fault(fault: fi.Fault, cycles: int, width: int, shots: int,
              seed: int) -> dict[str, Any]:
    """Probe one fault: healthy until `fault.onset`, faulted after. Return the coverage row."""
    probe = CanaryProbe(width=width, shots=shots, seed=seed)
    canary_fired: int | None = None
    baseline_fired: int | None = None
    false_positives = 0
    for _ in range(cycles):
        probe.fault = fault if probe.t + 1 >= fault.onset else None
        record = probe.cycle()
        c = record["cycle"]
        if record["alert"] is not None:
            if c < fault.onset:
                false_positives += 1
            elif canary_fired is None:
                canary_fired = c
        if baseline_detector(record) and c >= fault.onset and baseline_fired is None:
            baseline_fired = c

    canary_lat = _latency(canary_fired, fault.onset)
    baseline_lat = _latency(baseline_fired, fault.onset)
    verdict = _verdict(canary_lat, baseline_lat)
    pre = max(1, fault.onset - 1)
    specificity = 1.0 - (false_positives / pre)
    return {
        "id": fault.id,
        "kind": fault.kind,
        "magnitude": fault.magnitude,
        "onset": fault.onset,
        "canary_latency": canary_lat,
        "baseline_latency": baseline_lat,
        "canary_specificity": round(specificity, 3),
        "verdict": verdict,
        "note": fault.note,
    }


def _verdict(canary: int | None, baseline: int | None) -> str:
    """win = Canary catches something the incumbent misses or catches sooner; lose = the
    incumbent is faster (RB territory); tie = same latency; miss-both = neither fires."""
    if canary is None and baseline is None:
        return "miss-both"
    if canary is None:
        return "lose"
    if baseline is None:
        return "win"
    if canary < baseline:
        return "win"
    if canary > baseline:
        return "lose"
    return "tie"


def run_coverage(cycles: int, width: int, shots: int, seed: int) -> dict[str, Any]:
    rows = [run_fault(f, cycles, width, shots, seed) for f in fi.FAULTS]
    tally: dict[str, int] = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    return {"config": {"cycles": cycles, "width": width, "shots": shots, "seed": seed},
            "faults": rows, "summary": tally}


def _fmt(lat: int | None) -> str:
    return "miss" if lat is None else str(lat)


def _print_table(cov: dict[str, Any]) -> None:
    print(f"\n  {'fault':22} {'kind':22} {'canary':>7} {'baseline':>9} {'spec':>5}  verdict")
    print("  " + "-" * 78)
    for r in cov["faults"]:
        print(f"  {r['id']:22} {r['kind']:22} {_fmt(r['canary_latency']):>7} "
              f"{_fmt(r['baseline_latency']):>9} {r['canary_specificity']:>5.2f}  {r['verdict']}")
    print(f"\n  summary: {cov['summary']}")
    print("  latency = cycles from fault onset to first alarm (lower is better; 'miss' = never)")
    print("  Canary WINS on entanglement-visible faults the incumbent's 2q/readout numbers miss;")
    print("  LOSES on readout drift the incumbent catches at onset (RB already covers that).")


def write_coverage(cov: dict[str, Any]) -> str:
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(cl.OUTPUT_DIR, "canary_coverage.json")
    with open(path, "w") as f:
        json.dump(cov, f, indent=2, default=str)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F7 — Canary fault-injection coverage study")
    ap.add_argument("--cycles", type=int, default=24)
    ap.add_argument("--width", type=int, default=6)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=100)
    args = ap.parse_args()

    print(f"=== CQL F7 coverage: {len(fi.FAULTS)} faults, {args.cycles} cycles, "
          f"W={args.width}, shots={args.shots} ===")
    cov = run_coverage(args.cycles, args.width, args.shots, args.seed)
    _print_table(cov)
    print(f"\n  -> {write_coverage(cov)}")


if __name__ == "__main__":
    main()
