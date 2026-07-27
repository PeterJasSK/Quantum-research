# ECMP Collision DoS -- web demo (Plan 6)

Next.js static-export app that makes the five-experiment argument visible in a browser. See
`../plans/plan-6-web-demo.md` for the full plan/decisions.

## Run

```bash
npm install
npm run dev        # http://localhost:3000
```

## Build (Tier A static export)

```bash
npm run build       # runs check:parity, then `next build` -> web/out/
```

`next build` with `output: 'export'` emits the static bundle to `out/`. There is no `next
export` step on Next 16 -- do not add one.

To serve the exported bundle offline:

```bash
npx serve out
```

Disconnect the network and step through Scene 1 -> 2 -> 3; all three must run purely in the
browser (AC-1..4).

## Parity (build-time assert, not a test)

```bash
npm run check:parity
```

Runs the vendored `lib/ecmpHash.js` over every row of `lib/vectors.json` and fails non-zero on
any mismatch against the Python source of truth. Wired into `npm run build`.

## Re-vendoring P2's shared artefacts

```bash
npm run vendor:p2 -- --write
```

Copies `../testbed/vectors/ecmp_hash.js` and `../testbed/vectors/hash_vectors.json` into
`lib/` verbatim (D-parity). Run this whenever P2 changes those files; `npm run vendor:p2`
without `--write` just checks staleness and exits non-zero if the copies are out of date.

## GitHub Pages base path

Set `NEXT_PUBLIC_BASE_PATH=/<repo-name>` before building if deploying under a project path
(e.g. GitHub Pages `https://user.github.io/repo/`).

## Tier B (stretch, not implemented)

`lib/ws.ts`, `lib/replay.ts`, `lib/datasource.ts`'s `createLiveDataSource`/`createReplayDataSource`
are typed scaffolding only. Wiring them up needs:
- a WebSocket push layer on the Ryu controller reading `_port_stats_poll_loop`
  (`../testbed/controller/ecmp_controller.py`) -- not built yet (OQ-2, owned by this plan's Tier B).
- P5's recorded sweep subset under `public/replay/` -- P5 is Draft, not landed yet.

`public/replay/qrng-provenance.json` is a **structurally-accurate sample**, not a real Q-EaaS
receipt -- replace it with P5's recorded provenance run before using the demo publicly.

## `/load-balancing` -- entropy quality vs ECMP hash polarization (Plan 8)

A second, attack-free route: a k=4 fat-tree (20 switches, 16 hosts, `lib/fabric.ts`) under
uniform background traffic, no attacker, no defences. Salt-source selector (`weak-prng` |
`csprng` | `qrng`) re-derives per-switch salts and re-routes the same flow set through the
vendored `ecmpLink` per stage (D8-parity) -- `weak-prng` reuses one shared salt fabric-wide
(polarizes); `csprng`/`qrng` mint an independent salt per switch (spreads evenly). See
`../plans/plan-8-load-balancing-entropy.md`.

`FatTreeView` renders the full fabric as a tall vertical SVG (tiers stacked core -> aggregation
-> edge -> hosts) -- deliberately not cropped or simplified (OQ8-3). `FairnessReadout` computes
Jain's index + polarization index (`lib/fairness.ts`, mirrors `testbed/metrics/fairness.py`) live
from the real routed bucket counts. The QRNG selection shows the same `ProvenancePanel` as Scene
3, labelled provenance-only (epic s3.2 null result) -- never "balances better than CSPRNG."

Cross-linked from the attack demo via `components/Nav.tsx` (basePath-aware via `next/link`).
