"""`radiomics` section: feature distributions synthetic vs real, classifier two-sample test, real-vs-real null.

Engine: "radiomics-lite" (own NumPy; first-order 18 + shape 10 + 3-D GLCM over 13 directions, IBSI-style definitions,
fixed bin width 25 HU). PyRadiomics 3.1.0 is not installed (plan Q1); the engine name is recorded in the section.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy import stats

from H_analysis.src import roi
from shared import seedhash

BIN = 25.0
DIRS = [d for d in __import__("itertools").product((-1, 0, 1), repeat=3) if d > (0, 0, 0)]  # 13 directions
ENGINE = "radiomics-lite"


def first_order(v: np.ndarray) -> dict:
    q10, q25, q75, q90 = np.percentile(v, [10, 25, 75, 90])
    hist, _ = np.histogram(np.floor(v / BIN), bins=max(int(np.ptp(np.floor(v / BIN))) + 1, 1))
    p = hist[hist > 0] / hist.sum()
    mu, sd = v.mean(), v.std()
    return {"fo_energy": float((v**2).sum()), "fo_entropy": float(-(p * np.log2(p)).sum()),
            "fo_min": float(v.min()), "fo_p10": float(q10), "fo_p90": float(q90), "fo_max": float(v.max()),
            "fo_mean": float(mu), "fo_median": float(np.median(v)), "fo_iqr": float(q75 - q25),
            "fo_range": float(np.ptp(v)), "fo_mad": float(np.abs(v - mu).mean()),
            "fo_rmad": float(np.abs(v[(v >= q10) & (v <= q90)] - v[(v >= q10) & (v <= q90)].mean()).mean()),
            "fo_rms": float(np.sqrt((v**2).mean())), "fo_skew": float(stats.skew(v)) if sd > 0 else 0.0,
            "fo_kurt": float(stats.kurtosis(v, fisher=False)) if sd > 0 else 0.0, "fo_var": float(v.var()),
            "fo_uniformity": float((p**2).sum()), "fo_total_energy": float((v**2).sum())}


def shape(mask: np.ndarray) -> dict:
    m = mask.astype(bool)
    vol = float(m.sum())
    surf = float((m ^ ndi.binary_erosion(m)).sum())  # boundary-voxel count as surface proxy
    z, y, x = np.nonzero(m)
    pts = np.stack([z, y, x], 1).astype(float)
    ev = np.sort(np.linalg.eigvalsh(np.cov(pts.T))) if len(pts) > 3 else np.ones(3)
    ev = np.clip(ev, 1e-9, None)
    ax = 4 * np.sqrt(ev)
    maxd = float(np.sqrt(((pts.max(0) - pts.min(0)) ** 2).sum())) if len(pts) else 0.0
    return {"sh_volume": vol, "sh_surface": surf, "sh_sa_to_vol": surf / vol if vol else 0.0,
            "sh_sphericity": float((36 * np.pi * vol**2) ** (1 / 3) / surf) if surf else 0.0,
            "sh_compactness": float(vol / (np.sqrt(np.pi) * surf ** 1.5)) if surf else 0.0,
            "sh_max_diameter": maxd, "sh_major_axis": float(ax[2]), "sh_minor_axis": float(ax[1]),
            "sh_elongation": float(np.sqrt(ev[1] / ev[2])), "sh_flatness": float(np.sqrt(ev[0] / ev[2]))}


def glcm(img: np.ndarray, mask: np.ndarray) -> dict:
    g = np.floor(img / BIN).astype(int)
    m = mask.astype(bool)
    g = g - g[m].min()
    ng = int(g[m].max()) + 1
    ng = min(ng, 64)
    g = np.clip(g, 0, ng - 1)
    acc = np.zeros((ng, ng))
    for d in DIRS:
        a = g[tuple(slice(max(0, -k), g.shape[i] - max(0, k)) for i, k in enumerate(d))]
        b = g[tuple(slice(max(0, k), g.shape[i] - max(0, -k)) for i, k in enumerate(d))]
        ma = m[tuple(slice(max(0, -k), g.shape[i] - max(0, k)) for i, k in enumerate(d))]
        mb = m[tuple(slice(max(0, k), g.shape[i] - max(0, -k)) for i, k in enumerate(d))]
        sel = ma & mb
        h = np.zeros((ng, ng))
        np.add.at(h, (a[sel], b[sel]), 1)
        acc += h + h.T
    if acc.sum() == 0:
        return {k: 0.0 for k in ("glcm_contrast", "glcm_correlation", "glcm_joint_energy", "glcm_joint_entropy",
                                 "glcm_homogeneity", "glcm_idm", "glcm_autocorr", "glcm_cluster_shade")}
    p = acc / acc.sum()
    i, j = np.indices(p.shape)
    mu = (i * p).sum()
    sd = np.sqrt(((i - mu) ** 2 * p).sum())
    nz = p[p > 0]
    return {"glcm_contrast": float(((i - j) ** 2 * p).sum()),
            "glcm_correlation": float(((i - mu) * (j - mu) * p).sum() / sd**2) if sd > 0 else 1.0,
            "glcm_joint_energy": float((p**2).sum()), "glcm_joint_entropy": float(-(nz * np.log2(nz)).sum()),
            "glcm_homogeneity": float((p / (1 + np.abs(i - j))).sum()), "glcm_idm": float((p / (1 + (i - j) ** 2)).sum()),
            "glcm_autocorr": float((i * j * p).sum()), "glcm_cluster_shade": float((((i + j - 2 * mu)) ** 3 * p).sum())}


def extract(img: np.ndarray, mask: np.ndarray) -> dict:
    v = img[mask.astype(bool)].astype(float)
    return {**first_order(v), **shape(mask), **glcm(img, mask)}


def _bh(p: np.ndarray) -> np.ndarray:
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    q[order] = np.minimum.accumulate((p[order] * n / (np.arange(n) + 1))[::-1])[::-1]
    return np.minimum(q, 1)


def _compare(a: np.ndarray, b: np.ndarray, names: list[str]) -> dict:
    ks, smd = [], []
    for k in range(a.shape[1]):
        r = stats.ks_2samp(a[:, k], b[:, k])
        ks.append((r.statistic, r.pvalue))
        sp = np.sqrt((a[:, k].var(ddof=1) + b[:, k].var(ddof=1)) / 2)
        smd.append((a[:, k].mean() - b[:, k].mean()) / sp if sp > 0 else 0.0)
    qv = _bh(np.array([p for _, p in ks]))
    return {"features": {n: {"ks_D": float(d), "ks_p": float(p), "ks_q_bh": float(q), "smd": float(s)}
                         for n, (d, p), q, s in zip(names, ks, qv, smd)},
            "frac_abs_smd_lt_0p5": float(np.mean(np.abs(smd) < 0.5))}


def c2st(x_a, x_b, groups, seed_hex: str, label: str) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler

    x = np.vstack([x_a, x_b])
    y = np.r_[np.zeros(len(x_a)), np.ones(len(x_b))]
    ng = len(set(groups))
    if ng < 5 or min(len(x_a), len(x_b)) < 10:
        return {"status": "insufficient input", "n": [len(x_a), len(x_b)]}
    rng = seedhash.rng(seed_hex, label)
    oof = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(x, y, groups):
        sc = StandardScaler().fit(x[tr])
        clf = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(x[tr]), y[tr])
        oof[te] = clf.predict_proba(sc.transform(x[te]))[:, 1]
    auc = roc_auc_score(y, oof)
    boots = []
    for _ in range(200):
        i = rng.integers(0, len(y), len(y))
        if len(set(y[i])) == 2:
            boots.append(roc_auc_score(y[i], oof[i]))
    return {"auc": float(auc), "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}


def run(syn: list[dict], real: list[dict], seed_hex: str) -> dict:
    """syn/real: dicts {type, patient, features:{name:val}}."""
    out: dict = {"engine": ENGINE, "bin_width_hu": BIN, "n": len(syn), "n_real": len(real)}
    if len(syn) < 5 or len(real) < 5:
        out["status"] = "insufficient input"
        out["note"] = "need >= 5 synthetic and >= 5 real lesions for distribution comparison"
        return out
    names = sorted(syn[0]["features"])
    xs = np.array([[s["features"][n] for n in names] for s in syn])
    xr = np.array([[r["features"][n] for n in names] for r in real])
    cmp_ = _compare(xs, xr, names)
    out["n_features"] = len(names)
    out["frac_abs_smd_lt_0p5"] = cmp_["frac_abs_smd_lt_0p5"]
    out["per_feature"] = cmp_["features"]
    out["c2st"] = c2st(xs, xr, [s["patient"] for s in syn] + [r["patient"] for r in real], seed_hex, "H.c2st")
    # null: patient-level split halves of the real set
    pats = sorted({r["patient"] for r in real})
    fr, au = [], []
    for k in range(50):
        rng = seedhash.rng(seed_hex, f"H.null.{k}")
        half = set(rng.permutation(pats)[: len(pats) // 2])
        a = [i for i, r in enumerate(real) if r["patient"] in half]
        b = [i for i, r in enumerate(real) if r["patient"] not in half]
        if len(a) < 5 or len(b) < 5:
            continue
        fr.append(_compare(xr[a], xr[b], names)["frac_abs_smd_lt_0p5"])
        if k < 10:
            res = c2st(xr[a], xr[b], [real[i]["patient"] for i in a + b], seed_hex, f"H.null.c2st.{k}")
            if "auc" in res:
                au.append(res["auc"])
    out["null"] = {"frac_abs_smd_lt_0p5": float(np.mean(fr)) if fr else None,
                   "c2st_auc": float(np.mean(au)) if au else None, "n_splits": len(fr)}
    return out
