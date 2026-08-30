"""Classical (non-QC) equivalent of the SK number-partitioning instance.

Same problem the QAOA arms solve: split numbers {a_i} into two sets with sums as
equal as possible. Objective H = (sum_i a_i s_i)^2, s_i in {+1,-1} — identical to
`sk_instance.energy` with A=1. This module is a pure classical reference: brute
force for the exact answer plus a subset-sum DP that counts optimal partitions
without enumerating 2^n assignments.

Primary entry point:
    number_of_optimal_partitions(numbers) -> int
        how many DISTINCT two-way partitions achieve the minimum discrepancy.

A sign flip (s -> -s) swaps the two sets but is the SAME partition, so raw
assignment counts are halved. Empty-vs-all is excluded from "distinct" the same
way (it is just one assignment pair).
"""
from __future__ import annotations

from collections import defaultdict


def discrepancy(numbers: list[int], signs: list[int]) -> int:
    """|sum a_i s_i|; the partition is perfect when this is 0."""
    return abs(sum(a * s for a, s in zip(numbers, signs)))


def brute_force(numbers: list[int]) -> tuple[int, int, list[int]]:
    """Exhaustive scan. Returns (min_discrepancy, n_optimal_assignments, example).

    `n_optimal_assignments` counts sign vectors (so each partition twice).
    `example` is one optimal +/-1 assignment.
    """
    n = len(numbers)
    best = None
    count = 0
    example: list[int] = []
    for mask in range(1 << n):
        signs = [1 if (mask >> i) & 1 == 0 else -1 for i in range(n)]
        d = discrepancy(numbers, signs)
        if best is None or d < best:
            best, count, example = d, 1, signs
        elif d == best:
            count += 1
    return best, count, example


def count_optimal_assignments(numbers: list[int]) -> tuple[int, int]:
    """(min_discrepancy, n_optimal_assignments) via subset-sum DP — O(n * S).

    S = sum(numbers). Signs +/-1 <=> pick a subset P (the +1 group); the
    discrepancy is |2*sum(P) - S|. Count subsets by their sum, then find the
    subset sum closest to S/2 and total the ways at the two closest sums.
    """
    total = sum(numbers)
    # ways[s] = number of subsets summing to s
    ways: dict[int, int] = defaultdict(int)
    ways[0] = 1
    for a in numbers:
        nxt = defaultdict(int, ways)
        for s, c in ways.items():
            nxt[s + a] += c
        ways = nxt

    best_d = None
    best_count = 0
    for s, c in ways.items():
        d = abs(2 * s - total)
        if best_d is None or d < best_d:
            best_d, best_count = d, c
        elif d == best_d:
            best_count += c
    return best_d, best_count


def number_of_optimal_partitions(numbers: list[int]) -> int:
    """DISTINCT two-way partitions achieving the minimum discrepancy.

    Each partition corresponds to a complementary subset pair (P, complement),
    i.e. two sign vectors — so the assignment count is halved.
    """
    _, assignments = count_optimal_assignments(numbers)
    return assignments // 2


def solve(numbers: list[int]) -> dict:
    """Full classical result for one instance."""
    min_d, assignments = count_optimal_assignments(numbers)
    return {
        "numbers": numbers,
        "sum": sum(numbers),
        "min_discrepancy": min_d,
        "min_energy": min_d * min_d,          # matches sk_instance.energy (A=1)
        "optimal_assignments": assignments,
        "optimal_partitions": assignments // 2,
        "perfect": min_d == 0,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Classical SK number-partitioning solver")
    ap.add_argument("numbers", nargs="+", type=int,
                    help="the integers to partition, e.g. 14 7 13 15")
    ap.add_argument("--verify", action="store_true",
                    help="cross-check the DP against brute force (small n only)")
    args = ap.parse_args()

    res = solve(args.numbers)
    print(f"numbers            : {res['numbers']}")
    print(f"sum                : {res['sum']}")
    print(f"min discrepancy    : {res['min_discrepancy']}")
    print(f"min energy (H)     : {res['min_energy']}")
    print(f"optimal partitions : {res['optimal_partitions']}")
    print(f"perfect split      : {res['perfect']}")

    if args.verify:
        bd, ba, ex = brute_force(args.numbers)
        ok = (bd == res["min_discrepancy"]
              and ba == res["optimal_assignments"])
        print(f"brute-force check  : min_d={bd} assignments={ba} "
              f"match={ok} example={ex}")
