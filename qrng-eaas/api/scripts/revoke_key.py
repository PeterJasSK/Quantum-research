#!/usr/bin/env python
"""CLI: revoke API key(s) locally, alongside `POST /admin/keys/revoke` (AC-8).

Usage:
    python -m scripts.revoke_key --owner <name>
    python -m scripts.revoke_key --key-hash <hash>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qeaas import db


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--owner")
    group.add_argument("--key-hash")
    args = parser.parse_args()

    if args.key_hash:
        revoked = db.revoke_api_key(args.key_hash)
        print(f"revoked {int(revoked)} key(s) for key_hash {args.key_hash!r}")
        return

    hashes = db.get_api_key_hashes_by_owner(args.owner)
    count = sum(1 for key_hash in hashes if db.revoke_api_key(key_hash))
    print(f"revoked {count} key(s) for owner {args.owner!r}")


if __name__ == "__main__":
    main()
