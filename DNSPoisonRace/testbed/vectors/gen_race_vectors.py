#!/usr/bin/env python3
"""Generate `race_vectors.json` from the Python race engine (source of
truth, epic §4). Standalone; imports only `types`/`sim.race`/`config`.
Deterministic (seeded) -- seeds the P6 parity gate (OQ-P1.3 schema)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from testbed import config  # noqa: E402
from testbed.sim.race import run_race  # noqa: E402
from testbed.types import Draw, DrawProvenance  # noqa: E402

OUTPUT_PATH = Path(__file__).with_name("race_vectors.json")

# Each scenario: (seed, txid, port, forged_guess, rtt, retransmit, send_schedule,
# parallel_queries). P1 has no retransmit/parallel-window logic yet (P3), so
# those fields are recorded as fixed placeholders for schema stability.
SCENARIOS = [
    (1, 4242, 33333, (1, 1), 0.02, 0.5, [0.001], 1),
    (2, 100, 200, (100, 200), 0.02, 0.5, [0.001], 1),
    (3, 65535, 65535, (65534, 65535), 0.02, 0.5, [0.005, 0.010], 1),
    (4, 0, 0, (0, 0), 0.01, 0.5, [0.0005], 1),
]


def generate() -> list[dict]:
    vectors = []
    for seed, txid, port, forged_guess, rtt, retransmit, send_schedule, parallel_queries in SCENARIOS:
        draw = Draw(txid, port, DrawProvenance())
        result = run_race(
            draw=draw,
            forged_guess=forged_guess,
            rtt=rtt,
            send_schedule=send_schedule,
            seed=seed,
        )
        eff_bits = config.TXID_BITS + config.PORT_BITS
        vectors.append(
            {
                "seed": seed,
                "txid": txid,
                "port": port,
                "eff_bits": eff_bits,
                "rtt": rtt,
                "retransmit": retransmit,
                "send_schedule": send_schedule,
                "parallel_queries": parallel_queries,
                "outcome": result.outcome,
                "forged_packets": result.forged_packets,
                "t_outcome": result.t_outcome,
            }
        )
    return vectors


def main() -> int:
    vectors = generate()
    OUTPUT_PATH.write_text(json.dumps(vectors, indent=2) + "\n")
    print(f"wrote {len(vectors)} vectors to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
