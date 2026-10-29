"""Append-only, hash-chained ledger of receipts (AC-6). Entry format: the frozen ledger_entry contract.

entry_hash = sha256(canonical_json(entry minus entry_hash)); genesis prev_hash = 64 x "0".
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from shared import CONTRACT_VERSION, RE_ROOT
from shared.seedhash import canonical_json, sha256_bytes
from shared.validate import ledger_errors

LEDGER = RE_ROOT / "G_provenance" / "runs" / "ledger.jsonl"
ZERO = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read(path: Path = LEDGER) -> list[dict]:
    if not Path(path).is_file():
        return []
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def make_entry(index: int, kind: str, prev_hash: str, receipt_sha256: str, created_utc: str) -> dict:
    e = {"contract": "ledger_entry", "contract_version": CONTRACT_VERSION, "index": index, "kind": kind,
         "prev_hash": prev_hash, "receipt_sha256": receipt_sha256, "created_utc": created_utc}
    e["entry_hash"] = sha256_bytes(canonical_json(e))
    return e


def write(entries: list[dict], path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries))


def ensure_genesis(path: Path = LEDGER) -> None:
    if not read(path):
        write([make_entry(0, "genesis", ZERO, ZERO, _now())], path)


def append(receipt_sha256: str, path: Path = LEDGER) -> dict:
    """Append a kind "receipt" entry (commit entries are receipts in state "committed", CCR-G1)."""
    ensure_genesis(path)
    entries = read(path)
    entry = make_entry(len(entries), "receipt", entries[-1]["entry_hash"], receipt_sha256, _now())
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def find_receipt(receipt_sha256: str, path: Path = LEDGER) -> dict | None:
    for e in read(path):
        if e["kind"] == "receipt" and e["receipt_sha256"] == receipt_sha256:
            return e
    return None


def verify_chain(path: Path = LEDGER) -> list[str]:
    return ledger_errors(Path(path))


def rechain(entries: list[dict]) -> list[dict]:
    """Re-number and re-hash entries in order (used by the forgery attacks in the r19 reproduction)."""
    out, prev = [], ZERO
    for i, e in enumerate(entries):
        n = make_entry(i, e["kind"], prev, e["receipt_sha256"], e["created_utc"])
        out.append(n)
        prev = n["entry_hash"]
    return out
