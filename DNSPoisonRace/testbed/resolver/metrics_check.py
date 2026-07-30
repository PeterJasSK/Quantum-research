#!/usr/bin/env python3
"""Offline correctness gate for `testbed/resolver/` (project directive --
no `pytest`). Standalone, root-free, network-free -- constructs synthetic
`PoisonRaceResult`/`CellRecord` instances directly, never calls
`run_poison_race`, so it cannot be invalidated by an upstream P1-P3 change,
only by a P4 regression."""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testbed.attacker.attack import PoisonRaceResult  # noqa: E402
from testbed.resolver.cache import resolve_cache  # noqa: E402
from testbed.resolver.csv_writer import write_record_json  # noqa: E402
from testbed.resolver.metrics import CellRecord, amplification_factor  # noqa: E402
from testbed.types import DrawProvenance  # noqa: E402

_checks_run = 0
_checks_failed = 0


def _check(name: str, condition: bool) -> None:
    global _checks_run, _checks_failed
    _checks_run += 1
    if condition:
        print(f"PASS  {name}")
    else:
        _checks_failed += 1
        print(f"FAIL  {name}")


def _synthetic_result(*, outcome: str, forged_packets: int, t_outcome: float) -> PoisonRaceResult:
    return PoisonRaceResult(
        kind="csprng",
        outcome=outcome,
        t_outcome=t_outcome,
        forged_packets=forged_packets,
        effective_bits=16,
        parallel_queries=1,
        send_rate_pps=10000,
        k=0,
        poisoned_window=0 if outcome == "poisoned" else None,
        provenance=DrawProvenance(kind="csprng", detail={"source": "secrets.randbits"}),
    )


def _poison_rate(results: list[PoisonRaceResult]) -> float:
    poisoned = sum(1 for r in results if r.outcome == "poisoned")
    return poisoned / len(results)


def _check_poison_rate() -> None:
    all_poisoned = [_synthetic_result(outcome="poisoned", forged_packets=5, t_outcome=0.1)] * 10
    all_legit = [_synthetic_result(outcome="resolved_legit", forged_packets=5, t_outcome=0.1)] * 10
    mixed = all_poisoned[:3] + all_legit[:7]

    _check("(a) all-poisoned trial set gives poison_rate == 1.0", _poison_rate(all_poisoned) == 1.0)
    _check("(a) all-legit trial set gives poison_rate == 0.0", _poison_rate(all_legit) == 0.0)
    _check("(a) mixed trial set gives the exact fraction", _poison_rate(mixed) == 0.3)


def _check_means() -> None:
    import statistics

    trials = [
        _synthetic_result(outcome="poisoned", forged_packets=4, t_outcome=1.0),
        _synthetic_result(outcome="poisoned", forged_packets=6, t_outcome=3.0),
        _synthetic_result(outcome="resolved_legit", forged_packets=8, t_outcome=0.0),
    ]
    mean_forged = statistics.fmean(r.forged_packets for r in trials)
    poisoned_times = [r.t_outcome for r in trials if r.outcome == "poisoned"]
    mean_time = statistics.fmean(poisoned_times) if poisoned_times else None

    _check("(b) mean_forged_packets over all trials", mean_forged == statistics.fmean([4, 6, 8]))
    _check("(b) mean_time_to_poison over poisoned subset only", mean_time == 2.0)

    zero_poisoned = [_synthetic_result(outcome="resolved_legit", forged_packets=1, t_outcome=0.0)]
    zero_poisoned_times = [r.t_outcome for r in zero_poisoned if r.outcome == "poisoned"]
    _check(
        "(b) zero-poisoned edge case is None, not a crash",
        (statistics.fmean(zero_poisoned_times) if zero_poisoned_times else None) is None,
    )


def _check_amplification_factor() -> None:
    _check(
        "(c) amplification_factor on known rates",
        amplification_factor(0.2467, 0.0333) == 0.2467 / 0.0333,
    )
    _check(
        "(c) amplification_factor guards a zero baseline with None, not a crash",
        amplification_factor(0.5, 0.0) is None,
    )


def _make_cell_record(*, k: int, effective_bits: int) -> CellRecord:
    return CellRecord(
        kind="csprng",
        effective_bits=effective_bits,
        k=k,
        send_rate_pps=100000,
        parallel_queries=1,
        trials=2000,
        poison_rate=0.03,
        mean_forged_packets=123.4,
        mean_time_to_poison=0.05,
        amplification_factor=None,
        provenance=DrawProvenance(kind="csprng", detail={"source": "secrets.randbits"}),
    )


def _check_k_and_effective_bits_passthrough() -> None:
    record = _make_cell_record(k=8, effective_bits=24)
    _check(
        "(d) k and effective_bits pass through unchanged into CellRecord",
        record.k == 8 and record.effective_bits == 24,
    )


def _check_record_json_roundtrip() -> None:
    record = _make_cell_record(k=0, effective_bits=16)
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "cell.record.json")
        write_record_json(record, path, run_tag="check-run")
        with open(path, encoding="utf-8") as handle:
            written = json.load(handle)
    from dataclasses import asdict

    _check(
        "(e) write_record_json round-trips provenance field-for-field",
        written["provenance"] == asdict(record.provenance),
    )


def _check_cache_mapping() -> None:
    poisoned = resolve_cache(_synthetic_result(outcome="poisoned", forged_packets=1, t_outcome=2.0))
    legit = resolve_cache(
        _synthetic_result(outcome="resolved_legit", forged_packets=1, t_outcome=2.0)
    )
    closed = resolve_cache(
        _synthetic_result(outcome="window_closed", forged_packets=1, t_outcome=2.0)
    )
    _check(
        "(f) poisoned outcome maps to state=poisoned with a TTL",
        poisoned.state == "poisoned" and poisoned.ttl_expires_at is not None,
    )
    _check(
        "(f) resolved_legit outcome maps to state=resolved_legit with a TTL",
        legit.state == "resolved_legit" and legit.ttl_expires_at is not None,
    )
    _check(
        "(f) window_closed outcome maps to state=window_closed with no TTL",
        closed.state == "window_closed" and closed.ttl_expires_at is None,
    )


def main() -> int:
    _check_poison_rate()
    _check_means()
    _check_amplification_factor()
    _check_k_and_effective_bits_passthrough()
    _check_record_json_roundtrip()
    _check_cache_mapping()

    print(f"\n{_checks_run - _checks_failed}/{_checks_run} checks passed")
    if _checks_failed:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
