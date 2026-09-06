"""AC-T0.10 — the framework smoke run (`python -m framework.selftest`).

The `MINIMAL.md` query-count pipeline promoted into the framework as its self-test.
On a trivial built-in subset oracle it sweeps ``n in {4..14}`` and proves the
THEOREM axis before any real problem lands:

    classical arm  -> slope_vs_logspace ~ 1.0   (calls == 2^n exactly)
    quantum arm    -> slope_vs_logspace ~ 0.5   (Dürr–Høyer ~ 1.3*2^{n/2})

with R^2 > 0.99. Prints a POC-style table and a clear PASS/FAIL line. Deterministic
(seeded), so it reproduces identical numbers across runs.
"""
from __future__ import annotations

from .bruteforce import brute_force_min, enumerate_space
from .fit import fit
from .grover_min import expected_queries, search_space_size
from .oracle import OracleCounter

N_LO, N_HI = 4, 14
SEED = 7


def _cost_factory(n: int):
    """A trivial-but-nontrivial seeded subset cost: distance to a fixed seeded
    target bitmask. Optimum (cost 0) is unique; every one of the 2^n candidates
    is evaluated, so the classical count is exactly 2^n."""
    target = (SEED * 2654435761 + n) % (1 << n)  # Knuth multiplicative hash, seeded

    def cost(x: int) -> float:
        return float(bin(x ^ target).count("1"))  # Hamming distance to target

    return cost, target


def run() -> bool:
    ns = list(range(N_LO, N_HI + 1))
    classical_calls: list[float] = []
    quantum_calls: list[float] = []
    spaces: list[int] = []

    print(f"{'n':>3} {'|S|=2^n':>9} {'classical':>10} {'quantum(DH)':>12} {'speedup':>9}")
    counter = OracleCounter()
    for n in ns:
        cost, target = _cost_factory(n)
        counter.reset()
        argmin, best, calls = brute_force_min(enumerate_space(n, "subset"), cost, counter)
        assert argmin == target and best == 0.0, f"n={n}: wrong optimum"
        N = search_space_size(n, "subset")
        assert calls == N, f"n={n}: classical calls {calls} != 2^n {N}"
        q = expected_queries(n, "subset", 1, "min")
        classical_calls.append(float(calls))
        quantum_calls.append(q)
        spaces.append(N)
        print(f"{n:>3} {N:>9} {calls:>10} {q:>12.1f} {calls / q:>8.1f}x")

    fc = fit(ns, classical_calls, spaces, kind="subset")
    fq = fit(ns, quantum_calls, spaces, kind="subset")

    print()
    print(f"classical: slope_vs_logspace = {fc.slope_vs_logspace:.4f}  R^2 = {fc.r2_vs_logspace:.4f}  (expect ~1.0)")
    print(f"quantum  : slope_vs_logspace = {fq.slope_vs_logspace:.4f}  R^2 = {fq.r2_vs_logspace:.4f}  (expect ~0.5)")

    ok = (
        abs(fc.slope_vs_logspace - 1.0) < 0.05 and fc.r2_vs_logspace > 0.99
        and abs(fq.slope_vs_logspace - 0.5) < 0.05 and fq.r2_vs_logspace > 0.99
    )
    print()
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if run() else 1)
