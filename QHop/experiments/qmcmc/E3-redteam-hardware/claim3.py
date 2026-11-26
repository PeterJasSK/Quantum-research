"""Claim 3 attack: can a Heron calibration run (proposal-matrix tomography, or a sequential chain) resolve S>1 within
<= $500? Uses noisy n=8 native-subset Q (claim2, global depolarizing at D4 CZ counts) and exact FakeMarrakesh n=6 Q (D3).
Shot model: N shots per start state (each shot a random (gamma,t) draw), Q_hat row = multinomial/N, symmetrised
(Q_hat+Q_hat^T)/2 with diagonal fixed (rows sum to 1) -> reversible plain-MH estimate. 20 replicas per N.
Cost model [own estimate]: 0.3 ms per shot (250 us rep delay + circuit), $96 per QPU minute.
-> results/claim3.json"""
import json

import numpy as np

import e3lib as L
qmc = L.qmc
D4 = "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D4-compilation"
import sys; sys.path.insert(0, D4)
import d4lib as D  # noqa: E402

SHOT_S, USD_MIN = 3e-4, 96.0
rng = np.random.default_rng(7)


def est_Q(Q, N):
    C = np.array([rng.multinomial(N, Q[a] / Q[a].sum()) for a in range(len(Q))], float) / N
    S = 0.5 * (C + C.T)
    np.fill_diagonal(S, 0.0)
    S = np.minimum(S, 1.0)
    sc = np.maximum(S.sum(1), 1.0)
    S = S / sc[:, None] if np.any(sc > 1) else S
    np.fill_diagonal(S, 1.0 - S.sum(1))
    return S


out = {"tomography": [], "chain": []}
cases = []
Z = np.load("results/claim2_Q_n8.npz")
for seed in range(5):
    J, h = D.fam_sk(8, seed)
    cases.append((f"n8_native_short_s{seed}", qmc.ising_energies(J, h), Z[f"s{seed}_noisy_short"], 8, 1.0))
D3 = "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D3-noise/"
inst = {(r["n"], r["seed"]): r for r in json.load(open(D3 + "results/instances.json")) if r["source"] == "exactDM"}
for seed in (100, 101, 102):
    J, h = qmc.sk_instance(6, seed)
    cases.append((f"n6_marrakesh_s{seed}", qmc.ising_energies(J, h), np.load(D3 + f"cache/fake_marrakesh_n6_s{seed}.npz")["Q_RO"],
                  6, inst[(6, seed)]["beta_LOW"]))

for name, E, Q, n, b in cases:
    gc, _, _ = L.best_mix(E, b, n)
    S_true = qmc.gap(Q, E, b) / gc
    for N in (64, 256, 1024, 4096, 16384):
        Sh = [qmc.gap(est_Q(Q, N), E, b) / gc for _ in range(20)]
        shots = N * 2 ** n
        usd = shots * SHOT_S / 60 * USD_MIN
        r = dict(case=name, beta=b, S_true=S_true, N_per_row=N, total_shots=shots, usd=usd,
                 S_hat_mean=float(np.mean(Sh)), S_hat_sd=float(np.std(Sh)))
        out["tomography"].append(r)
        print(name, "S_true %.3f N %5d shots %.2e $%.0f  S_hat %.3f +- %.3f" % (S_true, N, shots, usd, r["S_hat_mean"],
                                                                         r["S_hat_sd"]), flush=True)

# sequential chain: 1000 steps (~1 job/step); IAT of energy, quantum vs best mixture, 100 replicas
for name, E, Q, n, b in cases[:5]:
    _, w, _ = L.best_mix(E, b, n)
    Qc = qmc.mixture_Q([qmc.local_Q(n), qmc.uniform_Q(n)], [w + 1e-12, 1 - w + 1e-12])
    tq = [qmc.iat(E[qmc.run_chain(Q, E, b, 1000, s)]) for s in range(100)]
    tc = [qmc.iat(E[qmc.run_chain(Qc, E, b, 1000, 10_000 + s)]) for s in range(100)]
    tq, tc = np.array(tq), np.array(tc)
    ok = np.isfinite(tq) & np.isfinite(tc)
    r = dict(case=name, iat_q_med=float(np.nanmedian(tq)), iat_q_cv=float(np.nanstd(tq) / np.nanmean(tq)),
             iat_c_med=float(np.nanmedian(tc)), iat_c_cv=float(np.nanstd(tc) / np.nanmean(tc)),
             frac_q_faster=float(np.mean(tq[ok] < tc[ok])))
    out["chain"].append(r)
    print("chain", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
json.dump(out, open("results/claim3.json", "w"), indent=1)
