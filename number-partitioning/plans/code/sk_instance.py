"""Sherrington-Kirkpatrick number-partitioning instance + exact optimum.

Number partitioning: split numbers {a_i} into two sets with equal sums.
Spins s_i in {+1, -1}; objective H = A * (sum_i a_i s_i)^2.

Expanding the square drops to an Ising model on the COMPLETE graph K_n:
    H = A * sum_i a_i^2  +  2A * sum_{i<j} a_i a_j s_i s_j
The constant A*sum a_i^2 is irrelevant to optimisation; the coupling is
    J_ij = 2A * a_i a_j        (every pair -> long-range on heavy-hex)
with no linear (h_i) term. This is the flagship dense target of qh-13.

Qubit encoding: |0> = +1, |1> = -1.
"""
from __future__ import annotations

import random


def make_instance(n: int, seed: int, lo: int = 1, hi: int | None = None) -> list[int]:
    """A fixed-seed list of n positive integers. Default range [1, 2^n)."""
    if hi is None:
        hi = 1 << n
    rng = random.Random(seed)
    return [rng.randint(lo, hi - 1) for _ in range(n)]


def ising_couplings(a: list[int], A: float = 1.0) -> dict[tuple[int, int], float]:
    """J_ij = 2A * a_i a_j for every pair i<j (complete graph K_n)."""
    n = len(a)
    return {
        (i, j): 2.0 * A * a[i] * a[j]
        for i in range(n)
        for j in range(i + 1, n)
    }


def energy(bits: str, a: list[int], A: float = 1.0) -> float:
    """H = A * (sum_i a_i s_i)^2, with s_i = +1 for bit '0', -1 for bit '1'.

    `bits` is a Qiskit little-endian classical bitstring: rightmost char = spin 0.
    """
    n = len(a)
    b = bits[::-1]  # b[i] = spin i
    total = 0.0
    for i in range(n):
        s = 1.0 if b[i] == "0" else -1.0
        total += a[i] * s
    return A * total * total


def brute_force_optimum(a: list[int], A: float = 1.0) -> tuple[float, float, str]:
    """Exhaustive scan of all 2^n sign assignments.

    Returns (min_energy, max_energy, best_bits). min_energy is the partition
    optimum; max_energy is the worst assignment (used to normalise the
    approximation ratio robustly when the optimum is 0).
    """
    n = len(a)
    best_e = float("inf")
    worst_e = float("-inf")
    best_bits = "0" * n
    for mask in range(1 << n):
        bits = format(mask, f"0{n}b")  # big-endian; energy() reverses internally
        e = energy(bits, a, A)
        if e < best_e:
            best_e, best_bits = e, bits
        if e > worst_e:
            worst_e = e
    return best_e, worst_e, best_bits


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="SK number-partitioning instance")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lo", type=int, default=1)
    ap.add_argument("--hi", type=int, default=0, help="0 = default 2^n")
    ap.add_argument("--A", type=float, default=1.0)
    args = ap.parse_args()

    a = make_instance(args.n, args.seed, args.lo, args.hi or None)
    opt, worst, bits = brute_force_optimum(a, args.A)
    print(f"instance (n={args.n}, seed={args.seed}): {a}")
    print(f"sum = {sum(a)}")
    print(f"optimum energy   = {opt}  partition = {bits}")
    print(f"worst energy     = {worst}")
