#!/usr/bin/env python3
"""CLI entry: run the experiment matrix, print per-cell PASS/FAIL, then hand
the collected CSVs to the analysis layer (plan-5 Design "1. Experiment
orchestrator"). Needs root/Mininet (like `run_topo.py`/`run_attack.py`).

Run with:
    sudo .venv/bin/python3 testbed/experiments/run_experiments.py --exp all
    sudo .venv/bin/python3 testbed/experiments/run_experiments.py --exp 4 --no-graphs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from testbed.experiments.harness import run_cell  # noqa: E402
from testbed.experiments.matrix import cells_for  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exp", choices=["1", "2", "3", "4", "5", "all"], required=True)
    parser.add_argument(
        "--no-graphs", action="store_true", help="stop after collecting CSVs; skip rendering"
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    cells = cells_for(args.exp)

    any_failed = False
    for cell in cells:
        print(f"--- {cell.experiment}/{cell.cell_id} ---")
        result = run_cell(cell)
        status = "SKIP" if result.passed is None else ("PASS" if result.passed else "FAIL")
        print(f"{status}: {result.reason}")
        if result.run_record is not None:
            print(json.dumps(result.run_record, indent=2))
            # Persist alongside the CSV so graphs.py can calibrate t_try
            # from the measured reconstruction cost without a live re-run.
            Path(cell.csv_path).with_suffix(".record.json").write_text(
                json.dumps(result.run_record, indent=2)
            )
        if result.passed is False:
            any_failed = True

    if not args.no_graphs:
        from testbed.analysis.graphs import render_graphs

        render_graphs()

    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
