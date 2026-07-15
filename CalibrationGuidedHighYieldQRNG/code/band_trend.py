#!/usr/bin/env python3
"""
band_trend.py — EPIC 2, S2.4 (AC-4, AC-5). The reframed core: Spearman
(predicted_quality, usable_depth) and each raw calibration feature vs
usable_depth over the 15 harvested qubits (D-E2.3 — continuous, not
band-binned), plus the ordered-groups trend across bands (Kruskal-Wallis
omnibus + monotone best>=next>=worst check, D-E2.4 — no Jonckheere-Terpstra,
not in scipy) on usable_depth, min-entropy, and |serial-correlation| at
depth-1 and max depth.

USAGE
    python code/band_trend.py

OUTPUT (results/)
    bands_<backend>_<ts>_trend.json
"""

from __future__ import annotations

import csv
from typing import Any

import numpy as np
from scipy.stats import kruskal, spearmanr

from band_registry import BAND_ORDER
from eval_common import RESULTS_DIR, calibration_of, load_run, write_json
from evaluate_stage_a import CALIB_FEATURES

COMBINED_CSV = f"{RESULTS_DIR}/bands_ibm_marrakesh_bands_combined.csv"
BACKEND_TS = "ibm_marrakesh_bands"

# The three Stage B raw files (for calibration features) and depths present.
STAGE_B_RAW_BY_BAND = {
    "best": "qrng_output/stageb_ibm_marrakesh_20260714-214816_raw.json",
    "next": "qrng_output/stageb_ibm_marrakesh_20260714-215558_raw.json",
    "worst": "qrng_output/stageb_ibm_marrakesh_20260714-215818_raw.json",
}
MIN_DEPTH = 1
MAX_DEPTH = 8


def load_combined_rows() -> list[dict[str, Any]]:
    with open(COMBINED_CSV) as f:
        return list(csv.DictReader(f))


def spearman_or_null(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    if np.std(x) == 0.0 or np.std(y) == 0.0:
        return {"rho": 0.0, "p_value": 1.0}
    rho, p = spearmanr(x, y)
    return {"rho": float(rho), "p_value": float(p)}


def gradient_tests(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """AC-4 — continuous join over all 15 qubits: predicted_quality and each
    raw calibration feature vs usable_depth."""
    usable_depth = np.array([float(r["usable_depth"]) for r in rows])
    predicted_quality = np.array([float(r["predicted_quality"]) for r in rows])

    calib_by_qubit: dict[int, dict[str, float | None]] = {}
    for band, path in STAGE_B_RAW_BY_BAND.items():
        raw = load_run(path)
        calib_by_qubit.update(calibration_of(raw))

    out: dict[str, Any] = {
        "predicted_quality_vs_usable_depth": spearman_or_null(predicted_quality, usable_depth),
    }
    for feat in CALIB_FEATURES:
        vals = np.array([
            float(calib_by_qubit[int(r["qubit"])].get(feat) or 0.0) for r in rows
        ])
        out[f"{feat}_vs_usable_depth"] = spearman_or_null(vals, usable_depth)
    return out


def monotone_check(band_means: dict[str, float]) -> bool:
    """best >= next >= worst (D-E2.4 — Spearman on band ordinal as the
    monotone-trend proxy; Jonckheere-Terpstra is not in scipy)."""
    return band_means["best"] >= band_means["next"] >= band_means["worst"]


def ordered_band_trend(rows: list[dict[str, Any]], outcome_key: str,
                        outcome_label: str) -> dict[str, Any]:
    """AC-5 — Kruskal-Wallis omnibus across the three bands on `outcome_key`,
    plus the monotone best>=next>=worst check on band means and a Spearman
    of band-ordinal vs the outcome as the trend-direction proxy (D-E2.4)."""
    by_band: dict[str, list[float]] = {b: [] for b in BAND_ORDER}
    for r in rows:
        by_band[r["band"]].append(float(r[outcome_key]))

    groups = [by_band[b] for b in BAND_ORDER]
    if all(np.std(g) == 0.0 for g in groups) and len({tuple(g) for g in groups}) == 1:
        stat, p = 0.0, 1.0
    else:
        stat, p = kruskal(*groups)

    band_means = {b: float(np.mean(by_band[b])) for b in BAND_ORDER}
    band_ordinal = np.array([i for i, b in enumerate(BAND_ORDER) for _ in by_band[b]])
    all_vals = np.array([v for b in BAND_ORDER for v in by_band[b]])
    ordinal_trend = spearman_or_null(band_ordinal, all_vals)

    return {
        "outcome": outcome_label,
        "band_means": band_means,
        "kruskal_h": float(stat),
        "kruskal_p_value": float(p),
        "monotone_best_ge_next_ge_worst": monotone_check(band_means),
        "band_ordinal_spearman": ordinal_trend,
    }


def main() -> None:
    rows = load_combined_rows()
    if len(rows) != 15:
        raise ValueError(f"Expected 15 rows in {COMBINED_CSV}, got {len(rows)}")

    for r in rows:
        r["abs_serial_correlation_d1"] = abs(float(r["serial_correlation_d1"]))
        r[f"abs_serial_correlation_d{MAX_DEPTH}"] = abs(float(r[f"serial_correlation_d{MAX_DEPTH}"]))

    gradient = gradient_tests(rows)

    band_trends = [
        ordered_band_trend(rows, "usable_depth", "usable_depth"),
        ordered_band_trend(rows, "min_entropy_per_bit_d1", "min_entropy_per_bit_depth1"),
        ordered_band_trend(rows, f"min_entropy_per_bit_d{MAX_DEPTH}", f"min_entropy_per_bit_depth{MAX_DEPTH}"),
        ordered_band_trend(rows, "abs_serial_correlation_d1", "abs_serial_correlation_depth1"),
        ordered_band_trend(rows, f"abs_serial_correlation_d{MAX_DEPTH}", f"abs_serial_correlation_depth{MAX_DEPTH}"),
    ]

    monotone_across_bands = all(t["monotone_best_ge_next_ge_worst"] for t in band_trends
                                 if t["outcome"] == "usable_depth")

    out = {
        "gradient_over_15_qubits": gradient,
        "ordered_band_trends": band_trends,
        "monotone_across_bands": monotone_across_bands,
    }

    out_path = f"{RESULTS_DIR}/bands_{BACKEND_TS}_trend.json"
    write_json(out_path, out)

    print(f"Wrote {out_path}")
    print(f"predicted_quality vs usable_depth: rho={gradient['predicted_quality_vs_usable_depth']['rho']:.3f} "
          f"p={gradient['predicted_quality_vs_usable_depth']['p_value']:.3f}")
    for t in band_trends:
        print(f"{t['outcome']}: kruskal H={t['kruskal_h']:.3f} p={t['kruskal_p_value']:.3f} "
              f"monotone={t['monotone_best_ge_next_ge_worst']} means={t['band_means']}")


if __name__ == "__main__":
    main()
