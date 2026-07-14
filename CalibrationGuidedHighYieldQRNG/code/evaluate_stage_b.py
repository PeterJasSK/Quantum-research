#!/usr/bin/env python3
"""
evaluate_stage_b.py — EPIC 1, S1.3 (AC-5). Scores every per-qubit-per-depth
Stage B stream (serial correlation, min-entropy, reset-induced bias, next-bit,
Markov via evaluate_stream) and finds each qubit's maximum usable measure-reset
depth (E4): the largest depth k such that every depth <= k passes.

USAGE
    python evaluate_stage_b.py qrng_output/stageb_<backend>_<ts>_raw.json

OUTPUT (results/, stem from the source _raw.json)
    <stem>_scores.csv          one row per qubit x depth
    <stem>_usable_depth.json   one usable depth per qubit (0 if depth-1 fails) + the flag
"""

from __future__ import annotations

import argparse
from typing import Any

from eval_common import RESULTS_DIR, evaluate_stream, load_run, reconstruct_stage_b, stem_of, write_csv, write_json


def score_depths(raw: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    streams = reconstruct_stage_b(raw)
    return {key: evaluate_stream(bits) for key, bits in streams.items()}


def is_usable(score: dict[str, Any], depth1_bias: float) -> bool:
    """E4 — a depth-k stream is usable when _stream_verdict is PASS AND the
    serial-correlation gate passes AND |global_bias| does not exceed the
    depth-1 magnitude for that qubit."""
    return (
        score["verdict"] == "PASS"
        and score["serial_correlation_ok"]
        and abs(score["global_bias"]) <= depth1_bias
    )


def usable_depths(qubits: list[int], depths: list[int],
                   scores: dict[tuple[int, int], dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    sorted_depths = sorted(depths)
    for q in qubits:
        depth1_bias = abs(scores[(q, sorted_depths[0])]["global_bias"])
        usable = 0
        for k in sorted_depths:
            score = scores.get((q, k))
            if score is None or not is_usable(score, depth1_bias):
                break
            usable = k
        out[q] = {"usable_depth": usable, "flagged": usable == 0}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Stage B per-qubit-per-depth streams; find usable depth.")
    parser.add_argument("raw_json")
    args = parser.parse_args()

    raw = load_run(args.raw_json)
    depths: list[int] = raw["run"]["depths"]
    qubits: list[int] = raw["run"]["qubit_list"]

    scores = score_depths(raw)
    print(f"Scored {len(qubits)} qubits x {len(depths)} depths from {args.raw_json}")

    rows = []
    for q in qubits:
        for k in sorted(depths):
            score = scores.get((q, k))
            if score is None:
                continue
            rows.append({"qubit": q, "depth": k, **score})
    fieldnames = ["qubit", "depth"] + [k for k in rows[0] if k not in ("qubit", "depth")]

    usable = usable_depths(qubits, depths, scores)

    stem = stem_of(args.raw_json)
    scores_csv_path = f"{RESULTS_DIR}/{stem}_scores.csv"
    usable_path = f"{RESULTS_DIR}/{stem}_usable_depth.json"

    write_csv(scores_csv_path, rows, fieldnames)
    write_json(usable_path, usable)

    print(f"Wrote {scores_csv_path}, {usable_path}")
    for q in qubits:
        print(f"  qubit {q}: usable depth {usable[q]['usable_depth']}"
              f"{' (flagged)' if usable[q]['flagged'] else ''}")


if __name__ == "__main__":
    main()
