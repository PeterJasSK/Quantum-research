"""AC-T0.7 — the single source of truth: ``research_runs/ledger.json`` (v1).

Every verdict in the epic lives in exactly one file. T0 owns the schema + writer
+ validator + renderer; T1 appends one row per problem; the map figure and the
T2 web spectacle read it. No verdict lives anywhere else (epic CD).

Field names are the epic §4/§9 contract — DO NOT rename; T1 and T2 consume them.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from typing import List, Optional

DEFAULT_PATH = "research_runs/ledger.json"
SCHEMA_VERSION = 1
GROVER_EXPONENT = 0.5
THRESHOLD = 0.5

# Canonical row ids the map knows to expect; anything here but absent from the
# loaded ledger renders greyed "pending" in the figure/web.
EXPECTED_IDS: tuple[str, ...] = (
    "_3sat_reference",
    "p1_betweenness",
    "p2_numerical_matching",
    "p3_quadratic_congruences",
    "p4_kernel_digraph",
    "p5_minla",
)


@dataclass
class LedgerRow:
    """One problem's verdict. Exactly the §4 schema; optionals default ``None``."""

    id: str
    name: str
    citation: str
    search_space: str                 # "subset" | "ordering"
    search_space_size_expr: str       # "2^n" | "n!"
    classical_bruteforce_exponent: float  # theorem-axis slope, classical
    quantum_exponent: float           # theorem-axis slope, quantum (~0.5)
    verdict: str                      # SURVIVES | COLLAPSES | UNKNOWN
    hardness_assumption: str          # SETH | Set-Cover Conjecture | none | ...
    best_classical_exponent: Optional[float] = None   # verdict-axis c (subset); None ordering
    best_classical_source: Optional[str] = None
    margin_to_line: Optional[float] = None            # c - 0.5 (subset); None ordering
    collapse_mechanism: Optional[str] = None          # None | structural | measure-and-conquer | algebraic
    ft_logical_qubits: Optional[int] = None
    ft_t_count_order: Optional[str] = None
    instance_seed: Optional[int] = None
    n_swept: Optional[List[int]] = None
    fit_r2_classical: Optional[float] = None
    fit_r2_quantum: Optional[float] = None
    notes: Optional[str] = None       # optional


@dataclass
class Ledger:
    """The whole file: schema header + ordered rows."""

    schema_version: int = SCHEMA_VERSION
    grover_exponent: float = GROVER_EXPONENT
    threshold: float = THRESHOLD
    rows: List[LedgerRow] = field(default_factory=list)


def _row_from_dict(d: dict) -> LedgerRow:
    known = {f.name for f in fields(LedgerRow)}
    return LedgerRow(**{k: v for k, v in d.items() if k in known})


def load(path: str = DEFAULT_PATH) -> Ledger:
    """Load a ledger from JSON; a missing file yields an empty (header-only) one."""
    if not os.path.exists(path):
        return Ledger()
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return Ledger(
        schema_version=data.get("schema_version", SCHEMA_VERSION),
        grover_exponent=data.get("grover_exponent", GROVER_EXPONENT),
        threshold=data.get("threshold", THRESHOLD),
        rows=[_row_from_dict(r) for r in data.get("rows", [])],
    )


def save(ledger: Ledger, path: str = DEFAULT_PATH) -> None:
    """Serialise a ledger to JSON (pretty-printed, stable row order)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = {
        "schema_version": ledger.schema_version,
        "grover_exponent": ledger.grover_exponent,
        "threshold": ledger.threshold,
        "rows": [asdict(r) for r in ledger.rows],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def append_row(row: LedgerRow, path: str = DEFAULT_PATH) -> None:
    """Append (or overwrite) ``row`` — IDEMPOTENT on ``id``.

    Re-appending an existing ``id`` overwrites that row in place (re-runs never
    duplicate); a new ``id`` appends. Insertion order is preserved for a stable
    figure/table.
    """
    ledger = load(path)
    for i, existing in enumerate(ledger.rows):
        if existing.id == row.id:
            ledger.rows[i] = row
            break
    else:
        ledger.rows.append(row)
    save(ledger, path)


def validate(ledger: Ledger) -> None:
    """Fail loudly on an incoherent decided row.

    Raises :class:`ValueError` when a row has ``verdict != UNKNOWN`` and either
    it is a subset problem missing ``best_classical_exponent``, or it is a
    ``COLLAPSES`` row missing ``collapse_mechanism``.
    """
    for row in ledger.rows:
        if row.verdict == "UNKNOWN":
            continue
        if row.search_space == "subset" and row.best_classical_exponent is None:
            raise ValueError(
                f"row {row.id!r}: verdict {row.verdict} on a subset problem but "
                f"best_classical_exponent is missing"
            )
        if row.verdict == "COLLAPSES" and row.collapse_mechanism is None:
            raise ValueError(
                f"row {row.id!r}: COLLAPSES verdict but collapse_mechanism is missing"
            )


def render_markdown(ledger: Ledger, path: str = "research_runs/ledger.md") -> str:
    """Render the ledger as a Markdown table, write it to ``path``, and return it."""
    header = (
        f"# The √2 Query-Advantage Ledger (schema v{ledger.schema_version})\n\n"
        f"Grover exponent (threshold): **{ledger.threshold}** — "
        f"SURVIVES ⟺ best-known-classical exponent c > 0.5.\n\n"
        "| id | name | space | verdict | c (best classical) | margin | mechanism | assumption |\n"
        "|----|------|-------|---------|--------------------|--------|-----------|------------|\n"
    )
    lines = []
    for r in ledger.rows:
        c = "—" if r.best_classical_exponent is None else f"{r.best_classical_exponent:.3f}"
        margin = "—" if r.margin_to_line is None else f"{r.margin_to_line:+.3f}"
        mech = r.collapse_mechanism or "—"
        lines.append(
            f"| `{r.id}` | {r.name} | {r.search_space_size_expr} | "
            f"**{r.verdict}** | {c} | {margin} | {mech} | {r.hardness_assumption} |"
        )
    pending = [i for i in EXPECTED_IDS if i not in {r.id for r in ledger.rows}]
    body = header + "\n".join(lines) + "\n"
    if pending:
        body += "\nPending rows (not yet in ledger): " + ", ".join(
            f"`{i}`" for i in pending
        ) + "\n"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return body
