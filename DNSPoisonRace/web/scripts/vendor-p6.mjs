#!/usr/bin/env node
// P6 parity: copies the Python-adjacent source-of-truth race artefacts into
// web/lib/ verbatim. Fails if the testbed source changed but the web/ copy is
// stale, so a forgotten re-vendor never ships silently. Clone of the twin's
// vendor-p2.mjs.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const testbedVectors = path.resolve(webRoot, "..", "testbed", "vectors");

const PAIRS = [
  { src: path.join(testbedVectors, "race_core.js"), dst: path.join(webRoot, "lib", "raceCore.js") },
  { src: path.join(testbedVectors, "race_vectors.json"), dst: path.join(webRoot, "lib", "raceVectors.json") },
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
