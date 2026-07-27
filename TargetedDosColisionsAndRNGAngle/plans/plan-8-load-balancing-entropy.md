# Plan 8 — Load-balancing angle: entropy quality vs ECMP hash polarization (multi-tier fabric)

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source:** new (post-EPIC, pre-paper) · **Priority:** `[SHOULD]`
**Status:** Complete (`/implement-feature` pass 2026-07-27) · **Depends on:** P2 (shared hash + salt engine, landed `6adb4d2`), P6 (web app, Tier A landed `9bb47b2`). Independent of P7 — lands **before** the paper so P7 can cite it.

> Pick up with `/implement-feature plans/plan-8-load-balancing-entropy.md` after approval. Read epic §3.2 (QRNG null
> result + practical angle), §6 + §8 Q1 (controller-managed-salt fabric-wide blast radius), §3.4 (scale caveat),
> and this plan's **§Honest mechanism** + **§Codebase integration** FIRST — the whole plan hinges on *where* entropy
> quality does and does not affect load balancing, and the controller is hard-wired single-leaf today (must be
> generalized behind a flag). **No automated tests** (project directive); correctness is an offline check + the
> existing build-time JS↔Python parity assert, same shape as P3/P4/P6.

## Epic alignment (why this fits, not scope-creep)
- **§3.2 (QRNG null result):** this plan is the *load-balancing* instance of the same honest line — QRNG = CSPRNG
  for balancing; provenance is the only extra. Never "balances better."
- **§6 + §8 Q1 (RESOLVED qualitative, topology headroom left):** Q1 deferred *measuring* the controller-managed-salt
  fabric-wide blast radius (option (b): a bigger multi-switch topology) to a cheap bolt-on. **This plan builds that
  topology** — the k=4 fat-tree makes the "one weak salt weakens the whole fabric at once" property *measurable*
  (as polarization), turning Q1's qualitative argument into a figure without an attacker. Frame it as the promised
  low-cost bolt-on, not a new claim.
- **§3.4 (scale-invariant ratios):** the polarization index is a ratio (`max/mean`), scale-free by construction.
- **§3.5 (one hash core):** reuses `hash_core.ecmp_link` (Python) and P2's vendored `ecmpHash.js` (web) unchanged.
- **§10 (MTD / unpredictability-as-primitive umbrella):** per-switch seed independence is the load-balancing face of
  "randomness quality saturates at CSPRNG; QRNG adds provenance" — a citable tie-in for P7's practical-deployment note.

## Goal
A **second, attack-free** argument for the demo and paper: **entropy quality affects load-balancing quality in a
multi-tier fabric — bad PRNG salt causes systematic congestion (ECMP *hash polarization*) even with zero attacker
and perfectly uniform traffic; CSPRNG/QRNG salt spreads traffic evenly.** Deliver it as:
1. a new **web page** (`/load-balancing`) that shows this on a **3-tier fat-tree (k=4)**, reusing P2's vendored
   `ecmpLink` so the hash stays parity-locked; and
2. a **real Python multi-tier topology + offline polarization measurement** in `testbed/` that produces the numbers
   the page and P7 cite.

This is the "practical QRNG/CSPRNG deployment" angle the epic keeps separate from the attack outcome (§3.2), made
concrete: the payoff of good entropy is **decorrelated per-switch hashing**, not "stops the attack better."

## Honest mechanism — read before building *(frozen here)*
This is the load-bearing correctness claim; get it wrong and the page lies.

- **On a single switch, salt entropy does NOT change spread quality.** `link = SHA-256(5tuple ‖ salt) mod N`
  diffuses uniformly across links for *any* fixed salt, even a terrible one — SHA-256 is a good mixer regardless of
  input entropy. A page that shows "bad salt → lopsided links on one switch" would be **false**. Do not build that.
- **The effect is a multi-switch, multi-stage phenomenon: ECMP hash polarization.** In a fat-tree, a packet is
  hashed independently at each tier (edge → aggregation → core → …). Polarization is the documented failure
  (Cisco/Juniper/Arista ECMP docs; RFC 2992 discussion) where **correlated hash decisions across stages** funnel
  traffic onto a subset of end-to-end paths, starving the rest. The standard vendor fix is an **independent,
  well-mixed seed per switch/stage**.
- **Where entropy quality bites:** the weak PRNG (`config.PRNG_SEED` default `0`, deterministic sequential draws)
  means an operator who deploys one controller image fabric-wide gets **identical or low-entropy-collision salt
  sequences across many switches** → stages hash *the same way* → polarization. CSPRNG (`secrets.token_bytes`) and
  QRNG each yield **independent 256-bit per-switch salts** → negligible salt collision → decorrelated stages → even
  end-to-end spread. So the honest chain is: *weak entropy → per-switch seed reuse/correlation → stage correlation →
  polarization → congestion*, with **no attacker in the loop**.
- **QRNG = CSPRNG for load balancing (null result holds, §3.2).** Both give independent high-entropy per-switch
  salts; both fully de-polarize. QRNG's *only* extra is attestable entropy **provenance** (signed receipt, entropy
  epoch) — label it exactly that on the page, never "balances better than CSPRNG." The three-way comparison is
  **bad-PRNG (polarizes) vs {CSPRNG, QRNG} (both even)**, matching the user's framing.

## Decision D8-parity — reuse P2's vendored `ecmpLink`, hash per stage *(frozen here)*
The page simulates a multi-hop path by calling the **same vendored async `ecmpLink(fiveTuple, saltHex, nLinks)`**
(P6's `web/lib/ecmpHash.js`, which *is* P2's `testbed/vectors/ecmp_hash.js`) **once per switch on the path**, each
call using **that switch's own salt** and its own fan-out count. No new hash. The Python side calls
`testbed/hash_core.ecmp_link` the same way. This keeps Python ⇄ vectors ⇄ vendored JS parity intact (epic §3.3) and
means "polarization" emerges from real hashing, not fabricated numbers.

## Decision D8-seed — per-switch salt derivation is the entropy knob *(frozen here)*
The exact hashing mechanism (verified): a flow's egress at each switch is `ecmp_link(five_tuple, salt, k) =
int.from_bytes(sha256(five_tuple.to_bytes() + salt)[:8]) % k`. Two facts that pin the honest model:
1. **One switch always spreads uniformly** — for *any* salt, `sha256(·)` is a good mixer, so a single stage's
   `mod k` is uniform regardless of salt entropy. Entropy quality is invisible at one stage.
2. **Polarization is stage *correlation*.** If two switches on a path share the **same salt**, then for a given
   flow both compute the *identical* digest → identical `mod k` → the stage-2 choice is perfectly correlated with
   stage-1. Flows that collided at stage 1 keep colliding downstream → traffic funnels onto a diagonal subset of
   end-to-end paths (classic ECMP polarization). **Independent per-switch salts decorrelate the stages** → flows
   re-spread → all paths used. This is the whole mechanism; it needs ≥2 stages, which is why the topology must be
   multi-tier.

The salt **source** is the independent variable, and per-switch derivation is where it bites:
- **prng (weak) — fails every time (OQ8-2):** models the realistic same-image-same-seed deployment — **every switch
  derives its salt from the same fixed `PRNG_SEED`, yielding one identical salt fabric-wide.** (Note: this is *not*
  the P2 prng source's default behaviour — its module-global `random.Random(PRNG_SEED)` advances per draw, so
  sequential draws differ. Fabric mode deliberately re-seeds a fresh `random.Random(PRNG_SEED)` **per switch** so
  all switches collide on the same salt — the honest model of a fabric-wide weak/shared seed.) Salt identical across
  all stages → total, deterministic polarization on every run; no seed makes it pass.
- **csprng / qrng:** per-switch salt is an **independent** draw (`secrets.token_bytes(SALT_SIZE)` / one QRNG fetch
  per switch). Cross-fabric salt-collision probability is negligible → stages decorrelate → even spread. QRNG ≡
  CSPRNG here (null result).
The web mirror uses P6's `web/lib/salt.ts`: prng → one shared `weakPrngSaltHex(PRNG_SEED)` reused for **every**
switch (identical → polarized); csprng/qrng → `csprngSaltHex()` called **once per switch** (independent → even).
Tier A only needs to *demonstrate* the correlation, not reproduce Python bit-for-bit (P6's `salt.ts` stance).

## Codebase integration surfaces (verified 2026-07-27)
What plan-8 touches and the exact assumptions it must respect. All `file:line` from a full read of current `main`.

**Hash (reuse verbatim, do not modify — P3/P6 depend on it):**
- `testbed/hash_core.py:14` — `ecmp_link(five_tuple: FiveTuple, salt: bytes, n_links: int) -> int`. Salt is
  **bytes**. Web mirror = P6 vendored `web/lib/ecmpHash.js` `ecmpLink(fiveTuple, saltHex, nLinks): Promise<number>`
  (salt as **hex**, async).

**Salt (reuse):** `testbed/salt/sources.py:51` — `salt_source(kind, *, size=SALT_SIZE) -> SaltResult`; `SaltResult.salt`
is **bytes**. prng (`sources.py:62`) is a *module-global stateful* `random.Random(PRNG_SEED)` that advances per
draw — see D8-seed for why fabric mode re-seeds a fresh RNG per switch instead of calling this sequentially.

**Controller — hard-wired single-leaf; this is the big generalization (all gated behind new `FABRIC_MODE`, default off):**
`testbed/controller/ecmp_controller.py`. Today it hashes **only at `LEAF_DPID`** and the docstring says so. The
single-leaf assumptions plan-8 must generalize, each guarded so the OFF path stays byte-for-byte identical:
- `switch_features_handler` (`:125`): `if datapath.id != LEAF_DPID:` installs a `NORMAL` flow and returns; leaf
  caches `self._leaf_datapath` and installs table-miss→CONTROLLER. **Fabric mode:** every fat-tree switch is a
  hasher — track `self._fabric_datapaths: dict[int, Datapath]` and install table-miss→CONTROLLER on all of them; no
  switch gets the blanket `NORMAL` shortcut.
- `packet_in_handler` (`:151`): early `return` if `datapath.id != LEAF_DPID`; computes
  `ecmp_link(five_tuple, self.active_salt, N_LINKS)` (`:214`), `out_port = EGRESS_PORTS[link_index]`, tracks in the
  single `self._ecmp_flows: set` (`:216`). **Fabric mode:** handle packet-in from *any* fabric dpid; pick the salt
  from `self._fabric_salts[dpid]` and the fan-out from the per-switch **upward egress ports** for that dpid; install
  the pinning flow; track per-dpid in `self._fabric_flows: dict[int, set]`. Downward (toward destination host) is
  deterministic by destination subnet, **not** hashed — only *upward* fan-out hashes (standard fat-tree).
- Salt state: `self.active_salt: bytes` (`:81`) + `rotate_salt()` (`:241`) iterate the single flow set. **Fabric
  mode:** `self._fabric_salts: dict[int, bytes]` populated at switch-features per dpid (D8-seed derivation); rotation
  is out of scope here (no attacker → no rotation needed for this page; keep rotation single-leaf-only).
- Globals `LEAF_DPID`, `EGRESS_PORTS`, `N_LINKS`, `REMOTE_IPS`, `LOCAL_IP_TO_PORT` (config) all assume one hashing
  switch + one link bundle. Fabric mode needs a **per-dpid egress map** and a routing table, supplied by the shared
  fabric model (below) — do not overload the single-leaf globals.

**Metrics — P4 schema is leaf-shaped, do NOT force the fabric through it:**
- `testbed/metrics/csv_writer.py:13` per-poll header has exactly `link{i}_util for i in range(n_links)` +
  `max_link_util,jains_index,victim_mbps,target_link,target_tx_packets,tracked_flows`, and `MetricsCollector`
  (`collector.py:39`) counts only `EGRESS_PORTS` with a single `target_link`. A fat-tree has many more links and no
  single target link. **Plan-8 emits its own compact fabric CSV** (per salt source: per-link load vector, Jain's
  index, polarization index) — it reuses `fairness.jains_index` and the **new** `fairness.polarization_index`, but
  not the leaf per-poll schema. (The plan's earlier "same CSV shape as P4" intent is corrected here.)
- `testbed/metrics/fairness.py` — `jains_index(values)` exists and is already asserted in `metrics_check.py`. Add
  `polarization_index(values) -> float` beside it.

**Topology:** `testbed/topology/ecmp_topo.py` — `ECMPTopo(Topo)`; switches `addSwitch("s1"/"s2",
protocols="OpenFlow15")`, dpid derived from name by Mininet; **no `TCLink`/`bw=`** (LINK_CAPACITY_MBPS is only
controller math). `run_topo.py` wires `RemoteController` + `OVSSwitch`. New fat-tree mirrors this style.

**Web (`web/`, Next 16.2.10 static export):**
- New route = **create `web/app/load-balancing/page.tsx`** (static export auto-emits `out/load-balancing/index.html`).
- `web/app/layout.tsx` has **no nav bar** — add a minimal cross-link (demo ↔ load-balancing) in `layout.tsx` chrome
  or a small `Nav` component.
- Style idioms (from `SceneController.tsx`): outer `mx-auto flex max-w-4xl flex-col gap-6 p-6`; cards use the
  `.panel` class + `p-4`; headings `text-(--color-heading)`; colours via CSS vars (`--color-danger/success/...`).
- `web/components/TopologyView.tsx` — inline `<svg viewBox=...>`, fixed tier coords, link colour = danger if
  `util >= SATURATION_UTILISATION` else success. `FatTreeView` mirrors this with stacked tiers (vertical, OQ8-3).
- `web/lib/datasource.ts` — `SceneSample { linkUtil, victimMbps, jainsIndex, rateLimiterActive, throttleActive }`.
  The load-balancing page has no victim/defences, so define a small local type (e.g. `FabricSample { perLinkUtil,
  jainsIndex, polarizationIndex }`) rather than abusing `SceneSample`.
- `web/components/ProvenancePanel.tsx` — props `{ visible: boolean }`, reusable as-is for the QRNG panel.
- `web/lib/qeaas.ts` — `loadRecordedProvenance()` fetches `${NEXT_PUBLIC_BASE_PATH ?? ""}/replay/qrng-provenance.json`;
  reuse the **basePath-aware** fetch/link pattern for any new asset.
- `web/next.config.ts` — `basePath`/`assetPrefix` = `NEXT_PUBLIC_BASE_PATH`; `package.json` `build` runs
  `check:parity` first (`scripts/check-parity.mjs`, 28 vectors) — a hash/route change must keep it green.

## Deliverable A — Python multi-tier fabric + polarization measurement (`testbed/`)
A real 3-tier fat-tree (k=4) and a measurement that quantifies spread quality per salt source. **No attacker.** The
**pure-data fabric model + offline check is the primary correctness gate** (dependency-light, no Mininet/root); the
live Mininet fat-tree is the "real topology" deliverable and reuses that model.

- **Shared fabric model — `testbed/topology/fabric.py` (pure data, no Mininet):** the source of truth for both the
  offline check and the (heavier) live controller. Provides:
  - `build_fattree(k: int) -> Fabric` — canonical Al-Fares k=4: **4 core, 4 pods × (2 aggregation + 2 edge), 2 hosts
    per edge → 16 hosts, 20 switches**. Exposes, per switch: its tier, its **upward egress ports** (the hashed
    fan-out) and its **downward/destination routing** (deterministic by pod/subnet, not hashed).
  - `fabric_salts(kind: str, fabric: Fabric) -> dict[switch_id, bytes]` — per-switch salt per D8-seed: prng → one
    identical salt for every switch (fresh `random.Random(PRNG_SEED)` per switch); csprng/qrng → independent
    `salt_source(kind).salt` per switch.
  - `route(fabric, salts, five_tuple) -> list[link_id]` — walks the flow edge→agg→core→…→edge→host, calling
    `hash_core.ecmp_link(five_tuple, salts[switch], fanout_k)` at each **upward** hop, deterministic downward;
    returns the ordered links traversed. Uses the **real** `ecmp_link` (no copy).
  - `link_load(fabric, salts, flows) -> list[int]` — per-link flow counts over a uniform flow set.
- **Fat-tree Mininet topology — `testbed/topology/fattree_topo.py`** (`FatTreeTopo(Topo)`, mirrors `ecmp_topo.py`
  style: `addSwitch(name, protocols="OpenFlow15")`, deterministic switch names so dpids are stable and match
  `fabric.py`'s switch ids). Add a `FATTREE_K` config knob (default 4). Leaf-spine / other k is out of scope.
- **Controller `FABRIC_MODE` path** (`ecmp_controller.py`, gated, default off — see §Codebase integration for the
  exact single-leaf assumptions to generalize): every fabric switch hashes its **upward** fan-out under
  `self._fabric_salts[dpid]` (populated at `switch_features_handler` from `fabric.fabric_salts(SALT_KIND, ...)`),
  installs the pinning flow, tracks per-dpid flows. OFF path byte-for-byte unchanged (same discipline as
  `DEFENCES_ENABLED`). Rotation stays single-leaf-only (no attacker in this scenario).
- **Measurement (no attacker):** uniform background flows (many distinct 5-tuples across all host pairs) routed
  through the fabric; record **per-link load** across all fabric links. Compute `fairness.jains_index` (existing)
  and the **new `fairness.polarization_index(values) = max(values)/mean(values)`** (OQ8-1). **Emit a compact
  fabric CSV tagged by `salt_source`** — *not* P4's leaf-shaped per-poll schema (see §Codebase integration for
  why): columns `salt_source, n_switches, n_links, jains_index, polarization_index, max_link_load, mean_link_load`.
- **Offline check (no Mininet/root) — the correctness gate: `testbed/topology/polarization_check.py`** (mirrors
  `collision_check.py`/`metrics_check.py` structure — `sys.path` insert, `_check_*()` funcs, non-zero exit).
  Asserts the honest mechanism: (1) **prng polarizes on every run** — `jains_index` well below csprng/qrng, high
  `polarization_index` (deterministic, no passing seed, OQ8-2); (2) csprng/qrng → `jains_index ≈ 1.0`, low
  polarization; (3) **single-switch control** — routing one flow set through a *single* switch, prng and csprng give
  statistically equal spread (the false-claim guard from D8-seed fact 1). Non-zero exit on any failure. **Build this
  check first** — it is what stops the page lying.

## Deliverable B — web page `/load-balancing` (Next.js, Tier A, static export)
A new **route** in the P6 app (`web/app/load-balancing/page.tsx`), reachable from the existing demo — **the attack
scenes are untouched**; this is the "just load balancing" view the user asked for.

- **FatTreeView** — **tall vertical** SVG of the *full* k=4 fat-tree (all 20 switches + 16 hosts), tiers stacked
  top→bottom (core → aggregation → edge → hosts), links coloured by utilisation (green→red), so polarization is
  *visible* as a few hot paths while others sit idle. Show the whole fabric — the complexity is the point (OQ8-3);
  the page scrolls vertically rather than shrinking the topology.
- **Salt-source selector** — `weak-prng | csprng | qrng`. Switching it re-derives per-switch salts and re-routes the
  same uniform flow set through the vendored `ecmpLink` per stage (D8-parity), animating links from polarized (prng)
  to evenly spread (csprng/qrng).
- **Fairness readouts** — Jain's-index gauge + polarization index + a per-link/path bar strip, all recomputed
  in-browser from the real bucketed counts (no fabricated numbers).
- **Provenance panel (reused from P6)** — shown only for qrng, labelled **attestable provenance, equal balancing to
  CSPRNG** (§3.2 honesty). A one-line honest caption states the single-switch caveat so a reader can't over-claim.
- **No attacker, no defences lamps, no rotation slider** on this page — it is purely entropy-quality → spread.

## Acceptance criteria
- [x] **AC-1** `testbed/topology/fattree_topo.py` builds a k=4 fat-tree (16 hosts, 20 switches) from a `FATTREE_K`
  config knob; boots under Mininet/OVS with the existing controller launcher.
  **Covered by:** `testbed/topology/fattree_topo.py:19,24-40` (`FATTREE_K` default, `FatTreeTopo.build()`); verified
  structurally via `FatTreeTopo()` construction (no Mininet/root needed for `Topo.build()`): 20 switches, 16 hosts,
  48 links. Live boot under real Mininet/OVS/root not exercised in this environment (none available) — see §13.
- [x] **AC-2** Controller hashes independently at every fabric switch under a **per-switch salt** keyed by dpid,
  gated behind `FABRIC_MODE` (default off → P1–P5 behaviour byte-for-byte unchanged).
  **Covered by:** `testbed/controller/ecmp_controller.py:105-114` (per-dpid `_fabric_salts`/`_fabric_ports`/
  `_switch_id_by_dpid`, `FABRIC_MODE`-gated), `:143-156` (`switch_features_handler` fabric branch, every switch gets
  table-miss→CONTROLLER), `:178-185` + `:266-` (`_fabric_packet_in` dispatch via `fabric.next_hop`). OFF path
  (`FABRIC_MODE=0`, default) diff-verified additive-only — no existing single-leaf line altered.
- [x] **AC-3** `polarization_check.py` runs offline (no Mininet/root) and asserts: prng polarizes on **every** run
  (low Jain's, high polarization index — deterministic, no passing seed, OQ8-2), csprng/qrng do not (Jain's ≈ 1.0),
  **and** the single-switch control shows prng ≈ csprng (the false-claim guard). Exits non-zero on any mismatch.
  **Covered by:** `testbed/topology/polarization_check.py` (`_check_prng_polarizes`, `_check_csprng_qrng_even`,
  `_check_single_switch_control`, `main`). Run: exit 0, prng jains≈0.66-0.69/polarization≈2.0-2.2 vs csprng
  jains≈0.97-0.98/polarization≈1.2-1.3, single-switch prng≈csprng jains≈0.99 both. Deliberately weakened csprng
  (shared salt) → gate turned red (jains 0.66, FAIL) then restored to green — confirms the gate actually gates.
  qrng skipped (no `QEAAS_API_KEY`/network in this environment) with an explicit `SKIP:` line, not silently passed.
- [x] **AC-4** A live fat-tree uniform-traffic run (no attacker) emits a compact `salt_source`-tagged fabric CSV
  (`jains_index`, `polarization_index`, per-link load) — **not** P4's leaf per-poll schema — and the prng vs
  csprng/qrng Jain's-index gap reproduces the offline result. `FABRIC_MODE=0` leaves the single-leaf topology
  byte-for-byte unchanged.
  **Partially covered — deferred per plan's own Risk mitigation.** `FABRIC_MODE=0` unchanged: confirmed (diff review,
  AC-2 above). The live Mininet+OVS+root run and its CSV emitter were **not built** — no Mininet/OVS/root available
  in this environment to develop or verify one, and the plan explicitly treats the live controller as separable
  ("ship the offline + web deliverables first and treat the live fabric controller as the follow-on — the argument
  and the figure stand on the offline gate alone"). The offline gate (AC-3) reproduces the Jain's-index gap this AC
  asks for; the live CSV emitter is flagged as follow-on work in §13.
- [x] **AC-5** Web `/load-balancing` route renders the fat-tree, re-routes the uniform flow set through the vendored
  `ecmpLink` per stage on salt-source switch, and visibly moves from polarized (prng) to even (csprng/qrng); build-
  time parity assert still passes 28/28; `grep -r X-API-Key web/out/` stays empty.
  **Covered by:** `web/app/load-balancing/page.tsx`, `web/components/LoadBalanceController.tsx`,
  `web/lib/fabric.ts` (route/fabricLinkLoad using vendored `ecmpLink`). `npm run build` → `check-parity: 28/28
  vectors match`, static export succeeded (`out/load-balancing.html` present), `grep -r X-API-Key web/out/` → 0
  matches. Node-side cross-check of `fabric.ts`'s algorithm against real `ecmpHash.js` confirms the same
  polarization-collapse mechanism as the Python offline gate (weak-prng jains≈0.69/polarization≈2.1 vs csprng
  jains≈0.96/polarization≈1.4).
- **Done when:** the offline check passes, the page shows polarization collapsing as entropy improves, and the
  QRNG panel is labelled as provenance-only (equal balancing to CSPRNG) — ready for P7 to cite as the load-balancing
  figure.

## File plan
Paths relative to `TargetedDosColisionsAndRNGAngle/`. Reuse P4 metrics + P6 web idioms; add nothing new to the hash.

**New files:**
| File | Purpose | Notes |
|------|---------|-------|
| `testbed/topology/fabric.py` | Pure-data fat-tree model: `build_fattree(k)->Fabric`, `fabric_salts(kind, fabric)->dict[sid,bytes]`, `route(fabric, salts, five_tuple)->list[link_id]`, `link_load(fabric, salts, flows)->list[int]`. Calls `hash_core.ecmp_link` per upward hop. No Mininet import. | Shared source of truth (check + controller + parity vs `web/lib/fabric.ts`). |
| `testbed/topology/fattree_topo.py` | `FatTreeTopo(Topo)`, k=4 (20 switches, 16 hosts), `protocols="OpenFlow15"`, stable switch names → stable dpids matching `fabric.py`. | AC-1. Mirrors `ecmp_topo.py`. |
| `testbed/topology/polarization_check.py` | Offline gate: `_check_prng_polarizes()`, `_check_csprng_qrng_even()`, `_check_single_switch_control()`; non-zero exit. | AC-3. Mirrors `collision_check.py` (sys.path insert, `main()`). |
| `web/app/load-balancing/page.tsx` | New static-export route; mounts `LoadBalanceController`. | AC-5. Attack scenes untouched. |
| `web/lib/fabric.ts` | TS mirror of `fabric.py`: fat-tree model + per-switch salt (prng shared / csprng per-switch via `salt.ts`) + `await ecmpLink` per upward hop; `fabricLinkLoad(...)->number[]`. | D8-parity. `ecmpLink` is async. |
| `web/components/FatTreeView.tsx` | **Tall vertical** inline-SVG of the full k=4 fabric (core→agg→edge→hosts stacked), links coloured danger/success by util (CSS vars), `.panel`. | AC-5, OQ8-3. Mirrors `TopologyView.tsx` coord+CSS-var style. |
| `web/components/FairnessReadout.tsx` | Jain's-index gauge + polarization index + per-link bar strip, from real counts. `.panel`. | AC-5. |
| `web/components/LoadBalanceController.tsx` | Client component: salt-source selector (`weak-prng`\|`csprng`\|`qrng`), re-derives salts + re-routes uniform flows via `fabric.ts`, honest QRNG caption + single-switch caveat line, reuses `<ProvenancePanel visible={source==="qrng"}/>`. | AC-5. |

**Modified files:**
| File | Change | Notes |
|------|--------|-------|
| `testbed/config.py` | Add `FATTREE_K = int(env("FATTREE_K","4"))`, `FABRIC_MODE = env("FABRIC_MODE","0")=="1"`. | Toggle discipline like `DEFENCES_ENABLED`. |
| `testbed/metrics/fairness.py` | Add `polarization_index(values: Sequence[float]) -> float` = `max/mean` (guard empty / all-zero → 1.0, mirroring `jains_index`). | Extend, don't rewrite. |
| `testbed/metrics/metrics_check.py` | Add asserts for `polarization_index` on hand-computed vectors (`[1,1,1,1]→1.0`, `[4,0,0,0]→4.0`). | Keeps the metrics gate honest. |
| `testbed/controller/ecmp_controller.py` | `FABRIC_MODE` branch in `switch_features_handler` + `packet_in_handler`: per-dpid datapaths/salts/flows, hash upward fan-out from `fabric.py`. OFF path byte-for-byte unchanged. | AC-2. See §Codebase integration for exact guards. |
| `web/app/layout.tsx` (or new `web/components/Nav.tsx`) | Minimal cross-link demo ↔ `/load-balancing` (basePath-aware). | Discoverability; no nav exists today. |
| `web/README.md`, `testbed/README.md` | Document the `/load-balancing` route, `FABRIC_MODE`/fat-tree run, and `polarization_check.py`. | |

Fabric measurement CSV (compact, salt_source-tagged) is written by `polarization_check.py`/the live run helper as
described in Deliverable A — **not** via `csv_writer.py` (leaf-shaped). No new metrics-writer module unless the live
fabric run needs one; if so, add `testbed/topology/fabric_metrics.py` rather than widening the P4 schema.

## Manual verification (no automated tests, project directive)
1. **Offline gate (primary):** `.venv/bin/python3 testbed/topology/polarization_check.py` → exits 0, prints the
   prng-vs-csprng/qrng Jain's + polarization gap and the single-switch control result. Deliberately weaken a salt
   (make csprng share one salt) to confirm the gate turns red, then restore. This is the correctness gate.
2. **Metrics gate:** `.venv/bin/python3 testbed/metrics/metrics_check.py` → still 0 with the new
   `polarization_index` asserts.
3. **JS↔Python parity (constraint):** in `web/`, `npm run check:parity` → 28/28 (a hash/route change must not break
   it). Optionally spot-check that `fabric.ts` `route()` and `fabric.py` `route()` agree on a few 5-tuples.
4. **Live fat-tree (needs Mininet + OVS + root):**
   `FABRIC_MODE=1 SALT_KIND=prng .venv/bin/python3 testbed/controller/run_controller.py &` +
   `sudo .venv/bin/python3 testbed/topology/run_topo.py` (fat-tree variant), drive **uniform** background traffic
   (no attacker), read `ovs-ofctl -O OpenFlow15 dump-ports` across switches → prng concentrates on a diagonal
   subset; repeat with `SALT_KIND=csprng` → even spread. Confirm the fabric CSV's `jains_index`/`polarization_index`
   reproduce the offline gap. Also confirm `FABRIC_MODE=0` boots the original single-leaf topology unchanged.
5. **Web (Tier A):** `cd web && npm run build` (runs parity first, static export to `out/`), serve `out/`, open
   `/load-balancing` offline: full vertical fat-tree renders; toggling prng→csprng→qrng visibly collapses
   polarization to an even spread; Jain's gauge + polarization index update from real bucket counts; QRNG panel
   shows recorded provenance labelled provenance-only with the single-switch caveat line. `grep -r X-API-Key web/out/`
   → empty (no key leak). Confirm the demo↔load-balancing nav link works under a `NEXT_PUBLIC_BASE_PATH` subpath.

## Out of scope
- The attack scenes / attacker (P3) — this page is deliberately attack-free.
- Leaf-spine / selectable topologies — fat-tree k=4 only.
- Tier B live WebSocket wiring (still P6 stretch) — the page runs on the in-browser sim; a live/replay fat-tree feed
  is a later follow-on.
- The paper (P7) — this plan produces the figure + numbers P7 cites; P7 writes the prose.

## Risks
- **False single-switch claim** → the offline check's single-switch control assert (AC-3) is mandatory and must
  ship first; the page copy must carry the caveat. This is the plan's top risk.
- **Hash/JS drift** → eliminated by reusing P2's vendored `ecmpLink` per stage (D8-parity) + the existing build-time
  parity assert.
- **Over-claiming QRNG** → framing is fixed (D8-seed, §3.2): QRNG = CSPRNG for balancing, provenance is its only
  extra; enforced in page copy + README.
- **`FABRIC_MODE` regressing P1–P5** → default off, OFF path byte-for-byte unchanged, same toggle discipline as
  `DEFENCES_ENABLED`; verify a single-leaf run is untouched with the flag off.
- **Fat-tree visual clutter** (20 switches) → colour links by utilisation and de-emphasise idle ones so polarization
  reads at a glance; k=4 is the smallest fat-tree that still shows it.
- **Controller generalization is the heaviest piece** → the controller is hard-wired single-leaf (per-`LEAF_DPID`
  guards, single `active_salt`/`_leaf_datapath`/`_ecmp_flows`). Fabric mode needs per-dpid datapaths/salts/flows, a
  per-switch upward-egress map, and real up/down routing at every switch — non-trivial. **Mitigation:** the offline
  `fabric.py` + `polarization_check.py` path (the primary correctness gate and what the web page mirrors) needs
  **no controller changes**; the live `FABRIC_MODE` controller is the separable heavier half. If time-boxed, ship
  the offline + web deliverables first and treat the live fabric controller as the follow-on — the argument and the
  figure stand on the offline gate alone.
- **Multi-switch L2/ARP in Mininet** → today s2 gets a single `NORMAL` flow for L2 learning; a full fat-tree of
  learning switches will loop on broadcast/ARP without care. The live topology must handle ARP/return-path across
  many switches (deterministic downward routing + controlled flooding), or restrict the live demo to the offline
  model's flow-level accounting. Flagged so the implementer scopes it, not discovers it live.

## Open questions — RESOLVED (2026-07-27)
- **OQ8-1 — polarization index definition. [RESOLVED: the ratio.]** `polarization_index = max_link_util /
  mean_link_util` (scale-free, pairs with the epic's scale-invariance framing §3.4).
- **OQ8-2 — how weak-PRNG collides fabric-wide. [RESOLVED: demonstrative model, tuned to fail every time.]** Per
  D8-seed, prng salt is the demonstrative small-seed-space LCG (not the exact Python PRNG). Tune it so polarization
  is **deterministic and total, not probabilistic**: model the realistic worst case where the operator ships **one
  identical salt across the whole fabric** (or a seed space so small — e.g. 1–2 collision classes — that every
  stage correlates). `polarization_check.py` asserts prng fails the fairness bar on **every** run (no seed makes it
  pass); no `Math.random`-style variance in the prng path. csprng/qrng stay independent per switch. This makes the
  page's prng→csprng flip unambiguous every load.
- **OQ8-3 — fat-tree too large for one screen. [RESOLVED: vertical layout, show the full complexity.]** Do **not**
  simplify or crop the fabric — render the *whole* k=4 fat-tree (all 20 switches + 16 hosts) and make the complexity
  visible on purpose. Lay it out **vertically** (tiers stacked top→bottom: core → aggregation → edge → hosts) so it
  fits the page width and scrolls down if tall; the page scrolls vertically rather than shrinking the topology.
  `FatTreeView` is a tall vertical SVG, not a squeezed horizontal one — seeing the full multi-tier setup *is* the
  point (it's what makes polarization legible).
- **OQ8-4 — live fat-tree feed to the page.** Deferred to a P6-Tier-B-style follow-on; Tier A sim is the shipping
  commitment here.

## Post-implementation notes (2026-07-27)

**Built:** the pure-data fat-tree model (`testbed/topology/fabric.py`) and its offline correctness gate
(`testbed/topology/polarization_check.py`, AC-3) — the primary, CI-runnable proof of the honest mechanism; the
Mininet fat-tree topology (`testbed/topology/fattree_topo.py`, AC-1); the `FABRIC_MODE` controller generalization
(`testbed/controller/ecmp_controller.py`, AC-2); `fairness.polarization_index` + `metrics_check.py` asserts;
`config.py`'s `FATTREE_K`/`FABRIC_MODE` knobs; and the full web deliverable (`/load-balancing` route, `FatTreeView`,
`FairnessReadout`, `LoadBalanceController`, `web/lib/fabric.ts`/`fairness.ts`, AC-5). Both READMEs document the new
surfaces.

**Bug caught and fixed during implementation:** the first draft of `fabric.py`'s `route()` sent same-pod,
different-edge traffic up through a core switch and back down unnecessarily (real fat-trees keep intra-pod traffic
at the aggregation tier). Caught by cross-checking `route()`'s whole-path output against `next_hop()`'s per-switch
decomposition (the controller consumes `next_hop()`, the offline gate/web consume `route()` — they must agree) over
all 240 host-pair combinations; fixed by short-circuiting `route()` at the aggregation switch when `src_pod ==
dst_pod`. Re-verified: 0 mismatches, offline gate still green.

**Deferred (per this plan's own Risk mitigation, "ship offline + web first"):** the live Mininet+OVS+root fat-tree
run and its `salt_source`-tagged fabric CSV emitter (AC-4's live half) were not built or exercised — no
Mininet/OVS/root was available in the implementation environment. `FABRIC_MODE=0`'s byte-for-byte-unchanged
guarantee for the existing single-leaf controller/topology *was* verified (diff review — every changed line in
`ecmp_controller.py` is additive, gated behind `if FABRIC_MODE:` blocks placed before the existing single-leaf
logic). The developer should run the live fat-tree scenario documented in `testbed/README.md`'s new section on real
hardware/a Mininet-capable box before citing AC-4 as fully closed, and build the fabric CSV emitter
(`testbed/topology/fabric_metrics.py`, per the plan's File plan note) at that point.

**ARP/broadcast in `FABRIC_MODE`:** routed deterministically via the same `next_hop()` path as a synthetic
zero-port five-tuple, not flooded — a fat-tree is a multigraph of redundant paths and naive multi-port flooding
loops (flagged as a risk in this plan). This choice is implemented but, like the rest of `FABRIC_MODE`'s live path,
untested against real OVS/Mininet ARP behaviour.

**Not touched:** `testbed/topology/run_topo.py` (still launches the single-leaf `ECMPTopo` only, per the plan's
own File plan — no fat-tree launcher script was in scope); `testbed/README.md`'s live-run section instead gives an
inline Mininet snippet for `FatTreeTopo` until/unless a dedicated script is wanted.
