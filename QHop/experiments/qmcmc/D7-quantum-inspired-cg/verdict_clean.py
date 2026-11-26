"""Censoring-aware verdict. Unresolved IATs (N_post/tau < 50) are only lower bounds, so a ratio comp/q is
valid evidence FOR q only if q is resolved, and AGAINST q only if the competitor is resolved.
Classes per (instance,target,q-config,observable,competitor): QBETTER / QWORSE / UNDETERMINED."""
import csv, collections
import numpy as np
rows = list(csv.DictReader(open("results/summary_runs.csv")))
for r in rows:
    for kk in ["tauE_moves", "tauH_moves", "tauE_sec", "tauH_sec"]: r[kk] = float(r[kk])
    r["resE"] = int(r["resE"]); r["resH"] = int(r["resH"])
by = collections.defaultdict(list)
for r in rows: by[(r["inst"], r["target"])].append(r)
def cls(comp, q, o, unit):
    a, b = comp[f"tau{o}_{unit}"], q[f"tau{o}_{unit}"]
    rc, rq = comp[f"res{o}"], q[f"res{o}"]
    if a > b and rq: return "QBETTER", a / b
    if a < b and rc: return "QWORSE", a / b
    if a == b and rc and rq: return "QWORSE", 1.0
    return "UNDET", a / b
out = collections.defaultdict(collections.Counter)
best_for_q = []
for (inst, tgt), xs in by.items():
    fam = xs[0]["family"]
    cl = [x for x in xs if x["method"] in ("metro", "pt", "pth")]
    hb = {(x["k"], x["group"]): x for x in xs if x["method"] == "hb"}
    for q in xs:
        if q["method"] not in ("q", "dec"): continue
        for o in "EH":
            h = hb[(q["k"], q["group"])]
            c1, r1 = cls(h, q, o, "moves"); out[(fam, tgt, q["method"], "vs_HBsamegroup_perstep")][c1] += 1
            c2, r2 = cls(h, q, o, "sec"); out[(fam, tgt, q["method"], "vs_HBsamegroup_persec")][c2] += 1
            bhb = min(hb.values(), key=lambda x: x[f"tau{o}_sec"])
            c3, r3 = cls(bhb, q, o, "sec"); out[(fam, tgt, q["method"], "vs_bestHB_persec")][c3] += 1
            # best classical = smallest tau among metro/pt/pth; q better only if better than ALL of them
            cs = [cls(c, q, o, "sec") for c in cl]
            if all(c[0] == "QBETTER" for c in cs): c4 = "QBETTER"
            elif any(c[0] == "QWORSE" for c in cs): c4 = "QWORSE"
            else: c4 = "UNDET"
            out[(fam, tgt, q["method"], "vs_bestMetroPT_persec")][c4] += 1
            if "QBETTER" in (c2, c3, c4) or c1 == "QBETTER":
                best_for_q.append((inst, tgt, q["config"], o, c1, round(r1, 2), c2, c4))
lines = ["family target move comparison : QBETTER QWORSE UNDET  (counts over instances x configs x {E,H})"]
for k in sorted(out):
    c = out[k]; lines.append("%s %s %s %s : %d %d %d" % (*k, c["QBETTER"], c["QWORSE"], c["UNDET"]))
lines.append("\nCases with any QBETTER (inst target config obs perstep_class perstep_ratio(hb/q) persec_vsHB persec_vsBestMetroPT):")
lines += [" ".join(map(str, b)) for b in best_for_q]
open("results/verdict_clean.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines[:40])); print(len(best_for_q), "QBETTER cases")
