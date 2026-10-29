"""Reproduce the Pixel2Cancer [E01] growth behaviours on its liver setting (feature plan AC-5, Q1/Q2).

    python -m E_classical_growth.repro.p2c_behaviour                       # synthetic liver phantom
    python -m E_classical_growth.repro.p2c_behaviour --ct liver.nii.gz --mask liver_mask.nii.gz

[E01] publishes no growth number (its results are segmentation DSC and a reader study), so the reproduced
result is behavioural, with the reference liver hyper-parameters (Organ_HU = [100, 160], steps ∈ [5, 150),
threshold 10, death rule above 50 steps):
  B1  a vessel is entered only after the barrier pressure threshold, and the tumor wraps around it;
  B2  growth flattens against the organ boundary; nothing survives outside the organ mask;
  B3  dead cells appear only once the size rule (steps > 50) has triggered, and sit in the core;
  B4  tumor size over random steps ∈ [5, 150): range, and monotone in steps (Spearman ρ).
Phantom: 1 mm isotropic, ellipsoid liver (HU ≈ 112 ± 12, smoothed noise) with a vertical vessel (r = 3 mm,
200 HU). Writes p2c_behaviour.json into the run dir and figures/p2c_behaviour.png (central slices).
"""
from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from E_classical_growth.src import p2c  # noqa: E402
from E_classical_growth.src.figures import FIGURES  # noqa: E402
from shared import STUBS  # noqa: E402
from shared.runrecord import start_run  # noqa: E402
from shared.seedhash import rng  # noqa: E402
from shared.volumes import read_volume  # noqa: E402

CERT = STUBS / "certificate" / "certificate.json"
ORGAN = "liver"
N = 96                      # phantom edge, voxels (1 mm)
VESSEL_X, VESSEL_R = 14, 3.0


def phantom(g: np.random.Generator):
    z, y, x = np.mgrid[:N, :N, :N].astype(float) - (N - 1) / 2
    organ = (x / 44) ** 2 + (y / 40) ** 2 + (z / 36) ** 2 <= 1
    noise = gaussian_filter(g.normal(size=organ.shape), 1.5)
    hu = 112 + 12 * noise / noise.std()
    vessel = ((x - VESSEL_X) ** 2 + y ** 2 <= VESSEL_R ** 2) & organ
    hu[vessel] = 200
    hu[~organ] = -100
    return hu, organ, vessel


def _vox(c_mm_from_center) -> tuple[int, int, int]:
    return tuple(int(round(v + (N - 1) / 2)) for v in c_mm_from_center)


def b1_vessel(levels, organ, vessel, g) -> tuple[dict, np.ndarray]:
    lo_steps = 90
    start = _vox((0, 0, VESSEL_X - VESSEL_R - 5))        # 5 mm from the vessel wall
    m = p2c.P2C(levels, g)
    m.seed(start)
    res = m.run(lo_steps, p2c.TUMOR_SIZE_STEPS[ORGAN] * 10)  # growth only: no death in B1
    pop = m.volume(m.pop)
    entered = m.volume(m.invaded) & vessel
    zc = start[0]
    yy, xx = np.mgrid[:N, :N] - (N - 1) / 2
    ring = (np.hypot(xx - VESSEL_X, yy) > VESSEL_R) & (np.hypot(xx - VESSEL_X, yy) <= VESSEL_R + 1.5)
    ang = np.arctan2(yy, xx - VESSEL_X)
    sectors = np.floor((ang + np.pi) / (2 * np.pi) * 12).astype(int) % 12
    slab = (pop[zc - 3:zc + 4] > 0).any(axis=0)
    covered = len(set(sectors[ring & slab].tolist()))
    pushes = m.pushes_at_invasion
    out = {"steps": lo_steps, "contact_step": res["contact_step"], "vessel_voxels": int(vessel.sum()),
           "vessel_voxels_entered": int(entered.sum()),
           "min_pushes_at_invasion": int(min(pushes)) if pushes else None,
           "pressure_threshold": p2c.PRESSURE_THRESHOLD, "wrap_sectors_of_12": covered}
    out["pass"] = bool(covered >= 6 and (not pushes or min(pushes) >= p2c.PRESSURE_THRESHOLD))
    return out, pop


def b2_boundary(levels, organ, g) -> tuple[dict, np.ndarray]:
    steps = 90
    start = _vox((0, 0, -44 + 6))                         # 6 mm inside the organ's -x pole
    m = p2c.P2C(levels, g)
    m.seed(start)
    m.run(steps, 10 ** 6)
    pop = m.volume(m.pop)
    outside_before = int(((pop != 0) & ~organ).sum())
    pop = np.where(organ, pop, 0)                         # reference: tumor_out[organ == 0] = 0
    xs = np.argwhere(pop[start[0]] > 0)[:, 1]
    toward, away = start[2] - xs.min(), xs.max() - start[2]
    out = {"steps": steps, "extent_toward_boundary_mm": int(toward), "extent_away_mm": int(away),
           "ratio": round(float(toward / max(away, 1)), 3), "voxels_outside_before_mask": outside_before,
           "voxels_outside_after_mask": int(((pop != 0) & ~organ).sum())}
    out["pass"] = bool(out["ratio"] < 0.8 and out["voxels_outside_after_mask"] == 0)
    return out, pop


def _start_inside(organ, vessel, g, margin=12) -> tuple[int, int, int]:
    from scipy.ndimage import distance_transform_edt
    ok = np.argwhere(distance_transform_edt(organ & ~vessel) > margin)
    return tuple(ok[g.integers(len(ok))])


def b3_death(levels, organ, vessel, g) -> tuple[dict, np.ndarray | None]:
    runs, dead_pop = [], None
    for steps in (30, 45, 50, 60, 90, 120, 60, 90, 120):
        m = p2c.P2C(levels, g)
        start = _start_inside(organ, vessel, g)
        m.seed(start)
        r = m.run(steps, p2c.TUMOR_SIZE_STEPS[ORGAN])
        pop = m.volume(m.pop)
        tum = np.argwhere(pop != 0)
        d_all = np.linalg.norm(tum - start, axis=1).mean()
        dead = np.argwhere(pop == -1)
        d_dead = float(np.linalg.norm(dead - start, axis=1).mean()) if len(dead) else None
        runs.append({"steps": steps, "death_rule": r["death_rule"], "dead": r["dead"],
                     "mean_dist_dead_mm": d_dead, "mean_dist_tumor_mm": round(float(d_all), 2)})
        if r["dead"] and dead_pop is None:
            dead_pop = pop
    small = [x for x in runs if x["steps"] <= p2c.TUMOR_SIZE_STEPS[ORGAN]]
    big = [x for x in runs if x["steps"] > p2c.TUMOR_SIZE_STEPS[ORGAN]]
    core = all(x["mean_dist_dead_mm"] < x["mean_dist_tumor_mm"] for x in big if x["dead"])
    out = {"runs": runs, "dead_in_small": sum(x["dead"] for x in small),
           "big_runs_with_dead": sum(1 for x in big if x["dead"]), "dead_in_core": core}
    out["pass"] = bool(out["dead_in_small"] == 0 and out["big_runs_with_dead"] >= 1 and core)
    return out, dead_pop


def b4_sizes(levels, organ, vessel, g, n=12) -> dict:
    steps = g.integers(5, p2c.MAX_STEPS[ORGAN], n)
    diam = []
    for s in steps:
        m = p2c.P2C(levels, g)
        m.seed(_start_inside(organ, vessel, g))
        m.run(int(s), 10 ** 6)
        v = float((m.volume(m.pop) != 0).sum())          # 1 mm³ voxels
        diam.append(round((6 * v / np.pi) ** (1 / 3), 2))
    rho = float(spearmanr(steps, diam).statistic)
    out = {"steps": steps.tolist(), "eq_diameter_mm": diam, "min_mm": min(diam), "max_mm": max(diam),
           "spearman_rho": round(rho, 3), "single_focus": True}
    out["pass"] = bool(rho > 0.9)
    return out


def figure(levels, b1_pop, b2_pop, b3_pop, res) -> object:
    cmap = ListedColormap(["#4a6fa5", "#e6e6e6", "#c8c8c8", "#aaaaaa"])
    tum = ListedColormap(["#111111", "#ffffff00"] + [matplotlib.cm.Reds(0.3 + 0.07 * k) for k in range(10)])
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    for ax, pop, title in zip(axes, (b1_pop, b2_pop, b3_pop),
                              (f"B1 vessel: {res['B1']['wrap_sectors_of_12']}/12 sectors wrapped, "
                               f"{res['B1']['vessel_voxels_entered']} vessel vox entered",
                               f"B2 boundary: toward/away = {res['B2']['ratio']}",
                               "B3 death: dead core (black)")):
        if pop is None:
            ax.set_title(title + " (no death run)", fontsize=8)
            continue
        z = int(np.argwhere(pop != 0)[:, 0].mean())
        ax.imshow(levels[z], cmap=cmap, vmin=0, vmax=3, interpolation="nearest")
        ax.imshow(pop[z] + 1, cmap=tum, vmin=0, vmax=11, interpolation="nearest")
        ax.set_title(title, fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("[E01] Pixel2Cancer behaviours, liver hyper-parameters (blue = barrier level 0; "
                 "red = population 1–10)", fontsize=9)
    fig.tight_layout()
    out = FIGURES / "p2c_behaviour.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ct", help="optional real liver CT (NIfTI); needs --mask")
    ap.add_argument("--mask", help="optional liver mask (NIfTI, >0 = liver)")
    a = ap.parse_args(argv)
    seed_hex = json.loads(CERT.read_text())["extracted_seed_hex"]
    r = start_run("E_classical_growth", "p2c-behaviour", seed_hex=seed_hex, tool="E_classical_growth.repro.p2c_behaviour")
    g = rng(seed_hex, "E/p2c/behaviour")
    if a.ct:
        hu, _ = read_volume(a.ct)
        organ = read_volume(a.mask)[0] > 0
        vessel = organ & (hu >= p2c.ORGAN_HU[ORGAN][1])
        source = {"ct": a.ct, "mask": a.mask}
        r.add_input(a.ct, "external_ct")
    else:
        hu, organ, vessel = phantom(g)
        source = {"phantom": f"{N}³ mm, ellipsoid liver, vessel r={VESSEL_R} mm at x=+{VESSEL_X} mm"}
    lo, hi = p2c.ORGAN_HU[ORGAN]
    levels = p2c.quantify(hu, organ, lo, hi)
    res = {"organ": ORGAN, "source": source, "organ_hu": [lo, hi], "threshold": p2c.THRESHOLD,
           "levels_voxels": {str(k): int((levels == k).sum()) for k in range(4)}}
    res["B1"], b1_pop = b1_vessel(levels, organ, vessel, g)
    res["B2"], b2_pop = b2_boundary(levels, organ, g)
    res["B3"], b3_pop = b3_death(levels, organ, vessel, g)
    res["B4"] = b4_sizes(levels, organ, vessel, g)
    res["seed_note"] = "repro has no certificate: stub certificate seed used (shared/stubs/certificate)"
    fig = figure(levels, b1_pop, b2_pop, b3_pop, res)
    out = r.path / "p2c_behaviour.json"
    out.write_text(json.dumps(res, indent=1) + "\n")
    r.add_output(out, "p2c_behaviour")
    run_json = r.finish("[E01] behaviour checks B1-B4, liver hyper-parameters")
    b1, b2, b3, b4 = res["B1"], res["B2"], res["B3"], res["B4"]
    pf = {True: "PASS", False: "FAIL"}
    print(f"B1 vessel   {pf[b1['pass']]}  contact step {b1['contact_step']}, vessel voxels entered "
          f"{b1['vessel_voxels_entered']}/{b1['vessel_voxels']}, min pushes at invasion "
          f"{b1['min_pushes_at_invasion']} (threshold {b1['pressure_threshold']}), wrap {b1['wrap_sectors_of_12']}/12")
    print(f"B2 boundary {pf[b2['pass']]}  extent toward/away {b2['extent_toward_boundary_mm']}/"
          f"{b2['extent_away_mm']} mm (ratio {b2['ratio']}), outside before/after mask "
          f"{b2['voxels_outside_before_mask']}/{b2['voxels_outside_after_mask']}")
    print(f"B3 death    {pf[b3['pass']]}  dead cells in steps≤50 runs: {b3['dead_in_small']}; steps>50 runs with "
          f"dead cells: {b3['big_runs_with_dead']}/6; dead in core: {b3['dead_in_core']}")
    print(f"B4 sizes    {pf[b4['pass']]}  eq. diameter {b4['min_mm']}–{b4['max_mm']} mm over steps "
          f"{min(b4['steps'])}–{max(b4['steps'])}, Spearman ρ = {b4['spearman_rho']}")
    print(f"\n{out}\n{run_json}\n{fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
