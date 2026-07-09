#!/usr/bin/env python
"""CLI: mint a dev API key (Q4). Prints the plaintext key once; stores only its hash.

Usage:
    python -m scripts.mint_key --owner <name> [--tier default] [--quota <bytes>]

The HTTP `POST /admin/keys` mint route lands in EPIC 3; this local CLI seeds
usable dev keys until then.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qeaas import db
from qeaas.auth import hash_api_key


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--tier", default="default")
    parser.add_argument("--quota", type=int, default=None)
    args = parser.parse_args()

    key = secrets.token_urlsafe(32)
    db.insert_api_key(hash_api_key(key), args.owner, args.tier, args.quota)
    print(f"api key for {args.owner!r} (tier={args.tier}): {key}")
    print("store this now -- it will not be shown again.")


if __name__ == "__main__":
    main()
