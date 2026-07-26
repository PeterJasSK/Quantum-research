#!/usr/bin/env node
// D-parity: copies P2's shared JS/vector artefacts into web/lib/ verbatim.
// Fails if testbed source changed but the web/ copy is stale, so a forgotten
// re-vendor never ships silently.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const testbedVectors = path.resolve(webRoot, "..", "testbed", "vectors");

const PAIRS = [
  { src: path.join(testbedVectors, "ecmp_hash.js"), dst: path.join(webRoot, "lib", "ecmpHash.js") },
  { src: path.join(testbedVectors, "hash_vectors.json"), dst: path.join(webRoot, "lib", "vectors.json") },
];

const forceWrite = process.argv.includes("--write");
let stale = false;

for (const { src, dst } of PAIRS) {
  const srcContent = readFileSync(src, "utf8");
  const dstContent = existsSync(dst) ? readFileSync(dst, "utf8") : null;

  if (dstContent === srcContent) {
    console.log(`up to date: ${path.relative(webRoot, dst)}`);
    continue;
  }

  if (forceWrite) {
    writeFileSync(dst, srcContent, "utf8");
    console.log(`vendored: ${path.relative(webRoot, dst)}`);
  } else {
    stale = true;
    console.error(`stale (run with --write to re-vendor): ${path.relative(webRoot, dst)}`);
  }
}

if (stale) {
  process.exit(1);
}
