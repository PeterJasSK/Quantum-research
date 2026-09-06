"""AC-T0.6 — the fault-tolerant resource estimator (documented formula).

Makes the honest cost of the advantage explicit: it is a fault-tolerant
query-model claim, not a NISQ wall-clock one. All formulae are stated here so the
number is auditable, not magic.

Formula
-------
    logical_qubits = oracle_qubits + ancillas + 1   (the +1 is phase workspace)
    toffoli_total  = queries * oracle_toffoli_count
    t_count        ~ 7 * toffoli_total              (7 T-gates per Toffoli, standard)

``t_count`` is reported as an order of magnitude (e.g. ``"~1e6"``) — the point is
scale, not spurious precision.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log10


@dataclass
class Resources:
    """Fault-tolerant cost of one Grover/Dürr–Høyer run."""

    logical_qubits: int
    toffoli_total: float
    t_count: str  # order-of-magnitude string, e.g. "~1e6"


def _order_of_magnitude(x: float) -> str:
    """Return the NEAREST order of magnitude as ``"~1eK"`` where
    ``K = round(log10(x))``; ``"~0"`` for ``x <= 0``. Nearest (not floor) so e.g.
    ``3.5e8`` reports ``~1e9`` — the honest order-of-magnitude of the T-count."""
    if x <= 0:
        return "~0"
    return f"~1e{round(log10(x))}"


def estimate_grover_resources(
    oracle_qubits: int,
    oracle_toffoli_count: int,
    queries: float,
    ancillas: int = 0,
) -> Resources:
    """Estimate fault-tolerant logical qubits, total Toffolis and T-count order.

    See module docstring for the formula. ``queries`` is the expected oracle-call
    count (from :func:`framework.grover_min.expected_queries`).
    """
    logical_qubits = oracle_qubits + ancillas + 1
    toffoli_total = queries * oracle_toffoli_count
    t_count = _order_of_magnitude(7 * toffoli_total)
    return Resources(
        logical_qubits=logical_qubits,
        toffoli_total=toffoli_total,
        t_count=t_count,
    )


def quadratization_ancillas(hubo_degree: int, n_terms: int) -> int:
    """Extra qubits a HUBO->QUBO reduction costs (P3's algebraic-collapse case).

    Reducing a degree-``d`` pseudo-boolean term to quadratic by the standard
    substitution introduces ``d - 2`` auxiliary variables per high-degree term;
    over ``n_terms`` such terms that is ``max(hubo_degree - 2, 0) * n_terms``.
    Documented so the algebraic case's overhead is visible even in the FT model.
    """
    return max(hubo_degree - 2, 0) * n_terms
