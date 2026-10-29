"""Final 2-D export (plan AC-14): axial / coronal / sagittal slices through the lesion centre.

PNG only, written to F_render/figures/; host, hybrid and hybrid − host in the lung window (W1500/L−600)
and the mediastinal window (W400/L40), pixel aspect from the voxel spacing. PNGs are never read back.

    python -m F_render.src.export_slices <hybrid_volume.json> [--tag NAME]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from F_render.src import io as fio  # noqa: E402
from shared.volumes import read_volume  # noqa: E402

WINDOWS = {"lung": (1500, -600), "mediastinal": (400, 40)}


def export(manifest: str | Path, tag: str = "render", half_mm: float = 30.0) -> list[Path]:
    doc, mp = fio.load(manifest, "hybrid_volume")
    host, meta = read_volume(fio.ref(mp, doc["files"]["host_ct"]))
    hyb, _ = read_volume(fio.ref(mp, doc["files"]["hybrid_ct"]))
    les, _ = read_volume(fio.ref(mp, doc["files"]["lesion_mask"]))
    sp = np.asarray(meta["spacing_mm_xyz"], float)[::-1]
    c = np.round(ndi.center_of_mass(les)).astype(int) if les.any() else np.array(host.shape) // 2
    h = np.ceil(half_mm / sp).astype(int)
    crop = tuple(slice(max(ci - hi, 0), ci + hi + 1) for ci, hi in zip(c, h))
    views = {  # (2-D array getter, aspect = row spacing / col spacing)
        "axial": (lambda v: v[c[0], crop[1], crop[2]], sp[1] / sp[2]),
        "coronal": (lambda v: v[crop[0], c[1], crop[2]][::-1], sp[0] / sp[2]),
        "sagittal": (lambda v: v[crop[0], crop[1], c[2]][::-1], sp[0] / sp[1]),
    }
    out = []
    fig_dir = fio.F_DIR / "figures"
    fig_dir.mkdir(exist_ok=True)
    for wname, (W, L) in WINDOWS.items():
        fig, axs = plt.subplots(3, 3, figsize=(9, 9), dpi=110)
        for r, (vname, (get, asp)) in enumerate(views.items()):
            for col, (title, vol) in enumerate((("host", host), ("hybrid", hyb))):
                axs[r, col].imshow(get(vol), cmap="gray", vmin=L - W / 2, vmax=L + W / 2, aspect=asp,
                                   interpolation="nearest")
                axs[r, col].set_title(f"{title} — {vname}", fontsize=8)
            d = get(hyb).astype(float) - get(host).astype(float)
            m = max(np.abs(d).max(), 1.0)
            axs[r, 2].imshow(d, cmap="RdBu_r", vmin=-m, vmax=m, aspect=asp, interpolation="nearest")
            axs[r, 2].set_title(f"hybrid − host (±{m:.0f} HU)", fontsize=8)
        for ax in axs.ravel():
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle(f"{doc['host_scan_id']} · {doc['site_id']} · step {doc['snapshot_step']} · {wname} "
                     f"W{W}/L{L} · 2-D export of the 3-D result", fontsize=9)
        fig.tight_layout()
        f = fig_dir / f"render-{tag}-{wname}.png"
        fig.savefig(f)
        plt.close(fig)
        out.append(f)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("--tag", default="render")
    a = ap.parse_args(argv)
    for f in export(a.manifest, a.tag):
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
