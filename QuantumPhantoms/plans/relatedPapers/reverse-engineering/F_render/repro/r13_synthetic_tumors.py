"""#13 reproduction — SyntheticTumors (Hu et al. CVPR 2023 [H01]) generation recipe, Table 1 + Table 6 verbatim.

The paper's headline (U-Net trained on synthetic tumours: DSC 59.81 % vs 57.63 % with real tumours on LiTS)
needs LiTS/CHAOS data and network training — NOT reproduced here (plan Q5). What we reproduce is the
documented generation pipeline (§3.1, Fig. 3, Appendix Figs 8–10) on a synthetic contrast-liver phantom
(no patient data), with every hyper-parameter from Table 1 / Table 6:

  location  v = [f ⊗ g(σa) > mean(liver) + b], σa = 0.5 + 0.025 σp, b = 15; reject sites with a vessel within r
  texture   N(µt, σp), µt ~ U(30, µp − 10); cubic up-scale η ~ U(1.1, 1.5); blur σb = 0.6
  shape     ellipsoid, half-axes ~ U(0.75, 1.25)·r (r = 8 "small", 16 "medium" voxels, Table 6);
            elastic deformation σe ~ U[1, 2] / U[3, 6]; mask blur σc ~ U(0.6, 1.2)
  place     f' = (1 − t'') f + t'' T''                                              (eq. 4)
  mass eff. γmax = 1.3 r, I = 30                                                     (eq. 5)
  capsule   e = [0.4 ≤ t'' ≤ 0.7], e' = e ⊗ g(σd = 0.8), f''' = f'' + d e', d = 120  (eq. 6–8)

Checked numbers: generated tumour mean HU lies in µt's range, and the capsule/mass-effect steps act only
inside γmax. The lung adaptation (no capsule, library HU, E lattice instead of an ellipsoid) is
F_render.src.render; its figure is figures/render-lidc-*.png.

    python -m F_render.repro.r13_synthetic_tumors
"""
from __future__ import annotations

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from F_render.src import io as fio  # noqa: E402
from F_render.src import noise as fn  # noqa: E402
from F_render.src import texture as ftex  # noqa: E402
from F_render.src.status import set_reproduced  # noqa: E402
from shared.runrecord import start_run  # noqa: E402
from shared.seedhash import rng  # noqa: E402

SEED = "13" * 32
SP = np.array([2.5, 0.8, 0.8])             # z y x mm
SHAPE = (48, 192, 192)
MU_P, SIGMA_P = 110.0, 15.0                # contrast-enhanced liver parenchyma (synthetic)
TABLE6 = {"small": (8, (1.0, 2.0)), "medium": (16, (3.0, 6.0))}


def liver_phantom(g):
    zz, yy, xx = np.indices(SHAPE).astype(np.float32)
    c = np.array(SHAPE) / 2
    body = (((yy - c[1]) / 90) ** 2 + ((xx - c[2]) / 90) ** 2) < 1
    liver = ((zz - c[0]) / 20) ** 2 + ((yy - c[1]) / 60) ** 2 + ((xx - c[2] + 10) / 70) ** 2 < 1
    vessels = np.zeros(SHAPE, bool)
    for y0, x0 in ((70, 80), (110, 120), (90, 60)):
        vessels |= ((yy - y0) ** 2 + (xx - x0) ** 2 < 3.0 ** 2) & liver
    f = np.where(body, 40.0, -1000.0).astype(np.float32)
    f[liver] = MU_P
    f[vessels] = 180.0
    f = ndi.gaussian_filter(f, (0.4, 0.8, 0.8))
    fr = np.linspace(0, 0.6, 40)
    f += fn.noise_slices(SHAPE, SP[2], SP[1], fr, fr * np.exp(-(fr / 0.2) ** 2), g, sigma=SIGMA_P) * body
    return f, liver


def generate(f, liver, size: str, g):
    r, se_rng = TABLE6[size]
    sigma_a = 0.5 + 0.025 * SIGMA_P
    fs = ndi.gaussian_filter(f, sigma_a)
    T = fs[liver].mean() + 15.0                                           # b = 15
    v = (fs > T) & liver
    rz = max(int(round(r * SP[1] / SP[0])), 1)
    cand = np.argwhere(ndi.binary_erosion(liver, iterations=r // 2))
    for _ in range(500):
        cz, cy, cx = cand[g.integers(len(cand))]
        if not v[max(cz - rz, 0):cz + rz + 1, cy - r:cy + r + 1, cx - r:cx + r + 1].any():
            break
    mu_t = float(g.uniform(30, MU_P - 10))
    eta = float(g.uniform(1.1, 1.5))
    tex = ftex.texture_field(SHAPE, mu_t, SIGMA_P, g, eta, 0.6, renormalise=False)
    half = np.array([r * SP[1] / SP[0], r, r]) * g.uniform(0.75, 1.25, 3)
    t = ftex.ellipsoid_mask(SHAPE, (cz, cy, cx), half)
    sigma_e = float(g.uniform(*se_rng))
    t = ftex.deform_shape(t, SP, sigma_e * SP[1], 4 * SP[1], g)            # σe voxels → displacement amplitude
    t2 = np.clip(ndi.gaussian_filter(t, float(g.uniform(0.6, 1.2))), 0, 1)
    f1 = (1 - t2) * f + t2 * tex                                           # eq. 4
    r_mm = r * SP[1]
    f2 = ftex.mass_effect(f1, (cz, cy, cx), r_mm, SP, 30.0, 1.3)           # eq. 5
    t2w = ftex.mass_effect(t2, (cz, cy, cx), r_mm, SP, 30.0, 1.3)
    f3 = f2 + ftex.capsule(t2w, (0.4, 0.7), 0.8, 120.0)                    # eq. 6–8
    core = t2w > 0.9
    return {"stages": (f, tex, t2, f1, f2, f3), "center": (cz, cy, cx), "mu_t": mu_t, "eta": eta,
            "sigma_e": sigma_e, "mean_core_hu": float(f2[core].mean()), "std_core_hu": float(f2[core].std()),
            "changed_outside_gmax": float(np.abs(f3 - f1)[_outside(f1.shape, (cz, cy, cx), 1.3 * r_mm)].max())}


def _outside(shape, c, radius_mm):
    zz, yy, xx = np.indices(shape)
    d = np.sqrt(((zz - c[0]) * SP[0]) ** 2 + ((yy - c[1]) * SP[1]) ** 2 + ((xx - c[2]) * SP[2]) ** 2)
    return d > radius_mm + 3 * SP[0]


def main() -> int:
    run = start_run("F_render", "repro-13", seed_hex=SEED, tool="F_render.repro.r13_synthetic_tumors")
    g = rng(SEED, "F.r13")
    f, liver = liver_phantom(g)
    res = {k: generate(f, liver, k, g) for k in TABLE6}
    fig, axs = plt.subplots(2, 6, figsize=(14, 5), dpi=100)
    titles = ["liver (synthetic)", "texture T''", "mask t''", "placed f' (eq. 4)", "mass effect f''", "capsule f'''"]
    for i, (k, r) in enumerate(res.items()):
        cz, cy, cx = r["center"]
        w = TABLE6[k][0] * 2 + 6
        for j, (im, ti) in enumerate(zip(r["stages"], titles)):
            sl = im[cz, max(cy - w, 0):cy + w, max(cx - w, 0):cx + w]
            axs[i, j].imshow(sl, cmap="gray", vmin=(0 if j == 2 else -40), vmax=(1 if j == 2 else 220))
            axs[i, j].set_xticks([])
            axs[i, j].set_yticks([])
            axs[i, j].set_title(f"{ti}" if i == 0 else "", fontsize=8)
        axs[i, 0].set_ylabel(f"{k}: r={TABLE6[k][0]} vox\nµt={r['mu_t']:.0f} η={r['eta']:.2f}", fontsize=8)
    fig.suptitle("#13 [H01] generation pipeline, Table 1/6 parameters verbatim, synthetic liver phantom "
                 "(W240/L90; no patient data)", fontsize=9)
    fig.tight_layout()
    fig.savefig(fio.F_DIR / "figures" / "r13-synthetic-tumors-liver.png")
    plt.close(fig)
    summary = {k: {kk: vv for kk, vv in v.items() if kk not in ("stages", "center")} for k, v in res.items()}
    (run.path / "r13_results.json").write_text(json.dumps(summary, indent=1) + "\n")
    in_range = all(30 - 3 * SIGMA_P / 4 <= v["mean_core_hu"] <= MU_P - 10 + 3 * SIGMA_P / 4 for v in summary.values())
    local = all(v["changed_outside_gmax"] < 1e-3 for v in summary.values())
    set_reproduced(13, "adapted", {
        "quantity": "H01 generation pipeline (Table 1 + Table 6 hyper-parameters, eqs. 1–8)",
        "paper_value": "Fig. 3 / Appendix Figs 8–10 (qualitative); tumour mean HU = µt ~ U(30, µp − 10)",
        "our_value": "; ".join(f"{k}: core mean {v['mean_core_hu']:.1f} HU (µt {v['mu_t']:.1f}), σ {v['std_core_hu']:.1f}"
                               for k, v in summary.items()) + f"; edits confined to γmax: {local}",
        "unit": "HU",
        "agreement": ("qualitative + parameter match" if in_range and local else "parameter mismatch")
                     + "; DSC 59.81 % (LiTS training) not reproduced — needs data + training",
        "sim_mode": "n/a", "figure": "figures/r13-synthetic-tumors-liver.png"},
        ["figures/r13-synthetic-tumors-liver.png"])
    run.finish(json.dumps(summary))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
