#!/usr/bin/env python3
"""
band_headline.py — EPIC 2, S2.5 (AC-6). Reframed headline: per-band
usable-bits/qubit/shot and usable-bits/free-tier-minute, best-vs-worst and
best-vs-next ratios, the reused baseline (Stage A --select all) vs best-band
ratio (unchanged from EPIC 1), and a monotone_across_bands flag. Verdict
wording covers both the gain case and the honest-failure case (worst ~= best).

USAGE
    python code/band_headline.py

OUTPUT (results/)
    bands_<backend>_<ts>_headline.json
"""

from __future__ import annotations

import csv
from typing import Any

from band_registry import BAND_ORDER
from eval_common import RESULTS_DIR, load_run, write_json

COMBINED_CSV = f"{RESULTS_DIR}/bands_ibm_marrakesh_bands_combined.csv"
TREND_JSON = f"{RESULTS_DIR}/bands_ibm_marrakesh_bands_trend.json"
STAGE_A_65000_SHOT_RAW = "qrng_output/stagea_ibm_marrakesh_20260714-210803_raw.json"
STAGE_B_QUANTUM_SECONDS_BY_BAND = {
    "best": "qrng_output/stageb_ibm_marrakesh_20260714-214816_raw.json",
    "next": "qrng_output/stageb_ibm_marrakesh_20260714-215558_raw.json",
    "worst": "qrng_output/stageb_ibm_marrakesh_20260714-215818_raw.json",
}
BACKEND_TS = "ibm_marrakesh_bands"
HONEST_FAILURE_RATIO_THRESHOLD = 1.1  # worst-vs-best within 10% counts as "worst ~= best"


def load_json(path: str) -> Any:
    import json
    with open(path) as f:
        return json.load(f)


def per_band_bits_per_minute() -> dict[str, dict[str, float]]:
    with open(COMBINED_CSV) as f:
        rows = list(csv.DictReader(f))

    out: dict[str, dict[str, float]] = {}
    for band in BAND_ORDER:
        band_rows = [r for r in rows if r["band"] == band]
        raw = load_run(STAGE_B_QUANTUM_SECONDS_BY_BAND[band])
        run = raw["run"]
        shots = run["shots_per_depth"]
        quantum_seconds = run["quantum_seconds"] or 1e-9

        usable_bits_per_shot = sum(float(r["usable_depth"]) for r in band_rows)
        bits_per_qsec = (usable_bits_per_shot * shots) / quantum_seconds
        bits_per_minute = bits_per_qsec * 60.0

        out[band] = {
            "usable_bits_per_qubit_per_shot": usable_bits_per_shot / len(band_rows),
            "usable_bits_per_shot_total": usable_bits_per_shot,
            "usable_bits_per_free_tier_minute": bits_per_minute,
        }
    return out


def baseline_vs_best(best_bits_per_minute: float) -> dict[str, Any]:
    """Reused from EPIC 1: naive baseline (Stage A --select all) vs best-band."""
    raw = load_run(STAGE_A_65000_SHOT_RAW)
    run = raw["run"]
    n_qubits_baseline = run["n_qubits_used"]
    quantum_seconds_baseline = run["quantum_seconds"] or 1e-9
    shots_baseline = run["shots"]

    baseline_bits_per_shot = n_qubits_baseline
    baseline_bits_per_qsec = (baseline_bits_per_shot * shots_baseline) / quantum_seconds_baseline
    baseline_bits_per_minute = baseline_bits_per_qsec * 60.0

    ratio = (best_bits_per_minute / baseline_bits_per_minute
             if baseline_bits_per_minute > 0 else float("inf"))
    return {
        "baseline_bits_per_free_tier_minute": baseline_bits_per_minute,
        "ratio_best_over_baseline": ratio,
    }


def main() -> None:
    per_band = per_band_bits_per_minute()
    trend = load_json(TREND_JSON)

    best_bpm = per_band["best"]["usable_bits_per_free_tier_minute"]
    next_bpm = per_band["next"]["usable_bits_per_free_tier_minute"]
    worst_bpm = per_band["worst"]["usable_bits_per_free_tier_minute"]

    best_vs_worst_ratio = best_bpm / worst_bpm if worst_bpm > 0 else float("inf")
    best_vs_next_ratio = best_bpm / next_bpm if next_bpm > 0 else float("inf")

    best_usable = per_band["best"]["usable_bits_per_shot_total"]
    worst_usable = per_band["worst"]["usable_bits_per_shot_total"]
    delta_usable_depth_best_minus_worst = best_usable - worst_usable

    baseline = baseline_vs_best(best_bpm)
    monotone_across_bands = bool(trend["monotone_across_bands"])

    honest_failure = worst_bpm > 0 and best_vs_worst_ratio < HONEST_FAILURE_RATIO_THRESHOLD
    if honest_failure:
        verdict = ("NO GAIN (honest failure case) — worst-band usable yield is within "
                    f"{(HONEST_FAILURE_RATIO_THRESHOLD - 1) * 100:.0f}% of best-band; "
                    "calibration selection did not separate the bands")
    elif best_vs_worst_ratio > 1.0:
        verdict = "GAIN — calibration-selected best-band yields more usable bits/minute than worst-band"
    else:
        verdict = "NO GAIN (honest failure case) — worst-band outperforms or matches best-band"

    out = {
        "per_band": per_band,
        "best_vs_worst_ratio": best_vs_worst_ratio,
        "best_vs_next_ratio": best_vs_next_ratio,
        "delta_usable_bits_per_shot_best_minus_worst": delta_usable_depth_best_minus_worst,
        "baseline_vs_best": baseline,
        "monotone_across_bands": monotone_across_bands,
        "verdict": verdict,
    }

    out_path = f"{RESULTS_DIR}/bands_{BACKEND_TS}_headline.json"
    write_json(out_path, out)

    print(f"Wrote {out_path}")
    print(f"best-vs-worst ratio: {best_vs_worst_ratio:.3f}, best-vs-next ratio: {best_vs_next_ratio:.3f}")
    print(f"baseline-vs-best ratio: {baseline['ratio_best_over_baseline']:.3f}")
    print(f"monotone_across_bands: {monotone_across_bands}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
