# Plan 4 — Baseline defences & instrumentation

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 3** · **Priority:** `[MUST]`
**Status:** Complete · **Depends on:** P1 (topology + controller), P2 (salt engine, frozen), P3 (volumetric flood) · **Gates:** P5 (runs the matrix), P6 Tier B (reads the CSV / counters)

> Pick up with `/plan-feature plans/plan-4-defences-instrumentation.md`. Read epic §3.1 (why these
> defences must *fire on the flood yet fail against precision*), §3.5 (frozen interfaces — do not touch
> the hash core or salt engine), §4 (the five metrics + the run-tagged CSV schema) first.
> **No GitHub issue** — planned from the epic + source build plan (`plan/ECMP_COLLISION_DOS_BUILD_PLAN.md`
> EPIC 3, `plan/3-ecmp-collision-dos-extended.md` Experiment 1).
> **No automated tests** (project directive) — verification is manual, described in §Manual verification.
> Any "verified" AC is met by a standalone check script / live run, never a test suite.

## Goal
The two baseline defences that **must stop the volumetric flood but fail against the precision attacker** —
per-source **rate limiting** and per-source **connection throttling** — plus the **five metrics collectors**
that prove it, all writing to a single **run-tagged CSV**. Without a defence that provably fires on the flood,
"our attacker evades defences" is indistinguishable from "the defences were misconfigured" (epic §3.1). P4
delivers *working defences* (installed as controller flow rules / OpenFlow meters) and *working instrumentation*
(port-stats polling → utilisation, Jain, victim throughput, saturation timing). It does **not** run the
experiment matrix or render graphs — that is P5, which drives the attacker (P3) against these defences and reads
this CSV.

## Context — what upstream froze that P4 consumes (never re-implements)
P1 and P2 are **Complete**; P3 is **Complete**. P4 extends the controller with defences + instrumentation and
imports the rest verbatim (epic §3.5 — reusing the real controller/hash is the only way the experiments are valid):

- `testbed/controller/ecmp_controller.py` — `ECMPController(OSKenApp)`, OpenFlow **1.5** (`ofproto_v1_5`) on
  os_ken. Key extension points P4 edits, not rewrites:
  - `packet_in_handler` (`:101-167`) — the leaf install path. For a victim-bound 5-tuple it computes
    `ecmp_link(...)`, tracks the flow in `self._ecmp_flows`, and installs an **exact-match priority-10** flow
    (`_add_flow`, `:344-350`). This is where a per-source **meter** (rate limit) and the **throttle decision**
    hook in.
  - `_add_flow(datapath, priority, match, actions)` (`:344-350`) and `_match_for(parser, five_tuple)`
    (`:288-295`) — the flow-install / match helpers P4 reuses.
  - `switch_features_handler` (`:79-99`) — where the leaf datapath is captured (`self._leaf_datapath`);
    P4 spawns the port-stats poll loop once the leaf is up (mirrors the `_rotation_loop` `hub.spawn` at `:76-77`).
  - `self.salt_kind` / `self.active_salt` (`:63-64`) and `ROTATION_INTERVAL_SECONDS` — the controller already
    knows two of the four CSV tags (`salt_source`, `rotation_interval`); P4 reads them for tagging.
- `testbed/config.py` — `N_LINKS = 4`, `LEAF_DPID`, `EGRESS_PORTS` (the N leaf→spine ports whose stats we poll),
  `SALT_KIND`, `ROTATION_INTERVAL_SECONDS`. P4 adds a `DEFENCE_*` / `METRICS_*` block alongside the existing
  `P2`/`P3` blocks; it reuses `EGRESS_PORTS`/`N_LINKS`, never redefines them.
- `testbed/attacker/` (P3) — the attacker emits a structured **run-record**
  `{level, mode, target_link, salt_source, sources_used, flows_sent, reconstruction:{attempts, elapsed_seconds}}`
  (plan-3 §Interfaces). It owns **no CSV**. P4's collector supplies the CSV; the two run-tags the controller does
  *not* know — `knowledge_level` and `attack_mode` — are passed to the collector as run context (env/CLI), set by
  whoever launches the run (P5's matrix, or a manual operator). P4 does **not** launch the attacker.
- `testbed/salt/…` and `testbed/hash_core.py` — **frozen, untouched.** Rotation, salt sources, and the hash are
  P2's; P4 only reads `salt_kind`/`interval` for tagging.

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`, EPIC 3)
- **AC-1** (S3.1) — Per-source **rate limiting** (bandwidth cap per source).
  **Delivered by:** `testbed/controller/defences.py` (`DefencePolicy.meter_id_for`, `defences.py:61`) + a per-source
  OpenFlow **meter** (`OFPMeterMod`/`OFPMeterBandDrop`/`OFPMF_KBPS`) installed on demand
  (`ecmp_controller.py:406-424` `_ensure_meter`), referenced from the ECMP flow via `OFPInstructionMeter`
  (`ecmp_controller.py:397-404` `_add_flow`). Cap = `config.RATE_LIMIT_KBPS` (`config.py`) per distinct `src_ip`.
- **AC-2** (S3.1) — Per-source **connection throttling** (drop/deprioritise after N connections/requests).
  **Delivered by:** `DefencePolicy.note_flow` (`defences.py:40-56`) — per-`src_ip` new-flow counter over a sliding
  window, deduped by `(src_ip, five_tuple)` so rotation re-installs don't double-count; once over
  `config.THROTTLE_MAX_CONNECTIONS`, `ecmp_controller.py:426-434` `_install_throttle_drop` installs a priority-20
  drop flow matching that `src_ip` (deprioritise variant via `config.THROTTLE_ACTION`, `ecmp_controller.py:193-198`).
- **AC-3** (S3.1) — Both must visibly stop the volumetric flood (verified in Experiment 1).
  **Delivered by:** both mechanisms above are installed when `config.DEFENCES_ENABLED` is set
  (`ecmp_controller.py:78-90` init, `:145-146` poll-loop spawn). Manual verification (steps 3-4 below) demonstrates
  each fires on an appropriate single-source flood. The *combined* Experiment-1 verification is **P5's** to run and
  record — P4 provides and proves the mechanisms; it does not own Experiment 1.
- **AC-4** (S3.2) — Per-link utilisation (OpenFlow port-stats poll) + **max link utilisation**.
  **Delivered by:** `ecmp_controller.py:459-467` polls `OFPPortStatsRequest` on `EGRESS_PORTS` at
  `config.PORT_STATS_POLL_INTERVAL_SECONDS`; `testbed/metrics/collector.py:95-163` `on_port_stats` computes
  Δtx_bytes/Δt ÷ `config.LINK_CAPACITY_MBPS` per link and `max()` across links (`collector.py:120-127`). Verified
  offline: `metrics_check.py::_check_utilisation_and_max` (PASS).
- **AC-5** (S3.2) — **Jain's fairness index** across links.
  **Delivered by:** `testbed/metrics/fairness.py:7-17` (`jains_index(values)`), applied per poll in
  `collector.py:128`. Verified offline: `metrics_check.py::_check_jains_edge_cases` — idle `1.0`, fair `1.0`,
  single-link concentration `0.25` (PASS).
- **AC-6** (S3.2) — **Victim throughput** under attack (`iperf`).
  **Delivered by:** `testbed/metrics/victim_throughput.py` — `run_server`/`run_client` (`:24-42`) wrap `iperf3`
  (victim = server, `bg` host = client); `latest_mbps` (`:44-64`) parses the rolling `--json-stream` output and is
  read by the collector each poll (`collector.py:131-133`), merged by timestamp. Degrades to `None`/empty column,
  never a crash, if `iperf3` is absent.
- **AC-7** (S3.2) — **Time-to-saturation** and **packets/flows-to-saturation** of the target link.
  **Delivered by:** `collector.py:135-139` latches on the first poll `max_util ≥ config.SATURATION_UTILISATION`,
  recording elapsed seconds since `RunContext.start_time` plus the target port's cumulative `tx_packets` and
  `tracked_flows` at that instant. Verified offline: `metrics_check.py::_check_saturation_latch` — latches on the
  correct poll with the correct elapsed/packets/flows (PASS).
- **Done when:** defences drop the naive flood; all five metrics log to CSV per run, timestamped and tagged by
  (salt source, knowledge level, rotation interval, attack mode).
  **Delivered by:** `testbed/metrics/csv_writer.py` — `CsvWriter.write_row` (`:56-61`) writes `config.METRICS_CSV_PATH`
  with every row carrying the four tags + timestamp + elapsed (`collector.py:141-159`); `CsvWriter.write_summary`
  (`:63-69`) rewrites the `*.summary.csv` sidecar with the always-current saturation/final metrics
  (`collector.py:166-179`).

## The five metrics (epic §4) → where each is produced
| Metric | Source | Producer |
|--------|--------|----------|
| Max link utilisation | Δtx_bytes over poll interval ÷ link capacity, max over `EGRESS_PORTS` | `metrics/collector.py` |
| Jain's fairness index | per-link throughput vector each poll | `metrics/fairness.py` |
| Victim throughput (`iperf`) | `iperf` server on victim, client on `bg`, parsed per interval | `metrics/victim_throughput.py` |
| Time-to-saturation | first poll `max_util ≥ SATURATION_UTILISATION`, elapsed since attack start | `metrics/collector.py` |
| Packets/flows-to-saturation | target-port `tx_packets` + tracked flow count at saturation | `metrics/collector.py` |

**CSV tagging (mandatory, epic §4):** every row tagged `(salt_source, knowledge_level, rotation_interval,
attack_mode)` + ISO-8601 `timestamp` + `elapsed_seconds`. `salt_source`/`rotation_interval` come from the
controller (`salt_kind`, `ROTATION_INTERVAL_SECONDS`); `knowledge_level`/`attack_mode` come from run context
(env `KNOWLEDGE_LEVEL` / `ATTACK_MODE`, default `"na"`). A missing tag breaks P5 filtering and P6 Tier-B replay.

## Design

### Defences (`testbed/controller/defences.py` + minimal `ecmp_controller.py` edits)
Keep the *policy* (pure, testable-by-hand, no OpenFlow imports where avoidable) in `defences.py`; keep the
*wiring* (installing meters / drop flows on the live datapath) in the controller, reusing its existing helpers.

- **`DefencePolicy`** (frozen-ish state object owned by the controller):
  - `note_flow(src_ip) -> ThrottleDecision` — increments the per-`src_ip` new-flow counter over a sliding window
    (`config.THROTTLE_WINDOW_SECONDS`); returns whether the source is now over `THROTTLE_MAX_CONNECTIONS`.
    The controller uses this in `packet_in_handler` **before** installing an ECMP flow.
  - `meter_id_for(src_ip) -> int` — a stable small integer per source (e.g. hash of the last IP octet into a
    bounded meter-id range), so one meter per source is installed once and reused.
  - `wall-clock is injected` (pass a `now: float`) so the policy stays deterministic and clock-free at its core.
- **Rate limiting (AC-1):** on the first ECMP flow for a `src_ip`, the controller sends an `OFPMeterMod`
  (`command=ADD`, one `OFPMeterBandDrop(rate=RATE_LIMIT_KBPS, burst_size=RATE_LIMIT_BURST_KB)`, `flags=OFPMF_KBPS`)
  and thereafter includes `OFPInstructionMeter(meter_id_for(src_ip))` in that source's flow instructions
  (alongside the existing `OFPActionOutput`). Bytes over the cap are dropped by the datapath — a genuine
  per-source bandwidth cap, no controller involvement per packet.
- **Throttling (AC-2):** when `note_flow(src_ip)` reports over-limit, install a **priority-20** drop flow
  (`OFPMatch(eth_type=IP, ipv4_src=src_ip)`, empty action list = drop) so subsequent new flows from that source
  are dropped at the switch. `THROTTLE_ACTION = "drop" | "deprioritise"` selects drop vs a low-priority
  best-effort re-route (deprioritise = install the ECMP flow but at priority 1 so it loses to legitimate traffic).
- **Toggle:** all of the above is gated on `config.DEFENCES_ENABLED` (default off, so P3's existing runs and the
  "defences OFF" experiment cells are unaffected). When off, `packet_in_handler` behaves exactly as today.
- **Why this stops volumetric but not precision (the epic's thesis, realised here):** the volumetric control is a
  single `src_ip` → its byte rate trips the per-source meter *and* its connection/request rate trips the throttle.
  The precision attacker (P3) spreads the identical collision set across `ATTACK_SOURCE_IPS` at
  `PRECISION_PER_SOURCE_PPS`, so **no single source** exceeds either per-source cap — the aggregate still lands on
  one link. P4 must therefore keep both caps *per-source* (never global) and tune them (below) so precision passes
  under and volumetric does not. Those exact thresholds are frozen and **reused unchanged** in P5 Experiments 2–3.

### Threshold tuning (frozen once, reused in P5)
`RATE_LIMIT_KBPS` and `THROTTLE_MAX_CONNECTIONS` must sit **above** what one precision source emits
(`PRECISION_PER_SOURCE_PPS = 5`, small per-source connection count) and **below** what the volumetric control
emits (`VOLUMETRIC_PPS = 1000`, single source). Pick defaults with clear headroom on both sides (e.g. rate limit
an order of magnitude above one precision source's bandwidth but well under the volumetric single-source rate),
document the chosen numbers in `config.py` comments and the README, and **do not re-tune per experiment** — a
moving threshold would make "precision evades / volumetric caught" unfalsifiable. This is the single most
important correctness property of P4.

### Instrumentation (`testbed/metrics/`)
- **`PortStatsPoller` / poll loop** — the controller `hub.spawn`s a loop (once `_leaf_datapath` is set) that sends
  `OFPPortStatsRequest(datapath, port_no=OFPP_ANY)` every `PORT_STATS_POLL_INTERVAL_SECONDS`; the reply handler
  (`@set_ev_cls(EventOFPPortStatsReply, MAIN_DISPATCHER)`) forwards the `body` to the `MetricsCollector`.
- **`MetricsCollector` (`metrics/collector.py`)** — stateful over a run:
  - keeps last-sample `tx_bytes`/`tx_packets` per egress port; each poll computes Δ/Δt → per-link throughput and
    utilisation (AC-4), the max (AC-4), and Jain's index over the per-link vector (AC-5);
  - merges the latest victim-throughput reading (AC-6) by timestamp;
  - on the first poll crossing `SATURATION_UTILISATION`, latches time-to-saturation, target-port `tx_packets`, and
    the tracked flow count (AC-7);
  - writes one CSV row per poll (all metrics + four tags + timestamp + elapsed) via `metrics/csv_writer.py`, and
    on run-stop writes/updates a `*.summary.csv` sidecar with the saturation metrics and final Jain/victim numbers.
  - **Pure computation** (Δ, utilisation, Jain, saturation detection) lives in `collector.py`/`fairness.py` as
    plain functions with no OpenFlow types, so they are checkable offline with synthetic samples.
- **`jains_index(values)` (`metrics/fairness.py`)** — `(Σx)² / (n · Σx²)`, returns `1.0` for the all-zero vector
  (no traffic = trivially fair), so an idle poll does not divide by zero.
- **`victim_throughput.py`** — a runner that starts `iperf`/`iperf3` (victim server, `bg` client) for the run
  duration and parses per-interval throughput into `(timestamp, mbps)` samples. Runs out-of-band from the
  controller (it needs host/netns exec, not the OpenFlow channel); the collector reads its rolling output file so
  the CSV carries victim throughput per poll. If `iperf` is unavailable, the column is written empty and the run is
  flagged — never a crash.
- **Run context / tags** — a tiny `metrics/run_context.py` reads `KNOWLEDGE_LEVEL`, `ATTACK_MODE`,
  `METRICS_CSV_PATH`, and the run start time from env; the collector stamps every row from it plus the controller's
  `salt_kind`/`interval`. P5's matrix sets these env vars per cell; a manual operator exports them before launch.

### CSV schema (frozen — P5 and P6 Tier-B read it)
Per-poll rows in `METRICS_CSV_PATH`:
`timestamp, elapsed_seconds, salt_source, knowledge_level, rotation_interval, attack_mode, link0_util, …, linkN-1_util, max_link_util, jains_index, victim_mbps, target_link, target_tx_packets, tracked_flows`.
Summary sidecar `*.summary.csv`: one row per run — the four tags + `time_to_saturation_s`,
`packets_to_saturation`, `flows_to_saturation`, `final_jains_index`, `min_victim_mbps`, `saturated` (bool).

## Interfaces exposed to P5 / P6 (freeze — downstream reads, does not redefine)
- **`config.DEFENCES_ENABLED`** and the threshold knobs — P5 toggles defences per experiment cell; the thresholds
  are frozen across cells (see tuning note).
- **The CSV + summary schema above** — P5 filters by the four tags to build the matrix; P6 Tier-B replays it.
- **`jains_index`**, **`saturation` detection**, per-link utilisation — reusable helpers P5 imports rather than
  re-deriving (single definition of "saturated", one Jain implementation).
- P4 does **not** own the experiment matrix, the two graphs, the attacker launch, rotation, or the WebSocket
  bridge (P6 Tier-B) — those consume this CSV/counters but are out of scope here.

## File plan
All paths relative to `TargetedDosColisionsAndRNGAngle/`. New unless marked **edit**.

| File | Purpose | AC | Notes |
|------|---------|----|-------|
| `testbed/controller/defences.py` | `DefencePolicy` (per-source throttle counter + meter-id assignment, clock injected); `ThrottleDecision`; pure meter/drop **spec** builders. | AC-1, AC-2 | No live-datapath calls; the controller does the sending. Dependency-free (stdlib only) so it is checkable offline. |
| `testbed/controller/ecmp_controller.py` | **edit** — when `DEFENCES_ENABLED`: consult `DefencePolicy` in `packet_in_handler` (throttle decision + per-source meter install + `OFPInstructionMeter` on the flow); add drop-flow install; `hub.spawn` the port-stats poll loop; add `EventOFPPortStatsReply` handler forwarding to the collector. | AC-1–4, AC-7 | Minimal, additive edits behind the toggle — OFF path is byte-for-byte the current behaviour. Reuse `_add_flow`/`_match_for`. |
| `testbed/metrics/__init__.py` | Package marker; re-export `MetricsCollector`, `jains_index`, `RunContext`. | — | New package, sibling of `testbed/salt/`, `testbed/attacker/`. |
| `testbed/metrics/collector.py` | `MetricsCollector`: consume port-stats samples → per-link util, max, Jain, saturation timing, packets/flows-to-saturation; write per-poll CSV + summary sidecar. Pure delta/util maths. | AC-4, AC-5, AC-7 | No OpenFlow imports — takes plain `(port_no, tx_bytes, tx_packets, t)` samples. |
| `testbed/metrics/fairness.py` | `jains_index(values: Sequence[float]) -> float`. | AC-5 | `(Σx)²/(n·Σx²)`, `1.0` on all-zero. Tiny, pure. |
| `testbed/metrics/csv_writer.py` | Run-tagged CSV row writer + summary-sidecar writer; frozen header/schema. | Done-when | Uses stdlib `csv`; no raw file formatting by hand. |
| `testbed/metrics/victim_throughput.py` | Start/parse `iperf`/`iperf3` (victim server, `bg` client); emit `(timestamp, mbps)` samples to a rolling file the collector reads. | AC-6 | The only module needing host exec; degrades to empty column if `iperf` absent. |
| `testbed/metrics/run_context.py` | `RunContext.from_env()`: `KNOWLEDGE_LEVEL`, `ATTACK_MODE`, `METRICS_CSV_PATH`, run start time. | Done-when | Supplies the two tags the controller can't know. |
| `testbed/metrics/metrics_check.py` | Standalone offline check (like P3's `collision_check.py`): feed synthetic port-stats samples, assert per-link util / Jain / saturation timing / packets-to-saturation are computed correctly; exit non-zero on mismatch. | AC-4,5,7 | The "verified" ACs as a manual checker, no test suite (project directive). |
| `testbed/config.py` | **edit** — add a `DEFENCE_*` / `METRICS_*` block: `DEFENCES_ENABLED`, `RATE_LIMIT_KBPS`, `RATE_LIMIT_BURST_KB`, `THROTTLE_MAX_CONNECTIONS`, `THROTTLE_WINDOW_SECONDS`, `THROTTLE_ACTION`, `PORT_STATS_POLL_INTERVAL_SECONDS`, `LINK_CAPACITY_MBPS`, `SATURATION_UTILISATION`, `METRICS_CSV_PATH`. Read `KNOWLEDGE_LEVEL`/`ATTACK_MODE` in `run_context`, not here. | all | Knobs as data (env-overridable, like existing P2/P3 blocks). Reuse `EGRESS_PORTS`/`N_LINKS`. |
| `testbed/README.md` | **edit** — add "Running with defences + metrics": enabling defences, the threshold rationale, the CSV location/schema, running `iperf` for victim throughput, and `metrics_check.py`. | — | Extends the P1/P2/P3 runbook. |
| `requirements.txt` | **edit** — note `iperf`/`iperf3` are **system** tools (not pip), like `hping3`. No new pip dependency (port-stats via os_ken already present; CSV via stdlib). | — | Keep existing notes. |

## Manual verification (no automated tests — project directive)
Run from `TargetedDosColisionsAndRNGAngle/`. Steps 1–2 need no Mininet/root; steps 3–5 need the live testbed
(Mininet + OVS + root), consistent with P1/P2/P3 verification.

1. **AC-4/5/7 metrics maths (offline)** — `python testbed/metrics/metrics_check.py`: feed synthetic two-poll
   port-stats samples with a known byte delta and confirm per-link utilisation, `max_link_util`, and `jains_index`
   match hand-computed values; feed a rising series that crosses `SATURATION_UTILISATION` and confirm
   time-to-saturation and packets-to-saturation latch on the correct poll. Exit non-zero on any mismatch.
2. **Jain edge cases (offline)** — confirm `jains_index([0,0,0,0]) == 1.0` (idle), `jains_index([1,1,1,1]) == 1.0`
   (perfectly fair), and a single-link concentration (`[4,0,0,0]`) returns `0.25` (= 1/N) — the single-link
   signature the attack produces.
3. **AC-1 rate limit (live)** — boot P1 topology + P2 controller with `DEFENCES_ENABLED=1`, `SALT_KIND=prng`,
   rotation off. From the `attacker` host run P3's **volumetric** mode (`run_attack.py --mode volumetric`); confirm
   the source's throughput is capped at ~`RATE_LIMIT_KBPS` via `ovs-ofctl -O OpenFlow15 dump-meters s1` /
   `dump-ports`, and that the target link does **not** saturate. Confirm a precision source at
   `PRECISION_PER_SOURCE_PPS` stays under the meter (no drops).
4. **AC-2 throttle (live)** — with the same defences on, drive many rapid connections from a single source and
   confirm the priority-20 drop flow appears (`ovs-ofctl -O OpenFlow15 dump-flows s1`) after
   `THROTTLE_MAX_CONNECTIONS`, and that a precision run spread across `ATTACK_SOURCE_IPS` never trips it (no drop
   flow installed). This is the "both fire on the flood, neither fires on precision" property.
5. **AC-4–7 end-to-end CSV (live)** — with defences on and the poller running, launch a volumetric flood and
   confirm `METRICS_CSV_PATH` fills with per-poll rows carrying all four tags + timestamp, `max_link_util` rising,
   `jains_index` falling toward `1/N`, `victim_mbps` present (with `iperf` running), and the summary sidecar
   recording `time_to_saturation_s` / `packets_to_saturation`. Repeat with `DEFENCES_ENABLED=0` to see saturation
   reached faster (baseline). *(Experiment 1's formal "defences protect the victim vs volumetric" result is P5's to
   record — here we only confirm the mechanisms fire and the CSV is well-formed and complete.)*

## Conventions
- Strict typing + PEP 8, matching P1/P2/P3: `from __future__ import annotations`, full type hints on public
  functions, frozen dataclasses for result/spec objects.
- `defences.py`, `collector.py`, `fairness.py`, `csv_writer.py`, `run_context.py` stay **importable without os_ken
  / root** (stdlib only, plain-data inputs) so `metrics_check.py` runs in any environment (as P2's parity checker
  and P3's `collision_check.py` do). OpenFlow message construction stays in `ecmp_controller.py`.
- **Defences are controller flow rules / OpenFlow meters** (epic §Conventions) — never host-level `tc`/`iptables`.
  Rate limiting = per-source meter; throttling = per-source drop/deprioritise flow.
- **CSV via stdlib `csv`**, one frozen header; no hand-rolled string formatting, no raw SQL (there is no DB here).
- Reuse `EGRESS_PORTS`, `N_LINKS`, `_add_flow`, `_match_for` — do not duplicate topology constants or flow helpers.
- The OFF path (`DEFENCES_ENABLED=0`) must leave `packet_in_handler` behaviour identical to today.

## Out of scope
- **Rotation and the salt sources** — P2 owns them; P4 only reads `salt_kind`/`interval` for CSV tagging.
- **The QRNG source / provenance** — P2 (source), P6 (display).
- **Running the experiment matrix, Experiment 1's formal result, and the two graphs** — P5. P4 provides the
  defences + collectors and proves they fire; it does not run or record the experiments.
- **The web demo and its WebSocket bridge** (P6 Tier B consumes this CSV / the port counters, but the bridge is P6).
- **The paper** (P7).
- **The Q1 blast-radius multi-victim topology** (epic §8 Q1 — a later bolt-on, not this plan).
- Any change to `hash_core.ecmp_link`, `FiveTuple`, the salt engine, or the attacker's frozen interfaces.

## Risks
- **OVS meter support** → per-source rate limiting relies on OpenFlow meters; some OVS/datapath builds implement
  meters only in the userspace datapath or reject `OFPMeterMod` on OF1.5. Mitigation: verify with
  `ovs-ofctl -O OpenFlow15 dump-meter-features s1` during step 3; if meters are unsupported, fall back to a
  per-source **queue + `OFPActionSetQueue`** with an OVS QoS min/max-rate on the egress ports (documented fallback,
  same per-source-cap semantics). Flag early — this gates AC-1.
- **Threshold mis-tuning** → if `RATE_LIMIT_KBPS`/`THROTTLE_MAX_CONNECTIONS` are set so a precision source trips
  them (or so volumetric slips under), the epic's central claim is unfalsifiable. Mitigation: pick defaults with an
  order-of-magnitude margin on both sides, verify both directions in steps 3–4, then **freeze** them for P5.
- **Port-stats poll interval vs saturation resolution** → too coarse a poll makes time/packets-to-saturation
  imprecise (P5 Exp 5's x-axis). Mitigation: default `PORT_STATS_POLL_INTERVAL_SECONDS` small (e.g. 0.5–1 s),
  configurable; document the sampling granularity as the metric's resolution.
- **Meter/flow accounting under rotation** → when rotation reinstalls flows (P2), per-source meters must survive
  (they key on `src_ip`, not the flow) and the throttle counter must not double-count re-resolved flows.
  Mitigation: install meters once per source (idempotent by `meter_id_for`), and have `note_flow` count only
  genuinely new `(src_ip, 5-tuple)` pairs, not rotation-driven re-installs.
- **`iperf` availability / version skew** → `iperf` vs `iperf3` output formats differ. Mitigation: detect which is
  present, parse accordingly, and degrade to an empty `victim_mbps` column (flagged) rather than crashing the run.
- **Poller load on the emulation** → very frequent port-stats polling can perturb Mininet timing. Mitigation: keep
  the interval configurable and document a sane default; the poll is one request/reply per interval, not per port.

## Open questions — RESOLVED (2026-07-26, all defaults accepted)
- [x] **OQ-1 (throttle unit — connections vs requests).** **RESOLVED:** throttle on **per-source new-flow count**
  (catches connection floods and the precision-vs-source axis cleanly); rely on the **rate-limit meter** to catch
  the single-flow high-byte-rate volumetric case — "both defences stop the volumetric flood" is satisfied by the two
  mechanisms jointly, with the volumetric control shaped (many rapid short connections from one source) so the
  throttle also visibly fires. Document which mechanism catches which flood shape. *Affects `defences.py`, P5 Exp 1
  shaping.*
- [x] **OQ-2 (CSV granularity — per-poll rows vs per-run summary).** **RESOLVED:** write **both** — per-poll rows in
  `METRICS_CSV_PATH` and a per-run `*.summary.csv` sidecar — from the one collector, so P5 never re-derives
  saturation from raw rows. *Affects `collector.py`, `csv_writer.py`, P5 ingestion.*
- [x] **OQ-3 (link capacity for utilisation).** **RESOLVED:** `LINK_CAPACITY_MBPS` is a config constant that P1's
  topology `TCLink` bandwidth is set to match (single source of truth); note the coupling in both configs. If P1
  currently sets no `bw`, flag to P1 to pin one so utilisation is meaningful. *Affects `config.py`, possibly P1
  topology.*
- [x] **OQ-4 (collector lives in the controller process).** **RESOLVED:** the `MetricsCollector` is instantiated
  **by** `ECMPController` and fed from the port-stats reply handler (pure-maths core stays in `metrics/`), not a
  separate OF app — one OF connection, no second controller. `victim_throughput.py` stays out-of-band (host exec).
  *Affects `ecmp_controller.py`, `collector.py`.*
- [x] **OQ-5 (deprioritise vs drop for throttle).** **RESOLVED:** default `THROTTLE_ACTION="drop"` (unambiguous
  "throttle fired" signal for Experiment 1), with `"deprioritise"` (install the flow at priority 1) available as a
  config alternative. *Affects `defences.py`, `config.py`.*

## Notes for `/implement-feature` (downstream)
- Gate **every** defence and poll behaviour on `config.DEFENCES_ENABLED`; the OFF path must be byte-for-byte the
  current controller behaviour so P3's runs and the "defences off" experiment cells are unaffected.
- Keep `defences.py` / `metrics/*` importable **without** os_ken or root so `metrics_check.py` runs anywhere; put
  all `OFPMeterMod`/`OFPFlowMod`/`OFPPortStatsRequest` construction in `ecmp_controller.py`.
- **Freeze the CSV header and the four tags exactly** as in §CSV schema — P5's matrix and P6 Tier-B replay parse it
  positionally/by-name; a renamed or dropped column silently breaks them (epic §4).
- **Tune the thresholds once and freeze them** — verify both directions (precision under, volumetric over) in
  manual steps 3–4 before handing to P5; a per-experiment re-tune invalidates the central claim.
- Reuse `EGRESS_PORTS`/`N_LINKS`/`_add_flow`/`_match_for` and the `hub.spawn` pattern already in the controller;
  do not add a second OF connection or duplicate topology constants.
- Emit `salt_source`/`rotation_interval` from the controller's own `salt_kind`/`ROTATION_INTERVAL_SECONDS`, and
  `knowledge_level`/`attack_mode` from `RunContext.from_env()` — do not try to infer the latter two inside the
  controller.

## Post-implementation notes

Built exactly per the file plan: `testbed/controller/defences.py` (`DefencePolicy` — sliding-window throttle
counter deduped by `(src_ip, five_tuple)`, stable per-source meter-id assignment from the last IP octet);
`testbed/metrics/{__init__,fairness,csv_writer,run_context,collector,victim_throughput,metrics_check}.py`; a new
`config.py` P4 block (`DEFENCES_ENABLED`, `RATE_LIMIT_KBPS=1000`, `RATE_LIMIT_BURST_KB=100`,
`THROTTLE_MAX_CONNECTIONS=20`, `THROTTLE_WINDOW_SECONDS=5`, `THROTTLE_ACTION=drop`,
`PORT_STATS_POLL_INTERVAL_SECONDS=0.5`, `LINK_CAPACITY_MBPS=10`, `SATURATION_UTILISATION=0.9`,
`METRICS_CSV_PATH`, `VICTIM_THROUGHPUT_PATH`); minimal additive edits to `ecmp_controller.py` (meter/throttle hook
in `packet_in_handler`, `_ensure_meter`/`_install_throttle_drop`/`_build_metrics_collector`/`_port_stats_poll_loop`/
`_request_port_stats`/`port_stats_reply_handler`, `_add_flow` extended with an optional `meter_id`).

`metrics_check.py` (offline, no os_ken/root) passes all three checks — utilisation/max-link-util against a
hand-computed delta, Jain's edge cases (`1.0`/`1.0`/`0.25`), and saturation latching on the correct poll of a
rising series. `DefencePolicy` was additionally smoke-tested standalone (throttle triggers past the limit,
rotation-style re-note of an already-seen flow doesn't double-count, meter ids are stable per source).

**Not verified in this session** (no live Mininet/OVS/root environment available): manual steps 3–5 (AC-1 rate
limit, AC-2 throttle, AC-4–7 end-to-end CSV against a real OVS datapath) from §Manual verification. The threshold
defaults are documented with their margin rationale in `config.py` and the README but have **not** been confirmed
live against a real OVS meter implementation — the plan's own Risk ("OVS meter support") and the
"do not re-tune per experiment" rule both still apply once P5/an operator runs steps 3–5 for the first time.
`iperf3`'s `--json-stream` JSON shape in `victim_throughput.latest_mbps` was written from the documented format,
not confirmed against a real `iperf3` binary in this session.
