"""Tune PT ladder size R: geometric ladder bmin..beta_target, smallest R with min swap rate >= 0.2
(2 s CPU pilot on seeds 1 and 2, min over both). usage: python tune_pt.py FAMILY -> results/pt_tuning_<fam>.json"""
import json, os, sys
import numpy as np
import cg

fam = sys.argv[1]
CFG = json.load(open(os.path.join(cg.HERE, "config.json")))
fc = CFG[fam]
out = {}
for size in fc["sizes"]:
    out[str(size)] = {}
    n = size if fam == "sk" else size * size
    for tgt in ["MEDIUM", "LOW"]:
        if fam == "sk":
            bt, bmin = fc["beta_over_betac"][tgt] / np.sqrt(n), fc["pt_bmin_over_betac"] / np.sqrt(n)
        else:
            bt, bmin = 1.0 / fc["T"][tgt], 1.0 / fc["pt_Tmax"]
        chosen, log = None, []
        for R in [4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40]:
            lad = np.geomspace(bmin, bt, R)
            ms = min(min(cg.pt(cg.Inst(fam, size, sd), lad, R - 1, 2.0, 77 + sd)["swap"]) for sd in [1, 2])
            log.append((R, ms))
            if ms >= 0.2:
                chosen = R
                break
        out[str(size)][tgt] = dict(R=chosen or 40, log=log)
        print(fam, size, tgt, out[str(size)][tgt], flush=True)
json.dump(out, open(os.path.join(cg.HERE, "results", f"pt_tuning_{fam}.json"), "w"), indent=1)
