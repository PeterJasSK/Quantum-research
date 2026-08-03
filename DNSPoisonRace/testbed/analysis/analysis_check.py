#!/usr/bin/env python3
"""Offline correctness gate for P5's `experiments/`, `analysis/`, `sim/replay_export.py`
(epic §9 P5, project directive -- no `pytest`). Standalone, root-free, network-free --
builds synthetic CSV rows on the frozen P4 schema, never calls `collect_cell`/
`run_poison_race` for the sweep aggregates, so it can't be invalidated by an upstream
P1-P4 change, only by a P5 regression. The one place it does call `run_poison_race`
(via a monkeypatched `_race_scene`) is stubbed out entirely for the replay-export check.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testbed import config  # noqa: E402
from testbed.experiments import matrix  # noqa: E402
from testbed.resolver.csv_writer import CSV_FIELDS  # noqa: E402

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


def _check_matrix_shape() -> None:
    bit_sweep = range(config.EFF_BITS_MIN, config.EFF_BITS_MAX + 1, config.EFF_BITS_STEP)
    _check("(a) CLIFF has 4 sources x the bit sweep", len(matrix.CLIFF) == 4 * len(bit_sweep))
    _check("(a) COLLAPSE has PORT_BITS + 1 cells", len(matrix.COLLAPSE) == config.PORT_BITS + 1)
    _check(
        "(a) every ExperimentCell.k matches the max(0, TXID+PORT-eff) identity",
        all(
            cell.k == max(0, config.TXID_BITS + config.PORT_BITS - cell.effective_bits)
            for group in (matrix.CLIFF, matrix.COLLAPSE, matrix.BIRTHDAY)
            for cell in group
        ),
    )
    _check(
        "(a) cells_for('all') is the exact concatenation",
        matrix.cells_for("all") == [*matrix.CLIFF, *matrix.COLLAPSE, *matrix.BIRTHDAY],
    )
    try:
        matrix.cells_for("bogus")
        raised = False
    except ValueError:
        raised = True
    _check("(a) cells_for('bogus') raises ValueError", raised)


def _synthetic_row(
    *,
    kind: str,
    effective_bits: int,
    k: int,
    poison_rate: float,
    send_rate_pps: int = 10000,
    parallel_queries: int = 1,
    run_tag: str = "check",
) -> dict:
    return {
        "run_tag": run_tag,
        "timestamp": "2026-01-01T00:00:00Z",
        "kind": kind,
        "effective_bits": effective_bits,
        "k": k,
        "send_rate_pps": send_rate_pps,
        "parallel_queries": parallel_queries,
        "trials": 500,
        "poison_rate": poison_rate,
        "mean_forged_packets": 4.0,
        "mean_time_to_poison": 0.1,
        "amplification_factor": "",
    }


def _write_synthetic_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _cliff_and_collapse_rows() -> list[dict]:
    cliff = [
        _synthetic_row(kind=kind, effective_bits=eff, k=max(0, 32 - eff), poison_rate=1.0 - eff / 32)
        for kind in ("fixed", "prng", "csprng", "qrng")
        for eff in (8, 16, 24, 32)
    ]
    collapse = [
        _synthetic_row(kind="csprng", effective_bits=32 - k, k=k, poison_rate=k / 16)
        for k in range(0, 17)
    ]
    return cliff + collapse


def _check_renders() -> None:
    from testbed.analysis.graphs import render_cliff, render_collapse

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "metrics.csv"
        _write_synthetic_csv(csv_path, _cliff_and_collapse_rows())

        cliff_out = render_cliff(csv_path=str(csv_path), output_prefix=str(Path(tmp) / "cliff"))
        _check(
            "(b) render_cliff writes both .png and .svg",
            cliff_out.with_suffix(".png").exists() and cliff_out.with_suffix(".svg").exists(),
        )

        collapse_out = render_collapse(csv_path=str(csv_path), output_prefix=str(Path(tmp) / "collapse"))
        _check(
            "(c) render_collapse writes both .png and .svg",
            collapse_out.with_suffix(".png").exists() and collapse_out.with_suffix(".svg").exists(),
        )


def _check_load_dedup() -> None:
    from testbed.analysis.graphs import _load

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "metrics.csv"
        _write_synthetic_csv(
            csv_path,
            [
                _synthetic_row(kind="csprng", effective_bits=16, k=16, poison_rate=0.9, run_tag="r1"),
                _synthetic_row(kind="csprng", effective_bits=16, k=16, poison_rate=0.1, run_tag="r2"),
            ],
        )
        df = _load(str(csv_path))
        matching = df[(df["kind"] == "csprng") & (df["effective_bits"] == 16)]
        _check(
            "(d) _load keeps the last row per cell key on an appended rerun",
            len(matching) == 1 and float(matching["poison_rate"].iloc[0]) == 0.1,
        )


def _check_replay_export() -> None:
    import testbed.sim.replay_export as replay_export

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        csv_path = tmp_path / "metrics.csv"
        record_dir = tmp_path / "records"
        record_dir.mkdir()
        replay_dir = tmp_path / "replay"

        _write_synthetic_csv(csv_path, _cliff_and_collapse_rows())

        original_replay_dir = replay_export._REPLAY_DIR
        original_race_scene = replay_export._race_scene
        replay_export._REPLAY_DIR = replay_dir
        replay_export._race_scene = lambda kind, *, seed: {
            "kind": kind,
            "seed": seed,
            "txid_bits": 16,
            "port_bits": 16,
            "k": 0,
            "send_rate_pps": 10000,
            "rtt": 0.02,
            "retransmit": 0.5,
            "parallel_queries": 1,
            "outcome": "poisoned",
            "t_outcome": 0.1,
            "forged_packets": 3,
        }
        try:
            written_no_record = replay_export.export_replay(
                csv_path=str(csv_path), record_dir=str(record_dir)
            )
            placeholder = json.loads((replay_dir / "qrng-provenance.json").read_text())
            _check(
                "(e) missing qrng record yields the placeholder, not a crash",
                placeholder == replay_export._PLACEHOLDER_PROVENANCE,
            )
            _check("(e) export_replay writes files with a missing qrng record", len(written_no_record) > 0)

            qrng_provenance = {"kind": "qrng", "detail": {"request_id": "abc123"}}
            qrng_record = {
                "run_tag": "check",
                "kind": "qrng",
                "effective_bits": 16,
                "k": 16,
                "send_rate_pps": 10000,
                "parallel_queries": 1,
                "trials": 500,
                "poison_rate": 0.5,
                "mean_forged_packets": 4.0,
                "mean_time_to_poison": 0.1,
                "amplification_factor": None,
                "provenance": qrng_provenance,
            }
            (record_dir / "check-qrng.record.json").write_text(json.dumps(qrng_record))

            written = replay_export.export_replay(csv_path=str(csv_path), record_dir=str(record_dir))
            names = {path.name for path in written}
            expected_names = {
                "cliff.json",
                "collapse.json",
                "qrng-provenance.json",
                "race_fixed.json",
                "race_prng.json",
                "race_csprng.json",
                "race_qrng.json",
            }
            _check("(e) export_replay writes all documented files", expected_names.issubset(names))

            cliff_payload = json.loads((replay_dir / "cliff.json").read_text())
            collapse_payload = json.loads((replay_dir / "collapse.json").read_text())
            _check(
                "(e) cliff.json / collapse.json round-trip with documented top-level keys",
                "sources" in cliff_payload and "series" in collapse_payload,
            )

            provenance_payload = json.loads((replay_dir / "qrng-provenance.json").read_text())
            _check(
                "(e) qrng-provenance.json carries the real record's provenance once present",
                provenance_payload == qrng_provenance,
            )
        finally:
            replay_export._REPLAY_DIR = original_replay_dir
            replay_export._race_scene = original_race_scene


def main() -> int:
    _check_matrix_shape()
    _check_renders()
    _check_load_dedup()
    _check_replay_export()

    print(f"\n{_checks_run - _checks_failed}/{_checks_run} checks passed")
    if _checks_failed:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
