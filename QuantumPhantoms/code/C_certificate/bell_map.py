"""Bell map: CHSH on many disjoint pairs of the chip in one job (plans/feature-QSCALE-*.md).

    matchings   up to MATCHINGS edge matchings of the coupling graph, best forecast signal first, so most couplers
                are measured once. Every pair of a matching is a Bell pair in the same circuit (one CZ per pair).
    circuits    4 CHSH setting circuits per matching (settings fixed per circuit, not drawn per shot)
    score       S and sigma per pair
    toeplitz    Toeplitz hashing of the raw outcomes over GF(2): the bit pool the rest of the run spends

    commit      SHA-256 of the circuits and the run name, written before the job (C-CHAIN, plans/feature-QCAND-*.md)

The pairs sit on one chip and the settings are fixed per circuit: a violation here is job-level, never
device-independent. The extractor seed is 32 bytes (the first public beacon pulse after the commit, or os.urandom
when the beacon cannot be reached) expanded with SHAKE-256 to the Toeplitz length (a computational expansion, not
an information-theoretic seed).
"""
from __future__ import annotations

import hashlib
import json
import math
import time

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit

from common import qhard as QH, quantum as Q, runio
from common.runio import Ctx

BELL_SHOTS = 1024             # shots per setting circuit
MATCHINGS = 3                 # 3 matchings x 4 settings = 12 circuits
DRY = {"matchings": 1, "pairs": 6, "shots": 200}
MAX_BITS = 4096               # cap of the extracted pool

# Optimal CHSH angles (radians), applied as ry(-theta) before the Z readout: a on the first qubit, b on the second.
CHSH_SETTINGS = {"a0": 0.0, "a1": math.pi / 2, "b0": math.pi / 4, "b1": -math.pi / 4}
CHSH_PAIRS = (("a0", "b0"), ("a0", "b1"), ("a1", "b0"), ("a1", "b1"))
CHSH_SIGNS = (1.0, 1.0, 1.0, -1.0)


def matchings(tg, k: int, max_pairs: int | None = None) -> list[list[list[int]]]:
    """Up to k disjoint-edge sets of the coupling graph; each coupler appears in at most one of them."""
    g = nx.Graph()
    for a, b in tg.graph.edges:
        w = QH.pair_signal(tg, a, b)
        if w > 0:                                   # a dead coupler or qubit gives no Bell signal: not measured
            g.add_edge(a, b, w=w)
    out = []
    for _ in range(k):
        m = nx.max_weight_matching(g, maxcardinality=True, weight="w")
        if not m:
            break
        pairs = sorted(([int(min(e)), int(max(e))] for e in m), key=lambda p: (-g[p[0]][p[1]]["w"], p))
        out.append(pairs[:max_pairs] if max_pairs else pairs)
        g.remove_edges_from(m)
    return out


def chsh_circuits(pairs: list[list[int]], tag: str) -> list[QuantumCircuit]:
    """The 4 setting circuits of one matching. Qubit 2i, 2i + 1 = pair i; clbit k = qubit k."""
    n = len(pairs)
    out = []
    for a_key, b_key in CHSH_PAIRS:
        qc = QuantumCircuit(2 * n, 2 * n, name=f"bell_{tag}_{a_key}{b_key}")
        for i in range(n):
            qc.h(2 * i)
            qc.cx(2 * i, 2 * i + 1)
            qc.ry(-CHSH_SETTINGS[a_key], 2 * i)
            qc.ry(-CHSH_SETTINGS[b_key], 2 * i + 1)
        qc.measure(range(2 * n), range(2 * n))
        qc.metadata = {"layout": [int(q) for p in pairs for q in p]}
        out.append(qc)
    return out


def chsh(bits: np.ndarray) -> tuple[float, float]:
    """bits: (4 settings, rounds, 2) outcomes of one pair (or of pooled pairs). -> (S, sigma)."""
    e = 1.0 - 2.0 * (bits[:, :, 0] ^ bits[:, :, 1]).mean(1)
    return float((np.array(CHSH_SIGNS) * e).sum()), float(math.sqrt(((1 - e * e) / bits.shape[1]).sum()))


def commit(ctx: Ctx, circuits: list[QuantumCircuit]) -> dict:
    """C-CHAIN: SHA-256 of the run name and of every circuit of section C (OpenQASM 3 text + layout), written to
    <run>/commit.json before the job is submitted. A continued run keeps the commit it made first."""
    from qiskit import qasm3

    h = hashlib.sha256(ctx.run_dir.name.encode())
    for qc in circuits:
        h.update(qasm3.dumps(qc).encode() + json.dumps(qc.metadata["layout"]).encode())
    old = runio.load_json(ctx.run_dir / "commit.json")
    if old and old["commit"] == h.hexdigest():
        return old
    doc = {"commit": h.hexdigest(), "created_unix": time.time(), "run": ctx.run_dir.name, "circuits": len(circuits),
           "what": "sha256(run name, then OpenQASM 3 text + layout of every section C circuit), before the job"}
    runio.save_json(ctx.path("commit.json"), doc)
    return doc


def measure(ctx: Ctx, n_matchings: int | None = None, also=()) -> tuple[list[dict], dict]:
    """The Bell-map job. n_matchings: fewer matchings than MATCHINGS (GRAPH-BELL runs one, for the pool); also:
    the other circuits of section C, committed with these before the job.
    -> (one row per pair: qubits, matching, S, sigma, _bits (4, shots, 2); job info with the commit)."""
    tg = Q.session(ctx).target
    k, max_pairs, shots = (MATCHINGS, None, BELL_SHOTS) if ctx.live else (DRY["matchings"], DRY["pairs"], DRY["shots"])
    ms = matchings(tg, min(k, n_matchings or k), max_pairs)
    circuits = [qc for j, m in enumerate(ms) for qc in chsh_circuits(m, f"m{j}")]
    done = commit(ctx, circuits + list(also))
    bits, info = Q.execute(ctx, "bell_map", circuits, shots)
    info["commit"] = done
    rows = []
    for j, m in enumerate(ms):
        four = np.stack(bits[4 * j:4 * j + 4])                      # (4, shots, 2 n)
        for i, pair in enumerate(m):
            b = four[:, :, 2 * i:2 * i + 2]
            S, sigma = chsh(b)
            rows.append({"qubits": pair, "matching": j, "S": S, "sigma": sigma, "_bits": b})
    return rows, info


def toeplitz(raw: np.ndarray, m: int, seed: bytes) -> np.ndarray:
    """m bits = T raw over GF(2), T[i, j] = s[i + n - 1 - j], s = SHAKE-256(seed) of n + m - 1 bits. The product
    is a convolution, computed by FFT and rounded (exact at these sizes)."""
    n = len(raw)
    if m <= 0 or n == 0:
        return np.zeros(0, dtype=np.uint8)
    s = np.unpackbits(np.frombuffer(hashlib.shake_256(seed).digest((n + m + 6) // 8), dtype=np.uint8))[:n + m - 1]
    size = 1 << int(math.ceil(math.log2(2 * n + m)))
    conv = np.fft.irfft(np.fft.rfft(s, size) * np.fft.rfft(raw, size), size)
    return (np.rint(conv[n - 1:n - 1 + m]).astype(np.int64) & 1).astype(np.uint8)
