#!/usr/bin/env python3
"""Page GET /v1/seed on the deployed QRNG-EaaS API into a bits: sample file.

Standalone HTTP client script (no `qeaas` import) — mirrors the curl shape already
proven in `qrng-eaas/claude/prod_seed/smoke_test.sh`. Used to gather a raw-bytes
sample from the live, deployed service for the EPIC 7 seed-quality report.

Usage:
    python3 pull_seed_sample.py --api-base URL --api-key KEY \
        --total-bytes 1572864 --chunk-size 4096 --out samples/service_sample.txt
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _bytes_to_bits_file(data: bytes, out: Path) -> None:
    """Write `data` to `out` as a `bits:`-prefixed, MSB-first 0/1 string."""
    bit_string = "".join(format(byte, "08b") for byte in data)
    out.write_text(f"bits:{bit_string}")


def _fetch_chunk(api_base: str, api_key: str, chunk_size: int) -> bytes:
    """Fetch one chunk from /v1/seed, retrying once on a transient 429."""
    query = urllib.parse.urlencode({"bytes": chunk_size, "format": "hex"})
    url = f"{api_base}/v1/seed?{query}"
    request = urllib.request.Request(url, headers={"X-API-Key": api_key})

    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return bytes.fromhex(json.load(response)["data"])
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            error = json.loads(body).get("error", "unknown") if body else "unknown"

            if exc.code == 503:
                print(f"ABORT: 503 {error} — quantum pool is degraded, not retrying.", file=sys.stderr)
                sys.exit(1)

            if exc.code == 429:
                if error == "quota_exceeded" or attempt == 1:
                    print(f"ABORT: 429 {error} — {body}", file=sys.stderr)
                    sys.exit(1)
                retry_after = float(exc.headers.get("Retry-After", "1"))
                print(f"429 {error} — backing off {retry_after}s and retrying once.", file=sys.stderr)
                time.sleep(retry_after)
                continue

            print(f"ABORT: unexpected status {exc.code} — {body}", file=sys.stderr)
            sys.exit(1)

    print("ABORT: retry exhausted.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", required=True, help="Deployed API base URL, e.g. https://quantum-research-api.vercel.app")
    parser.add_argument("--api-key", required=True, help="Keyed API key (X-API-Key)")
    parser.add_argument("--total-bytes", type=int, required=True, help="Total raw bytes to accumulate")
    parser.add_argument("--chunk-size", type=int, default=4096, help="Bytes per /v1/seed call (32..4096)")
    parser.add_argument("--out", required=True, help="Output path for the bits: sample file")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    collected = bytearray()
    calls = 0
    while len(collected) < args.total_bytes:
        collected.extend(_fetch_chunk(api_base, args.api_key, args.chunk_size))
        calls += 1
        if calls % 50 == 0:
            print(f"...{len(collected)}/{args.total_bytes} bytes ({calls} calls)")

    data = bytes(collected[: args.total_bytes])
    _bytes_to_bits_file(data, out_path)
    print(f"Wrote {len(data)} bytes ({len(data) * 8} bits) to {out_path} in {calls} calls.")


if __name__ == "__main__":
    main()
