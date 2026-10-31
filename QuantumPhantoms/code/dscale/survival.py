"""D-SCALE survive-vs-simulable map (AC-13, AC-14).

    python -m dscale.survival --budget 40|100|120 --target boston|nighthawk|marrakesh|kingston|helios-class
                              [--families ...] [--smoke] [--out DIR]

Sweeps each family's fixed PARAM_GRID (hashed before any run; no look-elsewhere) and classifies every cell:
  dead            the survival metric is not above its threshold by k = 2 sigma
  alive_bp_easy   alive, and BP reaches fidelity >= 0.99 at some chi <= chi_max
  alive_bp_hard   alive, and BP < 0.99 at chi_max, or the chi-gap |O(chi_max) - O(chi_max / 2)| > 0.01
The alive_bp_hard cells are the Goldilocks zone, the only honest meaning of "closer to quantum advantage" here; an
empty zone is a reported result. Entanglement is not hardness: ghz-spine and pmd-bank never enter the frontier column.

Survival metrics: spine F_dfe; QCA echo fidelity (+ negativity where full noise is simulable); PMD the AC-11 rule;
anchor the magnetisation at the Clifford points. Noise: the Pauli-twirled target model (AC-4). Non-Clifford circuits
run as their real circuit under full Pauli noise up to NOISY_REAL_MAX sites (density matrix) and as the Clifford twin
above, labelled `predicted (Clifford twin, Pauli-twirled <target>)`; AC-4's noise_validation.json decides whether
Pauli / twin verdicts above 24 q count as `validated`.
BP references, best first: stabilizer-exact; light-cone-exact statevector (<= 25 q); otherwise chi-convergence only.
chi in {2, 4, 8} at >= 100 q, {2, 4, 8, 16} at <= 40 q; a cell that hits the deadline records `bp: timeout`.
`--smoke` runs the first cells of each family's grid, round-robin across families, until the deadline.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit

from dscale import allocate as A, bp as BPm, budget as B, families as F, lint as L, targets as T
from dscale import witness_scale as WS

OUT_DEFAULT = Path(__file__).resolve().parents[2] / "research_runs" / "_dscale"
NOISY_REAL_MAX = 12          # full-noise simulation of the real non-Clifford circuit (density matrix, 4000 shots)
LIGHTCONE_MAX = 25
BP_THR, GAP_THR = 0.99, 0.01


def chis_for(n: int) -> list[int]:
    return [2, 4, 8, 16] if n <= 40 else [2, 4, 8]


# ---------------------------------------------------------------------------------------------- references
def _coherent(qc: QuantumCircuit) -> QuantumCircuit:
    out = QuantumCircuit(qc.num_qubits)
    idx = {q: k for k, q in enumerate(qc.qubits)}
    for ins in qc.data:
        if ins.operation.name in BPm.SKIP or ins.operation.name.startswith("save"):
            continue
        out.append(ins.operation, [idx[q] for q in ins.qubits])
    return out


def obs_keys(nodes, edges) -> list[str]:
    ks = [f"Z{n}" for n in nodes]
    for a, b in edges:
        a, b = sorted((a, b))
        ks += [f"Z{a}Z{b}", f"X{a}X{b}"]
    return ks


def _pauli_exp(state, n: int, lbl: dict[int, str]) -> float:
    from qiskit.quantum_info import Pauli

    s = ["I"] * n
    for k, p in lbl.items():
        s[n - 1 - k] = p
    return float(np.real(state.expectation_value(Pauli("".join(s)))))


def stabilizer_reference(qc: QuantumCircuit, nodes, edges) -> dict:
    from qiskit.quantum_info import StabilizerState

    st = StabilizerState(_coherent(qc))
    return _observe(lambda lbl: _pauli_exp(st, qc.num_qubits, lbl), nodes, edges)


def _observe(f, nodes, edges) -> dict:
    out = {}
    for n in nodes:
        out[f"Z{n}"] = f({n: "Z"})
    for a, b in edges:
        a, b = sorted((a, b))
        out[f"Z{a}Z{b}"] = f({a: "Z", b: "Z"})
        out[f"X{a}X{b}"] = f({a: "X", b: "X"})
    return out


def light_cone(qc: QuantumCircuit, support: set[int]) -> tuple[set[int], list]:
    """Backward light cone of `support`: the gates needed (in forward order) and the qubits they touch."""
    idx = {q: k for k, q in enumerate(qc.qubits)}
    cone = set(support)
    keep = []
    for ins in reversed(_coherent(qc).data):
        qs = [idx[q] for q in ins.qubits] if ins.qubits[0] in idx else []
        if not qs:
            qs = [qc.find_bit(q).index for q in ins.qubits]
        if cone.intersection(qs):
            cone |= set(qs)
            keep.append((ins.operation, qs))
    return cone, keep[::-1]


def lightcone_reference(qc: QuantumCircuit, nodes, edges, limit: int = LIGHTCONE_MAX) -> dict | None:
    from qiskit.quantum_info import Statevector

    support = set(nodes) | {q for e in edges for q in e}
    cone, gates = light_cone(qc, support)
    if len(cone) > limit:
        return None
    order = sorted(cone)
    m = {q: k for k, q in enumerate(order)}
    sub = QuantumCircuit(len(order))
    for op, qs in gates:
        sub.append(op, [m[q] for q in qs])
    sv = Statevector(sub)
    return _observe(lambda lbl: _pauli_exp(sv, len(order), {m[k]: p for k, p in lbl.items()}), nodes, edges) | \
        {"_cone": len(cone)}


def bp_profile(entry: dict, deadline: B.Deadline, n_sites: int) -> dict:
    qc = entry["qc"]
    edges_all = entry["edges"]
    on, oe = entry["obs_nodes"], entry["obs_edges"]
    g = nx.Graph()
    g.add_nodes_from(range(qc.num_qubits))
    g.add_edges_from(edges_all)
    if entry.get("clifford"):
        ref, kind = stabilizer_reference(qc, on, oe), "stabilizer-exact"
    else:
        ref = lightcone_reference(qc, on, oe)
        kind = f"light-cone-exact ({ref.pop('_cone')} q)" if ref else "chi-convergence"
    rows, prev = [], None
    for chi in chis_for(n_sites):
        if deadline.expired():
            deadline.skip(f"bp chi={chi} {entry['name']}")
            return {"timeout": True, "per_chi": rows, "ref_kind": kind}
        t0 = time.time()
        tn = BPm.simulate(qc, chi, graph=g)
        o = BPm.observables(tn, on, oe)
        row = {"chi": chi, "runtime_s": round(time.time() - t0, 3), "trunc_err": tn.trunc_err}
        if ref:
            row["fidelity"] = BPm.fidelity_vs_sim(o, ref)
        if prev is not None:
            row["chi_gap"] = float(max(abs(o[k] - prev[k]) for k in o))
        rows.append(row)
        prev = o
        if (entry.get("clifford") and row.get("fidelity", 0) >= 1 - 1e-9):
            break                                         # stabilizer state reproduced exactly: stop early
    last = rows[-1]
    fid = [r["fidelity"] for r in rows if "fidelity" in r]
    easy = any(f >= BP_THR for f in fid)
    gap = last.get("chi_gap")
    hard = (bool(fid) and last.get("fidelity", 1) < BP_THR) or (gap is not None and gap > GAP_THR) or \
        (not fid and gap is None)
    return {"chi_max": last["chi"], "fidelity_vs_ref": last.get("fidelity"), "ref_kind": kind,
            "chi_gap": gap, "per_chi": rows, "easy": bool(easy and not (gap is not None and gap > GAP_THR)),
            "hard": bool(hard and not (entry.get("clifford")))}


# ---------------------------------------------------------------------------------------------- cells
def _validated(n: int, label: str, val: dict | None) -> str:
    if n <= 24 and not label.startswith("predicted"):
        return "n/a (<= 24 q)"
    if val is None:
        return "unvalidated (no noise_validation.json)"
    return "validated" if val.get("passed") else "unvalidated (AC-4 failed)"


def ghz_cell(tg, budget, N, args, dl, draw, val) -> dict | None:
    from dscale.families import ghz_spine as G

    pre = G.preset(budget, tg)
    params = pre | {"N": N, "checks": min(pre["checks"], max(1, N // 12))}
    alloc = A.allocate(G.region_request(budget, tg, params), tg)
    L.enforce(G.build(alloc, params, draw), alloc["regions"], G.NAME, tg.graph)
    mode = f"pauli:{tg.name}"
    cell = G.run_cell(alloc, params, draw, mode, tg.name, args.shots, args.repeats, dl)
    if not cell:
        return None
    ent = G.bp_circuits(alloc, params)[0]
    ent["obs_nodes"] = list(range(min(4, ent["qc"].num_qubits)))
    ent["obs_edges"] = ent["edges"][:4]
    bp = bp_profile(ent, dl, N)
    return {"family": G.NAME, "n_qubits": cell["N"], "depth_or_t": cell["depth"], "alpha": None,
            "sim_label": cell["sim_label"], "metric": "F_dfe (GME)", "value": cell["F_dfe"], "sigma": cell["F_sigma"],
            "k": WS.K_HEADLINE, "alive": cell["gme"], "bp": bp, "kept_fraction": cell["kept_fraction"],
            "validated": _validated(cell["N"], cell["sim_label"], val), "hashes": cell["hashes"][:3]}


def qca_cell(tg, budget, sites, t, alpha, args, dl, draw, val) -> dict | None:
    from dscale.families import ch_qca as Q

    params = {"sites": sites, "t_max": t, "t_w": min(t, 3), "alpha": alpha, "rule": "parity"}
    alloc = A.allocate(Q.region_request(budget, tg, params), tg)
    patch = Q.patch_of(alloc, tg)
    sp = Q.spec(patch, params, draw)
    n = len(sp["nodes"])
    twin = n > NOISY_REAL_MAX
    job = Q.job_from_spec(sp, params, twin=twin)
    L.enforce(job, alloc["regions"], Q.NAME, tg.graph if not tg.meta.get("all_to_all") else None)
    mode = f"{'twin' if twin else 'pauli'}:{tg.name}"
    # echo-only job for the map (snapshots + tomography live in the run / seed path)
    echo = [c for c in job if c.metadata["echo"] and c.metadata["t"] == t]
    tomo = [c for c in job if c.metadata["tomo"]] if not twin else []
    if dl.expired():
        dl.skip(f"ch-qca {n} t={t} a={alpha:.3f}")
        return None
    method = "density_matrix" if not twin else None
    ex = F.execute(echo + tomo, mode, tg.name, args.shots, F.sim_seed(draw["seed_hex"], f"DS-qca-map-{n}-{t}"),
                   method=method, deadline=dl)
    an = Q.analyse(echo + tomo, ex["bits"], sp, args.shots, draw["seed_hex"])
    e = an["echo"][0]
    ent = Q.bp_circuits(alloc, params | {"t": t}, tg, draw)[0]
    col = {q: k for k, q in enumerate(sp["nodes"])}
    ent["obs_edges"] = [(col[a], col[b]) for a, b in sp["reg_edges"]]
    ent["obs_nodes"] = sorted({q for ed in ent["obs_edges"] for q in ed})
    bp = bp_profile(ent, dl, n)
    label = ex["sim_label"]
    return {"family": Q.NAME, "n_qubits": n, "depth_or_t": t, "alpha": alpha, "sim_label": label,
            "metric": "echo fidelity", "value": e["F"], "sigma": e["sigma"], "k": WS.K_HEADLINE,
            "alive": e["alive"], "random_band": an["random_band"], "negativity": an["negativity_edges"] or None,
            "bp": bp, "validated": _validated(n, label, val), "hashes": ex["hashes"][:2]}


def pmd_cell(tg, budget, args, dl, draw, val, cache) -> dict | None:
    from dscale.families import pmd_bank as P

    alloc = A.allocate(P.region_request(budget, tg), tg)
    L.enforce(P.build(alloc, {}, draw), alloc["regions"], P.NAME, tg.graph)
    cell = P.run_cell(alloc, {}, draw, f"pauli:{tg.name}", tg.name, args.shots, args.repeats, dl, cache)
    ms = [m for m in cell["machines"] if "gap_over_floor" in m]
    if not ms:
        return None
    best = max(ms, key=lambda m: m["gap_over_floor"])
    return {"family": P.NAME, "n_qubits": sum(len(m["path"]) for m in ms), "depth_or_t": cell["process"]["L"],
            "alpha": None, "sim_label": cell["sim_label"], "metric": "PMD gap / floor (AC-11 rule)",
            "value": best["gap_over_floor"], "sigma": None, "k": 3, "alive": cell["passed_all"],
            "machines": ms, "process": cell["process"],
            "bp": {"chi_max": 2, "fidelity_vs_ref": 1.0, "ref_kind": "structure: 2-qubit blocks on a path (exact)",
                   "chi_gap": 0.0, "easy": True, "hard": False}, "validated": "n/a (<= 24 q per machine)"}


def kim_cell(tg, budget, theta, steps, args, dl, draw, val) -> dict | None:
    from dscale.families import kicked_ising as K

    alloc = A.allocate(K.region_request(budget, tg), tg)
    job = K.build(alloc, {"theta_h": theta, "steps": steps}, draw)
    L.enforce(job, alloc["regions"], K.NAME, tg.graph if not tg.meta.get("all_to_all") else None, claim=False)
    clifford = any(math.isclose(theta, c) for c in K.CLIFFORD_THETAS)
    run = job if clifford else K.clifford_twin(job)
    mode = f"{'pauli' if clifford else 'twin'}:{tg.name}"
    if dl.expired():
        dl.skip(f"kicked-ising theta={theta:.3f} steps={steps}")
        return None
    ex = F.execute(run, mode, tg.name, args.shots, F.sim_seed(draw["seed_hex"], f"DS-kim-{theta:.3f}-{steps}"),
                   deadline=dl)
    ideal = F.execute(run, "ideal", tg.name, args.shots, 1, deadline=dl)
    m_noisy, m_ideal = K.magnetisation(ex["bits"][0]), K.magnetisation(ideal["bits"][0])
    sig = 1 / math.sqrt(args.shots * len(job[0].metadata["layout"]))
    alive = abs(m_ideal) > 0.05 and (m_noisy * np.sign(m_ideal)) > WS.K_HEADLINE * sig
    ent = K.bp_circuits(alloc, {"theta_h": theta, "steps": steps})[0]
    nq = ent["qc"].num_qubits
    ent["obs_edges"] = ent["edges"][:4]
    ent["obs_nodes"] = sorted({q for e in ent["obs_edges"] for q in e})
    bp = bp_profile(ent, dl, nq)
    return {"family": K.NAME, "n_qubits": nq, "depth_or_t": steps, "alpha": theta, "sim_label": ex["sim_label"],
            "metric": "magnetisation (noisy vs exact)", "value": m_noisy, "value_exact": m_ideal, "sigma": sig,
            "k": WS.K_HEADLINE, "alive": bool(alive), "bp": bp, "validated": _validated(nq, ex["sim_label"], val)}


def regime(c: dict) -> str:
    if not c["alive"]:
        return "dead"
    bp = c.get("bp") or {}
    if bp.get("timeout"):
        return "alive_bp_timeout"
    if c["family"] in ("ghz-spine", "pmd-bank"):
        return "alive_bp_easy"                           # entanglement != hardness (plan §4)
    return "alive_bp_hard" if bp.get("hard") else "alive_bp_easy"


# ---------------------------------------------------------------------------------------------- sweep
def cell_plan(budget: int, tg: T.Target, families: list[str]) -> dict[str, list[tuple]]:
    from dscale.families import ch_qca as Q, ghz_spine as G, kicked_ising as K

    plan: dict[str, list[tuple]] = {}
    if "ghz-spine" in families:
        plan["ghz-spine"] = [("ghz", N) for N in F.width_ladder(G.LADDER, G.preset(budget, tg)["N"])]
    if "ch-qca" in families:
        sizes = sorted({s for s in Q.PARAM_GRID["sites"] if s <= budget} | {Q.PRESETS[budget]["sites"]})
        plan["ch-qca"] = [("qca", s, t, a) for s in sizes for t in Q.PARAM_GRID["t"]
                          for a in sorted(Q.PARAM_GRID["alpha"], reverse=True)]
    if "pmd-bank" in families:
        plan["pmd-bank"] = [("pmd",)]
    if "kicked-ising" in families:
        plan["kicked-ising"] = [("kim", th, st) for st in K.PARAM_GRID["steps"] for th in K.PARAM_GRID["theta_h"]]
    return plan


def param_grids(families: list[str]) -> dict:
    return {f: F.get(f).PARAM_GRID for f in families}


def sweep(budget: int, target: str, families: list[str], args, dl: B.Deadline, val: dict | None) -> dict:
    tg = T.get(target)
    draw = F.default_draw()
    plan = cell_plan(budget, tg, families)
    cells, cache = [], {}
    queues = {f: list(v) for f, v in plan.items()}
    rr = 0
    while any(queues.values()):
        fam = [f for f in plan if queues[f]][rr % len([f for f in plan if queues[f]])]
        rr += 1
        spec = queues[fam].pop(0)
        if dl.expired():
            dl.skip(f"{fam} {spec[1:]}")
            continue
        t0 = time.time()
        try:
            if spec[0] == "ghz":
                c = ghz_cell(tg, budget, spec[1], args, dl, draw, val)
            elif spec[0] == "qca":
                c = qca_cell(tg, budget, spec[1], spec[2], spec[3], args, dl, draw, val)
            elif spec[0] == "pmd":
                c = pmd_cell(tg, budget, args, dl, draw, val, cache)
            else:
                c = kim_cell(tg, budget, spec[1], spec[2], args, dl, draw, val)
        except B.DeadlineHit:
            continue
        if c is None:
            continue
        c["regime"] = regime(c)
        c["runtime_s"] = round(time.time() - t0, 1)
        cells.append(c)
        bp = c["bp"]
        a_txt = "" if c["alpha"] is None else f"a={c['alpha']:.3f} "
        print(f"  {c['family']:12s} n={c['n_qubits']:3d} t={c['depth_or_t']} {a_txt}"
              f"{c['metric']}={c['value']:+.4f}"
              + (f" +- {c['sigma']:.4f}" if c.get("sigma") else "")
              + f"  alive={c['alive']}  BP[{bp.get('ref_kind')}] chi={bp.get('chi_max')} "
                f"fid={bp.get('fidelity_vs_ref')} gap={bp.get('chi_gap')}  -> {c['regime']}  ({c['runtime_s']} s)",
              flush=True)
    gz = [i for i, c in enumerate(cells) if c["regime"] == "alive_bp_hard"]
    return {"budget": budget, "target": target, "target_label": tg.label, "families": families,
            "param_grid_sha256": F.grid_sha256(param_grids(families)), "shots": args.shots, "repeats": args.repeats,
            "cells": cells, "goldilocks_zone": gz, "goldilocks_empty": not gz, "truncated": dl.truncated,
            "skipped": dl.skipped, "noisy_real_max": NOISY_REAL_MAX,
            "calibration": tg.calibration}


# ---------------------------------------------------------------------------------------------- figures
COL = {"dead": "#9e9e9e", "alive_bp_easy": "#1f77b4", "alive_bp_hard": "#d62728", "alive_bp_timeout": "#ff7f0e"}
MARK = {"ghz-spine": "o", "ch-qca": "s", "pmd-bank": "^", "kicked-ising": "D"}


def figures(m: dict, out: Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out.mkdir(parents=True, exist_ok=True)
    f1 = out / f"survival_map_{m['budget']}_{m['target']}.png"
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for c in m["cells"]:
        ax.scatter(c["n_qubits"], c["depth_or_t"] + (0.08 * (c["alpha"] or 0)), c=COL[c["regime"]],
                   marker=MARK.get(c["family"], "x"), s=60, edgecolors="k", linewidths=0.4)
    for fam, mk in MARK.items():
        ax.scatter([], [], marker=mk, c="w", edgecolors="k", label=fam)
    for r, cl in COL.items():
        ax.scatter([], [], marker="s", c=cl, label=r)
    ax.set_xlabel("qubits in the cell")
    ax.set_ylabel("depth / cycles t / steps (offset by angle)")
    gz = "EMPTY" if m["goldilocks_empty"] else f"{len(m['goldilocks_zone'])} cell(s)"
    ax.set_title(f"D-SCALE survive-vs-simulable map, budget {m['budget']}, {m['target_label']}\n"
                 f"Goldilocks zone (alive and BP-hard): {gz}; simulated (Pauli-twirled / Clifford-twin predicted)"
                 + ("; truncated" if m["truncated"] else ""), fontsize=8)
    ax.legend(fontsize=7, loc="best", ncol=2)
    fig.tight_layout()
    fig.savefig(f1, dpi=110)
    plt.close(fig)
    f2 = out / "bp_frontier.png"
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for c in m["cells"]:
        rows = (c.get("bp") or {}).get("per_chi") or []
        xs = [r["chi"] for r in rows if "fidelity" in r]
        ys = [r["fidelity"] for r in rows if "fidelity" in r]
        if xs:
            ax.plot(xs, ys, marker=MARK.get(c["family"], "x"), color=COL[c["regime"]], alpha=0.7, lw=0.8)
        gx = [r["chi"] for r in rows if "chi_gap" in r]
        gy = [1 - r["chi_gap"] for r in rows if "chi_gap" in r]
        if gx and not xs:
            ax.plot(gx, gy, ls=":", marker=MARK.get(c["family"], "x"), color=COL[c["regime"]], alpha=0.7)
    ax.axhline(BP_THR, color="k", ls="--", lw=0.8)
    ax.set_xscale("log", base=2)
    ax.set_xlabel("bond dimension chi")
    ax.set_ylabel("BP fidelity vs reference (dotted: 1 - chi-gap)")
    ax.set_title(f"BP frontier, budget {m['budget']}, {m['target']} (simulated; BP = belief-propagation TN)", fontsize=9)
    fig.tight_layout()
    fig.savefig(f2, dpi=110)
    plt.close(fig)
    return [f1, f2]


def load_validation(out: Path) -> dict | None:
    for p in (out / "noise_validation.json", OUT_DEFAULT / "noise_validation.json"):
        if p.exists():
            return json.loads(p.read_text())
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--budget", type=int, default=40, choices=F.BUDGETS)
    ap.add_argument("--target", default="boston", choices=T.NAMES)
    ap.add_argument("--families", nargs="*", default=list(F.FAMILIES))
    ap.add_argument("--out", type=Path, help="output dir (default research_runs/_dscale/survival_<budget>_<target>)")
    B.add_args(ap)
    a = ap.parse_args()
    dl = B.check(a, default_repeats=2 if a.smoke else B.REPEATS)
    out = a.out or OUT_DEFAULT / f"survival_{a.budget}_{a.target}"
    out.mkdir(parents=True, exist_ok=True)
    val = load_validation(out)
    print(f"survival map: budget {a.budget}, target {a.target}, families {a.families}; shots {a.shots} x repeats "
          f"{a.repeats}; cap {a.max_minutes} min; PARAM_GRID sha256 {F.grid_sha256(param_grids(a.families))[:12]}")
    m = sweep(a.budget, a.target, a.families, a, dl, val)
    figs = figures(m, out / "figures")
    (out / "survival_map.json").write_text(json.dumps(m, indent=1, default=str))
    gz = "empty" if m["goldilocks_empty"] else ", ".join(
        f"{m['cells'][i]['family']} n={m['cells'][i]['n_qubits']} t={m['cells'][i]['depth_or_t']}"
        for i in m["goldilocks_zone"])
    print(f"Goldilocks zone (alive and BP-hard): {gz}")
    print("wrote", out / "survival_map.json", *figs, sep="\n  ")
    print(dl.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
