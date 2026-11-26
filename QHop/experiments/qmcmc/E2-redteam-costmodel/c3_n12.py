"""E2 claim 3(c): does the D9 basin-difference(+50% local) / full-QeMCMC gap ratio (0.72-0.83 at n<=10) hold at SK n=12?
Exact (Lanczos) gaps, ideal. Reuses D9 d9lib unmodified. Usage: python c3_n12.py SEED [SEED...] -> results/c3_n12_s{SEED}.json"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D9-mask-library")
import d9lib as D  # noqa
from d9lib import qmc  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
n = 12
for seed in map(int, sys.argv[1:]):
    t0 = time.time()
    J, h = qmc.sk_instance(n, seed)
    E = qmc.ising_energies(J, h)
    bgrid = np.round(np.geomspace(0.05, 5, 41), 4)
    C = qmc.thermo(E, n, bgrid)
    bc = float(bgrid[C.argmax()])
    ga, ts = D.layden_params(seed, 16)
    Q, _ = D.quantum_and_decohered_Q(E, ga, ts, want_dec=False)
    tq = time.time() - t0
    basin = D.greedy_minima_law(E, n)
    Mb = D.clean(D.xor_autocorr(basin))
    Ml = D.local_law(n)
    Mb_lib = D.library(Mb, 1024, 100000 * seed + 10 * 1024 + 1)
    rows = []
    for bl, b in (("0.3", 0.3), ("bc", bc), ("1", 1.0), ("3", 3.0)):
        r = dict(blabel=bl, beta=b)
        r["qFull"] = D.gap_Q(Q, E, b)
        r["basin_mix"] = D.gap_mask(D.mix(Ml, Mb), E, b)
        r["basin_mix_L1024"] = D.gap_mask(D.mix(Ml, Mb_lib), E, b)
        r["local"] = D.gap_mask(Ml, E, b)
        r["ratio_mix_over_q"] = r["basin_mix"] / r["qFull"]
        r["ratio_L1024_over_q"] = r["basin_mix_L1024"] / r["qFull"]
        rows.append(r)
        print(seed, bl, {k: round(v, 4) for k, v in r.items() if k.startswith("ratio")}, f"{time.time()-t0:.0f}s", flush=True)
    json.dump(dict(n=n, seed=seed, beta_c=bc, n_minima=int((basin > 0).sum()), t_Q_s=tq, t_s=time.time() - t0,
                   rows=rows), open(os.path.join(HERE, "results", f"c3_n12_s{seed}.json"), "w"), indent=1)
