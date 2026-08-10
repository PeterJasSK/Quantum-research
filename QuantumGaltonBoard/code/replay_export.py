#!/usr/bin/env python3
"""
replay_export.py — Quantum Galton Board: the P5 replay contract (P4, plan §8, OQ-6).

Writes ONE ``web/replay.json`` that P5 embeds verbatim into its single
self-contained HTML (OQ-6). This is the frozen interface to P5 (the JS decoder +
JS metric mirror read it), so its shape is documented in SCHEMA.md (§8) and must
not drift without a P5-visible amendment. numpy + json only; no matplotlib, no
metric definitions (it serialises already-aggregated series).

  export_replay(summaries, out_path=...)  (AC-4.4) — carries, per depth and per
      arm: the mean ``position_histogram`` (int-keyed -> string on write,
      mirroring run.json), the fitted per-depth metrics (variance, horn_contrast,
      entropy, a_local), the closed-form ``binomial_reference`` per depth, and the
      extracted knee. Phase A fills ``ideal`` and ``noisy``; ``hw`` is a ``null``
      arm slot. Phase B rewrites the same file with ``per_arm.hw`` populated (mean
      histograms + ``_mean``/``_std`` metrics + a knee with lo/hi band); P5 needs
      no structural change — its hw toggle simply stops seeing ``null``.
"""

from __future__ import annotations

import glob
import json
import os

import analytics
from walk_spec import WALK_SPEC

_HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.normpath(os.path.join(_HERE, "..", "web"))
RESEARCH_RUNS_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))
DEFAULT_OUT = os.path.join(WEB_DIR, "replay.json")

ARMS_ORDER = ("ideal", "noisy", "hw")


def _load(summary) -> dict:
    if isinstance(summary, str):
        with open(summary) as f:
            return json.load(f)
    return summary


def _normalise(summaries) -> dict[str, dict]:
    """Accept {arm: summary}, a list, or a single summary -> {arm: summary dict}."""
    if isinstance(summaries, dict) and "per_depth" not in summaries:
        return {arm: _load(s) for arm, s in summaries.items()}
    if not isinstance(summaries, (list, tuple)):
        summaries = [summaries]
    out: dict[str, dict] = {}
    for s in summaries:
        s = _load(s)
        out[s["meta"]["arm"]] = s
    return out


def _arm_block(summary: dict) -> dict:
    """One arm's replay block: backend, per-depth histogram+metrics, knee."""
    meta = summary["meta"]
    by_depth: dict[str, dict] = {}
    for entry in summary["per_depth"]:
        m = entry["metrics"]
        by_depth[str(int(entry["steps"]))] = {
            # already string-keyed in summary.json; carried verbatim so the JS
            # decode is identical to run.json (pipeline.py:101)
            "position_histogram": entry["position_histogram"],
            "metrics": {
                "variance": m.get("variance_mean"),
                "horn_contrast": m.get("horn_contrast_mean"),
                "entropy": m.get("entropy_mean"),
                "a_local": m.get("a_local"),
            },
        }
    return {
        "backend": meta["backend"],
        "by_depth": by_depth,
        "knee": {
            "knee_depth": meta.get("knee_depth"),
            "contrast_knee": meta.get("contrast_knee"),
            "rule": meta.get("rule"),
        },
    }


def export_replay(summaries, out_path: str = DEFAULT_OUT) -> str:
    """Write ``web/replay.json`` (§8 shape); return its path (AC-4.4).

    ``summaries`` maps arms to their summary.json (paths or dicts), or is a list
    of them. Any of ``ideal``/``noisy``/``hw`` absent is written as a ``null``
    arm slot (Phase A: ``hw`` null). ``walk_spec`` is embedded verbatim from
    ``walk_spec.WALK_SPEC`` (P5 JS-mirror parity, epic §4).
    """
    by_arm = _normalise(summaries)

    depths = sorted({int(e["steps"])
                     for s in by_arm.values() for e in s["per_depth"]})
    binomial = {str(n): {str(pos): p
                         for pos, p in analytics.binomial_reference(n).items()}
                for n in depths}

    per_arm: dict[str, dict | None] = {}
    for arm in ARMS_ORDER:
        per_arm[arm] = _arm_block(by_arm[arm]) if arm in by_arm else None

    payload = {
        "walk_spec": dict(WALK_SPEC),          # verbatim (P5 decoder parity)
        "encoding": WALK_SPEC["encoding"],
        "arms": list(ARMS_ORDER),
        "depths": depths,
        "binomial_reference": binomial,
        "per_arm": per_arm,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f)
    return out_path


# --- script entry: export from the latest research_runs summaries ----------

def _latest_summary(arm: str, out_dir: str = RESEARCH_RUNS_DIR) -> str | None:
    matches = sorted(glob.glob(os.path.join(out_dir, f"{arm}_*_summary.json")))
    return matches[-1] if matches else None


def main() -> int:
    summaries: dict[str, str] = {}
    for arm in ("ideal", "noisy"):
        path = _latest_summary(arm)
        if path is not None:
            summaries[arm] = path
    if not summaries:
        print("no research_runs/*_summary.json found; run sweep.py --aggregate first")
        return 1
    out = export_replay(summaries)
    with open(out) as f:
        payload = json.load(f)
    filled = [a for a in payload["arms"] if payload["per_arm"][a] is not None]
    print(f"wrote {out}")
    print(f"  arms={payload['arms']} filled={filled} depths={payload['depths']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
