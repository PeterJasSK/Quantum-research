#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const core = require(path.resolve(here, "..", "lib", "raceCore.js"));
const vectors = JSON.parse(readFileSync(path.resolve(here, "..", "lib", "raceVectors.json"), "utf8"));
let failures = 0;
for (const [i, v] of vectors.entries()) {
  let r;
  if (v.mode === "run_race") {
    r = core.runRace(v.seed, [v.txid, v.port], v.forged_guess, v.rtt, v.send_schedule);
  } else {
    r = core.buildFloodVector(v);
    if (r.send_schedule.length !== v.send_schedule.length || !r.send_schedule.every((x, j) => x === v.send_schedule[j])) {
      failures++; console.error(`vector[${i}] send_schedule MISMATCH`); continue;
    }
  }
  if (r.outcome !== v.outcome || r.forged_packets !== v.forged_packets || r.t_outcome !== v.t_outcome) {
    failures++; console.error(`vector[${i}] MISMATCH: expected ${v.outcome}/${v.forged_packets}/${v.t_outcome}, got ${r.outcome}/${r.forged_packets}/${r.t_outcome}`);
  }
}
if (failures > 0) { console.error(`check-parity: ${failures}/${vectors.length} failed -- JS/Python drift`); process.exit(1); }
console.log(`check-parity: ${vectors.length}/${vectors.length} vectors match`);
