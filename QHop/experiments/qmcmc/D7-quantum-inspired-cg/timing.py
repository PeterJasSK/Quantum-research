"""CPU time per move for every move type (C kernels) + python/scipy reference for the quantum move."""
import json, os, time
import numpy as np
from scipy.sparse.linalg import expm_multiply
from scipy.linalg import eigh
import scipy.sparse as sp
import cg, qmc
rows = []
for fam, size in [("sk", 32), ("sk", 64), ("sk", 128), ("ea", 8), ("ea", 12), ("ea", 16)]:
    inst = cg.Inst(fam, size, 1)
    n = inst.n
    beta = (1.0 / np.sqrt(n)) if fam == "sk" else 1.0
    r = cg.chain(inst, "metro", beta, 1.0, 1, moves_per_rec=10)
    rows.append(dict(inst=inst.name, n=n, move="metro_sweep", k=0, us_per_move=1e6 * r["cpu"] / r["moves"],
                     ns_per_spin_attempt=1e9 * r["cpu"] / r["moves"] / n))
    for m in ["hb", "q", "dec"]:
        for k in [4, 8, 12]:
            tl = 1.5
            r = cg.chain(inst, m, beta, tl, 1, k=k, gmode="block", moves_per_rec=1)
            rows.append(dict(inst=inst.name, n=n, move=m, k=k, us_per_move=1e6 * r["cpu"] / r["moves"],
                             cheb_terms=r["cheb"], acc=r["acc"] / r["moves"]))
    print(inst.name, "done", flush=True)
# scipy references for one quantum group move (diag from random group energies)
ref = []
rng = np.random.default_rng(0)
for k in [4, 8, 12]:
    D = 2 ** k
    Hm = sp.csr_matrix(qmc.mixer(k)) if k <= 12 else None
    d = rng.normal(size=D) * np.sqrt(k)
    gam, t = 0.4, 11.0
    v = np.zeros(D); v[0] = 1
    t0 = time.process_time(); reps = 5 if k == 12 else 50
    for _ in range(reps):
        H = sp.diags(d * (1 - gam)) + gam * Hm
        expm_multiply(-1j * t * H, v.astype(complex))
    t_em = (time.process_time() - t0) / reps
    t0 = time.process_time(); reps2 = 1 if k == 12 else 20
    for _ in range(reps2):
        eigh(np.diag(d) + gam * qmc.mixer(k))
    t_eigh = (time.process_time() - t0) / reps2
    ref.append(dict(k=k, scipy_expm_multiply_us=1e6 * t_em, scipy_dense_eigh_us=1e6 * t_eigh))
json.dump(dict(rows=rows, scipy_ref=ref), open("results/timing.json", "w"), indent=1)
import csv
with open("results/timing.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["inst", "n", "move", "k", "us_per_move", "ns_per_spin_attempt", "cheb_terms", "acc"])
    w.writeheader(); [w.writerow(r) for r in rows]
for r in rows: print(r["inst"], r["move"], r["k"], "%.2f us" % r["us_per_move"], "cheb %.0f" % r.get("cheb_terms", 0))
print(ref)
