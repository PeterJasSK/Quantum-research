#!/usr/bin/env python3
"""PJ1 spectacle -- the pretty two-body collision (visual only, no witness science).

Strips the arena down to the one thing that looks alive: two quantum walkers on a shared track,
gliding toward each other, meeting, and ENTANGLING on contact. No germ lines, no genealogy witness,
no 3-arm comparison -- just the collision, as smooth and legible as possible.

Physics (honest, and identical to the real one-hot soma walk -- just efficiently computed): each body
is a single excitation on an L-site lattice = the 1-particle sector of the XX+YY hopping model. Two
distinguishable walkers A,B live in the L*L two-particle sector (NOT 2^L qubits -- that's why L can be
large and the sim stays exact + fast). A on-site interaction U*n_A*n_B acts only when both are at the
same site => they scatter and become entangled. Occupancy and the A|B entanglement entropy are read
straight off the two-particle wavefunction. Fat Gaussian packets with opposite momenta make the motion
read as "a lump glides, they meet, they react".

Two arms (a visual toggle, not a study):
  * soma_soma -- U>0: they collide, scatter, and the entanglement meter lights up.
  * none      -- U=0: they glide straight through each other, meter flat (the control, for contrast).

Output: a self-contained wave-bars page (port of plans/pj1Concepts/4_wave-bars_PICKED.html) with the
real frames injected -> research/pj1_spectacle/index.html. CSP-safe, opens from file://.

Usage:
    cd artificial-life/code
    python pj1_spectacle.py                        # default L=26, 48 frames, both arms
    python pj1_spectacle.py --sites 30 --frames 60 --arms soma_soma
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TEMPLATE = os.path.join(_ROOT, "plans", "pj1Concepts", "4_wave-bars_PICKED.html")
_DEFAULT_OUT = os.path.join(_ROOT, "research", "pj1_spectacle")


def _packet(x_sites: np.ndarray, x0: float, k: float, sig: float) -> np.ndarray:
    """A Gaussian wave packet centred at x0 with momentum kick k and width sig (normalized)."""
    g = np.exp(-((x_sites - x0) ** 2) / (2 * sig ** 2)) * np.exp(1j * k * x_sites)
    return g / np.linalg.norm(g)


def simulate(sites: int, frames: int, *, u_int: float, dt: float = 0.14, hop: float = 1.0,
             kick: float = 1.2, sig: float = 2.6) -> list[dict]:
    """Evolve two packets in the L*L two-particle sector; return per-frame occupancy + entropy."""
    x = np.arange(sites)
    psi = np.kron(_packet(x, 0.20 * (sites - 1), kick, sig),
                  _packet(x, 0.80 * (sites - 1), -kick, sig))          # opposite ends, toward centre

    h1 = np.zeros((sites, sites), complex)                             # 1-D nearest-neighbour hopping
    for i in range(sites - 1):
        h1[i, i + 1] = h1[i + 1, i] = -hop
    eye = np.eye(sites)
    ham = np.kron(h1, eye) + np.kron(eye, h1)
    if u_int:
        diag = np.zeros(sites * sites)
        for a in range(sites):
            diag[a * sites + a] = u_int                               # both walkers on the same site
        ham = ham + np.diag(diag)
    evals, evecs = np.linalg.eigh(ham)
    step = evecs @ np.diag(np.exp(-1j * evals * dt)) @ evecs.conj().T

    out: list[dict] = []
    for _ in range(frames):
        m = psi.reshape(sites, sites)
        occ_a = (np.abs(m) ** 2).sum(axis=1)
        occ_b = (np.abs(m) ** 2).sum(axis=0)
        sv = np.linalg.svd(m, compute_uv=False)                       # Schmidt spectrum of A|B
        p = sv ** 2
        p = p[p > 1e-12]
        ent = float(-(p * np.log2(p)).sum())                          # entanglement entropy (bits)
        overlap = float((occ_a * occ_b).sum())
        out.append({
            "a": [round(float(v), 4) for v in occ_a],
            "b": [round(float(v), 4) for v in occ_b],
            "s": round(ent, 3),
            "ov": round(overlap, 4),
            "w": 1.0,                                                  # both walkers stay globally pure
        })
        psi = step @ psi
    return out


def render(data: dict, out_dir: str) -> str:
    """Inject `data` into the picked wave-bars template; drop the germ_routed (science) button;
    write a self-contained index.html."""
    with open(_TEMPLATE) as f:
        template = f.read()
    import re
    present = set(data["arms"])
    literal = "const DATA = " + json.dumps(data, separators=(",", ":")) + ";"
    lines = template.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("const DATA ="):
            indent = line[:len(line) - len(line.lstrip())]
            lines[i] = indent + literal
        m = re.search(r'data-arm="(\w+)"', line)                      # keep only built arms' buttons
        if m and m.group(1) not in present:
            lines[i] = ""
    html = "\n".join(lines)
    if "soma_soma" not in present:                                    # keep the default arm valid
        html = html.replace("setArm('soma_soma')", f"setArm('{next(iter(present))}')")
    head = ('<!doctype html>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    with open(out, "w") as f:
        f.write(head + html + "\n")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the PJ1 two-body collision spectacle (visual "
                                             "only; no witness science).")
    ap.add_argument("--sites", type=int, default=26, help="track length L (bigger = fatter/prettier)")
    ap.add_argument("--frames", type=int, default=48, help="animation frames (more = smoother)")
    ap.add_argument("--arms", type=str, default="none,soma_soma",
                    help="comma list: soma_soma (collide) and/or none (pass-through toggle)")
    ap.add_argument("--u", type=float, default=5.0, help="on-site collision strength")
    ap.add_argument("--out-dir", dest="out_dir", default=_DEFAULT_OUT)
    args = ap.parse_args()

    if not os.path.exists(_TEMPLATE):
        print(f"[FAIL] picked template not found: {_TEMPLATE}")
        return 1

    arms = [a for a in args.arms.split(",") if a.strip()]
    data = {"L": args.sites, "frames": args.frames, "arms": {}}
    for arm in arms:
        u = args.u if arm == "soma_soma" else 0.0
        frames = simulate(args.sites, args.frames, u_int=u)
        data["arms"][arm] = frames
        peak_s = max(f["s"] for f in frames)
        peak_ov = max(f["ov"] for f in frames)
        print(f"  {arm:12} peak_entanglement={peak_s:.2f} bits  peak_overlap={peak_ov:.3f}")

    out = render(data, args.out_dir)
    print(f"[OK] wrote {out}  (L={args.sites} frames={args.frames} arms={arms})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
