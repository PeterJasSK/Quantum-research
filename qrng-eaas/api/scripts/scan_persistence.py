"""S10.4/AC-7: persistence-invariant scan.

Read-only operational check (run by hand / in a runbook, not a test suite): grep the
DB (and, given --log-file, a log file) for anything that shouldn't be there --
plaintext QRNG bytes, a plaintext master key, or a plaintext DRBG seed. Only
ciphertext + metadata should ever be persisted (build plan EPIC 10, S10.4).

Usage:
    python scripts/scan_persistence.py [--log-file PATH] [--database-url URL]

Exits 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qeaas import db

# Columns allowed on the sensitive tables. Any other bytea/text column with a
# name that looks sensitive is treated as an unexpected plaintext leak.
_ENTROPY_POOL_ALLOWED = {
    "id",
    "ciphertext",
    "nonce",
    "tag",
    "plaintext_len",
    "consumed_offset",
    "source_label",
    "uploaded_at",
}
_DRBG_ROOT_ALLOWED = {
    "id",
    "root_key",
    "nonce",
    "tag",
    "reseed_counter",
    "outputs_since_reseed",
    "rotated_at",
}
_LOG_TABLES_ALLOWED = {
    "issue_log": {
        "request_id",
        "principal",
        "endpoint",
        "size",
        "epoch_id",
        "ts",
    },
    "usage_log": {"id", "ts", "principal", "endpoint", "nbytes"},
}
_KNOWN_TABLES = {"entropy_pool", "drbg_root", "api_keys", *_LOG_TABLES_ALLOWED}
_SENSITIVE_NAME_RE = re.compile(
    r"plaintext|bits|raw|seed|data|value|output|secret", re.IGNORECASE
)
_QRNG_RUN_RE = re.compile(r"[01]{64,}")


@dataclass
class Violation:
    check: str
    detail: str


def check_schema_columns() -> list[Violation]:
    violations: list[Violation] = []
    columns = db.list_table_columns()

    entropy_pool = set(columns.get("entropy_pool", []))
    unexpected = entropy_pool - _ENTROPY_POOL_ALLOWED
    for name in unexpected:
        if _SENSITIVE_NAME_RE.search(name):
            violations.append(
                Violation("entropy_pool schema", f"unexpected sensitive column {name!r}")
            )

    drbg_root = set(columns.get("drbg_root", []))
    unexpected = drbg_root - _DRBG_ROOT_ALLOWED
    for name in unexpected:
        if _SENSITIVE_NAME_RE.search(name):
            violations.append(
                Violation("drbg_root schema", f"unexpected sensitive column {name!r}")
            )

    for table, allowed in _LOG_TABLES_ALLOWED.items():
        actual = set(columns.get(table, []))
        unexpected = actual - allowed
        for name in unexpected:
            if _SENSITIVE_NAME_RE.search(name):
                violations.append(
                    Violation(f"{table} schema", f"unexpected sensitive column {name!r}")
                )

    # Fail closed on any table this scan doesn't otherwise know about that has a
    # sensitive-looking column -- e.g. a stray `leak_test(bits text)` table.
    for table, cols in columns.items():
        if table in _KNOWN_TABLES:
            continue
        for name in cols:
            if _SENSITIVE_NAME_RE.search(name):
                violations.append(
                    Violation(
                        "unexpected table",
                        f"{table}.{name} looks sensitive and isn't an allow-listed table",
                    )
                )

    return violations


def _shannon_bytes_per_byte(data: bytes) -> float:
    if not data:
        return 0.0

    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    entropy = 0.0
    for c in counts:
        if c:
            p = c / n
            entropy -= p * math.log2(p)
    return entropy  # bits of entropy per byte, max 8.0


def check_pool_ciphertext() -> list[Violation]:
    violations: list[Violation] = []
    master_key = bytes.fromhex(os.environ["MASTER_KEY"])

    for ciphertext, nonce, tag in db.sample_entropy_pool():
        if master_key in ciphertext:
            violations.append(
                Violation("entropy_pool.ciphertext", "row contains the MASTER_KEY bytes")
            )
        if len(ciphertext) >= 16 and _shannon_bytes_per_byte(ciphertext) < 6.5:
            violations.append(
                Violation(
                    "entropy_pool.ciphertext",
                    "row is not high-entropy (looks like it may not be ciphertext)",
                )
            )
        if len(nonce) != 12 or len(tag) != 16:
            violations.append(
                Violation("entropy_pool.ciphertext", "nonce/tag are not GCM-shaped (12/16 bytes)")
            )

    return violations


def check_root_key() -> list[Violation]:
    """Q1 = encrypt (resolved): `drbg_root.root_key` must be GCM-ciphertext-shaped."""
    violations: list[Violation] = []

    for row_id, root_key, nonce, tag in db.sample_drbg_root():
        if nonce is None or tag is None:
            violations.append(
                Violation(
                    "drbg_root.root_key",
                    f"row id={row_id} has no nonce/tag -- looks like a plaintext seed",
                )
            )
            continue
        if len(nonce) != 12 or len(tag) != 16:
            violations.append(
                Violation(
                    "drbg_root.root_key",
                    f"row id={row_id} nonce/tag are not GCM-shaped (12/16 bytes)",
                )
            )
        if len(root_key) != 32:
            violations.append(
                Violation(
                    "drbg_root.root_key",
                    f"row id={row_id} ciphertext length {len(root_key)} != 32 "
                    "(expected same length as the plaintext seed under GCM)",
                )
            )

    return violations


def check_logs(log_file: str | None) -> list[Violation]:
    violations: list[Violation] = []
    if log_file is None:
        return violations

    master_key_hex = os.environ.get("MASTER_KEY", "")
    with open(log_file, "r", errors="ignore") as f:
        for lineno, line in enumerate(f, start=1):
            if master_key_hex and master_key_hex in line:
                violations.append(
                    Violation("logs", f"{log_file}:{lineno} contains the MASTER_KEY value")
                )
            if _QRNG_RUN_RE.search(line):
                violations.append(
                    Violation(
                        "logs", f"{log_file}:{lineno} contains a long 0/1 run (QRNG-looking)"
                    )
                )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-file", default=None, help="path to a log file to grep")
    parser.add_argument(
        "--database-url",
        default=None,
        help="overrides DATABASE_URL env var for this run",
    )
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    checks: list[tuple[str, list[Violation]]] = [
        ("entropy_pool: only ciphertext/nonce/tag/meta columns", check_schema_columns()),
        ("entropy_pool.ciphertext: high-entropy, no plaintext match", check_pool_ciphertext()),
        ("drbg_root.root_key: GCM ciphertext (nonce+tag present)", check_root_key()),
        ("logs: no MASTER_KEY / no 0/1 QRNG runs", check_logs(args.log_file)),
    ]

    all_violations: list[Violation] = []
    print(f"{'CHECK':<55} RESULT")
    for label, violations in checks:
        status = "PASS" if not violations else "FAIL"
        print(f"{label:<55} {status}")
        all_violations.extend(violations)

    if all_violations:
        print("\nViolations:")
        for v in all_violations:
            print(f"  [{v.check}] {v.detail}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
