"""Run-tagged CSV row writer + summary-sidecar writer (P4, Done-when).

Frozen header/schema (epic §4 / plan-4 CSV schema) -- P5's matrix and P6
Tier-B replay parse it positionally/by-name; a renamed or dropped column
silently breaks them. Uses stdlib `csv`, no hand-rolled formatting.
"""
from __future__ import annotations

import csv
from pathlib import Path


def per_poll_header(n_links: int) -> list[str]:
    link_cols = [f"link{i}_util" for i in range(n_links)]
    return [
        "timestamp",
        "elapsed_seconds",
        "salt_source",
        "knowledge_level",
        "rotation_interval",
        "attack_mode",
        *link_cols,
        "max_link_util",
        "jains_index",
        "victim_mbps",
        "target_link",
        "target_tx_packets",
        "tracked_flows",
    ]


SUMMARY_HEADER = [
    "salt_source",
    "knowledge_level",
    "rotation_interval",
    "attack_mode",
    "time_to_saturation_s",
    "packets_to_saturation",
    "flows_to_saturation",
    "final_jains_index",
    "min_victim_mbps",
    "saturated",
]


class CsvWriter:
    """Appends per-poll rows to `csv_path` and writes the `*.summary.csv`
    sidecar next to it, both with the frozen headers above."""

    def __init__(self, csv_path: str, n_links: int) -> None:
        self._csv_path = Path(csv_path)
        self._summary_path = self._csv_path.with_suffix(".summary.csv")
        self._header = per_poll_header(n_links)
        self._wrote_header = self._csv_path.exists() and self._csv_path.stat().st_size > 0

    def write_row(self, row: dict) -> None:
        with self._csv_path.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self._header)
            if not self._wrote_header:
                writer.writeheader()
                self._wrote_header = True
            writer.writerow(row)

    def write_summary(self, row: dict) -> None:
        """Rewrites the sidecar with the single up-to-date summary row for
        this run (OQ-2: one row per run, updated as saturation/final metrics
        are known -- not appended per poll)."""
        with self._summary_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=SUMMARY_HEADER)
            writer.writeheader()
            writer.writerow(row)
