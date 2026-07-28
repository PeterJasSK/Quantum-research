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

Disconnect the network and drive the single page: switch the salt source
(`weak-prng` -> `csprng` -> `qrng`) and launch the attacker; everything must run purely in the
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

## Single unified page (`/`) -- QEaaS product demo

The old three-scene attack demo and the separate `/load-balancing` route were merged into one page
(`components/LoadBalanceController.tsx`). It is a live **k=6** fat-tree (`lib/fabric.ts`: 47 switches
+ 2 WAN gateways, 36 hosts) with animated packets flowing along the real ECMP routes, routed through
the vendored `ecmpLink` per stage (D-parity).

- **Main stage** -- load balancing (`LiveFatTree` canvas). Salt-source selector (`weak-prng` |
  `csprng` | `qrng`) re-derives per-switch salts and re-routes the same seeded traffic. `weak-prng`
  reuses a tiny shared salt pool fabric-wide (polarizes); `csprng`/`qrng` mint an independent salt per
  switch (spreads evenly). `FairnessReadout` computes Jain's index + polarization live
  (`lib/fairness.ts`).
- **Side panel** -- a live **precision collision attacker** (`AttackPanel`): one host, one deep
  core->agg target link, **no botnet**. It solves the ECMP hash offline against the salt it *believes*
  (== real only under a predictable salt), floods the victim, and a live "victim link congestion" gauge
  shows the attack landing under weak salt and dissolving under strong salt. Success verdict uses the
  exact `onTargetFraction` from `craftAttackFlows`, not a background-fooled live ratio.
- **QRNG** selection surfaces `ProvenancePanel` -- the QEaaS signed provenance receipt.

### Framing note (emphasis directive)

The page is framed as a **QEaaS viability demo**: the lead message is per-switch quantum entropy
delivered as a service with an attestable, signed provenance receipt per draw. The fact that a strong
CSPRNG is *sufficient* for the same attack/balancing outcome (QRNG null result) is real and stated
honestly, but kept as a **footnote**, never the focus. Preserve that emphasis when editing texts here.
Keep all three salt-source modules -- weak/csprng/qrng stay selectable.
