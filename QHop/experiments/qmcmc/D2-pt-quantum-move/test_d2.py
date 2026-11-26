"""Correctness checks + speed benchmark for D2 kernels. Run: python test_d2.py"""
import time
import numpy as np
import d2lib as L
import qmc

out = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    out.append(s)


# 1) Chebyshev quantum row vs exact qmc.quantum_Q (n=8 SK, same 16-pair pool)
inst = L.Instance("sk", 8, 8)
g, ts = L.pool(0)
Qex = qmc.quantum_Q(inst.E, np.repeat(g, 4), ts.reshape(-1), alpha=inst.alpha)
qs = L.QSampler(inst)
err = max(np.abs(qs.row(a) - Qex[a]).max() for a in range(0, 256, 17))
log("quantum row max abs err vs qmc.quantum_Q (n=8):", err)
# single-shot sampler histogram vs row
a = 5
cnt = np.bincount([qs.single(a) for _ in range(20000)], minlength=256) / 20000
log("single-sample TV distance vs exact row (20000 draws, n=8):", 0.5 * np.abs(cnt - Qex[a]).sum())
log("symmetry of Q_m (exact, n=8):", qmc.asymmetry(Qex))

# 2) decohered walk histogram vs qmc.decohered_Q (n=8)
Dex = np.zeros((256, 256))
for gg, tg in zip(g, ts):
    Dex += qmc.decohered_Q(inst.E, [gg] * 4, tg, alpha=inst.alpha) * 4
Dex /= 16
ds = L.DSampler(inst)
cnt = np.bincount([ds.propose(a) for _ in range(20000)], minlength=256) / 20000
log("decohered TV distance vs qmc.decohered_Q (20000 draws, n=8):", 0.5 * np.abs(cnt - Dex[a]).sum(),
    "leak/substep", ds.stats()["mean_leak_per_substep"])
# sampling noise floor for 20000 draws
ref = np.random.default_rng(1).choice(256, 20000, p=Dex[a] / Dex[a].sum())
log("  sampling-noise TV floor (exact draws):", 0.5 * np.abs(np.bincount(ref, minlength=256) / 20000 - Dex[a]).sum())

# 3) Metropolis, PT, PT+Houdayer, quantum chain reproduce exact <E> (n=12)
for fam in ["sk", "ea"]:
    inst = L.Instance(fam, 16 if fam == "ea" else 12, 3)
    bc, _ = inst.beta_c()
    b = 2 * bc
    Eex, _ = inst.exact(b)
    E, q = L.metro(inst, b, 4_000_000, inst.n, 1)
    log(fam, "n", inst.n, "beta", round(b, 3), "exact <E>", round(Eex, 3), "metro", round(E[len(E) // 5:].mean(), 3))
    betas = np.geomspace(0.3 * bc, b, 6)
    pt = L.PT(inst, betas, 2)
    E, q = pt.run(50000)
    log("   PT", round(E[10000:].mean(), 3), "swap", np.round(pt.swap_rates(), 2))
    pt = L.PT(inst, betas, 2, ncopy=2, houdayer=True)
    E, q = pt.run(50000)
    log("   PT+Houdayer", round(E[10000:].mean(), 3), "mean cluster", pt.hstat[1] / max(pt.hstat[0], 1),
        "exact <|q_gs|>", round(inst.exact_q(b), 3), "PT+H <|q|>", round(q[10000:].mean(), 3))
    if inst.n <= 12:
        qs = L.QSampler(inst)
        E, q, acc = L.qchain(inst, qs, b, 6000, 4)
        log("   QeMCMC", round(E[1000:].mean(), 3), "acc", round(acc, 3), qs.stats())

# 4) speed of quantum proposal (single (gamma,t) evolution + one sample; full 16-pair row) and decohered walk
for n in [12, 14, 16, 18]:
    inst = L.Instance("sk", n, 1)
    qs = L.QSampler(inst)
    t0 = time.time()
    for k in range(3):
        qs.single(k)
    ts1 = (time.time() - t0) / 3
    t0 = time.time()
    qs.row(7)
    tr = time.time() - t0
    ds = L.DSampler(inst)
    t0 = time.time()
    for k in range(20):
        ds.propose(k)
    td = (time.time() - t0) / 20
    log(f"speed n={n}: single-shot quantum proposal {ts1:.3f} s, full row {tr:.3f} s, decohered proposal {td:.4f} s,"
        f" Chebyshev K per gamma {[p['K'] for p in qs.par]}")
open("test_d2_output.txt", "w").write("\n".join(out) + "\n")
