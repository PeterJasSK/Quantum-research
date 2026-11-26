"""eps_half: eps where the median excess (S-1) falls to half of (S_ideal-1); appended to results/summary.txt."""
import json
import numpy as np
thr = json.load(open("results/thresholds.json"))
out = []
for r in thr:
    if r["noise"] not in ("dep", "ad", "adtw", "adgp", "gdepmodel") or r["S_ideal"] <= 1.05:
        continue
    e = np.array([float(k) for k in r["S_by_eps"]]); s = np.array(list(r["S_by_eps"].values()))
    y = (s - 1) / (r["S_ideal"] - 1)
    eh = None
    for k in range(len(e)):
        if y[k] <= 0.5:
            eh = float(e[k]) if k == 0 else float(np.exp(np.interp(0.5, [y[k], y[k - 1]], [np.log(e[k]), np.log(e[k - 1])])))
            break
    out.append(f"  {r['source']:16s} n={int(r['n']):2d} {r['noise']:9s} {r['regime']:6s} S_ideal={r['S_ideal']:.2f} eps_half={eh if eh is None else f'{eh:.2g}'}")
txt = "\nEPS_HALF (eps where median (S-1) falls to half of (S_ideal-1); None = not reached by eps=1e-2)\n" + "\n".join(out) + "\n"
open("results/summary.txt", "a").write(txt)
print(txt)
