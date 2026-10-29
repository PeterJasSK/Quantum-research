"""Wootton quantum blur: 2-D paper-style reproduction and 3-D seed-shape adaptation, with Gaussian baseline."""
import json

import numpy as np

from B_mapping.src.blur import best_gaussian, corr, gaussian_blur, quantum_blur
from shared import RE_ROOT

LETTER_DIR = RE_ROOT / "B_mapping"
THETAS = [0.1 * np.pi, 0.25 * np.pi, 0.5 * np.pi]


def heightmap(n=16):
    y, x = np.mgrid[0:n, 0:n]
    h = 0.05 + np.exp(-((x - 5) ** 2 + (y - 5) ** 2) / 6) + 0.7 * np.exp(-((x - 11) ** 2 + (y - 10) ** 2) / 4)
    h[(abs(x - 8) < 1) & (y > 2)] += 0.5
    return h


def sphere(n=8, r=3.0):
    z, y, x = np.mgrid[0:n, 0:n, 0:n] - (n - 1) / 2
    return (x ** 2 + y ** 2 + z ** 2 <= r ** 2).astype(float) + 0.02


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    res = {"sim_label": "simulated: ideal", "hardware": None, "2d": [], "3d": []}
    h2 = heightmap()
    h3 = sphere()
    fig, ax = plt.subplots(4, len(THETAS) + 1, figsize=(10, 9))
    ax[0, 0].imshow(h2); ax[0, 0].set_title("2-D input", fontsize=8)
    ax[1, 0].axis("off")
    ax[2, 0].imshow(h3[4]); ax[2, 0].set_title("3-D sphere, mid slice", fontsize=8)
    ax[3, 0].axis("off")
    for j, th in enumerate(THETAS, 1):
        for key, h, rows in (("2d", h2, (0, 1)), ("3d", h3, (2, 3))):
            q = quantum_blur(h, th)
            sg, c = best_gaussian(h, q)
            g = gaussian_blur(h, sg)
            res[key].append({"theta_over_pi": th / np.pi, "best_sigma": sg, "corr_quantum_vs_gaussian": c,
                             "corr_quantum_vs_input": corr(q, h)})
            sl = (lambda a: a) if key == "2d" else (lambda a: a[4])
            ax[rows[0], j].imshow(sl(q)); ax[rows[0], j].set_title(f"quantum, theta={th/np.pi:.2f}pi", fontsize=8)
            ax[rows[1], j].imshow(sl(g)); ax[rows[1], j].set_title(f"gaussian sigma={sg:.2f} (r={c:.2f})", fontsize=8)
            print(f"[simulated: ideal] {key} theta={th/np.pi:.2f}pi best gaussian sigma={sg:.2f}  "
                  f"corr(quantum, gaussian)={c:.3f}  corr(quantum, input)={corr(q, h):.3f}")
    for a in ax.ravel():
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle("Quantum blur vs Gaussian baseline, simulated: ideal", fontsize=10)
    fig.tight_layout()
    fig.savefig(LETTER_DIR / "figures" / "quantum_blur_vs_gaussian.png", dpi=150)
    (LETTER_DIR / "data" / "blur_result.json").write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
