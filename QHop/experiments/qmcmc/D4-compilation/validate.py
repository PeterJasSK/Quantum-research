"""Validate the per-layer linear model N(r) = N(3) + (r-3)(N(5)-N(3))/2 against full-r transpiles (level 3, 2 seeds,
best kept).  -> results/validate.jsonl"""
import json
import warnings

from qiskit_ibm_runtime import fake_provider as fp

import d4lib as D
from compile import best_of, GAM, DT

warnings.simplefilter("ignore")
CASES = [("DENSE", 8, 14, lambda r: D.ising_circuit(*D.fam_sk(8, 0), GAM, DT * r, r)),
         ("DENSE", 16, 20, lambda r: D.ising_circuit(*D.fam_sk(16, 0), GAM, DT * r, r)),
         ("EA", 16, 15, lambda r: D.ising_circuit(*D.fam_ea(4, 4, 0), GAM, DT * r, r)),
         ("HH", 27, 20, lambda r: D.ising_circuit(*D.fam_hh(27, 0), GAM, DT * r, r)),
         ("POTTS3", 27, 12, lambda r: D.potts_circuit(D.fam_potts(3, 3, 3, 0), GAM, DT * r, r))]

if __name__ == "__main__":
    B = {"heavyhex": fp.FakeMarrakesh(), "square": fp.FakeNighthawk()}
    lay = {}
    for l in open("results/compile_layers.jsonl"):
        d = json.loads(l)
        if d["variant"] == "sabre":
            lay[(d["struct"], d["n"], d["topo"], d["r"])] = d
    with open("results/validate.jsonl", "w") as fh:
        for s, n, r, mk in CASES:
            for topo, be in B.items():
                b, _ = best_of(mk(r), be, range(2))
                a3, a5 = lay[(s, n, topo, 3)], lay[(s, n, topo, 5)]
                pred = {k: a3[k] + (r - 3) * (a5[k] - a3[k]) / 2 for k in ("n2q", "depth2q", "duration_s")}
                rec = dict(struct=s, n=n, r=r, topo=topo, full=b, pred=pred,
                           rel_err_n2q=(pred["n2q"] - b["n2q"]) / b["n2q"])
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                print(s, n, r, topo, b["n2q"], round(pred["n2q"]), flush=True)
