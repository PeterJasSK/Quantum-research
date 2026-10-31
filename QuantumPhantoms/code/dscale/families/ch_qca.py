"""D-SCALE family `ch-qca` (AC-10): single-control Goldilocks QCA, native on heavy-hex and on the square lattice.

    python -m dscale.families.ch_qca --budget 40 100 120 --target boston nighthawk marrakesh --print-swaps
    python -m dscale.families.ch_qca --seed-region --mode ideal [--target marrakesh]     # 21-site witness + seed

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

import argparse
import itertools
import math

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate

from dscale import allocate as A, budget as B, families as F, lint as L, seedlift as SL, targets as T
from dscale import witness_scale as WS
from imaging.seedhash import derive_seed, rng

NAME = "ch-qca"
CLAIM = "L1"
WITNESS = "Bonferroni pair negativity at t_w <= 3 (p < 0.05) + echo fidelity above the random band by 2 sigma"
HARDNESS = "non-Clifford; depth + angle + short loops: the frontier family"
PRESETS = {40: {"sites": 40, "t_max": 3, "t_w": 2, "alpha": math.pi / 2, "rule": "parity"},
           100: {"sites": 100, "t_max": 3, "t_w": 2, "alpha": math.pi / 2, "rule": "parity"},
           120: {"sites": 120, "t_max": 3, "t_w": 2, "alpha": math.pi / 2, "rule": "parity"}}
PARAM_GRID = {"sites": [12, 21, 24, 40, 100, 120], "t": [1, 2, 3, 4, 6], "alpha": [math.pi / 8, math.pi / 4,
                                                                                   3 * math.pi / 8, math.pi / 2]}
BASES = ("X", "Y", "Z")
N_REG_EDGES = 4
NOISY_SIM_MAX = 24
MAX_EXTRA = 6


def preset_text(budget: int) -> str:
    return {40: "40-site heavy-hex patch / 5 x 8 square patch",
            100: "100-site patch",
            120: "full 12 x 10 Nighthawk (118 after pruning): headline frontier run; 120-site patch on Heron"}[budget]


def default_draw() -> dict:
    return F.default_draw()


# ---------------------------------------------------------------------------------------------- regions
def region_request(budget: int, tg: T.Target, params: dict | None = None) -> list[dict]:
    p = PRESETS[budget] | (params or {})
    if tg.name == "nighthawk" and p["sites"] >= tg.n_qubits:
        return [{"name": "qca", "family": NAME, "kind": "patch", "n": p["sites"], "role": "active", "min_n": 6, "lattice": "grid"}]
    if tg.name == "nighthawk" and budget == 40 and p["sites"] == 40:
        return [{"name": "qca", "family": NAME, "kind": "patch", "n": 40, "role": "active", "min_n": 6,
                 "within": [10 * r + c for r in range(4, 9) for c in range(1, 9)]}]          # 5 x 8 square
    return [{"name": "qca", "family": NAME, "kind": "patch", "n": p["sites"], "role": "active", "min_n": 6, "lattice": "grid"}]


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


def build(alloc: dict, params: dict, draw: dict, tg: T.Target | None = None) -> list[QuantumCircuit]:
    tg = tg or T.get(alloc["target"])
    sp = spec(patch_of(alloc, tg), params, draw)
    return job_from_spec(sp, params)


def job_from_spec(sp: dict, params: dict, twin: bool = False) -> list[QuantumCircuit]:
    t_max, t_w = int(params.get("t_max", 3)), int(params.get("t_w", 2))
    job = [circuit(sp, t, "Z", twin=twin) for t in range(t_max + 1)]
    job += [circuit(sp, t_w, (bA, bB), twin=twin) for bA, bB in itertools.product(BASES, BASES)]
    job += [circuit(sp, t, "Z", echo=True, twin=twin) for t in range(1, t_max + 1)]
    return job


def clifford_twin(circuits: list[QuantumCircuit]) -> list[QuantumCircuit]:
    out = []
    for c in circuits:
        md = c.metadata
        b = md["tomo"] if md["tomo"] else "Z"
        out.append(circuit(md["qca"], md["t"], tuple(b) if md["tomo"] else b, echo=md["echo"], twin=True))
    return out


def bp_circuits(alloc: dict, params: dict, tg: T.Target | None = None, draw: dict | None = None) -> list[dict]:
    tg = tg or T.get(alloc["target"])
    sp = spec(patch_of(alloc, tg), params, draw or default_draw())
    col = {q: k for k, q in enumerate(sp["nodes"])}
    t = int(params.get("t", params.get("t_max", 3)))
    return [{"name": f"ch-qca:{len(sp['nodes'])}:t{t}:a{sp['alpha']:.3f}", "qc": circuit(sp, t, measure=False),
             "clifford": False, "edges": [(col[a], col[b]) for a, b in sp["edges"]],
             "twin": circuit(sp, t, measure=False, twin=True)}]


# ---------------------------------------------------------------------------------------------- SWAPs
def routing_swaps(qc: QuantumCircuit, target: str, seed: int = 1) -> int:
    """SWAPs the router inserts on the target with the trivial (allocated) layout."""
    from qiskit.transpiler import StagedPassManager
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    tg = T.get(target)
    if tg.backend is None:
        return 0
    pm = generate_preset_pass_manager(1, backend=tg.backend, initial_layout=qc.metadata["layout"], seed_transpiler=seed)
    pm2 = StagedPassManager(stages=["init", "layout", "routing"], init=pm.init, layout=pm.layout, routing=pm.routing)
    return int(pm2.run(qc).count_ops().get("swap", 0))


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


def run_job(sp: dict, params: dict, mode: str, target: str, shots: int, seed: int, seed_hex: str,
            twin: bool = False, deadline: B.Deadline | None = None) -> dict:
    job = job_from_spec(sp, params, twin=twin)
    kind = mode.partition(":")[0]
    if kind == "pauli" and not twin:
        method = "density_matrix" if len(sp["nodes"]) <= 12 else "statevector"
    else:
        method = None
    ex = F.execute(job, mode, target, shots, seed, method=method, deadline=deadline)
    out = analyse(job, ex["bits"], sp, shots, seed_hex)
    tw = sum(c.count_ops().get("cz", 0) for c in ex["isa"])
    return out | {"sites": len(sp["nodes"]), "rule": sp["rule"], "alpha": sp["alpha"], "t_w": params.get("t_w", 2),
                  "init": sp["init"], "hashes": ex["hashes"], "sim_label": ex["sim_label"], "isa_cz": tw,
                  "_isa": ex["isa"]}


def claim(cell: dict) -> dict:
    ok = bool(cell.get("witness_passed"))
    best = max(cell.get("negativity_edges") or [{"N": 0, "sigma": 0}], key=lambda e: e["N"])
    return {"family": NAME, "claim_level": CLAIM if ok else "L0", "witness": "QCA pair negativity (Bonferroni)",
            "value": best["N"], "sigma": best["sigma"], "k": WS.K_HEADLINE, "passed": ok,
            "label": cell.get("sim_label"),
            "note": f"{cell.get('sites')} sites, t_w={cell.get('t_w')}, rule {cell.get('rule')}; non-Clifford "
                    f"(frontier family); hardness is the BP column, not this witness"}


# ---------------------------------------------------------------------------------------------- seed shapes
def seed_shape(target: str, mode: str, draw: dict, shots: int, deadline: B.Deadline | None = None,
               witness: bool = True, params: dict | None = None) -> dict:
    """AC-10/AC-15: per tile, a QCA Z snapshot on the simulable seed region (21-site ideal / 12-site noisy), driven by
    the tile's draw, lifted to a 3-D occupancy. One sampled shot = the snapshot (seed "DS-qca-snapshot")."""
    tg = T.get(F.mode_target(mode, target))
    g, _ = A.prune(tg)
    patch = SL.seed_patch(tg.name, g, mode)
    p = {"t_max": 2, "t_w": 2, "alpha": math.pi / 2, "rule": "parity"} | (params or {})
    sp = spec(patch, p, draw)
    seed = derive_seed(draw["seed_hex"], "DS-qca-snapshot") % 2 ** 31
    snap = circuit(sp, int(p["t_w"]), "Z")
    ex = F.execute([snap], mode, target, 1, seed)
    bits = ex["bits"][0][0]
    active = [q for q, b in zip(sp["nodes"], bits) if b]
    occ = SL.lift(patch, active)
    res = {"region": patch["kind"], "sites": len(sp["nodes"]), "init": sp["init"], "active": active,
           "occupancy": occ, "seed_cells": int(occ.sum()), "witness_passed": None, "claim_level": "L0",
           "hashes": ex["hashes"], "sim_label": ex["sim_label"], "spec": sp, "t": int(p["t_w"])}
    if witness and (deadline is None or not deadline.expired()):
        job = [circuit(sp, int(p["t_w"]), (bA, bB)) for bA, bB in itertools.product(BASES, BASES)]
        try:
            ex9 = F.execute(job, mode, target, shots, derive_seed(draw["seed_hex"], "DS-qca-witness") % 2 ** 31,
                            deadline=deadline)
        except B.DeadlineHit:
            return res                                   # snapshot kept, witness skipped (claim L0, truncated)
        an = analyse(job, ex9["bits"], sp, shots, draw["seed_hex"])
        res |= {"witness_passed": an["witness_passed"], "negativity_edges": an["negativity_edges"],
                "claim_level": CLAIM if an["witness_passed"] else "L0", "hashes": res["hashes"] + ex9["hashes"]}
    elif witness and deadline is not None:
        deadline.skip(f"qca witness for {draw.get('tile_id')}")
    return res


# ---------------------------------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--budget", type=int, nargs="*", default=[40], choices=F.BUDGETS)
    ap.add_argument("--target", nargs="*", default=["marrakesh"], choices=T.NAMES)
    ap.add_argument("--mode", default="ideal")
    ap.add_argument("--print-swaps", action="store_true", help="transpile the presets and print the routing SWAPs")
    ap.add_argument("--seed-region", action="store_true", help="21-site (ideal) / 12-site (noisy) witness + seed")
    ap.add_argument("--rule", default="parity", choices=("parity", "v3"))
    ap.add_argument("--alpha", type=float, default=math.pi / 2)
    ap.add_argument("--t-w", type=int, default=2)
    B.add_args(ap)
    a = ap.parse_args()
    dl = B.check(a, default_repeats=1)
    if a.rule == "v3" and a.mode != "ideal":
        raise SystemExit("refused: --rule v3 is simulation-only in ideal mode")
    if a.print_swaps:
        for tname in a.target:
            tg = T.get(tname)
            for b in a.budget:
                if dl.expired():
                    dl.skip(f"swaps {tname} {b}")
                    continue
                alloc = A.allocate(region_request(b, tg), tg)
                job = build(alloc, PRESETS[b] | {"rule": a.rule, "alpha": a.alpha}, default_draw(), tg)
                L.enforce(job, alloc["regions"], NAME, tg.graph)
                deep = [c for c in job if not c.metadata["tomo"] and not c.metadata["echo"]][-1]
                echo = job[-1]
                sw = routing_swaps(deep, tname) + routing_swaps(echo, tname)
                cz = F.transpile_to(deep, tname, 1).count_ops().get("cz", 0) if tg.backend else None
                print(f"  {tname:10s} budget {b:3d}: {len(deep.metadata['layout']):3d} sites, "
                      f"{len(colour_layers(patch_of(alloc, tg)['graph']))} colour layers, ISA CZ (t={deep.metadata['t']}"
                      f") {cz}, SWAPs (snapshot t={deep.metadata['t']} + echo t={echo.metadata['t']}): {sw}", flush=True)
        print(dl.report())
        return 0
    if a.seed_region:
        tname = a.target[0]
        draw = default_draw()
        r = seed_shape(tname, a.mode, draw, a.shots, dl, params={"t_w": a.t_w, "t_max": a.t_w, "alpha": a.alpha,
                                                                   "rule": a.rule})
        print(f"seed region {r['region']} ({r['sites']} sites), {r['sim_label']}; init {r['init']}")
        for e in r.get("negativity_edges", []):
            print(f"  edge ({e['i']},{e['j']}): N = {e['N']:.4f} +- {e['sigma']:.4f}  p_bonf = {e['p_bonf']:.2e}  "
                  f"passed={e['passed']}")
        print(f"  witness passed: {r['witness_passed']} -> claim {r['claim_level']}; snapshot active "
              f"{len(r['active'])}/{r['sites']}; seed occupancy {r['occupancy'].shape} with {r['seed_cells']} voxels")
        print(dl.report())
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
