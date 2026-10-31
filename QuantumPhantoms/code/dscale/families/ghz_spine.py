"""D-SCALE family `ghz-spine` (AC-9): a certified clonal genealogy as a Big-Cats GHZ tree with a separable soma.

    python -m dscale.families.ghz_spine --budget 40 --target marrakesh --mode heron --smoke [--N 12] [--trex]
    python -m dscale.families.ghz_spine --budget 120 --mode pauli:boston --smoke

Spine: `bfs_tree(N)` with an H root and one CX per tree edge in BFS order (IBM "Big cats", arXiv 2510.09520);
`--spines k` adds independent subclone trees. Parity checks: ancilla a gets CX(i->a), CX(j->a) on a Z_i Z_j
stabilizer, is measured at the end, and the shot is post-selected on a = 0 (kept fraction recorded).
Soma: qubits with no gate from the spine (separate region behind a buffer). Each gets Ry(theta_fate) from the
tile's draw (illustrative type x margin table below, Q11); soma Z bits give per-cell fates: claim L0, the exact
classical surrogate is a Bernoulli(sin^2(theta/2)) coin.
DD: an X-X pair in every spine idle window in heron mode; inert in the Pauli model (stated).
Circuits per job: 2 ghz2 (all-X, all-Z) + 40 DFE stabilizers + 1 soma Z.
Claim: L1 (GME, DFE F > 1/2 by 2 sigma) only. A GHZ state is a stabilizer state with BP chi = 2: never L2.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit

from dscale import allocate as A, budget as B, families as F, lint as L, targets as T, witness_scale as WS
from imaging.seedhash import rng

NAME = "ghz-spine"
CLAIM = "L1"
WITNESS = "DFE F > 0.5 by 2 sigma (GME, m = 40) + ghz2 = <X^N> + <ZZ> > 1"
HARDNESS = "stabilizer state, BP chi = 2: none (never in the frontier column)"
LADDER = (6, 12, 24, 36, 48, 64, 92, 112)
PRESETS = {40: {"N": 30, "checks": 2, "soma": 8},
           100: {"N": 84, "checks": 8, "soma": 8},
           120: {"N": 112, "checks": 8, "soma": 8}}
NIGHTHAWK_120 = {"N": 108, "checks": 8, "soma": 4}
PARAM_GRID = {"N": list(LADDER), "dd": [True]}
STAND_INS: dict = {}                                     # already Clifford (spine); soma is split off
SPINE_MODES = {"ideal": "stabilizer", "heron": "matrix_product_state", "pauli": "stabilizer", "twin": "stabilizer"}

# Illustrative fate probability P(proliferative) per type x margin (Q11). Ordering only follows the published risk
# factors of the Brock model (McWilliams et al., NEJM 2013: spiculation and part-solid raise risk); the numbers are
# NOT fitted biology. theta_fate = 2 asin(sqrt(p)).
FATE_P = {"solid": {"smooth": 0.20, "lobulated": 0.35, "spiculated": 0.50},
          "part-solid": {"smooth": 0.30, "lobulated": 0.45, "spiculated": 0.60},
          "ground-glass": {"smooth": 0.10, "lobulated": 0.20, "spiculated": 0.30},
          "calcified": {"smooth": 0.02, "lobulated": 0.03, "spiculated": 0.05}}
FATE_SOURCE = ("illustrative type x margin table; ordering after the Brock model risk factors (McWilliams et al., "
               "NEJM 2013); not fitted")


def preset(budget: int, tg: T.Target | None = None) -> dict:
    if budget == 120 and tg is not None and tg.name == "nighthawk":
        return dict(NIGHTHAWK_120)
    return dict(PRESETS[budget])


def preset_text(budget: int) -> str:
    p = PRESETS[budget]
    extra = f"; on Nighthawk {NIGHTHAWK_120['N']} + {NIGHTHAWK_120['checks']} + {NIGHTHAWK_120['soma']}" \
        if budget == 120 else ""
    return f"spine {p['N']} + {p['checks']} checks + {p['soma']} soma{extra}"


def default_draw() -> dict:
    return F.default_draw()


def theta_fate(draw: dict) -> float:
    p = FATE_P.get(draw.get("type", "solid"), FATE_P["solid"]).get(draw.get("margin", "smooth"), 0.2)
    return 2 * math.asin(math.sqrt(p))


# ---------------------------------------------------------------------------------------------- regions
def region_request(budget: int, tg: T.Target, params: dict | None = None) -> list[dict]:
    p = preset(budget, tg) | (params or {})
    reqs = []
    for s in range(int(p.get("spines", 1))):
        name = "spine" if s == 0 else f"spine{s + 1}"
        n = p["N"] if s == 0 else max(6, p["N"] // 4)
        reqs.append({"name": name, "family": NAME, "kind": "bfs_tree", "n": n, "role": "certified",
                     "checks": p["checks"] if s == 0 else max(1, p["checks"] // 4), "min_n": 4})
    reqs.append({"name": "soma", "family": NAME, "kind": "free", "n": p["soma"], "role": "soma", "min_n": 1})
    return reqs


def _trees(alloc: dict) -> list[dict]:
    out = []
    for name, r in alloc["regions"].items():
        if r["role"] == "certified" and r["family"] == NAME:
            chk = alloc["regions"].get(name + "_checks", {"checks": []}).get("checks", [])
            out.append({"name": name, "nodes": r["qubits"], "edges": r["edges"], "root": r["root"],
                        "depth": r.get("depth"), "checks": chk})
    return out


# ---------------------------------------------------------------------------------------------- circuits
def build(alloc: dict, params: dict, draw: dict) -> list[QuantumCircuit]:
    trees = _trees(alloc)
    soma = alloc["regions"].get("soma", {"qubits": []})["qubits"]          # the composite has no soma region
    layout = [q for t in trees for q in t["nodes"]] + [c["ancilla"] for t in trees for c in t["checks"]] + list(soma)
    col = {q: k for k, q in enumerate(layout)}
    th = theta_fate(draw)
    g = rng(draw["seed_hex"], "DS-spine-dfe")
    m = int(params.get("m", WS.M_DFE))
    dfe = [{t["name"]: WS.ghz_stabilizers(len(t["nodes"]), 1, g)[0] for t in trees} for _ in range(m)]

    def prep(name: str, basis_of: dict[int, str], basis: str) -> QuantumCircuit:
        qc = QuantumCircuit(len(layout), len(layout), name=name)
        for t in trees:
            qc.h(col[t["root"]])
            for p_, c_ in sorted(t["edges"], key=lambda e: t["nodes"].index(e[1])):    # BFS order
                qc.cx(col[p_], col[c_])
            for c in t["checks"]:
                a = col[c["ancilla"]]
                qc.cx(col[c["pair"][0]], a)
                qc.cx(col[c["pair"][1]], a)
        for q in soma:
            qc.ry(th, col[q])
        for q, b in basis_of.items():
            if b == "X":
                qc.h(col[q])
            elif b == "Y":
                qc.sdg(col[q])
                qc.h(col[q])
        for k in range(len(layout)):
            qc.measure(k, k)
        qc.metadata = {"layout": layout, "basis": basis, "root": trees[0]["root"], "family": NAME,
                       "dd_qubits": [q for t in trees for q in t["nodes"]]}
        return qc

    spine_q = [q for t in trees for q in t["nodes"]]
    job = [prep("ghz2_X", {q: "X" for q in spine_q}, "X"), prep("ghz2_Z", {}, "Z")]
    for k, st in enumerate(dfe):
        bo = {}
        for t in trees:
            for q, pch in zip(t["nodes"], st[t["name"]]["paulis"]):
                if pch in "XY":
                    bo[q] = pch
        c = prep(f"dfe_{k:02d}", bo, "dfe")
        c.metadata["stabilizers"] = st
        job.append(c)
    job.append(prep("soma_Z", {}, "Z"))
    return job


def clifford_twin(circuits: list[QuantumCircuit]) -> list[QuantumCircuit]:
    return list(circuits)                                 # the spine is Clifford; the soma is split off


def bp_circuits(alloc: dict, params: dict) -> list[dict]:
    out = []
    for t in _trees(alloc):
        col = {q: k for k, q in enumerate(t["nodes"])}
        qc = QuantumCircuit(len(t["nodes"]))
        qc.h(col[t["root"]])
        for p_, c_ in sorted(t["edges"], key=lambda e: t["nodes"].index(e[1])):
            qc.cx(col[p_], col[c_])
        out.append({"name": f"ghz-spine:{t['name']}:N{len(t['nodes'])}", "qc": qc, "clifford": True,
                    "edges": [(col[a], col[b]) for a, b in t["edges"]]})
    return out


# ---------------------------------------------------------------------------------------------- run + witness
def _split(job: list[QuantumCircuit], alloc: dict):
    spine_keep = [q for t in _trees(alloc) for q in t["nodes"] + [c["ancilla"] for c in t["checks"]]]
    soma = alloc["regions"].get("soma", {"qubits": []})["qubits"]
    return [F.restrict(qc, spine_keep) for qc in job[:-1]], (F.restrict(job[-1], soma, "soma_Z") if soma else None)


def run_job(alloc: dict, params: dict, draw: dict, mode: str, target: str, shots: int, seed: int,
            trex: bool = False, deadline: B.Deadline | None = None) -> dict:
    job = build(alloc, params, draw)
    spine_job, soma_c = _split(job, alloc)
    kind = mode.partition(":")[0]
    ex = F.execute(spine_job, mode, target, shots, seed, method=SPINE_MODES[kind], deadline=deadline)
    so = F.execute([soma_c], "ideal" if kind in ("pauli", "twin") else mode, target, shots, seed + 1,
                   method="statevector" if kind != "heron" else "automatic") if soma_c is not None else \
        {"bits": [np.zeros((0, 0), np.uint8)], "hashes": [], "isa": []}
    tg = T.get(F.mode_target(mode, target))
    trees = _trees(alloc)
    lay = spine_job[0].metadata["layout"]
    col = {q: k for k, q in enumerate(lay)}
    anc = [col[c["ancilla"]] for t in trees for c in t["checks"]]
    keep = [(b[:, anc].sum(1) == 0) if anc else np.ones(len(b), bool) for b in ex["bits"]]
    kept_fraction = float(np.mean([k.mean() for k in keep]))
    t0 = trees[0]
    cols0 = [col[q] for q in t0["nodes"]]
    edges0 = [(col[a], col[b]) for a, b in t0["edges"]]
    xb, zb = ex["bits"][0][keep[0]], ex["bits"][1][keep[1]]
    g2 = WS.ghz2(xb, zb, cols0, edges0)
    vals = []
    for c, bits, kp in zip(spine_job[2:], ex["bits"][2:], keep[2:]):
        st = c.metadata["stabilizers"][t0["name"]]
        v, se = WS.stabilizer_value(bits[kp], st, cols0)
        if trex:
            used = [q for q, pch in zip(t0["nodes"], st["paulis"]) if pch != "I"]
            v, se = WS.trex_lite(v, se, used, tg.p01, tg.p10)
        vals.append(v)
    if trex:
        xs, _ = WS.trex_lite(g2["X"], 0.0, t0["nodes"], tg.p01, tg.p10)
        g2 = g2 | {"X_trex": xs}
    dfe = WS.dfe_ghz(vals)
    soma_bits = so["bits"][0]
    th = theta_fate(draw)
    return {"N": len(t0["nodes"]), "depth": t0["depth"], "n_checks": len(t0["checks"]),
            "kept_fraction": kept_fraction, "F_dfe": dfe["F"], "F_sigma_dfe": dfe["sigma"], "ghz2": g2["value"],
            "ghz2_sigma": g2["sigma"], "ghz2_X": g2["X"], "ghz2_ZZ": g2["ZZ"], "trex": trex,
            "isa_depth": int(max(c.depth() for c in ex["isa"][:2])) if ex["isa"] else None,
            "isa_2q": int(ex["isa"][0].count_ops().get("cz", 0)) if ex["isa"] else None,
            "soma": {"theta_fate": th, "p_fate": math.sin(th / 2) ** 2,
                     "fates": soma_bits.mean(0).round(4).tolist() if soma_bits.size else [], "claim_level": "L0",
                     "classical_surrogate": "Bernoulli(sin^2(theta/2)) coin per soma cell", "source": FATE_SOURCE},
            "hashes": ex["hashes"] + so["hashes"], "sim_label": ex["sim_label"], "isa": ex["isa"] + so["isa"]}


def run_cell(alloc: dict, params: dict, draw: dict, mode: str, target: str, shots: int, repeats: int,
             deadline: B.Deadline, trex: bool = False) -> dict:
    """repeats x job; F_dfe value = mean over repeats, sigma = sqrt(repeat spread^2 + 1/shots + DFE sigma^2)."""
    from imaging.seedhash import derive_seed

    reps = []
    for r in range(repeats):
        if deadline.expired():
            deadline.skip(f"{NAME} N={params.get('N')} repeat {r + 1}/{repeats}")
            break
        try:
            reps.append(run_job(alloc, params, draw, mode, target, shots,
                                derive_seed(draw["seed_hex"], f"DS-spine-sim-{r}") % 2 ** 31, trex, deadline))
        except B.DeadlineHit:
            break
    if not reps:
        return {}
    last = reps[-1]
    sig_dfe = float(np.sqrt(np.mean([x["F_sigma_dfe"] ** 2 for x in reps]) / len(reps)))
    al = WS.alive([x["F_dfe"] for x in reps], shots, threshold=0.5, sigma_extra=sig_dfe)
    g2 = WS.alive([x["ghz2"] for x in reps], shots, threshold=1.0,
                  sigma_extra=float(np.mean([x["ghz2_sigma"] for x in reps])))
    out = {k: last[k] for k in ("N", "depth", "n_checks", "isa_depth", "isa_2q", "soma", "hashes", "sim_label",
                                "trex")}
    out |= {"kept_fraction": float(np.mean([x["kept_fraction"] for x in reps])), "F_dfe": al["value"],
            "F_sigma": al["sigma"], "gme": al["alive"], "gme_k3": al["alive_k3"], "ghz2": g2["value"],
            "ghz2_sigma": g2["sigma"], "ghz2_alive": g2["alive"], "repeats": len(reps), "_isa": last["isa"]}
    return out


def claim(cell: dict) -> dict:
    return {"family": NAME, "claim_level": CLAIM if cell.get("gme") else "L0", "witness": "DFE GHZ fidelity (GME)",
            "value": cell.get("F_dfe"), "sigma": cell.get("F_sigma"), "k": WS.K_HEADLINE,
            "passed": bool(cell.get("gme")), "label": cell.get("sim_label"),
            "note": f"N={cell.get('N')}, kept {cell.get('kept_fraction', 0):.3f}; ghz2={cell.get('ghz2', 0):.3f}; "
                    f"stabilizer state (BP chi = 2): survives, not hard"}


# ---------------------------------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--budget", type=int, default=40, choices=F.BUDGETS)
    ap.add_argument("--target", default="marrakesh", choices=T.NAMES)
    ap.add_argument("--mode", default="ideal", help="ideal | heron | pauli:<target>")
    ap.add_argument("--N", type=int, nargs="*", help="widths (default: ladder capped by the preset)")
    ap.add_argument("--spines", type=int, default=1)
    ap.add_argument("--trex", action="store_true", help="TREX-lite readout correction on the parities")
    ap.add_argument("--out", type=Path, help="write ghz_spine.json here")
    B.add_args(ap)
    a = ap.parse_args()
    dl = B.check(a, default_repeats=3 if a.smoke else B.REPEATS)
    tname = F.mode_target(a.mode, a.target)
    tg = T.get(tname)
    pre = preset(a.budget, tg)
    widths = a.N or F.width_ladder(LADDER, pre["N"])
    draw = default_draw()
    print(f"ghz-spine budget {a.budget} on {tg.label}, mode {a.mode} ({T.sim_label(a.mode)}); "
          f"shots {a.shots} x repeats {a.repeats}; widths {widths}")
    rows = []
    for N in widths:
        if dl.expired():
            dl.skip(f"N={N}")
            continue
        params = pre | {"N": N, "checks": min(pre["checks"], max(1, N // 12)), "spines": a.spines}
        alloc = A.allocate(region_request(a.budget, tg, params), tg)
        job = build(alloc, params, draw)
        try:
            L.enforce(job, alloc["regions"], NAME, tg.graph)
        except L.LintError as e:
            print("lint:", e)
            return L.EXIT_LINT
        cell = run_cell(alloc, params, draw, a.mode, tname, a.shots, a.repeats, dl, a.trex)
        if not cell:
            continue
        cell.pop("_isa")
        rows.append(cell)
        print(f"  N={cell['N']:3d} depth={cell['depth']} checks={cell['n_checks']} ISA depth={cell['isa_depth']} "
              f"kept={cell['kept_fraction']:.3f}  F_dfe={cell['F_dfe']:.4f} +- {cell['F_sigma']:.4f}  "
              f"GME(k=2)={cell['gme']} (k=3 {cell['gme_k3']})  ghz2={cell['ghz2']:.3f} +- {cell['ghz2_sigma']:.3f}"
              f"  repeats={cell['repeats']}", flush=True)
    print(dl.report())
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "ghz_spine.json").write_text(json.dumps({"rows": rows, "truncated": dl.truncated,
                                                          "skipped": dl.skipped}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
