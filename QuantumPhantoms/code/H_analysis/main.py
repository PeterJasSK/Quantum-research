"""Section H: analysis. What the run shows, with its limits -> analysis.json.

    cohort vs rulebook   marginals of size and lobe against the published rulebook (total variation distance; at
                         n = 12 this is a sanity check, not a test)
    certificate          the CHSH gate's verdict
    claims               every quantum claim: level, bound, rigour of the bound, passed or not. A non-pass is a result.
    render checks        fallbacks, inserted-volume error, noise ratio in / out of the lesion, seed sources
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from common import runio
from common.runio import Ctx


def _tvd(counts: Counter, probs: dict, n: int) -> float:
    return 0.5 * sum(abs(counts.get(k, 0) / n - probs.get(k, 0.0)) for k in set(probs) | set(counts))


def _stat(diag: list[dict], key: str) -> dict | None:
    v = [d[key] for d in diag if isinstance(d.get(key), (int, float))]
    return {"n": len(v), "median": float(np.median(v)), "min": float(np.min(v)), "max": float(np.max(v))} if v else None


def run(ctx: Ctx) -> None:
    d = ctx.run_dir
    cohort, rb = runio.load_json(d / "cohort_params.json"), runio.load_json(d / "rulebook.json")
    claims, tiles = runio.load_json(d / "claims.json") or [], runio.load_json(d / "tiles.json")["tiles"]
    n = len(cohort)
    size_of = {round(v, 3): k for k, v in rb["size_mm"].items()}
    sizes = Counter(size_of.get(round(t["size_mm"], 3), "?") for t in cohort)
    lobes = Counter(t["lobe"] for t in cohort)
    diag = [t.get("diag", {}) for t in tiles]
    out = {
        "run": d.name, "backend": runio.load_json(d / "backend.json"),
        "readiness": "one run, small n: descriptive only. A dry run certifies nothing.",
        "cohort_vs_rulebook": {"n": n, "note": "TVD at this n is dominated by sampling noise",
                               "size": {"counts": dict(sizes), "tvd": round(_tvd(sizes, rb["size"], n), 3)},
                               "lobe": {"counts": dict(lobes), "tvd": round(_tvd(lobes, rb["lobe"], n), 3)},
                               "type": dict(Counter(t["type"] for t in cohort)),
                               "margin": dict(Counter(t["margin"] for t in cohort))},
        "certificate": runio.load_json(d / "certificate.json"),
        "claims": [{k: c.get(k) for k in ("stage", "config", "family", "claim_level", "value", "sigma", "bound",
                                          "bound_rigour", "passed", "label")} for c in claims],
        "claims_summary": {"total": len(claims), "passed": sum(bool(c.get("passed")) for c in claims),
                           "not_passed": [f"{c.get('stage')}:{c.get('family')}" for c in claims if not c.get("passed")],
                           "rule": "advantage is the exception; a non-pass is a result, not an error"},
        "render": {"tiles": len(tiles), "renderers": dict(Counter(t.get("renderer") for t in tiles)),
                   "fallbacks": [t["tile_id"] for t in tiles if t.get("renderer") == "procedural-fallback"],
                   "seed_sources": dict(Counter(t.get("seed_source", "n/a") for t in tiles)),
                   "volume_pd_pct": _stat(diag, "volume_pd_pct"), "sigma_ratio_in_out": _stat(diag, "sigma_ratio_in_out"),
                   "vdt_d": _stat(diag, "vdt_d")},
    }
    runio.save_json(d / "analysis.json", out)
    s = out["claims_summary"]
    print(f"  claims: {s['passed']} of {s['total']} passed" + (f"; not passed: {', '.join(s['not_passed'])}" if s["not_passed"] else ""))
    print(f"  render: {out['render']['renderers']}, fallbacks {len(out['render']['fallbacks'])}, seeds {out['render']['seed_sources']}")
