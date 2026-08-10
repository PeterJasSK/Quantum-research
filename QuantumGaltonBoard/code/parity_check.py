#!/usr/bin/env python3
"""
parity_check.py — Quantum Galton Board: the P5 JS<->Python parity gate (§6, AC-5.4).

The honest realisation of "the browser matches the Python source of truth", with
no test suite and no browser automation (epic §3.6 LOCKED). It runs the *actual
shipping JS* server-side under node: the exact code between the
``GALTON-PARITY-BLOCK`` sentinels in ``web/quantum_galton.html`` (§5) is extracted,
executed against every filled replay histogram + synthetic decode inputs, and
asserted equal to ``metrics.py`` / ``walk_spec.decode_counts`` within 1e-9.

Scope is the distribution/metric rendering only (§3.6). The AC-5.3 interference
glow is analytic-illustrative (ideal amplitude phase) and deliberately excluded
(OQ-5.3). Network-free, QPU-free, aer-free; the only external tool is ``node``
(OQ-5.2, verified present). One PASS line per metric; non-zero exit on the first
mismatch (mirrors metrics_check.py / experiment_check.py).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

import metrics
from walk_spec import decode_counts

_HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.normpath(os.path.join(_HERE, "..", "web"))
HTML_PATH = os.path.join(WEB_DIR, "quantum_galton.html")
REPLAY_PATH = os.path.join(WEB_DIR, "replay.json")

TOL = 1e-9
_START = "// ===GALTON-PARITY-BLOCK-START==="
_END = "// ===GALTON-PARITY-BLOCK-END==="

# the JS functions the driver exports; must match the sentinel-block definitions.
_EXPORTS = ("decodeCounts", "mean", "variance", "hornContrast", "entropy",
            "tvDistance", "hellinger", "localVarianceExponent", "crossoverDepth")


def _extract_block(html: str) -> str:
    """The exact text between the two GALTON-PARITY-BLOCK sentinels (§5)."""
    i = html.find(_START)
    j = html.find(_END)
    if i == -1 or j == -1 or j < i:
        raise ValueError("GALTON-PARITY-BLOCK sentinels not found in "
                         f"{HTML_PATH} — cannot extract the shipping JS mirror")
    return html[i + len(_START):j]


def _run_node(block_js: str, ops: list[dict], walk_spec: dict) -> list:
    """Run the extracted JS under node against ``ops``; return the JS results.

    Writes the shipping block to a temp ``.mjs`` with an ``export`` footer, a
    tiny driver that dispatches each op to the matching function, and the ops as
    JSON; runs ``node driver.mjs input.json`` and parses stdout. No network.
    """
    exports = ", ".join(_EXPORTS)
    with tempfile.TemporaryDirectory() as tmp:
        block_path = os.path.join(tmp, "block.mjs")
        driver_path = os.path.join(tmp, "driver.mjs")
        input_path = os.path.join(tmp, "input.json")
        with open(block_path, "w") as f:
            f.write('"use strict";\n')
            f.write(block_js)
            f.write(f"\nexport {{ {exports} }};\n")
        with open(driver_path, "w") as f:
            f.write(_DRIVER)
        with open(input_path, "w") as f:
            json.dump({"walk_spec": walk_spec, "ops": ops}, f)
        proc = subprocess.run(
            ["node", driver_path, input_path],
            capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"node failed (exit {proc.returncode}):\n{proc.stderr}")
        return json.loads(proc.stdout)


_DRIVER = r"""
"use strict";
import * as M from "./block.mjs";
import { readFileSync } from "node:fs";
const input = JSON.parse(readFileSync(process.argv[2], "utf8"));
const out = input.ops.map(op => {
  switch(op.fn){
    case "decodeCounts": return M.decodeCounts(op.counts, op.steps, input.walk_spec);
    case "variance": return M.variance(op.hist);
    case "hornContrast": return M.hornContrast(op.hist);
    case "entropy": return M.entropy(op.hist);
    case "tvDistance": return M.tvDistance(op.p, op.q);
    case "hellinger": return M.hellinger(op.p, op.q);
    case "localVarianceExponent": return M.localVarianceExponent(op.depths, op.variances);
    case "crossoverDepth": return M.crossoverDepth(op.depths, op.variances, op.contrasts);
    default: throw new Error("unknown fn " + op.fn);
  }
});
process.stdout.write(JSON.stringify(out));
"""


def _close(a, b, tol: float = TOL) -> bool:
    """None-aware abs/rel closeness (both None -> equal; one None -> not)."""
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol + tol * max(abs(a), abs(b))


def _synthetic_decode_cases() -> list[tuple[dict, int]]:
    """Raw one-hot count maps covering even/odd n and multi-bin superpositions."""
    return [
        # even n=2: bin 0 (pos -2) + bin 2 (pos +2), 4 qubits little-endian
        ({"0010": 2048, "1001": 2048}, 2),
        # even n=2: single bin 1 (pos 0) — coin qubit set/unset both map to bin 1
        ({"0100": 1000, "0101": 1000}, 2),
        # odd n=3: bins 0,1,2,3 (pos -3,-1,1,3), 5 qubits
        ({"00010": 100, "00100": 200, "01000": 300, "10000": 400}, 3),
        # odd n=3 multi-bin with coin bit flipped (coin ignored for position)
        ({"00011": 512, "01001": 512, "10001": 512, "00101": 512}, 3),
        # even n=4: spread over several bins, 6 qubits
        ({"000010": 10, "000100": 20, "001000": 30, "010000": 40, "100000": 50}, 4),
    ]


def check_decode(block_js: str, walk_spec: dict) -> None:
    """AC-5.4 / §5.1: JS decodeCounts == walk_spec.decode_counts on synthetic maps."""
    cases = _synthetic_decode_cases()
    ops = [{"fn": "decodeCounts", "counts": c, "steps": n} for c, n in cases]
    js = _run_node(block_js, ops, walk_spec)
    for (counts, n), jhist in zip(cases, js):
        ref = decode_counts(counts, n)
        jint = {int(k): v for k, v in jhist.items()}
        assert set(jint) == set(ref), f"decodeCounts n={n}: JS keys {set(jint)} != Python {set(ref)}"
        for pos in ref:
            assert _close(jint[pos], ref[pos]), \
                f"decodeCounts n={n} pos={pos}: JS {jint[pos]} != Python {ref[pos]}"
    print(f"PASS decodeCounts: JS mirror == walk_spec.decode_counts on {len(cases)} synthetic one-hot maps")


def check_metrics(block_js: str, replay: dict) -> None:
    """§6.2-4: JS variance/hornContrast/entropy/tv/hellinger/knee == metrics.py.

    Over every filled arm and depth, with a single node round-trip: the per-depth
    scalar metrics on each histogram, the arm-vs-binomial distances, and the
    depth-series knee extractor (fed the same Python-computed series so the gate
    isolates the JS metric-function parity).
    """
    binomial = replay["binomial_reference"]
    filled = [(a, blk) for a in replay["arms"]
              if (blk := replay["per_arm"].get(a)) is not None]
    assert filled, "no filled arm in replay.json — nothing to gate"

    ops: list[dict] = []
    plan: list[tuple] = []          # (kind, arm, depth-or-None, python_value)

    for arm, blk in filled:
        depths = [int(d) for d in replay["depths"] if str(d) in blk["by_depth"]]
        variances: list[float] = []
        contrasts: list[float] = []
        for n in depths:
            hist = metrics.to_int_hist(blk["by_depth"][str(n)]["position_histogram"])
            binom = metrics.to_int_hist(binomial[str(n)])
            variances.append(metrics.variance(hist))
            contrasts.append(metrics.horn_contrast(hist))
            for fn, pyval in (("variance", metrics.variance(hist)),
                              ("hornContrast", metrics.horn_contrast(hist)),
                              ("entropy", metrics.entropy(hist))):
                ops.append({"fn": fn, "hist": blk["by_depth"][str(n)]["position_histogram"]})
                plan.append((fn, arm, n, pyval))
            for fn, pyfn in (("tvDistance", metrics.tv_distance),
                             ("hellinger", metrics.hellinger)):
                ops.append({"fn": fn,
                            "p": blk["by_depth"][str(n)]["position_histogram"],
                            "q": binomial[str(n)]})
                plan.append((fn, arm, n, pyfn(hist, binom)))
        # series-level: local exponent + knee (same series to both sides)
        py_local = metrics.local_variance_exponent(depths, variances)
        ops.append({"fn": "localVarianceExponent", "depths": depths, "variances": variances})
        plan.append(("localVarianceExponent", arm, None, py_local))
        py_knee = metrics.crossover_depth(depths, variances, contrasts)
        ops.append({"fn": "crossoverDepth",
                    "depths": depths, "variances": variances, "contrasts": contrasts})
        plan.append(("crossoverDepth", arm, None, py_knee))

    js = _run_node(block_js, ops, replay["walk_spec"])

    seen: dict[str, int] = {}
    for (kind, arm, n, pyval), jsval in zip(plan, js):
        if kind == "localVarianceExponent":
            assert len(jsval) == len(pyval), f"{arm} localVarianceExponent length mismatch"
            for (jt, ja), (pt, pa) in zip(jsval, pyval):
                assert jt == pt, f"{arm} a_local depth mismatch {jt} != {pt}"
                assert _close(ja, pa), f"{arm} a_local depth={pt}: JS {ja} != Python {pa}"
        elif kind == "crossoverDepth":
            for key in ("knee_depth", "exponent_knee", "contrast_knee"):
                assert _close(jsval[key], pyval[key]), \
                    f"{arm} crossoverDepth.{key}: JS {jsval[key]} != Python {pyval[key]}"
            assert jsval["rule"] == pyval["rule"], f"{arm} crossoverDepth.rule mismatch"
        else:
            assert _close(jsval, pyval), \
                f"{kind} arm={arm} depth={n}: JS {jsval} != Python {pyval}"
        seen[kind] = seen.get(kind, 0) + 1

    for kind in ("variance", "hornContrast", "entropy", "tvDistance", "hellinger",
                 "localVarianceExponent", "crossoverDepth"):
        print(f"PASS {kind}: JS mirror == metrics.py on {seen.get(kind, 0)} inputs "
              f"(<= {TOL:.0e})")


def main() -> int:
    if not os.path.exists(HTML_PATH):
        print(f"no {HTML_PATH}", file=sys.stderr)
        return 1
    if not os.path.exists(REPLAY_PATH):
        print(f"no {REPLAY_PATH}; run replay_export.py first", file=sys.stderr)
        return 1
    with open(HTML_PATH) as f:
        block_js = _extract_block(f.read())
    with open(REPLAY_PATH) as f:
        replay = json.load(f)
    try:
        check_decode(block_js, replay["walk_spec"])
        check_metrics(block_js, replay)
    except (AssertionError, RuntimeError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print("parity_check: JS<->Python parity gate passes (distribution/metric rendering)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
