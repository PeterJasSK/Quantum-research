#!/usr/bin/env python3
"""Cheap exact ideal, no 20-qubit dynamic sim.
A) 4-qubit unit test: is _teleport_cx == plain CX (ff and herald-00 branch)?
B) ideal bond sign: genome circuit with stage-3 as a DIRECT cx (pure unitary, fast)."""
import sys, types, math, functools, time
import numpy as np
print = functools.partial(print, flush=True)

CODE = "/home/peter/PycharmProjects/Quantum-research/QuantumLife/code"
stub = types.ModuleType("pipeline_common")
for a in ("connect", "run_sampler", "qpu_seconds"):
    setattr(stub, a, lambda *x, **k: None)
stub.timestamp = lambda: "sim"; stub.Sampler = None; stub.SHOTS_PER_JOB = 10**9
sys.modules["pipeline_common"] = stub
sys.path.insert(0, CODE)

import research_qtree_teleport as TEL
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
SIM = AerSimulator(method="statevector")
SB = 6

# ---------- A. 4-qubit logical equivalence ----------
def ct_dist(mode, ac, at, shots=40000):
    q = QuantumRegister(4, "q")
    cr = ClassicalRegister(2, "ct")
    if mode == "cx":
        qc = QuantumCircuit(q, cr)
    else:
        tel = ClassicalRegister(2, "tel"); qc = QuantumCircuit(q, cr, tel)
    qc.ry(ac, 0); qc.ry(at, 1)          # prep control, target
    if mode == "cx":
        qc.cx(0, 1)
    else:
        TEL._teleport_cx(qc, q[0], q[1], q[2], q[3], tel, 0, feedforward=(mode == "ff"))
    qc.measure(0, cr[0]); qc.measure(1, cr[1])
    counts = SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
    d = {"00": 0, "01": 0, "10": 0, "11": 0}
    tot = 0
    for k, c in counts.items():
        toks = k.split()
        ct = toks[-1]                    # 'ct' creg (added first -> rightmost in key)
        tel = toks[0] if len(toks) == 2 else None
        if mode == "herald" and tel is not None and set(tel) != {"0"}:
            continue                     # post-select tel==00
        d[ct] += c; tot += c
    return {k: v / tot for k, v in d.items()}, tot

def unit_test():
    print("=== A. is _teleport_cx == plain CX ?  (ct output distribution, L1 vs cx) ===")
    grid = [0.0, math.pi / 2, math.pi, 0.7, 2.3]
    worst_ff = worst_h = 0.0
    for ac in grid:
        for at in grid:
            ref, _ = ct_dist("cx", ac, at)
            ff, _ = ct_dist("ff", ac, at)
            hz, _ = ct_dist("herald", ac, at)
            l1ff = sum(abs(ff[k] - ref[k]) for k in ref)
            l1h = sum(abs(hz[k] - ref[k]) for k in ref)
            worst_ff = max(worst_ff, l1ff); worst_h = max(worst_h, l1h)
    print(f"  worst L1(ff, cx)     = {worst_ff:.4f}")
    print(f"  worst L1(herald, cx) = {worst_h:.4f}")
    tol = 0.03
    print(f"  => feed-forward {'== CX (equivalent)' if worst_ff < tol else 'DIFFERS from CX !!'}")
    print(f"  => herald-00    {'== CX (equivalent)' if worst_h  < tol else 'DIFFERS from CX !!'}")

# ---------- B. ideal bond sign (direct cx, pure unitary) ----------
def spec_for(ns):
    return {"n_bits": SB * ns, "slot_bits": SB, "n_slots": ns}

def build_ideal(theta, kick, env, spec, bonds):
    n = spec["n_bits"]; sb = spec["slot_bits"]; ns = spec["n_slots"]
    qr = QuantumRegister(n, "q"); cr = ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)
    for i in range(n):
        qc.ry(theta[i], i)
    TEL._entangle(qc, n, "brickwall")
    for (si, sj) in bonds:                # stage 3 = DIRECT long-range CX (the ideal)
        qc.cx(si * sb, sj * sb)
    ab, sb_ = env["angle_bias"], env["season_bias"]
    for s in range(ns):
        b = s * sb
        qc.rx(ab, b + 0); qc.rx(ab, b + 1)
        qc.ry(sb_, b + 2); qc.ry(sb_, b + 3); qc.ry(sb_, b + 4)
        qc.ry(TEL.FORK_BIAS, b + 4); qc.ry(TEL.LEAF_BIAS, b + 5)
    for i in range(n):
        if kick[i]:
            qc.rx(kick[i], i)
    qc.measure(qr, cr)
    return qc

def ideal_sign(d, gens, shots):
    ns = d + 1; spec = spec_for(ns); n = spec["n_bits"]; bonds = [(0, d)]
    print(f"\n=== B. IDEAL bond sign (direct CX), d={d*SB}q ({ns} slots={n}q), {gens} gens, {shots} shots ===")
    theta = [math.pi / 2] * n; kick = [0.0] * n
    env_sched, _ = TEL.build_env(gens)
    vals = []
    for g in range(gens):
        env = env_sched[g]
        qc = build_ideal(theta, kick, env, spec, bonds)
        counts = SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
        fields = [k[::-1] for k, c in counts.items() for _ in range(c)]
        cd = TEL.bond_correlations(fields, n, bonds, SB)[0]["c_at_d"]
        p, *_ = TEL.field_stats(fields, n)
        vals.append(cd)
        print(f"  gen{g}: ideal c(d) = {cd:+.4f}")
        theta, kick = TEL.next_belief(theta, p, n)
    m = float(np.mean(vals))
    sgn = "POSITIVE" if m > 0.003 else ("NEGATIVE" if m < -0.003 else "~0")
    print(f"  MEAN ideal c(d) = {m:+.4f}  => {sgn}")
    return m

if __name__ == "__main__":
    t = time.time()
    unit_test()
    ideal_sign(2, 4, 20000)
    print(f"\n[total {time.time()-t:.1f}s]")
