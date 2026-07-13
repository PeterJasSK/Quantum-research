#!/usr/bin/env python3
"""Draw a same-size OS-CSPRNG baseline sample into a bits: file.

Companion to `pull_seed_sample.py` for the EPIC 7 seed-quality report: uses
`os.urandom` (Python's interface to `/dev/urandom` on Linux) as the comparison
baseline against the deployed service's `/v1/seed` output.

Usage:
    python3 pull_urandom_sample.py --total-bytes 1572864 --out samples/urandom_sample.txt
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pull_seed_sample import _bytes_to_bits_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--total-bytes", type=int, required=True, help="Total bytes to draw from os.urandom")
    parser.add_argument("--out", required=True, help="Output path for the bits: sample file")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = os.urandom(args.total_bytes)
    _bytes_to_bits_file(data, out_path)
    print(f"Wrote {len(data)} bytes ({len(data) * 8} bits) to {out_path}.")


if __name__ == "__main__":
    main()
