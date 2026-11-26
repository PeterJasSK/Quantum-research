"""Claim B, classical side strengthened: mixtures of exact SW / Wolff with local+uniform (weights 0.25/0.5/0.75),
so the classical 'best' is not just max(single kernel). Reads layden gaps from results/claimB_n{N}.json.
Usage: python claimB_mix.py N   -> results/claimB_mix_n{N}.json"""
import sys, json
import numpy as np
import e1lib as e
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D1-temperature-map")
import d1lib as L  # noqa
qmc = e.qmc
n = int(sys.argv[1])
B = json.load(open(f"results/claimB_n{n}.json"))
full = 2 ** (n + 1) - 1
X = np.arange(2 ** n)
out = []
for r in B:
    inst = r["inst"]
    J, h = qmc.sk_instance(n, 1000 * n + inst); E = qmc.ising_energies(J, h)
    nv, ed = L.graph_from_J(J, h, ghost=True)
    Ql, Qu = qmc.local_Q(n), qmc.uniform_Q(n)
    res = dict(n=n, inst=inst, rows=[])
    for x in r["rows"]:
        b = x["beta"]; pi = L.boltz(E, b); dq = np.sqrt(pi)
        Psw, Pw = e.cluster_kernels(nv, ed, b, X)
        Acl = {}
        for nm, P in (("SW", Psw), ("Wolff", Pw)):
            Pp = P[:, X] + P[:, X ^ full]
            A = (dq[:, None] * Pp) / dq[None, :]
            Acl[nm] = 0.5 * (A + A.T)
        best = (-1, "")
        for wu in (0.0, 0.1, 0.3, 0.5):
            Am = L.mh_sym((1 - wu) * Ql + wu * Qu, E, b)
            for nm, Ac in Acl.items():
                for wc in (0.25, 0.5, 0.75):
                    g = L.gap_sym(wc * Ac + (1 - wc) * Am, pi)
                    if g > best[0]:
                        best = (g, f"{nm}{wc}+mix(u={wu})")
            Asw_w = 0.5 * (Acl["SW"] + Acl["Wolff"])
        g = L.gap_sym(Asw_w, pi)
        if g > best[0]:
            best = (g, "SW+Wolff")
        res["rows"].append(dict(ratio=x["ratio"], beta=b, clmix=best[0], clmix_name=best[1], layden=x["layden"][0],
                                prev_best=max(x["mixbest"][0], x["SW"][0], x["Wolff"][0]),
                                tuned=x.get("tuned", [np.nan])[0]))
    out.append(res)
    print(inst, " ".join(f"r{y['ratio']:.2f}:lay/clmix={y['layden']/y['clmix']:.2f}({y['clmix_name']}),gain={y['clmix']/y['prev_best']:.2f}" for y in res["rows"]), flush=True)
json.dump(out, open(f"results/claimB_mix_n{n}.json", "w"))
gm = [np.exp(np.mean([np.log(y["layden"] / y["clmix"]) for y in rr["rows"]])) for rr in out]
gt = [np.exp(np.mean([np.log(y["tuned"] / y["clmix"]) for y in rr["rows"]])) for rr in out]
print(f"n={n} MEDIUM layden/best(incl cluster mixtures) median {np.median(gm):.3g} IQR [{np.percentile(gm,25):.3g},{np.percentile(gm,75):.3g}]"
      f" tuned/best {np.nanmedian(gt):.3g}")
