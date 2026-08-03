"""Orchestrator (epic ss9 P3). The one place `draw_source` + `sad_dns` + the
engine meet. Mints the true draw through P2's factory, sizes the search
through P2's `effective_bits`, races on the frozen `EventQueue` via
`sim.race.run_attack_race` -- never re-implements the draw, the entropy-
reduction knob, or the event core (epic ss3.5)."""
from __future__ import annotations

from dataclasses import dataclass

from testbed import config
from testbed.draw.sad_dns import effective_bits
from testbed.draw.source_model import attacker_search_bits
from testbed.draw.sources import DrawKind, draw_source
from testbed.sim.race import run_attack_race
from testbed.types import DrawProvenance

from .guessing import GuessStream, effective_index
from .portable_prng import bounded


@dataclass(frozen=True)
class PoisonRaceResult:
    """Frozen for P4 (epic ss9 P3) -- P4 reads these fields into the CSV +
    `.record.json` without reshaping."""

    kind: str
    outcome: str
    t_outcome: float
    forged_packets: int
    effective_bits: int
    parallel_queries: int
    send_rate_pps: int
    k: int
    poisoned_window: int | None
    provenance: DrawProvenance


def run_poison_race(
    kind: DrawKind,
    *,
    txid_bits: int = config.TXID_BITS,
    port_bits: int = config.PORT_BITS,
    k: int = config.SAD_DNS_LEAK_BITS,
    send_rate_pps: int = config.ATTACKER_SEND_RATE_PPS,
    rtt: float = config.RTT_SECONDS,
    retransmit: float = config.RETRANSMIT_SECONDS,
    parallel_queries: int = config.PARALLEL_QUERIES,
    seed: int,
) -> PoisonRaceResult:
    """The single entry point P4 calls per sweep cell (epic ss9 P3). Mints
    `parallel_queries * (MAX_RETRANSMITS + 1)` draws via `draw_source(kind)`
    -- one per window, including retransmit-spawned windows (epic ss5,
    Kaminsky amplification, OQ-P3.4) -- builds each window's target index and
    (portable-PRNG-jittered) authoritative arrival, and runs the race on
    `sim.race.run_attack_race`."""
    # `eff_bits` is the defender's *nominal* entropy (the cliff x-axis). The
    # attacker's real problem can be smaller for a weak source (epic §3.2/§6a):
    # `fixed`'s known port and `prng`'s recoverable state shrink the space the
    # flood must cover, so the poison probability keys on `search_bits`, not
    # `eff_bits`. csprng/qrng get no discount -> they overlap (M5: QRNG's
    # differentiator is the signed receipt, not a lower rate).
    eff_bits = effective_bits(txid_bits, port_bits, k)
    search_bits = attacker_search_bits(
        kind, txid_bits=txid_bits, port_bits=port_bits, k=k, prng_leak_bits=config.PRNG_LEAK_BITS
    )
    space_size = 1 << search_bits

    state = seed
    windows_spec: list[list[tuple[int, float, float]]] = []
    first_provenance: DrawProvenance | None = None

    for _ in range(parallel_queries):
        rounds: list[tuple[int, float, float]] = []
        for round_index in range(config.MAX_RETRANSMITS + 1):
            draw = draw_source(kind, txid_bits=txid_bits, port_bits=port_bits)
            if first_provenance is None:
                first_provenance = draw.provenance
            target_index = effective_index(draw, port_bits, k)
            t_open = round_index * retransmit
            jitter_unit, state = bounded(state, 1_000_000)
            jitter = (jitter_unit / 1_000_000 - 0.5) * 2 * config.RTT_JITTER_FRAC * rtt
            t_authoritative = t_open + rtt + jitter
            rounds.append((target_index, t_open, t_authoritative))
        windows_spec.append(rounds)

    guess_stream = GuessStream(space_size=space_size, state=state)

    result = run_attack_race(
        windows_spec=windows_spec,
        guess_stream=guess_stream,
        send_rate_pps=send_rate_pps,
        rtt=rtt,
        retransmit=retransmit,
        parallel_queries=parallel_queries,
        seed=seed,
        guess_budget=config.ATTACK_GUESS_BUDGET,
        attempts=config.ATTACK_ATTEMPTS,
    )

    assert first_provenance is not None  # parallel_queries >= 1 guarantees at least one draw
    return PoisonRaceResult(
        kind=kind,
        outcome=result.outcome,
        t_outcome=result.t_outcome,
        forged_packets=result.forged_packets,
        effective_bits=eff_bits,
        parallel_queries=parallel_queries,
        send_rate_pps=send_rate_pps,
        k=k,
        poisoned_window=result.poisoned_window,
        provenance=first_provenance,
    )
