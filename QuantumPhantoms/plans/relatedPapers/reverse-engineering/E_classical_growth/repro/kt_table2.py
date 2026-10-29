"""Reproduce [E02] Table 2 (Kansal–Torquato 2000) with the paper's parameters.

    python -m E_classical_growth.repro.kt_table2                    # paper's reported site count (~1.5e6)
    python -m E_classical_growth.repro.kt_table2 --spacing-scale 1  # literal eq. 2 spacing (~5e4 sites)

Grows a tumor from Rt = 0.1 mm on the variable-density Delaunay lattice (repro/kt_lattice.py) until
Rt = 25 mm (or --max-days), records Rt, growth fraction, necrotic fraction and volumetric doubling time per
day, and compares them with Table 2 at Rt = 0.5 / 5 / 18.5 / 25 mm. Writes kt_table2.json into the run dir
and figures/kt_table2.png, kt_growth_curve.png, kt_cross_sections.png (2-D exports).

Tolerance (feature plan Q3): fractions ±10 percentage points, doubling time ±35 %, day ±25 % of paper Sim.
Randomness: shared.seedhash.rng(stub certificate seed, "E/kt/…") — there is no certificate in a repro.
"""
from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from E_classical_growth.repro import kt_lattice  # noqa: E402
from E_classical_growth.src import kt  # noqa: E402
from E_classical_growth.src.figures import FIGURES, STATE_COLORS  # noqa: E402
from shared import STUBS  # noqa: E402
from shared.runrecord import start_run  # noqa: E402
from shared.seedhash import derive_seed, rng  # noqa: E402

CERT = STUBS / "certificate" / "certificate.json"
CELLS_PER_MM3 = 1.5e6   # derived from Table 2 Data: 1e11 cells in a 25 mm-radius sphere (65.4 cm³)
PAPER_SITES = 1.5e6
TOL = {"growth_fraction": 0.10, "necrotic_fraction": 0.10, "doubling_time_days": 0.35, "day": 0.25}


def run(spacing_scale: float, radius_mm: float, max_days: int, seed_hex: str) -> dict:
    lat = kt_lattice.build(radius_mm=radius_mm, spacing_scale=spacing_scale,
                           seed=derive_seed(seed_hex, "E/kt/lattice") % 2**32)
    g = kt.KTGraph(lat["points"], lat["indptr"], lat["indices"], lat["weight"], rng(seed_hex, "E/kt/table2"))
    targets = list(kt.TABLE2["radius_mm"])
    days, rts, gfs, nfs, snaps = [0], [g.radius()], [], [], {}
    gf, nf = g.fractions()
    gfs.append(gf)
    nfs.append(nf)
    while g.day < max_days and rts[-1] < targets[-1] + 0.5:
        g.step()
        rt = g.radius()
        gf, nf = g.fractions()
        days.append(g.day)
        rts.append(rt)
        gfs.append(gf)
        nfs.append(nf)
        for t in targets:
            if t not in snaps and rt >= t:
                snaps[t] = g.state.copy()
        if g.day % 50 == 0:
            print(f"  day {g.day:4d}  Rt {rt:6.2f} mm  GF {gf:.2f}  NF {nf:.2f}", flush=True)
    days, rts = np.array(days), np.array(rts)
    vol = 4.0 / 3.0 * np.pi * rts ** 3
    vdt = kt.doubling_time(days, vol)
    rows = []
    for i, t in enumerate(targets):
        hit = np.flatnonzero(rts >= t)
        if not hit.size:
            rows.append({"radius_mm": t, "reached": False})
            continue
        k = int(hit[0])
        ours = {"day": int(days[k]), "cell_number": float(vol[k] * CELLS_PER_MM3), "growth_fraction": gfs[k],
                "necrotic_fraction": nfs[k], "doubling_time_days": float(np.nanmean(vdt[max(k - 2, 0):k + 3]))}
        paper = {q: kt.TABLE2[q]["sim"][i] for q in ("day", "cell_number", "growth_fraction", "necrotic_fraction",
                                                       "doubling_time_days")}
        data = {q: kt.TABLE2[q]["data"][i] for q in ("cell_number", "growth_fraction", "necrotic_fraction",
                                                      "doubling_time_days")}
        ok = {q: (abs(ours[q] - paper[q]) <= TOL[q]) if "fraction" in q else
              (abs(ours[q] - paper[q]) <= TOL[q] * paper[q]) for q in TOL}
        rows.append({"radius_mm": t, "stage": kt.TABLE2["stage"][i], "reached": True, "ours": ours,
                     "paper_sim": paper, "paper_data": data, "within": ok, "within_tolerance": all(ok.values())})
    return {"lattice": {"n_sites": int(len(lat["points"])), "radius_mm": radius_mm, "spacing_scale": spacing_scale,
                        "mean_neighbours": float(np.diff(lat["indptr"]).mean()), "paper_sites": PAPER_SITES},
            "params": {"p0": g.p0, "a_mm13": g.a, "b_mm13": g.b, "Rmax_mm": g.rmax, "r_init_mm": kt.R_INIT_MM},
            "tolerance": TOL, "rows": rows,
            "series": {"day": days.tolist(), "Rt_mm": rts.tolist(), "growth_fraction": gfs, "necrotic_fraction": nfs,
                       "vdt_days": [None if np.isnan(v) else float(v) for v in vdt]},
            "_snaps": snaps, "_points": lat["points"]}


def figures(res: dict, tag: str) -> list:
    s = res["series"]
    rows = [r for r in res["rows"] if r["reached"]]
    r_all = np.array(s["Rt_mm"])
    outs = []
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.4))
    for ax, q, lab in zip(axes, ("growth_fraction", "necrotic_fraction", "doubling_time_days", "day"),
                          ("growth fraction", "necrotic fraction", "doubling time (days)", "day reached")):
        if q == "day":
            ax.plot(r_all, s["day"], color="C0", label="ours")
        elif q == "doubling_time_days":
            ax.plot(r_all, [np.nan if v is None else v for v in s["vdt_days"]], color="C0", label="ours")
        else:
            ax.plot(r_all, s[q], color="C0", label="ours")
        ax.plot(kt.TABLE2["radius_mm"], kt.TABLE2[q]["sim"], "s", color="C3", label="paper Sim")
        if "data" in kt.TABLE2[q]:
            ax.plot(kt.TABLE2["radius_mm"], kt.TABLE2[q]["data"], "o", mfc="none", color="k", label="paper Data")
        ax.plot([r["radius_mm"] for r in rows], [r["ours"][q] for r in rows], "^", color="C0")
        ax.set_xscale("log")
        ax.set_xlabel("tumor radius Rt (mm)")
        ax.set_title(lab, fontsize=9)
    axes[2].set_yscale("log")
    axes[0].legend(fontsize=7)
    fig.suptitle(f"[E02] Table 2 reproduction · {res['lattice']['n_sites']:,} sites "
                 f"(spacing scale {res['lattice']['spacing_scale']})", fontsize=9)
    fig.tight_layout()
    outs.append(FIGURES / f"kt_table2{tag}.png")
    fig.savefig(outs[-1], dpi=120)
    plt.close(fig)

    fig, a1 = plt.subplots(figsize=(6, 3.6))
    a1.plot(s["day"], s["Rt_mm"], color="C0")
    a1.set_xlabel("day")
    a1.set_ylabel("radius Rt (mm)", color="C0")
    a2 = a1.twinx()
    a2.plot(s["day"], 4 / 3 * np.pi * r_all ** 3 / 1000, color="C1")
    a2.set_ylabel("volume (cm³)", color="C1")
    a1.set_title("[E02] Fig. 4 analogue: radius and volume vs time", fontsize=9)
    fig.tight_layout()
    outs.append(FIGURES / f"kt_growth_curve{tag}.png")
    fig.savefig(outs[-1], dpi=120)
    plt.close(fig)

    pts = res["_points"]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.7))
    for ax, t, st in zip(axes, kt.TABLE2["radius_mm"], kt.TABLE2["stage"]):
        ax.set_aspect("equal")
        ax.set_title(f"{st} (Rt ≥ {t} mm)", fontsize=9)
        if t not in res["_snaps"]:
            continue
        state = res["_snaps"][t]
        slab = (np.abs(pts[:, 2]) < max(0.02, 0.04 * t)) & (state > 0)
        for code, col in STATE_COLORS.items():
            m = slab & (state == code)
            ax.scatter(pts[m, 0], pts[m, 1], s=1.5, c=col, linewidths=0)
        ax.set_xlim(-1.1 * t, 1.1 * t)
        ax.set_ylim(-1.1 * t, 1.1 * t)
        ax.set_xlabel("mm")
    fig.suptitle("[E02] Fig. 3 analogue: central section (red proliferating, yellow non-proliferative, "
                 "black necrotic)", fontsize=9)
    fig.tight_layout()
    outs.append(FIGURES / f"kt_cross_sections{tag}.png")
    fig.savefig(outs[-1], dpi=120)
    plt.close(fig)
    return outs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spacing-scale", type=float, default=0.29,
                    help="k in z = k·r^(2/3)/6; 0.29 ≈ the paper's 1.5e6 sites within 30 mm, 1 = literal eq. 2")
    ap.add_argument("--lattice-radius-mm", type=float, default=30.0)
    ap.add_argument("--max-days", type=int, default=600)
    a = ap.parse_args(argv)
    seed_hex = json.loads(CERT.read_text())["extracted_seed_hex"]
    tag = "" if a.spacing_scale == 0.29 else f"_k{a.spacing_scale:g}"
    r = start_run("E_classical_growth", f"kt-table2{tag.replace('_', '-')}", seed_hex=seed_hex,
                  tool="E_classical_growth.repro.kt_table2")
    print(f"run {r.path.name}: building lattice (k={a.spacing_scale}, R={a.lattice_radius_mm} mm)", flush=True)
    res = run(a.spacing_scale, a.lattice_radius_mm, a.max_days, seed_hex)
    outs = figures(res, tag)
    res = {k: v for k, v in res.items() if not k.startswith("_")}
    res["seed_note"] = "repro has no certificate: stub certificate seed used (shared/stubs/certificate)"
    out = r.path / "kt_table2.json"
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(f"\nsites {res['lattice']['n_sites']:,} (paper {PAPER_SITES:,.0f}), "
          f"mean neighbours {res['lattice']['mean_neighbours']:.1f}")
    hdr = f"{'Rt mm':>6} | {'day':>15} | {'growth frac':>17} | {'necrotic frac':>17} | {'doubling d':>15} | ok"
    print(hdr + "\n" + "-" * len(hdr))
    print(f"{'':>6} | {'Sim   ours':>15} | {'Data  Sim  ours':>17} | {'Data  Sim  ours':>17} | "
          f"{'Data Sim ours':>15} |")
    for row in res["rows"]:
        if not row["reached"]:
            print(f"{row['radius_mm']:6.1f} | not reached within --max-days")
            continue
        o, p, d = row["ours"], row["paper_sim"], row["paper_data"]
        print(f"{row['radius_mm']:6.1f} | {p['day']:6d} {o['day']:8d} | "
              f"{d['growth_fraction']:.2f} {p['growth_fraction']:.2f} {o['growth_fraction']:5.2f} | "
              f"{d['necrotic_fraction']:.2f} {p['necrotic_fraction']:.2f} {o['necrotic_fraction']:5.2f} | "
              f"{d['doubling_time_days']:4.0f} {p['doubling_time_days']:4.0f} {o['doubling_time_days']:5.1f} | "
              f"{'within tolerance' if row['within_tolerance'] else 'OUT: ' + ','.join(k for k, v in row['within'].items() if not v)}")
    r.add_output(out, "kt_table2")
    run_json = r.finish(f"[E02] Table 2 reproduction, {res['lattice']['n_sites']} sites")
    print(f"\n{out}\n{run_json}")
    for f in outs:
        print(f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
