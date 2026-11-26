"""D3 symmetry checks (exact DM, complex128): which noise keeps Q = Q^T, and do gauge / twirl fixes work?
python symmetry_checks.py  -> results/symmetry_checks.json
Instances: SK n=4 seed 1 and n=6 seed 100, single grid point gamma=0.4, t=3 (r=7 Strang steps).
"""
import json
import numpy as np
import dmsim as D
import qmc

res = []
for n, seed in [(4, 1), (6, 100)]:
    J, h = qmc.sk_instance(n, seed)
    u, _ = D.trotter_units(J, h, 0.4, 3.0)
    u1, _ = D.trotter_units(J, h, 0.4, 3.0, order="first")
    U, U1 = D.ideal_unitary(u, n), D.ideal_unitary(u1, n)
    Qi = np.abs(U) ** 2
    res.append(dict(n=n, case="ideal 2nd-order palindromic", palindrome=D.is_palindrome(u),
                    max_abs_U_minus_UT=float(np.abs(U - U.T).max()), asym=qmc.asymmetry(Qi)))
    res.append(dict(n=n, case="ideal 1st-order (control)", palindrome=D.is_palindrome(u1),
                    max_abs_U_minus_UT=float(np.abs(U1 - U1.T).max()), asym=qmc.asymmetry(np.abs(U1) ** 2)))
    for e in (1e-3, 1e-2):
        for name, nz in [("dep", dict(dep2=4 / 3 * e, dep1=e / 5)), ("deph", dict(deph2=e, deph1=e / 10)),
                         ("ad", dict(ad2=e, ad1=e / 10)), ("ad_pauli_twirl", dict(ad2=e, ad1=e / 10, twirl_ad=True))]:
            for pl in ("after", "split"):
                Q = D.noisy_Q(u, n, nz, pl)
                res.append(dict(n=n, case=name, eps=e, placement=pl, asym=qmc.asymmetry(Q)))
        nz = dict(ad2=e, ad1=e / 10)
        for pl in ("after", "split"):
            masks = range(2 ** n) if n <= 4 else [0, 2 ** n - 1]
            Qm = {}
            for m in masks:                      # literal gauge transform of the problem, then relabel
                Jm, hm = D.gauge(J, h, m)
                um, _ = D.trotter_units(Jm, hm, 0.4, 3.0)
                Qm[m] = D.relabel(D.noisy_Q(um, n, nz, pl), m)
            res.append(dict(n=n, case="ad gauge pair {0,1..1}", eps=e, placement=pl,
                            asym=qmc.asymmetry(0.5 * (Qm[0] + Qm[2 ** n - 1])), asym_unfixed=qmc.asymmetry(Qm[0])))
            if n <= 4:
                res.append(dict(n=n, case="ad gauge full 2^n masks", eps=e, placement=pl,
                                asym=qmc.asymmetry(np.mean(list(Qm.values()), 0))))
    for p in (1e-2, 5e-2):
        res.append(dict(n=n, case="readout symmetric", eps=p, asym=qmc.asymmetry(D.readout_apply(Qi, n, p, p))))
        res.append(dict(n=n, case="readout asym (0.5p,1.5p)", eps=p, asym=qmc.asymmetry(D.readout_apply(Qi, n, .5 * p, 1.5 * p))))
        res.append(dict(n=n, case="readout twirl+mirrored pre-flip", eps=p,
                        asym=qmc.asymmetry(D.prep_apply(D.readout_apply(Qi, n, p, p), n, p, p))))
    print(n, "done", flush=True)
json.dump(res, open("results/symmetry_checks.json", "w"), indent=1)
for r in res:
    print({k: (f"{v:.2e}" if isinstance(v, float) else v) for k, v in r.items()})
