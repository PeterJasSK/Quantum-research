#!/usr/bin/env python3
"""Standalone JS<->Python hash parity checker (AC-5): load `hash_vectors.json`,
recompute each `link` via Node running `ecmp_hash.js`, exit non-zero on any
mismatch and print the offending vector. The "asserts fail on drift" AC,
framed as a manual checker (no test suite -- project directive)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

VECTORS_PATH = Path(__file__).with_name("hash_vectors.json")
ECMP_HASH_JS_PATH = Path(__file__).with_name("ecmp_hash.js")

_NODE_DRIVER = """
const { ecmpLink } = require(process.argv[1]);
let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", async () => {
  const vectors = JSON.parse(input);
  const results = [];
  for (const v of vectors) {
    results.push(await ecmpLink(v.five_tuple, v.salt_hex, v.n_links));
  }
  process.stdout.write(JSON.stringify(results));
});
"""


def recompute_via_node(vectors: list[dict]) -> list[int]:
    result = subprocess.run(
        ["node", "-e", _NODE_DRIVER, str(ECMP_HASH_JS_PATH)],
        input=json.dumps(vectors),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    vectors = json.loads(VECTORS_PATH.read_text())
    js_links = recompute_via_node(vectors)

    mismatches = 0
    for i, (vector, js_link) in enumerate(zip(vectors, js_links)):
        if vector["link"] != js_link:
            mismatches += 1
            print(
                f"MISMATCH at vector {i}: python link={vector['link']} js link={js_link} "
                f"vector={vector}",
                file=sys.stderr,
            )

    if mismatches:
        print(f"FAIL: {mismatches}/{len(vectors)} vectors disagree", file=sys.stderr)
        return 1

    print(f"PASS: {len(vectors)}/{len(vectors)} vectors agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
