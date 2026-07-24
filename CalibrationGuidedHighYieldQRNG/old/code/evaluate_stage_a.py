#!/usr/bin/env python3
"""
evaluate_stage_a.py — EPIC 1, S1.2 (AC-3, AC-4). Scores every per-qubit
Stage A stream, correlates each calibration property against each quality
metric (Spearman), fits a simple Ridge predictor from calibration alone
(E5), ranks qubits, and selects the top-N for the manual Stage B run.

USAGE
    python evaluate_stage_a.py qrng_output/stagea_<backend>_<ts>_raw.json [--top 5]

OUTPUT (results/, stem from the source _raw.json)
    <stem>_scores.json / .csv     one row per qubit: metrics + verdict + nist_na
    <stem>_correlations.json      each calibration property x each quality metric (Spearman)
    <stem>_predictor.json         Ridge coefficients + R^2, ranked qubits, top-N selection
Prints the ready-to-paste "--qubits q1,q2,..." line for the Stage B manual run.
"""

from __future__ import annotations

import argparse
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from eval_common import (
    RESULTS_DIR, calibration_of, evaluate_stream, load_run, reconstruct_stage_a,
    stem_of, write_csv, write_json,
)

CALIB_FEATURES = ["t1", "t2", "readout_error", "sx_error", "reset_error"]
QUALITY_METRICS = [
    "global_bias", "min_entropy_per_bit", "nist_pass_rate", "serial_correlation",
]
DEFAULT_TOP_N = 5
RIDGE_ALPHA = 1.0


def score_qubits(raw: dict[str, Any]) -> tuple[list[int], dict[int, dict[str, Any]]]:
    streams = reconstruct_stage_a(raw)
    qubits = sorted(streams)
    scores = {q: evaluate_stream(streams[q]) for q in qubits}
    return qubits, scores


def calibration_matrix(qubits: list[int],
                        calib: dict[int, dict[str, float | None]]) -> tuple[np.ndarray, list[bool]]:
    """Rows = qubits, cols = CALIB_FEATURES. reset_error mean-imputed when null (E5)."""
    raw_vals = np.array(
        [[calib[q].get(f) for f in CALIB_FEATURES] for q in qubits], dtype=object,
    )
    imputed_flags = [False] * len(qubits)
    X = np.zeros((len(qubits), len(CALIB_FEATURES)), dtype=np.float64)
    for j, feat in enumerate(CALIB_FEATURES):
        col = raw_vals[:, j]
        present = np.array([v is not None for v in col])
        col_f = np.array([float(v) if v is not None else np.nan for v in col], dtype=np.float64)
        if present.any():
            mean_val = col_f[present].mean()
        else:
            mean_val = 0.0
        for i in range(len(qubits)):
            if not present[i]:
                col_f[i] = mean_val
                if feat == "reset_error":
                    imputed_flags[i] = True
        X[:, j] = col_f
    return X, imputed_flags


def correlate(X: np.ndarray, scores: dict[int, dict[str, Any]],
              qubits: list[int]) -> dict[str, dict[str, dict[str, float]]]:
    """Spearman correlation of each raw calibration property vs each quality metric (AC-3)."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for j, feat in enumerate(CALIB_FEATURES):
        out[feat] = {}
        for metric in QUALITY_METRICS:
            y = np.array([scores[q][metric] for q in qubits], dtype=np.float64)
            if np.std(X[:, j]) == 0.0 or np.std(y) == 0.0:
                rho, p = 0.0, 1.0
            else:
                rho, p = spearmanr(X[:, j], y)
            out[feat][metric] = {"rho": float(rho), "p_value": float(p)}
    return out


def fit_predictor(X: np.ndarray, qubits: list[int],
                   scores: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """E5 — Ridge on standardized calibration features, target = min_entropy_per_bit."""
    y = np.array([scores[q]["min_entropy_per_bit"] for q in qubits], dtype=np.float64)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    model = Ridge(alpha=RIDGE_ALPHA)
    model.fit(Xs, y)
    pred = model.predict(Xs)
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    ranked = sorted(zip(qubits, pred.tolist()), key=lambda t: t[1], reverse=True)
    return {
        "features": CALIB_FEATURES,
        "coefficients": dict(zip(CALIB_FEATURES, model.coef_.tolist())),
        "intercept": float(model.intercept_),
        "r_squared": r2,
        "target": "min_entropy_per_bit",
        "ranked_qubits": [{"qubit": q, "predicted_quality": p} for q, p in ranked],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Stage A per-qubit streams; select top-N.")
    parser.add_argument("raw_json")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N)
    args = parser.parse_args()

    raw = load_run(args.raw_json)
    calib = calibration_of(raw)
    qubits, scores = score_qubits(raw)
    print(f"Scored {len(qubits)} qubits from {args.raw_json}")

    X, imputed_flags = calibration_matrix(qubits, calib)
    for q, imputed in zip(qubits, imputed_flags):
        scores[q]["reset_error_imputed"] = imputed

    correlations = correlate(X, scores, qubits)
    predictor = fit_predictor(X, qubits, scores)

    ranked_qubits = [row["qubit"] for row in predictor["ranked_qubits"]]
    top_qubits = ranked_qubits[: args.top]

    stem = stem_of(args.raw_json)
    rows = []
    for q in qubits:
        row = {"qubit": q, **scores[q]}
        rows.append(row)
    fieldnames = ["qubit"] + [k for k in rows[0] if k != "qubit"]

    scores_json_path = f"{RESULTS_DIR}/{stem}_scores.json"
    scores_csv_path = f"{RESULTS_DIR}/{stem}_scores.csv"
    correlations_path = f"{RESULTS_DIR}/{stem}_correlations.json"
    predictor_path = f"{RESULTS_DIR}/{stem}_predictor.json"

    write_json(scores_json_path, rows)
    write_csv(scores_csv_path, rows, fieldnames)
    write_json(correlations_path, correlations)
    write_json(predictor_path, {**predictor, "top_n": args.top, "selected_qubits": top_qubits})

    print(f"Wrote {scores_json_path}, {scores_csv_path}, {correlations_path}, {predictor_path}")
    print(f"Predictor R^2 = {predictor['r_squared']:.4f}")
    print(f"\n--qubits {','.join(str(q) for q in top_qubits)}")


if __name__ == "__main__":
    main()
