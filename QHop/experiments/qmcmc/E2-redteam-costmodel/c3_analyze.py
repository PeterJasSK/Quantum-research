"""E2 claim 3(a) analysis of results/c3_bench.jsonl -> results/c3_table.txt.
Per (family,size,regime,method): median over 5 instances of tau_sec (IAT x CPU s per record) for E and |q|, resolved
count, median <E> and <|q|> (trapping check vs PT), CPU s per record. Win/lose per instance for mask vs best of
(metro, pt), censoring as D7: counts FOR mask only if mask resolved, AGAINST only if competitor resolved."""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(os.path.join(HERE, "results", "c3_bench.jsonl"))]
key = lambda r: (r["fam"], r["size"], r["regime"])
cells = sorted({key(r) for r in R}, key=lambda k: (k[0], k[1], k[2] != "MEDIUM"))
L = ["fam size regime method | tauE_s med  resE | tauq_s med  resq | <E> med   <|q|> med | s/rec    | t_lib_s | extra"]
wins = {}
for c in cells:
    for m in ("metro", "pt", "mask", "ptmask"):
        rs = [r for r in R if key(r) == c and r["method"] == m]
        if not rs:
            continue
        ex = f"acc_mask {np.median([r['acc_mask'] for r in rs]):.3f}" if "acc_mask" in rs[0] and m == "mask" else (
            f"swap {np.median([r['swap'] for r in rs]):.2f} R={rs[0]['R']}" if "swap" in rs[0] else "")
        L.append(f"{c[0]} {c[1]:3d} {c[2]:6s} {m:6s} | {np.median([r['tauE_sec'] for r in rs]):.2e} {sum(r['resE'] for r in rs)}/5"
                 f" | {np.median([r['tauq_sec'] for r in rs]):.2e} {sum(r['resq'] for r in rs)}/5 | "
                 f"{np.median([r['meanE'] for r in rs]):8.2f} {np.median([r['meanq'] for r in rs]):.3f} | "
                 f"{np.median([r['sec_per_rec'] for r in rs]):.1e} | {np.median([r['t_lib'] for r in rs]):.3f} | {ex}"
                 f" | minima {int(np.median([r['n_unique_minima'] for r in rs]))}/256 masklen {np.median([r['mean_mask_len'] for r in rs]):.1f}")
    for obs in ("E", "q"):
        for seed in range(1, 6):
            g = {r["method"]: r for r in R if key(r) == c and r["seed"] == seed}
            if "mask" not in g:
                continue
            comp = [g[m] for m in ("metro", "pt") if m in g]
            best = min(comp, key=lambda r: r[f"tau{obs}_sec"])
            mk = g["mask"]
            if mk[f"tau{obs}_sec"] < best[f"tau{obs}_sec"] and mk[f"res{obs}"]:
                v = "win"
            elif mk[f"tau{obs}_sec"] >= best[f"tau{obs}_sec"] and best[f"res{obs}"]:
                v = "lose"
            else:
                v = "undet"
            wins.setdefault((c[0], c[1], c[2]), []).append((obs, v, mk[f"tau{obs}_sec"] / best[f"tau{obs}_sec"]))
L.append("")
L.append("mask vs best(metro,pt) per CPU second, per instance (obs: verdict ratio tau_mask/tau_best):")
for c, v in wins.items():
    tally = {k: sum(1 for x in v if x[1] == k) for k in ("win", "lose", "undet")}
    L.append(f"{c} {tally} median ratio {np.median([x[2] for x in v]):.1f} range [{min(x[2] for x in v):.1f},{max(x[2] for x in v):.1f}]")
tot = [x for v in wins.values() for x in v]
L.append(f"TOTAL: win {sum(x[1]=='win' for x in tot)} lose {sum(x[1]=='lose' for x in tot)} undet {sum(x[1]=='undet' for x in tot)} of {len(tot)}")
open(os.path.join(HERE, "results", "c3_table.txt"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
