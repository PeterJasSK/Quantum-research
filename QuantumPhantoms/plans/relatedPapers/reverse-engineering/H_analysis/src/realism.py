"""`realism` section: interior HU, edge width, shell noise of synthetic lesions vs LIDC real nodules, per type."""
from __future__ import annotations

import numpy as np
from scipy import stats

from H_analysis.src import roi

METRICS = ("hu_mean", "hu_std", "edge_width_mm", "shell_sigma")


def lesion_metrics(img: np.ndarray, mask: np.ndarray, host: np.ndarray | None = None) -> dict:
    inner = roi.eroded_interior(mask, 1)
    inner = inner if inner.sum() >= 5 else mask.astype(bool)
    e = roi.edge_width(img, mask)
    sh = roi.shell(mask, 10, 20)
    out = {"hu_mean": float(img[inner].mean()), "hu_std": float(img[inner].std()),
           "edge_width_mm": e["width_10_90_mm"], "shell_sigma": roi.local_noise(img, sh)}
    if host is not None:
        hs = roi.local_noise(host, sh)
        out["host_shell_sigma"] = hs
        out["shell_sigma_ratio"] = out["shell_sigma"] / hs if hs and np.isfinite(hs) else float("nan")
    return out


def _fin(x):
    return [v for v in x if v is not None and np.isfinite(v)]


def run(syn: list[dict], real: list[dict]) -> dict:
    """syn/real: dicts with 'type' + metrics. -> section dict."""
    out: dict = {"per_type": {}, "n": len(syn), "n_real": len(real)}
    types = sorted({s["type"] for s in syn})
    for t in types:
        out["per_type"][t] = {}
        sv_t = [s for s in syn if s["type"] == t]
        rv_t = [r for r in real if r["type"] == t]
        for m in METRICS:
            sv, rv = _fin([s[m] for s in sv_t]), np.array(_fin([r[m] for r in rv_t]))
            d = {"syn": sv, "n_syn": len(sv)}
            if len(rv):
                p5, p50, p95 = np.percentile(rv, [5, 50, 95])
                d["real_summary"] = {"p5": float(p5), "p50": float(p50), "p95": float(p95), "n": int(len(rv))}
                d["syn_percentile"] = [float(stats.percentileofscore(rv, v)) for v in sv]
                d["pass"] = bool(sv) and all(p5 <= v <= p95 for v in sv)
                if len(sv) >= 5 and len(rv) >= 5:
                    k = stats.ks_2samp(sv, rv)
                    d["ks_D"], d["ks_p"] = float(k.statistic), float(k.pvalue)
            else:
                d["real_summary"] = {"n": 0}
                d["status"] = "insufficient input (no real reference)"
            out["per_type"][t][m] = d
    ratios = _fin([s.get("shell_sigma_ratio") for s in syn])
    out["shell_noise_ratio"] = ({"mean": float(np.mean(ratios)), "min": float(np.min(ratios)),
                                 "max": float(np.max(ratios)), "within_10pct": bool(all(abs(r - 1) <= 0.1 for r in ratios)),
                                 "n": len(ratios)} if ratios else {"status": "insufficient input", "n": 0})
    return out
