"""Deliverable D (plan-10 §Deliverable D, epic §8 Q4): emit the P6 Tier-B
replay subset `web/public/replay/*.json` from the produced per-poll CSVs.

The web reader (`web/lib/replay.ts` / `ws.ts`) expects a JSON array of
`PortStatsMessage` -- `{link_utils: number[], victim_mbps: number,
jains_index: number}` per poll -- NOT the flat CSV column layout. This maps
the frozen P4 per-poll CSV (`link{i}_util`, `victim_mbps`, `jains_index`)
into that array shape. It also drops the real Q-EaaS provenance receipt (from
the qrng cell's `.record.json`) into `qrng-provenance.json`, replacing the
sample placeholder (plan-6 L251-253).

Recorded subset (epic §8 Q4 decision -- the three scenes + a QRNG provenance
run + the full rotation-interval sweep the Scene-3 slider drives; blind is
skipped, noted in the demo README).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from testbed import config
from testbed.experiments.matrix import (
    EXP1_VOLUMETRIC,
    EXP2_PRECISION_RATE_LIMIT,
    EXP4B_CSPRNG_ROTATION,
    EXP4C_QRNG_ROTATION,
    EXP5_SWEEP,
    ExperimentCell,
)

_REPLAY_DIR = Path(__file__).resolve().parents[2] / "web" / "public" / "replay"


def _poll_messages(cell: ExperimentCell) -> list[dict]:
    """Read a cell's per-poll CSV into `PortStatsMessage[]` shape."""
    csv_path = Path(cell.csv_path)
    if not csv_path.exists():
        return []
    messages: list[dict] = []
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            link_utils = [float(row[f"link{i}_util"]) for i in range(config.N_LINKS)]
            victim = row.get("victim_mbps", "")
            messages.append(
                {
                    "link_utils": link_utils,
                    "victim_mbps": float(victim) if victim else 0.0,
                    "jains_index": float(row["jains_index"]),
                }
            )
    return messages


def _write(name: str, payload) -> Path:
    _REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    out = _REPLAY_DIR / f"{name}.json"
    out.write_text(json.dumps(payload, indent=2))
    return out


def export_replay_subset() -> list[Path]:
    """Emit the Tier-B replay subset; returns the files written."""
    written: list[Path] = []

    # Three scenes (epic §8 Q4): volumetric+defences, precision weak-PRNG,
    # csprng+rotation dispersal.
    scenes = {
        "scene1_volumetric": EXP1_VOLUMETRIC,
        "scene2_precision": EXP2_PRECISION_RATE_LIMIT,
        "scene3_rotation": EXP4B_CSPRNG_ROTATION,
    }
    for name, cell in scenes.items():
        messages = _poll_messages(cell)
        if messages:
            written.append(_write(name, messages))

    # Full rotation-interval sweep the Scene-3 slider drives.
    for cell in EXP5_SWEEP:
        messages = _poll_messages(cell)
        if messages:
            name = f"sweep_{str(cell.rotation_interval).replace('.', '_')}s"
            written.append(_write(name, messages))

    # Real Q-EaaS provenance receipt (replaces the sample placeholder).
    record_path = Path(EXP4C_QRNG_ROTATION.csv_path).with_suffix(".record.json")
    if record_path.exists():
        record = json.loads(record_path.read_text())
        provenance = record.get("qrng_provenance")
        if provenance is not None:
            written.append(_write("qrng-provenance", provenance))

    return written


def main() -> int:
    written = export_replay_subset()
    if not written:
        print("no replay files written -- run the sim first (results/**/*.csv missing)")
        return 1
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
