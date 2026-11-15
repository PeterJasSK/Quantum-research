"""D-SCALE family `ch-qca` (AC-10): single-control Goldilocks QCA, native on heavy-hex and on the square lattice.


Rule: for every neighbour k of an updated site j apply CV(k -> j), V = H. Since H^2 = 1 this fires H iff the number of
active neighbours is odd:
  * degree-2 sites: exactly Jones' T6 ("H iff exactly one neighbour active", D14 Fig. 1c, two CH per site);
  * degree-3/4 sites: the **parity-Goldilocks rule** (activate iff an odd number of neighbours is active), a named new
    rule (Q7). It needs no multi-control gate, so RE D-3's C^3-H (376 routing SWAPs) is gone.
  `--rule v3` (V^3 = 1, V = exp(-i 2pi/3 n.sigma), n = (1,1,1)/sqrt3) is simulation-only.
Structure: bipartite Floquet (sublattice A, then B); within a half-step the CV gates run in edge-colour layers (3 colours
on heavy-hex, 4 on the square lattice); CH = Ry(pi/4) CZ Ry(-pi/4) on the target.
Dial: V(alpha) = e^{i alpha} exp(-i alpha n.sigma), n = (x+z)/sqrt2, so V(pi/2) = H; CV(alpha) = Ry(pi/4) CP(2 alpha)
Ry(-pi/4) (1 CZ at alpha = pi/2, 2 CZ otherwise). Clifford twin: CY with the same CZ skeleton (alpha = pi/2), or
CZ |barrier| CY (2 CZ) otherwise.
Initial condition: centre + k extra sites, k = clip(round(size_mm / 4), 0, 6), positions from
rng(tile geometry seed, "DS-qca-init") (Q11).
Circuits per job: Z snapshots t = 0..t_max; 9 bipartite settings at t_w <= 3 on pre-registered edges; echoes U^t U^-t.
Claim: L1 by Bonferroni negativity (noisy simulation <= 24 sites; hardware above). Non-Clifford: the frontier family.
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate

from common import targets as T
from D_quantum_growth import seedlift as SL
from common import witness as WS
from common.runio import rng

NAME = "ch-qca"
CLAIM = "L1"
BASES = ("X", "Y", "Z")
N_REG_EDGES = 4
MAX_EXTRA = 6


def patch_of(alloc: dict, tg: T.Target) -> dict:
    r = alloc["regions"]["qca"]
    h = tg.graph.subgraph(r["qubits"]).copy()
    h.remove_edges_from([e for e in list(h.edges) if list(sorted(e)) not in [sorted(x) for x in r["edges"]]])
    coords = (SL.square_coords(r["qubits"]) if tg.name == "nighthawk"
              else SL.square_coords(r["qubits"], 14) if tg.meta.get("all_to_all") else None)
    return SL.patch_dict(h, coords, kind=f"{tg.name}:{len(r['qubits'])}")


# ---------------------------------------------------------------------------------------------- spec + circuits
def colour_layers(h: nx.Graph) -> list[list[tuple[int, int]]]:
    """Proper edge colouring of the bipartite patch (Konig: max-degree colours), greedy by sorted edges."""
    col: dict[tuple[int, int], int] = {}
    used: dict[int, set[int]] = {n: set() for n in h.nodes}
    for e in sorted(tuple(sorted(x)) for x in h.edges):
        c = 0
        while c in used[e[0]] or c in used[e[1]]:
            c += 1
        col[e] = c
        used[e[0]].add(c)
        used[e[1]].add(c)
    k = max(col.values(), default=-1) + 1
    return [[e for e, c in col.items() if c == i] for i in range(k)]


def initial_sites(patch: dict, draw: dict) -> list[int]:
    k = int(np.clip(round(float(draw.get("size_mm", 0)) / 4), 0, MAX_EXTRA))
    others = [n for n in patch["nodes"] if n != patch["centre"]]
    g = rng(draw["seed_hex"], "DS-qca-init")
    extra = sorted(int(x) for x in g.choice(others, size=min(k, len(others)), replace=False)) if k else []
    return sorted({patch["centre"], *extra})


def registered_edges(patch: dict) -> list[tuple[int, int]]:
    """Pre-registered (before any run): the patch edges at the centre, then the next shell, sorted, up to 4."""
    h, c = patch["graph"], patch["centre"]
    dist = nx.single_source_shortest_path_length(h, c)
    es = sorted((tuple(sorted(e)) for e in h.edges), key=lambda e: (min(dist[e[0]], dist[e[1]]), e))
    return es[:N_REG_EDGES]


def spec(patch: dict, params: dict, draw: dict) -> dict:
    return {"nodes": patch["nodes"], "A": patch["A"], "B": patch["B"], "centre": patch["centre"],
            "edges": [list(e) for e in sorted(tuple(sorted(x)) for x in patch["graph"].edges)],
            "init": initial_sites(patch, draw), "alpha": float(params.get("alpha", math.pi / 2)),
            "rule": params.get("rule", "parity"), "reg_edges": [list(e) for e in registered_edges(patch)]}


def _v3() -> np.ndarray:
    n = np.array([1, 1, 1]) / math.sqrt(3)
    sig = n[0] * np.array([[0, 1], [1, 0]]) + n[1] * np.array([[0, -1j], [1j, 0]]) + n[2] * np.diag([1, -1])
    th = 2 * math.pi / 3
    return math.cos(th) * np.eye(2) - 1j * math.sin(th) * sig


def _cv(qc: QuantumCircuit, c: int, t: int, sp: dict, twin: bool, inverse: bool = False) -> None:
    a = sp["alpha"]
    if sp["rule"] == "v3":
        U = _v3()
        cu = UnitaryGate(U.conj().T if inverse else U).control(1)
        qc.append(cu, [c, t])
        return
    if twin:                                             # Clifford stand-in, same CZ skeleton
        if not math.isclose(a, math.pi / 2):
            qc.cz(c, t)
            qc.barrier(c, t)
        qc.cy(c, t)                                      # self-inverse
        return
    sgn = -1 if inverse else 1
    qc.ry(-math.pi / 4, t)
    if math.isclose(a, math.pi / 2):
        qc.cz(c, t)                                      # CH = Ry(pi/4) CZ Ry(-pi/4)
    else:
        qc.cp(sgn * 2 * a, c, t)
    qc.ry(math.pi / 4, t)


def _half(qc, col, sp, layers, updated: set[int], twin: bool, inverse: bool = False) -> None:
    seq = layers if not inverse else layers[::-1]
    for layer in seq:
        for i, j in (layer if not inverse else layer[::-1]):
            tgt, ctl = (j, i) if j in updated else (i, j)
            _cv(qc, col[ctl], col[tgt], sp, twin, inverse)


def _evolve(qc, col, sp, t: int, twin: bool, inverse: bool = False) -> None:
    h = nx.Graph()
    h.add_edges_from(tuple(e) for e in sp["edges"])
    layers = colour_layers(h)
    A_, B_ = set(sp["A"]), set(sp["B"])
    first = A_ if sp["centre"] in A_ else B_                       # sublattice holding the centre flip first
    second = B_ if first is A_ else A_
    for _ in range(t):
        if not inverse:
            _half(qc, col, sp, layers, second, twin)               # neighbours of the flip update first
            _half(qc, col, sp, layers, first, twin)
        else:
            _half(qc, col, sp, layers, first, twin, True)
            _half(qc, col, sp, layers, second, twin, True)


def circuit(sp: dict, t: int, basis: str | tuple[str, str] = "Z", echo: bool = False, twin: bool = False,
            measure: bool = True) -> QuantumCircuit:
    nodes = sp["nodes"]
    col = {q: k for k, q in enumerate(nodes)}
    qc = QuantumCircuit(len(nodes), len(nodes) if measure else 0,
                        name=f"qca_{'echo' if echo else 'snap'}_t{t}_{basis if isinstance(basis, str) else ''.join(basis)}")
    for q in sp["init"]:
        qc.x(col[q])
    _evolve(qc, col, sp, t, twin)
    if echo:
        qc.barrier()                                     # keeps the transpiler from cancelling U^t U^-t
        _evolve(qc, col, sp, t, twin, inverse=True)
    if measure:
        if not isinstance(basis, str):
            bA, bB = basis
            for q in nodes:
                b = bA if q in sp["A"] else bB
                if b == "X":
                    qc.h(col[q])
                elif b == "Y":
                    qc.sdg(col[q])
                    qc.h(col[q])
        for k in range(len(nodes)):
            qc.measure(k, k)
    qc.metadata = {"layout": list(nodes), "family": NAME, "root": None, "qca": sp, "t": t, "echo": echo,
                   "twin": twin, "basis": basis if isinstance(basis, str) else "tomo:" + "".join(basis),
                   "tomo": None if isinstance(basis, str) else list(basis)}
    return qc


# ---------------------------------------------------------------------------------------------- witness
def analyse(job: list[QuantumCircuit], bits: list[np.ndarray], sp: dict, shots: int, seed_hex: str) -> dict:
    col = {q: k for k, q in enumerate(sp["nodes"])}
    init = np.zeros(len(sp["nodes"]), np.uint8)
    for q in sp["init"]:
        init[col[q]] = 1
    snaps = {c.metadata["t"]: b.mean(0).round(4).tolist() for c, b in zip(job, bits)
             if not c.metadata["echo"] and not c.metadata["tomo"]}
    shots9 = {tuple(c.metadata["tomo"]): b for c, b in zip(job, bits) if c.metadata["tomo"]}
    neg = WS.pair_negativity(shots9, [tuple(e) for e in sp["reg_edges"]], set(sp["A"]), col, seed_hex) \
        if len(shots9) == 9 else []
    band = WS.random_band(len(sp["nodes"]), shots)
    echo = []
    for c, b in zip(job, bits):
        if c.metadata["echo"]:
            Fv, se = WS.echo_fidelity(b, init)
            echo.append({"t": c.metadata["t"], "F": Fv, "sigma": se,
                         "alive": bool(Fv - band > WS.K_HEADLINE * math.sqrt(se ** 2 + 1 / shots))})
    return {"negativity_edges": neg, "witness_passed": any(e["passed"] for e in neg), "echo": echo,
            "random_band": band, "snapshots_p1": snaps}


def claim(cell: dict) -> dict:
    ok = bool(cell.get("witness_passed"))
    best = max(cell.get("negativity_edges") or [{"N": 0, "sigma": 0}], key=lambda e: e["N"])
    return {"family": NAME, "claim_level": CLAIM if ok else "L0", "witness": "QCA pair negativity (Bonferroni)",
            "value": best["N"], "sigma": best["sigma"], "k": WS.K_HEADLINE, "passed": ok,
            "label": cell.get("sim_label"),
            "note": f"{cell.get('sites')} sites, t_w={cell.get('t_w')}, rule {cell.get('rule')}; non-Clifford "
                    f"(frontier family); hardness is the BP column, not this witness"}


