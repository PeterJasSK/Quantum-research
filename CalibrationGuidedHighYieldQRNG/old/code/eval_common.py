#!/usr/bin/env python3
"""
eval_common.py — EPIC 1 shared helpers (AC-1, AC-2, E1-E3, E6, E7).

Imports the battery from ErrorDetectionVSRawBits/qrng_compare.py via sys.path
(never edited, never copied — E1). Adds one metric the battery lacks, lag-1
serial correlation (AC-2, E3), on top of a thin evaluate_stream() wrapper
around the battery's own analyze() + _stream_verdict() (AC-1). Also holds the
Stage A / Stage B stream reconstructors (E2) and the results/ IO helpers (E7).
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import warnings
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BATTERY_DIR = os.path.join(_REPO_ROOT, "ErrorDetectionVSRawBits")
if _BATTERY_DIR not in sys.path:
    sys.path.insert(0, _BATTERY_DIR)

from qrng_compare import analyze, _stream_verdict, load_bits, hash_extract  # noqa: E402

import numpy as np

RESULTS_DIR = "results"

SERIAL_CORR_Z = 1.96  # two-sided alpha=0.05 large-sample test (E3, Q1)


# ---------------------------------------------------------------------------
# AC-2 / E3 — lag-1 serial correlation (the one metric the battery lacks)
# ---------------------------------------------------------------------------
def serial_correlation(arr: np.ndarray) -> float:
    """Pearson r between arr[:-1] and arr[1:]; 0.0 for a constant/too-short stream."""
    if len(arr) < 2:
        return 0.0
    a, b = arr[:-1].astype(np.float64), arr[1:].astype(np.float64)
    if a.std() == 0.0 or b.std() == 0.0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def serial_corr_ok(r: float, n: int) -> bool:
    """PASS iff |r| is not significantly non-zero at alpha=0.05 (E3, Q1)."""
    if n <= 1:
        return True
    return abs(r) * math.sqrt(n - 1) < SERIAL_CORR_Z


# ---------------------------------------------------------------------------
# AC-1 — thin wrapper around the battery's analyze() + _stream_verdict()
# ---------------------------------------------------------------------------
def evaluate_stream(bits: str) -> dict[str, Any]:
    """Runs the battery on `bits` (a "0101..." string), appends serial
    correlation (AC-2) and an nist_na flag (E6), and reports the verdict via
    the battery's own _stream_verdict() rule, unchanged."""
    arr = np.array([int(b) for b in bits], dtype=np.int8)
    with warnings.catch_warnings():
        # Short per-qubit streams legitimately hit single-class CV folds in the
        # battery's next-bit test (E6) — expected noise at this sample size,
        # not an error; the resulting NIST/next-bit verdict is unaffected.
        warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
        warnings.filterwarnings("ignore", message=".*Only one class is present.*")
        r = analyze(arr)
    verdict, nist_ok, nb_ok, mk_ok = _stream_verdict(r)
    sc = serial_correlation(arr)
    nist_na = r["nist"].get("tests_run", 0) == 0
    return {
        "n_bits": r["n_bits"],
        "global_bias": r["global_bias"],
        "min_entropy_per_bit": r["min_entropy_per_bit"],
        "nist_pass_rate": r["nist"]["overall_pass_rate"],
        "nist_tests_run": r["nist"].get("tests_run", 0),
        "nist_na": nist_na,
        "next_bit_verdict": r["next_bit"]["verdict"],
        "markov_verdict": r["markov"]["verdict"],
        "serial_correlation": sc,
        "serial_correlation_ok": serial_corr_ok(sc, r["n_bits"]),
        "nist_ok": nist_ok,
        "next_bit_ok": nb_ok,
        "markov_ok": mk_ok,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# IO — load a Stage A / Stage B _raw.json run
# ---------------------------------------------------------------------------
def load_run(path: str) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def calibration_of(raw: dict[str, Any]) -> dict[int, dict[str, float | None]]:
    return {int(q): info for q, info in raw["calibration"].items()}


# ---------------------------------------------------------------------------
# E2 — stream reconstruction
# ---------------------------------------------------------------------------
def reconstruct_stage_a(raw: dict[str, Any]) -> dict[int, str]:
    """Per-qubit stream: for shot string s, reversed r = s[::-1]; qubit q's bit
    at this shot is r[qubits_used.index(q)]. Streams are in shot order."""
    qubits_used: list[int] = raw["run"]["qubits_used"]
    streams: dict[int, list[str]] = {q: [] for q in qubits_used}
    for s in raw["raw_measurements"]:
        r = s[::-1]
        for i, q in enumerate(qubits_used):
            streams[q].append(r[i])
    return {q: "".join(bits) for q, bits in streams.items()}


def reconstruct_stage_b(raw: dict[str, Any]) -> dict[tuple[int, int], str]:
    """Per-(qubit, depth) stream: for each depths[j] entry, reverse each shot
    string; qubit qubit_list[i] at rep is r[rep*n + i] (rep-major, E2). A
    qubit's depth-k stream is those bits across all shots and reps, in
    (shot, rep) order — the temporal order the serial-correlation metric
    needs."""
    streams: dict[tuple[int, int], str] = {}
    for entry in raw["depths"]:
        depth = entry["depth"]
        qubit_list: list[int] = entry["qubit_list"]
        n = entry["n_qubits"]
        per_qubit: dict[int, list[str]] = {q: [] for q in qubit_list}
        for s in entry["raw_measurements"]:
            r = s[::-1]
            for rep in range(depth):
                for i, q in enumerate(qubit_list):
                    per_qubit[q].append(r[rep * n + i])
        for q, bits in per_qubit.items():
            streams[(q, depth)] = "".join(bits)
    return streams


# ---------------------------------------------------------------------------
# E7 — results IO
# ---------------------------------------------------------------------------
def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)


def write_csv(path: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def stem_of(raw_path: str) -> str:
    """'.../stagea_ibm_marrakesh_20260714-210551_raw.json' -> 'stagea_ibm_marrakesh_20260714-210551'."""
    base = os.path.basename(raw_path)
    if base.endswith("_raw.json"):
        base = base[: -len("_raw.json")]
    return base
