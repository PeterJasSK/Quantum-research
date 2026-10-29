"""2-D export of a placement run (plan AC-12). Export only: nothing reads this figure back.

    python -m A_placement.src.export_figures --run A_placement/runs/<run_id>

One row per placement class (its first site), three orthogonal slices through the site centre:
CT (lung window) with lobe, vessel and airway contours and the nominal-radius circle.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from shared import RE_ROOT
from shared.volumes import read_volume
from A_placement.src.classes import CLASSES
from A_placement.src.lidc_io import A_DIR

FIGURE = A_DIR / "figures" / "18-host-sites.png"
LOBE_COLORS = ["#e41a1c", "#ff7f00", "#4daf4a", "#984ea3", "#377eb8"]


def export(run_dir: Path, out: Path = FIGURE) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sites = json.loads((run_dir / "sites.json").read_text())
    vols = {k: read_volume(run_dir / f"{k}.nii.gz")[0] for k in ("host_ct", "lobes", "vessels", "airway")}
    _, meta = read_volume(run_dir / "lobes.nii.gz")
    sx, sy, sz = meta["spacing_mm_xyz"]
    first = {}
    for s in sites["sites"]:
        first.setdefault(s["context"]["placement_class"], s)
    rows = [c for c in CLASSES if c in first]
    fig, axes = plt.subplots(len(rows), 3, figsize=(10, 3.4 * len(rows)), squeeze=False)
    for r, cls in enumerate(rows):
        s = first[cls]
        z, y, x = s["center_vox_zyx"]
        rad = s["context"]["extra"]["nominal_radius_mm"]
        views = [("axial", np.s_[z, :, :], (x, y), sy / sx),
                 ("coronal", np.s_[:, y, :], (x, z), sz / sx),
                 ("sagittal", np.s_[:, :, x], (y, z), sz / sy)]
        for c, (name, sl, (u, v), aspect) in enumerate(views):
            ax = axes[r, c]
            img = vols["host_ct"][sl]
            origin = "upper" if name == "axial" else "lower"
            ax.imshow(img, cmap="gray", vmin=-1000, vmax=400, aspect=aspect, origin=origin)
            for i, col in enumerate(LOBE_COLORS, 1):
                if (vols["lobes"][sl] == i).any():
                    ax.contour(vols["lobes"][sl] == i, [0.5], colors=col, linewidths=0.6, origin=origin)
            for k, col in (("vessels", "#00e5ff"), ("airway", "#ffff00")):
                if vols[k][sl].any():
                    ax.contour(vols[k][sl] > 0, [0.5], colors=col, linewidths=0.4, origin=origin)
            px = sx if name != "sagittal" else sy
            ax.add_patch(plt.Circle((u, v), rad / px, fill=False, color="#ff00ff", lw=1.2))
            ax.set_xticks([]), ax.set_yticks([])
            ax.set_title(f"{s['site_id']} {cls} · {name}" if c == 0 else name, fontsize=9)
    fig.suptitle(f"{sites['host_scan_id']}: one candidate site per placement class "
                 f"(2-D export of 3-D run {run_dir.name})", fontsize=10)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    a = ap.parse_args()
    run = a.run if a.run.is_absolute() else RE_ROOT / a.run
    print(export(run))


if __name__ == "__main__":
    main()
