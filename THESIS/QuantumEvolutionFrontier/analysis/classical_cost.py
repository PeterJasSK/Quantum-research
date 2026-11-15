"""Classical cost of every hardware circuit family in the paper (the H axis), plus its ideal value.

For each family the circuit that ran on hardware is rebuilt from the original builder and simulated exactly
on this machine (8 cores, Aer 0.17.2): matrix-product-state (MPS) without truncation, or a statevector.
Recorded: wall-clock seconds, maximal MPS bond dimension chi, and the ideal value of the observable the
hardware reported, so hardware/ideal ratios are computed, not assumed. Also the belief-propagation (BP)
depth ladder of the live ch-qca seed region, giving F6's distance to L2 = t* - t_pass.

    cd QuantumPhantoms/code && /home/peter/anaconda3/bin/python3 \
        ../../THESIS/QuantumEvolutionFrontier/analysis/classical_cost.py [--part qt|qalife|dscale|all]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qpy, transpile
from qiskit_aer import AerSimulator

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "THESIS/QuantumEvolutionFrontier/runs/classical_cost.json"
sys.path[:0] = [str(REPO / "CalibrationGuidedHighYieldQRNG/old/code"), str(REPO / "QuantumLife/code"), str(REPO / "artificial-life/code"), str(REPO / "QuantumPhantoms/code")]
SEED = 1234


def mps_profile(qc: QuantumCircuit, shots: int) -> dict:
    """Exact MPS (no truncation): seconds to build the state, max bond dimension, then seconds to sample."""
    bare = qc.remove_final_measurements(inplace=False)
    if "crx" in bare.count_ops():                            # Aer MPS has no crx: exact decomposition
        bare = bare.decompose(gates_to_decompose=["crx"])
    sim = AerSimulator(method="matrix_product_state", seed_simulator=SEED)
    b = bare.copy()
    b.save_matrix_product_state(label="mps")
    t0 = time.time()
    res = sim.run(b, shots=1).result()
    t_state = time.time() - t0
    gam, lam = res.data(0)["mps"]
    chi = max([len(l) for l in lam] or [1])
    m = bare.copy()
    m.measure_all()
    t0 = time.time()
    mem = sim.run(m, shots=shots, memory=True).result().get_memory()
    t_samp = time.time() - t0
    bits = np.array([[int(c) for c in s.replace(" ", "")[::-1]] for s in mem], dtype=np.uint8)
    return {"n_qubits": qc.num_qubits, "chi_max": int(chi), "t_state_s": round(t_state, 3),
            "t_sample_s": round(t_samp, 3), "shots": shots, "bits": bits}


def c_of_d(bits: np.ndarray, dmax: int = 2) -> list[float]:
    b = bits.astype(float)
    mu = b.mean(0)
    out = []
    for d in range(dmax + 1):
        x, y = b[:, : b.shape[1] - d], b[:, d:]
        out.append(float(np.mean((x * y).mean(0) - mu[: len(mu) - d] * mu[d:])))
    return out


# ---------------------------------------------------------------- QuantumTree generation-0 circuits
def part_qt() -> dict:
    import research_qtree as RS
    import research_qtree_brickwall as RB
    from genome import GENOME_SPEC
    led = json.loads((REPO / "THESIS/QuantumEvolutionFrontier/runs/ledger.json").read_text())
    bl = REPO / "QuantumLife/research_runs/BackLog"
    arms = {"serial_L1": ("B0_ctrl_ibm_kingston", "serial", 1), "serial_L2": ("B_hw_ibm_kingston", "serial", 2),
            "serial_L4": ("C_L4_ibm_kingston", "serial", 4), "brick_L1": ("bw_L0_ibm_kingston", "brickwall", 1),
            "brick_L2": ("bw_L2_ibm_kingston", "brickwall", 2)}
    n = GENOME_SPEC["n_bits"]
    out = {}
    for name, (arm, ent, layers) in arms.items():
        src = led["quantum_tree"]["arms"][arm]
        files = json.loads((REPO / src["source"]).read_text())["meta"]["run_files"]
        rows = []
        for rf in files:
            r = json.loads((bl / rf).read_text())
            g0 = r["generations"][0]
            env = g0["env"]
            theta, kick = [math.pi / 2] * n, [0.0] * n
            if ent == "serial":
                qc = RS.build_circuit(theta, kick, env, layers, GENOME_SPEC)
            else:
                qc = RB.build_circuit(theta, kick, env, layers, GENOME_SPEC, ent)
            prof = mps_profile(qc, 20000)
            C = c_of_d(prof.pop("bits"))
            Ch = g0["correlation"]["C"]
            rows.append(prof | {"seed": r["meta"]["seed"], "logical_depth_hw": g0["logical_depth"],
                                "ideal_c1": C[1] / C[0], "ideal_c2": C[2] / C[0], "hw_c1_gen0": Ch[1] / Ch[0],
                                "hw_c2_gen0": Ch[2] / Ch[0]})
            print(f"  QT {name} seed {rows[-1]['seed']}: chi {prof['chi_max']}, {prof['t_state_s']}+{prof['t_sample_s']} s,"
                  f" ideal c1 {rows[-1]['ideal_c1']:+.4f} hw gen0 {rows[-1]['hw_c1_gen0']:+.4f}", flush=True)
        out[name] = {"hardware_arm": arm, "entangler": ent, "entangling_layers_applied": layers, "rows": rows}
    return out


# ---------------------------------------------------------------- QALife genealogies
def xparity(bits: np.ndarray, cols: list[int]) -> float:
    s = bits[:, cols].sum(1) % 2
    return float(1 - 2 * s.mean())


def part_qalife() -> dict:
    import qalife as QA
    import pj_qalife as PJ
    out = {"month4_unitary": [], "pj0_natural_separable": []}
    for W in (3, 4, 6, 12, 24, 32, 50):
        th = QA._sim_thetas(W, 100, 0.08)                   # hardware used Q-EaaS angles; PRNG stand-in at the same scale
        qc = QA.build_population(W, 3, th, "nn", death="unitary")
        wq = [QA.geno_q(k) for k in range(W)]
        x = qc.copy()
        for q in wq:
            x.h(q)
        prof = mps_profile(x, 8192)
        out["month4_unitary"].append(prof | {"W": W, "steps": 3, "mut_scale": 0.08,
                                             "ideal_witness": xparity(prof.pop("bits"), wq)})
        print(f"  M4 W={W}: chi {prof['chi_max']} {prof['t_state_s']}+{prof['t_sample_s']} s "
              f"ideal {out['month4_unitary'][-1]['ideal_witness']:.3f}", flush=True)
    for W in (4, 6, 12, 24, 50, 54, 77):
        steps = max(4, W // 2)
        th = [0.0] * W                                      # PJ0 hardware ran mut_scale = 0
        qc = PJ.to_witness_basis(PJ.build_germsoma(W, steps, th, phenotype="separable", soma_death="natural"), W)
        wq = PJ.witness_qubits(W)
        prof = mps_profile(qc, 8192)
        out["pj0_natural_separable"].append(prof | {"W": W, "steps": steps, "mut_scale": 0.0,
                                                    "ideal_witness": xparity(prof.pop("bits"), wq)})
        print(f"  PJ0 W={W}: {qc.num_qubits} q, chi {prof['chi_max']} {prof['t_state_s']}+{prof['t_sample_s']} s "
              f"ideal {out['pj0_natural_separable'][-1]['ideal_witness']:.3f}", flush=True)
    return out


# ---------------------------------------------------------------- QuantumPhantoms live D-SCALE circuits
def part_dscale() -> dict:
    from qiskit.quantum_info import Statevector
    run = REPO / "QuantumPhantoms/research_runs/dscale_live_100_20261031-170957/dscale/live/components.qpy"
    with open(run, "rb") as f:
        comps = qpy.load(f)
    fam = {}
    for c in comps:
        fam.setdefault(c.metadata.get("family"), []).append(c)
    out = {}
    spine = fam["ghz-spine"][0]
    t0 = time.time()
    AerSimulator(method="stabilizer").run(spine, shots=4000).result()
    out["ghz_spine"] = {"n_qubits": spine.num_qubits, "method": "stabilizer", "t_s": round(time.time() - t0, 3)}
    qca = [c for c in fam["ch-qca"] if c.metadata.get("tile_id")]
    rows = []
    for c in qca[:3]:
        bare = c.remove_final_measurements(inplace=False)
        t0 = time.time()
        Statevector(bare)
        rows.append({"tile": c.metadata["tile_id"], "n_qubits": c.num_qubits, "t_statevector_s": round(time.time() - t0, 3),
                     **{k: v for k, v in mps_profile(c, 4000).items() if k != "bits"}})
        print(f"  QCA {rows[-1]['tile']}: sv {rows[-1]['t_statevector_s']} s, chi {rows[-1]['chi_max']}", flush=True)
    out["ch_qca_tiles"] = rows
    out["ch_qca_bp_ladder"] = bp_ladder()
    return out


def bp_ladder() -> list[dict]:
    """F6 S5: BP chi needed vs QCA depth t on the live 23-site seed region (marrakesh), ideal references."""
    from dscale import allocate as A, budget as B, targets as T
    from dscale import survival as SV
    from dscale.families import ch_qca as Q
    tg = T.get("marrakesh")
    draw = Q.default_draw()
    rows = []
    for t in range(1, 7):
        params = {"sites": 23, "t_max": t, "t_w": min(t, 3), "alpha": math.pi / 2, "rule": "parity"}
        alloc = A.allocate(Q.region_request(100, tg, params), tg)
        patch = Q.patch_of(alloc, tg)
        sp = Q.spec(patch, params, draw)
        ent = Q.bp_circuits(alloc, params | {"t": t}, tg, draw)[0]
        col = {q: k for k, q in enumerate(sp["nodes"])}
        ent["obs_edges"] = [(col[a], col[b]) for a, b in sp["reg_edges"]]
        ent["obs_nodes"] = sorted({q for ed in ent["obs_edges"] for q in ed})
        t0 = time.time()
        bp = SV.bp_profile(ent, B.Deadline(1800), len(sp["nodes"]))
        rows.append({"t": t, "sites": len(sp["nodes"]), "ref_kind": bp.get("ref_kind"), "hard": bp.get("hard"),
                     "easy": bp.get("easy"), "fidelity_at_chi_max": bp.get("fidelity_vs_ref"),
                     "per_chi": bp.get("per_chi"), "wall_s": round(time.time() - t0, 2)})
        print(f"  BP t={t}: easy {bp.get('easy')} hard {bp.get('hard')} fid {bp.get('fidelity_vs_ref')} "
              f"({rows[-1]['wall_s']} s)", flush=True)
    return rows


def part_extra() -> dict:
    """Teleported long-range bond (102 + 2 ancilla qubits, mid-circuit measurement) and the motile organism."""
    import research_qtree_teleport as RT
    import pj_qalife as PJ
    bl = REPO / "QuantumLife/research_runs/BackLog"
    f = sorted(bl.glob("tel_herald_hw_ibm_marrakesh_seed100_*_run.json"))
    out = {}
    for rf in f:
        r = json.loads(rf.read_text())
        m, g0 = r["meta"], r["generations"][0]
        spec = m["genome_spec"]
        n = spec["n_bits"]
        qc = RT.build_circuit([math.pi / 2] * n, [0.0] * n, g0["env"], m["layers"], spec, m["entangler"],
                              m["bonds"], herald=m["herald"])
        sim = AerSimulator(method="matrix_product_state", seed_simulator=SEED)
        q = qc.decompose(gates_to_decompose=["crx"]) if "crx" in qc.count_ops() else qc
        t0 = time.time()
        sim.run(q, shots=4096).result()
        d = r["generations"][0]["bonds"][0]["d_qubits"]
        out[f"teleport_herald_d{d}"] = {"n_qubits": qc.num_qubits, "t_sample_s": round(time.time() - t0, 3),
                                        "shots": 4096, "source": rf.name}
        print("  teleport", d, out[f"teleport_herald_d{d}"], flush=True)
    qc = PJ.build_motile_vivarium(2, 4, 6, [0.0, 0.0])
    t0 = time.time()
    q = qc.copy()
    if not q.num_clbits:
        q.measure_all()
    AerSimulator(method="statevector", seed_simulator=SEED).run(q, shots=8192).result()
    out["motile_org2_L4"] = {"n_qubits": qc.num_qubits, "t_sample_s": round(time.time() - t0, 3), "shots": 8192,
                             "note": "mutation angles 0 (hardware drew Q-EaaS angles); cost is angle-independent"}
    print("  motile", out["motile_org2_L4"], flush=True)
    return out


def part_qcascan() -> dict:
    """Exact MPS cost of the ch-qca Z snapshot vs patch size and depth (marrakesh layout, ideal), with 2q counts."""
    from dscale import allocate as A, targets as T
    from dscale.families import ch_qca as Q
    tg = T.get("marrakesh")
    draw = Q.default_draw()
    rows = []
    for sites in (23, 40, 60, 100):
        for t in (2, 3, 4, 5, 6):
            params = {"sites": sites, "t_max": t, "t_w": min(t, 3), "alpha": math.pi / 2, "rule": "parity"}
            try:
                alloc = A.allocate(Q.region_request(100 if sites <= 100 else 120, tg, params), tg)
                sp = Q.spec(Q.patch_of(alloc, tg), params, draw)
            except Exception as e:                       # region does not fit: record, do not guess
                rows.append({"sites": sites, "t": t, "error": f"{type(e).__name__}: {e}"[:200]})
                continue
            qc = Q.circuit(sp, t, "Z")
            n2 = sum(v for k, v in qc.count_ops().items() if k in ("cz", "cx", "ecr"))
            t0 = time.time()
            try:
                prof = mps_profile(qc, 200)
                prof.pop("bits")
            except Exception as e:
                prof = {"error": f"{type(e).__name__}: {e}"[:200]}
            rows.append({"sites": len(sp["nodes"]), "t": t, "two_q": n2, "wall_s": round(time.time() - t0, 2)} | prof)
            print(f"  qca sites {len(sp['nodes'])} t {t}: 2q {n2}, chi {prof.get('chi_max')}, "
                  f"{rows[-1]['wall_s']} s", flush=True)
            if rows[-1]["wall_s"] > 900:
                break
    return {"rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all", choices=["qt", "qalife", "dscale", "qcascan", "extra", "all"])
    a = ap.parse_args()
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    res["machine"] = {"cores": os.cpu_count(), "aer": "0.17.2", "note": "exact MPS, no truncation"}
    for part, fn in (("qt", part_qt), ("qalife", part_qalife), ("dscale", part_dscale), ("qcascan", part_qcascan), ("extra", part_extra)):
        if a.part in (part, "all"):
            print(f"== {part}", flush=True)
            res[part] = fn()
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps(res, indent=1, default=float))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
