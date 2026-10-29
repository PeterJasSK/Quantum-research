"""Reproduce Borujeni et al. [B09]: 4-node oil-stock Bayesian network on a simulated circuit."""
import argparse
import json
from datetime import datetime, timezone

import numpy as np

from B_mapping.src.compiler import compile_rulebook, decode_bits
from B_mapping.src.rulebook import DATA, joint_table, tvd
from shared import CONTRACT_VERSION, RE_ROOT
from shared.seedhash import code_hash, hash_json
from shared.simbackend import make_simulator, sim_label, transpile_heron

LETTER_DIR = RE_ROOT / "B_mapping"
NETICA = {"IR": 0.750, "OI": 0.600, "SM": 0.425, "SP": 0.499}   # P(X=0), [B09]
PAPER_HW_RANGE = {0: "4.9 (Yorktown) - 36.3 (Burlington)", 3: "9.1 - 24"}
RUNS, SHOTS = 10, 8192


def build_rulebook() -> dict:
    """CPTs from [B09]. State 0 / 1 = state index 0 / 1."""
    def node(name, parents, cpt, src):
        return {"name": name, "states": ["0", "1"], "parents": parents, "context_keys": [], "cpt": cpt, "sources": [src]}
    src = "Borujeni et al. 2021 [B09], oil-stock network, Table of CPTs"
    nodes = [
        node("IR", [], [0.75, 0.25], src),
        node("OI", [], [0.6, 0.4], src),
        node("SM", ["IR"], [[0.3, 0.7], [0.8, 0.2]], src),                        # P(SM=1|IR)=0.7/0.2
        node("SP", ["OI", "SM"], [[[0.9, 0.1], [0.4, 0.6]], [[0.5, 0.5], [0.2, 0.8]]], src),  # 0.1/0.6/0.5/0.8
    ]
    doc = {"contract": "rulebook", "contract_version": CONTRACT_VERSION,
           "produced_by": {"letter": "B", "tool": "B_mapping.repro.borujeni", "run_id": None,
                           "code_hash": code_hash([LETTER_DIR / "src"])},
           "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "stub": False, "upstream": [], "rulebook_id": "borujeni-oilstock", "nodes": nodes}
    doc["rulebook_hash"] = hash_json(doc, exclude=["rulebook_hash", "created_utc", "produced_by"])
    return doc


def rmspe(meas: dict, exact: dict) -> float:
    return 100 * float(np.sqrt(np.mean([((meas[k] - exact[k]) / exact[k]) ** 2 for k in exact])))


def marginals0(joint: dict, names) -> dict:
    return {nm: sum(p for c, p in joint.items() if c[i] == 0) for i, nm in enumerate(names)}


def run_cell(rb, mode, control, level, seed):
    c = compile_rulebook(rb, {}, multi_control=control)
    tqc = transpile_heron(c.circuit, seed=seed, optimization_level=level)
    sim = make_simulator(mode, seed=seed)
    pooled = {}
    for r in range(RUNS):
        sim.set_options(seed_simulator=seed + r)
        for bits, n in sim.run(tqc, shots=SHOTS).result().get_counts().items():
            b = [int(ch) for ch in reversed(bits.replace(" ", ""))]
            combo = decode_bits(c, b)
            pooled[combo] = pooled.get(combo, 0) + n
    tot = sum(pooled.values())
    joint = {k: v / tot for k, v in pooled.items()}
    ops = tqc.count_ops()
    return joint, {"depth": tqc.depth(), "cz": ops.get("cz", 0), "n_qubits_logical": c.n_logical + c.n_ancilla}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("ideal", "heron"), required=True)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    rb = build_rulebook()
    (DATA / "rulebook_borujeni.json").write_text(json.dumps(rb, indent=2) + "\n")
    names = [n["name"] for n in rb["nodes"]]
    exact = joint_table(rb, {})
    print(f"[{sim_label(args.mode)}] {RUNS} runs x {SHOTS} shots; exact marginals P(X=0):",
          {k: round(v, 4) for k, v in marginals0(exact, names).items()})
    results = []
    cells = [(c, 1) for c in ("mcry", "ancilla")] if args.mode == "ideal" else \
        [(c, lv) for lv in range(4) for c in ("mcry", "ancilla")]
    print(f"{'control':<8}{'lvl':>4}{'RMSPE%':>9}{'TVD':>8}{'depth':>7}{'CZ':>5}   marginals P(X=0) IR/OI/SM/SP")
    for control, lv in cells:
        joint, info = run_cell(rb, args.mode, control, lv, args.seed)
        m = marginals0(joint, names)
        row = {"control": control, "level": lv, "rmspe_pct": rmspe(m, marginals0(exact, names)),
               "tvd": tvd(joint, exact), "marginals": m, **info}
        results.append(row)
        print(f"{control:<8}{lv:>4}{row['rmspe_pct']:>9.3f}{row['tvd']:>8.4f}{info['depth']:>7}{info['cz']:>5}   "
              + " ".join(f"{m[k]:.3f}" for k in names))
    out = {"sim_label": sim_label(args.mode), "hardware": None, "netica": NETICA, "results": results}
    if args.mode == "ideal":
        r = results[0]
        ok = all(abs(r["marginals"][k] - NETICA[k]) <= 0.01 for k in NETICA) and r["rmspe_pct"] <= 0.5
        print("paper simulator RMSPE 0.1 % (published); ours", f"{r['rmspe_pct']:.3f} %", "->", "MATCH" if ok else "NO MATCH")
    else:
        print("paper hardware RMSPE (2020 devices): level 0:", PAPER_HW_RANGE[0], "%; level 3:", PAPER_HW_RANGE[3],
              "% -- comparison only (2025 Heron model vs 2020 devices)")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        for control in ("mcry", "ancilla"):
            rs = [r for r in results if r["control"] == control]
            ax.plot([r["level"] for r in rs], [r["rmspe_pct"] for r in rs], "o-", label=control)
        ax.axhspan(4.9, 36.3, color="grey", alpha=0.15, label="paper hw, level 0 (4.9-36.3 %)")
        ax.set_xlabel("transpiler optimization level"); ax.set_ylabel("RMSPE of marginals (%)")
        ax.set_xticks(range(4))
        ax.set_title("Borujeni oil-stock BN, simulated: Heron-class noise (FakeMarrakesh)", fontsize=8)
        ax.legend(fontsize=7); fig.tight_layout()
        fig.savefig(LETTER_DIR / "figures" / "borujeni_rmspe_vs_level.png", dpi=150)
    (LETTER_DIR / "data" / f"borujeni_{args.mode}.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
