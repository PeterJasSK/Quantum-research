"""D-DU: a loss meter with an exact reference in a deep chaotic circuit (plans/feature-QCAND-*.md).

Kicked Ising chain at the dual-unitary point, one Floquet step
    U = exp(-i pi/4 sum X) exp(-i pi/4 sum Z Z) exp(-i h sum Z)        (2 CZ layers per step)
The two-site operator Z_x Y_(x+1) moves one site to the right per step and nothing else survives on the light cone:
    C(t) = Tr[ (Z_(x+t) Y_(x+t+1))(t)  Z_x Y_(x+1) ] / 2^n = cos^t(2h)
This form was found and checked numerically here on 10 qubits (h = 0.1, t <= 4) and again by the module's own
circuits on 9 qubits; it is not transcribed from 2411.00765 [verify]. At h = 0 the circuit is Clifford and C = 1.

Estimator  the trace is an average over the eigenstates of Z_0 Y_1 with every other qubit maximally mixed: per
           circuit a random bit string, qubit 0 in |0> or |1>, qubit 1 in |+i> or |-i>; Z on qubit t and Y on qubit
           t + 1 are read; the outcome is weighted by the eigenvalue of the input. Raw counts.
Fit        C_raw(t) / cos^t(2h) = A exp(-g t). g is the loss per Floquet step of a weight-2 operator, idle errors
           included (the ladder's shallow rungs do not see them, gap G4). loss_per_layer = g / 2 (per CZ layer) is
           merged into <run>/qhard/loss_per_cz.json; ring_l2.forecast uses it as the loss per CZ when present.
"""
from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit

from common import allocate as A, qhard as QH, quantum as Q, runio
from common.runio import Ctx


def exact(h: float, t: int) -> float:
    return math.cos(2 * h) ** t


def du_circuit(chain: list[int], h: float, t: int, s: np.ndarray, name: str) -> QuantumCircuit:
    """t Floquet steps on the chain from the product state s (s[1] picks |+i> or |-i> on qubit 1), then Z on qubit t
    and Y on qubit t + 1. exp(-i pi/4 Z Z) = CZ (S x S) up to a phase; exp(-i pi/4 X) = sqrt-X."""
    n = len(chain)
    qc = QuantumCircuit(n, n, name=name)
    for q in np.flatnonzero(s):
        qc.x(int(q))
    qc.h(1)
    qc.s(1)                                                     # |0> -> |+i>, |1> -> |-i>
    for _ in range(t):
        if h:
            qc.rz(2 * h, range(n))
        for par in (0, 1):
            for i in range(par, n - 1, 2):
                qc.cz(i, i + 1)
                qc.s(i)
                qc.s(i + 1)
        qc.sx(range(n))
    qc.sdg(t + 1)
    qc.h(t + 1)
    qc.measure(range(n), range(n))
    qc.metadata = {"layout": [int(q) for q in chain]}
    return qc


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    tg = Q.session(ctx).target
    g, _ = A.prune(tg)
    h = float(cfg["h"])
    r = Q.rng(ctx, name, "strings")
    rows, circuits = [], []
    for n in cfg["n"]:
        try:
            chain = A.path(g, tg, n)["nodes"]
        except A.Infeasible as e:
            rows.append({"n": n, "status": f"no chain: {e}"})
            continue
        for t in [t for t in cfg["t"] if t <= n - 2]:
            ss = [r.integers(0, 2, n).astype(np.uint8) for _ in range(cfg["strings"])]
            rows.append({"n": n, "h": h, "t": t, "status": "done", "C_exact": exact(h, t), "chain": [int(q) for q in chain],
                         "_s": ss, "_at": len(circuits)})
            circuits += [du_circuit(chain, h, t, s, f"du_n{n}_t{t}_{k}") for k, s in enumerate(ss)]
    done = [x for x in rows if x["status"] == "done"]
    if not done:
        raise QH.NoLayout(f"no chain of {cfg['n']} qubits on {tg.name}")
    bits, info = Q.execute(ctx, name, circuits, ctx.shots)
    for x in done:
        vals = []
        for k, s in enumerate(x["_s"]):
            bt = bits[x["_at"] + k]
            vals.append((-1.0) ** int(s[0] ^ s[1]) * (1.0 - 2.0 * (bt[:, x["t"]] ^ bt[:, x["t"] + 1])))
        v = np.concatenate(vals)
        x["C_raw"], x["sigma"] = float(v.mean()), float(max(v.std() / math.sqrt(len(v)), 1e-9))
    fit = [x for x in done if x["C_raw"] > 2 * x["sigma"]]
    result = {"rows": rows, "info": info, "h": h, "model": "C_raw(t) / cos^t(2h) = A exp(-g t), weighted least squares on the log"}
    if len({x["t"] for x in fit}) < 2:
        Q.save(ctx, name, result | {"loss_per_layer": None, "sigma": None, "status": "fewer than two usable points"})
        return [Q.claim(ctx, name, cfg, None, None, False, info["label"], "fewer than two points above 2 sigma: no fit")]
    X = np.array([[1.0, -x["t"]] for x in fit])
    y = np.array([math.log(x["C_raw"] / x["C_exact"]) for x in fit])
    w = np.array([x["C_raw"] / x["sigma"] for x in fit])                # 1 / sigma of the log
    P = np.linalg.pinv(X * w[:, None])
    (ln_a, gdec), cov = P @ (y * w), P @ P.T
    step, sig = float(gdec), float(math.sqrt(cov[1, 1]))
    result |= {"amplitude": float(math.exp(ln_a)), "loss_per_step": step, "sigma_step": sig, "loss_per_layer": step / 2,
               "sigma": sig / 2, "points": len(fit)}
    Q.save(ctx, name, result)
    f = ctx.path("qhard", "loss_per_cz.json")                   # merged: the ladder's two numbers stay
    runio.save_json(f, (runio.load_json(f) or {}) | {"loss_per_layer": step / 2, "sigma_layer": sig / 2, "layer_source": name,
                                                     "layer_label": info["label"]})
    return [Q.claim(ctx, name, cfg, step / 2, sig / 2, True, info["label"],
                    f"loss per CZ layer (half the loss per Floquet step {step:.4f} +- {sig:.4f}); amplitude A = "
                    f"{math.exp(ln_a):.3f} (preparation and readout); {len(fit)} points, chains of "
                    f"{sorted({x['n'] for x in fit})} qubits, t up to {max(x['t'] for x in fit)}, h = {h}, "
                    f"{cfg['strings']} input strings per point from the pool-seeded generator; raw counts, no mitigation; "
                    f"chain ranked by calibration cost; reference cos^t(2h) checked numerically, not transcribed [verify]")]
