"""D-SCALE noise validation (AC-4) and hardware back-test (AC-5).

    python -m dscale.validate_noise --pauli --smoke [--target marrakesh]
    python -m dscale.validate_noise --backtest --smoke

--pauli: the Pauli-twirled model (dscale.pauli_noise) against AerSimulator.from_backend(Fake<Target>) on identical
transpiled (ALAP-scheduled ISA) circuits:
  * ghz-spine N in {6, 12, 20}: <X^N> and mean adjacent <ZZ>;
  * ch-qca at 12 and 20 sites (t = 2 echo): the Clifford twin under both models (|delta|), and the real circuit
    under the full model vs the twin under the Pauli model (alive / dead class match).
  Pass: |delta| <= max(0.03, 2 sigma) on every pauli-vs-full row. If it fails, every Pauli / twin verdict above 24 q
  is labelled `unvalidated` (dscale.survival reads noise_validation.json).
--backtest (a report, not a gate; calibration drift is expected): three published hardware setups, re-derived (no
code imported), simulated with the Pauli model on `kingston` and `marrakesh`:
  * QALife 2018 ladder W = 3..32 (ibm_kingston 2026-08-25; artificial-life/research/CONCLUSION_MONTH4.md:147-154),
    re-derived as a 2W-qubit chain GHZ (germ clone + cx(g,p) phenotype copy) with Ry(0.08) germ mutations: an
    approximation of the `nn` / unitary-death / steps 3 model, witness <X^{2W}>;
  * PJ0 lean ladder W = 6..50 (PJ0_CONCLUSION.html Table 2): germ GHZ on alternate qubits of a 2W chain, separable
    idle soma, mut 0 (DD inert in the Pauli model), witness <X^W> on the germ;
  * IBM Big Cats 100 q / 120 q (arXiv 2510.09520): ghz-spine BFS tree + parity checks, DFE with m = 8 here.
  Prints predicted vs measured and the fitted per-qubit decay vs 0.861 (QALife) / 0.940 (PJ0).
Outputs research_runs/_dscale/noise_validation.json and figures/hw_backtest.png (or under --out).
"""
from __future__ import annotations

import argparse
import json
import math
import warnings
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from dscale import allocate as A, budget as B, families as F, pauli_noise as PN, targets as T
from dscale import witness_scale as WS

OUT_DEFAULT = Path(__file__).resolve().parents[2] / "research_runs" / "_dscale"

QALIFE = {"source": "artificial-life/research/CONCLUSION_MONTH4.md:147-154 (ibm_kingston, 2026-08-25)",
          "points": {3: 0.879, 4: 0.808, 6: 0.612, 12: 0.301, 24: 0.038, 32: 0.008}, "decay": 0.861}
PJ0 = {"source": "artificial-life/research/pj0_germsoma/PJ0_CONCLUSION.html Table 2 (ibm_kingston)",
       "points": {6: 0.870, 12: 0.756, 16: 0.296, 24: 0.193, 28: 0.355, 32: 0.271, 36: 0.220, 40: 0.067,
                  42: 0.068, 46: 0.081, 50: 0.058}, "decay": 0.940}
BIGCATS = {"source": "IBM Big cats, arXiv 2510.09520",
           "points": {100: {"ibm_kingston": 0.55, "ibm_kobe": 0.70}, 120: {"ibm_aachen": 0.56}}}


def tol(s1: float, s2: float) -> float:
    return max(0.03, 2 * math.sqrt(s1 * s1 + s2 * s2))


def full_sim(name: str, method: str) -> AerSimulator:
    return AerSimulator.from_backend(T.get(name).backend, method=method)


def _run_both(isa: list[QuantumCircuit], name: str, shots: int, seed: int, full_method: str):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pcs = [PN.delays_to_pauli(c, name) for c in isa]
        rp, _ = PN.run(pcs, name, shots, seed, prepared=True)
        rf = full_sim(name, full_method).run(isa, shots=shots, seed_simulator=seed, memory=True).result()
    return [WS.bits_of(rp, i) for i in range(len(isa))], [WS.bits_of(rf, i) for i in range(len(isa))]


# ---------------------------------------------------------------------------------------------- AC-4
def pauli_check(name: str, shots: int, dl: B.Deadline) -> dict:
    from dscale.families import ch_qca as Q, ghz_spine as G

    tg = T.get(name)
    draw = F.default_draw()
    rows, twin_rows = [], []
    for N in (6, 12, 20):
        if dl.expired():
            dl.skip(f"pauli ghz N={N}")
            continue
        params = G.PRESETS[40] | {"N": N, "checks": 0, "soma": 1}
        alloc = A.allocate(G.region_request(40, tg, params), tg)
        sj, _ = G._split(G.build(alloc, params, draw), alloc)
        isa = [PN.isa(c, name, 7) for c in sj[:2]]
        bp_, bf = _run_both(isa, name, shots, 11, "matrix_product_state")
        lay = sj[0].metadata["layout"]
        col = {q: k for k, q in enumerate(lay)}
        t0 = G._trees(alloc)[0]
        cols = [col[q] for q in t0["nodes"]]
        edges = [(col[a], col[b]) for a, b in t0["edges"]]
        for lab, fp, ff in (("<X^N>", WS.parity_expect(bp_[0], cols), WS.parity_expect(bf[0], cols)),
                            ("mean <ZZ>", _zz(bp_[1], edges), _zz(bf[1], edges))):
            d = fp[0] - ff[0]
            rows.append({"circuit": f"ghz-spine N={N}", "observable": lab, "pauli": fp[0], "full": ff[0],
                         "delta": d, "tol": tol(fp[1], ff[1]), "ok": abs(d) <= tol(fp[1], ff[1])})
            print(f"  ghz-spine N={N:2d} {lab:10s} Pauli {fp[0]:+.4f}  full {ff[0]:+.4f}  delta {d:+.4f}  "
                  f"tol {rows[-1]['tol']:.4f}  {'ok' if rows[-1]['ok'] else 'FAIL'}", flush=True)
    for sites in (12, 20):
        if dl.expired():
            dl.skip(f"pauli qca sites={sites}")
            continue
        params = {"sites": sites, "t_max": 2, "t_w": 2, "alpha": math.pi / 2, "rule": "parity"}
        alloc = A.allocate(Q.region_request(40, tg, params), tg)
        sp = Q.spec(Q.patch_of(alloc, tg), params, draw)
        real = Q.circuit(sp, 2, "Z", echo=True)
        twin = Q.circuit(sp, 2, "Z", echo=True, twin=True)
        init = np.zeros(len(sp["nodes"]), np.uint8)
        for q in sp["init"]:
            init[{q: k for k, q in enumerate(sp["nodes"])}[q]] = 1
        isa_t = [PN.isa(twin, name, 7)]
        tp, tf = _run_both(isa_t, name, shots, 13, "matrix_product_state")
        fp, fs = WS.echo_fidelity(tp[0], init)
        ff, fsf = WS.echo_fidelity(tf[0], init)
        d = fp - ff
        rows.append({"circuit": f"ch-qca twin {len(sp['nodes'])} sites t=2 echo", "observable": "echo F",
                     "pauli": fp, "full": ff, "delta": d, "tol": tol(fs, fsf), "ok": abs(d) <= tol(fs, fsf)})
        print(f"  ch-qca twin {len(sp['nodes'])} sites echo F: Pauli {fp:.4f}  full {ff:.4f}  delta {d:+.4f}  "
              f"tol {rows[-1]['tol']:.4f}  {'ok' if rows[-1]['ok'] else 'FAIL'}", flush=True)
        if dl.expired():
            dl.skip(f"real qca sites={sites}")
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isa_r = PN.isa(real, name, 7)
            small = len(sp["nodes"]) <= 12
            meth = "density_matrix" if small else "matrix_product_state"
            # one full-noise MPS call is not interruptible by the deadline: above 12 sites the class check (alive /
            # dead) runs on shots / 8, recorded in the row
            r_shots = shots if small else max(250, shots // 8)
            rr = full_sim(name, meth).run([isa_r], shots=r_shots, seed_simulator=17, memory=True).result()
        fr, frs = WS.echo_fidelity(WS.bits_of(rr, 0), init)
        band = WS.random_band(len(sp["nodes"]), shots)
        alive_t = fp - band > 2 * math.sqrt(fs ** 2 + 1 / shots)
        alive_r = fr - band > 2 * math.sqrt(frs ** 2 + 1 / r_shots)
        twin_rows.append({"sites": len(sp["nodes"]), "twin_pauli_F": fp, "real_full_F": fr, "twin_alive": alive_t,
                          "real_alive": alive_r, "class_match": alive_t == alive_r, "real_shots": r_shots,
                          "isa_cz_real": isa_r.count_ops().get("cz", 0),
                          "isa_cz_twin": isa_t[0].count_ops().get("cz", 0)})
        print(f"  ch-qca real {len(sp['nodes'])} sites echo F (full model) {fr:.4f} vs twin (Pauli) {fp:.4f}: "
              f"class {'match' if alive_t == alive_r else 'MISMATCH'} (alive {alive_r} / {alive_t}); "
              f"ISA CZ real {twin_rows[-1]['isa_cz_real']} twin {twin_rows[-1]['isa_cz_twin']}", flush=True)
    passed = bool(rows) and all(r["ok"] for r in rows) and not dl.truncated
    return {"target": name, "full_model": f"AerSimulator.from_backend({T.FAKES[name]})", "pauli_vs_full": rows,
            "twin_vs_real": twin_rows, "passed": passed,
            "verdict": "validated" if passed else "unvalidated (Pauli / twin verdicts above 24 q are labelled so)"}


def _zz(bits: np.ndarray, edges) -> tuple[float, float]:
    vals = [WS.parity_expect(bits, [a, b]) for a, b in edges]
    return float(np.mean([v for v, _ in vals])), float(math.sqrt(sum(s * s for _, s in vals)) / len(vals))


# ---------------------------------------------------------------------------------------------- AC-5
def chain_circuit(path: list[int], W: int, kind: str) -> QuantumCircuit:
    """Re-derived chain setups on a 2W-qubit physical path (approximations, no artificial-life code).
    kind 'pj0': germ GHZ on the first W chain qubits (clone = CX along the chain, mut 0), separable idle soma on the
    other W (no gate to the germ); witness <X^W> on the germ.
    kind 'qalife': GHZ over all 2W chain qubits (germ clone + cx(g,p) phenotype copy), Ry(0.08) per germ;
    witness <X^{2W}>."""
    n = 2 * W
    qc = QuantumCircuit(n, n, name=f"{kind}_W{W}")
    if kind == "pj0":
        qc.h(0)
        for k in range(1, W):
            qc.cx(k - 1, k)
        for k in range(W, n):
            qc.ry(0.6, k)                                     # separable soma trait (value irrelevant to the witness)
        meas = list(range(W))
    else:
        qc.h(0)
        for k in range(1, n):
            qc.cx(k - 1, k)
        for k in range(0, n, 2):
            qc.ry(0.08, k)
        meas = list(range(n))
    for k in meas:
        qc.h(k)
    for k in range(n):
        qc.measure(k, k)
    qc.metadata = {"layout": list(path), "witness_cols": meas}
    return qc


def backtest(shots: int, dl: B.Deadline, targets=("kingston", "marrakesh")) -> list[dict]:
    from dscale.families import ghz_spine as G

    jobs = []
    for name in targets:
        for W in QALIFE["points"]:
            jobs.append((2 * W, "qalife", name, W))
        for W in PJ0["points"]:
            jobs.append((2 * W, "pj0", name, W))
        for N in BIGCATS["points"]:
            jobs.append((N, "bigcats", name, N))
    jobs.sort(key=lambda x: (x[0], x[1], x[2]))
    rows = []
    for nq, kind, name, W in jobs:
        if dl.expired():
            dl.skip(f"backtest {kind} {name} {nq} q")
            continue
        tg = T.get(name)
        g, _ = A.prune(tg)
        try:
            if kind == "bigcats":
                draw = F.default_draw()
                params = {"N": W, "checks": 8, "soma": 1, "m": 8}
                alloc = A.allocate(G.region_request(120, tg, params), tg, fit=False)
                cell = G.run_job(alloc, params, draw, f"pauli:{name}", name, shots, 5)
                meas = BIGCATS["points"][W]
                rows.append({"source": BIGCATS["source"], "setup": "Big Cats", "target": name, "n": W,
                             "measured": meas, "predicted": cell["F_dfe"], "sigma": cell["F_sigma_dfe"],
                             "kept_fraction": cell["kept_fraction"], "n_checks": cell["n_checks"],
                             "observable": "GHZ fidelity (DFE, m = 8; post-selected on the checks)"})
            else:
                path = A.path(g, tg, nq, time_box=20)["nodes"]
                qc = chain_circuit(path, W, kind)
                isa = PN.isa(qc, name, 3)
                r, _ = PN.run([PN.delays_to_pauli(isa, name)], name, shots, 5, prepared=True)
                v, se = WS.parity_expect(WS.bits_of(r, 0), qc.metadata["witness_cols"])
                src = QALIFE if kind == "qalife" else PJ0
                rows.append({"source": src["source"], "setup": "QALife 2018 (re-derived)" if kind == "qalife"
                             else "PJ0 lean", "target": name, "n": W, "qubits": nq, "measured": src["points"][W],
                             "predicted": v, "sigma": se, "observable": "<X^{2W}>" if kind == "qalife" else "<X^W>"})
        except A.Infeasible as e:
            rows.append({"setup": kind, "target": name, "n": W, "error": str(e)})
            print(f"  {kind:8s} {name:9s} n={W:3d}: infeasible ({e})")
            continue
        r = rows[-1]
        m = r["measured"] if not isinstance(r["measured"], dict) else ", ".join(f"{k} {v}" for k, v in r["measured"].items())
        print(f"  {r['setup']:24s} {name:9s} n={W:3d}: predicted {r['predicted']:+.4f} +- {r['sigma']:.4f}   "
              f"measured {m}", flush=True)
    return rows


def fit_decay(rows: list[dict], setup: str, target: str) -> float | None:
    pts = [(r["n"], r["predicted"]) for r in rows if r.get("setup", "").startswith(setup) and r["target"] == target
           and "predicted" in r and r["predicted"] > 0.02]
    if len(pts) < 2:
        return None
    x, y = np.array(pts, float).T
    slope = np.polyfit(x, np.log(y), 1)[0]
    return float(np.exp(slope))


def backtest_figure(rows: list[dict], out: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, setup, src in ((axes[0], "QALife", QALIFE), (axes[1], "PJ0", PJ0)):
        ax.plot(list(src["points"]), list(src["points"].values()), "ks-", label="measured (ibm_kingston)")
        for name, c in (("kingston", "#1f77b4"), ("marrakesh", "#d62728")):
            pr = [(r["n"], r["predicted"], r["sigma"]) for r in rows
                  if r.get("setup", "").startswith(setup) and r["target"] == name and "predicted" in r]
            if pr:
                x, y, s = np.array(pr).T
                ax.errorbar(x, y, s, fmt="o--", color=c, label=f"predicted (Pauli-twirled {name})")
        ax.set_xlabel("width W")
        ax.set_ylabel("witness")
        ax.set_title(f"{setup} ladder: predicted vs measured", fontsize=9)
        ax.legend(fontsize=7)
    ax = axes[2]
    for r in rows:
        if r.get("setup") == "Big Cats" and "predicted" in r:
            ax.errorbar(r["n"] + (2 if r["target"] == "marrakesh" else 0), r["predicted"], r["sigma"], fmt="o",
                        label=f"predicted {r['target']}")
    for n, d in BIGCATS["points"].items():
        for dev, v in d.items():
            ax.plot(n, v, "k*", ms=10)
            ax.annotate(dev, (n, v), fontsize=7)
    ax.axhline(0.5, color="k", ls=":", lw=0.8)
    ax.set_xlabel("GHZ qubits")
    ax.set_ylabel("GHZ fidelity")
    ax.set_title("Big Cats: predicted (dots) vs measured (stars)", fontsize=9)
    fig.suptitle("D-SCALE hardware back-test (simulated: Pauli-twirled noise, stabilizer); a report, not a gate",
                 fontsize=10)
    fig.tight_layout()
    out.mkdir(parents=True, exist_ok=True)
    f = out / "hw_backtest.png"
    fig.savefig(f, dpi=110)
    plt.close(fig)
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pauli", action="store_true")
    ap.add_argument("--backtest", action="store_true")
    ap.add_argument("--target", default="marrakesh", choices=[t for t in T.NAMES if t != "helios-class"])
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    B.add_args(ap)
    a = ap.parse_args()
    dl = B.check(a, default_repeats=1)
    f = a.out / "noise_validation.json"
    rec = json.loads(f.read_text()) if f.exists() else {}
    if a.pauli:
        print(f"AC-4: Pauli-twirled model vs AerSimulator.from_backend on {a.target}, {a.shots} shots")
        rec |= pauli_check(a.target, a.shots, dl)
        print(f"verdict: {rec['verdict']}")
    if a.backtest:
        print(f"AC-5 back-test (report, not a gate), {a.shots} shots")
        rows = backtest(a.shots, dl)
        fits = {f"{s}:{t}": fit_decay(rows, s, t) for s in ("QALife", "PJ0") for t in ("kingston", "marrakesh")}
        for k, v in fits.items():
            ref = QALIFE["decay"] if k.startswith("QALife") else PJ0["decay"]
            print(f"  fitted decay per W {k:16s}: {'n/a' if v is None else f'{v:.3f}'}  (measured fit {ref})")
        fig = backtest_figure(rows, a.out / "figures")
        rec |= {"backtest": rows, "backtest_decay": fits, "backtest_figure": str(fig)}
        print("figure:", fig)
    rec |= {"truncated": dl.truncated, "skipped": dl.skipped}
    a.out.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rec, indent=1, default=str))
    print("wrote", f, "\n" + dl.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
