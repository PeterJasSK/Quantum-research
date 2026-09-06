"""Shared drivers for the five T1 problems (epic §9 — the three ~identical
driver files per problem delegate here so the only per-problem code stays in
``instance.py`` + each ``best_classical.py`` algorithm).

Contracts consumed from :mod:`framework` (T0, Complete):
  - ``OracleCounter`` — one increment per objective evaluation.
  - ``brute_force_min(candidates, cost, counter)`` — does NOT reset the counter.
  - ``enumerate_space(n, kind)`` — ``2**n`` int bitmasks (subset) / ``n!``
    permutation tuples of ``range(n)`` (ordering).
  - ``expected_queries(n, kind, marked, mode)`` — Dürr–Høyer ``~1.3·√|S|``.
  - ``fit`` / ``classify_subset`` / ``classify_ordering`` / ``LedgerRow`` /
    ``append_row`` / ``estimate_grover_resources``.

Claim discipline (epic §3): every advantage line carries the four qualifiers.
"""
from __future__ import annotations

import argparse
import warnings
from dataclasses import dataclass, field
from math import floor, log2, pi, sqrt
from typing import Callable, Dict, List, Sequence, Tuple

from framework.bruteforce import brute_force_min
from framework.classify import Verdict, classify_ordering, classify_subset
from framework.fit import fit
from framework.grover_min import expected_queries, search_space_size
from framework.ledger import DEFAULT_PATH, LedgerRow, append_row, load, validate
from framework.oracle import OracleCounter
from framework.resources import estimate_grover_resources

CLAIM_BANNER = (
    "advantage claim = query model · over brute force · quadratic · NOT wall-clock.\n"
    "The scaling evidence is the ORACLE-CALL count below (exact, device-independent);\n"
    "any statevector/hardware run is a feasibility/amplification demo, not the claim."
)

# Default sweeps. Ordering brute force enumerates n! candidates, so it is capped
# small; subset enumerates 2^n and can go further.
SUBSET_LO, SUBSET_HI = 6, 14
ORDER_LO, ORDER_HI = 5, 8


@dataclass(frozen=True)
class QUBO:
    """The Ising/QUBO map of an instance (for the FT resource estimate + the
    deferred hardware appendix). ``linear``/``quadratic`` are coefficient dicts
    keyed by variable index / index-pair."""

    linear: Dict[int, float]
    quadratic: Dict[Tuple[int, int], float]
    num_vars: int
    num_ancillas: int = 0
    degree: int = 2


# --- protocol every instance.py satisfies (structural, not enforced) ----------
# KIND: Literal["subset","ordering"]; SEARCH_SPACE_EXPR: str; META: dict
# generate(n, seed) -> Instance ; cost(candidate, instance) -> float
# enumerate(n) -> Iterable ; to_qubo(instance) -> QUBO  (or to_hubo)


def _fit_quiet(ns, calls, spaces, kind: str):
    """fit() but silence the (intended) ordering diagnostic UserWarning — for
    ordering problems we read ``exponent_in_n`` only as a diagnostic and take the
    verdict from ``classify_ordering``, exactly as the warning instructs."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return fit(ns, calls, spaces, kind=kind)


def _sweep_ns(kind: str, lo: int | None, hi: int | None) -> List[int]:
    if kind == "ordering":
        return list(range(lo or ORDER_LO, (hi or ORDER_HI) + 1))
    return list(range(lo or SUBSET_LO, (hi or SUBSET_HI) + 1, 2))


# --------------------------------------------------------------------------- #
# classical_bruteforce.py driver (AC-T1.3)
# --------------------------------------------------------------------------- #
def run_classical(mod, n: int, seed: int) -> Tuple[object, float, int]:
    inst = mod.generate(n, seed)
    counter = OracleCounter()
    counter.reset()
    argmin, best, calls = brute_force_min(
        mod.enumerate(n), lambda c: mod.cost(c, inst), counter
    )
    size = search_space_size(n, mod.KIND)
    print(f"problem      : {mod.META['name']} ({mod.KIND})")
    print(f"search space : {mod.SEARCH_SPACE_EXPR} = {size}")
    print(f"optimum cost : {best}   (0 == feasible/solved)")
    print(f"verifier calls (classical, exhaustive): {calls}  == {mod.SEARCH_SPACE_EXPR}")
    assert calls == size, f"classical calls {calls} != |S| {size}"
    print(f"classical query cost scales as O({mod.SEARCH_SPACE_EXPR}).")
    return argmin, best, calls


def classical_main(mod) -> None:
    ap = argparse.ArgumentParser(description=f"{mod.META['name']} — exhaustive brute force")
    ap.add_argument("--n", type=int, default=(6 if mod.KIND == "ordering" else 10))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    run_classical(mod, args.n, args.seed)


# --------------------------------------------------------------------------- #
# quantum_grover.py driver (AC-T1.4)
# --------------------------------------------------------------------------- #
def run_quantum(
    mod, n: int, seed: int, *, statevector: bool, backend: str, shots: int
) -> None:
    inst = mod.generate(n, seed)
    kind = mod.KIND
    size = search_space_size(n, kind)
    q = expected_queries(n, kind, 1, "min")

    ns = _sweep_ns(kind, None, None)
    qs = [expected_queries(k, kind, 1, "min") for k in ns]
    spaces = [search_space_size(k, kind) for k in ns]
    fq = _fit_quiet(ns, qs, spaces, kind)

    print(CLAIM_BANNER)
    print()
    print(f"problem       : {mod.META['name']} ({kind})")
    print(f"search space  : {mod.SEARCH_SPACE_EXPR} = {size}")
    print(f"Grover/DH oracle calls (quantum) : {q:.1f}  (~1.3·√|S|)")
    print(f"classical calls (brute force)    : {size}")
    print(f"speedup factor this instance     : {size / q:.1f}x  (asymptotic: √|S|)")
    print(f"theorem-axis slope log2(calls) vs log2|S| : {fq.slope_vs_logspace:.3f}  (expect ~0.5)")
    print()

    if not statevector:
        return
    if kind != "subset":
        print(
            "--statevector: permutation-Grover statevector demo is out of scope for "
            "ordering problems (OQ-5). The query-count scaling above IS the theorem; "
            "the amplification demo is shown on subset problems + the POC."
        )
        return
    _statevector_demo(mod, inst, n, shots=shots, backend=backend)


def _mark(qc, state: int, n: int) -> None:
    zeros = [q for q in range(n) if not ((state >> q) & 1)]
    if zeros:
        qc.x(zeros)
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    if zeros:
        qc.x(zeros)


def _statevector_demo(mod, inst, n: int, *, shots: int, backend: str) -> None:
    from qiskit import QuantumCircuit

    marked = [x for x in range(1 << n) if mod.cost(x, inst) == 0]
    if not marked:
        print("statevector demo: no feasible state at this n; skipping.")
        return

    m = len(marked)
    iters = max(1, floor((pi / 4) * sqrt((1 << n) / m)))
    qc = QuantumCircuit(n, n)
    qc.h(range(n))
    for _ in range(iters):
        for s in marked:
            _mark(qc, s, n)
        qc.h(range(n))
        qc.x(range(n))
        qc.h(n - 1)
        qc.mcx(list(range(n - 1)), n - 1)
        qc.h(n - 1)
        qc.x(range(n))
        qc.h(range(n))
    qc.measure(range(n), range(n))

    print(f"statevector demo : n={n}, marked M={m}, Grover iterations={iters}")
    if backend:
        counts = _counts_hw(qc, shots, backend)
    else:
        from qiskit_aer import AerSimulator

        counts = AerSimulator().run(qc, shots=shots).result().get_counts()
    total = sum(counts.values())
    marked_set = {format(s, f"0{n}b") for s in marked}
    hits = sum(v for k, v in counts.items() if k in marked_set)
    floor_frac = m / (1 << n)
    print(f"marked-state probability : {hits / total:.3f}   (uniform floor = {floor_frac:.3f})")
    print("amplification demonstrated" if hits / total > floor_frac else "no amplification (check n/M)")


def _counts_hw(qc, shots: int, backend_name: str) -> Dict[str, int]:
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()
    if backend_name == "auto":
        backend = service.least_busy(operational=True, simulator=False, min_num_qubits=qc.num_qubits)
    else:
        backend = service.backend(backend_name)
    print(f"backend : {backend.name} ({backend.num_qubits} qubits) — FEASIBILITY run only")
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    isa = pm.run(qc)
    result = SamplerV2(mode=backend).run([isa], shots=shots).result()
    return result[0].data.c.get_counts()


def quantum_main(mod) -> None:
    ap = argparse.ArgumentParser(description=f"{mod.META['name']} — Grover/Dürr–Høyer query count")
    ap.add_argument("--n", type=int, default=(6 if mod.KIND == "ordering" else 10))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--statevector", action="store_true", help="small-n Aer amplification demo (subset only)")
    ap.add_argument("--backend", default="", help="IBM backend, 'auto'=least-busy, empty=Aer sim (feasibility only)")
    ap.add_argument("--shots", type=int, default=4096)
    args = ap.parse_args()
    run_quantum(mod, args.n, args.seed, statevector=args.statevector, backend=args.backend, shots=args.shots)


# --------------------------------------------------------------------------- #
# best_classical.py driver — the hunt (AC-T1.5/T1.6/T1.7)
# --------------------------------------------------------------------------- #
Algorithm = Callable[[object], Tuple[object, int]]  # (result, work_units)


def run_hunt(
    mod, algorithm: Algorithm, *, n_lo: int | None, n_hi: int | None, seed: int, emit: bool
) -> LedgerRow:
    kind = mod.KIND
    meta = mod.META
    ns = _sweep_ns(kind, n_lo, n_hi)

    brute_calls: List[float] = []
    grover_calls: List[float] = []
    hunt_work: List[float] = []
    spaces: List[int] = []
    counter = OracleCounter()

    print(f"hunt: best-known classical for {meta['name']} — {meta['best_classical_source']}")
    print(f"{'n':>3} {'|S|':>12} {'brute':>12} {'grover(DH)':>12} {'hunt work':>12}")
    for n in ns:
        inst = mod.generate(n, seed)
        counter.reset()
        _, _opt, calls = brute_force_min(mod.enumerate(n), lambda c: mod.cost(c, inst), counter)
        size = search_space_size(n, kind)
        assert calls == size, f"n={n}: brute calls {calls} != |S| {size}"
        _res, work = algorithm(inst)
        brute_calls.append(float(calls))
        grover_calls.append(expected_queries(n, kind, 1, "min"))
        hunt_work.append(float(max(work, 1)))
        spaces.append(size)
        print(f"{n:>3} {size:>12} {calls:>12} {grover_calls[-1]:>12.1f} {int(hunt_work[-1]):>12}")

    fc = _fit_quiet(ns, brute_calls, spaces, kind)
    fq = _fit_quiet(ns, grover_calls, spaces, kind)
    fh = _fit_quiet(ns, hunt_work, spaces, kind)  # exponent_in_n == best-classical c (subset)

    if kind == "ordering":
        cr = classify_ordering(True, fh.exponent_in_n)
        best_c = None
        margin = None
        mechanism = "structural"
    else:
        c = fh.exponent_in_n
        cr = classify_subset(c)
        best_c = c
        margin = cr.margin_to_line
        mechanism = meta.get("mechanism") if cr.verdict == Verdict.COLLAPSES else None

    q_at = expected_queries(ns[-1], kind, 1, "min")
    qubo = mod.to_qubo(mod.generate(ns[-1], seed))
    toffoli_per_call = max(1, len(qubo.linear) + len(qubo.quadratic))  # one Toffoli per QUBO term (proxy)
    resources = estimate_grover_resources(
        qubo.num_vars, toffoli_per_call, q_at, qubo.num_ancillas
    )

    row = LedgerRow(
        id=meta["id"],
        name=meta["name"],
        citation=meta["citation"],
        search_space=kind,
        search_space_size_expr=mod.SEARCH_SPACE_EXPR,
        classical_bruteforce_exponent=round(fc.slope_vs_logspace, 3),
        quantum_exponent=round(fq.slope_vs_logspace, 3),
        verdict=cr.verdict.value,
        hardness_assumption=meta["hardness_assumption"],
        best_classical_exponent=(round(best_c, 3) if best_c is not None else None),
        best_classical_source=meta["best_classical_source"],
        margin_to_line=(round(margin, 3) if margin is not None else None),
        collapse_mechanism=mechanism,
        ft_logical_qubits=resources.logical_qubits,
        ft_t_count_order=resources.t_count,
        instance_seed=seed,
        n_swept=ns,
        fit_r2_classical=round(fc.r2_vs_logspace, 4),
        fit_r2_quantum=round(fq.r2_vs_logspace, 4),
        notes=meta.get("notes"),
    )

    print()
    print(f"theorem axis : classical slope {row.classical_bruteforce_exponent} "
          f"(R²={row.fit_r2_classical}) | quantum slope {row.quantum_exponent} (R²={row.fit_r2_quantum})")
    if kind == "subset":
        print(f"verdict axis : best-classical c = {best_c:.3f}  (√2 line at 0.5, margin {margin:+.3f})")
    else:
        print(f"verdict axis : ordering — √(n!) asymptotically above any 2^(c·n); a 2^(O(n)) DP exists")
    print(f"VERDICT      : {row.verdict}  mechanism={row.collapse_mechanism}  "
          f"[{row.hardness_assumption}]")

    if emit:
        append_row(row)
        validate(load())
        print(f"→ row '{row.id}' appended to {DEFAULT_PATH} and ledger validated.")
    else:
        print("(--no-emit: row not written)")
    return row


def hunt_main(mod, algorithm: Algorithm) -> None:
    ap = argparse.ArgumentParser(description=f"{mod.META['name']} — best-classical hunt + √2 verdict")
    ap.add_argument("--n-lo", type=int, default=None)
    ap.add_argument("--n-hi", type=int, default=None)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-emit", dest="emit", action="store_false", help="fit + classify but do not write the ledger row")
    ap.set_defaults(emit=True)
    args = ap.parse_args()
    run_hunt(mod, algorithm, n_lo=args.n_lo, n_hi=args.n_hi, seed=args.seed, emit=args.emit)
