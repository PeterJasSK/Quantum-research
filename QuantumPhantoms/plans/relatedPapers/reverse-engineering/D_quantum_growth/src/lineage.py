"""D-2: one-job quantum lineage with mid-circuit measurement, feed-forward, hidden CHSH rounds (target #8).

    python -m D_quantum_growth.src.lineage --mode ideal|heron [--dd] [--chsh-settings quantum|classical]

One dynamic circuit, G generations, 7 logical qubits on a FakeMarrakesh heavy-hex path. Per generation
(inside `if dead == 0`): divide parent -> daughter pair, basis coin (or CHSH setting coins in a hidden test
generation), mid-circuit pair readout, fate from the pair's joint outcome, `if_test` seeds the next parent,
reset. Necrotic outcome sets a dead flag on-chip; later generations are skipped. Simulation only.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile

from D_quantum_growth.src import heavyhex, io_contracts as io, witness as W
from shared.seedhash import derive_seed, rng
from shared.simbackend import (REFERENCE_FAKE, calibration_snapshot, circuit_hash, fake_backend,
                               make_simulator, sim_label)

G = 8
SHOTS = 4000
PHI0, DPHI = 0.5, 0.35      # illustrative fate-rotation constants (plan Q1), not fitted biology
NB = 6                      # clbits per generation: base, a, b, x, y, dead
IDX = {"base": 0, "a": 1, "b": 2, "x": 3, "y": 4, "dead": 5}
TOOL = "D_quantum_growth.src.lineage"
LABEL_CHSH = "certification-ready, not certified (simulated)"


def test_mask(seed_hex: str, n_gen: int = G) -> list[bool]:
    k = max(2, round(0.25 * n_gen))
    pick = rng(seed_hex, "D2-test-mask").choice(n_gen, size=k, replace=False)
    return [bool(g in set(int(i) for i in pick)) for g in range(n_gen)]


def _idle_window_dt() -> int:
    """Duration (dt) of one coin readout + reset, from the FakeMarrakesh target (median over qubits)."""
    t = fake_backend().target
    m = np.median([p.duration for p in t["measure"].values() if p and p.duration])
    r = np.median([p.duration for p in t["reset"].values() if p and p.duration]) if "reset" in t else 0
    return int(round((m + r) / fake_backend().dt / 16)) * 16


def build(mask: list[bool], dd: bool, classical: bool) -> QuantumCircuit:
    n_gen = len(mask)
    q = QuantumRegister(7, "q")
    d0, d1, p, coin, cx, cy, dq = q
    c = ClassicalRegister(NB * n_gen, "c")
    qc = QuantumCircuit(q, c, name="d2_lineage")
    T = _idle_window_dt()

    def bit(g, name):
        return c[NB * g + IDX[name]]

    def cnot(a, b):       # explicit CZ basis: the transpiler leaves cx/cry inside control-flow blocks untouched
        qc.h(b)
        qc.cz(a, b)
        qc.h(b)

    def idle(qubits):
        """Explicit idle window (so thermal relaxation applies); with --dd an X-X echo inside it."""
        if dd:
            for u in qubits:
                qc.delay(T // 4, u)
                qc.x(u)
                qc.delay(T // 2, u)
                qc.x(u)
                qc.delay(T // 4, u)
        else:
            for u in qubits:
                qc.delay(T, u)

    def body(g):
        test = mask[g]
        qc.h(d0)
        if not (test and classical):
            cnot(d0, d1)
        if not test:
            qc.ry(PHI0, d1)
            qc.ry(DPHI / 2, d1)                      # cry(DPHI, p, d1)
            cnot(p, d1)
            qc.ry(-DPHI / 2, d1)
            cnot(p, d1)
            qc.h(coin)
            qc.measure(coin, bit(g, "base"))
            qc.reset(coin)
            idle([d0, d1])
            with qc.if_test((bit(g, "base"), 1)):
                qc.h(d0)
                qc.h(d1)
        else:
            qc.h(cx)
            qc.h(cy)
            qc.measure(cx, bit(g, "x"))
            qc.measure(cy, bit(g, "y"))
            qc.reset(cx)
            qc.reset(cy)
            idle([d0, d1])
            with qc.if_test((bit(g, "x"), 1)):
                qc.h(d0)
            qc.ry(-np.pi / 4, d1)
            with qc.if_test((bit(g, "y"), 1)):
                qc.ry(np.pi / 2, d1)
        qc.measure(d0, bit(g, "a"))
        qc.measure(d1, bit(g, "b"))
        qc.reset(d0)
        qc.reset(d1)
        if not test:
            qc.reset(p)
            with qc.if_test((bit(g, "a"), 1)):          # next parent seeded from the measured genotype bit
                qc.x(p)
                with qc.if_test((bit(g, "b"), 0)):      # necrotic = joint outcome (1,0)
                    qc.x(dq)

    for g in range(n_gen):
        if g == 0:
            body(g)
        else:
            with qc.if_test((bit(g - 1, "dead"), 0)):
                body(g)
        qc.measure(dq, bit(g, "dead"))
    return qc


def coherent_block(kind: str) -> QuantumCircuit:
    """The unitary part of one generation (no measure / reset / feed-forward), for the BP adversary.
    kind: 'divide_Z' | 'divide_X' (fate-rotated pair, parent in |1>) | 'chsh' (test generation, settings x=y=1)."""
    q = QuantumRegister(3, "q")
    d0, d1, p = q
    qc = QuantumCircuit(q, name=f"d2_{kind}")
    if kind != "chsh":
        qc.x(p)                                    # parent genotype 1: the larger fate rotation
    qc.h(d0)
    qc.h(d1); qc.cz(d0, d1); qc.h(d1)
    if kind == "chsh":
        qc.h(d0)
        qc.ry(-np.pi / 4, d1)
        qc.ry(np.pi / 2, d1)
    else:
        qc.ry(PHI0, d1)
        qc.ry(DPHI / 2, d1); qc.h(d1); qc.cz(p, d1); qc.h(d1)
        qc.ry(-DPHI / 2, d1); qc.h(d1); qc.cz(p, d1); qc.h(d1)
        if kind == "divide_X":
            qc.h(d0); qc.h(d1)
    return qc


def layout() -> list[int]:
    P = heavyhex.path(7)
    # logical order: d0, d1, p, coin, cx, cy, dq  (d0-d1-p must be adjacent: path nodes 1,2,3)
    return [P[1], P[2], P[3], P[0], P[4], P[5], P[6]]


def run_job(mode: str, seed_hex: str, mask: list[bool], dd: bool, classical: bool, shots: int):
    qc = build(mask, dd, classical)
    tseed = derive_seed(seed_hex, "D2-sim") % 2 ** 31
    tqc = transpile(qc, backend=fake_backend(), initial_layout=layout(), optimization_level=1,
                    seed_transpiler=tseed)
    res = make_simulator(mode).run([tqc], shots=shots, seed_simulator=tseed, memory=True).result()
    mem = res.get_memory(0)
    bits = np.array([[int(ch) for ch in s[::-1]] for s in mem], dtype=np.uint8)  # clbit i = column i
    return {"bits": bits, "counts": dict(Counter(mem)), "transpiled": tqc, "seed": tseed,
            "hash": circuit_hash(tqc), "logical": qc}


def decode(bits: np.ndarray, mask: list[bool]) -> dict:
    """Per-shot, per-generation arrays: executed, fate code. fate: 0 divide, 1 rest, 2 necrotic, 3 test."""
    n, n_gen = bits.shape[0], len(mask)
    col = lambda g, k: bits[:, NB * g + IDX[k]]
    ran = np.zeros((n, n_gen), bool)
    fate = np.zeros((n, n_gen), np.uint8)
    for g in range(n_gen):
        ran[:, g] = True if g == 0 else (col(g - 1, "dead") == 0) & ran[:, g - 1]
        a, b = col(g, "a"), col(g, "b")
        if mask[g]:
            fate[:, g] = 3
        else:
            fate[:, g] = np.where((a == 1) & (b == 0), 2, np.where((a == 0) & (b == 1), 1, 0))
    return {"ran": ran, "fate": fate}


def lineage_witness(bits, dec, mask, seed_hex) -> tuple[dict, dict]:
    obs = {}
    col = lambda g, k: bits[:, NB * g + IDX[k]]
    xs, ys, as_, bs = [], [], [], []
    for g in range(len(mask)):
        r = dec["ran"][:, g]
        a, b = col(g, "a"), col(g, "b")
        if mask[g]:
            xs.append(col(g, "x")[r]); ys.append(col(g, "y")[r]); as_.append(a[r]); bs.append(b[r])
            continue
        base = col(g, "base")
        parts = {}
        for name, sel in (("ZZ", r & (base == 0)), ("XX", r & (base == 1))):
            v = np.stack([a[sel], b[sel]], 1)
            parts[name] = (W.corr(v[:, 0], v[:, 1]), W.boot_se(v, lambda s: W.corr(s[:, 0], s[:, 1]),
                                                              seed_hex, f"D-bootstrap-{name}{g}", 300), int(sel.sum()))
        val = parts["XX"][0] + parts["ZZ"][0]
        se = float(np.hypot(parts["XX"][1], parts["ZZ"][1]))
        obs[f"XX+ZZ_g{g}"] = {"value": val, "stderr": se, "n_zz": parts["ZZ"][2], "n_xx": parts["XX"][2]}
    x, y, a, b = (np.concatenate(v) for v in (xs, ys, as_, bs))
    S, S_se, n_rounds = W.chsh_S(x, y, a, b)
    return obs, {"S": S, "stderr": S_se, "n_test_samples": n_rounds}


def run(run_, seed_hex: str, mode: str, dd: bool = False, classical: bool = False, shots: int = SHOTS,
        tag: str = "") -> dict:
    mask = test_mask(seed_hex)
    job = run_job(mode, seed_hex, mask, dd, classical, shots)
    bits = job["bits"]
    dec = decode(bits, mask)
    obs, chsh = lineage_witness(bits, dec, mask, seed_hex)

    # job record (counts in a run-local counts file; CCR-D1: one logical job = one circuit here)
    job_id = io.job_id(seed_hex, "lineage", mode, dd, classical, shots)
    cf = run_.add_job(job_id, job["hash"], shots, job["counts"])
    suffix = ("_" + tag) if tag else ""
    from shared.seedhash import sha256_file
    jrec = io.envelope("quantum_job_record", run_, mode) | {
        "job_id": job_id, "sim_mode": mode, "fake_backend": REFERENCE_FAKE, "sim_seed": job["seed"],
        "shots": shots, "transpiled_hash": job["hash"],
        "counts_file": {"path": cf.name, "sha256": sha256_file(cf)},
        "test_round_mask": mask, "calibration_snapshot": calibration_snapshot()}
    jfile = run_.path / f"quantum_job_record_lineage{suffix}.json"
    jref = io.write_contract(jfile, jrec)
    run_.add_output(jfile.name, "quantum_job_record")

    # lineage: most frequent lineage, one shot chosen from the certificate seed
    ran, fate = dec["ran"], dec["fate"]
    names = ["divide", "rest", "necrotic", "test"]

    def sig(i):
        out = []
        for g in range(len(mask)):
            if not ran[i, g]:
                break
            out.append((int(bits[i, NB * g + IDX["a"]]), int(bits[i, NB * g + IDX["b"]]), int(fate[i, g])))
        return tuple(out)

    sigs = [sig(i) for i in range(shots)]
    top = Counter(sigs).most_common()
    best_n = top[0][1]
    best = sorted(s for s, n in top if n == best_n)[0]
    members = [i for i, s in enumerate(sigs) if s == best]
    pick = members[derive_seed(seed_hex, "D2-lineage-shot") % len(members)]
    gens = [{"g": g, "measured_bits": f"{a}{b}", "fate": [names[f]], "chsh_round": bool(mask[g])}
            for g, (a, b, f) in enumerate(best)]
    lin = io.envelope("quantum_lineage", run_, mode, [{"contract": "quantum_job_record", **jref}]) | {
        "job_record_ref": jref, "claim_level": "L1", "generations": gens}
    lfile = run_.path / f"quantum_lineage{suffix}.json"
    lref = io.write_contract(lfile, lin)
    run_.add_output(lfile.name, "quantum_lineage")

    # witness
    thr_ok = [(o["value"] - 3 * o["stderr"]) > 1.0 for o in obs.values()]
    wobs = {k: {"value": v["value"], "stderr": v["stderr"]} for k, v in obs.items()}
    wobs["S_chsh"] = {"value": chsh["S"], "stderr": chsh["stderr"]}
    passed = bool(thr_ok) and all(thr_ok)
    wrec = io.envelope("witness_record", run_, mode, [{"contract": "quantum_job_record", **jref}]) | {
        "claim_level": "L1", "job_record_ref": jref, "observables": wobs,
        "witness_expression": "<XX>_g + <ZZ>_g > 1 for every non-test generation g "
                              f"(S_chsh in observables: {LABEL_CHSH})",
        "threshold": 1.0, "passed": passed, "bases": ["X", "Z"], "mi_network": None}
    wfile = run_.path / f"witness_record_lineage{suffix}.json"
    io.write_contract(wfile, wrec)
    run_.add_output(wfile.name, "witness_record")

    s_ok = chsh["S"] > 2.0
    io.write_sidecar(run_.path / f"lineage_detail{suffix}.json", {
        "sim_label": sim_label(mode), "dd": dd, "chsh_settings": "classical" if classical else "quantum",
        "S_chsh": chsh, "S_label": LABEL_CHSH, "per_generation": obs, "test_mask": mask,
        "reached": [int(x) for x in ran.sum(0)], "fates_overall": {n: int(((fate == i) & ran).sum())
                                                                   for i, n in enumerate(names)},
        "dead_fraction": float((~ran[:, -1] | (fate[:, -1] == 2)).mean()), "lineage_shot": int(pick),
        "chsh_ok": s_ok})
    return {"mask": mask, "obs": obs, "chsh": chsh, "chsh_ok": s_ok, "passed": passed, "lineage_ref": lref,
            "lineage_file": lfile, "job_ref": jref, "bits": bits, "dec": dec, "job": job}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("ideal", "heron"), required=True)
    ap.add_argument("--dd", action="store_true")
    ap.add_argument("--chsh-settings", choices=("quantum", "classical"), default="quantum")
    ap.add_argument("--shots", type=int, default=SHOTS)
    io.add_input_args(ap)
    a = ap.parse_args()
    run_, paths, docs, seed = io.begin(a.mode, f"lineage-{a.mode}" + ("-dd" if a.dd else ""), TOOL,
                                       io.overrides_of(a))
    if seed is None:
        return 2
    r = run(run_, seed, a.mode, a.dd, a.chsh_settings == "classical", a.shots)
    note = (f"{sim_label(a.mode)}; S_chsh={r['chsh']['S']:.3f}+-{r['chsh']['stderr']:.3f} "
            f"witness_passed={r['passed']}" + ("" if r["chsh_ok"] else " REJECTED: S<=2"))
    if not r["chsh_ok"]:
        with open(io.LETTER_DIR / "runs" / "rejections.jsonl", "a") as f:
            f.write(json.dumps({"run_id": run_.path.name, "stage": "lineage", "mode": a.mode,
                                "S": r["chsh"]["S"]}) + "\n")
    run_.finish(note)
    print(run_.path, "\n ", note)
    for k, v in r["obs"].items():
        print(f"  {k}: {v['value']:.3f} +- {v['stderr']:.3f} (n_zz={v['n_zz']}, n_xx={v['n_xx']})")
    return 0 if r["chsh_ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
