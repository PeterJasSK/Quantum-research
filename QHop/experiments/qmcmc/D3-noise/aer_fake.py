"""D3 (v): device-calibrated noise (FakeMarrakesh Heron r2 / FakeBoston Heron r3), EXACT output probabilities.

For every basis input the transpiled Trotter circuit (same palindromic logical circuit as dmsim) is run on
AerSimulator(method='density_matrix', noise_model=NoiseModel.from_backend) with save_probabilities
(no shots). Readout error is applied analytically per physical qubit from the backend properties.
Gauge pair {0, all-ones}: literal gauge-transformed problem, relabelled.
python aer_fake.py --backend marrakesh --n 6 --seed 100
Output: cache/fake_<backend>_n<n>_s<seed>.npz  (Q_noRO, Q_RO, Q_gp_noRO, Q_gp_RO, counts)
"""
import argparse
import os
import time
import warnings
import numpy as np
import dmsim as D
import qmc

warnings.simplefilter("ignore")
from qiskit import QuantumCircuit, transpile                    # noqa: E402
from qiskit_aer import AerSimulator                              # noqa: E402
from qiskit_aer.noise import NoiseModel                          # noqa: E402
from qiskit_ibm_runtime import fake_provider as fp               # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--backend", default="marrakesh")
ap.add_argument("--n", type=int, default=6)
ap.add_argument("--seed", type=int, default=100)
ap.add_argument("--gammas", default="0.3,0.5")
ap.add_argument("--ts", default="2")
ap.add_argument("--nogauge", action="store_true")
a = ap.parse_args()
B = {"marrakesh": fp.FakeMarrakesh, "boston": fp.FakeBoston}[a.backend]()
nm = NoiseModel.from_backend(B)
sim = AerSimulator(method="density_matrix", noise_model=nm, max_parallel_threads=2)
J, h = qmc.sk_instance(a.n, a.seed)
n, d = a.n, 2 ** a.n
grid = [(float(g), float(t)) for g in a.gammas.split(",") for t in a.ts.split(",")]


def logical_circuit(units):
    qc = QuantumCircuit(n)
    for u in units:
        if u[0] == "zz":
            qc.rzz(u[3], u[1], u[2])
        elif u[0] == "z":
            qc.rz(u[2], u[1])
        else:
            qc.rx(u[2], u[1])
    return qc


def Q_for(Jx, hx, g, t, seed=7):
    units, _ = D.trotter_units(Jx, hx, g, t)
    body = logical_circuit(units)
    body.measure_all()
    tq = transpile(body, B, optimization_level=1, seed_transpiler=seed)
    # physical qubit measured into clbit k (= logical qubit k)
    meas = {}
    for ins in tq.data:
        if ins.operation.name == "measure":
            meas[tq.find_bit(ins.clbits[0]).index] = tq.find_bit(ins.qubits[0]).index
    phys_out = [meas[k] for k in range(n)]
    init = tq.layout.initial_layout
    vq = body.qubits
    phys_in = [init[vq[k]] for k in range(n)]
    core = tq.copy_empty_like()
    for ins in tq.data:
        if ins.operation.name not in ("measure", "barrier"):
            core.append(ins)
    circs = []
    for x in range(d):
        c = core.copy_empty_like()
        for k in range(n):
            if (x >> k) & 1:
                c.x(phys_in[k])
        c.compose(core, inplace=True)
        c.save_probabilities(phys_out)
        circs.append(c)
    res = sim.run(circs).result()
    Q = np.array([res.data(i)["probabilities"] for i in range(d)])
    ops = tq.count_ops()
    ro = [(B.properties().qubit_property(q, "prob_meas1_prep0")[0],
           B.properties().qubit_property(q, "prob_meas0_prep1")[0]) for q in phys_out]
    return Q, ops.get("cz", 0), tq.depth(), ro


def apply_ro(Q, ro):
    T = Q.reshape((d,) + (2,) * n)
    for q, (p01, p10) in enumerate(ro):
        M = np.array([[1 - p01, p01], [p10, 1 - p10]])
        ax = 1 + (n - 1 - q)
        T = np.moveaxis(np.tensordot(T, M, axes=([ax], [0])), -1, ax)
    return T.reshape(d, d)


os.makedirs("cache", exist_ok=True)
t0 = time.time()
out = {}
per = {}
for m in ([0] if a.nogauge else [0, d - 1]):
    Jm, hm = D.gauge(J, h, m)
    acc, accro, cz, dep = 0, 0, [], []
    for g, t in grid:
        Q, c, dp, ro = Q_for(Jm, hm, g, t)
        acc = acc + D.relabel(Q, m)
        accro = accro + D.relabel(apply_ro(Q, ro), m)   # readout on gauge-transformed physical bits
        cz.append(c)
        dep.append(dp)
    per[m] = (acc / len(grid), accro / len(grid), cz, dep)
out["Q_noRO"], out["Q_RO"], out["cz"], out["depth"] = per[0][0], per[0][1], np.array(per[0][2]), np.array(per[0][3])
if not a.nogauge:
    out["Q_gp_noRO"] = 0.5 * (per[0][0] + per[d - 1][0])
    out["Q_gp_RO"] = 0.5 * (per[0][1] + per[d - 1][1])
    out["cz_gp"] = np.array(per[d - 1][2])
out["ro"] = np.array(ro)
out["grid"] = np.array(grid)
out["sec"] = time.time() - t0
np.savez_compressed(f"cache/fake_{a.backend}_n{n}_s{a.seed}.npz", **out)
print(a.backend, n, a.seed, "sec %.0f" % out["sec"], "cz", out["cz"],
      {k: round(qmc.asymmetry(v), 5) for k, v in out.items() if k.startswith("Q")})
