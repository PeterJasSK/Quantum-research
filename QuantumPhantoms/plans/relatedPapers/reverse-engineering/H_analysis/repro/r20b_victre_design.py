"""R20b - VICTRE reader-study design gives a DeltaAUC standard error consistent with the paper (target #20).

Surrogate: Rolland-Barrett lumpy background (64x64), a Gaussian signal, two paired "modalities" A and B
imaging the same phantom with modality-specific noise whose case correlation rho is swept.
Amplitudes are tuned so AUC_A ~ 0.90 and AUC_B ~ 0.96 (VICTRE DM / DBT totals).
Design = VICTRE heterogeneous group: 30 readers, pool 1000 pairs, 100 pairs per reader, test 1500 neg / 2000 pos,
fully crossed. Dense group: pool 260, test 360/500. Paper SE(DeltaAUC): 0.0073 (hetero), 0.0148 (dense).
"Reproduced" if the paper's 0.0073 lies inside the SE band swept over rho (plan Q2).

Usage (cwd = reverse-engineering/):  python -m H_analysis.repro.r20b_victre_design
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from H_analysis.src import mrmc, observer  # noqa: E402
from shared import seedhash  # noqa: E402

H = Path(__file__).resolve().parents[1]
SEED = seedhash.sha256_bytes(b"H.r20b")
N, SIGMA_S, NOISE, LUMP_W, LUMP_MEAN = 64, 3.0, 1.0, 5.0, 8
READERS, PER_READER = 30, 100
RHOS = [0.0, 0.25, 0.5, 0.75]
PAPER = {"hetero": 0.0073, "dense": 0.0148}
DESIGN = {"hetero": dict(pool=1000, n_neg=1500, n_pos=2000), "dense": dict(pool=260, n_neg=360, n_pos=500)}
YY, XX = np.mgrid[:N, :N]
CENTRE = (N - 1) / 2.0
SIGNAL = np.exp(-((YY - CENTRE) ** 2 + (XX - CENTRE) ** 2) / (2 * SIGMA_S**2))
CHANS = observer.lg_channels_2d(N, a=SIGMA_S * np.sqrt(2 * np.pi), n=5)
CH = CHANS.reshape(5, -1)


def lumpy(rng, n: int) -> np.ndarray:
    """(n, N*N) lumpy backgrounds already flattened."""
    out = np.zeros((n, N * N))
    counts = rng.poisson(LUMP_MEAN, n)
    for i in range(n):
        c = rng.uniform(0, N, (counts[i], 2))
        g = np.exp(-(((YY[None] - c[:, 0, None, None]) ** 2 + (XX[None] - c[:, 1, None, None]) ** 2)
                     / (2 * LUMP_W**2))).sum(0)
        out[i] = g.ravel()
    return out


def channel_data(rng, n: int, amp_a: float, amp_b: float, rho: float, signal_present: bool):
    """Channel outputs (n, 5) for modality A and B of the same phantom."""
    bg = lumpy(rng, n)
    shared = rng.normal(0, NOISE, (n, N * N))
    na = np.sqrt(rho) * shared + np.sqrt(1 - rho) * rng.normal(0, NOISE, (n, N * N))
    nb = np.sqrt(rho) * shared + np.sqrt(1 - rho) * rng.normal(0, NOISE, (n, N * N))
    sa = amp_a * SIGNAL.ravel() if signal_present else 0.0
    sb = amp_b * SIGNAL.ravel() if signal_present else 0.0
    return (bg + na + sa) @ CH.T, (bg + nb + sb) @ CH.T


def study(seed_label: str, amps, rho: float, design: dict) -> dict:
    rng = seedhash.rng(SEED, f"H.r20b.{seed_label}")
    out = {}
    pools = {m: {} for m in "AB"}
    tests = {m: {} for m in "AB"}
    for sp in (False, True):
        a, b = channel_data(rng, design["pool"], *amps, rho, sp)
        pools["A"][sp], pools["B"][sp] = a, b
        a, b = channel_data(rng, design["n_pos"] if sp else design["n_neg"], *amps, rho, sp)
        tests["A"][sp], tests["B"][sp] = a, b
    sc = {m: {False: [], True: []} for m in "AB"}
    for k in range(READERS):
        r = seedhash.rng(SEED, f"H.reader.{k}.{seed_label}")
        idx = r.choice(design["pool"], PER_READER, replace=False)
        for m in "AB":
            w = observer.cho_train_v(pools[m][True][idx], pools[m][False][idx])
            for sp in (False, True):
                sc[m][sp].append(tests[m][sp] @ w)
    arr = {m: {sp: np.array(v) for sp, v in sc[m].items()} for m in "AB"}
    out["A"] = mrmc.mrmc_auc(arr["A"][False], arr["A"][True])
    out["B"] = mrmc.mrmc_auc(arr["B"][False], arr["B"][True])
    out["delta"] = mrmc.mrmc_delta_auc(arr["B"][False], arr["B"][True], arr["A"][False], arr["A"][True])
    return out


def tune() -> tuple[float, float]:
    """Amplitudes giving AUC_A ~ 0.90, AUC_B ~ 0.96 (bisection on a mid-size study at rho=0)."""
    design = dict(pool=1000, n_neg=600, n_pos=600)
    amps = []
    for target in (0.9005, 0.9596):
        lo, hi = 0.01, 3.0
        for _ in range(9):
            mid = (lo + hi) / 2
            res = study(f"tune{target}", (mid, mid), 0.0, design)["A"]["auc"]
            lo, hi = (mid, hi) if res < target else (lo, mid)
        amps.append((lo + hi) / 2)
    return amps[0], amps[1]


def main() -> int:
    amps = tune()
    print(f"tuned amplitudes A={amps[0]:.4f} B={amps[1]:.4f}")
    result = {}
    for gname, design in DESIGN.items():
        ses = []
        for rho in RHOS:
            res = study(f"{gname}.{rho}", amps, rho, design)
            ses.append(res["delta"]["se"])
            print(f"  {gname:6s} rho={rho:.2f}  AUC_A={res['A']['auc']:.4f} AUC_B={res['B']['auc']:.4f}  "
                  f"dAUC={res['delta']['delta_auc']:.4f}  SE(dAUC)={res['delta']['se']:.4f}")
        result[gname] = [min(ses), max(ses)]
    lo, hi = result["hetero"]
    inside = lo <= PAPER["hetero"] <= hi
    agree = "yes" if inside else "no"
    print(f"dense group: paper={PAPER['dense']} ours=[{result['dense'][0]:.4f}, {result['dense'][1]:.4f}]")
    print(f"paper={PAPER['hetero']} ours=[{lo:.4f}, {hi:.4f}] agreement={agree}")
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    for gname in DESIGN:
        ax.axhline(PAPER[gname], ls="--", lw=0.8, label=f"paper {gname} {PAPER[gname]}")
    ax.set_xlabel("modality case correlation rho"); ax.set_ylabel("SE(dAUC)")
    ax.set_title("VICTRE design, lumpy-background surrogate", fontsize=9)
    for gname, design in DESIGN.items():
        ax.plot(RHOS, [study(f"{gname}.{r}", amps, r, design)["delta"]["se"] for r in RHOS], "o-", label=f"ours {gname}")
    ax.legend(fontsize=7); fig.tight_layout()
    fig_path = H / "figures" / "r20b_mrmc_se.png"
    fig.savefig(fig_path, dpi=130)
    # status.json #20
    sp = H / "status.json"
    st = json.loads(sp.read_text())
    t20 = next(t for t in st["targets"] if t["number"] == 20)
    t20["reproduced"] = {"quantity": "SE(DeltaAUC), VICTRE heterogeneous design", "paper_value": str(PAPER["hetero"]),
                         "our_value": f"[{lo:.4f}, {hi:.4f}]", "unit": "AUC", "agreement": agree,
                         "sim_mode": "n/a", "figure": "figures/r20b_mrmc_se.png"}
    if inside and t20["state"] == "listed":
        t20["state"] = "dissected"  # advanced to reproduced by hand once the dossier exists (see README)
    sp.write_text(json.dumps(st, indent=2) + "\n")
    return 0 if inside else 1


if __name__ == "__main__":
    sys.exit(main())
