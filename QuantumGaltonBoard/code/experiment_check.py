#!/usr/bin/env python3
"""
experiment_check.py — Quantum Galton Board: the P4 offline correctness gate (epic §3.6).

Ideal-only, aer-free, network-free (mirrors walk_check.py / metrics_check.py): it
drives a tiny ideal sweep, aggregates it, renders both figures, and exports a
replay JSON — all to a temp dir — and asserts the P4 data/artefact contracts
hold. It NEVER touches the noisy or hw arm (no from_backend read, no live QC), so
it runs with no IBM account and no QPU. Exits non-zero on any breach; prints one
PASS line per check otherwise.

Checks (plan §9):
  AC-4.1/4.2 data  aggregate carries every per_depth[].metrics field and a
                   well-formed (possibly None) knee in meta.
  AC-4.1           fig_horns_melting renders non-empty PNG + SVG.
  AC-4.2           fig_collapse_curve renders non-empty PNG + SVG.
  AC-4.4           export_replay validates against the §8 shape: arms list, the
                   walk_spec embedded verbatim, string-keyed histograms summing
                   to ~1, and hw a null arm slot in Phase A.

The tiny ideal runs land in runs/ (run_arm's frozen output dir); they are valid
deterministic ideal runs. All P4 artefacts (summary/figures/replay) go to a temp
dir so the gate leaves research_runs/ / figures/ / web/ untouched.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import config
import figures
import replay_export
import sweep
from sweep import METRIC_FIELDS
from walk_spec import WALK_SPEC

GATE_DEPTHS = [2, 4, 6]                 # tiny; ideal is cheap and deterministic
TOL = 1e-6


def _tiny_ideal_summary(tmp: str) -> dict:
    """Drive a tiny ideal sweep and aggregate it into `tmp`; return the summary."""
    cfg = config.load()
    paths = sweep.run_sim_sweep("ideal", GATE_DEPTHS, cfg.seeds, cfg)
    out = sweep.aggregate("ideal", paths, out_dir=tmp, cfg=cfg)
    with open(out) as f:
        return json.load(f)


def check_aggregate(summary: dict) -> None:
    """AC-4.1/4.2 data: every per_depth metric field present, knee well-formed."""
    per_depth = summary["per_depth"]
    assert per_depth, "aggregate produced no per_depth entries"
    seen = {int(e["steps"]) for e in per_depth}
    assert seen == set(GATE_DEPTHS), f"depths {seen} != {GATE_DEPTHS}"
    for e in per_depth:
        for field in METRIC_FIELDS:
            assert field in e["metrics"], (
                f"per_depth n={e['steps']} missing metric {field!r}")
        assert isinstance(e["metrics"]["variance_mean"], float)
        assert e["metrics"]["a_local"] is not None, "a_local not filled"
    meta = summary["meta"]
    for key in ("knee_depth", "exponent_knee", "contrast_knee", "rule"):
        assert key in meta, f"meta missing knee field {key!r}"
    kd = meta["knee_depth"]
    assert kd is None or isinstance(kd, (int, float)), f"bad knee_depth {kd!r}"
    print(f"PASS AC-4.1/4.2 aggregate: {len(per_depth)} depths, all "
          f"{len(METRIC_FIELDS)} metric fields, knee_depth={kd}")


def check_figures(summary: dict, tmp: str) -> None:
    """AC-4.1 / AC-4.2: both figures render to non-empty PNG + SVG."""
    horns = figures.fig_horns_melting(
        [summary], GATE_DEPTHS, os.path.join(tmp, "horns_melting"))
    collapse = figures.fig_collapse_curve(
        summary, os.path.join(tmp, "collapse_curve"))
    for path in horns + collapse:
        assert os.path.isfile(path), f"figure not written: {path}"
        assert os.path.getsize(path) > 0, f"figure empty: {path}"
    print(f"PASS AC-4.1/4.2 figures: horns_melting + collapse_curve "
          f"({len(horns + collapse)} files, all non-empty)")


def check_replay(summary: dict, tmp: str) -> None:
    """AC-4.4: replay JSON matches the §8 shape; hw null; histograms sum ~1."""
    out = replay_export.export_replay(
        {"ideal": summary}, out_path=os.path.join(tmp, "replay.json"))
    with open(out) as f:
        payload = json.load(f)
    assert payload["arms"] == ["ideal", "noisy", "hw"], payload["arms"]
    assert payload["walk_spec"] == dict(WALK_SPEC), "walk_spec not verbatim"
    assert payload["per_arm"]["hw"] is None, "hw arm not null in Phase A"
    ideal = payload["per_arm"]["ideal"]
    assert ideal is not None, "ideal arm missing"
    for depth, block in ideal["by_depth"].items():
        total = sum(float(v) for v in block["position_histogram"].values())
        assert abs(total - 1.0) < 1e-6, f"depth {depth} histogram sums to {total}"
        for field in ("variance", "horn_contrast", "entropy", "a_local"):
            assert field in block["metrics"], f"depth {depth} missing {field}"
    assert set(payload["binomial_reference"]) == {str(d) for d in GATE_DEPTHS}
    print("PASS AC-4.4 replay: arms=[ideal,noisy,hw], walk_spec verbatim, "
          "hw null, histograms sum~1")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="qgb_p4_gate_")
    try:
        summary = _tiny_ideal_summary(tmp)
        check_aggregate(summary)
        check_figures(summary, tmp)
        check_replay(summary, tmp)
    except AssertionError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print("experiment_check: all offline gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
