"""F4 within-generation entanglement witness (plan §4, AC-5).

W_g = <XX> + <ZZ> on a representative parent->first-daughter division pair: the
parent genotype qubit is put in superposition (`h`), then the P1 division
(controlled-copy + `Ry(theta_mut)`) is applied. Separable bound |W| <= 1; W > 1
witnesses entanglement. On a noiseless pair this state gives <XX> = <ZZ> =
cos(theta_mut), so W = 2*cos(theta_mut) (theta_mut=0.3 -> ~1.91), matching the
surviving GHZ-certificate precedent (memory qalife-pj24-motile-vivarium). On Heron
it degrades per generation — that per-generation decay is the headline hardware number.

Measuring collapses the state, so <XX> and <ZZ> come from two SEPARATE single-basis
jobs — the witness cannot share shots with the generation's division job (plan §4).
This pair characterises the division channel each generation (a representative pair,
not a population average; plan Q5); it is lineage-independent, so one witness per
generation suffices.

Pure reuse: circuit built here, correlator from f1_quantum.certify.
"""

from __future__ import annotations

from qiskit import QuantumCircuit

from f1_quantum.backend import run_counts
from f1_quantum.certify import correlator


def build_witness_circuits(theta_mut: float) -> dict[str, QuantumCircuit]:
    """The two single-basis witness circuits (ZZ and XX) for the division pair."""
    out: dict[str, QuantumCircuit] = {}
    for basis in ("zz", "xx"):
        qc = QuantumCircuit(2, 2)
        qc.h(0)                 # parent genotype qubit -> superposition (quantum input to P1)
        qc.cx(0, 1)             # P1 controlled-copy
        qc.ry(theta_mut, 1)     # P1 mutation
        if basis == "xx":
            qc.h(0)
            qc.h(1)
        qc.measure([0, 1], [0, 1])
        out[basis] = qc
    return out


def witness_value(theta_mut: float, shots: int, backend) -> tuple[float, float, float]:
    """Return (W, <XX>, <ZZ>) for one generation's division pair.

    Two separate jobs (one per basis); correlator reuses the F1 CHSH math.
    """
    circuits = build_witness_circuits(theta_mut)
    zz = correlator(run_counts(circuits["zz"], shots, backend))
    xx = correlator(run_counts(circuits["xx"], shots, backend))
    return xx + zz, xx, zz


# --- Mode B: cross-generation coherent-genealogy witness ------------------------------

def _pair_corr(counts: dict[str, int], i: int, j: int) -> float:
    """<Z_i Z_j> over a multi-qubit counts dict (qiskit keys are clbit N-1..0, no spaces)."""
    num = tot = 0
    for key, n in counts.items():
        bits = key.replace(" ", "")
        bi = int(bits[len(bits) - 1 - i])
        bj = int(bits[len(bits) - 1 - j])
        num += n * (1 if bi == bj else -1)
        tot += n
    return num / tot if tot else 0.0


def build_cross_witness_circuits(k: int, theta_mut: float) -> dict[str, QuantumCircuit]:
    """GHZ-star across k coherent cells on one representative qubit each (Mode B, P3).

    Founder qubit 0 is superposed, then coherently copied (cx + Ry(theta_mut)) to each of the
    k-1 daughter qubits WITHOUT measuring in between — the lineage stays entangled across the
    generation boundary. Measured in Z (both) and X (both) bases to certify founder<->daughter
    entanglement per pair (W = <XX>+<ZZ> > 1). This is the object a classical genealogy cannot
    reproduce.
    """
    out: dict[str, QuantumCircuit] = {}
    for basis in ("zz", "xx"):
        qc = QuantumCircuit(k, k)
        qc.h(0)
        for d in range(1, k):
            qc.cx(0, d)
            qc.ry(theta_mut, d)
        if basis == "xx":
            for q in range(k):
                qc.h(q)
        qc.measure(range(k), range(k))
        out[basis] = qc
    return out


def cross_generation_witness(k: int, theta_mut: float, shots: int, backend):
    """Return (W_min, pairs) for the coherent core: W per founder<->daughter pair, min = weakest link.

    `pairs` is a list of (daughter_index, xx, zz, w). W_min > 1 certifies the whole core's
    cross-generation entanglement survived. For k < 2 there is no pair -> (nan, []).
    """
    if k < 2:
        return float("nan"), []
    circuits = build_cross_witness_circuits(k, theta_mut)
    zz_counts = run_counts(circuits["zz"], shots, backend)
    xx_counts = run_counts(circuits["xx"], shots, backend)
    pairs = []
    for d in range(1, k):
        zz = _pair_corr(zz_counts, 0, d)
        xx = _pair_corr(xx_counts, 0, d)
        pairs.append((d, xx, zz, xx + zz))
    w_min = min(p[3] for p in pairs)
    return w_min, pairs
