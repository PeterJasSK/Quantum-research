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
