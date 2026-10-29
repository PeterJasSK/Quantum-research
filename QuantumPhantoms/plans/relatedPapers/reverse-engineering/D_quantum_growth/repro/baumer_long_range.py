"""Reproduction #8 (AC-3): Baumer et al. constant-depth long-range Bell pair [HW05], dynamic vs unitary.

    python -m D_quantum_growth.repro.baumer_long_range [--shots N] [--nmax 12]

Distance n = number of qubits on a FakeMarrakesh heavy-hex path; the Bell pair sits on its two end qubits.
  dynamic: Bell pairs on (q0,q1),(q2,q3),..., Bell measurements between neighbouring pairs (CNOT, H, measure), parity
           feed-forward (if_test X / Z on the far end): constant depth. Odd n: even-(n-1) construction + 1 SWAP.
  unitary: Bell(q0,q1) then a SWAP chain to the far end (depth O(n)).
Fidelity F = (1 + <XX> - <YY> + <ZZ>)/4 from the three end-qubit parities, ideal and Heron-class noise.
"""
from __future__ import annotations

import argparse
import json

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile

from D_quantum_growth.src import heavyhex
from shared import RE_ROOT
from shared.seedhash import derive_seed
from shared.simbackend import fake_backend, make_simulator, sim_label

FIG = RE_ROOT / "D_quantum_growth" / "figures" / "baumer_fidelity_vs_distance.png"
PAPER = ("Baumer et al. [HW05] Fig. 1(c) (CNOT teleportation on ibm_sherbrooke): dynamic circuits beat the unitary "
         "version for chains >~ 10 qubits; for GHZ preparation no crossover was found (genuine entanglement to 6 qubits).")


def end_basis(qc, q, b):
    if b == "X":
        qc.h(q)
    elif b == "Y":
        qc.sdg(q); qc.h(q)


def _cnot(qc, a, b):
    qc.h(b); qc.cz(a, b); qc.h(b)


def dynamic(n: int, basis: str) -> QuantumCircuit:
    m = n if n % 2 == 0 else n - 1
    q = QuantumRegister(n, "q")
    nb = max(m // 2 - 1, 0)
    c_a = ClassicalRegister(max(nb, 1), "a")
    c_b = ClassicalRegister(max(nb, 1), "b")
    c_e = ClassicalRegister(2, "e")
    qc = QuantumCircuit(q, c_a, c_b, c_e)
    for k in range(0, m, 2):
        qc.h(q[k]); _cnot(qc, q[k], q[k + 1])
    for k in range(nb):                                   # BSM between pairs k and k+1: qubits 2k+1, 2k+2
        x, y = q[2 * k + 1], q[2 * k + 2]
        _cnot(qc, x, y); qc.h(x)
        qc.measure(x, c_a[k]); qc.measure(y, c_b[k])
    for k in range(nb):
        with qc.if_test((c_b[k], 1)):
            qc.x(q[m - 1])
        with qc.if_test((c_a[k], 1)):
            qc.z(q[m - 1])
    if n != m:                                            # odd: move the far end one qubit along
        _cnot(qc, q[m - 1], q[m]); _cnot(qc, q[m], q[m - 1]); _cnot(qc, q[m - 1], q[m])
    end_basis(qc, q[0], basis); end_basis(qc, q[n - 1], basis)
    qc.measure(q[0], c_e[0]); qc.measure(q[n - 1], c_e[1])
    return qc


def unitary(n: int, basis: str) -> QuantumCircuit:
    q = QuantumRegister(n, "q"); c = ClassicalRegister(2, "e")
    qc = QuantumCircuit(q, c)
    qc.h(q[0]); _cnot(qc, q[0], q[1])
    for k in range(1, n - 1):
        _cnot(qc, q[k], q[k + 1]); _cnot(qc, q[k + 1], q[k]); _cnot(qc, q[k], q[k + 1])
    end_basis(qc, q[0], basis); end_basis(qc, q[n - 1], basis)
    qc.measure(q[0], c[0]); qc.measure(q[n - 1], c[1])
    return qc


def fidelity(counts_by_basis: dict[str, dict]) -> tuple[float, float]:
    ev, var = {}, 0.0
    for b, cts in counts_by_basis.items():
        tot = sum(cts.values())
        e = sum(v * (1 - 2 * ((int(k.split()[0], 2) ^ (int(k.split()[0], 2) >> 1)) & 1)) for k, v in cts.items()) / tot
        ev[b] = e
        var += (1 - e * e) / tot
    return (1 + ev["X"] - ev["Y"] + ev["Z"]) / 4, float(np.sqrt(var) / 4)


def run(mode: str, ns, shots: int) -> dict:
    out = {}
    seed = int(derive_seed("00" * 32, f"baumer-{mode}") % 2 ** 31)
    for kind, build in (("dynamic", dynamic), ("unitary", unitary)):
        out[kind] = {}
        for n in ns:
            path = heavyhex.path(n)
            circs = [transpile(build(n, b), backend=fake_backend(), initial_layout=path, optimization_level=1,
                               seed_transpiler=seed) for b in "XYZ"]
            res = make_simulator(mode).run(circs, shots=shots, seed_simulator=seed).result()
            F, se = fidelity({b: res.get_counts(i) for i, b in enumerate("XYZ")})
            depth = max(c.depth() for c in circs)
            out[kind][n] = {"F": F, "se": se, "depth": depth}
            print(f"  {mode:5s} {kind:8s} n={n:2d} F={F:.4f}+-{se:.4f} depth={depth}")
    return out


def crossover(res: dict) -> int | None:
    """First n > 2 where dynamic beats unitary by more than 2 combined standard errors (else None)."""
    for n in sorted(res["dynamic"]):
        d, u = res["dynamic"][n], res["unitary"][n]
        if n > 2 and d["F"] - u["F"] > 2 * float(np.hypot(d["se"], u["se"])):
            return n
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shots", type=int, default=4000)
    ap.add_argument("--nmax", type=int, default=12)
    ap.add_argument("--modes", nargs="*", default=["ideal", "heron"])
    a = ap.parse_args()
    ns = list(range(2, a.nmax + 1))
    allres = {m: run(m, ns, a.shots) for m in a.modes}
    fig, ax = plt.subplots(1, len(a.modes), figsize=(5.2 * len(a.modes), 3.8), squeeze=False)
    for k, m in enumerate(a.modes):
        r = allres[m]
        for kind, col in (("dynamic", "C0"), ("unitary", "C3")):
            ax[0][k].errorbar(ns, [r[kind][n]["F"] for n in ns], [r[kind][n]["se"] for n in ns], fmt="o-", color=col,
                              label=kind)
        ax[0][k].axhline(0.5, color="gray", ls=":", lw=0.8)
        ax[0][k].set_xlabel("chain length n (qubits)"); ax[0][k].set_ylabel("Bell fidelity")
        ax[0][k].set_title(sim_label(m), fontsize=8); ax[0][k].legend()
    fig.suptitle("Long-range Bell pair: dynamic (constant depth) vs unitary SWAP chain", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG, dpi=130)
    summary = {m: {"crossover_n": crossover(allres[m]), "results": allres[m]} for m in a.modes}
    (RE_ROOT / "D_quantum_growth" / "figures" / "baumer_summary.json").write_text(json.dumps(summary, indent=1))
    print("paper:", PAPER)
    for m in a.modes:
        print(f"{sim_label(m)}: dynamic>unitary first at n = {summary[m]['crossover_n']}; ideal dynamic F range "
              f"{min(v['F'] for v in allres[m]['dynamic'].values()):.4f}..{max(v['F'] for v in allres[m]['dynamic'].values()):.4f}")


if __name__ == "__main__":
    main()
