"""M15 ring_ansatz, M16 xeb_bits and the R4 runner: information supremacy on the 12-qubit seed hexagon.

Task (2509.07255 [verify]): Alice holds a Haar-random n-qubit state, Bob a random Clifford measurement; the pair
must output heavy strings. Per circuit: prepare a trained hexagon ansatz of the target, apply Bob's Clifford,
measure ONCE. Score eps = mean over circuits of (2^n p_target(x) - 1), p_target computed classically from the
target state (not from the ansatz). A classical message needs bits(eps) bits to reach the same score.

Ansatz (M15): |+>^n, then `layers` x (RZZ brick on alternating ring bonds, RX and RZ on every qubit), trained with
L-BFGS on the exact 2^12 statevector (adjoint gradient). Classical only.

What this implementation does NOT give the theorem (plan X13), and says so in the claim:
  * inputs: the targets and Cliffords are expanded with PCG64 from 64 bits of the run's Bell-test pool (same
    device, drawn before the circuit ran: the setting-independence loophole is open). That is a pseudo-random
    expansion of a short seed. A file of true random bytes in params["randomness_file"] replaces it.
  * bits(eps) (M16) is a straight line through two published points; the constants are not transcribed (gap G9).
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, random_clifford

from common import qhard as QH, quantum as Q, runio
from common.runio import Ctx

BITS_POINTS = ((0.16, 12.0), (0.25, 34.0))        # eps -> classical bits, read off the paper's bound [verify]


def xeb_bits(eps: float, n: int = 12) -> dict:
    """M16 (placeholder until the Supplement's constants are transcribed)."""
    (e0, b0), (e1, b1) = BITS_POINTS
    bits = b0 + (eps - e0) * (b1 - b0) / (e1 - e0)
    return {"eps": eps, "bits": bits, "n": n, "threshold_eps": e0,
            "rigour": "two-point linear reading of 2509.07255 [verify]; not a proven bound"}


# ---------------------------------------------------------------------------------------------- M15 ansatz
def _bonds(n: int, layer: int) -> list[tuple[int, int]]:
    return [(i, (i + 1) % n) for i in range(layer % 2, n, 2)]


def n_params(n: int, layers: int) -> int:
    return layers * (n // 2 + 2 * n)


def _signs(n: int) -> list[np.ndarray]:
    """z_q = +-1 as a broadcastable array; axis of qubit q is n - 1 - q (so reshape(-1) is qiskit's order)."""
    out = []
    for q in range(n):
        shape = [1] * n
        shape[n - 1 - q] = 2
        out.append(np.array([1.0, -1.0]).reshape(shape))
    return out


def _gates(n: int, layers: int) -> list[tuple[str, tuple]]:
    g = []
    for ell in range(layers):
        g += [("zz", b) for b in _bonds(n, ell)]
        g += [("x", (q,)) for q in range(n)]
        g += [("z", (q,)) for q in range(n)]
    return g


def _apply(state: np.ndarray, kind: str, qs: tuple, theta: float, sg: list, n: int) -> np.ndarray:
    """exp(-i theta G / 2) with G = Z Z, X or Z."""
    if kind == "zz":
        return state * np.exp(-0.5j * theta * sg[qs[0]] * sg[qs[1]])
    if kind == "z":
        return state * np.exp(-0.5j * theta * sg[qs[0]])
    return math.cos(theta / 2) * state - 1j * math.sin(theta / 2) * np.flip(state, axis=n - 1 - qs[0])


def _generator(state: np.ndarray, kind: str, qs: tuple, sg: list, n: int) -> np.ndarray:
    if kind == "zz":
        return state * sg[qs[0]] * sg[qs[1]]
    if kind == "z":
        return state * sg[qs[0]]
    return np.flip(state, axis=n - 1 - qs[0])


def ansatz_state(theta: np.ndarray, n: int, layers: int) -> np.ndarray:
    sg = _signs(n)
    psi = np.full((2,) * n, 2 ** (-n / 2), dtype=complex)
    for (kind, qs), th in zip(_gates(n, layers), theta):
        psi = _apply(psi, kind, qs, th, sg, n)
    return psi


def _loss(theta: np.ndarray, target: np.ndarray, n: int, layers: int) -> tuple[float, np.ndarray]:
    """1 - |<target|psi>|^2 and its gradient (adjoint method)."""
    sg = _signs(n)
    gates = _gates(n, layers)
    phi = ansatz_state(theta, n, layers)
    chi = target.copy()
    a = np.vdot(target, phi)
    grad = np.zeros(len(theta))
    for k in range(len(gates) - 1, -1, -1):
        kind, qs = gates[k]
        grad[k] = np.imag(np.conj(a) * np.vdot(chi, _generator(phi, kind, qs, sg, n)))
        phi = _apply(phi, kind, qs, -theta[k], sg, n)
        chi = _apply(chi, kind, qs, -theta[k], sg, n)
    return 1.0 - abs(a) ** 2, -grad


def ring_ansatz(target: np.ndarray, n: int, layers: int, iters: int, g: np.random.Generator) -> tuple[np.ndarray, float]:
    """M15. -> (parameters, ansatz fidelity). target: array of shape (2,) * n."""
    from scipy.optimize import minimize

    x0 = g.uniform(-0.3, 0.3, n_params(n, layers))
    res = minimize(_loss, x0, args=(target, n, layers), jac=True, method="L-BFGS-B", options={"maxiter": int(iters)})
    return res.x, float(1.0 - res.fun)


def ansatz_circuit(theta: np.ndarray, n: int, layers: int) -> QuantumCircuit:
    qc = QuantumCircuit(n, n)
    qc.h(range(n))
    for (kind, qs), th in zip(_gates(n, layers), theta):
        if kind == "zz":
            qc.rzz(float(th), qs[0], qs[1])
        elif kind == "x":
            qc.rx(float(th), qs[0])
        else:
            qc.rz(float(th), qs[0])
    return qc


# ---------------------------------------------------------------------------------------------- R4
def _randomness(ctx: Ctx, name: str, cfg: dict) -> tuple[np.random.Generator, str, bool]:
    f = cfg.get("randomness_file")
    if f and Path(f).is_file():
        raw = Path(f).read_bytes()
        seed = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")
        return np.random.Generator(np.random.PCG64(seed)), f"file {f} ({len(raw)} bytes), expanded with PCG64", True
    if runio.has_pool(ctx):
        return (Q.rng(ctx, name, "targets"),
                f"{Q.RNG_BITS} Bell-test bits of the same device (setting-independence loophole open), expanded with "
                f"PCG64", True)
    return (Q.rng(ctx, name, "targets"), "the run name (classical) expanded with SHA-256 / PCG64: pseudo-random, "
                                         "theorem assumption X13 NOT met", False)


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    n, layers, N = cfg["n"], cfg["layers"], cfg["circuits"]
    tg = Q.session(ctx).target
    ring = QH.tile_layout(tg, "hexagon", max_tiles=1)[0]["qubits"]
    g, rnd_label, true_random = _randomness(ctx, name, cfg)
    circuits, targets_p, fids = [], [], []
    for k in range(N):
        t = g.normal(size=(2,) * n) + 1j * g.normal(size=(2,) * n)
        t /= np.linalg.norm(t)
        theta, fid = ring_ansatz(t, n, layers, cfg["train_iters"], g)
        cl = random_clifford(n, seed=int(g.integers(2 ** 31))).to_circuit()
        qc = ansatz_circuit(theta, n, layers)
        qc.compose(cl, inplace=True)
        qc.measure(range(n), range(n))
        qc.name = f"xeb_{k:05d}"
        qc.metadata = {"layout": ring}
        circuits.append(qc)
        targets_p.append(np.abs(Statevector(t.reshape(-1)).evolve(cl).data) ** 2)
        fids.append(fid)
        if (k + 1) % max(1, N // 10) == 0:
            print(f"    {name}: trained {k + 1}/{N} targets, ansatz fidelity so far {np.mean(fids):.3f}", flush=True)
    bits, info = Q.execute(ctx, name, circuits, [int(cfg["shots_each"])] * N, opt=3, scalable=False)
    plan = {"ring": ring, "layers": layers, "circuits": N, "ansatz_fidelity_mean": float(np.mean(fids)),
            "ansatz_fidelity_min": float(np.min(fids)), "input_randomness": rnd_label, "info": info}
    w = 1 << np.arange(n)
    scores = np.concatenate([2 ** n * pt[(bt[:, :n] * w).sum(1)] - 1.0 for bt, pt in zip(bits, targets_p)])
    eps = float(scores.mean())
    sigma = float(scores.std(ddof=1) / math.sqrt(len(scores))) if len(scores) > 1 else float("nan")
    b = xeb_bits(eps, n)
    b_low = xeb_bits(eps - 3 * sigma, n)["bits"] if math.isfinite(sigma) else float("nan")
    assumptions = {"haar_targets_trained": True, "one_shot_per_circuit": int(cfg["shots_each"]) == 1,
                   "global_clifford_measurement": True, "inputs_bell_test_bits_or_true_random_file": true_random,
                   "bound_constants_transcribed": False}
    Q.save(ctx, name, plan | {"eps": eps, "sigma": sigma, "bits": b, "bits_at_minus_3_sigma": b_low,
                              "assumptions": assumptions})
    ok = b_low > cfg["bound"] and all(assumptions.values())
    missing = [k for k, v in assumptions.items() if not v]
    return [Q.claim(ctx, name, cfg, b["bits"], None, ok, info["label"],
                     f"eps = {eps:.3f} +- {sigma:.3f} over {N} circuits x {cfg['shots_each']} shot; bits at -3 sigma "
                     f"{b_low:.1f}; mean ansatz fidelity {np.mean(fids):.3f} at {layers} layers; inputs: {rnd_label}"
                     + (f"; cannot pass while these are open: {', '.join(missing)}" if missing else ""))]
