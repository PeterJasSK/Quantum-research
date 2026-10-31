"""D-SCALE 2-qubit tomography + witness statistics (frozen copy of RE D `src/witness.py`).

Original docstring: Witness statistics for D: lineage <XX>+<ZZ>, CHSH S, bipartite-setting 2q tomography, negativity, MI.
All errors are bootstrap standard errors (resample shots with rng(seed, "DS-bootstrap"))."""
# copied from plans/relatedPapers/reverse-engineering/D_quantum_growth/src/witness.py @ 2609cbe;
# changed: rng from imaging.seedhash, seed label D-bootstrap -> DS-bootstrap. See dscale/PORTED.md.
from __future__ import annotations

import itertools

import numpy as np

from imaging.seedhash import rng

BOOT = 1000
I2 = np.eye(2, dtype=complex)
PAULI = {"I": I2, "X": np.array([[0, 1], [1, 0]], dtype=complex),
         "Y": np.array([[0, -1j], [1j, 0]]), "Z": np.diag([1.0, -1.0]).astype(complex)}


def corr(a: np.ndarray, b: np.ndarray) -> float:
    """<sigma sigma> from 0/1 outcomes: mean of (-1)^(a xor b)."""
    a, b = a.astype(np.int64), b.astype(np.int64)
    return float(np.mean(1 - 2 * ((a ^ b) & 1))) if a.size else float("nan")


def boot_se(vals: np.ndarray, stat, seed_hex: str, label: str = "DS-bootstrap", n: int = BOOT) -> float:
    if vals.shape[0] < 2:
        return float("nan")
    g = rng(seed_hex, label)
    idx = g.integers(0, vals.shape[0], size=(n, vals.shape[0]))
    return float(np.std([stat(vals[i]) for i in idx], ddof=1))


def chsh_S(x, y, a, b) -> tuple[float, float, int]:
    """S = E00 + E01 + E10 - E11 and its standard error (binomial per setting pair)."""
    s, var = 0.0, 0.0
    for xi, yi in itertools.product((0, 1), (0, 1)):
        m = (x == xi) & (y == yi)
        n = int(m.sum())
        if n == 0:
            return float("nan"), float("nan"), 0
        e = corr(a[m], b[m])
        s += (-1 if (xi, yi) == (1, 1) else 1) * e
        var += (1 - e * e) / n
    return float(s), float(np.sqrt(var)), int(len(x))


# ---------------------------------------------------------------- 2-qubit linear-inversion tomography
def _pauli2(p: str, q: str) -> np.ndarray:
    return np.kron(PAULI[p], PAULI[q])




def tomo_pair(shots: dict[tuple[str, str], np.ndarray], i_idx: int, j_idx: int, i_in_A: bool) -> np.ndarray:
    """rho_ij from the 9 bipartite settings. shots[(bA, bB)] has columns = qubit index; site i is in the
    sublattice whose basis is bA if i_in_A else bB (and j in the other)."""
    exp = {}
    for (bA, bB), bits in shots.items():
        bi, bj = (bA, bB) if i_in_A else (bB, bA)
        zi = 1 - 2 * bits[:, i_idx].astype(float)
        zj = 1 - 2 * bits[:, j_idx].astype(float)
        exp[(bi, bj)] = float(np.mean(zi * zj))
        exp.setdefault((bi, "I"), float(np.mean(zi)))
        exp.setdefault(("I", bj), float(np.mean(zj)))
    rho = np.eye(4, dtype=complex) / 4
    for (p, q), v in exp.items():
        rho += v * _pauli2(p, q) / 4
    return rho


def nearest_physical(rho: np.ndarray) -> np.ndarray:
    """Smolin-Gambetta-Smith fast maximum-likelihood projection of a Hermitian trace-1 matrix to a state."""
    rho = (rho + rho.conj().T) / 2
    w, v = np.linalg.eigh(rho)
    order = np.argsort(w)[::-1]
    w, v = w[order], v[:, order]
    lam, acc, d = w.copy(), 0.0, len(w)
    i = d
    while i > 0 and lam[i - 1] + acc / i < 0:
        acc += lam[i - 1]
        lam[i - 1] = 0
        i -= 1
    lam[:i] += acc / i
    return (v * lam) @ v.conj().T


def negativity(rho: np.ndarray) -> float:
    r = rho.reshape(2, 2, 2, 2).transpose(0, 3, 2, 1).reshape(4, 4)  # partial transpose on qubit 2
    ev = np.linalg.eigvalsh((r + r.conj().T) / 2)
    return float(-ev[ev < 0].sum())


def vn_entropy(rho: np.ndarray) -> float:
    ev = np.linalg.eigvalsh((rho + rho.conj().T) / 2)
    ev = ev[ev > 1e-12]
    return float(-(ev * np.log2(ev)).sum())


def mutual_information(rho: np.ndarray) -> float:
    r = rho.reshape(2, 2, 2, 2)
    ra, rb = np.trace(r, axis1=1, axis2=3), np.trace(r, axis1=0, axis2=2)
    return float(vn_entropy(ra) + vn_entropy(rb) - vn_entropy(rho))
