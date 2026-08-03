#!/usr/bin/env python3
"""Orchestrator CLI (epic §9 P5, AC-5.1-5.4). Iterates one matrix group through P4's
`collect_cell`, writes each cell's CSV row + `.record.json` via P4's writer, then (unless
gated off) renders the two headline figures and exports the replay JSON. Mirrors the ECMP
twin's `sim/run_sim.py` `--no-graphs`/`--no-replay` flow and `resolver/run_metrics.py`'s
repo-root `sys.path` bootstrap. Never re-drives `run_poison_race` directly (epic §3.5) --
only `collect_cell`, once per matrix cell.
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testbed import config  # noqa: E402
from testbed.experiments.matrix import cells_for  # noqa: E402
from testbed.resolver.csv_writer import write_record_json, write_row  # noqa: E402
from testbed.resolver.metrics import amplification_factor, collect_cell  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the P5 experiment matrix.")
    parser.add_argument("--group", choices=["cliff", "collapse", "birthday", "all"], required=True)
    parser.add_argument("--trials", type=int, default=config.TRIALS_PER_CELL)
    parser.add_argument(
        "--send-rate", type=int, default=None, help="override each cell's send_rate_pps for this run"
    )
    parser.add_argument("--seed", type=int, default=config.PRNG_SEED)
    parser.add_argument("--out", type=str, default=config.RESULTS_CSV_PATH)
    parser.add_argument("--record-dir", type=str, default=config.RESULTS_RECORD_DIR)
    parser.add_argument("--no-graphs", action="store_true", help="stop at data; don't render figures")
    parser.add_argument("--no-replay", action="store_true", help="don't emit replay JSON")
    parser.add_argument(
        "--fresh", action="store_true", help="truncate --out before writing (default: append)"
    )
    args = parser.parse_args()

    if args.fresh and os.path.exists(args.out):
        os.remove(args.out)

    cells = cells_for(args.group)
    run_tag = f"{args.group}-{args.seed}"

    baseline_rate: float | None = None
    for cell in cells:
        record = collect_cell(
            cell.kind,
            k=cell.k,
            send_rate_pps=args.send_rate or cell.send_rate_pps,
            parallel_queries=cell.parallel_queries,
            trials=args.trials,
            seed=args.seed,
        )
        if cell.group == "birthday":
            if cell.parallel_queries == 1:
                baseline_rate = record.poison_rate
            amp = (
                amplification_factor(record.poison_rate, baseline_rate)
                if baseline_rate is not None
                else None
            )
            record = dataclasses.replace(record, amplification_factor=amp)

        write_row(record, args.out, run_tag=run_tag)
        record_path = os.path.join(args.record_dir, f"{run_tag}-{cell.cell_id}.record.json")
        write_record_json(record, record_path, run_tag=run_tag)
        print(f"[DATA] {cell.cell_id} poison_rate={record.poison_rate:.4f}")

    if not args.no_graphs:
        from testbed.analysis.graphs import render_graphs

        cliff_png, collapse_png = render_graphs(csv_path=args.out)
        print(f"rendered {cliff_png}, {collapse_png}")

    if not args.no_replay:
        from testbed.sim.replay_export import export_replay

        for path in export_replay(csv_path=args.out, record_dir=args.record_dir):
            print(f"wrote {path}")

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
