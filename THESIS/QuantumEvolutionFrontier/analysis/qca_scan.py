"""Exact classical cost of the ch-qca Z snapshot vs patch size and depth (ideal, marrakesh layout).

Each cell runs in its own subprocess with a wall-clock timeout and an address-space cap, so a cell that is too
expensive is recorded as a measured lower bound ("did not finish within T s / M GB") instead of being guessed.

    cd QuantumPhantoms/code && /home/peter/anaconda3/bin/python3 \
        ../../THESIS/QuantumEvolutionFrontier/analysis/qca_scan.py            # driver
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "THESIS/QuantumEvolutionFrontier/runs/qca_scan.json"
PY = "/home/peter/anaconda3/bin/python3"
TIMEOUT_S = 1200
MEM_GB = 20


def one(sites: int, t: int) -> dict:
    sys.path[:0] = [str(REPO / "QuantumPhantoms/code"), str(Path(__file__).parent)]
    from classical_cost import mps_profile
    from dscale import allocate as A, targets as T
    from dscale.families import ch_qca as Q
    tg = T.get("marrakesh")
    params = {"sites": sites, "t_max": t, "t_w": min(t, 3), "alpha": math.pi / 2, "rule": "parity"}
    alloc = A.allocate(Q.region_request(100, tg, params), tg)
    sp = Q.spec(Q.patch_of(alloc, tg), params, Q.default_draw())
    qc = Q.circuit(sp, t, "Z")
    n2 = sum(v for k, v in qc.count_ops().items() if k in ("cz", "cx", "ecr"))
    prof = mps_profile(qc, 200)
    prof.pop("bits")
    return {"sites": len(sp["nodes"]), "t": t, "two_q": n2} | prof


def driver() -> None:
    rows = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    done = {(r["sites_requested"], r["t"]) for r in rows}
    for sites in (23, 40, 60, 100):
        for t in (2, 3, 4, 5, 6):
            if (sites, t) in done:
                continue
            t0 = time.time()
            cmd = ["prlimit", f"--as={MEM_GB * 2 ** 30}", PY, __file__, "--one", str(sites), str(t)]
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S,
                                   cwd=REPO / "QuantumPhantoms/code")
                line = [l for l in p.stdout.splitlines() if l.startswith("{")]
                row = json.loads(line[-1]) if line else {"error": (p.stderr.strip().splitlines() or ["?"])[-1][:200]}
            except subprocess.TimeoutExpired:
                row = {"timeout_s": TIMEOUT_S}
            row |= {"sites_requested": sites, "t": t, "wall_s": round(time.time() - t0, 1), "mem_cap_gb": MEM_GB}
            rows.append(row)
            OUT.write_text(json.dumps({"timeout_s": TIMEOUT_S, "mem_cap_gb": MEM_GB, "rows": rows}, indent=1))
            print(json.dumps(row), flush=True)
            if "chi_max" not in row:                 # deeper cells at this size only cost more
                break


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", nargs=2, type=int)
    a = ap.parse_args()
    if a.one:
        print(json.dumps(one(*a.one)), flush=True)
    else:
        driver()
