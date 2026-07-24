#!/usr/bin/env python3
"""
evaluate_bands.py — EPIC 2, S2.2/S2.3 (AC-2, AC-3). Re-fits the Stage A
quality/predictor on the 65000-shot run (band membership stays as-run,
D-E2.2), scores all three bands' per-qubit x depth Stage B streams (reusing
evaluate_stage_b's score_depths/usable_depths, D-E2.6), and merges into one
combined 15-qubit table tagged band/predicted_quality/rank.

USAGE
    python code/evaluate_bands.py

OUTPUT (results/)
    bands_<backend>_<ts>_combined.csv
    bands_<backend>_<ts>_usable_depth.json
"""

from __future__ import annotations

from typing import Any

from band_registry import BAND_ORDER, RUNTIME_PREDICTOR_JSON, load_bands, verify_against_ranking
from eval_common import RESULTS_DIR, calibration_of, load_run, write_csv, write_json
from evaluate_stage_a import calibration_matrix, correlate, fit_predictor, score_qubits
from evaluate_stage_b import score_depths, usable_depths

STAGE_A_65000_SHOT_RAW = "qrng_output/stagea_ibm_marrakesh_20260714-210803_raw.json"
BACKEND_TS = "ibm_marrakesh_bands"


def refit_stage_a_predictor(stage_a_raw_path: str) -> dict[str, Any]:
    """AC-2 — re-fit the Stage A quality/predictor on the 65000-shot run so
    predicted_quality in the join is meaningful (not the 100-shot probe the
    run-time band ranking used)."""
    raw = load_run(stage_a_raw_path)
    calib = calibration_of(raw)
    qubits, scores = score_qubits(raw)
    X, imputed_flags = calibration_matrix(qubits, calib)
    for q, imputed in zip(qubits, imputed_flags):
        scores[q]["reset_error_imputed"] = imputed
    correlations = correlate(X, scores, qubits)
    predictor = fit_predictor(X, qubits, scores)
    return {"predictor": predictor, "correlations": correlations, "calib": calib}


PER_DEPTH_METRICS = ["min_entropy_per_bit", "serial_correlation", "global_bias", "verdict"]


def score_band(band: str, raw: dict[str, Any], predicted_quality: dict[int, float],
               rank: dict[int, int]) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    """Scores one band's Stage B streams (reusing evaluate_stage_b, D-E2.6)
    and returns one row per qubit (AC-3: "one combined table of the 15
    qubits") with per-depth metrics flattened as <metric>_d<depth> columns,
    tagged with band, predicted_quality, and rank."""
    depths: list[int] = raw["run"]["depths"]
    qubits: list[int] = raw["run"]["qubit_list"]
    scores = score_depths(raw)
    usable = usable_depths(qubits, depths, scores)

    rows = []
    for q in qubits:
        row: dict[str, Any] = {
            "band": band,
            "qubit": q,
            "predicted_quality": predicted_quality[q],
            "rank": rank[q],
            "usable_depth": usable[q]["usable_depth"],
            "flagged": usable[q]["flagged"],
        }
        for k in sorted(depths):
            score = scores.get((q, k))
            if score is None:
                continue
            for metric in PER_DEPTH_METRICS:
                row[f"{metric}_d{k}"] = score[metric]
        rows.append(row)
    return rows, usable


def main() -> None:
    verify_against_ranking(RUNTIME_PREDICTOR_JSON)
    bands = load_bands()

    stage_a = refit_stage_a_predictor(STAGE_A_65000_SHOT_RAW)
    predictor = stage_a["predictor"]
    print(f"Re-fit Stage A predictor on {STAGE_A_65000_SHOT_RAW}: "
          f"R^2 = {predictor['r_squared']:.4f}")

    predicted_quality = {row["qubit"]: row["predicted_quality"] for row in predictor["ranked_qubits"]}
    rank = {row["qubit"]: i + 1 for i, row in enumerate(predictor["ranked_qubits"])}

    all_rows: list[dict[str, Any]] = []
    combined_usable_depth: dict[str, Any] = {}
    for band in BAND_ORDER:
        raw = bands[band]
        rows, usable = score_band(band, raw, predicted_quality, rank)
        all_rows.extend(rows)
        for q, info in usable.items():
            combined_usable_depth[str(q)] = {**info, "band": band}
        print(f"Scored band '{band}': {len(raw['run']['qubit_list'])} qubits x "
              f"{len(raw['run']['depths'])} depths")

    head_keys = ["band", "qubit", "predicted_quality", "rank", "usable_depth", "flagged"]
    fieldnames = head_keys + [k for k in all_rows[0] if k not in head_keys]

    combined_csv_path = f"{RESULTS_DIR}/bands_{BACKEND_TS}_combined.csv"
    usable_depth_path = f"{RESULTS_DIR}/bands_{BACKEND_TS}_usable_depth.json"
    predictor_path = f"{RESULTS_DIR}/bands_{BACKEND_TS}_stagea_predictor_65000shot.json"

    write_csv(combined_csv_path, all_rows, fieldnames)
    write_json(usable_depth_path, combined_usable_depth)
    write_json(predictor_path, {**predictor, "r_squared_note": "re-fit on 65000-shot run, D-E2.2"})

    print(f"Combined table: {len(all_rows)} rows (expect 15, one per qubit)")
    print(f"Wrote {combined_csv_path}, {usable_depth_path}, {predictor_path}")


if __name__ == "__main__":
    main()
