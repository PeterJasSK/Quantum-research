#!/usr/bin/env python3
"""
08 — BB84 Quantum Key Distribution  (unbreakable key sharing)

THE IDEA
    BB84 (Bennett & Brassard, 1984) is the first and most famous quantum
    cryptography protocol — and it is deployed in real hardware today. Two
    parties build a shared secret key, and the laws of quantum mechanics
    guarantee that any eavesdropper is DETECTED, because measuring a qubit in
    the wrong basis disturbs it.

HOW IT WORKS
    For each bit Alice picks a random bit and a random basis (Z = {0,1},
    X = {+,-}) and sends the encoded qubit. Bob measures in his own random
    basis. Afterwards they publicly compare bases (not values) and KEEP only
    the bits where their bases matched — the "sifted key". Those bits agree.

    An eavesdropper (Eve) who measures in transit must guess the basis. When
    she guesses wrong she scrambles the qubit, injecting errors into the
    sifted key. Alice and Bob sacrifice a few key bits to estimate the error
    rate: ~0% means the line is clean, ~25% screams "eavesdropper!".

THIS DEMO
    Runs the protocol twice over the same random choices: once with NO Eve,
    once WITH Eve. It reports the sifted-key error rate for each. Everything
    runs on the local simulator; a fixed seed makes it reproducible.
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

N = 48                          # number of transmitted qubits (raw)


def measure_bit(prep_bit, prep_basis, meas_basis, shot_seed):
    """Prepare a qubit (bit in a basis), measure it in meas_basis, return 0/1."""
    qc = QuantumCircuit(1, 1)
    if prep_bit:
        qc.x(0)
    if prep_basis == "X":       # encode in the diagonal basis
        qc.h(0)
    if meas_basis == "X":       # rotate diagonal -> computational before measuring
        qc.h(0)
    qc.measure(0, 0)
    res = StatevectorSampler(seed=shot_seed).run([qc], shots=1).result()
    outcome = list(res[0].data.c.get_counts())[0]   # only one key (shots=1)
    return int(outcome)


def run_protocol(eve, rng):
    a_bits = rng.integers(0, 2, N)
    a_bases = rng.choice(["Z", "X"], N)
    b_bases = rng.choice(["Z", "X"], N)
    e_bases = rng.choice(["Z", "X"], N)

    bob_bits = []
    for i in range(N):
        prep_bit, prep_basis = int(a_bits[i]), a_bases[i]
        if eve:
            # Eve intercepts, measures in her basis, then resends what she saw
            e_bit = measure_bit(prep_bit, prep_basis, e_bases[i], SEED + 1000 + i)
            prep_bit, prep_basis = e_bit, e_bases[i]
        bob_bits.append(measure_bit(prep_bit, prep_basis, b_bases[i], SEED + i))

    # sift: keep positions where Alice's and Bob's bases agree
    sifted_a, sifted_b = [], []
    for i in range(N):
        if a_bases[i] == b_bases[i]:
            sifted_a.append(int(a_bits[i]))
            sifted_b.append(bob_bits[i])
    errors = sum(x != y for x, y in zip(sifted_a, sifted_b))
    rate = errors / len(sifted_a) if sifted_a else 0.0
    return {
        "sifted_len": len(sifted_a),
        "errors": errors,
        "error_rate": round(rate, 4),
        "alice_sifted_key": "".join(map(str, sifted_a)),
        "bob_sifted_key": "".join(map(str, sifted_b)),
    }


clean = run_protocol(eve=False, rng=np.random.default_rng(SEED))
tapped = run_protocol(eve=True, rng=np.random.default_rng(SEED))

os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(GRAPH_DIR, exist_ok=True)

payload = {
    "algorithm": "08 — BB84 Quantum Key Distribution",
    "file": "08_bb84",
    "backend": "qiskit StatevectorSampler (local, ideal, no noise)",
    "seed": SEED,
    "raw_qubits": N,
    "note": "Clean line -> 0% sifted-key errors. Eavesdropper -> ~25% errors "
            "(detected). That detectability is the security guarantee.",
    "no_eavesdropper": clean,
    "with_eavesdropper": tapped,
}
with open(os.path.join(RESULT_DIR, "08_bb84.json"), "w") as f:
    json.dump(payload, f, indent=2)

# graph: sifted-key error rate, clean vs eavesdropped
plt.figure(figsize=(5, 4))
bars = plt.bar(["no eavesdropper", "with eavesdropper"],
               [clean["error_rate"], tapped["error_rate"]],
               color=["#4C72B0", "#C44E52"])
for b, v in zip(bars, [clean["error_rate"], tapped["error_rate"]]):
    plt.text(b.get_x() + b.get_width() / 2, v, f"{v:.0%}", ha="center", va="bottom")
plt.axhline(0.25, ls="--", color="gray", lw=1)
plt.text(1.4, 0.255, "25% alarm", color="gray", fontsize=8, ha="right")
plt.ylim(0, 0.4)
plt.ylabel("sifted-key error rate")
plt.title("08 — BB84: eavesdropping shows up as errors")
plt.tight_layout()
plt.savefig(os.path.join(GRAPH_DIR, "08_bb84.png"), dpi=110)
plt.close()

print("=== 08 — BB84 ===")
print(f"  clean line     : sifted {clean['sifted_len']} bits, "
      f"error rate {clean['error_rate']:.0%}")
print(f"  eavesdropped   : sifted {tapped['sifted_len']} bits, "
      f"error rate {tapped['error_rate']:.0%}")
print(f"  alice key (clean): {clean['alice_sifted_key']}")
print(f"  bob   key (clean): {clean['bob_sifted_key']}")
print("  result -> ../result/08_bb84.json")
print("  graph  -> ../graph/08_bb84.png")
