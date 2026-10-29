"""Drift of B-1 (three placement classes) and B-2, ideal vs Heron-class noise, against the ancestral baseline."""
import argparse
import json

from B_mapping.src.map import DEFAULT_CERT, DEFAULT_SITES, run_variant
from shared import RE_ROOT
from shared.simbackend import sim_label

LETTER_DIR = RE_ROOT / "B_mapping"
CASES = [("b1", "S001", "free"), ("b1", "S002", "juxtavascular"), ("b1", "S003", "juxtapleural"), ("b2", None, "joint")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--b2-heron-shots", type=int, default=256, help="B-2 circuit is ~10^4 CZ: noisy trajectories are slow")
    ap.add_argument("--sites", default=str(DEFAULT_SITES))
    a = ap.parse_args()
    from pathlib import Path
    rows = []
    for variant, site, label in CASES:
        for mode in ("ideal", "heron"):
            run, draw, dr = run_variant(variant, mode, Path(a.sites), DEFAULT_CERT, site or "S001",
                                        a.b2_heron_shots if (variant, mode) == ("b2", "heron") else a.shots, 8,
                                        out_tag=f"drift-{label}-{mode}")
            rows.append({"case": f"{variant}:{label}", "mode": mode, "sim_label": sim_label(mode),
                         "joint_tvd": dr["joint_tvd"], "baseline_tvd": dr["baseline_ancestral_tvd"],
                         "shots": dr["shots"], "invalid": dr["invalid_shot_fraction"], "depth": dr["depth"], "cz": dr["cz_count"],
                         "qubits": dr["qubits_logical"], "run": str(run.path.relative_to(RE_ROOT))})
            r = rows[-1]
            print(f"{r['case']:<20}{mode:<6} TVD {r['joint_tvd']:.4f}  ancestral {r['baseline_tvd']:.4f}  "
                  f"shots {r['shots']}  invalid {r['invalid']:.1%}  depth {r['depth']}  CZ {r['cz']}", flush=True)
    (LETTER_DIR / "data" / "drift_b1_b2.json").write_text(json.dumps(rows, indent=2) + "\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    cases = [f"{v}:{l}" for v, _, l in CASES]
    x = np.arange(len(cases))
    fig, ax = plt.subplots(figsize=(7, 4))
    for off, (key, lab, col) in enumerate([("ideal", "circuit, simulated: ideal", "tab:blue"),
                                           ("heron", "circuit, simulated: Heron-class noise (FakeMarrakesh)", "tab:red")]):
        ax.bar(x + (off - 1) * 0.27, [r["joint_tvd"] for r in rows if r["mode"] == key], 0.27, label=lab, color=col)
    ax.bar(x + 0.27, [r["baseline_tvd"] for r in rows if r["mode"] == "ideal"], 0.27, label="classical ancestral sampler", color="grey")
    ax.set_xticks(x); ax.set_xticklabels(cases, fontsize=8); ax.set_yscale("log")
    ax.set_ylabel("joint TVD to exact rulebook"); ax.legend(fontsize=6)
    ax.set_title("Drift of B-1 / B-2 draws, same shot count", fontsize=9)
    fig.tight_layout(); fig.savefig(LETTER_DIR / "figures" / "drift_b1_b2.png", dpi=150)


if __name__ == "__main__":
    main()
