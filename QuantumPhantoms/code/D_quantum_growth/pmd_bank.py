"""D-SCALE family `pmd-bank` (AC-11): deferred-measurement causal-state machines, the L1' gap above the floor.


Process (Wu et al., arXiv 2208.12744): Phi(n) = Gamma^n (1 - V sin^2(n pi / N)). Re-tune over V in {0.4, 0.6, 0.8,
0.95}, Gamma in {0.5, 0.7, 0.85}, N in {8, 16, 32}, L in {6, 8, 10}, maximising
[d_KL(best classical staircase model) - d_KL(quantum)] / floor, with floor = (2^L - 1) / (2 n L ln 2) per symbol,
n = shots x repeats (4,000 x 15 = 60,000 at the first-run caps), the staircase = best 2^k-state classical HMMs for
k = 1 .. log2 N - 1 (D_quantum_growth.causal_states), and d_KL(quantum) taken as its expected sampling bias (= the floor; the
1-qubit Wu model is exact).
Deferred machine: memory + L fresh outputs along path(L+1); each step is one merged U.SWAP (<= 3 CZ), so the memory
walks along the path; all outputs are measured at the end; the final memory is read in Z / X / Y (3 circuits).
Control arm: the copied mid-circuit builder of RE D-5 (measure + reset per step), declared to the lint.
Bank: K = 3 / 8 / 10 machines on disjoint buffered paths in one job, simulated per machine (crosstalk not modelled,
Q13). Pass: d_KL(q) < 1e-2, d_KL(q) < every staircase model with fewer than log2 N bits, gap > 3 x floor.
Claim L1' (memory advantage, simulated); 2-qubit blocks: never L2.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate

from D_quantum_growth import causal_states as C

NAME = "pmd-bank"
CLAIM = "L1'"
# Fallback until `--retune` has written research_runs/_dscale/pmd_retune.json (its `best` is then used).
DEFAULT_PROCESS = {"V": 0.95, "Gamma": 0.85, "N": 8, "L": 8}
RETUNE_FILE = Path(__file__).resolve().parents[2] / "research_runs" / "_dscale" / "pmd_retune.json"
VARIANTS = ("Z", "X", "Y")


def process() -> dict:
    if RETUNE_FILE.exists():
        best = json.loads(RETUNE_FILE.read_text()).get("best")
        if best:
            return {k: best[k] for k in ("V", "Gamma", "N", "L")}
    return dict(DEFAULT_PROCESS)


def floor(L_: int, n: int) -> float:
    return (2 ** L_ - 1) / (2 * n * L_ * math.log(2))


# ---------------------------------------------------------------------------------------------- staircase / retune
def staircase(proc: dict, seed_hex: str, n_starts: int = 24) -> dict:
    """Exact d_KL (bits/symbol) of the best 2^k-state classical model, k = 1 .. log2 N - 1."""
    h = C.pmd_hazards(proc["Gamma"], proc["V"], proc["N"])
    p_exact = C.exact_words(h, proc["L"], start=0)
    out = {}
    for k in range(1, int(math.log2(proc["N"]))):
        base = C.best_classical_fixed_memory(p_exact, proc["L"], 2 ** k, seed_hex, n_starts=n_starts)
        q = C.hmm_words(base["T"], proc["L"])
        out[k] = C.kl_bits(q, p_exact) / proc["L"]
    return out


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


def claim(cell: dict) -> dict:
    ms = [m for m in cell.get("machines", []) if "gap_over_floor" in m]
    best = max(ms, key=lambda m: m["gap_over_floor"]) if ms else {}
    return {"family": NAME, "claim_level": CLAIM if cell.get("passed_all") else "L0",
            "witness": "PMD memory gap / floor", "value": best.get("gap_over_floor"), "sigma": None, "k": 3,
            "passed": bool(cell.get("passed_all")), "label": cell.get("sim_label"),
            "note": f"process {cell.get('process')}; {len(ms)} machines; 2-q blocks: survives, never L2"}


