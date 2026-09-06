"""The shared spine of the Quantum Query-Advantage Map epic (T0).

One framework, one theorem demonstrated identically, one √2 map figure. T0 owns
all math and I/O contracts; T1's five problems supply only an instance generator
+ cost oracle + QUBO map and inherit everything here; T2's web spectacle vendors
the counter (JS mirror) and reads the ledger.

The two axes T0 keeps distinct (the crux the epic §6 spine corrects)
-------------------------------------------------------------------
1. THEOREM axis — ``log2(oracle_calls)`` vs ``log2(|S|)``: slope 1.0 classical /
   0.5 quantum for EVERY problem, the quadratic query speedup proven by counting
   (``fit.slope_vs_logspace``; ``selftest`` asserts it).
2. VERDICT axis — the √2 line: quantum vs best-known-classical as functions of
   input ``n``; SURVIVES ⟺ classical exponent c > 0.5 (``classify``).
"""
from __future__ import annotations

from .classify import Verdict, classify_ordering, classify_subset
from .fit import fit
from .grover_min import expected_queries
from .ledger import LedgerRow
from .oracle import OracleCounter

__all__ = [
    "OracleCounter",
    "Verdict",
    "LedgerRow",
    "expected_queries",
    "fit",
    "classify_subset",
    "classify_ordering",
]
