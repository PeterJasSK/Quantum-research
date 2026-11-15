"""Exact ideal replay of the QuantumTree long-range bond runs (teleport and SWAP arms), generation by generation.

The beliefs of generation g+1 follow deterministically from the recorded hardware frequencies p of generation g
(next_belief) and the run's seeded random stream (random.seed(seed); build_env; one WIGGLE draw per qubit per
generation). So each hardware circuit is rebuilt exactly and simulated without noise (exact MPS, 20,000 shots),
with the same herald post-selection and the same bond metric (c_at_d = connected bond correlation / C0).

    /home/peter/anaconda3/bin/python3 THESIS/QuantumEvolutionFrontier/analysis/teleport_replay.py
"""
from __future__ import annotations

import json
import random
import sys
import types
from pathlib import Path

import numpy as np
from qiskit_aer import AerSimulator

REPO = Path(__file__).resolve().parents[3]
BL = REPO / "QuantumLife/research_runs/BackLog"
OUT = REPO / "THESIS/QuantumEvolutionFrontier/runs/teleport_replay.json"
stub = types.ModuleType("pipeline_common")
for a in ("connect", "run_sampler", "qpu_seconds"):
    setattr(stub, a, lambda *x, **k: None)
stub.timestamp = lambda: "replay"
stub.Sampler = None
stub.SHOTS_PER_JOB = 10 ** 9
sys.modules["pipeline_common"] = stub
sys.path.insert(0, str(REPO / "QuantumLife/code"))
import research_qtree_swaplr as SW        # noqa: E402
import research_qtree_teleport as TEL     # noqa: E402

SHOTS = int(__import__("os").environ.get("REPLAY_SHOTS", "20000"))


def replay(path: Path) -> dict:
    r = json.loads(path.read_text())
    m = r["meta"]
    mod = TEL if m.get("long_range") == "teleport" else SW
    spec, n, sb = m["genome_spec"], m["genome_spec"]["n_bits"], m["genome_spec"]["slot_bits"]
    random.seed(m["seed"])
    env_sched, _ = mod.build_env(m["generations"])
    theta, kick = [np.pi / 2] * n, [0.0] * n
    sim = AerSimulator(method="matrix_product_state", seed_simulator=7)
    rows = []
    for g, rec in enumerate(r["generations"]):
        env = env_sched[g]
        env_match = all(abs(env[k] - rec["env"][k]) < 1e-3 for k in ("angle_bias", "season_bias"))
        if mod is TEL:
            qc = TEL.build_circuit(theta, kick, env, m["layers"], spec, m["entangler"], m["bonds"], herald=m["herald"])
        else:
            qc = SW.build_circuit(theta, kick, env, m["layers"], spec, m["entangler"], m["bonds"])
        q = qc.decompose(gates_to_decompose=["crx"]) if "crx" in qc.count_ops() else qc
        res = sim.run(q, shots=SHOTS, memory=True).result().get_memory()
        regs = [cr.name for cr in qc.cregs]
        fields, kept = [], 0
        for s in res:
            parts = s.split(" ")[::-1]                 # memory lists cregs last-declared first
            byname = dict(zip(regs, parts))
            if m.get("herald") and "tel" in byname and set(byname["tel"]) - {"0"}:
                continue
            kept += 1
            fields.append(byname["c"][::-1])
        b = TEL.bond_correlations(fields, n, m["bonds"], sb)[0]
        rows.append({"gen": g, "env_match": env_match, "ideal_c_at_d": b["c_at_d"], "hw_c_at_d": rec["bonds"][0]["c_at_d"],
                     "ideal_kept_frac": kept / SHOTS, "hw_herald_frac": rec.get("herald_frac")})
        theta, kick = TEL.next_belief(theta, rec["p"], n)
    ideal = np.array([x["ideal_c_at_d"] for x in rows])
    hw = np.array([x["hw_c_at_d"] for x in rows])
    return {"source": path.name, "arm": m.get("long_range"), "herald": m.get("herald"), "d_qubits": rows[0] and
            r["generations"][0]["bonds"][0]["d_qubits"], "seed": m["seed"], "rows": rows,
            "ideal_mean": float(ideal.mean()), "hw_mean": float(hw.mean()),
            "sign_agree_frac": float((np.sign(ideal) == np.sign(hw)).mean()),
            "corr_ideal_hw": float(np.corrcoef(ideal, hw)[0, 1]) if len(rows) > 2 else None}


def main() -> None:
    files = sorted(list(BL.glob("tel_herald_*_run.json")) + list(BL.glob("tel_ff_*_run.json"))
                   + list(BL.glob("swap_*_run.json")))
    out = json.loads(OUT.read_text()) if OUT.exists() else []
    done = {x["source"] for x in out if "error" not in x}
    files = [f for f in files if f.name not in done]
    for f in files:
        try:
            res = replay(f)
        except Exception as e:                         # record, never guess
            res = {"source": f.name, "error": f"{type(e).__name__}: {e}"[:300]}
        res["shots"] = SHOTS
        out.append(res)
        OUT.write_text(json.dumps(out, indent=1))
        if "error" in res:
            print(res["source"], res["error"], flush=True)
        else:
            print(f"{res['source'][:52]:52s} {res['arm']:8s} d={res['d_qubits']:2d} ideal {res['ideal_mean']:+.4f} "
                  f"hw {res['hw_mean']:+.4f} sign-agree {res['sign_agree_frac']:.2f} env-ok "
                  f"{all(x['env_match'] for x in res['rows'])}", flush=True)
    OUT.write_text(json.dumps(out, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
