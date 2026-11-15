"""Hardware numbers ledger for the paper "Certified, Not Superior".

Reads every hardware run file the paper cites and writes one JSON with the numbers, their uncertainty and the
source path, so no number in the paper is typed by hand. Nothing here submits a job.

    /home/peter/anaconda3/bin/python3 THESIS/QuantumEvolutionFrontier/analysis/ledger.py
"""
from __future__ import annotations

import glob
import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "THESIS/QuantumEvolutionFrontier/runs/ledger.json"
QT = REPO / "QuantumLife/research_runs/BackLog"
AL = REPO / "artificial-life/research_runs"
REC = REPO / "THESIS/QuantumEvolutionFrontier/data/recovered"
QP = REPO / "QuantumPhantoms/research_runs/dscale_live_100_20261031-170957"


def rel(p) -> str:
    return str(Path(p).resolve().relative_to(REPO))


def mean_se(x) -> dict:
    x = np.asarray(x, float)
    n = len(x)
    return {"mean": float(x.mean()), "se": float(x.std(ddof=1) / math.sqrt(n)) if n > 1 else None, "n": n}


# ---------------------------------------------------------------- QuantumTree C(d) arms
def qtree_arm(summary: Path) -> dict:
    s = json.loads(summary.read_text())
    m = s["meta"]
    c1, c2, xi, div, depth = [], [], [], [], []
    for rf in m["run_files"]:
        r = json.loads((summary.parent / rf).read_text())
        for g in r["generations"]:
            C = g["correlation"]["C"]
            c = [v / C[0] for v in C]
            c1.append(c[1]); c2.append(c[2]); xi.append(sum(c[1:]))
            div.append(g["diversity"]); depth.append(g["logical_depth"])
    return {"source": rel(summary), "backend": m["backend"], "sim": m["sim"], "layers": m.get("layers"),
            "entangler": m.get("entangler", "serial"), "repeats": m["repeats"], "generations": m["generations"],
            "shots": m["shots"], "c1": mean_se(c1), "c2": mean_se(c2), "xi": mean_se(xi),
            "diversity": mean_se(div), "logical_depth_mean": float(np.mean(depth))}


def z(a: dict, b: dict) -> float:
    return (a["mean"] - b["mean"]) / math.sqrt(a["se"] ** 2 + b["se"] ** 2)


def quantum_tree() -> dict:
    arms = {}
    for tag in ["A_base_sim", "B0_ctrl_ibm_kingston", "B_hw_ibm_kingston", "C_L0_ibm_kingston", "C_L1_ibm_kingston",
                "C_L2_ibm_kingston", "C_L4_ibm_kingston"]:
        f = sorted(QT.glob(f"{tag}_2026*_summary.json"))[-1]
        arms[tag] = qtree_arm(f)
    for f in sorted(QT.glob("bw_C_L2L_ibm_kingston_2026*_summary.json")):
        a = qtree_arm(f)
        arms[f"bw_L{a['layers']}_ibm_kingston"] = a
    out = {"arms": arms}
    out["z_c1_B_vs_sim"] = z(arms["B_hw_ibm_kingston"]["c1"], arms["A_base_sim"]["c1"])
    out["z_c1_B_vs_B0"] = z(arms["B_hw_ibm_kingston"]["c1"], arms["B0_ctrl_ibm_kingston"]["c1"])
    out["z_c1_bwL2_vs_bwL0"] = z(arms["bw_L2_ibm_kingston"]["c1"], arms["bw_L0_ibm_kingston"]["c1"])
    return out


# ---------------------------------------------------------------- teleport vs SWAP long-range bond
def bond_arm(files: list[str]) -> dict:
    vals, signs, depth, herald, meta = [], [], [], [], None
    for f in files:
        r = json.loads(Path(f).read_text())
        meta = r["meta"]
        for g in r["generations"]:
            b = g["bonds"][0]
            vals.append(b["c_at_d"]); depth.append(g["logical_depth"])
            if "herald_frac" in g:
                herald.append(g["herald_frac"])
        dq = r["generations"][0]["bonds"][0]["d_qubits"]
    v = np.array(vals)
    return {"sources": [rel(f) for f in files], "backend": meta["backend"], "sim": meta["sim"],
            "long_range": meta.get("long_range"), "herald": meta.get("herald"), "d_qubits": dq,
            "n_qubits": meta.get("n_qubits"), "shots": meta["shots"], "c_bond": mean_se(v),
            "frac_negative": float((v < 0).mean()), "logical_depth_mean": float(np.mean(depth)),
            "herald_frac_mean": float(np.mean(herald)) if herald else None}


def teleport() -> dict:
    groups = {}
    for f in sorted(QT.glob("*_run.json")):
        n = f.name
        if not any(n.startswith(p) for p in ("tel_", "swap_")):
            continue
        r = json.loads(f.read_text())
        if not r["generations"] or "bonds" not in r["generations"][0]:
            continue
        key = n.split("_seed")[0].split("_2026")[0]
        dq = r["generations"][0]["bonds"][0]["d_qubits"]
        groups.setdefault(f"{key}_d{dq}", []).append(str(f))
    return {k: bond_arm(v) for k, v in sorted(groups.items())}


# ---------------------------------------------------------------- QALife genealogy witness sweeps
def qalife_file(f: Path) -> list[dict]:
    d = json.loads(f.read_text())
    m = d["meta"]
    rows = []
    for w, v in d["by_width"].items():
        sig, s = v["entanglement_signal"], v["witness_joint_sigma"]
        rows.append({"source": rel(f), "backend": m["backend"], "stage": m.get("stage"), "model": m.get("model"),
                     "death": m.get("death", m.get("soma_death")), "phenotype": m.get("phenotype"),
                     "steps": m["steps"], "mut_scale": m["mut_scale"], "repeats": m["repeats"], "shots": m["shots"],
                     "W": int(w), "signal": sig, "sigma": s, "k_sigma": sig / s if s else None,
                     "separable_null": v["separable_mean"], "survives_k2": v["survives"],
                     "survives_k3": bool(s and sig > 3 * s)})
    return rows


def qalife() -> dict:
    month4 = [r for f in sorted(REC.glob("qalife_m4p2_*kingston*.json")) for r in qalife_file(f)]
    p2 = [r for f in sorted((AL / "originalP2").glob("*.json")) for r in qalife_file(f)]
    pj0 = [r for f in sorted((AL / "pj").glob("*LIVE*.json")) for r in qalife_file(f)]
    return {"month4_unitary": sorted(month4, key=lambda r: r["W"]), "p2": p2,
            "pj0": sorted(pj0, key=lambda r: (r["phenotype"] or "", r["death"] or "", r["W"]))}


def motile() -> dict:
    f = AL / "pj2_motile/pj2_line_org2L4_ibm_marrakesh_20260927-180920.json"
    d = json.loads(f.read_text())
    frames = d["scenarios"]["motile"]["isolated"]
    rows = [{"gen": fr["gen"], "w": fr["w"], "w_sigma": fr["w_sigma"], "zz": fr.get("zz"),
             "w_plus_zz": fr["w"] + fr["zz"] if fr.get("zz") is not None else None, "certified": fr["certified"],
             "alive": fr["alive"], "born": fr["born"]} for fr in frames]
    return {"source": rel(f), "backend": d["meta"]["backend"], "shots": d["meta"]["shots"], "frames": rows}


# ---------------------------------------------------------------- QuantumPhantoms live run
def phantoms() -> dict:
    q = json.loads((QP / "quantum_run.json").read_text())
    S, n = q["chsh_value"], 2048                      # dscale/live.py CHSH_SHOTS = 2048 per setting
    # sigma_S under equal |E| = S/4 per setting (binomial correlator variance (1 - E^2)/n, four settings)
    e = S / 4
    sigma_s = math.sqrt(4 * (1 - e * e) / n)
    det = json.loads((QP / "dscale/scale_detail.json").read_text())
    run = json.loads((QP / "dscale/dscale_run.json").read_text())
    tiles = json.loads((QP / "tiles.json").read_text())["tiles"]
    tdiag = [{"tile": t["tile_id"], "type": t["type"], "size_mm": t["size_mm"], "lobe": t["lobe"],
              "margin": t["margin"], "renderer": t.get("renderer"), "seed_source": t.get("seed_source"),
              **{k: t["diag"].get(k) for k in ("diameter_baseline_mm", "vdt_d", "seed_cells", "hu_core",
                                               "volume_pd_pct", "sigma_ratio_in_out", "sigma_edge_mm")}}
             for t in tiles]
    return {"source": rel(QP), "roll_job": q["job_id"], "chsh": {"S": S, "shots_per_setting": n,
            "sigma_S_equal_E": sigma_s, "z_above_2": (S - 2) / sigma_s},
            "dscale_job": run["job_id"], "claims": run["claims"], "ghz_spine": det["ghz_spine"],
            "ch_qca": {k: det["ch_qca"][k] for k in ("sites", "t_w", "negativity_edges", "echo")},
            "pmd_bank": det.get("pmd_bank"), "usage_s": det.get("usage_s"), "tiles": tdiag}


def separable_check() -> dict:
    """Exact: the classical mixture 1/2(|+...+><+...+| + |-...-><-...-|) against the one-basis PJ0 test."""
    out = []
    for n in (2, 4, 24, 50):
        joint = 0.5 * (1 + (-1) ** n)                 # <X^n> on |+>^n is 1, on |->^n is (-1)^n
        marg = 0.5 * (1 + -1)                         # each <X_i> averages +1 and -1
        out.append({"n": n, "joint_X": joint, "prod_marginals": marg ** n if n else 1.0, "signal": joint - marg ** n})
    return {"state": "1/2(|+>^n<+|^n + |->^n<-|^n), fully separable", "rows": out}


def main() -> None:
    led = {"quantum_tree": quantum_tree(), "teleport": teleport(), "qalife": qalife(), "motile": motile(),
           "phantoms": phantoms(), "separable_check": separable_check()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(led, indent=1))
    qt = led["quantum_tree"]
    print("QuantumTree c(1):", {k: round(v["c1"]["mean"], 4) for k, v in qt["arms"].items()})
    print("  z B vs sim %.1f, B vs B0 %.1f, brick L2 vs L0 %.1f" % (qt["z_c1_B_vs_sim"], qt["z_c1_B_vs_B0"],
                                                                     qt["z_c1_bwL2_vs_bwL0"]))
    for k, v in led["teleport"].items():
        print(f"  bond {k:38s} d={v['d_qubits']:3d} c={v['c_bond']['mean']:+.4f}±{v['c_bond']['se'] or 0:.4f} "
              f"n={v['c_bond']['n']} neg={v['frac_negative']:.2f} depth={v['logical_depth_mean']:.0f}")
    for r in led["qalife"]["month4_unitary"]:
        print(f"  M4 W={r['W']:3d} signal {r['signal']:.4f} ± {r['sigma']:.4f}  k={r['k_sigma']:.1f}")
    for r in led["qalife"]["pj0"]:
        print(f"  PJ0 {r['death']}/{r['phenotype']} W={r['W']:3d} steps={r['steps']} {r['signal']:.4f} k={r['k_sigma']:.1f}")
    print("CHSH", led["phantoms"]["chsh"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
