"""D-SCALE family `pmd-bank` (AC-11): deferred-measurement causal-state machines, the L1' gap above the floor.

    python -m dscale.families.pmd_bank --retune --smoke          # pick (V, Gamma, N, L)
    python -m dscale.families.pmd_bank --budget 40 --mode heron --smoke

Process (Wu et al., arXiv 2208.12744): Phi(n) = Gamma^n (1 - V sin^2(n pi / N)). Re-tune over V in {0.4, 0.6, 0.8,
0.95}, Gamma in {0.5, 0.7, 0.85}, N in {8, 16, 32}, L in {6, 8, 10}, maximising
[d_KL(best classical staircase model) - d_KL(quantum)] / floor, with floor = (2^L - 1) / (2 n L ln 2) per symbol,
n = shots x repeats (4,000 x 15 = 60,000 at the first-run caps), the staircase = best 2^k-state classical HMMs for
k = 1 .. log2 N - 1 (dscale.causal_states), and d_KL(quantum) taken as its expected sampling bias (= the floor; the
1-qubit Wu model is exact).
Deferred machine: memory + L fresh outputs along path(L+1); each step is one merged U.SWAP (<= 3 CZ), so the memory
walks along the path; all outputs are measured at the end; the final memory is read in Z / X / Y (3 circuits).
Control arm: the copied mid-circuit builder of RE D-5 (measure + reset per step), declared to the lint.
Bank: K = 3 / 8 / 10 machines on disjoint buffered paths in one job, simulated per machine (crosstalk not modelled,
Q13). Pass: d_KL(q) < 1e-2, d_KL(q) < every staircase model with fewer than log2 N bits, gap > 3 x floor.
Claim L1' (memory advantage, simulated); 2-qubit blocks: never L2.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import UnitaryGate

from dscale import allocate as A, budget as B, causal_states as C, families as F, lint as L, targets as T
from imaging.seedhash import derive_seed

NAME = "pmd-bank"
CLAIM = "L1'"
WITNESS = "d_KL(quantum) gap above the best classical staircase model > 3 x sampling floor"
HARDNESS = "2-qubit blocks: never L2"
PRESETS = {40: {"K": 3}, 100: {"K": 8}, 120: {"K": 10}}
GRID = {"V": [0.4, 0.6, 0.8, 0.95], "Gamma": [0.5, 0.7, 0.85], "N": [8, 16, 32], "L": [6, 8, 10]}
PARAM_GRID = {"process": GRID, "K": [3, 8, 10]}
# Fallback until `--retune` has written research_runs/_dscale/pmd_retune.json (its `best` is then used).
DEFAULT_PROCESS = {"V": 0.95, "Gamma": 0.85, "N": 8, "L": 8}
RETUNE_FILE = Path(__file__).resolve().parents[3] / "research_runs" / "_dscale" / "pmd_retune.json"
VARIANTS = ("Z", "X", "Y")


def preset_text(budget: int) -> str:
    return f"K = {PRESETS[budget]['K']} machines (memory + L outputs each, L = {process()['L']})"


def default_draw() -> dict:
    return F.default_draw()


def process() -> dict:
    if RETUNE_FILE.exists():
        best = json.loads(RETUNE_FILE.read_text()).get("best")
        if best:
            return {k: best[k] for k in ("V", "Gamma", "N", "L")}
    return dict(DEFAULT_PROCESS)


def floor(L_: int, n: int) -> float:
    return (2 ** L_ - 1) / (2 * n * L_ * math.log(2))


# ---------------------------------------------------------------------------------------------- staircase / retune
def staircase(proc: dict, seed_hex: str, n_starts: int = 24, deadline: B.Deadline | None = None) -> dict:
    """Exact d_KL (bits/symbol) of the best 2^k-state classical model, k = 1 .. log2 N - 1."""
    h = C.pmd_hazards(proc["Gamma"], proc["V"], proc["N"])
    p_exact = C.exact_words(h, proc["L"], start=0)
    out = {}
    for k in range(1, int(math.log2(proc["N"]))):
        if deadline is not None and deadline.expired():
            deadline.skip(f"staircase k={k} for {proc}")
            break
        base = C.best_classical_fixed_memory(p_exact, proc["L"], 2 ** k, seed_hex, n_starts=n_starts)
        q = C.hmm_words(base["T"], proc["L"])
        out[k] = C.kl_bits(q, p_exact) / proc["L"]
    return out


def retune(shots: int, repeats: int, seed_hex: str, deadline: B.Deadline, n_starts: int = 24) -> dict:
    n = shots * repeats
    rows = []
    order = sorted(itertools.product(GRID["V"], GRID["Gamma"], GRID["N"], GRID["L"]),
                   key=lambda x: (x[2], x[3], -x[0], -x[1]))                     # cheap staircases first
    for V, G, N, L_ in order:
        if deadline.expired():
            deadline.skip(f"V={V} Gamma={G} N={N} L={L_}")
            continue
        proc = {"V": V, "Gamma": G, "N": N, "L": L_}
        row = proc | {"physical": C.check_physical(G, V, N)}
        try:
            C.wu_model(G, V, N)
        except ValueError as e:
            rows.append(row | {"error": str(e)})
            continue
        if not row["physical"]:
            rows.append(row | {"error": "survival not monotone"})
            continue
        st = staircase(proc, seed_hex, n_starts, deadline)
        if len(st) < int(math.log2(N)) - 1:
            rows.append(row | {"staircase": {str(k): v for k, v in st.items()}, "truncated": True})
            continue
        fl = floor(L_, n)
        d_q = fl                                       # expected sampling bias of the exact 1-qubit model
        best_c = min(st.values())
        rows.append(row | {"staircase": {str(k): v for k, v in st.items()}, "floor": fl, "d_kl_q_expected": d_q,
                           "gap_over_floor": (best_c - d_q) / fl})
        print(f"  V={V:4.2f} Gamma={G:4.2f} N={N:2d} L={L_:2d}  floor={fl:.2e}  staircase "
              + " ".join(f"k{k}={v:.2e}" for k, v in st.items()) + f"  gap/floor={rows[-1]['gap_over_floor']:.2f}",
              flush=True)
    ok = [r for r in rows if "gap_over_floor" in r]
    best = max(ok, key=lambda r: r["gap_over_floor"]) if ok else None
    return {"n": n, "shots": shots, "repeats": repeats, "grid": GRID, "rows": rows, "best": best,
            "truncated": deadline.truncated, "skipped": deadline.skipped}


# ---------------------------------------------------------------------------------------------- regions / circuits
def region_request(budget: int, tg: T.Target, params: dict | None = None) -> list[dict]:
    p = PRESETS[budget] | (params or {})
    L_ = (params or {}).get("L", process()["L"])
    return [{"name": f"pmd{k}", "family": NAME, "kind": "path", "n": L_ + 1, "role": "active", "min_n": 3,
             "optional": k > 0} for k in range(p["K"])]


def _model(proc: dict) -> dict:
    return C.wu_model(proc["Gamma"], proc["V"], proc["N"])


def machine_circuit(path: list[int], proc: dict, basis: str) -> QuantumCircuit:
    """Deferred machine on a physical path: memory starts at path[0]; step t applies U.SWAP on (path[t], path[t+1])."""
    model = _model(proc)
    s0 = model["sigma"][0]
    U = C.kraus_unitary(model["A0"], model["A1"])               # on [memory, output], index = 2 o + m
    SW = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], complex)
    W = SW @ U
    steps = len(path) - 1
    qc = QuantumCircuit(len(path), len(path), name=f"pmd_{basis}")
    qc.ry(2 * np.arctan2(s0[1].real, s0[0].real), 0)
    for t in range(steps):
        qc.append(UnitaryGate(W, label="U.SWAP"), [t, t + 1])
    if basis == "X":
        qc.h(steps)
    elif basis == "Y":
        qc.sdg(steps)
        qc.h(steps)
    for k in range(len(path)):
        qc.measure(k, k)
    qc.metadata = {"layout": list(path), "basis": basis, "family": NAME, "root": None, "process": proc,
                   "outputs": list(range(steps)), "memory": steps}
    return qc


def _order_path(r: dict) -> list[int]:
    if not r["edges"]:
        return list(r["qubits"])
    import networkx as nx
    g = nx.Graph([tuple(e) for e in r["edges"]])
    ends = [n for n in g.nodes if g.degree(n) == 1]
    return nx.shortest_path(g, min(ends), max(ends))


def build(alloc: dict, params: dict, draw: dict) -> list[QuantumCircuit]:
    proc = params.get("process") or process()
    job = []
    for name, r in sorted(alloc["regions"].items()):
        if r["family"] == NAME and r["role"] == "active":
            path = _order_path(r)
            for b in VARIANTS:
                c = machine_circuit(path, proc, b)
                c.name = f"{name}_{b}"
                c.metadata["machine"] = name
                job.append(c)
    return job


def control_arm(path: list[int], proc: dict, basis: str) -> QuantumCircuit:
    """Copied mid-circuit builder of RE D-5 (`memory_advantage.build`): U -> measure output -> reset, per step.
    Declared control arm (lint rule 1 tolerated)."""
    model = _model(proc)
    s0 = model["sigma"][0]
    U = C.kraus_unitary(model["A0"], model["A1"])
    steps = proc["L"]
    q = QuantumRegister(2, "q")
    c = ClassicalRegister(steps + 1, "c")
    qc = QuantumCircuit(q, c, name=f"d5_{basis}")
    m, o = q
    qc.ry(2 * np.arctan2(s0[1].real, s0[0].real), m)
    for t in range(steps):
        qc.unitary(U, [m, o], label="U")
        qc.measure(o, c[t])
        qc.reset(o)
    if basis == "X":
        qc.h(m)
    elif basis == "Y":
        qc.sdg(m)
        qc.h(m)
    qc.measure(m, c[steps])
    qc.metadata = {"layout": list(path[:2]), "basis": basis, "family": NAME, "root": None, "control_arm": True,
                   "process": proc}
    return qc


def clifford_twin(circuits):
    return list(circuits)                                       # no Clifford twin needed: 2-qubit blocks


def bp_circuits(alloc: dict, params: dict) -> list[dict]:
    return []                                                   # 2-q blocks on a path: exact at chi = 2


# ---------------------------------------------------------------------------------------------- witness
def words_dkl(bits_list: list[np.ndarray], proc: dict, out_cols: list[int]) -> tuple[float, int]:
    L_ = proc["L"]
    words = np.concatenate([b[:, out_cols[:L_]] for b in bits_list]).astype(np.int64)
    idx = words @ (1 << np.arange(L_ - 1, -1, -1))
    p_sim = np.bincount(idx, minlength=2 ** L_) / len(idx)
    h = C.pmd_hazards(proc["Gamma"], proc["V"], proc["N"])
    p_exact = C.exact_words(h, L_, start=0)
    return C.kl_bits(p_sim, p_exact) / L_, len(idx)


def machine_verdict(d_q: float, n: int, proc: dict, st: dict) -> dict:
    fl = floor(proc["L"], n)
    best_c = min(st.values()) if st else float("nan")
    passed = bool(d_q < 1e-2 and all(d_q < v for v in st.values()) and (best_c - d_q) > 3 * fl)
    return {"d_kl_q": float(d_q), "n_words": int(n), "floor": fl,
            "d_kl_classical": {str(k): float(v) for k, v in st.items()},
            "gap_over_floor": float((best_c - d_q) / fl), "passed": passed}


def run_cell(alloc: dict, params: dict, draw: dict, mode: str, target: str, shots: int, repeats: int,
             deadline: B.Deadline, staircase_cache: dict | None = None, control: bool = False) -> dict:
    proc = params.get("process") or process()
    key = json.dumps(proc, sort_keys=True)
    cache = staircase_cache if staircase_cache is not None else {}
    if key not in cache:
        cache[key] = staircase(proc, draw["seed_hex"], 24, deadline)
    st = cache[key]
    job = build(alloc, params | {"process": proc}, draw)
    machines = sorted({c.metadata["machine"] for c in job})
    rows, hashes, label, isa = [], [], None, []
    for mname in machines:
        if deadline.expired():
            deadline.skip(f"pmd machine {mname}")
            continue
        mj = [c for c in job if c.metadata["machine"] == mname]
        if len(mj[0].metadata["layout"]) < proc["L"] + 1:
            rows.append({"k": mname, "error": f"path {len(mj[0].metadata['layout'])} < L + 1 (fitted)"})
            continue
        zb = []
        for r in range(repeats):
            if deadline.expired():
                deadline.skip(f"pmd {mname} repeat {r + 1}")
                break
            try:
                ex = F.execute(mj, mode, target, shots, derive_seed(draw["seed_hex"], f"DS-pmd-sim-{mname}-{r}") % 2 ** 31,
                               deadline=deadline)
            except B.DeadlineHit:
                break
            zb.append(ex["bits"][0])
            hashes += ex["hashes"]
            label = ex["sim_label"]
            isa = ex["isa"]
        if not zb:
            continue
        d_q, n = words_dkl(zb, proc, mj[0].metadata["outputs"])
        rows.append({"k": mname, "path": mj[0].metadata["layout"]} | machine_verdict(d_q, n, proc, st))
    out = {"process": proc, "machines": rows, "hashes": hashes, "sim_label": label, "_isa": isa,
           "passed_all": bool(rows) and all(r.get("passed") for r in rows)}
    if control and rows and not deadline.expired():
        path = rows[0].get("path") or [0, 1]
        arm = [control_arm(path, proc, b) for b in VARIANTS]
        try:
            ex = F.execute(arm, mode, target, shots, derive_seed(draw["seed_hex"], "DS-pmd-control") % 2 ** 31,
                           deadline=deadline)
            d_c, n_c = words_dkl([ex["bits"][0]], proc, list(range(proc["L"])))
            out["control_arm"] = {"kind": "mid-circuit (RE D-5 builder, measure + reset per step)",
                                  "sim_label": ex["sim_label"]} | machine_verdict(d_c, n_c, proc, st)
        except B.DeadlineHit:
            pass
    return out


def claim(cell: dict) -> dict:
    ms = [m for m in cell.get("machines", []) if "gap_over_floor" in m]
    best = max(ms, key=lambda m: m["gap_over_floor"]) if ms else {}
    return {"family": NAME, "claim_level": CLAIM if cell.get("passed_all") else "L0",
            "witness": "PMD memory gap / floor", "value": best.get("gap_over_floor"), "sigma": None, "k": 3,
            "passed": bool(cell.get("passed_all")), "label": cell.get("sim_label"),
            "note": f"process {cell.get('process')}; {len(ms)} machines; 2-q blocks: survives, never L2"}


# ---------------------------------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--retune", action="store_true")
    ap.add_argument("--budget", type=int, default=40, choices=F.BUDGETS)
    ap.add_argument("--target", default="marrakesh", choices=T.NAMES)
    ap.add_argument("--mode", default="ideal")
    ap.add_argument("--no-control", action="store_true", help="skip the mid-circuit control arm")
    B.add_args(ap)
    a = ap.parse_args()
    dl = B.check(a, default_repeats=B.REPEATS if a.retune else (2 if a.smoke else B.REPEATS))
    draw = default_draw()
    if a.retune:
        print(f"re-tune: n = shots x repeats = {a.shots} x {a.repeats} = {a.shots * a.repeats}")
        res = retune(a.shots, a.repeats, draw["seed_hex"], dl, n_starts=6 if a.smoke else 24)
        res["n_starts"] = 6 if a.smoke else 24
        b = res["best"]
        if b:
            print(f"best: V={b['V']} Gamma={b['Gamma']} N={b['N']} L={b['L']}  gap/floor={b['gap_over_floor']:.2f} "
                  f"(floor {b['floor']:.2e}; staircase {b['staircase']})")
        RETUNE_FILE.parent.mkdir(parents=True, exist_ok=True)
        RETUNE_FILE.write_text(json.dumps(res, indent=1))
        print("wrote", RETUNE_FILE, "\n" + dl.report())
        return 0
    tname = F.mode_target(a.mode, a.target)
    tg = T.get(tname)
    alloc = A.allocate(region_request(a.budget, tg), tg)
    job = build(alloc, {}, draw)
    L.enforce(job, alloc["regions"], NAME, tg.graph)
    proc = process()
    arm = [control_arm(job[0].metadata["layout"], proc, b) for b in VARIANTS]
    print("control arm lint rule 1:",
          [r["detail"] for r in L.lint(arm, alloc["regions"], NAME, tg.graph) if r["rule"] == 1][0])
    print(f"pmd-bank budget {a.budget} on {tg.label}, mode {a.mode}; process {proc}; "
          f"{len({c.metadata['machine'] for c in job})} machines; shots {a.shots} x repeats {a.repeats}")
    cell = run_cell(alloc, {}, draw, a.mode, tname, a.shots, a.repeats, dl, control=not a.no_control)
    for m in cell["machines"]:
        if "error" in m:
            print(f"  {m['k']}: {m['error']}")
            continue
        print(f"  {m['k']}: d_KL(q)={m['d_kl_q']:.2e} (n={m['n_words']}, floor {m['floor']:.2e})  staircase "
              + " ".join(f"k{k}={v:.2e}" for k, v in m["d_kl_classical"].items())
              + f"  gap/floor={m['gap_over_floor']:.2f}  passed={m['passed']}")
    if "control_arm" in cell:
        c = cell["control_arm"]
        print(f"  control arm ({c['kind']}): d_KL={c['d_kl_q']:.2e} (n={c['n_words']}) gap/floor="
              f"{c['gap_over_floor']:.2f} passed={c['passed']}")
    print(f"  {cell['sim_label']}; claim {claim(cell)['claim_level']}\n" + dl.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
