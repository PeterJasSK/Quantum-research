"""Clean traveling-wavepacket data for the PJ1 visual study.

Single-excitation-per-organism subspace of the one-hot soma walker == a 1-D lattice
hopping model. Two particles A,B on an L-site lattice, opposite momenta, meet in the
middle. On-site interaction U*n_A n_B entangles/scatters them on contact. This is
mathematically the same dynamics the real circuit runs (single excitation each),
just tuned + longer so the motion is LEGIBLE: a lump glides, they meet, they react.

Arms:
  none       U=0  -> packets pass through, no entanglement (control)
  soma_soma  U>0  -> scatter + entangle on contact; germ untouched -> witness stays 1
  germ_routed U>0 + contact dephases the germ -> witness collapses (schematic verdict)
Outputs occA[x], occB[x] (real), entanglement entropy (real), witness per arm.
"""
import json, numpy as np

L = 25
X = np.arange(L)
FRAMES = 46
DT = 0.16
T0 = 1.0            # hopping
K = 1.15           # momentum kick
SIG = 2.3          # packet width
xA0, xB0 = 5.0, 19.0
U = 4.0            # contact interaction

def packet(x0, k):
    g = np.exp(-((X - x0) ** 2) / (2 * SIG ** 2)) * np.exp(1j * k * X)
    return g / np.linalg.norm(g)

# 1-D hopping Hamiltonian (open chain)
H1 = np.zeros((L, L), complex)
for i in range(L - 1):
    H1[i, i + 1] = H1[i + 1, i] = -T0

def evolve(U_int):
    psiA, psiB = packet(xA0, K), packet(xB0, -K)
    psi = np.kron(psiA, psiB)                      # L*L
    I = np.eye(L)
    H = np.kron(H1, I) + np.kron(I, H1)
    if U_int:                                       # on-site contact interaction
        diag = np.zeros(L * L)
        for a in range(L):
            diag[a * L + a] = U_int                 # both particles same site
        H = H + np.diag(diag)
    ev, evec = np.linalg.eigh(H)
    step = evec @ np.diag(np.exp(-1j * ev * DT)) @ evec.conj().T
    frames = []
    cum = 0.0
    for f in range(FRAMES):
        M = psi.reshape(L, L)
        occA = (np.abs(M) ** 2).sum(axis=1)
        occB = (np.abs(M) ** 2).sum(axis=0)
        s = np.linalg.svd(M, compute_uv=False)
        p = s ** 2; p = p[p > 1e-12]
        ent = float(-(p * np.log2(p)).sum())
        overlap = float((occA * occB).sum())
        cum += overlap
        frames.append({"a": [round(float(v), 4) for v in occA],
                       "b": [round(float(v), 4) for v in occB],
                       "s": round(ent, 3), "ov": round(overlap, 4), "cum": cum})
        psi = step @ psi
    return frames

none = evolve(0.0)
soma = evolve(U)

def witness(frames, arm):
    out = []
    maxcum = max(fr["cum"] for fr in frames) or 1.0
    for fr in frames:
        if arm in ("none", "soma_soma"):
            w = 1.0                                  # germ untouched -> exact
        else:                                        # germ_routed: contact dephases germ
            w = -0.17 + 1.17 * np.exp(-3.2 * fr["cum"] / maxcum)
        out.append(round(float(w), 4))
    return out

data = {"L": L, "frames": FRAMES, "arms": {}}
for arm, fr in (("none", none), ("soma_soma", soma), ("germ_routed", soma)):
    w = witness(fr, arm)
    data["arms"][arm] = [{"a": fr[i]["a"], "b": fr[i]["b"], "s": fr[i]["s"],
                          "ov": fr[i]["ov"], "w": w[i]} for i in range(FRAMES)]

open("clean.min.json", "w").write(json.dumps(data, separators=(",", ":")))
# summary
for arm in ("none", "soma_soma", "germ_routed"):
    fr = data["arms"][arm]
    peak_ov = max(x["ov"] for x in fr); peak_s = max(x["s"] for x in fr)
    print(f"{arm:12s} peak_overlap {peak_ov:.3f} peak_entropy {peak_s:.2f} "
          f"witness {fr[0]['w']:+.2f}->{fr[-1]['w']:+.2f}")
print("bytes", len(json.dumps(data, separators=(',', ':'))))
