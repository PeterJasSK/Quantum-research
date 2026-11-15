"""DSCALE: today's quantum growth. One composite job on the run's backend.

Three circuit families on disjoint, buffered regions of the same chip, multiplexed into the same circuits (regions
never share a gate; every family passes common.lint first):
    ghz-spine   certified clonal genealogy: GHZ tree + parity checks; ghz2 + DFE stabilizers          (claim L1, GME)
    ch-qca      Goldilocks QCA: 9 tomography settings + 1 echo, and ONE Z-SNAPSHOT PER TUMOUR with that tumour's
                draw-driven initial set. The snapshot becomes the tumour's 3-D seed shape           (claim L1)
    pmd-bank    one deferred-measurement causal-state machine, read in Z / X / Y                    (claim L1')
The seed snapshot of a tumour is the shot picked by rng(its geometry seed, "DS-qca-snapshot").
Proof of concept: one job, n = 1; the QCA witness is measured on the first tumour's initial set and applies to the
run, not per tumour. Never an L2 / advantage claim. The allocation is saved (dscale/plan.json) so a continued run
analyses the job that was submitted.

One family alone (GHZ-SPINE, CH-QCA, PMD-BANK in main.py): cfg["families"] keeps only those regions, cfg["request"]
overrides their allocation request and cfg["circuits"] is the least number of circuits in the job. The family then
has the first pick of the chip and nothing else runs next to it. Only CH-QCA writes seed shapes.
"""
from __future__ import annotations

import math

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile

from common import allocate as A, lint as L, quantum as Q, runio, witness as WS
from common.runio import Ctx
from D_quantum_growth import ch_qca as QCA_F, ghz_spine as G, pmd_bank as P, seedlift as SL

BUDGET = 40                  # qubits of the composite: 40 | 100 | 120
M_DFE = 24                    # DFE stabilizers on the spine
DRY_BUDGET, DRY_M_DFE = 40, 4  # dry run: a small composite (tests the pipeline)
QCA = {"t_max": 2, "t_w": 2, "alpha": math.pi / 2, "rule": "parity"}
REGS = {"ghz-spine": "s", "ch-qca": "c", "pmd-bank": "p"}


def components(alloc: dict, tg, draws: list[dict], m_dfe: int) -> dict[str, list[QuantumCircuit]]:
    draw0 = draws[0]
    out: dict[str, list[QuantumCircuit]] = {}
    fams = {r["family"] for r in alloc["regions"].values()}
    if "ghz-spine" in fams:
        out["ghz-spine"] = G.build(alloc, {"m": m_dfe}, draw0)[:-1]          # ghz2 X, Z + DFE (no soma here)
    if "ch-qca" in fams:
        patch = QCA_F.patch_of(alloc, tg)
        sp0 = QCA_F.spec(patch, QCA, draw0)
        job = [QCA_F.circuit(sp0, QCA["t_w"], (a, b)) for a in QCA_F.BASES for b in QCA_F.BASES]
        job.append(QCA_F.circuit(sp0, QCA["t_w"], "Z", echo=True))
        for d in draws:                                                      # one seed snapshot per tumour
            c = QCA_F.circuit(QCA_F.spec(patch, QCA, d), QCA["t_w"], "Z")
            c.metadata["tile_id"] = d["tile_id"]
            c.name = f"seed_{d['tile_id']}"
            job.append(c)
        out["ch-qca"] = job
    pm = [r for k, r in sorted(alloc["regions"].items()) if r["family"] == "pmd-bank" and r["role"] == "active"]
    proc = P.process()
    if pm and len(pm[0]["qubits"]) >= proc["L"] + 1:
        out["pmd-bank"] = list(P.build({"regions": {"pmd0": pm[0]}}, {}, draw0))
    return out


def merge(comp: dict[str, list[QuantumCircuit]], n_phys: int, k_min: int = 0) -> list[QuantumCircuit]:
    """K circuits; circuit k carries component k mod len of every family, each into its own classical register."""
    K = max(k_min, *(len(v) for v in comp.values()))
    out = []
    for k in range(K):
        regs = {f: ClassicalRegister(v[0].num_clbits, REGS[f]) for f, v in comp.items()}
        qc = QuantumCircuit(QuantumRegister(n_phys, "q"), *regs.values(), name=f"dscale_{k:02d}")
        for f, v in comp.items():
            c = v[k % len(v)]
            qc.compose(c, qubits=c.metadata["layout"], clbits=list(regs[f]), inplace=True)
        out.append(qc)
    return out


def analyse_spine(comps, bl, alloc, tg, shots) -> dict:
    lay = comps[0].metadata["layout"]
    col = {q: k for k, q in enumerate(lay)}
    trees = G._trees(alloc)
    t0 = trees[0]
    anc = [col[c["ancilla"]] for t in trees for c in t["checks"]]
    keep = [(b[:, anc].sum(1) == 0) if anc else np.ones(len(b), bool) for b in bl]
    cols0 = [col[q] for q in t0["nodes"]]
    edges0 = [(col[a], col[b]) for a, b in t0["edges"]]
    g2 = WS.ghz2(bl[0][keep[0]], bl[1][keep[1]], cols0, edges0)
    vals, vt = [], []
    for c, b, kp in zip(comps[2:], bl[2:], keep[2:]):
        st = c.metadata["stabilizers"][t0["name"]]
        v, se = WS.stabilizer_value(b[kp], st, cols0)
        vals.append(v)
        used = [q for q, p in zip(t0["nodes"], st["paulis"]) if p != "I"]
        vt.append(WS.trex_lite(v, se, used, tg.p01, tg.p10)[0])
    dfe, dfe_t = WS.dfe_ghz(vals), WS.dfe_ghz(vt)
    al = WS.alive([dfe["F"]], shots, threshold=0.5, sigma_extra=dfe["sigma"])
    return {"N": len(t0["nodes"]), "depth": t0["depth"], "n_checks": len(t0["checks"]),
            "kept_fraction": float(np.mean([k.mean() for k in keep])), "m": len(vals),
            "F_dfe": dfe["F"], "F_sigma": al["sigma"], "gme": al["alive"], "gme_k3": al["alive_k3"],
            "F_dfe_trex": dfe_t["F"], "ghz2": g2["value"], "ghz2_sigma": g2["sigma"], "ghz2_X": g2["X"],
            "ghz2_ZZ": g2["ZZ"]}


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    s = Q.session(ctx)
    tg = s.target
    budget, m_dfe = (BUDGET, M_DFE) if s.live else (DRY_BUDGET, DRY_M_DFE)
    plan_file = ctx.path("dscale", "plan.json")
    plan = runio.load_json(plan_file)
    if plan:
        alloc = plan["alloc"]
    else:
        try:
            reqs = A.composite_requests(budget, tg)
            if cfg.get("families"):
                reqs = [r | cfg.get("request", {}) for r in reqs if r["family"] in cfg["families"]]
            alloc = A.allocate(reqs, tg) | {"budget": budget, "recipe": name}
        except A.Infeasible as e:
            raise Q.Refused(f"the {budget}-qubit composite does not fit {tg.name} after calibration pruning ({e})")
        runio.save_json(plan_file, {"alloc": alloc, "backend": tg.name, "budget": budget})
    draws = runio.draws(ctx.run_dir)
    comp = components(alloc, tg, draws, m_dfe)
    if not plan:                                                              # a continued run was linted at submit
        for fam, job_c in comp.items():
            L.enforce(job_c, alloc["regions"], fam, tg.graph)
        Q.log("lint ok: " + ", ".join(f"{f} {len(v)} circuits" for f, v in comp.items()))
    isa = [transpile(c, backend=s.backend, initial_layout=list(range(tg.n_qubits)), optimization_level=1,
                     seed_transpiler=1) for c in merge(comp, tg.n_qubits, cfg.get("circuits", 0))]
    shots = Q.fit_shots(ctx, name, isa, [ctx.shots] * len(isa))[0]
    result, job_id, label = Q.run_isa(ctx, name, isa, [shots] * len(isa), dd=True, twirl=True, wide=True)
    Q.log(f"result in; analysing ({label})")

    # unpack per family (circuit k holds component k mod len)
    fam_bits: dict[str, list[np.ndarray]] = {}
    for fam, v in comp.items():
        per = [[] for _ in v]
        for k in range(len(isa)):
            per[k % len(v)].append(Q.bits(result[k], REGS[fam]))
        fam_bits[fam] = [np.concatenate(x) for x in per]

    claims, detail = [], {"label": label, "job_id": job_id, "shots": shots, "budget": budget, "used": alloc.get("n_used")}
    if "ghz-spine" in comp:
        sp = analyse_spine(comp["ghz-spine"], fam_bits["ghz-spine"], alloc, tg, shots)
        detail["ghz_spine"] = sp
        claims.append(G.claim(sp | {"sim_label": label}))
        Q.log(f"ghz-spine N={sp['N']}: F_dfe {sp['F_dfe']:.3f} +- {sp['F_sigma']:.3f} (m={sp['m']}), GME {sp['gme']}; "
              f"ghz2 {sp['ghz2']:.3f}; kept {sp['kept_fraction']:.2f}")
    if "ch-qca" in comp:
        cq, bq = comp["ch-qca"], fam_bits["ch-qca"]
        sp0 = cq[0].metadata["qca"]
        an = QCA_F.analyse(cq[:10], bq[:10], sp0, shots, draws[0]["seed_hex"])
        detail["ch_qca"] = {"sites": len(sp0["nodes"]), "rule": sp0["rule"], "alpha": sp0["alpha"], "t_w": QCA["t_w"],
                            "init": sp0["init"], "negativity_edges": an["negativity_edges"], "echo": an["echo"],
                            "random_band": an["random_band"], "witness_passed": an["witness_passed"]}
        claims.append(QCA_F.claim(detail["ch_qca"] | {"sim_label": label}))
        Q.log(f"ch-qca {len(sp0['nodes'])} sites: witness {an['witness_passed']}")
        patch = QCA_F.patch_of(alloc, tg)
        masks, tiles = {}, {}
        for c, bt in zip(cq[10:], bq[10:]):
            tid = c.metadata["tile_id"]
            d = next(x for x in draws if x["tile_id"] == tid)
            shot = int(runio.rng(d["seed_hex"], "DS-qca-snapshot").integers(len(bt)))
            active = [q for q, v in zip(c.metadata["layout"], bt[shot]) if v]
            masks[tid] = SL.lift(patch, active)
            tiles[tid] = {"region": f"{tg.name}:{len(patch['nodes'])}", "sites": len(patch["nodes"]),
                          "init": c.metadata["qca"]["init"], "active": active, "seed_cells": int(masks[tid].sum()),
                          "shot": shot, "claim_level": QCA_F.CLAIM if an["witness_passed"] else "L0",
                          "witness_passed": an["witness_passed"],
                          "witness_scope": "run-level (measured on the first tumour's initial set)"}
        runio.save_seed_shapes(ctx, masks, tiles, "ch-qca")
    if "pmd-bank" in comp:
        cp, bp_ = comp["pmd-bank"], fam_bits["pmd-bank"]
        proc = cp[0].metadata["process"]
        st = P.staircase(proc, draws[0]["seed_hex"], n_starts=6)
        d_q, n = P.words_dkl(bp_, proc, cp[0].metadata["outputs"])        # Z / X / Y differ on the memory only
        v = P.machine_verdict(d_q, n, proc, st)
        detail["pmd_bank"] = {"process": proc, "machines": [{"k": "pmd0", "path": cp[0].metadata["layout"]} | v],
                              "passed_all": v["passed"]}
        claims.append(P.claim(detail["pmd_bank"] | {"sim_label": label}))
        Q.log(f"pmd-bank: d_KL(q) {d_q:.2e}, gap/floor {v['gap_over_floor']:.2f}, passed {v['passed']}")
    Q.save(ctx, name, detail)
    dry = "" if s.live else " (dry run: not a claim)"
    return [c | {"config": name, "claim_level": c["claim_level"] + dry} for c in claims]
