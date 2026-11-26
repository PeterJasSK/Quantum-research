"""CZ count of the palindromic 2nd-order XY-mixer Trotter circuit at n=12 (qiskit 2.3 transpile, optimization_level=3,
seed_transpiler=0..2, best kept). Per step: RZZ(all energy pairs)/2, palindromic XX+YY layers, RZZ/2. Energy graph:
'cuau' = 48 NN+NNN pairs of the 3x4 torus; 'dense' = all 66 pairs (Coulomb / SK). Cost model N(r) = N(2) + (r-2)(N(3)-N(2)).
Also analytic all-to-all count (Helios-like, CZ basis: XX+YY = 2 CZ, RZZ = 2 CZ).
Usage: OMP_NUM_THREADS=2 python run_cz.py -> results/cz.json
"""
import json
import time
import warnings

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import XXPlusYYGate
from qiskit_ibm_runtime import fake_provider as fp

import d8lib as L

warnings.simplefilter("ignore")
n, L1, L2 = 12, 3, 4
_, pos, nn, nnn = L.torus(L1, L2)


def round_robin(n):
    cols, others = [], list(range(1, n))
    for r in range(n - 1):
        rot = others[r:] + others[:r]
        cols.append([(0, rot[0])] + [(rot[i], rot[-i]) for i in range(1, n // 2)])
    return cols


MIX = {"ring": L.edge_colouring(L.snake_ring(L1, L2)), "grid": L.edge_colouring(nn), "complete": round_robin(n)}
EN = {"cuau": nn + nnn, "dense": L.complete_edges(n)}


def circuit(mix_layers, epairs, r, th=0.3, ph=0.2):
    qc = QuantumCircuit(n)
    qc.x(range(0, n, 2))
    for _ in range(r):
        for (i, j) in epairs:
            qc.rzz(ph / 2, i, j)
        for Lr in mix_layers[:-1]:
            for (i, j) in Lr:
                qc.append(XXPlusYYGate(th / 2), [i, j])
        for (i, j) in mix_layers[-1]:
            qc.append(XXPlusYYGate(th), [i, j])
        for Lr in mix_layers[-2::-1]:
            for (i, j) in Lr:
                qc.append(XXPlusYYGate(th / 2), [i, j])
        for (i, j) in epairs:
            qc.rzz(ph / 2, i, j)
    qc.measure_all()
    return qc


def n2q(tc):
    ops = tc.count_ops()
    return int(sum(v for kk, v in ops.items() if kk in ("cz", "ecr", "cx", "rzz")))


res = {}
for bname, be in (("heavyhex_FakeMarrakesh", fp.FakeMarrakesh()), ("square_FakeNighthawk", fp.FakeNighthawk())):
    for m, layers in MIX.items():
        for e, ep in EN.items():
            t0 = time.time()
            N = {}
            for r in (2, 3):
                qc = circuit(layers, ep, r)
                N[r] = min(n2q(transpile(qc, be, optimization_level=3, seed_transpiler=s)) for s in range(3))
            inc = N[3] - N[2]
            nmix = sum(len(Lr) for Lr in layers)
            mix_calls = sum(len(Lr) for Lr in layers[:-1]) * 2 + len(layers[-1])
            res[f"{bname}|{m}|{e}"] = dict(N_r2=N[2], N_r3=N[3], per_step=inc,
                                           analytic_alltoall_per_step=2 * mix_calls + 2 * len(ep),
                                           mixer_edges=nmix, energy_pairs=len(ep), secs=round(time.time() - t0, 1))
            print(bname, m, e, N, f"{time.time()-t0:.0f}s", flush=True)
json.dump(res, open("results/cz.json", "w"), indent=1)
