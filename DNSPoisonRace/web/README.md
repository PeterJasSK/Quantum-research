# DNS Poison Race — web demo (Plan 6)

Next.js 16 static-export app that makes the DNS cache-poisoning entropy race visible in the
browser: the forged-answer flood vs the authoritative reply, the self-drawing entropy cliff, the
SAD-DNS side-channel reveal, a guess-space heatmap, and a signed QRNG provenance receipt. See
`../plans/plan-6-web-demo.md` for the full plan and decisions.

## Run

```bash
npm install
npm run dev        # http://localhost:3000
```

## Build (static export, parity-gated)

```bash
npm run build      # runs check:parity, then `next build` -> web/out/
```

`next build` with `output: 'export'` emits the static bundle to `out/`. There is no `next export`
step on Next 16 — do not add one. Serve it offline with `npx serve out`.

## Parity gate (build-time assert, not a test) — AC-6.6

```bash
npm run check:parity
```

Imports the vendored `lib/raceCore.js`, recomputes every row of `lib/raceVectors.json`, and fails
non-zero on any mismatch against the Python source of truth. Wired into `npm run build`, so the
static export cannot ship on JS↔Python drift. `run_race` rows are recomputed via `runRace(...)`;
`flood` rows via `buildFloodVector(...)` (asserting `send_schedule` element-wise plus
`outcome`/`forged_packets`/`t_outcome`).

## Re-vendoring the race mirror

```bash
npm run vendor:p6 -- --write
```

Copies `../testbed/vectors/race_core.js` -> `lib/raceCore.js` and
`../testbed/vectors/race_vectors.json` -> `lib/raceVectors.json` verbatim. Run whenever the testbed
changes those files. `npm run vendor:p6` without `--write` just checks staleness and exits non-zero
if the copies are out of date. **Do not hand-edit the vendored copies in `lib/`** — edit the
testbed source and re-vendor.

## Environment

- `NEXT_PUBLIC_WEB_URL` — canonical site host for metadata/robots/sitemap/manifest. Defaults to
  `http://localhost:3000` (the production domain is not chosen yet — plan OQ-6.2, deferred).
- `NEXT_PUBLIC_API_URL` — QEaaS API host shown in the provenance callout (default
  `https://api.qeaas.eu`).
- `NEXT_PUBLIC_BASE_PATH` — set to `/<repo>` when deploying under a GitHub-Pages subpath. Applied to
  `basePath`/`assetPrefix` **and** inline to every replay `fetch` (assetPrefix does not rewrite
  `fetch`).

## The replay JSON contract (frozen by P5, consumed here)

`public/replay/*.json` are produced by P5 and consumed read-only:

- `cliff.json` — `{ sources: { fixed|prng|csprng|qrng: [{ effective_bits, poison_rate }] }, send_rate_pps }`.
- `collapse.json` — `{ kind: "csprng", series: [{ k, poison_rate }] }`.
- `race_fixed|prng|csprng.json` — per-source scenario descriptor
  `{ kind, seed, txid_bits, port_bits, k, send_rate_pps, rtt, retransmit, parallel_queries, outcome, t_outcome, forged_packets }`.
  `race_qrng.json` is not exported (QRNG defends identically to CSPRNG at k=0 — the null result);
  `lib/replay.ts` falls back to the CSPRNG descriptor relabelled `qrng`.
- `qrng-provenance.json` — `{ kind: "qrng", detail: { request_id, entropy_epoch, timestamp, receipt, endpoint } }`.
  May be the P5 sample placeholder; the provenance panel renders it honestly as clearly-not-real.

## Notes

- The interactive canvases animate a *display* trace derived from a race descriptor + slider state
  via `lib/scenario.ts` → `raceCore.buildFloodVector(..., true)`. Correctness of the race logic is
  proven separately by the parity gate over the golden vectors — the display heuristics (source
  entropy penalty, guess-space binning) never touch that gate.
- No animation library: every canvas is hand-rolled `requestAnimationFrame`, mirroring the twin's
  `LiveFatTree`.
- The `QEAAS_API_KEY` never reaches the browser — the bundle only reads the pre-recorded
  `qrng-provenance.json`.
