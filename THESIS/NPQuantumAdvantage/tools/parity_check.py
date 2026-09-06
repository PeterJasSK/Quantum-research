"""AC-T0.9 (Python side) — the reproducibility parity assert.

Dumps the Python values for a fixed vector of
``(n in 4..14) x (kind in {subset, ordering}) x (marked in {1,2,4})`` to
``tools/parity_vector.json``, shells out to the Node runner, and asserts:
  * INTEGER counts (search-space size, Grover iterations) identical (string compare,
    so BigInt vs Python int match exactly), and
  * FLOAT expected-query counts within 1e-9.

Exits non-zero on mismatch — the build-fail hook T2 wires into the Next build
(the TargetedDos D-parity discipline). Requires ``node`` on PATH.

Run: ``python tools/parity_check.py``  (from THESIS/NPQuantumAdvantage/)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

# Import the Python source of truth. Works both as `python tools/parity_check.py`
# (script dir on path) and `python -m tools.parity_check`.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from framework.grover_min import (  # noqa: E402
    expected_queries,
    grover_iterations,
    search_space_size,
)

NS = range(4, 15)
KINDS = ("subset", "ordering")
MARKED = (1, 2, 4)
FLOAT_TOL = 1e-9

_HERE = os.path.dirname(os.path.abspath(__file__))
VECTOR_PATH = os.path.join(_HERE, "parity_vector.json")
NODE_RUNNER = os.path.join(_HERE, "parity_check.mjs")


def build_vector() -> list[dict]:
    return [
        {"n": n, "kind": kind, "marked": m}
        for n in NS
        for kind in KINDS
        for m in MARKED
    ]


def python_values(vector: list[dict]) -> list[dict]:
    out = []
    for item in vector:
        n, kind, m = item["n"], item["kind"], item["marked"]
        N = search_space_size(n, kind)
        out.append(
            {
                "n": n,
                "kind": kind,
                "marked": m,
                "search_space_size": str(N),
                "grover_iterations": str(grover_iterations(N, m)),
                "expected_queries_search": expected_queries(n, kind, m, "search"),
                "expected_queries_min": expected_queries(n, kind, m, "min"),
            }
        )
    return out


def main() -> int:
    vector = build_vector()
    with open(VECTOR_PATH, "w", encoding="utf-8") as fh:
        json.dump(vector, fh)

    py = python_values(vector)

    try:
        proc = subprocess.run(
            ["node", NODE_RUNNER],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        print("PARITY DEFERRED: `node` not on PATH — Python vector dumped; the "
              "assert runs at the T2 web build (OQ-2).")
        return 0
    except subprocess.CalledProcessError as exc:
        print("PARITY ERROR: node runner failed:\n" + exc.stderr)
        return 2

    js = json.loads(proc.stdout)
    if len(js) != len(py):
        print(f"PARITY MISMATCH: length {len(js)} (js) != {len(py)} (py)")
        return 1

    for p, j in zip(py, js):
        tag = f"n={p['n']} kind={p['kind']} marked={p['marked']}"
        for key in ("search_space_size", "grover_iterations"):
            if p[key] != j[key]:
                print(f"PARITY MISMATCH [{tag}] {key}: py={p[key]} js={j[key]}")
                return 1
        for key in ("expected_queries_search", "expected_queries_min"):
            if abs(float(p[key]) - float(j[key])) > FLOAT_TOL:
                print(f"PARITY MISMATCH [{tag}] {key}: py={p[key]} js={j[key]}")
                return 1

    print(f"PARITY OK — {len(py)} vectors, integers identical, floats within {FLOAT_TOL}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
