"""Short re-timing in ONE process (machine still shared; CPU thread time) for the final per-move table."""
import json, numpy as np, cg
out = []
for fam, size in [("sk", 64), ("sk", 128), ("ea", 16)]:
    inst = cg.Inst(fam, size, 1); n = inst.n
    beta = 1.0 / np.sqrt(n) if fam == "sk" else 1.0
    r = cg.chain(inst, "metro", beta, 0.5, 1, moves_per_rec=20)
    out.append(dict(inst=inst.name, move="metro_sweep", k=0, us=1e6 * r["cpu"] / r["moves"]))
    for m in ["hb", "q", "dec"]:
        for k in [4, 8, 12]:
            if m == "dec" and k == 12: continue
            r = cg.chain(inst, m, beta, 0.6 if k < 12 else 1.5, 1, k=k, moves_per_rec=1)
            out.append(dict(inst=inst.name, move=m, k=k, us=1e6 * r["cpu"] / r["moves"], moves=r["moves"]))
    for o in out[-9:]: pass
json.dump(out, open("results/timing_iso.json", "w"), indent=1)
for o in out: print(o["inst"], o["move"], o["k"], "%.3g us" % o["us"])
