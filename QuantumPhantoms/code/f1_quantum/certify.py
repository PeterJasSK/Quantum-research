"""F1 CHSH certificate — the quantum-provenance proof (plan §4, AC-5).

Pure counts math: given the four CHSH basis settings' measurement counts, compute
the correlators E(a,b) and combine them into the Bell value S. No qiskit here —
`circuit.py` builds the four setting circuits and `run.py` feeds their counts in.

S is a single **job-level** statistic (one Bell test over many shots x 4 settings).
It is NOT a per-tile value and must never be fabricated per tile (plan §4 honesty
note). Classical bound S <= 2; Tsirelson bound 2*sqrt(2) ~= 2.828.

Ported from study-ideas/QuantumAlgorithmsExplained/code/11_chsh.py: E = (agree -
disagree)/total with agree = outcomes "00" + "11".
"""

from __future__ import annotations

import math

# Optimal CHSH angle settings (radians), as ry rotations applied before Z measurement.
# a in {a0, a1} on the first qubit, b in {b0, b1} on the second.
CHSH_SETTINGS = {
    "a0": 0.0,
    "a1": math.pi / 2,
    "b0": math.pi / 4,
    "b1": -math.pi / 4,
}

# The four (a, b) pairs and their signs in S. circuit.py applies ry(-theta) on each
# qubit before Z-measurement; with these angles S -> +2*sqrt(2) on a noiseless pair
# (matches study-ideas/QuantumAlgorithmsExplained/code/11_chsh.py).
CHSH_PAIRS = (("a0", "b0"), ("a0", "b1"), ("a1", "b0"), ("a1", "b1"))
CHSH_SIGNS = (1.0, 1.0, 1.0, -1.0)


def correlator(counts: dict[str, int]) -> float:
    """E = (agree - disagree)/total for a 2-qubit setting's counts.

    `counts` keys are 2-char bitstrings ("00".."11"); agree = "00" + "11".
    Extra classical bits (if the key is longer) are ignored by taking the last 2.
    """
    agree = disagree = 0
    for bitstring, n in counts.items():
        two = bitstring.replace(" ", "")[-2:]
        if two in ("00", "11"):
            agree += n
        else:
            disagree += n
    total = agree + disagree
    if total == 0:
        return 0.0
    return (agree - disagree) / total


def chsh_value(counts_by_pair: dict[tuple[str, str], dict[str, int]]) -> float:
    """S from the four settings' counts.

    `counts_by_pair` maps each (a, b) in CHSH_PAIRS to that setting's counts dict.
    S = E(a0,b0) + E(a0,b1) + E(a1,b0) - E(a1,b1).
    """
    return sum(
        sign * correlator(counts_by_pair[pair])
        for pair, sign in zip(CHSH_PAIRS, CHSH_SIGNS)
    )
