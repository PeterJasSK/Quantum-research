"""M12 rac_circuit and the R2 runner: a quantum random access code on the hand-off register (stage B -> D).

    R2-Q2   2 bits -> 1 qubit   states on the X-Z great circle, questions Z / X          ideal 0.854, classical 0.75
    R2-Q3   3 bits -> 1 qubit   Bloch vectors (+-1, +-1, +-1)/sqrt 3, questions Z / X / Y  ideal 0.789, classical 0.75
    R2-D4   2 dits -> 2 qubits  |e_x0> + sign |f_x1> with f = (H x H) e, questions Z Z / X X   ideal 0.75, classical 0.625

Score = success averaged over all inputs and questions (one circuit each). The claim rests on the dimension of
the message (one or two qubits): it is not device-independent (plan X6). Classical bounds are textbook [verify].
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation

from common import qhard as QH, quantum as Q
from common.runio import Ctx

IDEAL = {(2, 2): 0.5 + 0.5 / math.sqrt(2), (2, 3): 0.5 + 0.5 / math.sqrt(3), (4, 2): 0.75}


def rac_circuits(d: int, n_inputs: int, layout: list[int]) -> tuple[list[QuantumCircuit], list[int]]:
    """M12. -> (circuits, expected outcome per circuit as an integer over the measured qubits)."""
    out, want = [], []
    if d == 2:
        for x in itertools.product((0, 1), repeat=n_inputs):
            sx = [(-1) ** b for b in x]
            v = np.array([sx[1], sx[2] if n_inputs == 3 else 0.0, sx[0]], float)        # (x, y, z): Z asks bit 0
            v /= np.linalg.norm(v)
            for q in range(n_inputs):
                qc = QuantumCircuit(1, 1, name=f"rac_{''.join(map(str, x))}_q{q}")
                qc.u(math.acos(v[2]), math.atan2(v[1], v[0]), 0.0, 0)
                if q == 1:
                    qc.h(0)
                elif q == 2:
                    qc.sdg(0)
                    qc.h(0)
                qc.measure(0, 0)
                qc.metadata = {"layout": layout[:1], "input": list(x), "question": q}
                out.append(qc)
                want.append(x[q])
    elif d == 4 and n_inputs == 2:
        for x0, x1 in itertools.product(range(4), repeat=2):
            e = np.zeros(4)
            e[x0] = 1.0
            f = np.array([0.5 * (-1) ** bin(j & x1).count("1") for j in range(4)])
            psi = e + (-1) ** bin(x0 & x1).count("1") * f
            psi /= np.linalg.norm(psi)
            for q in range(2):
                qc = QuantumCircuit(2, 2, name=f"rac4_{x0}{x1}_q{q}")
                qc.append(StatePreparation(psi), [0, 1])
                if q == 1:
                    qc.h([0, 1])
                qc.measure([0, 1], [0, 1])
                qc.metadata = {"layout": layout[:2], "input": [x0, x1], "question": q}
                out.append(qc)
                want.append((x0, x1)[q])
    else:
        raise Q.Refused(f"random access code d = {d}, n_inputs = {n_inputs} is not in the plan")
    return out, want


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    tg = Q.session(ctx).target
    pair = QH.tile_layout(tg, "pair", max_tiles=1)[0]["qubits"]
    layout = pair if cfg["d"] == 4 else [min(pair, key=tg.ro)]
    circuits, want = rac_circuits(cfg["d"], cfg["n_inputs"], layout)
    shots = max(100, ctx.shots // 4)
    bits, info = Q.execute(ctx, name, circuits, shots, opt=3)
    plan = {"layout": layout, "n_circuits": len(circuits), "ideal": IDEAL[(cfg["d"], cfg["n_inputs"])],
            "info": info}
    ps = []
    for bt, w in zip(bits, want):
        val = (bt * (1 << np.arange(bt.shape[1]))).sum(1)
        ps.append(float((val == w).mean()))
    ps = np.array(ps)
    sh = info["shots"] if not isinstance(info["shots"], list) else info["shots"][0]
    succ = float(ps.mean())
    sigma = float(np.sqrt((ps * (1 - ps)).sum() / sh) / len(ps))
    Q.save(ctx, name, plan | {"success": succ, "sigma": sigma, "worst_case": float(ps.min()),
                              "per_circuit": ps})
    return [Q.claim(ctx, name, cfg, succ, sigma, succ - cfg["bound"] > 3 * sigma, info["label"],
                     f"{len(circuits)} circuits on qubit(s) {layout}; ideal {plan['ideal']:.3f}, worst input "
                     f"{ps.min():.3f}; average success, message dimension {cfg['d']} assumed")]
