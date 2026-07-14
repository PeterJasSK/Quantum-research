#!/usr/bin/env python3
"""
emit_quality_pdf.py — EPIC 1, S1.5 (AC-8). Assembles the baseline
_processed.txt (Stage A --select all) and a calibration-optimal harvested
stream (top-N Stage A qubits, each truncated to its Stage B usable depth),
then shells out to the existing ErrorDetectionVSRawBits/qrng_compare.py CLI
to produce the native PDF (E1) — no reimplementation of the report.

USAGE
    python emit_quality_pdf.py <baseline_processed.txt> <stageb_raw.json> \\
                                <usable_depth.json> [--top-qubits q,q,...]

OUTPUT
    results/optimal_harvested_<backend>_<ts>_processed.txt
    results/qrng_compare_<backend>_<ts>.pdf
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any

from eval_common import RESULTS_DIR, load_run, reconstruct_stage_b, stem_of

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BATTERY_CLI = os.path.join(_REPO_ROOT, "ErrorDetectionVSRawBits", "qrng_compare.py")


def load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def build_optimal_stream(stageb_raw: dict[str, Any], usable_depth: dict[str, Any],
                          top_qubits: list[int] | None) -> str:
    """Top-N qubits (or every qubit in usable_depth if not given), each
    truncated to its own usable depth, concatenated per qubit."""
    streams = reconstruct_stage_b(stageb_raw)
    qubits = top_qubits if top_qubits else sorted(int(q) for q in usable_depth)
    parts = []
    for q in qubits:
        depth = usable_depth[str(q)]["usable_depth"]
        if depth == 0:
            continue
        key = (q, depth)
        if key in streams:
            parts.append(streams[key])
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the calibration-optimal harvested stream and run the battery PDF report.")
    parser.add_argument("baseline_processed_txt")
    parser.add_argument("stageb_raw_json")
    parser.add_argument("usable_depth_json")
    parser.add_argument("--top-qubits", type=str, default=None,
                         help="comma-separated qubit list (default: every qubit in usable_depth_json)")
    args = parser.parse_args()

    stageb_raw = load_run(args.stageb_raw_json)
    usable_depth = load_json(args.usable_depth_json)
    top_qubits = ([int(q) for q in args.top_qubits.split(",") if q]
                  if args.top_qubits else None)

    optimal_stream = build_optimal_stream(stageb_raw, usable_depth, top_qubits)
    if not optimal_stream:
        print("No usable depth > 0 for any selected qubit — nothing to harvest.")
        sys.exit(1)

    stem = stem_of(args.stageb_raw_json)
    optimal_stem = f"{RESULTS_DIR}/optimal_harvested_{stem[len('stageb_'):]}" \
        if stem.startswith("stageb_") else f"{RESULTS_DIR}/optimal_harvested_{stem}"
    optimal_txt = f"{optimal_stem}_processed.txt"
    with open(optimal_txt, "w") as f:
        f.write("bits:" + optimal_stream + "\n")
    print(f"Wrote {optimal_txt} ({len(optimal_stream):,} bits)")

    pdf_path = f"{RESULTS_DIR}/qrng_compare_{stem[len('stageb_'):] if stem.startswith('stageb_') else stem}.pdf"

    cmd = [sys.executable, _BATTERY_CLI, args.baseline_processed_txt, optimal_txt, "-o", pdf_path]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
