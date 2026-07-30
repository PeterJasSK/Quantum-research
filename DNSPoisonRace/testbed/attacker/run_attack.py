#!/usr/bin/env python3
"""CLI runner (epic ss9 P3). Runs `--trials` poison races through
`run_poison_race` and prints per-trial outcomes plus a final poison-rate
summary. Root-free, network-free (network only if `--kind qrng` and
`QEAAS_API_KEY` set)."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testbed import config  # noqa: E402
from testbed.attacker.attack import run_poison_race  # noqa: E402
from testbed.draw.sources import DrawKind  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the DNS off-path poison race (plan-3).")
    parser.add_argument("--kind", choices=["fixed", "prng", "csprng", "qrng"], required=True)
    parser.add_argument("--eff-bits", type=int, default=None, help="derive txid_bits/port_bits from this")
    parser.add_argument("--port-bits", type=int, default=config.PORT_BITS)
    parser.add_argument("-k", "--leak-bits", type=int, default=config.SAD_DNS_LEAK_BITS)
    parser.add_argument("--send-rate", type=int, default=config.ATTACKER_SEND_RATE_PPS)
    parser.add_argument("--rtt", type=float, default=config.RTT_SECONDS)
    parser.add_argument("--retransmit", type=float, default=config.RETRANSMIT_SECONDS)
    parser.add_argument("--parallel", type=int, default=config.PARALLEL_QUERIES)
    parser.add_argument("--trials", type=int, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    txid_bits = config.TXID_BITS
    port_bits = args.port_bits
    if args.eff_bits is not None:
        # eff_bits = txid_bits + (port_bits - k); hold txid_bits fixed, solve k.
        args.leak_bits = max(0, txid_bits + port_bits - args.eff_bits)

    kind: DrawKind = args.kind
    poisoned = 0
    for trial in range(args.trials):
        result = run_poison_race(
            kind,
            txid_bits=txid_bits,
            port_bits=port_bits,
            k=args.leak_bits,
            send_rate_pps=args.send_rate,
            rtt=args.rtt,
            retransmit=args.retransmit,
            parallel_queries=args.parallel,
            seed=args.seed + trial,
        )
        if result.outcome == "poisoned":
            poisoned += 1
        if args.trials <= 20:
            print(
                f"trial={trial} outcome={result.outcome} t_outcome={result.t_outcome:.6f} "
                f"forged_packets={result.forged_packets} eff_bits={result.effective_bits}"
            )

    rate = poisoned / args.trials if args.trials else 0.0
    print(
        f"kind={kind} eff_bits={txid_bits + max(0, port_bits - args.leak_bits)} "
        f"send_rate={args.send_rate} parallel={args.parallel} trials={args.trials} "
        f"poison_rate={rate:.4f} ({poisoned}/{args.trials})"
    )
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
