#!/usr/bin/env python3
"""
join_and_headline.py — EPIC 1, S1.4 (AC-6, AC-7). Tests whether the Stage A
calibration predictor also predicts each qubit's Stage B usable depth
(Spearman + a combined Ridge model, AC-6), and computes the headline (E8):
usable bits per free-tier minute at the calibration-optimal config vs the
naive baseline (Stage A --select all).

USAGE
    python join_and_headline.py results/stagea_<...>_predictor.json \\
                                 results/stageb_<...>_usable_depth.json \\
                                 [--stage-a-raw qrng_output/stagea_..._raw.json]

OUTPUT
    results/headline_<backend>_<ts>.json
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from eval_common import RESULTS_DIR, load_run, write_json

BACKEND_TS_RE = re.compile(r"stage[ab]_(.+)_(\d{8}-\d{6})")


def backend_ts_from(path: str) -> str:
    m = BACKEND_TS_RE.search(path)
    return f"{m.group(1)}_{m.group(2)}" if m else "unknown"


def load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def predictor_test(predictor: dict[str, Any], usable_depth: dict[str, Any]) -> dict[str, Any]:
    """AC-6 — does the Stage A predicted quality (and each raw calibration
    property) also predict each qubit's Stage B usable depth?"""
    ranked = {row["qubit"]: row["predicted_quality"] for row in predictor["ranked_qubits"]}
    qubits = [q for q in ranked if str(q) in usable_depth]
    if len(qubits) < 3:
        return {"note": "fewer than 3 qubits overlap between Stage A and Stage B — "
                         "not enough to test the predictor", "n_qubits": len(qubits)}

    pred_quality = np.array([ranked[q] for q in qubits], dtype=np.float64)
    depth = np.array([usable_depth[str(q)]["usable_depth"] for q in qubits], dtype=np.float64)

    if np.std(pred_quality) == 0.0 or np.std(depth) == 0.0:
        rho, p = 0.0, 1.0
    else:
        rho, p = spearmanr(pred_quality, depth)

    scaler = StandardScaler()
    X = scaler.fit_transform(pred_quality.reshape(-1, 1))
    model = Ridge(alpha=1.0)
    model.fit(X, depth)
    pred = model.predict(X)
    ss_res = float(np.sum((depth - pred) ** 2))
    ss_tot = float(np.sum((depth - depth.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "n_qubits": len(qubits),
        "spearman_rho": float(rho),
        "spearman_p_value": float(p),
        "ridge_r_squared": r2,
        "predicts_usable_depth": bool(p < 0.05 and rho > 0),
    }


def headline(stage_a_raw_path: str, top_n_selected: list[int],
             usable_depth: dict[str, Any]) -> dict[str, Any]:
    """E8 — usable bits/shot and usable bits/free-tier-minute, baseline vs optimal."""
    raw = load_run(stage_a_raw_path)
    run = raw["run"]
    n_qubits_baseline = run["n_qubits_used"]
    quantum_seconds_baseline = run["quantum_seconds"] or 1e-9
    shots_baseline = run["shots"]

    baseline_bits_per_shot = n_qubits_baseline
    baseline_bits_per_qsec = (baseline_bits_per_shot * shots_baseline) / quantum_seconds_baseline
    baseline_bits_per_minute = baseline_bits_per_qsec * 60.0

    optimal_bits_per_shot = sum(usable_depth[str(q)]["usable_depth"] for q in top_n_selected)
    # Same measured QPU-seconds-per-shot rate as the baseline run (no Stage B
    # timing join available at this point); scale by the selected subset.
    qsec_per_shot_baseline = quantum_seconds_baseline / shots_baseline if shots_baseline else 0.0
    optimal_bits_per_qsec = (
        optimal_bits_per_shot / qsec_per_shot_baseline if qsec_per_shot_baseline else 0.0
    )
    optimal_bits_per_minute = optimal_bits_per_qsec * 60.0

    ratio = (
        optimal_bits_per_minute / baseline_bits_per_minute
        if baseline_bits_per_minute > 0 else float("inf")
    )

    return {
        "baseline_bits_per_shot": baseline_bits_per_shot,
        "baseline_bits_per_quantum_second": baseline_bits_per_qsec,
        "baseline_bits_per_free_tier_minute": baseline_bits_per_minute,
        "optimal_bits_per_shot": optimal_bits_per_shot,
        "optimal_bits_per_quantum_second": optimal_bits_per_qsec,
        "optimal_bits_per_free_tier_minute": optimal_bits_per_minute,
        "ratio_optimal_over_baseline": ratio,
        "verdict": "GAIN" if ratio > 1.0 else "NO GAIN (honest failure case)",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Join Stage A predictor with Stage B usable depth; compute the headline.")
    parser.add_argument("predictor_json")
    parser.add_argument("usable_depth_json")
    parser.add_argument("--stage-a-raw", type=str, default=None,
                         help="Stage A _raw.json (defaults to qrng_output/<stem-without-results-suffix>_raw.json)")
    args = parser.parse_args()

    predictor = load_json(args.predictor_json)
    usable_depth = load_json(args.usable_depth_json)

    stage_a_raw_path = args.stage_a_raw
    if stage_a_raw_path is None:
        m = re.search(r"(stagea_.+)_predictor\.json$", args.predictor_json)
        stem = m.group(1) if m else None
        if stem is None:
            raise SystemExit("Cannot infer the Stage A _raw.json path — pass --stage-a-raw explicitly.")
        stage_a_raw_path = f"qrng_output/{stem}_raw.json"

    top_n_selected: list[int] = predictor["selected_qubits"]

    test_result = predictor_test(predictor, usable_depth)
    headline_result = headline(stage_a_raw_path, top_n_selected, usable_depth)

    out = {
        "predictor_to_usable_depth": test_result,
        "headline": headline_result,
        "selected_qubits": top_n_selected,
    }

    bts = backend_ts_from(args.usable_depth_json)
    out_path = f"{RESULTS_DIR}/headline_{bts}.json"
    write_json(out_path, out)

    print(f"Wrote {out_path}")
    print(f"Predictor -> usable-depth: {test_result}")
    print(f"Headline: {headline_result['verdict']} "
          f"(ratio {headline_result['ratio_optimal_over_baseline']:.3f})")


if __name__ == "__main__":
    main()
