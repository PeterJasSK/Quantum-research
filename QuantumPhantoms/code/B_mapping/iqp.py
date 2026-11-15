"""B-IQP: the cohort drawn from a classically trained IQP circuit (plans/feature-QCAND-*.md; after 2503.02934 [verify]).

Circuit    H on every qubit, exp(i theta_e Z Z) on the couplers of the region (3 layers), exp(i theta_q Z) on every
           qubit, H, Z readout. 9 qubits per tumour: a measured 9-bit word is decoded by roll.bits_to_params.
Target     the rulebook's distribution of the property words (size, type | size, margin | type, lobe per tumour) plus
           one shared cohort covariate: a hidden coin per cohort shifts every tumour's size band up or down (SHIFT),
           so tumours of one cohort are correlated while each marginal stays the rulebook's.
Training   classical. For an IQP circuit the expectation of a Z string a is
               <Z_a> = E_z cos( 2 sum_j theta_j [g_j . a odd] (-1)^(g_j . z) ),   z uniform, g_j the generators,
           estimated on a fixed set of z. The loss is the squared MMD written on Z strings: the mean over a fixed
           set of subsets a (every single bit, then random small subsets) of (<Z_a>_model - <Z_a>_target)^2,
           minimised with L-BFGS (numpy + scipy). Trained once per region shape and cached in iqp_params.json.
Result     the same MMD for the hardware samples against the target and against the noiseless model; the trained
           and the untrained (start point) model against the target.

No hardness claim and no separation: level L0, a socket. The cohort decoded here replaces the one roll() drew from
the pool (each tumour its own lineage, no sibling pairs); it is still L0.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from scipy.optimize import minimize

from B_mapping import roll
from common import qhard as QH, quantum as Q, runio
from common.datamodel import LOBES, MARGINS, TYPES
from common.runio import Ctx

WORD = 9                      # bits per tumour: size 2, type 2, margin 2, lobe 3 (roll.bits_to_params)
SHIFT = (0.10, 0.0, -0.07, -0.03)             # cohort covariate: size-band probabilities +- this
TARGET_SAMPLES = 20000
Z_SAMPLES = 1024
RANDOM_SUBSETS = 400
ITERATIONS = 200
PARAMS_FILE = Path(__file__).with_name("iqp_params.json")


def target_words(tumours: int, k: int, g: np.random.Generator) -> np.ndarray:
    """k cohorts of `tumours` property words -> (k, 9 tumours) bits."""
    rb = roll.Rulebook()
    labels, p_size = rb.size_labels(), np.array(rb.size_probs())
    coin = g.integers(0, 2, k)
    out = np.zeros((k, WORD * tumours), dtype=np.uint8)
    for t in range(tumours):
        size, typ, margin = (np.zeros(k, dtype=int) for _ in range(3))
        for c in (0, 1):
            m = coin == c
            size[m] = g.choice(4, int(m.sum()), p=p_size + (1 - 2 * c) * np.array(SHIFT))
        for s in range(4):
            m = size == s
            typ[m] = g.choice(len(TYPES), int(m.sum()), p=roll._normalize(rb.type_given_size[labels[s]]))
        for i, name in enumerate(TYPES):
            m = typ == i
            margin[m] = g.choice(len(MARGINS), int(m.sum()), p=roll._normalize(rb.margin_given_type[name]))
        lobe = g.choice(len(LOBES), k, p=roll._normalize([rb.lobe_freqs[x] for x in LOBES]))
        for field, width, at in ((size, 2, 0), (typ, 2, 2), (margin, 2, 4), (lobe, 3, 6)):
            for b in range(width):                                       # first bit of a field = its MSB
                out[:, WORD * t + at + b] = (field >> (width - 1 - b)) & 1
    return out


def subsets(n: int, g: np.random.Generator) -> np.ndarray:
    """Z strings of the MMD: every single bit, then RANDOM_SUBSETS random ones of about 1, 2 or 4 bits."""
    rnd = g.random((RANDOM_SUBSETS, n)) < g.choice([1 / n, 2 / n, 4 / n], RANDOM_SUBSETS)[:, None]
    rnd = rnd[rnd.any(1)]
    return np.concatenate([np.eye(n, dtype=np.uint8), rnd.astype(np.uint8)])


def z_of_samples(bits: np.ndarray, sub: np.ndarray) -> np.ndarray:
    """<Z_a> of a sample set for every subset a."""
    return (1.0 - 2.0 * ((bits.astype(np.int32) @ sub.T.astype(np.int32)) & 1)).mean(0)


class Model:
    """Generators: one per qubit (Z), one per coupler (Z Z); theta in that order."""

    def __init__(self, n: int, edges: list[tuple[int, int]], sub: np.ndarray, g: np.random.Generator):
        self.n, self.edges = n, edges
        gen = np.zeros((n + len(edges), n), dtype=np.int32)
        gen[np.arange(n), np.arange(n)] = 1
        for j, (a, b) in enumerate(edges):
            gen[n + j, [a, b]] = 1
        z = g.integers(0, 2, (Z_SAMPLES, n)).astype(np.int32)
        self.A = ((sub.astype(np.int32) @ gen.T) & 1).astype(float)          # [subset, generator]: g . a odd
        self.S = 1.0 - 2.0 * ((z @ gen.T) & 1)                               # [z, generator]: (-1)^(g . z)

    def expect(self, theta: np.ndarray) -> np.ndarray:
        return np.cos(2.0 * (self.A * theta) @ self.S.T).mean(1)

    def loss(self, theta: np.ndarray, want: np.ndarray) -> tuple[float, np.ndarray]:
        phi = 2.0 * (self.A * theta) @ self.S.T
        diff = np.cos(phi).mean(1) - want
        grad = (2.0 / len(want)) * ((diff[:, None] * -2.0 * self.A * (np.sin(phi) @ self.S)).sum(0) / len(self.S))
        return float((diff ** 2).mean()), grad


def trained(n: int, edges: list[tuple[int, int]], tumours: int) -> dict:
    """Parameters for this region shape: from iqp_params.json, or trained now and added to it."""
    key = hashlib.sha256(json.dumps([n, edges, list(SHIFT), Z_SAMPLES, RANDOM_SUBSETS]).encode()).hexdigest()[:16]
    cache = runio.load_json(PARAMS_FILE) or {}
    if key not in cache:
        g = np.random.default_rng(int(key, 16) % 2 ** 32)       # classical training: a fixed seed per region shape
        sub = subsets(n, g)
        want = z_of_samples(target_words(tumours, TARGET_SAMPLES, g), sub)
        model = Model(n, edges, sub, g)
        start = 0.1 * g.standard_normal(n + len(edges))
        res = minimize(model.loss, start, args=(want,), jac=True, method="L-BFGS-B", options={"maxiter": ITERATIONS})
        Q.log(f"IQP trained on {n} qubits, {len(edges)} couplers: MMD^2 {model.loss(start, want)[0]:.4f} -> {res.fun:.4f} "
              f"in {res.nit} iterations")
        cache[key] = {"n": n, "edges": edges, "theta": res.x, "theta_untrained": start, "iterations": int(res.nit),
                      "mmd_model": float(res.fun), "mmd_untrained": model.loss(start, want)[0]}
        runio.save_json(PARAMS_FILE, cache)
        cache = runio.load_json(PARAMS_FILE)
    return cache[key] | {"key": key}


def iqp_circuit(nodes: list[int], edges: list[tuple[int, int]], theta: np.ndarray) -> QuantumCircuit:
    """edges in local indices. exp(i t Z) = RZ(-2 t), exp(i t Z Z) = RZZ(-2 t)."""
    n = len(nodes)
    qc = QuantumCircuit(n, n, name="iqp")
    qc.h(range(n))
    for layer in QH.edge_layers(edges):
        for a, b in layer:
            qc.rzz(-2.0 * float(theta[n + edges.index((a, b))]), a, b)
    for q in range(n):
        qc.rz(-2.0 * float(theta[q]), q)
    qc.h(range(n))
    qc.measure(range(n), range(n))
    qc.metadata = {"layout": [int(q) for q in nodes]}
    return qc


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    tumours = cfg["tumours"]
    n = WORD * tumours
    reg = QH.region(Q.session(ctx).target, n)
    nodes = reg["nodes"]
    pos = {q: k for k, q in enumerate(nodes)}
    edges = sorted(tuple(sorted((pos[a], pos[b]))) for a, b in reg["edges"])
    par = trained(n, edges, tumours)
    theta = np.array(par["theta"])
    bits, info = Q.execute(ctx, name, [iqp_circuit(nodes, edges, theta)], ctx.shots)
    g = np.random.default_rng(int(par["key"], 16) % 2 ** 32)    # the training's subsets and target, drawn again
    sub = subsets(n, g)
    want = z_of_samples(target_words(tumours, TARGET_SAMPLES, g), sub)
    model = Model(n, edges, sub, g)
    got = z_of_samples(bits[0], sub)
    mmd_target = float(((got - want) ** 2).mean())
    mmd_hw_model = float(((got - model.expect(theta)) ** 2).mean())
    n_tiles = roll.TILES if ctx.live else roll.DRY_TILES
    shots = Q.rng(ctx, name, "cohort-shots").choice(len(bits[0]), -(-n_tiles // tumours), replace=False)
    words = [bits[0][s, WORD * t:WORD * (t + 1)] for s in shots for t in range(tumours)][:n_tiles]
    roll.from_words(ctx, words, name)
    Q.save(ctx, name, {"n": n, "qubits": nodes, "couplers": len(edges), "tumours_per_shot": tumours, "info": info,
                       "mmd_target": mmd_target, "mmd_hw_model": mmd_hw_model, "mmd_model": par["mmd_model"],
                       "mmd_untrained": par["mmd_untrained"], "training_iterations": par["iterations"],
                       "params_key": par["key"], "cohort_shots": [int(s) for s in shots],
                       "params_sha256": hashlib.sha256(runio.canonical_json(par["theta"])).hexdigest(),
                       "mmd": "squared MMD on Z strings: every single bit and random small subsets; sampling floor "
                              "about 1 / shots"})
    return [Q.claim(ctx, name, cfg | {"bound": par["mmd_untrained"]}, mmd_target, None,
                    mmd_target < par["mmd_untrained"], info["label"],
                    f"hardware samples against the rulebook target {mmd_target:.4f}, against the noiseless model "
                    f"{mmd_hw_model:.4f}; trained model against the target {par['mmd_model']:.4f}, untrained "
                    f"{par['mmd_untrained']:.4f} (the bound shown); {n} qubits = {tumours} tumours x {WORD} bits, "
                    f"{len(edges)} couplers; the cohort of this run is decoded from {len(shots)} shot(s) of this "
                    f"circuit; classical training, no hardness claim")]
