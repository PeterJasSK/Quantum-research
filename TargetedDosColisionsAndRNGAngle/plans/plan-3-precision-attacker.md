# Plan 3 — Precision collision attacker & knowledge levels

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 2** · **Priority:** `[MUST]`
**Status:** Complete · **Depends on:** P2 (frozen `hash_core` + salt engine) · **Gates:** P4 (needs the volumetric flood), P5 (runs the matrix)

> Pick up with `/plan-feature plans/plan-3-precision-attacker.md`. Read epic §3.1 (the new-attack framing —
> this plan makes it real), §3.5 (frozen interfaces P3 imports), and §6 (threat model) first.
> **No GitHub issue** — planned from the epic + source build plan (`plan/ECMP_COLLISION_DOS_BUILD_PLAN.md` EPIC 2,
> `plan/3-ecmp-collision-dos-extended.md` Experiments 2–3).
> **No automated tests** (project directive) — verification is manual, described in §Manual verification. Any
> "assert" AC is met by a standalone check script (like P1's `salt_remap_check.py`), not a test suite.

## Goal
The precision collision attacker plus the naive volumetric control. This is the **"new attacker"** the whole epic
is built to characterise: structurally invisible to rate limiting and throttling because it damages by *mathematical
placement*, not by any behaviour a source-watching defence can observe (epic §3.1). P3 delivers a *working attacker*
with three knowledge levels and two traffic modes, plus the **salt-reconstruction timer** that anchors the
Experiment 5 rotation-frequency curve. It does **not** run the experiments or measure victim damage — that is P4
(defences + metrics) and P5 (the matrix).

## Context — what P2 froze that P3 imports (never re-implements)
P2 is **Complete**. P3 consumes these exact artefacts and leaves them untouched (epic §3.5 — the attacker must use
the real hash, or every experiment is silently invalid):

- `testbed/hash_core.py` — `ecmp_link(five_tuple: FiveTuple, salt: bytes, n_links: int) -> int` (SHA-256 of
  `to_bytes() + salt`, first 8 bytes big-endian `% n_links`). **The collision crafter computes against this
  function directly** — no copy, no re-derivation.
- `testbed/types.py` — `FiveTuple(src_ip, dst_ip, src_port, dst_port, proto)` + `to_bytes()`. The crafter emits
  `FiveTuple` instances; the traffic sender turns them into packets.
- `testbed/config.py` — `N_LINKS = 4`, `EGRESS_PORTS`, `REMOTE_IPS` (`{"10.0.0.2"}` = victim on the spine),
  `HOSTS` (`attacker` 10.0.0.1 on the leaf, `victim` 10.0.0.2 on the spine, `bg` 10.0.0.3 on the leaf). **Only
  traffic whose `dst_ip ∈ REMOTE_IPS` traverses the ECMP hash on s1** (`ecmp_controller.py:148-150`) — so every
  crafted flow must be addressed to the victim to be placed by the salt.
- `testbed/salt/sources.py` — the **weak-PRNG model** P3's partial attacker brute-forces: a module-level
  `random.Random(PRNG_SEED)` (32-bit seed space, `config.PRNG_SEED`) drawing successive `SALT_SIZE`-byte salts via
  `.randbytes(size)`, `draw_index` incremented per draw (`sources.py:62-82`). P3 **mirrors this model** to search
  the seed space; it does not import the private `_prng_*` state.
- `testbed/controller/ecmp_controller.py` — `self.active_salt` is the live salt; `rotate_salt()` mints the next
  one. P3's "full" attacker is handed this salt; P3's "partial" attacker must recover it without being told it.

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`, EPIC 2)
- **AC-1** (S2.1 Collision crafter) — Given salt (or a guessed seed space) + target link, enumerate 5-tuples that
  hash to that link. Vary source ports / destination combos so each flow looks distinct.
  **Covered by:** `testbed/attacker/collision.py:9-49` (`CollisionCrafter.craft`/`is_collision`, computes against
  the real `ecmp_link`). Manually verified: `collision_check.py` crafted 500 tuples for a fixed salt+link — all
  500 satisfy `ecmp_link(...) == target_link`, all individually distinct `(src_ip, src_port)`.
- **AC-2** (S2.2 Knowledge levels) — **Full:** salt known → craft exact collision set. **Partial:** algorithm
  known, brute-force seed space → derive salt. **Blind:** no salt info (expected failure baseline).
  **Covered by:** `testbed/attacker/knowledge.py:26-74` (`resolve_salt`, all three branches),
  `testbed/attacker/reconstruct.py:31-79` (`SeedBruteForcer` mirrors `sources._prng_source` exactly),
  `testbed/attacker/oracle.py:20-37` (`LocalOracle` validation channel). Manually verified: full returns the
  handed salt verbatim (`attempts=0`); partial recovered a known seed=42 salt in 43 attempts/0.0011s against a
  reduced 8-bit seed space; blind (`testbed/attacker/traffic.py:16-27` `random_five_tuples`) spread 2000 tuples
  ~uniformly across 4 links (`[532, 481, 499, 488]`, expected 500 each).
- **AC-3** (S2.3 Volumetric control) — single source, no 5-tuple variation, high rate.
  **Covered by:** `testbed/attacker/traffic.py:70-79` (`_send_volumetric`), wired in
  `testbed/attacker/attack.py:69-70` (repeats the first crafted tuple `count` times). Manually verified via
  mocked `scapy.all.send`: `run_attack(level="full", mode="volumetric", ...)` sent exactly `count` packets, one
  fixed 5-tuple, no per-source pacing. Live port-counter confirmation needs Mininet + root — not run this
  session (see Post-Implementation).
- **AC-4** (S2.3 Precision) — collision set spread across multiple compliant sources / many distinct flows, each
  below defence thresholds.
  **Covered by:** `testbed/attacker/traffic.py:82-96` (`_send_precision`, per-`src_ip` pacing at
  `per_source_cap` pps), `testbed/config.py` `ATTACK_SOURCE_IPS`/`PRECISION_PER_SOURCE_PPS`. Manually verified
  via mocked `scapy.all.send`: `run_attack(level="full", mode="precision", ...)` spread flows across the
  configured spoof pool, `sources_used` in the run-record showing multiple distinct source IPs. Live
  per-source-compliance confirmation needs Mininet + root — not run this session.
- **Done when:** the full-knowledge attacker drives crafted flows onto one target link; the partial attacker
  reconstructs the salt by brute force; the volumetric mode floods naively for the control.
  **Covered by:** all of the above; end-to-end `run_attack` exercised for `full`/`partial`/`blind` ×
  `volumetric`/`precision` with `scapy.all.send` mocked (no live network in this environment).

## Hard constraint — use the real hash
The crafter imports `ecmp_link` and `FiveTuple` from `testbed` and computes placement against them. A crafted
5-tuple is a member of the collision set **iff** `ecmp_link(ft, salt, N_LINKS) == target_link`. Never re-implement
the hash, the serialisation, or the `% N` step in the attacker — a drift there makes the attack look like it works
against a hash the controller does not use, silently invalidating Experiments 2–5.

## Attack design

### AC-1 — Collision crafter (`testbed/attacker/collision.py`)
`CollisionCrafter(salt: bytes, target_link: int, n_links: int = N_LINKS)` enumerates `FiveTuple`s that hash to
`target_link` under `salt`:

- `craft(count, *, dst_ip, proto, src_ip_pool, src_port_range, dst_port) -> list[FiveTuple]` — walk candidate
  `(src_ip, src_port)` combinations, keep those where `ecmp_link(ft, self.salt, self.n_links) == target_link`,
  stop at `count`. **`dst_ip` defaults to the victim IP** (the only address the ECMP hash acts on); each kept tuple
  varies `src_ip`/`src_port` so the flows look individually distinct (AC-1 "each flow looks distinct", and the
  raw material for AC-4's per-source spread).
- `is_collision(ft) -> bool` — single-tuple membership test, used by the check script.
- Collisions are ~`1/n_links` of the candidate space, so enumeration is cheap (thousands of hits per second).

### AC-2 — Knowledge levels (`testbed/attacker/knowledge.py`, `reconstruct.py`, `oracle.py`)
A single entry point resolves the salt the crafter will use, per level, and reports how much work it cost (the
Exp 5 anchor):

```python
KnowledgeLevel = Literal["full", "partial", "blind"]

@dataclass(frozen=True)
class Reconstruction:
    level: KnowledgeLevel
    salt: bytes | None          # recovered salt; None for blind
    attempts: int               # seeds tried (0 for full/blind)
    elapsed_seconds: float      # wall-clock reconstruction time — the Exp 5 x-axis anchor
    recovered_seed: int | None  # the seed found (partial only)

def resolve_salt(level: KnowledgeLevel, *, known_salt, oracle, seed_space_bits, draw_window) -> Reconstruction
```

- **Full** — `known_salt` (the controller's `active_salt`, handed to the attacker) is returned verbatim;
  `attempts=0`, `elapsed_seconds≈0`. Models "if the salt ever leaks, damage is immediate" (epic §8 Q3 upper bound).
- **Partial** — the realistic attacker. Knows the *algorithm* (weak `random.Random(seed).randbytes`, 32-bit seed
  space, per the P2 model) but not the seed. `SeedBruteForcer` (`reconstruct.py`) searches the seed space,
  reconstructing each candidate salt exactly as `sources._prng_source` would (`random.Random(seed).randbytes(size)`
  at a bounded `draw_window` of draw indices), and **validates each candidate against a `PlacementOracle`** — a
  handful of probe 5-tuples whose true egress link the attacker can observe. A candidate seed is accepted when its
  computed placements match the oracle on **all** probes. Returns the salt, seed, attempt count, and wall time.
- **Blind** — no salt info. `salt=None`; the attacker cannot craft a collision set, so the traffic layer falls
  back to random 5-tuples (expected failure baseline — they spread ~uniformly, no link saturates).

**The oracle (`oracle.py`).** Brute-force needs a way to confirm a guess. In the real threat model the attacker
*infers* placement from congestion/timing side channels; the testbed provides that channel as a first-class object:
`PlacementOracle` returns the true egress link for a probe 5-tuple under the controller's current salt.
`LocalOracle(salt)` computes it directly via `ecmp_link` (used offline for crafting and for the check script). The
"real inference is a congestion side-channel, not a direct read" caveat is documented for P7, not implemented here.

**Reconstruction timing is instrumented on purpose.** `elapsed_seconds` and `attempts` are the anchor P5 reads for
the Experiment 5 rotation-frequency curve ("rotate faster than the reconstruction window and the attacker never
assembles a working set" — extended doc, Exp 5). P3 only *produces and logs* this number; P5 sweeps it.

### AC-3 / AC-4 — Traffic modes (`testbed/attacker/traffic.py`)
One sender, two modes, both emitting crafted (or random-blind) `FiveTuple`s as real packets toward the victim:

- **Volumetric (AC-3)** — a single source IP + a single fixed 5-tuple (no variation), sent at high rate. This is
  the naive control the P4 defences must *catch* (Experiment 1). No collision crafting needed.
- **Precision (AC-4)** — the collision set spread across **multiple compliant sources** and many distinct flows,
  each individually below the P4 rate-limit and throttle thresholds. Since P1's topology has one `attacker` host,
  "multiple sources" is realised by **source-IP spoofing from that host** (scapy sets arbitrary `src_ip`/`src_port`)
  drawn from a configured source-IP pool — no topology change (P1 owns topology; epic §8 Q1 headroom is a
  *later* bolt-on, not this plan). The sender enforces a **per-source send cap** so each spoofed source stays under
  the defence threshold — that cap being under the limit is exactly what makes Experiments 2–3 land.

The defining property the sender must preserve: **no single source and no single flow is anomalous.** The damage is
the *aggregate* landing on one link; that is the whole point of the attacker.

## Interfaces exposed to P4/P5 (freeze — downstream imports, does not redefine)
- `CollisionCrafter` / `craft(...)` — P5 builds attack runs from it.
- `resolve_salt(level, ...) -> Reconstruction` — P5 reads `elapsed_seconds`/`attempts` for the Exp 5 curve and
  tags each run by `knowledge_level` (epic §4 run-tagged CSV).
- `run_attack(...)` orchestration + its CLI (`run_attack.py`) — P4/P5 launch attacks against the live testbed
  through this one entry point, passing `(knowledge_level, mode, target_link, salt or seed_space)`.
- The attack does **not** own any metrics CSV — it emits a small structured run-record
  (`{level, mode, target_link, salt_source, sources_used, flows_sent, reconstruction: {attempts, elapsed_seconds}}`)
  that P4's collectors and P5's matrix consume. Salt-source tagging comes from P2's `SaltResult.provenance`.

## File plan
All paths relative to `TargetedDosColisionsAndRNGAngle/`. New unless marked **edit**.

| File | Purpose | AC | Notes |
|------|---------|----|-------|
| `testbed/attacker/__init__.py` | Package marker; re-export `CollisionCrafter`, `resolve_salt`, `Reconstruction`, `KnowledgeLevel`, `run_attack`. | — | New package, sibling of `testbed/salt/`. |
| `testbed/attacker/collision.py` | `CollisionCrafter(salt, target_link, n_links)`; `craft(...) -> list[FiveTuple]`, `is_collision(ft)`. Imports `ecmp_link`, `FiveTuple`. | AC-1 | The real-hash crafter. Dependency-free (no scapy import here). |
| `testbed/attacker/oracle.py` | `PlacementOracle` protocol + `LocalOracle(salt)` computing true link via `ecmp_link`. | AC-2 | The brute-force validation channel; models the attacker's placement-inference side channel. |
| `testbed/attacker/reconstruct.py` | `SeedBruteForcer(seed_space_bits=32, draw_window)`: mirror the P2 weak-PRNG model, search seeds, validate via oracle, time it. | AC-2 | Mirrors `sources._prng_source` semantics exactly (`random.Random(seed).randbytes(size)`); the Exp 5 timing anchor lives here. |
| `testbed/attacker/knowledge.py` | `KnowledgeLevel`, `Reconstruction`, `resolve_salt(level, ...)`. Full→given, partial→`SeedBruteForcer`, blind→None. | AC-2 | The frozen knowledge-level entry point P5 imports. |
| `testbed/attacker/traffic.py` | `send_flows(five_tuples, *, mode, rate_pps, per_source_cap, iface)`; volumetric vs precision; scapy sender with src-IP/port spoofing; blind→random tuples. | AC-3, AC-4 | Only file needing scapy + root/netns. Keep packet crafting out of `collision.py`. |
| `testbed/attacker/attack.py` | `run_attack(level, mode, target_link, *, salt_source_kind, ...)`: resolve salt → craft set → send → emit run-record. | AC-1–4 | Orchestrator; wires P2 salt provenance into the run-record. |
| `testbed/attacker/run_attack.py` | argparse CLI run from the Mininet `attacker` host: `--level --mode --target-link --count --rate ...`. | AC-1–4 | Mirrors P1/P2 runner style (`run_controller.py`, `run_topo.py`). |
| `testbed/attacker/collision_check.py` | Standalone check (like P1's spike): craft K tuples for a fixed salt+link, assert every one satisfies `ecmp_link(...) == target_link`; exit non-zero on any miss. Also: blind set spreads ~uniformly; partial recovers a known seed. | AC-1, AC-2 | The "assert" ACs as a manual checker, no test suite (project directive). |
| `testbed/config.py` | **edit** — add an `ATTACK_*` block: `TARGET_LINK` (default `0`), `ATTACK_SOURCE_IPS` (spoof pool), `PRECISION_PER_SOURCE_PPS`, `VOLUMETRIC_PPS`, `PRNG_SEED_SPACE_BITS = 32`, `BRUTEFORCE_DRAW_WINDOW`. | AC-3, AC-4 | Knobs as data; P5 sweeps these. Reuse existing `N_LINKS`/`EGRESS_PORTS`/`REMOTE_IPS`. |
| `testbed/README.md` | **edit** — add "Running the attacker": each level × mode, the spoof-pool note, root/netns requirement, and `collision_check.py`. | — | Extends P1/P2 runbook. |
| `requirements.txt` | **edit** — add `scapy` (traffic gen). Note `hping3`/`iperf` are system tools, not pip deps. | — | Keep P1/P2 notes. |

## Manual verification (no automated tests — project directive)
Run from `TargetedDosColisionsAndRNGAngle/`. Steps 1–4 need no Mininet/root; step 5 needs the live testbed.

1. **AC-1 crafter (offline)** — `python testbed/attacker/collision_check.py`: for a fixed salt and `target_link`,
   craft e.g. 500 tuples and confirm **every** one satisfies `ecmp_link(ft, salt, N_LINKS) == target_link` (real
   hash), and that the tuples vary `src_ip`/`src_port` (distinct-flow property). Exit non-zero if any tuple misses.
2. **AC-2 full** — hand the crafter a known salt; confirm the crafted set maps entirely to the target link (a
   special case of step 1 with `salt = active_salt`).
3. **AC-2 partial** — set `PRNG_SEED` to a known value; build a `LocalOracle` from the salt that value produces;
   run `SeedBruteForcer` and confirm it **recovers the exact salt and seed**, and prints `attempts` and
   `elapsed_seconds` (the Exp 5 anchor). Try two seeds (small and near the top of a reduced space) to see the
   time grow with the seed index.
4. **AC-2 blind** — craft with no salt: the random 5-tuples spread ~uniformly across the N links (roughly
   `count/N` each, no single-link concentration) — the expected-failure baseline.
5. **AC-3/AC-4 live traffic** *(needs Mininet + OVS + root)* — boot the P1 topology + P2 controller
   (`SALT_KIND=prng`, rotation off). From the `attacker` host:
   - **Volumetric:** `run_attack.py --mode volumetric` — a single fixed flow at high rate; confirm it lands on one
     link and (in P4) trips the defence.
   - **Precision:** `run_attack.py --mode precision --level full` — confirm the target link's port-stats climb
     while **each spoofed source stays under `PRECISION_PER_SOURCE_PPS`** and total flows spread across the source
     pool. (Victim-collapse and defence-never-fires are *measured* in P4/P5; here only confirm placement +
     per-source compliance.)

## Conventions
- Strict typing + PEP 8, matching P1/P2: `from __future__ import annotations`, full type hints on public functions,
  frozen dataclasses for results.
- `collision.py`/`knowledge.py`/`reconstruct.py`/`oracle.py` stay **dependency-free** (import only `testbed`
  internals + stdlib) so they run and are checkable without root or scapy. scapy is confined to `traffic.py`.
- Reconstruction mirrors the P2 weak-PRNG model **exactly** — read `sources._prng_source` and reproduce
  `random.Random(seed).randbytes(size)` and the draw-index semantics; do not guess.
- No raw sockets hand-rolled where scapy suffices; `hping3`/`iperf` are optional load alternatives noted in the
  README, not required by the code.

## Out of scope
- The defences the attacker evades — rate limiting + throttling — and the five metrics/CSV (P4).
- Running the experiment matrix and rendering the two graphs (P5); measuring victim throughput, Jain's index,
  time-to-saturation (all P4/P5). P3 emits the run-record; it does not compute damage.
- The web demo's JS attacker mirror (P6) and the paper (P7).
- Any change to `hash_core.ecmp_link`, `FiveTuple.to_bytes`, or the P2 salt engine (frozen upstream — changing them
  breaks every downstream plan).
- The Q1 blast-radius multi-victim attack (epic §8 Q1 — a later bolt-on, not this plan).

## Risks
- **Attacker hash drift** → if the crafter ever computes against a re-implemented hash instead of `ecmp_link`, the
  attack "works" against a hash the controller does not use and Experiments 2–5 are silently invalid. Mitigated by
  importing the real function and by `collision_check.py` asserting membership against it.
- **Brute-force intractable / ill-defined** → if the partial attacker cannot validate a guess, or the seed+draw
  space is larger than modelled, reconstruction time (the Exp 5 anchor) is meaningless. Mitigated by the
  `PlacementOracle` validation channel and by keeping the seed space at the P2-frozen 32 bits with a bounded draw
  window (OQ-2).
- **Source spoofing blocked** → OVS/Mininet may drop packets whose `src_ip` is not the host's configured address
  (RPF/anti-spoof). Confirm in step 5 that spoofed sources traverse the leaf; if dropped, fall back to a small pool
  of real extra attacker hosts (needs a P1 topology tweak — flag to P1, do not silently change scope). *(OQ-3.)*
- **Rate too high crashes emulation** → scapy at very high pps can swamp Mininet. Keep `VOLUMETRIC_PPS` /
  `PRECISION_PER_SOURCE_PPS` as tunable config; document a sane default in the README.

## Open questions — RESOLVED (2026-07-24, all defaults accepted)
- [x] **OQ-1 (placement oracle).** **RESOLVED:** ship a testbed `PlacementOracle` (`LocalOracle` computing the true
  link via `ecmp_link`) as the brute-force validation channel, modelling the attacker's real-world
  placement-inference side channel; document that real inference is congestion/timing-based (P7), not a direct read.
  *Affects `oracle.py`, `reconstruct.py`.*
- [x] **OQ-2 (draw-index & per-rotation re-search).** **RESOLVED:** model the partial attacker as **re-searching the
  seed space (+ a bounded `BRUTEFORCE_DRAW_WINDOW` of draw indices) per rotation**, treating per-search
  `elapsed_seconds` as the Exp 5 reconstruction window. The "known weak-PRNG seed predicts the entire future salt
  sequence, making rotation useless" subtlety is **flagged for P5** (experiment design) and **P7** (honest framing of
  the weak-PRNG threat) — P3 implements the per-rotation re-search model and instruments the timing.
  *Affects `reconstruct.py`, and P5/P7 framing.*
- [x] **OQ-3 (multiple sources = spoofing vs extra hosts).** **RESOLVED:** realise "multiple compliant sources" by
  **src-IP spoofing from the single P1 `attacker` host** (scapy), drawn from `ATTACK_SOURCE_IPS` — no topology
  change. If OVS anti-spoofing drops them (Risk above), escalate to P1 for a small real-host pool rather than
  expanding P3's scope. *Affects `traffic.py`, possibly P1.*
- [x] **OQ-4 (target-link definition).** **RESOLVED:** an index into `EGRESS_PORTS` (`config.TARGET_LINK`, default
  `0`); for a realistic run, the attacker picks the link the victim's steady flow currently hashes to (obtained via
  the `PlacementOracle`), so the collision set lands on the victim's own link. *Affects `attack.py`, `config.py`.*
- [x] **OQ-5 (scapy dependency).** **RESOLVED:** add `scapy` to `requirements.txt` — the standard tool for arbitrary
  5-tuple / spoofed-source crafting, already named in the build plan (`scapy`/`hping3`/`iperf`). Confined to
  `traffic.py` so the rest of the attacker runs without it or root.

## Notes for `/implement-feature` (downstream)
- Import `ecmp_link`, `FiveTuple` (and `N_LINKS`, `EGRESS_PORTS`, `REMOTE_IPS`, `PRNG_SEED`) from `testbed`
  **verbatim** — the crafter and reconstructor must match the controller bit-for-bit (epic §3.5).
- Keep `collision.py`/`knowledge.py`/`reconstruct.py`/`oracle.py` runnable without scapy/root so
  `collision_check.py` and the partial-reconstruction check work in any environment (as P2's parity checker did).
- Instrument `Reconstruction.elapsed_seconds`/`attempts` carefully — they are the load-bearing input to P5's
  Experiment 5 curve, not just debug output.
- Emit the run-record structure listed under §Interfaces exposed to P4/P5 so P4/P5 can wire it into the CSV without
  reshaping.

## §13 Post-Implementation

Built the full P3 file plan: `testbed/attacker/` package (`__init__.py`, `collision.py`, `oracle.py`,
`reconstruct.py`, `knowledge.py`, `traffic.py`, `attack.py`, `run_attack.py`, `collision_check.py`), the
`ATTACK_*` block in `testbed/config.py`, `scapy` added to `requirements.txt`, and a "Running the attacker"
section in `testbed/README.md`. `hash_core.ecmp_link`/`FiveTuple`/`salt/sources.py` untouched — the crafter and
reconstructor import them verbatim, never re-implement.

**Verified this session (no Mininet/root available in this environment):**
- `collision_check.py` (offline, no scapy/root): all three checks pass — 500/500 crafted collisions verified
  against the real hash and individually distinct; blind traffic spread `[532, 481, 499, 488]` across 4 links;
  `SeedBruteForcer` recovered a known seed=42 in 43 attempts/0.0011s.
- `run_attack()` orchestration exercised end-to-end for all three knowledge levels × both traffic modes
  (`full`/`partial`/`blind` × `volumetric`/`precision`) with `scapy.all.send` mocked (`pip install scapy` into
  the venv; no root/netns/interface available here) — confirmed correct packet counts, per-source pacing
  (`sources_used` in the run-record), and the exact run-record shape from §Interfaces.
- One correctness fix found during verification: the initial `collision_check.py` partial-reconstruction probe
  set (3 probes) had too high a false-positive rate for an 8-bit test seed space — brute force found a wrong
  seed (6) before reaching the true seed (42). Fixed by widening to 6 probes (both in `collision_check.py` and
  `run_attack.py`'s `_build_probes`), which drops the false-positive rate to ~4^-6 per candidate.

**Not verified (needs the real testbed environment — Mininet + OVS + root, not available in this session):**
- AC-3/AC-4 live traffic (step 5): actual packet send via scapy from the Mininet `attacker` host, port-counter
  confirmation via `ovs-ofctl dump-ports`, and whether OVS/Mininet drops spoofed-source packets (RPF/anti-spoof,
  the Risk flagged in this plan and OQ-3).
- A real 32-bit partial-knowledge brute force (only a reduced 8/10/16-bit space was exercised) — the full
  `PRNG_SEED_SPACE_BITS = 32` default is computationally intractable in pure Python and is expected to only ever
  run at a reduced width in practice (per this plan's Manual verification §3 and OQ-2's per-rotation re-search
  framing); P5 sweeps the practical range.

**Deviations from the plan:** none in scope or interfaces. The 3→6 probe-count change above is an
implementation-detail fix within `collision_check.py`/`run_attack.py`'s own test/CLI fixtures, not a change to
any frozen interface (`resolve_salt`, `CollisionCrafter`, `run_attack` signatures are exactly as specified).
