"""PJ1 exploratory prototype (SIM ONLY, throwaway) -- two germ/soma organisms colliding.

Purpose: preview the DEMO output + visualization, NOT the real numbers. Small W.
Layout per organism o: [germ(W)] [soma(S)]  (mirrors pj_qalife organism_base).
- germ  = GHZ genotype chain, carries the entanglement witness <X^W> (X basis).
- soma  = one-hot position register on an S-site track (a quantum walker = the BODY).
Movement  = XX+YY hopping (excitation-conserving quantum walk) -- Trotterized in time.
Collision = XX+YY exchange between the two somas at ALIGNED track sites (energy transfer).
            This is a Hamiltonian term that is ALWAYS present at shared sites -- it only
            has effect when both walkers have amplitude there. Emergent contact, no if().
A/B arm   = 'germ_routed' instead couples the collision to a GERM qubit -> kills the witness.
"""
from __future__ import annotations
import json, math, sys
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, Pauli, partial_trace, entropy

W = 2            # germ qubits per organism (small for sim preview)
S = 5            # soma track sites per organism (one-hot)
ORG = 2
DT = 0.35        # trotter time step
J_HOP = 1.0      # walker hopping strength
J_COLL = 1.3     # collision coupling strength
FRAMES = 22
MUT = 0.15       # tiny mutation angle so germ isn't a perfect GHZ

def qmap(o, kind, i):
    base = o * (W + S)
    return base + (i if kind == "germ" else W + i)

def prep(qc):
    # germ GHZ + mutation (both organisms)
    for o in range(ORG):
        qc.ry(math.pi / 2, qmap(o, "germ", 0))
        for k in range(1, W):
            qc.cx(qmap(o, "germ", k - 1), qmap(o, "germ", k))
        for k in range(W):
            qc.ry(MUT, qmap(o, "germ", k))
    # soma walkers: A starts far-left (site 0), B parked off-center (site S-2)
    # asymmetric start -> breaks mirror symmetry -> visible NET energy transfer on contact
    qc.x(qmap(0, "soma", 0))
    qc.x(qmap(1, "soma", S - 2))

def hop_layer(qc, coll_mode):
    th = 2 * J_HOP * DT
    for o in range(ORG):
        for j in range(S - 1):
            a, b = qmap(o, "soma", j), qmap(o, "soma", j + 1)
            qc.rxx(th, a, b); qc.ryy(th, a, b)
    # collision: exchange between the two bodies at aligned sites
    thc = 2 * J_COLL * DT
    for j in range(S):
        a, b = qmap(0, "soma", j), qmap(1, "soma", j)
        if coll_mode == "soma_soma":
            qc.rxx(thc, a, b); qc.ryy(thc, a, b)
        elif coll_mode == "germ_routed":
            # WRONG-BY-DESIGN A/B: route contact through a germ qubit -> touches the witness
            g = qmap(1, "germ", 0)
            qc.rxx(thc, a, g); qc.ryy(thc, a, g)
        # coll_mode == 'none' -> walkers pass through each other, no interaction

def germ_witness(sv):
    # joint <X^(2W)> over ALL germ qubits, and per-organism, and separable null
    n = 2 * (W + S)
    def exp_X(qubits):
        label = ["I"] * n
        for q in qubits:
            label[q] = "X"
        return float(np.real(sv.expectation_value(Pauli("".join(reversed(label))))))
    allg = [qmap(o, "germ", k) for o in range(ORG) for k in range(W)]
    a = [qmap(0, "germ", k) for k in range(W)]
    b = [qmap(1, "germ", k) for k in range(W)]
    joint = exp_X(allg)
    # separable null = product of single-qubit <X>
    sep = 1.0
    for q in allg:
        sep *= exp_X([q])
    return joint, exp_X(a), exp_X(b), sep

def occupancy(sv):
    # per-organism site occupancy = <n_j> = P(soma qubit j == |1>), via cheap marginals
    occ = np.zeros((ORG, S))
    tot = np.zeros(ORG)
    for o in range(ORG):
        for j in range(S):
            q = qmap(o, "soma", j)
            p1 = float(sv.probabilities([q])[1])
            occ[o, j] = p1; tot[o] += p1
    return occ, tot

def run(coll_mode):
    # incremental evolution: build state once, evolve one layer per frame (O(frames))
    n = 2 * (W + S)
    p = QuantumCircuit(n); prep(p)
    sv = Statevector(p)
    layer = QuantumCircuit(n); hop_layer(layer, coll_mode)
    frames = []
    for f in range(FRAMES):
        if f > 0:
            sv = sv.evolve(layer)
        joint, wa, wb, sep = germ_witness(sv)
        occ, tot = occupancy(sv)
        # soma-soma entanglement entropy = the EMERGENT-CONTACT fingerprint (0 apart, >0 on overlap)
        somaA = [qmap(0, "soma", j) for j in range(S)]
        rhoA = partial_trace(sv, [q for q in range(2 * (W + S)) if q not in somaA])
        s_ent = float(entropy(rhoA, base=2))
        frames.append({
            "t": f,
            "occ": occ.tolist(),
            "mass": tot.tolist(),        # total excitation per organism (energy transfer)
            "witness_joint": joint,
            "witness_a": wa, "witness_b": wb,
            "sep_null": sep,
            "soma_entropy": s_ent,
        })
    return frames

out = {"W": W, "S": S, "frames": FRAMES,
       "soma_soma": run("soma_soma"),
       "germ_routed": run("germ_routed"),
       "none": run("none")}
path = sys.argv[1] if len(sys.argv) > 1 else "pj1_proto_out.json"
json.dump(out, open(path, "w"))

# quick text summary
for mode in ("none", "soma_soma", "germ_routed"):
    fr = out[mode]
    w0 = fr[0]["witness_joint"]; wl = fr[-1]["witness_joint"]
    m_a0, m_al = fr[0]["mass"][0], fr[-1]["mass"][0]
    print(f"{mode:12s} joint witness {w0:+.3f} -> {wl:+.3f} | orgA mass {m_a0:.2f} -> {m_al:.2f} | sepnull {fr[-1]['sep_null']:+.1e}")
print("wrote", path)
