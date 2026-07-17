#!/usr/bin/env python3
"""
11 — CHSH Game / Bell Inequality  (measuring quantum's advantage as a number)

THE IDEA
    Can the correlations of entangled qubits be explained by "hidden
    variables" — secret values decided in advance? The CHSH inequality answers
    NO, and turns it into a measurable score S:
        * any classical / local-hidden-variable strategy obeys  |S| <= 2
        * quantum entanglement reaches                          |S| = 2*sqrt(2) ~ 2.828
    Beating 2 is a hard, experimental proof that the world is not classical.
    Practically, the same test certifies that a quantum device is "really
    quantum" (device-independent security).

HOW IT WORKS
    Share a Bell pair. Alice randomly measures along one of two axes (a0, a1);
    Bob along one of two axes (b0, b1). For each of the 4 combinations we
    estimate the correlation:
        E = P(agree) - P(disagree)
    Then combine:  S = E(a0,b0) + E(a0,b1) + E(a1,b0) - E(a1,b1).

    Measuring "along an axis at angle phi" = rotate the qubit by Ry(-phi)
    first, then measure in the usual Z basis. The optimal angles below give
    the maximal quantum violation.

EXPECT
    S ~ 2.83 (> 2), impossible for any classical strategy.
"""
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler
from _common import RESULT_DIR, GRAPH_DIR, SEED

SHOTS = 8192

# measurement axes (angle from Z, in the X-Z plane) — the CHSH-optimal set
a_angles = {"a0": 0.0,          "a1": np.pi / 2}
b_angles = {"b0": np.pi / 4,    "b1": -np.pi / 4}


def correlation(theta_a, theta_b):
    """Estimate E = <A*B> for a Bell pair measured along the two given axes."""
    qc = QuantumCircuit(2, 2)
    qc.h(0)                     # Bell pair
    qc.cx(0, 1)
    qc.ry(-theta_a, 0)          # rotate Alice's measurement axis
    qc.ry(-theta_b, 1)          # rotate Bob's measurement axis
    qc.measure([0, 1], [0, 1])
    res = StatevectorSampler(seed=SEED).run([qc], shots=SHOTS).result()
    counts = res[0].data.c.get_counts()
    total = sum(counts.values())
    # agree = "00"/"11" (outcomes equal), disagree = "01"/"10"
    agree = counts.get("00", 0) + counts.get("11", 0)
    disagree = counts.get("01", 0) + counts.get("10", 0)
    return (agree - disagree) / total


E = {
    "E(a0,b0)": correlation(a_angles["a0"], b_angles["b0"]),
    "E(a0,b1)": correlation(a_angles["a0"], b_angles["b1"]),
    "E(a1,b0)": correlation(a_angles["a1"], b_angles["b0"]),
    "E(a1,b1)": correlation(a_angles["a1"], b_angles["b1"]),
}
S = E["E(a0,b0)"] + E["E(a0,b1)"] + E["E(a1,b0)"] - E["E(a1,b1)"]

os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(GRAPH_DIR, exist_ok=True)

payload = {
    "algorithm": "11 — CHSH / Bell inequality",
    "file": "11_chsh",
    "backend": "qiskit StatevectorSampler (local, ideal, no noise)",
    "seed": SEED,
    "shots_per_setting": SHOTS,
    "classical_bound": 2.0,
    "quantum_max": round(2 * np.sqrt(2), 4),
    "correlations": {k: round(v, 4) for k, v in E.items()},
    "S": round(S, 4),
    "note": "S ~ 2.83 beats the classical limit of 2 -> the correlations "
            "cannot come from any local hidden-variable theory.",
}
with open(os.path.join(RESULT_DIR, "11_chsh.json"), "w") as f:
    json.dump(payload, f, indent=2)

# graph: the CHSH score against both bounds
plt.figure(figsize=(5, 4))
plt.bar(["measured S"], [abs(S)], color="#4C72B0", width=0.5)
plt.axhline(2.0, ls="--", color="#C44E52", lw=1.5)
plt.text(0.45, 2.03, "classical limit = 2", color="#C44E52", fontsize=8, ha="right")
plt.axhline(2 * np.sqrt(2), ls=":", color="gray", lw=1.5)
plt.text(0.45, 2 * np.sqrt(2) + 0.03, "quantum max = 2√2", color="gray",
         fontsize=8, ha="right")
plt.text(0, abs(S) - 0.15, f"{abs(S):.3f}", ha="center", va="top", color="white")
plt.ylim(0, 3.2)
plt.ylabel("CHSH score S")
plt.title("11 — CHSH: quantum beats the classical bound")
plt.tight_layout()
plt.savefig(os.path.join(GRAPH_DIR, "11_chsh.png"), dpi=110)
plt.close()

print("=== 11 — CHSH ===")
for k, v in E.items():
    print(f"  {k} = {v:+.3f}")
print(f"  S = {S:.4f}   (classical <= 2, quantum max = {2*np.sqrt(2):.4f})")
print("  result -> ../result/11_chsh.json")
print("  graph  -> ../graph/11_chsh.png")
