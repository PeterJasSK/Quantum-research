// AC-T0.9 (Node side) — computes the JS mirror's values for the parity vector and
// writes them to stdout as JSON for parity_check.py to compare. Standalone:
//   node tools/parity_check.mjs   (reads tools/parity_vector.json)
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  searchSpaceSize,
  groverIterations,
  expectedQueries,
} from "../web/lib/grover_count.js";

const here = dirname(fileURLToPath(import.meta.url));
const vector = JSON.parse(readFileSync(join(here, "parity_vector.json"), "utf-8"));

const out = vector.map(({ n, kind, marked }) => ({
  n,
  kind,
  marked,
  // integers dumped as strings so BigInt values compare exactly against Python int
  search_space_size: searchSpaceSize(n, kind).toString(),
  grover_iterations: String(groverIterations(searchSpaceSize(n, kind), marked)),
  expected_queries_search: expectedQueries(n, kind, marked, "search"),
  expected_queries_min: expectedQueries(n, kind, marked, "min"),
}));

process.stdout.write(JSON.stringify(out));
