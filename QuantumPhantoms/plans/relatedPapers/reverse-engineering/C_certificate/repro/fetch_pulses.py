"""One-shot network fetch of public beacon pulses into repro/data/beacon_pulses.json (target #5).

The ONLY network-touching command of letter C (plan Q3). Everything else reads the committed cache.

    python -m C_certificate.repro.fetch_pulses [--n 12]

NIST Beacon 2.0 (chain 2): the last n consecutive pulses + their signing certificate(s), fully
verifiable offline by C_certificate.src.beacon. CURBy (random.colorado.edu, Kavuri C04): the latest
rounds are cached as a format sample only. CURBy blocks are IPLD dag-cbor objects addressed by CID,
and recomputing a CID needs a dag-cbor/multihash library that is not installed (no new installs),
so CURBy is dissected, not cryptographically verified; see dossiers/05-curby-beacon-chain.md.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import requests

from C_certificate.src.beacon import CACHE, verify_chain

NIST = "https://beacon.nist.gov/beacon/2.0"
CURBY = "https://random.colorado.edu/api/curbyq/round/latest"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=12, help="consecutive NIST pulses to cache")
    args = ap.parse_args()

    last = requests.get(f"{NIST}/pulse/last", timeout=30).json()["pulse"]
    chain, top = last["chainIndex"], last["pulseIndex"]
    pulses = [requests.get(f"{NIST}/chain/{chain}/pulse/{i}", timeout=30).json()["pulse"]
              for i in range(top - args.n + 1, top + 1)]
    certs = {cid: requests.get(f"{NIST}/certificate/{cid}", timeout=30).text
             for cid in sorted({p["certificateId"] for p in pulses})}
    curby = requests.get(CURBY, timeout=30).json()

    cache = {
        "source": "nist-beacon-2.0",
        "api_url": NIST,
        "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "chain_index": chain,
        "certificates": certs,
        "pulses": pulses,
        "curby_sample": {"api_url": CURBY, "rounds": curby,
                         "note": "format sample only; CID recomputation needs dag-cbor (not installed)"},
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1) + "\n")
    bad = [r["pulse_id"] for r in verify_chain(cache) if not r["ok"]]
    print(f"cached {len(pulses)} NIST pulses {pulses[0]['pulseIndex']}..{pulses[-1]['pulseIndex']} "
          f"+ {len(curby)} CURBy rounds → {CACHE}; failing: {bad or 'none'}")


if __name__ == "__main__":
    main()
