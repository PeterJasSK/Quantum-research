"""Games of section B (plans/feature-QCAND-*.md): B-GHZ, B-MSQ, B-KS. Each has the structure of common/game.py:
build the circuits, play them in one job, score the raw counts.

    B-GHZ   N-player GHZ parity game. A GHZ state on a breadth-first tree of the chip; inputs are bit strings of even
            weight; player i reads X (bit 0) or Y (bit 1); win when the parity of the outputs is (weight / 2) mod 2.
            Local players win at most 1/2 + 2^-ceil(N/2) on uniform inputs [verify].
    B-MSQ   Mermin-Peres magic square game on two Bell pairs per 4-qubit path. Alice gets a row, Bob a column; each
            reads its three commuting observables after a two-qubit basis change; win when they agree on the shared
            cell. Local players win at most 8/9.
    B-KS    The same square as a sequential contextuality test on 2 qubits: the three observables of a row or column
            are measured one after another through an ancilla (mid-circuit readout and reset).
            chi = sum of the 6 signed context products; noncontextual models reach 4, quantum theory 6.

The players of a game sit on one chip and are not separated: every claim here is "locality assumed (same chip)".
B-KS assumes compatible, sharp measurements; it is not a dimension-free claim.
"""
from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Clifford, Pauli

from common import allocate as A, game as GM, qhard as QH, quantum as Q
from common.runio import Ctx

MID_CIRCUIT_LIVE = False      # Peter: set True once mid-circuit readout is enabled for the account (off by default)


def _z_need(k: int) -> float:
    from scipy.stats import norm

    return 3.0 if k <= 1 else float(norm.isf(norm.sf(3.0) / k))          # Bonferroni over tiles or sizes


# ============================================================================================== B-GHZ
def ghz_inputs(n: int, k: int, g: np.random.Generator) -> list[tuple[int, ...]]:
    """k distinct even-weight strings; every one of them when there are at most k."""
    if 2 ** (n - 1) <= k:
        return [x for x in (tuple((v >> j) & 1 for j in range(n)) for v in range(2 ** n)) if sum(x) % 2 == 0]
    out: set[tuple[int, ...]] = set()
    while len(out) < k:
        x = [int(v) for v in g.integers(0, 2, n - 1)]
        out.add(tuple(x + [sum(x) % 2]))
    return sorted(out)


def ghz_circuit(tree: dict, x: tuple[int, ...], name: str, entangle: bool = True) -> QuantumCircuit:
    """GHZ on the tree (H on the root, CX parent -> child in breadth-first order), then X (input 0) or Y (input 1)."""
    nodes = tree["nodes"]
    pos = {q: k for k, q in enumerate(nodes)}
    qc = QuantumCircuit(len(nodes), len(nodes), name=name)
    qc.h(pos[tree["root"]])
    for p, c in tree["edges"] if entangle else ():
        qc.cx(pos[p], pos[c])
    for k, b in enumerate(x):
        if b:
            qc.sdg(k)
        qc.h(k)
    qc.measure(range(len(nodes)), range(len(nodes)))
    qc.metadata = {"layout": [int(q) for q in nodes]}
    return qc


def run_ghz(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    tg = Q.session(ctx).target
    g, _ = A.prune(tg)
    rows, circuits = [], []
    for n in cfg["n"]:
        try:
            tree = A.bfs_tree(g, tg, n, by_cost=True)
        except A.Infeasible as e:
            rows.append({"n": n, "status": f"no tree: {e}"})
            continue
        xs = ghz_inputs(n, cfg["inputs"], Q.rng(ctx, name, f"inputs-{n}"))
        rows.append({"n": n, "status": "done", "tree_depth": tree["depth"], "qubits": [int(q) for q in tree["nodes"]],
                     "inputs": len(xs), "bound": 0.5 + 2.0 ** -math.ceil(n / 2), "_xs": xs, "_at": len(circuits)})
        circuits += [ghz_circuit(tree, x, f"ghz_n{n}_{k:02d}") for k, x in enumerate(xs)]
    done = [r for r in rows if r["status"] == "done"]
    if not done:
        raise QH.NoLayout(f"no GHZ tree of {cfg['n']} qubits on {tg.name}")
    bits, info = Q.execute(ctx, name, circuits, GM._shots(ctx, cfg["inputs"]))
    z_need = _z_need(len(done))
    for r in done:
        ps = np.array([float(((bits[r["_at"] + k].sum(1) & 1) == (sum(x) // 2) % 2).mean()) for k, x in enumerate(r["_xs"])])
        sh = len(bits[r["_at"]])
        r["win"] = float(ps.mean())
        r["sigma"] = float(max(math.sqrt((ps * (1 - ps)).sum() / sh) / len(ps), 1e-9))
        r["passed"] = bool((r["win"] - r["bound"]) / r["sigma"] > z_need)
    ok = [r for r in done if r["passed"]]
    best = max(ok, key=lambda r: r["n"]) if ok else min(done, key=lambda r: r["n"])
    Q.save(ctx, name, {"rows": rows, "largest_passing_n": best["n"] if ok else None, "z_needed": z_need, "info": info})
    return [Q.claim(ctx, name, cfg | {"bound": best["bound"]}, best["win"], best["sigma"], bool(ok), info["label"],
                    (f"largest passing N = {best['n']}" if ok else f"no size passes; N = {best['n']} shown")
                    + f" (tree depth {best['tree_depth']}); sizes "
                    + ", ".join(f"{r['n']}: {r['win']:.3f} against {r['bound']:.3f}" for r in done)
                    + f"; z > {z_need:.2f} needed; {best['inputs']} even-weight inputs per size from the pool-seeded "
                      f"generator, the bound is for uniform inputs; tree ranked by calibration cost; raw counts")]


# ============================================================================================== the magic square
# Cell = (two-qubit Pauli, sign); first letter = the player's first qubit. Rows multiply to +1, columns to -1.
SQUARE = ((("XI", 1), ("IX", 1), ("XX", 1)),
          (("IZ", 1), ("ZI", 1), ("ZZ", 1)),
          (("XZ", -1), ("ZX", -1), ("YY", 1)))
ROWS = SQUARE
COLS = tuple(tuple(SQUARE[r][c] for r in range(3)) for c in range(3))


def _rotations():
    def none(qc, a, b):
        pass

    def hh(qc, a, b):
        qc.h([a, b])

    def h_a(qc, a, b):
        qc.h(a)

    def h_b(qc, a, b):
        qc.h(b)

    def bell(qc, a, b):
        qc.cx(a, b)
        qc.h(a)

    def h_bell(qc, a, b):
        qc.h(b)
        bell(qc, a, b)

    return none, hh, h_a, h_b, bell, h_bell


def readout(context, transpose: bool = False):
    """The two-qubit basis change that turns the three commuting observables of a context into Z readouts.
    -> (rotation, [(bits read, flip) per observable]): the observable's outcome bit = parity of those bits XOR flip.
    transpose: the other player's observables (a Y changes sign), so that the two players agree on a Bell pair."""
    for rot in _rotations():
        qc = QuantumCircuit(2)
        rot(qc, 0, 1)
        cl, out = Clifford(qc), []
        for label, sign in context:
            p = Pauli(label[::-1]).evolve(cl, frame="s")                # rot O rot^dagger = +- a Z string
            if p.x.any() or p.phase not in (0, 2):
                break
            s = sign * (1 if p.phase == 0 else -1) * ((-1) ** label.count("Y") if transpose else 1)
            out.append(([k for k in range(2) if p.z[k]], int(s < 0)))
        else:
            return rot, out
    raise RuntimeError(f"no basis change for the context {context}")


def msq_circuit(path: list[int], r: int, c: int, entangle: bool = True) -> QuantumCircuit:
    """One tile, input (row r, column c). Path qubits 0 1 2 3: Alice holds (0, 1), Bob (3, 2). A Bell pair is made
    on (1, 2), moved out to (0, 3) with two CX on each side, and a second pair is made on (1, 2)."""
    qc = QuantumCircuit(4, 4, name=f"msq_{r}{c}")
    for move in (True, False):
        qc.h(1)
        if entangle:
            qc.cx(1, 2)
        if move:
            for a, b in ((1, 0), (2, 3)):
                qc.cx(a, b)
                qc.cx(b, a)
    readout(ROWS[r])[0](qc, 0, 1)
    readout(COLS[c], transpose=True)[0](qc, 3, 2)
    qc.measure(range(4), range(4))
    qc.metadata = {"layout": [int(q) for q in path]}
    return qc


def msq_wins(bits: np.ndarray, r: int, c: int) -> np.ndarray:
    """Per-shot win flags of one tile (columns = path qubits): Alice's bit for cell (r, c) equals Bob's."""
    (ma, fa), (mb, fb) = readout(ROWS[r])[1][c], readout(COLS[c], transpose=True)[1][r]
    alice = (bits[:, [(0, 1)[k] for k in ma]].sum(1) & 1) ^ fa
    bob = (bits[:, [(3, 2)[k] for k in mb]].sum(1) & 1) ^ fb
    return alice == bob


def run_msq(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    tg = Q.session(ctx).target
    tiles = QH.tile_layout(tg, "path4", max_tiles=cfg["tiles"])
    inputs = [(r, c) for r in range(3) for c in range(3)]
    circuits = [GM.merge([msq_circuit(t["qubits"], r, c) for t in tiles], f"msq_{r}{c}") for r, c in inputs]
    bits, info = Q.execute(ctx, name, circuits, GM._shots(ctx, len(inputs)))
    wins = np.array([[msq_wins(bt[:, 4 * t:4 * t + 4], r, c).mean() for bt, (r, c) in zip(bits, inputs)]
                     for t in range(len(tiles))])
    win = wins.mean(1)
    sigma = np.maximum(np.sqrt((wins * (1 - wins)).sum(1) / len(bits[0])) / len(inputs), 1e-9)
    z_need = _z_need(len(tiles))
    ok = (win - cfg["bound"]) / sigma > z_need
    need = min(cfg.get("min_pass", len(tiles)), len(tiles))
    Q.save(ctx, name, {"tiles": [{"qubits": t["qubits"], "win": float(w), "sigma": float(s), "passed": bool(p)}
                                 for t, w, s, p in zip(tiles, win, sigma, ok)],
                       "inputs": inputs, "win_per_input": wins, "tiles_passed": int(ok.sum()), "z_needed": z_need,
                       "info": info})
    k = int(np.argsort(win)[len(tiles) // 2])
    return [Q.claim(ctx, name, cfg, float(win[k]), float(sigma[k]), bool(ok.sum() >= need), info["label"],
                    f"{int(ok.sum())} of {len(tiles)} tiles pass (need {need}, z > {z_need:.2f}); median tile shown, "
                    f"best {win.max():.3f}, worst {win.min():.3f}; all 9 inputs, one circuit each (no draw needed); "
                    f"ideal 1, raw counts")]


# ============================================================================================== B-KS
def _product_sign(context) -> int:
    p = Pauli("II")
    for label, _ in context:
        p = p.compose(Pauli(label[::-1]))
    return int(np.prod([s for _, s in context])) * (1 if p.phase == 0 else -1)


CONTEXTS = ROWS + COLS
EXPECT = tuple(_product_sign(c) for c in CONTEXTS)          # +1 for the rows, -1 for the columns


def ks_circuit(path: list[int], context, entangle: bool = True) -> QuantumCircuit:
    """One tile: data qubits 0 and 2, ancilla 1 between them. Each observable: H, controlled Paulis from the
    ancilla, H, readout into clbit j, reset."""
    qc = QuantumCircuit(3, 3, name="ks")
    for j, (label, _) in enumerate(context):
        qc.h(1)
        for d, p in zip((0, 2), label):
            if entangle and p != "I":
                getattr(qc, {"X": "cx", "Y": "cy", "Z": "cz"}[p])(1, d)
        qc.h(1)
        qc.measure(1, j)
        if j < 2:
            qc.reset(1)
    qc.metadata = {"layout": [int(q) for q in path]}
    return qc


def ks_chi(bits: list[np.ndarray]) -> tuple[float, float]:
    """bits[k]: (shots, 3) ancilla outcomes of context k of one tile -> (chi, sigma)."""
    chi, var = 0.0, 0.0
    for bt, ctxt, want in zip(bits, CONTEXTS, EXPECT):
        e = float(np.prod([s for _, s in ctxt]) * (1.0 - 2.0 * (bt.sum(1) & 1)).mean())
        chi += want * e
        var += (1 - e * e) / len(bt)
    return chi, math.sqrt(max(var, 1e-18))


def run_ks(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    s = Q.session(ctx)
    ops = set(s.backend.target.operation_names)
    if not {"measure", "reset"} <= ops:
        raise Q.Refused(f"{s.target.name} has no mid-circuit measurement and reset")
    if s.live and not MID_CIRCUIT_LIVE:
        raise Q.Refused("mid-circuit readout is an option of the IBM plan, off by default: set MID_CIRCUIT_LIVE = True "
                        "in B_mapping/games.py once it is enabled")
    tiles = QH.tile_layout(s.target, "path3", max_tiles=cfg["tiles"])
    circuits = [GM.merge([ks_circuit(t["qubits"], c) for t in tiles], f"ks_{k}") for k, c in enumerate(CONTEXTS)]
    # dynamic circuits: common.quantum.execute refuses them (lint rule 1), so this is the same path without that rule
    isa = [transpile(qc, backend=s.backend, initial_layout=qc.metadata["layout"], optimization_level=1,
                     seed_transpiler=1) for qc in circuits]
    per = Q.fit_shots(ctx, name, isa, [GM._shots(ctx, len(circuits))] * len(isa))
    g2 = s.target.gate_2q
    Q.log(f"{name}: {len(isa)} dynamic circuits, up to {max(c.count_ops().get(g2, 0) for c in isa)} {g2} each, on {s.target.name}")
    res, job_id, label = Q.run_isa(ctx, name, isa, per, dd=False)
    bits = [Q.bits(res[k]) for k in range(len(isa))]
    Q._keep(ctx, name, bits)
    info = {"backend": s.target.name, "circuits": len(isa), "shots": per[0], "job_id": job_id, "label": label,
            "two_qubit_gates_max": max(c.count_ops().get(g2, 0) for c in isa)}
    rows = []
    for t, tile in enumerate(tiles):
        chi, sig = ks_chi([bt[:, 3 * t:3 * t + 3] for bt in bits])
        rows.append({"qubits": tile["qubits"], "chi": chi, "sigma": sig})
    z_need = _z_need(len(tiles))
    ok = [(r["chi"] - cfg["bound"]) / r["sigma"] > z_need for r in rows]
    need = min(cfg.get("min_pass", len(tiles)), len(tiles))
    Q.save(ctx, name, {"tiles": rows, "contexts": [[lab for lab, _ in c] for c in CONTEXTS], "tiles_passed": int(sum(ok)),
                       "z_needed": z_need, "memory_bound_bits": math.log2(6), "info": info})
    r = sorted(rows, key=lambda x: x["chi"])[len(rows) // 2]
    return [Q.claim(ctx, name, cfg, r["chi"], r["sigma"], bool(sum(ok) >= need), label,
                    f"{int(sum(ok))} of {len(rows)} tiles pass (need {need}, z > {z_need:.2f}); median tile shown; 6 "
                    f"contexts, 3 sequential ancilla readouts each (mid-circuit readout and reset); quantum value 6; "
                    f"compatibility and sharpness of the measurements are assumed, no dimension-free claim; raw counts")]
