"""L2-BAND: random T-doped Clifford sampling on a 2-D patch, with no post-selection (L2 attempt).

Why a patch. Exact tensor-network contraction costs 2^W, W = two-qubit gates crossing the sweep front
(arXiv 2608.13110: IBM's 70-qubit depth-70 chain was contracted in 37 minutes; a ring has W = depth). To make W
large with the fewest CZ, the circuit must be wide where it is cut: N_CZ = edges x W / cutwidth. A ring has cutwidth
2 (64-ring, W = 73: 2,336 CZ); a heavy-hex patch has cutwidth ~4, so the same W costs about half the CZ; a
square-lattice patch (Nighthawk) has cutwidth ~sqrt(n). common.qhard.patch_layout picks the patch.

What is measured (all efficient, no supercomputer):
    reference   the Clifford skeleton (t = 0): direct fidelity estimation over random stabilizers -> raw fidelity F
    mirror      U then U^-1 then a random bit string: the return probability ~ F^2 with readout (a second estimator, as
                in the Nighthawk RCS claim, arXiv 2609.28657)
    samples     the T-doped circuit in the Z basis: the hard samples (live only; they do not fit a simulator)
T gates are virtual Z rotations (no added noise); without checks they may sit anywhere.

What is NOT here: spacetime checks (see ring_l2), gate twirling, the doping-loss theorem of 2607.25941 (a
placeholder is subtracted), an agreement test against exact simulation. So a pass is an attempt, not a certificate.
The claim passes only if the bound is positive AND the classical-cost ledger says hard (>= 2^73 operations per
amplitude by every known exact method).
"""
from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit, qpy
from qiskit.quantum_info import Pauli, StabilizerState

from common import qhard as QH, quantum as Q
from common.runio import Ctx
from D_quantum_growth.ring_l2 import _pauli_label, certify


def mirror(sk: dict, layout: list[int], t_sites, g: np.random.Generator, name: str) -> tuple[QuantumCircuit, np.ndarray]:
    """U, barrier, U^-1, X on a random string s; the ideal output is s."""
    n = sk["n"]
    u = QH.circuit(sk, layout, t_sites=t_sites).remove_final_measurements(inplace=False)
    s = g.integers(0, 2, n).astype(np.uint8)
    qc = QuantumCircuit(n, n, name=name)
    qc.compose(u, inplace=True)
    qc.barrier()                                         # keeps the transpiler from cancelling U U^-1
    qc.compose(u.inverse(), inplace=True)
    for q in np.flatnonzero(s):
        qc.x(int(q))
    qc.measure(range(n), range(n))
    qc.metadata = {"layout": [int(q) for q in layout]}
    return qc, s


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    s = Q.session(ctx)
    tg = s.target
    patch = QH.patch_layout(tg, cfg["n"], cfg["width"])
    g = Q.rng(ctx, name, "band")
    sk = QH.patch_skeleton(patch, seed=int(g.integers(2 ** 31)))
    n, layout = sk["n"], patch["nodes"]
    t = cfg["t"]
    ledger = QH.classical_cost(sk, t)
    sites = [(q, slot) for slot in range(sk["depth"]) for q in range(n)]
    tsites = [sites[int(i)] for i in sorted(g.choice(len(sites), t, replace=False))]
    Q.log(f"{name}: {n}-qubit patch on {tg.name}, cutwidth {patch['cutwidth']}, depth {sk['depth']}, {patch['n_cz']} CZ, "
          f"sweep width {ledger['sweep_width']}; cheapest exact method {ledger['binding']} at 2^{ledger['log2_cost_min']:.0f} "
          f"({'hard' if ledger['hard'] else 'NOT hard'}); predicted raw fidelity {patch['predicted_raw_fidelity']:.2e}")

    # reference: random stabilizers of the Clifford skeleton, signs from the ideal stabilizer state
    state = StabilizerState(QH.circuit(sk, layout).remove_final_measurements(inplace=False))
    gx, gz = QH.stabilizers(sk)
    stabs = []
    for _ in range(cfg["m_dfe"]):
        c = g.integers(0, 2, n).astype(np.uint8)
        if not c.any():
            c[0] = 1
        x, z = (c @ gx) & 1, (c @ gz) & 1
        lab = _pauli_label(x, z)
        sign = float(np.real(state.expectation_value(Pauli(lab[::-1]))))
        stabs.append({"label": lab, "sign": 1 if sign > 0 else -1, "support": [int(j) for j in np.flatnonzero(x | z)]})
    circuits = [QH.circuit(sk, layout, basis=st["label"].replace("I", "Z"), name=f"dfe_{k:02d}") for k, st in enumerate(stabs)]
    mirrors = [mirror(sk, layout, tsites if s.live else (), g, f"mirror_{k}") for k in range(cfg["mirrors"])]
    circuits += [qc for qc, _ in mirrors]
    doped = QH.circuit(sk, layout, t_sites=tsites, name=f"doped_t{t}")
    with open(ctx.path("qhard", name, f"doped_t{t}.qpy"), "wb") as f:
        qpy.dump(doped, f)
    if s.live:
        circuits.append(doped)
    bits, info = Q.execute(ctx, name, circuits, ctx.shots)

    vals, sigs = [], []
    for st, bt in zip(stabs, bits[:len(stabs)]):
        v = st["sign"] * (1.0 - 2.0 * (bt[:, st["support"]].sum(1) & 1))
        vals.append(float(v.mean()))
        sigs.append(float(math.sqrt(max(1 - v.mean() ** 2, 1e-12) / len(v))))
    cert = certify(vals, sigs, t)
    p_ret = [float((bt[:, :n] == sv).all(1).mean()) for (_, sv), bt in zip(mirrors, bits[len(stabs):])]
    f_mirror = math.sqrt(max(float(np.mean(p_ret)), 0.0))
    result = {"patch": patch, "depth": sk["depth"], "t": t, "ledger": ledger, "info": info, "certificate": cert,
              "mirror_return_probability": p_ret, "fidelity_from_mirror_sqrt": f_mirror,
              "mirror_note": "Clifford mirror in a dry run (T gates dropped); includes readout error",
              "doped_sampled": bool(s.live)}
    if s.live:
        np.save(ctx.path("qhard", name, "doped_samples.npy"), bits[-1][:, :n])
    Q.save(ctx, name, result)
    ok = cert["bound"] > 0 and ledger["hard"] and t >= cfg["min_t"]
    return [Q.claim(ctx, name, cfg, cert["bound"], cert["sigma"], ok, info["label"],
                    f"raw F_ref {cert['F_reference']:.4f} (m = {cert['m']}, no post-selection), mirror estimate "
                    f"{f_mirror:.4f}, desk forecast {patch['predicted_raw_fidelity']:.4f}; {n} qubits, {patch['n_cz']} CZ, "
                    f"t = {t}; cheapest exact classical method: {ledger['binding']} at 2^{ledger['log2_cost_min']:.0f} "
                    f"(threshold 2^{ledger['threshold_log2']}); doped circuit {'sampled' if s.live else 'built, not sampled'}; "
                    f"placeholder doping loss, no twirling: an attempt, not a certificate")]
