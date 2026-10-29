"""Figures for E (2-D exports of 3-D results only): lung run slices + growth curves.

    python -m E_classical_growth.src.figures E_classical_growth/runs/<run_id> [<run_id> ...]

For each run directory: `figures/lung_<site_id>.png` (axial / coronal / sagittal central slices of baseline and
follow-up, with the anatomy barriers), and for all runs together `figures/lung_growth_curves.png`.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

from shared import RE_ROOT  # noqa: E402
from shared.volumes import load_npz  # noqa: E402

FIGURES = Path(__file__).resolve().parent.parent / "figures"
# [E02] Fig. 3 colours: red proliferating, yellow non-proliferative, black necrotic
STATE_COLORS = {1: "#d62728", 2: "#f2c80f", 3: "#111111"}
STATE_CMAP = ListedColormap(["#ffffff00", STATE_COLORS[1], STATE_COLORS[2], STATE_COLORS[3]])
BARRIER_CMAP = ListedColormap(["#ffffff00", "#9e9e9e", "#4a6fa5"])   # 1 hard (outside lung / fissure), 2 soft


def _slices(vol: np.ndarray, c: tuple[int, int, int]) -> list[np.ndarray]:
    z, y, x = c
    return [vol[z], vol[:, y, :][::-1], vol[:, :, x][::-1]]


def lung_figure(run_dir: Path) -> Path:
    gdir = run_dir / "growth_trajectory"
    man = json.loads((gdir / "growth_trajectory.json").read_text())
    summ = json.loads((gdir / "growth_summary.json").read_text())
    env = load_npz(gdir / "environment.npz")
    barrier = env["barrier"]
    snaps = [s for s in man["snapshots"] if s["role"] in ("baseline", "follow-up")]
    states = [load_npz(gdir / s["npz"]["path"])["state"] for s in snaps]
    last = states[-1] > 0
    c = tuple(int(round(v)) for v in np.argwhere(last).mean(axis=0))
    sp = man["spacing_mm_xyz"][0]
    fig, axes = plt.subplots(len(states), 3, figsize=(9, 3.1 * len(states)), squeeze=False)
    for row, (s, st) in enumerate(zip(snaps, states)):
        for col, (b, t, name) in enumerate(zip(_slices(barrier, c), _slices(st, c), ("axial", "coronal", "sagittal"))):
            ax = axes[row, col]
            ax.imshow(b, cmap=BARRIER_CMAP, vmin=0, vmax=2, interpolation="nearest")
            ax.imshow(t, cmap=STATE_CMAP, vmin=0, vmax=3, interpolation="nearest")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"{s['role']} day {s['day']:.0f} · {name}", fontsize=8)
    ck = summ["checks"]
    fig.suptitle(f"{man['site_id']} ({summ['placement_class']}, {summ['tumor_type']}) · lattice {sp} mm · "
                 f"sphericity {ck['sphericity']:.2f} · outside lung {ck['voxels_outside_lung']} · "
                 f"vessel entered day {ck['vessel_entered_day']}", fontsize=8)
    fig.tight_layout()
    out = FIGURES / f"lung_{man['site_id']}.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def growth_curves(run_dirs: list[Path]) -> Path:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6))
    for rd in run_dirs:
        summ = json.loads((rd / "growth_trajectory" / "growth_summary.json").read_text())
        d = np.array([p["day"] for p in summ["per_day"]])
        a1.plot(d, [p["eq_diameter_mm"] for p in summ["per_day"]], label=f"{summ['site_id']} {summ['placement_class']}")
        a2.plot(d, [p["vdt_days"] for p in summ["per_day"]], label=summ["site_id"])
        for s in summ["snapshots"]:
            a1.axvline(s["day"], color="0.8", lw=0.6)
    a1.set_xlabel("day")
    a1.set_ylabel("equivalent diameter (mm)")
    a1.legend(fontsize=7)
    a2.set_xlabel("day")
    a2.set_ylabel("volumetric doubling time (days)")
    fig.tight_layout()
    out = FIGURES / "lung_growth_curves.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="+", type=Path)
    a = ap.parse_args(argv)
    dirs = [d if d.is_absolute() else RE_ROOT / d for d in a.runs]
    for d in dirs:
        print(lung_figure(d).relative_to(RE_ROOT))
    print(growth_curves(dirs).relative_to(RE_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
