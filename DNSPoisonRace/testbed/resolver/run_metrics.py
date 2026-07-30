#!/usr/bin/env python3
"""CLI runner (epic ss9 P4). For each `(kind, parallel)` pair, runs
`collect_cell`, computes `amplification_factor` against the first
`--parallel` value's baseline cell, and writes one CSV row + one
`.record.json`. Mirrors `attacker/run_attack.py`'s CLI shape and repo-root
`sys.path` bootstrap."""
from __future__ import annotations

import argparse
import dataclasses
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testbed import config  # noqa: E402
from testbed.draw.sources import DrawKind  # noqa: E402
from testbed.resolver.csv_writer import write_record_json, write_row  # noqa: E402
from testbed.resolver.metrics import amplification_factor, collect_cell  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the P4 resolver metrics collector.")
    parser.add_argument(
        "--kind",
        type=str,
        default="csprng",
        help="comma-separated list of fixed|prng|csprng|qrng (OQ-P4.3)",
    )
    parser.add_argument("--eff-bits", type=int, default=None, help="derive -k from this")
    parser.add_argument("--port-bits", type=int, default=config.PORT_BITS)
    parser.add_argument("-k", "--leak-bits", type=int, default=config.SAD_DNS_LEAK_BITS)
    parser.add_argument("--send-rate", type=int, default=config.ATTACKER_SEND_RATE_PPS)
    parser.add_argument(
        "--parallel",
        type=str,
        default=str(config.PARALLEL_QUERIES),
        help="comma-separated list, first value is the amplification baseline",
    )
    parser.add_argument("--trials", type=int, default=config.TRIALS_PER_CELL)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=str, default=config.RESULTS_CSV_PATH)
    parser.add_argument("--record-dir", type=str, default=config.RESULTS_RECORD_DIR)
    args = parser.parse_args()

    txid_bits = config.TXID_BITS
    port_bits = args.port_bits
    leak_bits = args.leak_bits
    if args.eff_bits is not None:
        # eff_bits = txid_bits + (port_bits - k); hold txid_bits fixed, solve k.
        leak_bits = max(0, txid_bits + port_bits - args.eff_bits)

    kinds: list[DrawKind] = [k.strip() for k in args.kind.split(",")]
    parallels = [int(p.strip()) for p in args.parallel.split(",")]
    baseline_parallel = parallels[0]

    base_tag = f"{int(time.time())}-{args.seed}"

    for kind in kinds:
        baseline_rate: float | None = None
        for parallel in parallels:
            record = collect_cell(
                kind,
                txid_bits=txid_bits,
                port_bits=port_bits,
                k=leak_bits,
                send_rate_pps=args.send_rate,
                parallel_queries=parallel,
                trials=args.trials,
                seed=args.seed,
            )
            if parallel == baseline_parallel:
                baseline_rate = record.poison_rate
            amp = (
                amplification_factor(record.poison_rate, baseline_rate)
                if baseline_rate is not None
                else None
            )
            record = dataclasses.replace(record, amplification_factor=amp)

            cell_tag = f"{base_tag}-{kind}-p{parallel}"
            write_row(record, args.out, run_tag=cell_tag)
            record_path = os.path.join(args.record_dir, f"{cell_tag}.record.json")
            write_record_json(record, record_path, run_tag=cell_tag)

            print(
                f"kind={kind} eff_bits={record.effective_bits} k={leak_bits} "
                f"send_rate={args.send_rate} parallel={parallel} trials={args.trials} "
                f"poison_rate={record.poison_rate:.4f} "
                f"amplification_factor={amp} "
                f"-> {args.out}, {record_path}"
            )

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
