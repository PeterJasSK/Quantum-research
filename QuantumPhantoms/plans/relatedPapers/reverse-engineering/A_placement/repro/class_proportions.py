"""Reproduction for target #18 (plan AC-9): placement-class proportions of LIDC consensus nodules
vs Kostis (200 nodules, cited by Ambrosini [F01]): ~0.45 vascularized, ~0.33 well-circumscribed,
~0.22 juxtapleural.

    python -m A_placement.repro.class_proportions --subset A_placement/repro/lidc_subset.txt [--limit N]

Each scan is segmented (cached), every consensus nodule (>= 3 readers, >= 3 mm) is classified with
classes.classify_mask against the RAW TotalSegmentator vessel mask minus the nodule's own voxels.
Thresholds are the fixed constants in classes.py; nothing is fitted to Kostis.
Writes runs/<run_id>/proportions.json and figures/18-class-proportions.png.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from shared.runrecord import start_run
from shared.volumes import read_volume
from A_placement.src.classes import (AGREEMENT_PP, CLASSES, KOSTIS, THRESHOLDS, agreement, classify_mask,
                                     wilson_ci)
from A_placement.src.lidc_io import A_DIR, read_subset
from A_placement.src.segment import segment

FIGURE = A_DIR / "figures" / "18-class-proportions.png"
PAD = 3


def classify_scan(cache: Path) -> list[dict]:
    vol = {k: read_volume(cache / f"{k}.nii.gz")[0] for k in ("lungs", "vessels_raw", "airway", "nodules")}
    info = {n["label"]: n for n in json.loads((cache / "nodules.json").read_text())}
    rows = []
    for lab, n in info.items():
        idx = np.argwhere(vol["nodules"] == lab)
        lo = np.maximum(idx.min(0) - PAD, 0)
        hi = np.minimum(idx.max(0) + PAD + 1, vol["nodules"].shape)
        c = tuple(slice(a, b) for a, b in zip(lo, hi))
        nod = vol["nodules"][c] == lab
        vessels = (vol["vessels_raw"][c] > 0) & ~nod
        cls, stats = classify_mask(nod, vol["lungs"][c], vessels, vol["airway"][c])
        rows.append({"patient_id": cache.name, "label": lab, "class": cls, **stats,
                     **{k: n[k] for k in ("n_readers", "diameter_mm", "radius_mm", "centroid_vox_zyx")}})
    return rows


def figure(props: dict, ci: dict, n: int, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.arange(len(CLASSES))
    ours = [props[c] for c in CLASSES]
    err = np.array([[props[c] - ci[c][0], ci[c][1] - props[c]] for c in CLASSES]).T
    fig, ax = plt.subplots(figsize=(6.4, 4))
    ax.bar(x - 0.2, ours, 0.4, yerr=err, capsize=4, color="#3b6ea5", label=f"ours, LIDC (n={n}, 95% Wilson CI)")
    ax.bar(x + 0.2, [KOSTIS[c] for c in CLASSES], 0.4, color="#c9a227", label="Kostis via Ambrosini [F01]")
    for i, c in enumerate(CLASSES):
        ax.fill_between([i + 0.0, i + 0.4], KOSTIS[c] - AGREEMENT_PP, KOSTIS[c] + AGREEMENT_PP,
                        color="#c9a227", alpha=0.2, lw=0)
    ax.set_xticks(x, ["free\n(well-circumscribed)", "juxtavascular\n(vascularized)", "juxtapleural"])
    ax.set_ylabel("fraction of nodules")
    ax.set_ylim(0, 0.8)
    ax.set_title("#18 placement-class proportions (shaded: ±10 pp pass band)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subset", type=Path, default=A_DIR / "repro" / "lidc_subset.txt")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    subset = read_subset(a.subset)[: a.limit]
    rows, skipped = [], {}
    for pid, _ in subset:
        try:
            rows += classify_scan(segment(pid))
        except (ValueError, FileNotFoundError) as e:
            skipped[pid] = str(e)
            print(f"skip {pid}: {e}")
    n = len(rows)
    counts = {c: sum(r["class"] == c for r in rows) for c in CLASSES}
    props = {c: counts[c] / n for c in CLASSES}
    ci = {c: wilson_ci(counts[c], n) for c in CLASSES}
    verdict = agreement(props)

    run = start_run("A_placement", "repro-proportions", tool="A_placement.repro.class_proportions")
    result = {
        "n_scans": len(subset) - len(skipped), "n_nodules": n, "skipped": skipped,
        "counts": counts, "proportions": {c: round(props[c], 4) for c in CLASSES},
        "wilson_ci95": {c: [round(v, 4) for v in ci[c]] for c in CLASSES},
        "kostis_reference": KOSTIS, "agreement_pp": AGREEMENT_PP, "agreement": verdict,
        "median_radius_mm": round(float(np.median([r["radius_mm"] for r in rows])), 2),
        "thresholds": THRESHOLDS, "nodules": rows,
    }
    (run.path / "proportions.json").write_text(json.dumps(result, indent=2) + "\n")
    figure(props, ci, n, FIGURE)
    run.finish(json.dumps({k: result[k] for k in ("n_scans", "n_nodules", "proportions", "agreement",
                                                    "median_radius_mm")}, sort_keys=True))
    for c in CLASSES:
        print(f"{c:14s} {counts[c]:4d}  {props[c]:.3f}  CI {ci[c][0]:.3f}-{ci[c][1]:.3f}  Kostis {KOSTIS[c]:.2f}")
    print(f"n={n} scans={result['n_scans']}  pass={verdict['pass']}  ordering={verdict['ordering_holds']}  "
          f"median r={result['median_radius_mm']} mm  -> {run.path / 'proportions.json'}")


if __name__ == "__main__":
    main()
