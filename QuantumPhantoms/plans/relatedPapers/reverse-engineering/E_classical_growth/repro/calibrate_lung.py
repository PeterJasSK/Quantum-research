"""Calibrate the lung engine's p0 per tumor type to a published volumetric doubling time (feature plan AC-11, Q6).

    python -m E_classical_growth.repro.calibrate_lung

On a free lattice (all parenchyma level 1, no barriers) grown from the stub seed shape, the simulated VDT at the
reference diameter (params_lung.json `calibration_reference_diameter_mm`) is matched to `vdt_target_days` by
secant iteration on p0 (VDT ∝ 1/p0 to first order). Writes p0 and vdt_achieved_days back into
src/params_lung.json, calibration.json into the run dir and figures/lung_calibration.png.
"""
from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from E_classical_growth.src import kt  # noqa: E402
from E_classical_growth.src.engine import LungEngine, LungParams  # noqa: E402
from E_classical_growth.src.figures import FIGURES  # noqa: E402
from E_classical_growth.src.lattice import Environment, place_seed  # noqa: E402
from E_classical_growth.src.io_contracts import PARAMS  # noqa: E402
from shared import STUBS  # noqa: E402
from shared.runrecord import start_run  # noqa: E402
from shared.seedhash import rng  # noqa: E402
from shared.volumes import load_npz  # noqa: E402

CERT = STUBS / "certificate" / "certificate.json"
SEED_SHAPE = STUBS / "seed_shape" / "seed_shape.npz"
TOL = 0.15


def free_env(spacing: float, half_width_mm: float) -> Environment:
    n = 2 * int(np.ceil(half_width_mm / spacing)) + 1
    z = np.zeros((n, n, n), bool)
    return Environment(spacing, [0.0, 0.0, 0.0], ((n - 1) // 2,) * 3, z, z.copy(), np.ones((n, n, n), np.int8), z.copy())


def grow_to(params: LungParams, ref_mm: float, spacing: float, seed_hex: str, label: str) -> dict:
    env = free_env(spacing, ref_mm / 2 + 2.5)
    s = load_npz(SEED_SHAPE)
    e = LungEngine(env, place_seed(env, s["occupancy"], float(s["spacing_mm_xyz"][0])), params, rng(seed_hex, label))
    per = [e.measure()]
    while per[-1]["eq_diameter_mm"] < ref_mm + 0.8 and e.day < 40000:
        e.step(per[-1]["Rt_mm"])
        per.append(e.measure())
    d = np.array([p["day"] for p in per])
    v = np.array([p["volume_mm3"] for p in per])
    dia = np.array([p["eq_diameter_mm"] for p in per])
    k = int(np.flatnonzero(dia >= ref_mm)[0])
    w = max(10, int(0.1 * d[k]))          # window ≈ 10 % of the elapsed time, ≥ 10 days
    vdt = kt.doubling_time(d, v, window=w)
    return {"vdt_days": float(np.nanmean(vdt[max(k - 2, 0):k + 3])), "day_at_ref": int(d[k]),
            "series": {"day": d.tolist(), "eq_diameter_mm": dia.tolist()}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max-iter", type=int, default=6)
    a = ap.parse_args(argv)
    seed_hex = json.loads(CERT.read_text())["extracted_seed_hex"]
    cfg = json.loads(PARAMS.read_text())
    ref, sp = cfg["calibration_reference_diameter_mm"], cfg["lattice_mm"]
    run = start_run("E_classical_growth", "calibrate-lung", seed_hex=seed_hex, tool="E_classical_growth.repro.calibrate_lung")
    out, curves = {}, {}
    for typ, t in cfg["types"].items():
        target = t["vdt_target_days"]
        p0, hist = t["p0"], []
        for it in range(a.max_iter):
            res = grow_to(LungParams.from_json({**t, "p0": p0}), ref, sp, seed_hex, f"E/calibrate/{typ}")
            hist.append({"p0": round(p0, 6), "vdt_days": round(res["vdt_days"], 2), "day_at_ref": res["day_at_ref"]})
            print(f"  {typ:12s} iter {it}: p0 {p0:.5f} → VDT {res['vdt_days']:7.1f} d (target {target}), "
                  f"{ref} mm at day {res['day_at_ref']}", flush=True)
            if abs(res["vdt_days"] - target) <= 0.05 * target:
                break
            p0 = min(p0 * res["vdt_days"] / target, 1.0)
        t["p0"] = round(hist[-1]["p0"], 6)
        t["vdt_achieved_days"] = hist[-1]["vdt_days"]
        out[typ] = {"target": target, "achieved": hist[-1]["vdt_days"], "p0": t["p0"], "iterations": hist,
                    "within_15pct": abs(hist[-1]["vdt_days"] - target) <= TOL * target}
        curves[typ] = res["series"]
    PARAMS.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    f = run.path / "calibration.json"
    f.write_text(json.dumps({"reference_diameter_mm": ref, "lattice_mm": sp, "types": out}, indent=1) + "\n")
    run.add_output(f, "lung_calibration")
    run.add_output(PARAMS, "params_lung")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6))
    for typ, c in curves.items():
        a1.plot(c["day"], c["eq_diameter_mm"], label=f"{typ} (p0 {out[typ]['p0']:.4f})")
    a1.axhline(ref, color="0.6", lw=0.8, ls="--")
    a1.set_xlabel("day")
    a1.set_ylabel("equivalent diameter (mm)")
    a1.legend(fontsize=7)
    x = np.arange(len(out))
    a2.bar(x - 0.2, [o["target"] for o in out.values()], 0.4, label="target (Hasegawa 2000, verify)", color="0.7")
    a2.bar(x + 0.2, [o["achieved"] for o in out.values()], 0.4, label="simulated", color="C0")
    a2.set_xticks(x, list(out))
    a2.set_ylabel(f"VDT at {ref} mm (days)")
    a2.legend(fontsize=7)
    fig.suptitle("Lung engine calibration: free lattice, stub seed shape", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES / "lung_calibration.png", dpi=120)
    plt.close(fig)
    rj = run.finish("p0 calibration per tumor type")
    print(f"\n{'type':12s} {'target':>7} {'achieved':>9} {'p0':>9}  within ±15 %")
    for typ, o in out.items():
        print(f"{typ:12s} {o['target']:7d} {o['achieved']:9.1f} {o['p0']:9.5f}  {o['within_15pct']}")
    print(f"\n{PARAMS}\n{f}\n{rj}\n{FIGURES / 'lung_calibration.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
