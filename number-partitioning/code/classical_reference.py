"""Classical number partitioning — brute force + optimal, self-contained record.

Problem: split integers {a_i} into two sets with sums as equal as possible.
Spins s_i in {+1,-1}; objective H = (sum_i a_i s_i)^2. The minimum discrepancy
d = |sum a_i s_i| is 0 for a perfect split.

Two methods, no external deps:
  * brute_force  -- exhaustive 2^n scan. Exact, but exponential. The ground truth.
  * optimal_dp   -- subset-sum DP in O(n * S), S = sum(a). Exact optimum without
                    enumerating assignments (pseudo-polynomial; the best practical
                    exact classical solver for bounded magnitudes).

This is the bar the QAOA arm (qc_simplified.py) is judged against.
"""
from __future__ import annotations

from collections import defaultdict


def brute_force(numbers: list[int]) -> tuple[int, int, list[int]]:
    """Exhaustive 2^n scan.

    Returns (min_discrepancy, n_optimal_assignments, example_signs).
    n_optimal_assignments counts sign vectors, so each partition is counted
    twice (s and -s are the same partition).
    """
    n = len(numbers)
    best: int | None = None
    count = 0
    example: list[int] = []
    for mask in range(1 << n):
        signs = [1 if (mask >> i) & 1 == 0 else -1 for i in range(n)]
        d = abs(sum(a * s for a, s in zip(numbers, signs)))
        if best is None or d < best:
            best, count, example = d, 1, signs
        elif d == best:
            count += 1
    return best, count, example


def optimal_dp(numbers: list[int]) -> tuple[int, int]:
    """Exact optimum via subset-sum DP — O(n * S).

    A +/-1 assignment <=> pick a subset P (the +1 group); discrepancy is
    |2*sum(P) - S|. Count subsets by sum, take the sum closest to S/2.
    Returns (min_discrepancy, n_optimal_assignments).
    """
    total = sum(numbers)
    ways: dict[int, int] = defaultdict(int)
    ways[0] = 1
    for a in numbers:
        nxt = defaultdict(int, ways)
        for s, c in ways.items():
            nxt[s + a] += c
        ways = nxt

    best_d: int | None = None
    best_count = 0
    for s, c in ways.items():
        d = abs(2 * s - total)
        if best_d is None or d < best_d:
            best_d, best_count = d, c
        elif d == best_d:
            best_count += c
    return best_d, best_count


def solve(numbers: list[int]) -> dict:
    min_d, assignments = optimal_dp(numbers)
    return {
        "numbers": numbers,
        "sum": sum(numbers),
        "min_discrepancy": min_d,
        "min_energy": min_d * min_d,
        "optimal_partitions": assignments // 2,
        "perfect": min_d == 0,
    }


def make_instance(n: int, seed: int) -> list[int]:
    """n random 10-bit integers in [1, 1023], fixed by seed (matches qc files)."""
    import random
    rng = random.Random(seed)
    return [rng.randint(1, (1 << 10) - 1) for _ in range(n)]


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Classical number partitioning")
    ap.add_argument("numbers", nargs="*", type=int,
                    help="explicit integers, e.g. 14 7 13 15; else use --n/--seed")
    ap.add_argument("--n", type=int, default=0, help="generate n random numbers")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--verify", action="store_true",
                    help="cross-check DP against brute force (small n only)")
    args = ap.parse_args()

    numbers = args.numbers if args.numbers else make_instance(args.n or 4, args.seed)
    res = solve(numbers)
    print(f"numbers            : {res['numbers']}")
    print(f"sum                : {res['sum']}")
    print(f"min deviation      : {res['min_discrepancy']}  (the optimal, classical bar)")
    print(f"optimal partitions : {res['optimal_partitions']}")
    print(f"perfect split      : {res['perfect']}")

    if args.verify:
        bd, ba, ex = brute_force(numbers)
        ok = bd == res["min_discrepancy"]
        print(f"brute-force check  : min_d={bd} assignments={ba} "
              f"match={ok} example={ex}")
