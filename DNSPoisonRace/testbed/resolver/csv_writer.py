"""Run-tagged CSV writer + per-cell `.record.json` writer (epic §9 P4,
AC-4.5). Stdlib `csv`/`json` only -- no pandas (confined to P5's
`analysis/`).
"""
from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import asdict

from .metrics import CellRecord

CSV_FIELDS = [
    "run_tag",
    "timestamp",
    "kind",
    "effective_bits",
    "k",
    "send_rate_pps",
    "parallel_queries",
    "trials",
    "poison_rate",
    "mean_forged_packets",
    "mean_time_to_poison",
    "amplification_factor",
]


def write_row(record: CellRecord, path: str, *, run_tag: str) -> None:
    """Append one row (creates file + header on first write) to the frozen
    CSV schema (epic §9 P4 CSV schema). Provenance is not a CSV column -- it
    lives in the `.record.json` sidecar."""
    write_header = not os.path.exists(path) or os.path.getsize(path) == 0
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "run_tag": run_tag,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "kind": record.kind,
                "effective_bits": record.effective_bits,
                "k": record.k,
                "send_rate_pps": record.send_rate_pps,
                "parallel_queries": record.parallel_queries,
                "trials": record.trials,
                "poison_rate": record.poison_rate,
                "mean_forged_packets": record.mean_forged_packets,
                "mean_time_to_poison": record.mean_time_to_poison,
                "amplification_factor": record.amplification_factor,
            }
        )


def write_record_json(record: CellRecord, path: str, *, run_tag: str) -> None:
    """One JSON object per cell, embedding the cell's provenance verbatim
    (AC-4.5). Written for every cell, not only `qrng`, so P5/P6 have one
    consistent per-cell artefact."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    payload = {
        "run_tag": run_tag,
        "kind": record.kind,
        "effective_bits": record.effective_bits,
        "k": record.k,
        "send_rate_pps": record.send_rate_pps,
        "parallel_queries": record.parallel_queries,
        "trials": record.trials,
        "poison_rate": record.poison_rate,
        "mean_forged_packets": record.mean_forged_packets,
        "mean_time_to_poison": record.mean_time_to_poison,
        "amplification_factor": record.amplification_factor,
        "provenance": asdict(record.provenance),
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
