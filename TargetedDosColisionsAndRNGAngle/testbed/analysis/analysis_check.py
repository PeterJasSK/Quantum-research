#!/usr/bin/env python3
"""P5 spike (AC-5-7): manual check, no test suite (project directive).

Runs standalone without Mininet/root/os_ken -- feeds synthetic summary CSVs
(a hand-built prng-success row, a csprng-fail row, a rotation sweep with a
known crossover) into the analysis package. Non-zero exit means one of:
  1. `attacker_succeeded` misclassifies a known saturated+collapsed row, a
     saturated-but-healthy-victim row, or a not-saturated row;
  2. `rotation_threshold` doesn't recover a planted crossover interval;
  3. `graphs.py` fails to render both figures from synthetic CSVs.
"""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, __file__.rsplit("/testbed/", 1)[0])

from testbed.analysis.rotation_threshold import rotation_threshold, t_try_from_reconstruction  # noqa: E402
from testbed.analysis.success import attacker_succeeded  # noqa: E402
from testbed.metrics.csv_writer import SUMMARY_HEADER  # noqa: E402


def _check_success_predicate() -> bool:
    prng_success = {
        "salt_source": "prng", "knowledge_level": "full", "rotation_interval": "0",
        "attack_mode": "precision", "time_to_saturation_s": "2.500", "packets_to_saturation": "1000",
        "flows_to_saturation": "500", "final_jains_index": "0.250000", "min_victim_mbps": "0.500",
        "saturated": "True",
    }
    csprng_fail = {**prng_success, "salt_source": "csprng", "saturated": "False", "min_victim_mbps": "9.800"}
    saturated_healthy_victim = {**prng_success, "min_victim_mbps": "8.000"}

    if not attacker_succeeded(prng_success):
        print("FAIL: expected prng saturated+collapsed row to classify as success", file=sys.stderr)
        return False
    if attacker_succeeded(csprng_fail):
        print("FAIL: expected csprng not-saturated row to classify as fail", file=sys.stderr)
        return False
    if attacker_succeeded(saturated_healthy_victim):
        print("FAIL: expected saturated-but-healthy-victim row to classify as fail", file=sys.stderr)
        return False
    print("PASS: attacker_succeeded classifies success/fail/healthy-victim rows correctly")
    return True


def _sweep_rows() -> list[dict]:
    # Planted crossover: succeeds (saturated) at 60/30/10s, fails at 5/2/1/0.5s
    # -- the largest failing interval (5s) is the expected empirical threshold.
    intervals_saturated = [(60.0, True), (30.0, True), (10.0, True), (5.0, False), (2.0, False), (1.0, False), (0.5, False)]
    return [
        {"rotation_interval": str(interval), "saturated": str(saturated)}
        for interval, saturated in intervals_saturated
    ]


def _check_rotation_threshold() -> bool:
    sweep = _sweep_rows()
    t_try = t_try_from_reconstruction(elapsed_seconds=0.004, attempts=1000)
    result = rotation_threshold(sweep, seed_space_bits=16, t_try=t_try)

    if result.empirical_threshold_seconds != 5.0:
        print(
            f"FAIL: empirical crossover {result.empirical_threshold_seconds} != planted 5.0",
            file=sys.stderr,
        )
        return False
    expected_t_bf = (2**16 / 2) * t_try
    if abs(result.analytical_t_bf_seconds - expected_t_bf) > 1e-9:
        print(
            f"FAIL: analytical T_bf {result.analytical_t_bf_seconds} != {expected_t_bf}",
            file=sys.stderr,
        )
        return False
    if "rotate faster than" not in result.recommendation:
        print(f"FAIL: recommendation missing practitioner one-liner: {result.recommendation!r}", file=sys.stderr)
        return False
    print(
        f"PASS: rotation_threshold recovers planted crossover (5.0s) and computes "
        f"T_bf={result.analytical_t_bf_seconds:.3g}s"
    )
    return True


def _write_summary_csv(path: Path, row: dict) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_HEADER)
        writer.writeheader()
        writer.writerow(row)


def _check_graphs_render() -> bool:
    import testbed.experiments.matrix as matrix

    with tempfile.TemporaryDirectory() as tmp:
        # ExperimentCell.csv_path derives from the module-level RESULTS_DIR
        # matrix.py imported at load time; patch that binding (not
        # testbed.config's) so every cell's summary lookup lands under tmp
        # for the duration of this check only.
        original_results_dir = matrix.RESULTS_DIR
        matrix.RESULTS_DIR = tmp
        try:
            for group in (matrix.GRAPH1, matrix.EXP5_SWEEP):
                for cell in group:
                    saturated = (
                        bool(cell.expected_saturated)
                        if cell.expected_saturated is not None
                        else cell.rotation_interval >= 10.0
                    )
                    row = {
                        "salt_source": cell.salt_kind, "knowledge_level": cell.knowledge_level,
                        "rotation_interval": cell.rotation_interval, "attack_mode": cell.attack_mode,
                        "time_to_saturation_s": f"{cell.rotation_interval:.3f}",
                        "packets_to_saturation": str(int(cell.rotation_interval * 100)),
                        "flows_to_saturation": "10", "final_jains_index": "0.500000",
                        "min_victim_mbps": "0.500" if saturated else "9.000",
                        "saturated": str(saturated),
                    }
                    csv_path = Path(cell.csv_path)
                    csv_path.parent.mkdir(parents=True, exist_ok=True)
                    _write_summary_csv(csv_path.with_suffix(".summary.csv"), row)

            from testbed.analysis.graphs import render_graph1, render_graph2

            graph1_out = render_graph1(output_prefix=str(Path(tmp) / "graph1"))
            graph2_out = render_graph2(output_prefix=str(Path(tmp) / "graph2"))
            for out in (graph1_out, graph2_out):
                if not out.with_suffix(".png").exists() or not out.with_suffix(".svg").exists():
                    print(f"FAIL: {out} did not render both .png and .svg", file=sys.stderr)
                    return False
        finally:
            matrix.RESULTS_DIR = original_results_dir

    print("PASS: graph1/graph2 render to temp dir without error (.png + .svg)")
    return True


def main() -> int:
    checks = (_check_success_predicate(), _check_rotation_threshold(), _check_graphs_render())
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
