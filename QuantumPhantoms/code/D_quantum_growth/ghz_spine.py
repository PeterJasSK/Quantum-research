"""D-SCALE family `ghz-spine` (AC-9): a certified clonal genealogy as a Big-Cats GHZ tree with a separable soma.


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

import math

from qiskit import QuantumCircuit

from common import witness as WS
from common.runio import rng

NAME = "ghz-spine"
CLAIM = "L1"

# Illustrative fate probability P(proliferative) per type x margin (Q11). Ordering only follows the published risk
# factors of the Brock model (McWilliams et al., NEJM 2013: spiculation and part-solid raise risk); the numbers are
# NOT fitted biology. theta_fate = 2 asin(sqrt(p)).
FATE_P = {"solid": {"smooth": 0.20, "lobulated": 0.35, "spiculated": 0.50},
          "part-solid": {"smooth": 0.30, "lobulated": 0.45, "spiculated": 0.60},
          "ground-glass": {"smooth": 0.10, "lobulated": 0.20, "spiculated": 0.30},
          "calcified": {"smooth": 0.02, "lobulated": 0.03, "spiculated": 0.05}}


def theta_fate(draw: dict) -> float:
    p = FATE_P.get(draw.get("type", "solid"), FATE_P["solid"]).get(draw.get("margin", "smooth"), 0.2)
    return 2 * math.asin(math.sqrt(p))


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


def claim(cell: dict) -> dict:
    return {"family": NAME, "claim_level": CLAIM if cell.get("gme") else "L0", "witness": "DFE GHZ fidelity (GME)",
            "value": cell.get("F_dfe"), "sigma": cell.get("F_sigma"), "k": WS.K_HEADLINE,
            "passed": bool(cell.get("gme")), "label": cell.get("sim_label"),
            "note": f"N={cell.get('N')}, kept {cell.get('kept_fraction', 0):.3f}; ghz2={cell.get('ghz2', 0):.3f}; "
                    f"stabilizer state (BP chi = 2): survives, not hard"}


