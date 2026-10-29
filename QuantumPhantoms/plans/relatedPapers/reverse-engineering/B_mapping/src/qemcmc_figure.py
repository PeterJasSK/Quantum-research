"""Figure of the tumor-patch spectral gaps from the newest qemcmc runs (ideal 8 and 6 spins, Heron 6 spins)."""
import json

from shared import RE_ROOT

RUNS = RE_ROOT / "B_mapping" / "runs"


def newest(mode, n):
    for p in sorted(RUNS.glob(f"*-qemcmc-{mode}"), reverse=True):
        f = p / "qemcmc_result.json"
        if f.exists() and json.loads(f.read_text())["n_spins"] == n:
            return json.loads(f.read_text())
    raise SystemExit(f"no qemcmc-{mode} run with n={n}")


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    i8, i6, h6 = newest("ideal", 8), newest("ideal", 6), newest("heron", 6)
    labels = ["8 spins\nsimulated: ideal", "6 spins\nsimulated: ideal", "6 spins\nHeron-class noise"]
    fig, ax = plt.subplots(figsize=(7, 4))
    series = {"quantum": [i8["ideal_random_draws"]["gap_quantum"], i6["ideal_random_draws"]["gap_quantum"], h6["heron"]["gap_quantum"]],
              "local": [i8["ideal_random_draws"]["gap_local"], i6["ideal_random_draws"]["gap_local"], None],
              "uniform": [i8["ideal_random_draws"]["gap_uniform"], i6["ideal_random_draws"]["gap_uniform"], None]}
    for k, (name, v) in enumerate(series.items()):
        xs = [i + (k - 1) * 0.27 for i, y in enumerate(v) if y is not None]
        ax.bar(xs, [y for y in v if y is not None], 0.27, label=name)
    ax.set_xticks(range(3)); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("MH spectral gap"); ax.legend(fontsize=7)
    ax.set_title(f"Tumor-patch QeMCMC, noisy-Q asymmetry {h6['heron']['asymmetry_Q']:.2f} (Heron arm)", fontsize=9)
    fig.tight_layout()
    fig.savefig(RE_ROOT / "B_mapping" / "figures" / "qemcmc_tumor_gap.png", dpi=150)


if __name__ == "__main__":
    main()
