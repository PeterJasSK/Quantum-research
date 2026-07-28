#!/usr/bin/env python3
"""Flow-level simulation CLI (plan-10 §6) -- the root-free replacement for the
deleted `experiments/run_experiments.py`.

`--exp {1,2,3,4,5,all}` selects the same `matrix.py` cells, iterates them
through `sim_harness.run_cell`, prints per-cell PASS/FAIL against the cell's
expected summary result, then renders the two graphs with the unchanged
`analysis.graphs.render_graphs` (unless `--no-graphs`) and emits the P6
Tier-B replay subset. Requires no root, no Mininet, no scapy, no os_ken --
only pandas/matplotlib (for the graphs) plus network access for the qrng
cells.
"""
from __future__ import annotations

import argparse
import os
import sys

# The partial attacker reconstructs a weak PRNG salt (plan-10 OQ10-1
# decision); set the reduced seed space as an env DEFAULT before any testbed
# import so BOTH the sim's real brute-force AND the frozen analysis/graphs.py
# T_bf line use the same bits (landing the analytical T_bf inside the swept
# rotation range). An explicit env override wins over this default.
os.environ.setdefault("PRNG_SEED_SPACE_BITS", "19")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testbed.experiments.matrix import cells_for  # noqa: E402
from testbed.sim.replay_export import export_replay_subset  # noqa: E402
from testbed.sim.sim_harness import run_cell  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the flow-level experiment matrix (plan-10).")
    parser.add_argument("--exp", choices=["1", "2", "3", "4", "5", "all"], required=True)
    parser.add_argument("--no-graphs", action="store_true", help="stop at data; don't render graphs")
    parser.add_argument("--no-replay", action="store_true", help="don't emit the web replay subset")
    args = parser.parse_args()

    cells = cells_for(args.exp)
    any_failed = False
    for cell in cells:
        result = run_cell(cell)
        if result.passed is None:
            tag = "SKIP" if result.reason.startswith("skipped") else "DATA"
        elif result.passed:
            tag = "PASS"
        else:
            tag = "FAIL"
            any_failed = True
        print(f"[{tag}] {cell.experiment}/{cell.cell_id}: {result.reason}")

    if not args.no_graphs:
        from testbed.analysis.graphs import render_graphs

        graph1, graph2 = render_graphs()
        print(f"rendered {graph1}.png / {graph2}.png")

    if not args.no_replay:
        written = export_replay_subset()
        print(f"replay subset: {len(written)} file(s) under web/public/replay/")

    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
