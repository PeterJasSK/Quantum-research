#!/usr/bin/env python3
"""P1 reconstruction baseline — bank the canonical clean-witness reference.

Standalone analysis/plotting tool for the QAL Darwinian-richness epic (stage P1).
Imports the exact 2018 four-operator model (`code/qalife.py`) as a library, computes
the noiseless *ideal* genealogical entanglement witness `<X^{otimes W}>` vs width W and
vs generation depth, loads the banked Month-4 *hardware* confirm from `research_runs/`,
overlays the *separable null* `prod_i <X_i>` (must sit at ~0, CD-3), and archives the
result (JSON + two PNGs + a README written separately) as the fixed reference every P3+
richness run is judged against (AC-P1.3).

No `code/` change (CD-1): this is a sibling tool that imports the model. The ideal curve
comes from the exact statevector, not the density-matrix `--sim` driver path (which walls
out ~W=7); the exact statevector reaches ~W=13 (2^{26} amps).

CD-3 gate: if the separable null is not ~0 anywhere, the baseline is invalid — the script
prints `[FAIL] separable null not ~0` and exits non-zero without archiving.

Regen the banked baseline with no args:  python analysis/plot_baseline.py
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any

import numpy as np

# --- Path shim (CD-1): make `import qalife` resolve without touching code/ -------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_CODE_DIR = os.path.normpath(os.path.join(_HERE, "..", "code"))
_RESEARCH_RUNS = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))
_DEFAULT_OUT = os.path.normpath(os.path.join(_HERE, "..", "research", "baseline_P1"))
if _CODE_DIR not in sys.path:
    sys.path.insert(0, _CODE_DIR)

import qalife as q4  # noqa: E402  (import after the path shim, by design)


# ---------------------------------------------------------------------------
# Exact ideal witness + separable null (statevector for unitary, DM for damping)
# ---------------------------------------------------------------------------
def ideal_witness_and_sep(width: int, steps: int, thetas: list[float], interaction: str,
                          death: str) -> tuple[float, float]:
    """Exact noiseless `<X^{otimes width}>` (joint) and `prod_k <X_{geno_q(k)}>` (separable
    null) over the genotype line, mirroring `xbasis_witness_from_counts`'s qubit selection
    (`geno_q(k) = 2k`, qalife.py:170/380). Statevector for unitary death, DensityMatrix for
    damping (which cannot be held as a pure state)."""
    qc = q4.build_population(width, steps, thetas[:width], interaction,
                             death=death, measure=False)
    state = (q4.DensityMatrix.from_instruction(qc) if death == "damping"
             else q4.Statevector.from_instruction(qc))
    genos = [q4.geno_q(k) for k in range(width)]
    joint = float(np.real(state.expectation_value(q4._x_string_op(qc.num_qubits, genos))))
    sep = 1.0
    for gq in genos:
        xi = float(np.real(state.expectation_value(q4._x_string_op(qc.num_qubits, [gq]))))
        sep *= xi
    return joint, sep


# ---------------------------------------------------------------------------
# Hardware confirm loader (the banked Month-4 ibm_kingston nn/unitary runs)
# ---------------------------------------------------------------------------
def load_hardware(hw_glob: str, k: float) -> dict[str, Any]:
    """Load `by_width` witness points from every matching hardware run. Collects
    (W, witness, sigma, separable, survives) across files, recomputes the k=2/k=3 survival
    gate (`witness - sep > k*sigma`), and records the source filenames for provenance (CD-6:
    QRNG entropy tracked by source-run filename, the schema field is deferred to P2)."""
    files = sorted(glob.glob(hw_glob))
    by_w: dict[int, dict[str, Any]] = {}
    for path in files:
        with open(path) as fh:
            blob = json.load(fh)
        for w_str, entry in blob.get("by_width", {}).items():
            w = int(w_str)
            by_w[w] = {  # last file wins if a width repeats (identical Month-4 data)
                "witness": float(entry["witness_joint_mean"]),
                "sigma": float(entry["witness_joint_sigma"]),
                "separable": float(entry["separable_mean"]),
                "survives_stored": bool(entry["survives"]),
            }
    widths = sorted(by_w)
    out: dict[str, Any] = {
        "W": widths,
        "witness": [by_w[w]["witness"] for w in widths],
        "sigma": [by_w[w]["sigma"] for w in widths],
        "separable": [by_w[w]["separable"] for w in widths],
        "survives_k2": [],
        "survives_k3": [],
        "source_runs": [os.path.basename(p) for p in files],
    }
    for w in widths:
        signal = by_w[w]["witness"] - by_w[w]["separable"]
        out["survives_k2"].append(bool(signal > 2.0 * by_w[w]["sigma"]))
        out["survives_k3"].append(bool(signal > 3.0 * by_w[w]["sigma"]))
    return out


# ---------------------------------------------------------------------------
# Figures (Agg backend, no display) — degrade gracefully if matplotlib absent (R5)
# ---------------------------------------------------------------------------
def render_figures(data: dict[str, Any], out_dir: str, k: float) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001 — any import/backend failure is non-fatal (R5)
        print(f"[WARN] matplotlib unavailable ({exc}); skipping figures. "
              f"JSON is banked and figures regenerate from it.")
        return False

    vw = data["witness_vs_W"]
    hw = vw["hardware"]

    # --- witness vs W ---
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    ax.plot(vw["W"], vw["ideal"], "-o", color="#1f77b4", label="ideal (exact statevector)")
    ax.plot(vw["W"], vw["ideal_separable"], ":", color="#1f77b4", alpha=0.6,
            label="ideal separable null")
    ax.errorbar(hw["W"], hw["witness"], yerr=[k * s for s in hw["sigma"]],
                fmt="s", color="#d62728", capsize=3, label=f"hardware (ibm_kingston, +/-{k:g}sigma)")
    ax.plot(hw["W"], hw["separable"], "x", color="#2ca02c", label="hardware separable null")
    ax.axhline(0.0, color="grey", lw=0.6)
    if 24 in hw["W"]:
        ax.annotate("W*=24 (marginal ALIVE)", xy=(24, 0.038), xytext=(24, 0.20),
                    ha="center", fontsize=8,
                    arrowprops=dict(arrowstyle="->", color="grey", lw=0.7))
    ax.set_xlabel("genealogy width W (individuals)")
    ax.set_ylabel(r"genealogical witness $\langle X^{\otimes W}\rangle$")
    ax.set_title("P1 baseline — witness vs W (ideal saturates; hardware is the ceiling)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p1 = os.path.join(out_dir, "baseline_P1_witness_vs_W.png")
    fig.savefig(p1, dpi=150)
    plt.close(fig)

    # --- witness vs generation depth (at fixed W_GEN) ---
    vg = data["witness_vs_gen"]
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    ax.plot(vg["gen"], vg["ideal"], "-o", color="#1f77b4",
            label=f"ideal (exact), W_fixed={vg['W_fixed']}")
    ax.axhline(0.0, color="grey", lw=0.6)
    ax.set_xlabel("genealogy depth g (line grown to width g+1)")
    ax.set_ylabel(r"ideal witness $\langle X^{\otimes(g+1)}\rangle$")
    ax.set_title("P1 baseline — exact witness vs generation depth (mutation-decayed)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p2 = os.path.join(out_dir, "baseline_P1_witness_vs_gen.png")
    fig.savefig(p2, dpi=150)
    plt.close(fig)

    print(f"[OK] figures written:\n  {p1}\n  {p2}")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Bank the P1 clean-witness baseline.")
    ap.add_argument("--sim-widths", default="2,3,4,5,6,8,10,12",
                    help="CSV of exact-ideal widths (statevector wall ~W=13).")
    ap.add_argument("--w-gen", type=int, default=12,
                    help="fixed width for the vs-generation-depth curve.")
    ap.add_argument("--steps", type=int, default=3, help="mutation steps per individual.")
    ap.add_argument("--mut-scale", type=float, default=0.08,
                    help="mutation angle scale (matches the Month-4 hardware runs).")
    ap.add_argument("--seed", type=int, default=100, help="PRNG seed for the sim thetas.")
    ap.add_argument("--k", type=float, default=2.0, help="sigma multiple for survival gate.")
    ap.add_argument("--interaction", default="nn", help="interaction topology.")
    ap.add_argument("--death", default="unitary", help="death mode for the ideal curve.")
    ap.add_argument("--hw-glob",
                    default=os.path.join(_RESEARCH_RUNS,
                                         "qalife_*_nn_unitary_ibm_kingston_*.json"),
                    help="glob for the banked hardware confirm runs.")
    ap.add_argument("--sep-tol", type=float, default=0.05,
                    help="CD-3 gate: max |separable null| allowed.")
    ap.add_argument("--out-dir", default=_DEFAULT_OUT, help="baseline archive directory.")
    args = ap.parse_args()

    sim_widths = [int(x) for x in args.sim_widths.split(",") if x.strip()]
    n_max = max(sim_widths + [args.w_gen])
    # Reproducible modeled mutation angles (PRNG stand-in used by sim/selftest, qalife.py:522).
    # Pass seed + mut_scale explicitly: _sim_thetas defaults mut_scale=1.0, we want the
    # hardware-matched 0.08 so the ideal reflects the MODELED biology, not a clean GHZ (R4).
    thetas = q4._sim_thetas(n_max, args.seed, args.mut_scale)

    print(f"[..] computing exact ideal witness for widths {sim_widths} "
          f"(steps={args.steps}, mut_scale={args.mut_scale}, seed={args.seed})")
    ideal: list[float] = []
    ideal_sep: list[float] = []
    for w in sim_widths:
        j, s = ideal_witness_and_sep(w, args.steps, thetas, args.interaction, args.death)
        ideal.append(j)
        ideal_sep.append(s)
        print(f"     W={w:>2}: ideal={j:+.4f}  separable={s:+.2e}")

    print(f"[..] computing exact ideal witness vs generation depth at W_fixed={args.w_gen}")
    vs_gen_ideal = q4.witness_ideal_by_gen(args.w_gen, args.steps, thetas,
                                           args.interaction, death=args.death)
    gen_axis = list(range(len(vs_gen_ideal)))

    print(f"[..] loading hardware confirm: {args.hw_glob}")
    hw = load_hardware(args.hw_glob, args.k)
    if not hw["W"]:
        print("[FAIL] no hardware confirm runs matched the glob — cannot bank the baseline.")
        return 1
    print(f"     hardware widths {hw['W']} from {hw['source_runs']}")

    # --- CD-3 gate: separable null must sit at ~0 everywhere or the baseline is invalid ---
    sep_pool = [abs(s) for s in ideal_sep] + [abs(s) for s in hw["separable"]]
    sep_max = max(sep_pool)
    if sep_max >= args.sep_tol:
        print(f"[FAIL] separable null not ~0: max|sep|={sep_max:.4f} >= tol={args.sep_tol} "
              f"(CD-3) — baseline invalid, not archiving.")
        return 1
    print(f"[OK] CD-3 separable-null gate passed: max|sep|={sep_max:.2e} < {args.sep_tol}")

    baseline: dict[str, Any] = {
        "meta": {
            "stage": "P1",
            "model": "AlvarezRodriguez2018_full",
            "interaction": args.interaction,
            "death": args.death,
            "steps": args.steps,
            "mut_scale": args.mut_scale,
            "seed": args.seed,
            "k": args.k,
            "ideal_method": "statevector_exact (qalife.build_population + X-string op)",
            "sim_widths": sim_widths,
            "hw_source_runs": hw["source_runs"],
            "hw_backend": "ibm_kingston",
        },
        "witness_vs_W": {
            "W": sim_widths,
            "ideal": ideal,
            "ideal_separable": ideal_sep,
            "hardware": {
                "W": hw["W"],
                "witness": hw["witness"],
                "sigma": hw["sigma"],
                "separable": hw["separable"],
                "survives_k2": hw["survives_k2"],
                "survives_k3": hw["survives_k3"],
            },
        },
        "witness_vs_gen": {
            "W_fixed": args.w_gen,
            "gen": gen_axis,
            "ideal": vs_gen_ideal,
        },
        "separable_null_max": sep_max,
    }

    os.makedirs(args.out_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, "baseline_P1.json")
    with open(json_path, "w") as fh:
        json.dump(baseline, fh, indent=2)
    print(f"[OK] banked baseline: {json_path}")

    render_figures(baseline, args.out_dir, args.k)
    print("[DONE] P1 baseline archived.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
