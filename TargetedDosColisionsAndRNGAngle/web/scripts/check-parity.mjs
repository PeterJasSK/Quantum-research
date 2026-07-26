#!/usr/bin/env node
// Epic §3.3: JS hash logic must be identical to Python, asserted by CI/build.
// Runs the vendored ecmpLink over every hash_vectors.json row and compares to
// the expected link. Any mismatch exits non-zero and fails `npm run build`.
// Mirrors testbed/vectors/check_parity.py (Python source of truth <-> JS).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import ecmpHash from "../lib/ecmpHash.js";
const { ecmpLink } = ecmpHash;

const here = path.dirname(fileURLToPath(import.meta.url));
const vectorsPath = path.resolve(here, "..", "lib", "vectors.json");
const vectors = JSON.parse(readFileSync(vectorsPath, "utf8"));

let failures = 0;

for (const [index, vector] of vectors.entries()) {
  const { five_tuple: fiveTuple, salt_hex: saltHex, n_links: nLinks, link: expected } = vector;
  // eslint-disable-next-line no-await-in-loop
  const actual = await ecmpLink(fiveTuple, saltHex, nLinks);
  if (actual !== expected) {
    failures += 1;
    console.error(
      `vector[${index}] MISMATCH: expected link=${expected}, got link=${actual} (${JSON.stringify(vector)})`,
    );
  }
}

if (failures > 0) {
  console.error(`check-parity: ${failures}/${vectors.length} vectors failed -- JS/Python drift detected`);
  process.exit(1);
}

console.log(`check-parity: ${vectors.length}/${vectors.length} vectors match`);
