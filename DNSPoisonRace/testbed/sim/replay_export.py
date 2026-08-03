"""Freeze replay JSON for P6 (epic §9 P5, AC-5.3/AC-5.4). Mirrors the ECMP twin's
`sim/replay_export.py` shape (stdlib-plus-pandas, `_write` helper, `web/public/replay/`
created if absent) but DNS has no per-poll metric stream -- `race_<kind>.json` is a
**scenario descriptor** (OQ-P5.4), not a packet trace: one `run_poison_race` call per
source at a fixed seed, the one place this module touches the race. The sweep
aggregates (`cliff.json`/`collapse.json`) still come from the CSV `collect_cell` wrote.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from testbed import config
from testbed.attacker.attack import run_poison_race
from testbed.draw.qrng_client import QRNGUnavailable

_REPLAY_DIR = Path(__file__).resolve().parents[2] / config.WEB_REPLAY_DIR

_PLACEHOLDER_PROVENANCE = {
    "kind": "qrng",
    "detail": {
        "request_id": "sample-placeholder",
        "entropy_epoch": "0",
        "timestamp": "1970-01-01T00:00:00Z",
        "receipt": "",
        "endpoint": "sample-placeholder",
    },
}


def _write(name: str, payload: object) -> Path:
    _REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    out = _REPLAY_DIR / f"{name}.json"
    out.write_text(json.dumps(payload, indent=2))
    return out


def _cliff_json(df: pd.DataFrame) -> dict:
    """AC-5.4/AC-6.2: per-source `{effective_bits, poison_rate}` series."""
    cliff = df[df["parallel_queries"] == 1]
    sources: dict[str, list[dict]] = {}
    for kind in ("fixed", "prng", "csprng", "qrng"):
        rows = cliff[cliff["kind"] == kind].sort_values("effective_bits")
        sources[kind] = [
            {"effective_bits": int(row.effective_bits), "poison_rate": float(row.poison_rate)}
            for row in rows.itertuples()
        ]
    send_rate = int(cliff["send_rate_pps"].iloc[0]) if not cliff.empty else None
    return {"sources": sources, "send_rate_pps": send_rate}


def _collapse_json(df: pd.DataFrame) -> dict:
    """AC-5.4/AC-6.3: `{k, poison_rate}` series for the SAD-DNS reveal."""
    collapse = df[(df["kind"] == "csprng") & (df["k"] <= config.PORT_BITS)].sort_values("k")
    series = [
        {"k": int(row.k), "poison_rate": float(row.poison_rate)} for row in collapse.itertuples()
    ]
    return {"kind": "csprng", "series": series}


def _race_scene(kind: str, *, seed: int) -> dict | None:
    """AC-5.4/AC-6.1: a representative scenario descriptor the P6 JS re-simulates through
    the §3.6 parity gate (OQ-P5.4) -- a single `run_poison_race` call, not a sweep.
    `qrng` needs `QEAAS_API_KEY` and a live endpoint; absent either, this is a graceful
    skip (`None`), mirroring the qrng-provenance placeholder posture (Risks: "Live Q-EaaS
    outage at export time" -- never a crash) -- a `cliff`/`collapse`/`birthday` export
    must not fail on the one live-network source."""
    if kind == "qrng":
        if not config.QEAAS_API_KEY:
            print("WARN: QEAAS_API_KEY not set -- skipping race_qrng.json this run")
            return None
        try:
            result = run_poison_race(kind, seed=seed)
        except QRNGUnavailable as exc:
            print(f"WARN: Q-EaaS unavailable ({exc}) -- skipping race_qrng.json this run")
            return None
    else:
        result = run_poison_race(kind, seed=seed)
    return {
        "kind": result.kind,
        "seed": seed,
        "txid_bits": config.TXID_BITS,
        "port_bits": config.PORT_BITS,
        "k": result.k,
        "send_rate_pps": result.send_rate_pps,
        "rtt": config.RTT_SECONDS,
        "retransmit": config.RETRANSMIT_SECONDS,
        "parallel_queries": result.parallel_queries,
        "outcome": result.outcome,
        "t_outcome": result.t_outcome,
        "forged_packets": result.forged_packets,
    }


def _latest_qrng_record(record_dir: str) -> dict | None:
    record_dir_path = Path(record_dir)
    if not record_dir_path.is_dir():
        return None
    candidates = sorted(record_dir_path.glob("*.record.json"), key=lambda p: p.stat().st_mtime)
    for path in reversed(candidates):
        record = json.loads(path.read_text())
        if record.get("kind") == "qrng":
            return record
    return None


def export_replay(
    csv_path: str = config.RESULTS_CSV_PATH, record_dir: str = config.RESULTS_RECORD_DIR
) -> list[Path]:
    """Emit `cliff.json`, `collapse.json`, one `race_<kind>.json` per source, and
    `qrng-provenance.json` (AC-5.3: the frozen live receipt, or a placeholder + `WARN:`
    on a missing/empty qrng record -- a graceful skip, never a crash). Returns the files
    written."""
    written: list[Path] = []

    df = pd.read_csv(csv_path)
    written.append(_write("cliff", _cliff_json(df)))
    written.append(_write("collapse", _collapse_json(df)))

    for kind in ("fixed", "prng", "csprng", "qrng"):
        scene = _race_scene(kind, seed=config.PRNG_SEED)
        if scene is not None:
            written.append(_write(f"race_{kind}", scene))

    record = _latest_qrng_record(record_dir)
    if record is not None:
        written.append(_write("qrng-provenance", record["provenance"]))
    else:
        print("WARN: no qrng .record.json found -- writing sample placeholder for qrng-provenance.json")
        written.append(_write("qrng-provenance", _PLACEHOLDER_PROVENANCE))

    return written


def main() -> int:
    written = export_replay()
    if not written:
        print("no replay files written -- run run_experiments.py first")
        return 1
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
