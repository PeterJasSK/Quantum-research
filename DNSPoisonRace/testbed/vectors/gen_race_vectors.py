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
from testbed.attacker.guessing import GuessStream  # noqa: E402
from testbed.attacker.portable_prng import bounded  # noqa: E402
from testbed.sim.race import run_attack_race, run_race  # noqa: E402
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

# Real off-path flood scenarios (P3, AC-3.4). Each: (seed, txid, port,
# port_bits, k, rtt, retransmit, send_rate_pps, parallel_queries,
# retransmit_rounds). `txid`/`port` are the *target* (first window's) draw --
# used at k=0 only here, so the effective index decodes back to them exactly
# (display/cross-check). All randomness (jitter, guess order) flows through
# `portable_prng.splitmix64`, seeded by `seed` -- the parity contract P6
# vendors verbatim.
FLOOD_SCENARIOS = [
    (101, 4242, 33333, 16, 0, 0.02, 0.5, 20000, 1, 1),
    (102, 100, 200, 16, 0, 0.02, 0.5, 20000, 4, 1),
    (103, 65535, 65535, 16, 0, 0.01, 0.2, 50000, 1, 2),
]


def _flood_vector(
    seed: int,
    txid: int,
    port: int,
    port_bits: int,
    k: int,
    rtt: float,
    retransmit: float,
    send_rate_pps: int,
    parallel_queries: int,
    retransmit_rounds: int,
) -> dict:
    """Thin adapter: derives the flood's target indices + jitter from the
    portable PRNG (mirroring what `attacker/attack.py` does with real draws),
    so the JS mirror reproduces this vector without a Python-only draw
    source. The first query's first-round target is pinned to `(txid, port)`
    at `k=0`; later rounds/queries draw fresh targets from the same stream."""
    space_size = 1 << (config.TXID_BITS + port_bits)
    state = seed
    windows_spec: list[list[tuple[int, float, float]]] = []

    target0 = (txid << port_bits) | port
    max_t_authoritative = 0.0
    for q_index in range(parallel_queries):
        rounds: list[tuple[int, float, float]] = []
        for round_index in range(retransmit_rounds + 1):
            if q_index == 0 and round_index == 0:
                target_index = target0
            else:
                target_index, state = bounded(state, space_size)
            t_open = round_index * retransmit
            jitter_unit, state = bounded(state, 1_000_000)
            jitter = (jitter_unit / 1_000_000 - 0.5) * 2 * config.RTT_JITTER_FRAC * rtt
            t_authoritative = t_open + rtt + jitter
            rounds.append((target_index, t_open, t_authoritative))
            max_t_authoritative = max(max_t_authoritative, t_authoritative)
        windows_spec.append(rounds)

    guess_stream = GuessStream(space_size=space_size, state=state)
    forged_count = int(max_t_authoritative * send_rate_pps)
    send_schedule = (
        [max_t_authoritative / forged_count * (i + 0.5) for i in range(forged_count)]
        if forged_count > 0
        else []
    )

    result = run_attack_race(
        windows_spec=windows_spec,
        guess_stream=guess_stream,
        send_rate_pps=send_rate_pps,
        rtt=rtt,
        retransmit=retransmit,
        parallel_queries=parallel_queries,
        seed=seed,
    )

    eff_bits = config.TXID_BITS + max(0, port_bits - k)
    return {
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
    for flood_scenario in FLOOD_SCENARIOS:
        vectors.append(_flood_vector(*flood_scenario))
    return vectors


def main() -> int:
    vectors = generate()
    OUTPUT_PATH.write_text(json.dumps(vectors, indent=2) + "\n")
    print(f"wrote {len(vectors)} vectors to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
