"""Main head-to-head run: equal CPU budget per (instance, target, method).
usage: python run_exp.py FAMILY SIZE [budget_s] [seeds]
Writes results/runs/<inst>_<target>_<method>.json (summary + thinned trace)."""
import json, os, sys
import numpy as np
import cg, qmc

fam, size = sys.argv[1], int(sys.argv[2])
B = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
seeds = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else [1, 2, 3, 4, 5]
CFG = json.load(open(os.path.join(cg.HERE, "config.json")))
TUNE = json.load(open(os.path.join(cg.HERE, "results", f"pt_tuning_{fam}.json")))
CFG[fam]["R"] = {sz: {t: v["R"] for t, v in d.items()} for sz, d in TUNE.items()}
if fam == "ea":  # MEDIUM was tuned at T=1.0, then moved to T=0.8 (Metropolis IAT ~100): keep d(ln beta) per step
    for sz in CFG[fam]["R"]:
        r0 = CFG[fam]["R"][sz]["MEDIUM"]
        CFG[fam]["R"][sz]["MEDIUM"] = int(np.ceil(r0 * np.log(CFG[fam]["pt_Tmax"] / CFG[fam]["T"]["MEDIUM"])
                                                  / np.log(CFG[fam]["pt_Tmax"] / CFG[fam]["pt_tuned_T_MEDIUM"])))
os.makedirs(os.path.join(cg.HERE, "results", "runs"), exist_ok=True)
os.makedirs(os.path.join(cg.HERE, "results", "refs"), exist_ok=True)


def betas_for(n):
    fc = CFG[fam]
    if fam == "sk":
        return {t: v / np.sqrt(n) for t, v in fc["beta_over_betac"].items()}, fc["pt_bmin_over_betac"] / np.sqrt(n)
    return {t: 1.0 / v for t, v in fc["T"].items()}, 1.0 / fc["pt_Tmax"]


def summarize(r, n, k, kind):
    E, H, T = r["E"], r["H"].astype(float) / n, r["T"]
    N = len(E); b = N // 4
    tE, tH = qmc.iat(E[b:]), qmc.iat(H[b:])
    sec_per_rec = r["cpu"] / max(N, 1)
    mpr = r.get("moves_per_rec", 1)
    out = dict(nrec=N, cpu=r["cpu"], sec_per_rec=sec_per_rec, moves_per_rec=mpr,
               tauE_rec=tE, tauH_rec=tH, tauE_moves=tE * mpr if tE == tE else None,
               tauH_moves=tH * mpr if tH == tH else None, tauE_sec=tE * sec_per_rec, tauH_sec=tH * sec_per_rec,
               resolvedE=bool(tE == tE and (N - b) / tE >= 50), resolvedH=bool(tH == tH and (N - b) / tH >= 50),
               Emean2=float(E[N // 2:].mean()), Hmean2=float(H[N // 2:].mean()), Emin=float(E.min()))
    th = max(1, N // 4000)
    out["trace"] = dict(T=T[::th].tolist(), E=E[::th].tolist(), H=H[::th].tolist())
    return out


def save(name, d):
    json.dump(d, open(os.path.join(cg.HERE, "results", "runs", name + ".json"), "w"))


for seed in seeds:
    inst = cg.Inst(fam, size, seed)
    n = inst.n
    tb, bmin = betas_for(n)
    # reference configuration: lowest-energy state of a PT(+Houdayer for EA) run at the LOW ladder
    refp = os.path.join(cg.HERE, "results", "refs", inst.name + ".json")
    R_low = CFG[fam]["R"][str(size)]["LOW"]
    if not os.path.exists(refp):
        lad = np.geomspace(bmin, tb["LOW"], R_low)
        hf = int(np.searchsorted(lad, 1.0)) if fam == "ea" else len(lad)
        rr = cg.pt(inst, lad, R_low - 1, 2.5 * B, 999 + seed, houdayer=(fam == "ea"), houd_from=hf)
        Es = [inst.energy(s) for s in rr["S"]]
        s_ref = rr["S"][int(np.argmin(Es))].astype(int)
        json.dump(dict(E_ref_state=float(min(Es)), s_ref=s_ref.tolist()), open(refp, "w"))
    ref = json.load(open(refp))
    sref = np.array(ref["s_ref"], np.int32)
    for target, beta in tb.items():
        common = dict(inst=inst.name, family=fam, size=size, n=n, seed=seed, target=target, beta=beta,
                      budget=B, E_ref_state=ref["E_ref_state"])
        jobs = [("metro", 0, "none")]
        for k, gm in CFG["hb_jobs"]:
            jobs.append(("hb", k, gm))
        for k, gm in CFG["q_jobs"]:
            jobs.append(("q", k, gm))
        for k, gm in CFG["dec_jobs"]:
            jobs.append(("dec", k, gm))
        for (m, k, gm) in jobs:
            name = f"{inst.name}_{target}_{m}_k{k}_{gm}"
            if os.path.exists(os.path.join(cg.HERE, "results", "runs", name + ".json")):
                continue
            if m == "metro":
                r = cg.chain(inst, "metro", beta, B, 10 * seed + 1, sref=sref)
            else:
                r = cg.chain(inst, m, beta, B, 10 * seed + 2, k=k, gmode=gm, sref=sref)
            d = dict(common, method=m, k=k, group=gm, acc=r["acc"] / max(r["moves"], 1), moves=r["moves"],
                     cheb=r["cheb"], us_per_move=1e6 * r["cpu"] / max(r["moves"], 1))
            d.update(summarize(r, n, k, m))
            save(name, d)
            print(name, "tauE_sec=%.3g res=%s" % (d["tauE_sec"], d["resolvedE"]), flush=True)
        if target == "HIGH":
            continue
        for hd in ([False, True] if fam == "ea" else [False]):
            name = f"{inst.name}_{target}_pt{'h' if hd else ''}_k0_none"
            if os.path.exists(os.path.join(cg.HERE, "results", "runs", name + ".json")):
                continue
            R = CFG[fam]["R"][str(size)][target]
            lad = np.geomspace(bmin, beta, R)
            hf = int(np.searchsorted(lad, 1.0)) if fam == "ea" else R
            r = cg.pt(inst, lad, R - 1, B, 10 * seed + 3, houdayer=hd, houd_from=hf, sref=sref)
            d = dict(common, method="pth" if hd else "pt", k=0, group="none", R=R, swap=r["swap"].tolist(),
                     moves=r["sweeps"], us_per_move=1e6 * r["cpu"] / max(r["sweeps"], 1), houd_size=r["houd_size"])
            d.update(summarize(r, n, 0, "pt"))
            save(name, d)
            print(name, "tauE_sec=%.3g res=%s minswap=%.2f" % (d["tauE_sec"], d["resolvedE"], min(r["swap"])),
                  flush=True)
