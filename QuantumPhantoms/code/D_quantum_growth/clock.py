"""M10 instrument, M11 clock_circuit and the R1 runner: the tick-clock (temporal memory advantage, L1'-T).

A machine with a d-level memory emits one bit per step through an instrument {K0, K1} (K0^ K0 + K1^ K1 = 1).
Quantum memory of one qubit, sequence 001: p = ||K1 K0 K0 psi0||^2 = 7/16, against 8/27 for every 2-state
classical machine (proven). Closed form used here (plan F3: singular values (1, 1/2) and (sqrt 3 / 2, 0)):

    K0 = [[2/3, -sqrt5/6], [sqrt5/3, 1/3]]      K1 = [[0, sqrt3/2], [0, 0]]      psi0 ~ (sqrt5/3, -1/6)

Deferred measurement (lint rule 1): each step is an isometry memory -> memory x fresh output qubit; everything is
measured at the end. On a star tile the memory is the degree-3 qubit and its 3 neighbours are the outputs, so no
routing is needed. `identical_steps = True` applies the same two-qubit unitary at every step; `False` compiles step 1
from the known input state. Both are reported (a referee may ask for the first).

Other sequences / a two-qubit memory (R1-M2-00001) come from a numerical optimiser: their quantum value is a lower
bound found by search and their classical bound is not proven here (plan X5, gap G1). Not a claim.
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation
from scipy.linalg import null_space

from common import allocate as A
from common import game as GM, qhard as QH, quantum as Q
from common.runio import Ctx

S5 = math.sqrt(5.0)


def instrument(memory_qubits: int, seq: str, restarts: int = 12) -> dict:
    """M10. -> {K: [K0, K1], psi0, value, rigour, d}."""
    d = 2 ** memory_qubits
    if memory_qubits == 1 and seq == "001":
        K0 = np.array([[2 / 3, -S5 / 6], [S5 / 3, 1 / 3]], dtype=complex)
        K1 = np.array([[0, math.sqrt(3) / 2], [0, 0]], dtype=complex)
        psi = np.array([S5 / 3, -1 / 6], dtype=complex)
        psi /= np.linalg.norm(psi)
        return {"K": [K0, K1], "psi0": psi, "value": seq_prob([K0, K1], psi, seq), "d": d,
                "rigour": "closed form (7/16)"}
    if seq in ("011",) or (memory_qubits == 1 and seq == "0001"):
        raise Q.Refused(f"sequence {seq} refused (plan X3: no gap or gap 0.05)")
    return _optimise(d, seq, restarts)


def seq_prob(K: list[np.ndarray], psi: np.ndarray, seq: str) -> float:
    s = psi
    for ch in seq:
        s = K[int(ch)] @ s
    return float(np.vdot(s, s).real)


def _optimise(d: int, seq: str, restarts: int) -> dict:
    from scipy.optimize import minimize

    g = np.random.default_rng(20261110)
    nz = 2 * d * d

    def unpack(v):
        Z = (v[:nz] + 1j * v[nz:2 * nz]).reshape(2 * d, d)
        Q, _ = np.linalg.qr(Z)                                   # isometry: rows = output * d + memory
        psi = v[2 * nz:2 * nz + d] + 1j * v[2 * nz + d:]
        return [Q[:d], Q[d:]], psi / np.linalg.norm(psi)

    best = None
    for _ in range(restarts):
        res = minimize(lambda v: -seq_prob(*unpack(v), seq), g.normal(size=2 * nz + 2 * d), method="BFGS")
        if best is None or res.fun < best.fun:
            best = res
    K, psi = unpack(best.x)
    return {"K": K, "psi0": psi, "value": float(-best.fun), "d": d,
            "rigour": f"numerical optimum, {restarts} restarts (a lower bound on the quantum value; not a claim)"}


def step_unitary(K: list[np.ndarray]) -> np.ndarray:
    """Unitary W on (memory, output) with W |m>|0> = K0|m>|0> + K1|m>|1>; index = output * d + memory."""
    V = np.vstack(K)
    return np.hstack([V, null_space(V.conj().T)])


def clock_circuit(ins: dict, seq: str, layout: list[int], identical_steps: bool, name: str = "clock") -> QuantumCircuit:
    """M11. Qubits: memory (m of them), then one output per step. Clbit k = qubit k."""
    m = int(round(math.log2(ins["d"])))
    L = len(seq)
    qc = QuantumCircuit(m + L, m + L, name=name)
    mem = list(range(m))
    W = step_unitary(ins["K"])
    first = 0
    if identical_steps:
        qc.append(StatePreparation(ins["psi0"]), mem)
    else:
        qc.append(StatePreparation(np.vstack(ins["K"]) @ ins["psi0"]), mem + [m])
        first = 1
    for i in range(first, L):
        qc.unitary(W, mem + [m + i], label="step")
    qc.measure(range(m + L), range(m + L))
    qc.metadata = {"layout": [int(q) for q in layout], "seq": seq, "identical_steps": identical_steps}
    return qc


def _patch(tg, size: int) -> list[int]:
    """Connected patch for the two-qubit memory: BFS from the best star centre (needs routing: plan 50 to 100 CZ)."""
    c = QH.tile_layout(tg, "star4", max_tiles=1)[0]["centre"]
    g, _ = A.prune(tg)
    order = [c] + [v for _, v in nx.bfs_edges(g, c)]
    if len(order) < size:
        raise QH.NoLayout(f"no connected patch of {size} qubits around {c}")
    return order[:size]


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    from scipy.stats import norm

    tg = Q.session(ctx).target
    seq, m = cfg["seq"], cfg["memory_qubits"]
    ins = instrument(m, seq, cfg.get("restarts", 12))
    if m == 1:
        tiles = QH.tile_layout(tg, "star4", max_tiles=cfg["tiles"], seed=0)
        layouts = [[t["centre"]] + t["outputs"] for t in tiles]
        arms = cfg.get("identical_steps", [False])
    else:
        layouts = [_patch(tg, m + len(seq))]
        arms = [True]
    circuits = [GM.merge([clock_circuit(ins, seq, lay, arm) for lay in layouts], f"clock_{'same' if arm else 'lean'}")
                for arm in arms]
    bits, info = Q.execute(ctx, name, circuits, ctx.shots, opt=3)
    plan = {"seq": seq, "memory_qubits": m, "tiles": layouts, "ideal_value": ins["value"],
            "instrument_rigour": ins["rigour"], "arms": ["identical_steps" if a else "first step compiled" for a in arms],
            "info": info}
    w = m + len(seq)
    want = np.array([int(ch) for ch in seq], dtype=np.uint8)
    n = len(layouts)
    z_need = 3.0 if n == 1 else float(norm.isf(norm.sf(3.0) / n))
    claims, rows = [], []
    for arm, bt in zip(arms, bits):
        ps = np.array([(bt[:, t * w + m:(t + 1) * w] == want).all(1).mean() for t in range(n)])
        sig = np.array([Q.binom_sigma(float(v), len(bt)) for v in ps])
        z = (ps - cfg["bound"]) / sig
        ok = int((z > z_need).sum())
        rows.append({"arm": "identical_steps" if arm else "first step compiled", "p": ps, "sigma": sig, "z": z,
                     "tiles_passed": ok, "z_needed": z_need})
        need = cfg.get("min_pass", n)
        passed = ok >= need and m == 1                       # the two-qubit clock cannot pass before G1 is closed
        k = int(np.argmax(ps)) if n == 1 else int(np.argsort(ps)[n // 2])
        claims.append(Q.claim(
            ctx, name, cfg | {"witness": cfg["witness"] + (" (median tile)" if n > 1 else "")}, float(ps[k]), float(sig[k]), passed, info["label"],
            f"{'identical steps' if arm else 'first step compiled from the known input'}; {ok} of {n} tiles pass "
            f"(need {need}, z > {z_need:.2f}); ideal {ins['value']:.4f} ({ins['rigour']}); worst tile {ps.min():.3f}; "
            f"up to {info['two_qubit_gates_max']} two-qubit gates in the circuit"
            + ("" if m == 1 else "; gap G1 open: classical 4-state bound not verified, so this cannot pass"),
            ))
    Q.save(ctx, name, plan | {"arms_result": rows})
    return claims
