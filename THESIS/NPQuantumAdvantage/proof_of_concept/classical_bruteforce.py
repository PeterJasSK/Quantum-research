"""Classical baseline — the BEST any classical algorithm can do on an
*unstructured* NP verifier: exhaustive search over the 2^n assignments.

Why this is the honest baseline
-------------------------------
The problem here is: given a boolean verifier V(x) over n bits (a small SAT-style
constraint set), find an x with V(x)=1. V is treated as a BLACK BOX — you may
only *evaluate* it, not inspect its structure. For a black-box predicate there is
a matching lower bound: any classical algorithm needs Omega(2^n) evaluations in
the worst case and 2^n / 2 on average (a simple adversary argument — the marked
input can hide in the last cell you check). So exhaustive search is not a lazy
baseline; it is provably optimal *in the query model* for the unstructured case.

This is exactly the regime where the quantum advantage SURVIVES (see README):
best-known-classical == brute force, so Grover's 2^(n/2) is a real quadratic
speedup over the state of the art, not just over a strawman.

When it would COLLAPSE (the honest other side)
----------------------------------------------
If V exposes structure, a smarter classical algorithm beats brute force and the
quantum edge evaporates. The classic example in this repo's family is number
partitioning: meet-in-the-middle already runs in ~2^(n/2), matching Grover, so
there the advantage collapses to brute-force-only. `meet_in_the_middle_note()`
documents that boundary; the whole thesis is mapping which side each problem
lands on.

Run:  python classical_bruteforce.py
"""
from __future__ import annotations


# --- The instance (identical to quantum_grover.py) ---------------------------
# A small boolean formula over N_VARS bits. Clauses are OR-of-literals;
# a literal is (var_index, expected_bit). The formula is the AND of all clauses.
# This is a genuine NP verifier: checking is cheap, searching is the hard part.
# A 9-clause 3-SAT instance with EXACTLY ONE satisfying assignment (x=0101),
# so the search really is needle-in-haystack: 1 marked cell out of 16. A dense
# many-solution instance would make even random guessing look good and hide the
# advantage; a unique solution is the honest hard case.
N_VARS = 4
CLAUSES = [
    [(1, 0), (3, 0), (0, 0)],   # ~x1 OR ~x3 OR ~x0
    [(1, 0), (0, 1), (2, 1)],   # ~x1 OR x0 OR x2
    [(2, 1), (1, 1), (0, 1)],   # x2 OR x1 OR x0
    [(0, 0), (1, 0), (3, 1)],   # ~x0 OR ~x1 OR x3
    [(1, 0), (2, 0), (3, 0)],   # ~x1 OR ~x2 OR ~x3
    [(2, 0), (3, 1), (1, 0)],   # ~x2 OR x3 OR ~x1
    [(1, 1), (2, 0), (0, 1)],   # x1 OR ~x2 OR x0
    [(1, 1), (2, 1), (0, 0)],   # x1 OR x2 OR ~x0
    [(1, 1), (0, 0), (3, 0)],   # x1 OR ~x0 OR ~x3
]


def verify(x: int) -> bool:
    """Black-box NP verifier: True iff assignment x (n-bit int) satisfies all
    clauses. This is the ONLY thing a search algorithm is allowed to call."""
    for clause in CLAUSES:
        if not any(((x >> var) & 1) == bit for (var, bit) in clause):
            return False
    return True


def brute_force(n: int) -> tuple[list[int], int]:
    """Best classical unstructured search. Returns (all solutions, #verifier
    calls). Counts every verifier evaluation — that is the query-model cost the
    quantum method is compared against."""
    solutions, calls = [], 0
    for x in range(1 << n):
        calls += 1
        if verify(x):
            solutions.append(x)
    return solutions, calls


def meet_in_the_middle_note() -> str:
    return (
        "COLLAPSE boundary: if the verifier decomposed additively (e.g. subset-sum\n"
        "/ number partitioning), meet-in-the-middle splits the n bits into two\n"
        "halves, sorts 2^(n/2) partial sums, and matches them in ~2^(n/2) time —\n"
        "erasing Grover's edge. No such decomposition exists for a generic SAT\n"
        "verifier, so here brute force stays optimal and the quantum edge SURVIVES."
    )


def _fmt(x: int, n: int) -> str:
    return format(x, f"0{n}b")


if __name__ == "__main__":
    sols, calls = brute_force(N_VARS)
    N = 1 << N_VARS
    print(f"problem     : {len(CLAUSES)}-clause SAT verifier over {N_VARS} vars")
    print(f"search space: 2^{N_VARS} = {N} assignments")
    print(f"solutions   : {[_fmt(s, N_VARS) for s in sols]}  (M={len(sols)})")
    print(f"verifier calls (classical, worst case): {calls}  == 2^{N_VARS}")
    print(f"classical query cost scales as O(2^n).")
    print()
    print(meet_in_the_middle_note())
