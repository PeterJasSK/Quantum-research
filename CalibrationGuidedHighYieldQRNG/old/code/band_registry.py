#!/usr/bin/env python3
"""
band_registry.py — EPIC 2, S2.1 (AC-1). Explicit best/next/worst band -> Stage
B _raw.json map (D-E2.1). No globbing: the 10-shot best-band probe
(...-214301) is named here only to be excluded. verify_against_ranking()
guards each band's qubit_list against the run-time (100-shot) predictor
ranking it was frozen from (D-E2.2) and errors loudly on mismatch.
"""

from __future__ import annotations

from typing import Any

from eval_common import load_run

QRNG_OUTPUT_DIR = "qrng_output"

# D-E2.1 — canonical band -> file map. The 10-shot best-band probe
# (stageb_ibm_marrakesh_20260714-214301_raw.json) is superseded by the
# 20000-shot ...-214816 run and is deliberately absent from this registry.
BAND_FILES: dict[str, str] = {
    "best": "stageb_ibm_marrakesh_20260714-214816_raw.json",
    "next": "stageb_ibm_marrakesh_20260714-215558_raw.json",
    "worst": "stageb_ibm_marrakesh_20260714-215818_raw.json",
}

DISCARDED_PROBE = "stageb_ibm_marrakesh_20260714-214301_raw.json"

# Run-time (100-shot) Stage A predictor the bands were frozen from at run
# time (D-E2.2) — used only to verify band membership, not to re-assign it.
RUNTIME_PREDICTOR_JSON = "results/stagea_ibm_marrakesh_20260714-210551_predictor.json"

BAND_ORDER = ["best", "next", "worst"]
BAND_SIZE = 5


def load_bands(qrng_output_dir: str = QRNG_OUTPUT_DIR) -> dict[str, dict[str, Any]]:
    """Loads each band's canonical _raw.json (AC-1). Errors loudly if a
    canonical file is missing or a qubit_list doesn't have exactly 5 qubits."""
    bands: dict[str, dict[str, Any]] = {}
    for band, filename in BAND_FILES.items():
        path = f"{qrng_output_dir}/{filename}"
        raw = load_run(path)
        qubit_list = raw["run"]["qubit_list"]
        if len(qubit_list) != BAND_SIZE:
            raise ValueError(
                f"Band '{band}' ({path}) has {len(qubit_list)} qubits, expected {BAND_SIZE}"
            )
        bands[band] = raw
    return bands


def verify_against_ranking(predictor_json_path: str = RUNTIME_PREDICTOR_JSON) -> None:
    """AC-1 guard — each band's qubit_list must equal the corresponding slice
    of the run-time (100-shot) predictor ranking (best=[0:5], next=[5:10],
    worst=last 5). Raises ValueError loudly on any mismatch."""
    import json

    with open(predictor_json_path) as f:
        predictor = json.load(f)
    ranked_qubits = [row["qubit"] for row in predictor["ranked_qubits"]]

    expected = {
        "best": ranked_qubits[0:BAND_SIZE],
        "next": ranked_qubits[BAND_SIZE:2 * BAND_SIZE],
        "worst": ranked_qubits[-BAND_SIZE:],
    }

    bands = load_bands()
    for band in BAND_ORDER:
        actual = bands[band]["run"]["qubit_list"]
        if actual != expected[band]:
            raise ValueError(
                f"Band '{band}' qubit_list {actual} does not match the run-time "
                f"ranking slice {expected[band]} from {predictor_json_path}"
            )


if __name__ == "__main__":
    verify_against_ranking()
    bands = load_bands()
    for band in BAND_ORDER:
        print(f"{band}: {bands[band]['run']['qubit_list']}")
    print(f"Discarded probe: {DISCARDED_PROBE}")
    print("Ranking guard passed.")
