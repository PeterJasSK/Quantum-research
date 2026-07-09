#!/usr/bin/env python
"""CLI: seed a local dev entropy pool from a plain 0/1 .txt file (AC-14).

Usage:
    python scripts/ingest_bits.py path/to/bits.txt [source_label]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qeaas.pool import ingest_bits_file


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    path = sys.argv[1]
    source_label = sys.argv[2] if len(sys.argv) > 2 else Path(path).name
    ingest_bits_file(path, source_label)
    print(f"ingested {path} as {source_label!r}")


if __name__ == "__main__":
    main()
