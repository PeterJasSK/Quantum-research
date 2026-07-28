# Plan 10 — Flow-level simulation of the experiment matrix (unblock the paper without a live Mininet host)

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source:** new (post-P9, **supersedes P9 Deliverable A** — the
live Mininet run — after `plans/investigation-1.md` established that path is environment-blocked) · **Priority:** `[MUST]`
**Status:** Complete (2026-07-27; QRNG cell resolved 2026-07-28 — see §Post-implementation notes; one item deferred: local
`pdflatex` compile only) · **Depends on:** P2/P3/P4 (Complete, frozen — imported verbatim), P5 (code Complete —
`testbed/experiments/matrix.py` cells + all of `testbed/analysis/` are **reused unchanged**), P8 (Complete — the precedent:
a self-contained flow-level simulator over the real frozen hash, no Mininet). **Gates:** closes the same targets P9 did —
`thesis/thesis.tex`'s three `% TODO(P5)` blocks and plan-7's Manual Verification items 1, 3, 4, 10 — plus produces the P6
Tier-B replay subset that both P5's live run and P9 left unbuilt.

> Pick up with `/plan-feature plans/plan-10-flow-level-simulation-results.md` after approval, or straight into
> `/implement-feature` once approved. Read `plans/plan-5-experiments-graphs.md` in full first (this plan drives the same
> matrix and the same analysis layer P5 built — it replaces only the *transport*, not the analysis), then
> `plans/investigation-1.md` (why the live path is abandoned as the results source) and `thesis/thesis.tex`'s S3-A / S5 / S6 /
> §Limitations so the honesty reframe (Deliverable C) matches the surrounding register.
> **No automated tests** (project directive). Correctness is `testbed/analysis/analysis_check.py` (unchanged, already passes)
> plus the manual verification below run against the new simulator instead of a live Mininet/OVS stack.

## Goal
Unblock the paper by producing the five-experiment matrix's results from a **self-contained, deterministic flow-level
simulator** that executes the real, frozen mechanism code — the SHA-256 hash core, the collision crafter, the seed-space
brute-forcer, the three salt sources (including the live QRNG endpoint), the defence policy, and the metrics collector —
and models **only the packet transport and link byte-counters** that Mininet + Open vSwitch + scapy previously provided.
The simulator's output is **byte-schema-identical** to the P4/P5 CSVs, so `testbed/analysis/` (`success.py`,
`rotation_threshold.py`, `graphs.py`, `analysis_check.py`) and the P6 web demo consume it **unchanged**. This plan then
copies the two figures into `thesis/`, fills `thesis.tex`'s three `% TODO(P5)` blocks with real numbers traced to the
produced CSVs, and — the one new obligation versus P9 — **honestly reframes the methodology prose** so the paper describes
the flow-level simulation it actually ran rather than a Mininet emulation it did not.

## Why this pivot is legitimate, not a shortcut (the credibility argument)
This is the crux the thesis defence turns on, so it is stated explicitly and must survive into the paper's own prose:

1. **The epic already blesses simulation.** epic §3.4 is titled *"Simulated topology is sufficient — with one honest scale
   caveat"* and states all five experiments are *"mechanism, not scale questions"* — the hash/salt/bucket-selection/defence
   logic under test is identical whatever carries the packets. The quantities reported are **ratios** (precision-vs-volumetric
   cost, weak-PRNG-vs-rotating-CSPRNG outcome) that are scale-invariant by construction (`thesis/thesis.tex:235-242`).
2. **P8 is a shipped precedent.** Plan-8 (Status: Complete) already delivered exactly this pattern — a self-contained
   flow-level entropy/polarization study (`testbed/topology/fabric.py` + `testbed/topology/polarization_check.py`) that reuses
   the real frozen hash, deliberately skips live Mininet, and is treated as valid because correctness rests on the real hash
   plus an offline gate, not on packet transport. Plan-10 applies the same discipline to the attack/defence matrix.
3. **Nothing security-critical is simulated.** The parts a reviewer would attack are all real, unchanged:
   - the **hash** is `testbed/hash_core.py:14`'s real SHA-256 `ecmp_link`, imported (epic §3.5: *"the attacker uses the real
     hash, not a copy"*);
   - the **collision set** is crafted by the real `CollisionCrafter.craft` against that hash (`testbed/attacker/collision.py:26`);
   - the **reconstruction cost** (Exp 5's timing anchor) is the real `SeedBruteForcer.search` running actual CPU work and
     measuring real `time.perf_counter()` wall-clock (`testbed/attacker/reconstruct.py:43-67`) — it is measured, not modelled;
   - the **QRNG null result** is measured by drawing a real salt from the live `api.qeaas.eu` endpoint and recording its real
     signed provenance, then running it through the identical pipeline as the CSPRNG salt;
   - the **utilisation / Jain / saturation / summary maths** is the real `MetricsCollector` (`testbed/metrics/collector.py`),
     fed the same `(port_no, tx_bytes, tx_packets, t)` sample shape it was explicitly designed to accept offline
     (`collector.py:6-9`, `95-100`).
   Only the transport — offered load → per-link byte accumulation over time — is modelled, and that model is deterministic,
   documented, and its parameters are the same `config.py` constants the live testbed would have used.
4. **The mechanism outcomes are logical consequences of the real hash, not artefacts of the model.** Whether the precision
   attacker evades the caps, whether a rotation disperses its crafted set, and whether QRNG ≡ CSPRNG are all decided by the
   real hash arithmetic and the real defence policy — the transport model cannot make a false claim true, it can only carry
   or drop the load the real components produce.

## Non-negotiable ground rules (inherited + one addition)
- **Never fabricate a number** (epic + P9). A cell that cannot be computed cleanly is marked `skipped-with-reason` in the CSV
  and the prose — never estimated, interpolated, or invented to make S5/S6 look complete.
- **Never re-implement the mechanism** (epic §3.5, hard rule). The hash, collision crafter, seed brute-forcer, salt sources,
  defence policy, metrics collector, and CSV schema are **imported verbatim** from P2/P3/P4. A silent re-implementation drift
  here invalidates Experiments 2–5. The transport model is the **only** new mechanism, and its every parameter is stated in
  code and in the paper.
- **Honesty about what ran.** Because Mininet/OVS is not executed, no sentence in the paper may claim it was. Deliverable C
  reframes the methodology to describe the flow-level simulation truthfully (see OQ10-1).

## How this resolves `plans/investigation-1.md`
The investigation tracked eleven environment/dependency blockers (conda-vs-system `python3`, PEP 668, `os_ken` install, stale
OVS bridges) culminating in the real blocker — issue #10/#11: `testbed/attacker/traffic.py:71-99`'s scapy L3 `send()` does a
fresh route + ARP lookup per packet inside the Mininet netns, and when ARP never resolves the 500-packet send blocks for the
full ARP timeout *per packet*, an effective hang. **This plan is the resolution: the live path is abandoned as the results
source.** Rationale:
- The scapy-hang could be fixed (L2 `sendp()` with a pre-resolved dest MAC + static ARP), but that keeps the root/Mininet/OVS
  requirement, the env fragility catalogued in investigation-1 (#1–#9), the teardown-leakage risk (P5 Risks), and — worst for a
  thesis — **emulation jitter near the saturation edge** (P5 Risks: *"Non-determinism in success classification"*), the exact
  thing that makes a borderline cell un-reproducible.
- The simulator is **deterministic, reproducible, root-free, cross-platform, and orders of magnitude faster**, and per epic
  §3.4 is *sufficient* for the mechanism claims. It also makes explicit what the live path left implicit: the scapy sender
  never defined a sustained offered-load model at all (it sends each crafted tuple once), so saturation in the live path
  depended on undocumented OVS/TCLink dynamics that were never actually validated (the live run never completed).
- **The Mininet path is deleted, not retained (OQ10-4 resolved: cut it).** This study is positioned as a **preliminary
  flow-level study**; the *next* implementation is a **bare-metal** one (OQ10-1 resolved), so Mininet/OVS/scapy/os_ken is cut
  and forgotten — not framed as a "confirmation" rung. `testbed/experiments/harness.py`, `testbed/experiments/run_experiments.py`,
  the Mininet topology builders, the os_ken live controller, the scapy traffic sender, the `iperf3` victim reader, and
  `plans/investigation-1.md` are removed (see File plan). Only the pure helpers those files re-export and the sim reuses
  (`random_five_tuples`, `TrafficMode`, `salt_handoff`, `matrix`, and every P2/P3/P4 mechanism module) are preserved. The
  future-confirmation story in the paper is the bare-metal build, replacing the old physical-10G/Mininet framing entirely.

## Deliverables

### Deliverable A — the flow-level simulator + the run (new code)
A new, self-contained simulation backend under `testbed/sim/` (OQ10-2) that, given a `testbed/experiments/matrix.py`
`ExperimentCell` (reused unchanged), produces the same per-poll CSV + `*.summary.csv` sidecar a live cell would, then runs
`--exp 1` through `--exp 5` and `--exp all` to populate `results/**` and render both graphs. Requires **no root, no Mininet,
no scapy, no os_ken** — only the analysis deps (`pandas`/`matplotlib`) plus network access for the QRNG cells.

### Deliverable B — figures into `thesis/` (same as P9 Deliverable B)
Copy (do not re-plot — a data/caption change means re-rendering `graphs.py` and re-copying, per epic §D-figures):
- `results/graph1_success_matrix.png` → `thesis/graph1_success_matrix.png`
- `results/graph2_rotation_threshold.png` → `thesis/graph2_rotation_threshold.png`

### Deliverable C — fill `thesis.tex`'s three `% TODO(P5)` blocks **and** reframe the methodology honestly
The three fill-ins are identical in shape to P9 Deliverable C:
1. **§Experimental Results (S5)** (`thesis/thesis.tex:328-347`, currently a placeholder + commented Graph 1 figure) — a
   `booktabs` table reporting per matrix cell `saturated`, `min_victim_mbps`, `final_jains_index`, and whether the defence
   fired, for Exp 1–4; state Exp 4's null result numerically (the 4b-vs-4c Jain/throughput delta, quoted); uncomment and
   finalise the Graph 1 figure + caption against the rendered PNG.
2. **§Rotation-Frequency Specification (S6), empirical half** (`thesis/thesis.tex:361-395`) — the analytic `T_bf = S/2r`
   derivation (`thesis.tex:369-378`) stays untouched (frozen prose); append the Exp 5 empirical confirmation: measured
   `elapsed_seconds`/`attempts` from the real `SeedBruteForcer`, the measured crossover interval, and how closely it tracks
   the analytical `T_bf`; uncomment and finalise the Graph 2 figure + caption.
3. **Numeric traceability** — every number added traces to a specific `results/*.summary.csv` row, kept implicit in precise
   wording (per plan-7 MV item 4).

The **new, plan-10-specific** part of Deliverable C — the honesty reframe (OQ10-1 resolved: **preliminary flow-level study,
bare-metal next**). The current draft repeatedly asserts a Mininet/OVS emulation that will not be run. **Every** Mininet /
Open vSwitch / emulation mention is removed and reworded to describe the flow-level simulation truthfully and to name the
study as preliminary, with a bare-metal implementation as the explicit next step. Lines to sweep:
- **Abstract** (`thesis/thesis.tex:47-49`): *"…on a controller-managed ECMP fabric (Mininet/Open vSwitch/SDN controller)…"* →
  the flow-level simulation over the real frozen hash/salt/defence implementation; drop "Mininet/Open vSwitch" entirely.
- **§Research Methodology / Experimental Design** (`thesis/thesis.tex:195-200`): *"We built a controller-managed ECMP testbed
  in Mininet with Open vSwitch…"* → describe the implemented controller/hash/salt/rotation/defence stack (all real, all run)
  and state that results come from driving those real components through a deterministic flow-level transport model; **no**
  Mininet retained-artefact language — Mininet is cut.
- **§III-C Scale Caveat** (`thesis/thesis.tex:235-242`): reword the "identical in Mininet/OVS emulation and on physical 10G
  silicon" argument to "identical in this flow-level simulation and on a bare-metal implementation" — the scale-invariance
  argument is unchanged, only the two endpoints of the ladder change.
- **§Limitations** (`thesis/thesis.tex:483-494`): the "emulated in Mininet/OVS rather than physical silicon" limitation
  becomes *this is a preliminary flow-level study; a bare-metal implementation is the direct next step*, reusing the existing
  scale-invariance argument. Any remaining "Mininet"/"emulation" token is removed.
- **§Future Work** (`thesis/thesis.tex:496-500`): the "physical 10G hardware confirmation run" becomes the **bare-metal
  implementation** as the primary next work (folding the old physical-hardware rung into it); drop the Mininet-confirmation
  concept.
- Add a **one-sentence explicit statement** in §Methodology that the security-critical components (hash, collision craft,
  seed reconstruction with real measured timing, live QRNG draw, defence policy, metrics maths) are executed for real and
  only the transport is modelled — the Deliverable-A credibility argument compressed to one honest line.
- **Grep gate:** after editing, `grep -in "mininet\|open vswitch\|ovs" thesis/thesis.tex` must return nothing (the paper makes
  no claim about a stack that was not run).

### Deliverable D — the P6 Tier-B replay subset (was blocked on the live run)
Generate the epic §8 Q4 replay subset the P6 web demo's Tier B reads — `web/public/replay/*.json` (three-scene runs + one QRNG
provenance run + the full Exp 5 rotation-interval sweep; **blind skipped**), mapping the P4 CSV columns
`link{i}_util`/`max_link_util`/`jains_index`/`victim_mbps` (plan-6 L145, L171). This unblocks P6 Tier B, which today throws
"not wired" stubs (plan-6 L245-250). The QRNG provenance JSON carries the **real** receipt drawn during Deliverable A, replacing
plan-6's labelled placeholder (plan-6 L251-253).

### Deliverable E — close plan-7's remaining Manual Verification items (same as P9 Deliverable D)
- **Item 1 (compiles clean):** run `pdflatex thesis/thesis.tex` twice, no unresolved `\ref`/`\cite`, no missing-figure errors.
- **Item 3 (both graphs render):** satisfied by Deliverable B.
- **Item 4 (numeric traceability):** satisfied by Deliverable C.
- **Item 10 (venues named):** add the one-line ACM ANCS / IEEE ICNP / IFIP Networking submission note near the Conclusion
  (P9 OQ9-2 resolution, carried forward).

## Design

### 1. The transport model (`testbed/sim/transport.py`) — the one new mechanism
A pure, deterministic function from a set of offered flows + a salt-over-time schedule to a stream of per-link byte counters.
No scapy, no OpenFlow, no root. Documented as *the* model the paper stands on. Inputs and behaviour:

- **Offered flows.** Each flow is a `FiveTuple` plus a sustained offered rate. The precision attacker's flows come from the
  real `CollisionCrafter.craft(...)`; the volumetric control is a single fixed flow (matching `attack.py:72-73`'s
  `[five_tuples[0]] * count` collapse); the blind baseline is the real `random_five_tuples(...)`
  (`testbed/attacker/traffic.py:18`).
- **pps → bits/sec** via a single explicit constant `PACKET_SIZE_BYTES` (new config knob, §3 below), so every rate in the
  model is auditable arithmetic, not a hidden assumption.
- **Defences applied with the real policy.** For each flow's `src_ip`/`flow_key`, call the real
  `DefencePolicy.note_flow(...)` / `meter_id_for(...)` (`testbed/controller/defences.py:40,61`) when `defences_enabled`:
  a source over `THROTTLE_MAX_CONNECTIONS` in the window has its flows dropped (or deprioritised per `THROTTLE_ACTION`), and a
  source's aggregate offered rate is capped at `RATE_LIMIT_KBPS` (the meter). The frozen P4 thresholds are used **unchanged**;
  the model never re-tunes them (P4 tuning note, P5 Conventions).
- **Link assignment with the real hash.** Each surviving flow is placed on link `ecmp_link(flow, active_salt(t), N_LINKS)`
  (`hash_core.py:14`). Per-link offered load = sum of the rates of flows currently mapped there, capped at
  `LINK_CAPACITY_MBPS`. Utilisation, Jain, and saturation are **not** computed here — they are produced by the real
  `MetricsCollector` fed the samples this model emits (see §2), so there is exactly one definition of each.
- **Output.** For each poll tick (`PORT_STATS_POLL_INTERVAL_SECONDS`) over `RUN_DURATION_SECONDS`, emit
  `(port_no, tx_bytes_cumulative, tx_packets_cumulative, t)` per egress port — the exact tuple shape
  `MetricsCollector.on_port_stats` consumes (`collector.py:95-100`).

### 2. The simulation harness (`testbed/sim/sim_harness.py`) — parallel to `experiments/harness.py`, root-free
Per `ExperimentCell` (imported from `testbed/experiments/matrix.py` unchanged):
1. **Mint the salt schedule.** Call the real `salt_source(cell.salt_kind)` (`salt/sources.py:51`) to mint the active salt; if
   `cell.rotation_interval > 0`, build a schedule that mints a fresh salt every interval across `RUN_DURATION_SECONDS`. Log
   each via the real `rotation_log` writer (`salt/rotation_log.py:12`), including the OQ-1 initial-salt event, so the salt
   handoff and provenance path are byte-identical to the live controller's.
2. **Resolve the attacker's salt for real.** `full` → hand off the logged active salt (real `salt_handoff` read); `partial` →
   run the real `SeedBruteForcer.search` against a `LocalOracle` on probe tuples (`reconstruct.py`, `oracle.py`) — real CPU,
   real `elapsed_seconds`; `blind` → no salt. This is the real `resolve_salt` (`knowledge.py:27`), invoked as `run_attack`
   invokes it (`attack.py:47-55`).
3. **Craft for real.** Real `CollisionCrafter.craft(...)` against the resolved salt (`collision.py:26`).
4. **Drive the transport model** (§1) over the run duration with the salt schedule (so a rotation mid-run re-hashes the
   crafted set and disperses it — the Exp 4b/4c/5 mechanism, computed by the real hash).
5. **Feed the real collector.** Construct the real `MetricsCollector` with the cell's `RunContext`/tags
   (`metrics/run_context.py`, `metrics/collector.py:35`) and a `victim_mbps_reader` backed by the §4 victim model; push each
   poll's samples through `on_port_stats(...)`; it writes the per-poll rows and the `*.summary.csv` sidecar via the real
   `CsvWriter` (`metrics/csv_writer.py`). **Zero change to the collector or the schema.**
6. **Idempotent, deterministic.** No teardown needed (no processes); a fixed `PRNG_SEED` and a fixed model make a cell's CSV
   reproducible bit-for-bit (verified in Manual Verification step 7), which the live path could never guarantee.

### 3. Attack offered-load operating point (`testbed/config.py`, new sim block)
The live path never defined a sustained offered-load model, so the simulator must — explicitly, with margins, the way P4 tuned
its thresholds. The **internal-consistency inequalities** the central claim (Exp 2–3: precision evades both caps yet saturates)
requires, all computed from existing frozen constants:
- **saturate:** aggregate offered load on the target link ≥ `SATURATION_UTILISATION · LINK_CAPACITY_MBPS` (= 9 Mbps at the
  defaults);
- **evade the meter:** each source's offered rate ≤ `RATE_LIMIT_KBPS` (= 1 Mbps);
- **evade the throttle:** each source's distinct-flow count in the window ≤ `THROTTLE_MAX_CONNECTIONS` (= 20);
- therefore **≥ 9 compliant sources** are needed; the frozen `ATTACK_SOURCE_IPS` pool has 16 (`config.py:83`), giving clear
  margin (e.g. 16 sources × ~15 flows × a per-flow rate summing to ~0.6 Mbps/source → ~9.6 Mbps aggregate, each source under
  both caps).

The plan adds two explicit, env-overridable constants — `PACKET_SIZE_BYTES` (the pps↔bps bridge) and a precision per-flow
sustained rate (or its derivation from the inequalities above) — documented as the attack's stated operating point, with a
one-line note in the paper that the mechanism claim is invariant to the exact point as long as the three inequalities hold.
The volumetric control is a single source offering above the meter (e.g. `VOLUMETRIC_PPS`×`PACKET_SIZE_BYTES` ≈ 8 Mbps → the
real meter caps it to 1 Mbps → ~10% util → not saturated, defence fired — reproducing Exp 1).
**If the frozen P3/config values turn out internally inconsistent** (cannot both evade caps and saturate), that is surfaced to
the developer as a finding — never silently papered over with numbers chosen to fake the claim (ground rule 1).

### 4. Victim-throughput model (replaces `iperf3`)
The live path measured victim throughput out-of-band via `iperf3` (`metrics/victim_throughput.py`). The simulator supplies the
same `victim_mbps_reader` callable the collector already accepts (`collector.py:61,131`) with a documented contention model: the
victim's background flow shares the target link; its throughput is its fair share of residual capacity after the attacker's
surviving load, collapsing toward zero as the target link saturates and returning to full `LINK_CAPACITY_MBPS` when no attack /
after a rotation disperses the crafted set. This is the one place the model asserts user-visible damage; it is stated plainly
and drives `min_victim_mbps` into the same `success.py` predicate P5 froze (`saturated AND min_victim_mbps ≤ VICTIM_COLLAPSE_MBPS`).

### 5. QRNG cells — real live draw, real provenance (unchanged from the live plan)
The `qrng` cells call the real `salt/qrng_client.py` against `api.qeaas.eu` (needs `QEAAS_API_KEY`), record the real
provenance (`request_id`/`entropy_epoch`/timestamp/Ed25519 receipt), and on `503 low_quantum_entropy`/`429` degrade/retry via
the existing client, marking a cell that never gets provenance `skipped-with-reason` (P5 Risks, carried forward). The QRNG null
result is thus **measured**, not asserted: the real QRNG salt runs through the identical §1–§4 pipeline as the CSPRNG salt and
must land in the same summary outcome within noise.

### 6. Run CLI (`testbed/sim/run_sim.py`) — mirrors `run_experiments.py`
`--exp {1,2,3,4,5,all}` selects the same `matrix.py` cells, iterates them through `sim_harness.py`, prints per-cell PASS/FAIL
against the cell's *expected* summary result (Exp 2 expects `saturated=True` **and** no meter/throttle fire; Exp 4 expects
4a-sat, 4b/4c-not-sat-and-numerically-close), then hands the CSVs to the unchanged `testbed/analysis/graphs.render_graphs`
(or stops at data with `--no-graphs`). It sets `KNOWLEDGE_LEVEL`/`ATTACK_MODE` per cell (the two tags the collector cannot
derive), exactly as `run_experiments.py:200` does. It does **not** re-tune thresholds, re-mint salts outside the real source,
or touch upstream code.

## Interfaces consumed / produced (freeze — nothing downstream is redefined)
- **Consumed unchanged:** `hash_core.ecmp_link`, `attacker/{collision,knowledge,oracle,reconstruct}.py`,
  `salt/{sources,rotation_log,qrng_client}.py`, `controller/defences.py`, `metrics/{collector,csv_writer,fairness,run_context}.py`,
  and `experiments/matrix.py`'s `ExperimentCell`/`MATRIX`. Zero edits to any of these.
- **Produced identically to P5:** `results/<exp>/<cell_id>.csv` + `.summary.csv` (frozen `per_poll_header`/`SUMMARY_HEADER`,
  `csv_writer.py:13-43`), `results/graph1_success_matrix.{png,svg}`, `results/graph2_rotation_threshold.{png,svg}`, and the
  Q4 replay subset — so `analysis/*`, the two figures P7 embeds, and the P6 Tier-B reader all work with no change.

## File plan
All paths relative to `TargetedDosColisionsAndRNGAngle/`. New unless marked **edit**. (Package location per OQ10-2.)

| File | Action | Notes |
|------|--------|-------|
| `testbed/sim/__init__.py` | **Create** | New package, sibling of `testbed/experiments/`. Re-export the harness + CLI entry. |
| `testbed/sim/transport.py` | **Create** | §1 flow-level transport model: offered flows + salt-schedule → per-poll `(port, tx_bytes, tx_packets, t)` samples. Imports the real `ecmp_link` + `DefencePolicy`; no scapy/OpenFlow. |
| `testbed/sim/victim_model.py` | **Create** | §4 contention model supplying the collector's `victim_mbps_reader`. Replaces `iperf3` only. |
| `testbed/sim/sim_harness.py` | **Create** | §2 per-cell driver: real salt-schedule + real `resolve_salt`/craft → transport → real `MetricsCollector` → real `CsvWriter`. Deterministic, root-free. |
| `testbed/sim/run_sim.py` | **Create** | §6 CLI `--exp {1..5,all}`, per-cell PASS/FAIL vs expected, then unchanged `analysis.graphs.render_graphs`. |
| `testbed/sim/replay_export.py` | **Create** | Deliverable D: emit the Q4 replay subset `web/public/replay/*.json` from the produced CSVs (+ the real QRNG receipt). |
| `testbed/config.py` | **edit** | New sim block: `PACKET_SIZE_BYTES`, the precision per-flow-rate constant/derivation (§3), `SIM_RESULTS_DIR` if separated. Reuse every existing constant; redefine none. |
| `results/graph1_success_matrix.{png,svg}` | **Create (via sim run)** | Deliverable A. Gitignore raw per-cell CSVs per P5 OQ-5; commit figures + replay subset only. |
| `results/graph2_rotation_threshold.{png,svg}` | **Create (via sim run)** | Deliverable A. |
| `web/public/replay/*.json` | **Create (via sim run)** | Deliverable D — the P6 Tier-B replay subset. |
| `thesis/graph1_success_matrix.png` | **Create (copy)** | Deliverable B. |
| `thesis/graph2_rotation_threshold.png` | **Create (copy)** | Deliverable B. |
| `thesis/thesis.tex` | **edit** | Deliverable C: fill the three `% TODO(P5)` blocks; reframe the abstract clause + §III-A + §Limitations honestly (OQ10-1); add the venue note (Deliverable E item 10). No other section touched. |
| `testbed/README.md` | **edit** | Replace the live-run runbook with a "Running the flow-level simulation" one; state plainly all results are simulation-derived and this is a preliminary study (bare-metal next). Remove Mininet/OVS/iperf3 prerequisites. |
| `plans/plan-7-writeup.md` | **edit** | Flip Manual Verification items 1/3/4/10 to confirmed with file:line evidence; update Status to data-complete via simulation. |
| `plans/plan-9-run-experiments-fill-paper.md` | **edit** | Add a Status note: Deliverable A superseded by plan-10 (simulation); B/C/D fulfilled here; Mininet path deleted. |

### Deletions (OQ10-4 — Mininet cut and forgotten)
Delete the live-emulation path entirely. **Before deleting each, confirm no kept module imports it** (the pure helpers below are
preserved *because* the sim reuses them). If a kept module imports a to-be-deleted symbol, that symbol is first moved to a pure
module, not left dangling.

| File | Action | Notes |
|------|--------|-------|
| `testbed/experiments/harness.py` | **Delete** | Mininet subprocess lifecycle — the investigation-1 blocker lives here. |
| `testbed/experiments/run_experiments.py` | **Delete** | Live CLI, replaced by `testbed/sim/run_sim.py`. |
| `testbed/experiments/salt_handoff.py` | **Keep** (move if needed) | Pure rotation-log read reused by the sim harness. |
| `testbed/experiments/matrix.py`, `__init__.py` | **Keep** | The cell definitions the sim iterates — pure data. |
| `testbed/topology/run_topo.py`, `ecmp_topo.py`, `fattree_topo.py` | **Delete** | Mininet/OVS topology builders. |
| `testbed/topology/fabric.py`, `polarization_check.py` | **Keep** | P8's offline flow-level study — no Mininet, Complete, independent. |
| `testbed/controller/run_controller.py`, `ecmp_controller.py` | **Delete** | os_ken live controller (the SIGINT/`HubThread.kill` bug in investigation-1 #6). |
| `testbed/controller/defences.py`, `__init__.py` | **Keep** | Pure `DefencePolicy` — reused by the transport model. |
| `testbed/attacker/traffic.py` | **Delete scapy portion; keep pure** | Remove `send_flows`/`_build_packet`/`_send_*` (scapy — the investigation-1 hang). Preserve `random_five_tuples`/`TrafficMode` (pure blind fallback) — move to a scapy-free module (e.g. `attacker/flows.py`) so `attack.py`/the sim import them without scapy. |
| `testbed/attacker/run_attack.py` | **Delete** | scapy CLI on the Mininet `attacker` host. |
| `testbed/attacker/attack.py` | **Keep, edit** | Its `send_flows` call is the live transport; the sim uses `resolve_salt`+`craft` directly, so drop the scapy import path (or leave `attack.py` unused by the sim and delete if nothing imports it). |
| `testbed/metrics/victim_throughput.py` | **Delete** | `iperf3` subprocess reader — replaced by `testbed/sim/victim_model.py`. |
| `plans/investigation-1.md` | **Delete** | Live-run blocker log — obsolete once the live path is cut. |
| `rotation_events.jsonl` (repo root) | **Delete** | Stray live-run artefact. |

## Manual verification (no automated tests — project directive)
Run from `TargetedDosColisionsAndRNGAngle/`. **No root/Mininet required for any step.** QRNG cells need `QEAAS_API_KEY`.
1. `python testbed/analysis/analysis_check.py` exits 0 — the unchanged offline analysis path still classifies the synthetic
   success/fail rows and recovers the planted rotation crossover (confirms the analysis layer is untouched).
2. `python testbed/sim/run_sim.py --exp 1` — summary row shows `saturated=False`, healthy `min_victim_mbps`, and the real
   `DefencePolicy` recorded the volumetric source as metered/throttled. **Defences fire.**
3. `--exp 2` then `--exp 3` — `saturated=True`, `min_victim_mbps` collapsed below `VICTIM_COLLAPSE_MBPS`, and **no** source is
   over the meter or the throttle (assert against the `DefencePolicy` state, the sim analogue of "no meter/throttle drop flow").
   The central claim.
4. `--exp 4` — 4a `saturated=True`; 4b (csprng+rotation) and 4c (qrng+rotation) both `saturated=False` and their
   `final_jains_index`/`min_victim_mbps` **numerically indistinguishable** (quote the delta); 4d (clean background, all three
   sources) high Jain + full victim throughput. The qrng cell recorded a real Q-EaaS receipt (or is `skipped-with-reason`).
5. `--exp 5` — `time_to_saturation_s`/`packets_to_saturation` rise as the interval shortens; the empirical crossover lands near
   the analytical `T_bf` computed from the **real measured** `reconstruction.elapsed_seconds`/`attempts`.
6. `--exp all` then confirm `results/graph1_*.svg` (3×3 grid, null result visible) and `results/graph2_*.svg` (curve with both
   thresholds) render, and `web/public/replay/*.json` exists for P6 Tier B.
7. **Determinism check (sim-only, new):** re-run any non-QRNG cell with the same `PRNG_SEED` and confirm the produced
   `.summary.csv` is byte-identical — the reproducibility the live path could not offer.
8. **Internal-consistency check (§3):** confirm the recorded per-source offered rates in Exp 2–3 are each ≤ `RATE_LIMIT_KBPS`
   and each source's flow count ≤ `THROTTLE_MAX_CONNECTIONS`, while the aggregate ≥ `SATURATION_UTILISATION·LINK_CAPACITY` — i.e.
   the claim is not made true by an inconsistent operating point.
9. `pdflatex thesis/thesis.tex` twice — clean PDF, no unresolved refs/cites, no missing figures; re-read plan-7's MV checklist
   and confirm items 1/3/4/10 pass; confirm no sentence in the paper claims a Mininet/OVS run was executed.
10. Every number added to S5/S6 checked by hand against its source `results/*.summary.csv` row.

## Conventions
- Strict typing + PEP 8, matching P1–P8: `from __future__ import annotations`, full hints on public functions, frozen
  dataclasses for model/result objects.
- `testbed/sim/*` stays importable without root/scapy/os_ken (only `pandas`/`matplotlib` + network for QRNG), like P4's
  `metrics_check.py`, P5's `analysis/*`, and P8's `polarization_check.py`.
- **No new mechanism except the transport model.** The sim imports the real hash/craft/reconstruct/salt/defence/metrics; it
  never re-implements or re-tunes them.
- **Deterministic and seedable** — a fixed `PRNG_SEED` yields identical CSVs; the only intentional non-determinism is the live
  QRNG draw, whose *outcome* (the null result) is nonetheless deterministic.
- One success predicate (`success.py`), one threshold derivation (`rotation_threshold.py`) — reused, never re-defined.

## Out of scope
- Any change to `hash_core`, the salt engine/sources, rotation, the attacker crafting/reconstruction, the defences, or the
  metrics collector / CSV schema — all frozen upstream, imported unchanged.
- Re-tuning P4's defence thresholds or re-deriving the success predicate — reused as-is.
- Running any live Mininet/OVS/scapy cell — the live path is deleted, not run (OQ10-4). Bare-metal is a *future* study, not this plan.
- The bare-metal implementation itself — named as the next step in the paper, not built here.
- Any P8 change (fat-tree/polarization) — Complete and independent; its offline files (`fabric.py`/`polarization_check.py`) are kept.
- Any thesis prose beyond the three `% TODO(P5)` blocks, the Mininet-removal/preliminary-study reframe (abstract clause, §III-A,
  §III-C scale caveat, §Limitations, §Future Work), and the one venue line — S1–S2, S4, S7–S8's unaffected prose stay frozen from P7.
- The Q1 multi-victim blast-radius run and the physical-10G hardware run — future work, unchanged.

## Risks
- **The frozen config values may not saturate under an explicit model.** `PRECISION_PER_SOURCE_PPS=5` × 16 sources is far below
  a 9 Mbps saturation floor, so the sim will expose whether the P3/config operating point is internally consistent. Mitigation:
  §3 derives an explicit, margin-ed offered-load operating point from the existing frozen constants and states it; if no
  consistent point exists with the frozen values, surface it as a finding for a developer decision — do not fake it.
- **Reviewer challenge: "a simulation is weaker than an emulation."** Mitigation: the credibility argument (Deliverable A intro)
  is put into the paper explicitly — real hash/craft/reconstruct/QRNG, transport-only model, epic §3.4 sufficiency, P8 precedent,
  scale-invariant ratios. The honest reframe (Deliverable C) is what makes this hold; skipping it would be the actual integrity
  failure.
- **Honesty-reframe scope creep / conflict with frozen prose.** Mitigation: touch only the Mininet/emulation sentences
  (abstract clause, §III-A, §III-C scale caveat, §Limitations, §Future Work) + the three TODO blocks — a small, mergeable
  diff. The grep gate (`grep -in "mininet\|open vswitch\|ovs" thesis/thesis.tex` returns nothing) bounds it objectively.
- **A dangling import after the Mininet deletions.** Deleting `traffic.py`'s scapy path / `run_attack.py` / the controller
  could break a kept module's import. Mitigation: the File-plan Deletions block requires confirming no kept module imports a
  deleted symbol first, moving pure helpers (`random_five_tuples`/`TrafficMode`) to a scapy-free module before deleting.
- **Transport-model over-fitting.** A model tuned to produce the desired answer is worthless. Mitigation: the model carries load
  the *real* components produce and cannot flip a saturation/evasion outcome the real hash+policy did not; the Manual
  Verification internal-consistency check (step 8) guards this.
- **QRNG live dependency.** Same as P5/P9 — `503`/`429` mid-run handled by the existing client's degrade/retry;
  skipped-with-reason, never a silent gap or a faked receipt.

## Open questions — RESOLVED (2026-07-27, developer)
- [x] **OQ10-1 — thesis framing.** **RESOLVED:** this is a **preliminary flow-level study**; the next implementation is a
  **bare-metal** one. All Mininet/OVS/emulation prose is cut from the paper (not retained as a "confirmation" rung); the
  flow-level simulation is described as the primary method, and the bare-metal build is named as the direct next step (folding
  in the old physical-10G future-work rung). *Affects Deliverable C's thesis edits.*
- [x] **OQ10-2 — code location.** **RESOLVED (default):** new `testbed/sim/` package (clean separation, mirrors how P8 kept
  its offline study self-contained). *Affects the File plan.*
- [x] **OQ10-3 — offered-load operating point + config knobs.** **RESOLVED (default):** add two documented, env-overridable
  constants to `config.py` — `PACKET_SIZE_BYTES` and an explicit precision per-flow sustained rate — derived to satisfy §3's
  inequalities with margin, so the attack's operating point is inspectable like the P4 thresholds. *Affects `config.py`, §3.*
- [x] **OQ10-4 — Mininet path disposition.** **RESOLVED:** **delete it — cut and forgotten.** `experiments/harness.py`,
  `run_experiments.py`, the Mininet topology builders, the os_ken controller, the scapy sender, the `iperf3` reader, and
  `plans/investigation-1.md` are removed (see File plan Deletions). Only pure helpers the sim reuses are preserved. *Affects
  the File plan.*
- [x] **OQ10-5 — optional live cross-check.** **RESOLVED:** dropped. No live path remains to cross-check against; the future
  confirmation is the bare-metal implementation (OQ10-1), not a Mininet run.

## Post-implementation notes (2026-07-27)

**What was built.** A self-contained, root-free flow-level simulator under `testbed/sim/`
(`transport.py`, `victim_model.py`, `sim_harness.py`, `run_sim.py`, `replay_export.py`, `__init__.py`) that drives
the real, frozen mechanism (SHA-256 `ecmp_link`, `CollisionCrafter`, `SeedBruteForcer`, the three `salt_source`
kinds, `DefencePolicy`, `MetricsCollector`/`CsvWriter`) and models only the packet transport. Output is
byte-schema-identical to P4/P5, so `testbed/analysis/*` and the P6 web demo consume it unchanged. The Mininet/OVS/
os-ken/scapy/iperf3 live path was deleted; the pure helpers `random_five_tuples`/`TrafficMode` moved to
`testbed/attacker/flows.py` (surprise: the old `traffic.py` was already scapy-free at module level — scapy imports
were lazy — so no import broke on deletion). Config gained a P10 block (`PACKET_SIZE_BYTES`, `PRECISION_PER_FLOW_PPS`,
`PRECISION_FLOWS_PER_SOURCE`, `SIM_RECON_SEED_SPACE_BITS`, `SIM_RECON_TARGET_SEED`, `VICTIM_DEMAND_MBPS`), all
env-overridable, all derived from the frozen constants.

**Results (all PASS against expected; deterministic cells reproducible bit-for-bit).**
- Exp 1 (volumetric, defences on): not saturated, victim 9.0 Mbps, meter fired. Exp 2/3 (precision, defences on):
  saturated, victim 0.4 Mbps, **neither** defence fired — the central claim. Exp 4a: saturated. 4b (csprng+rot):
  not saturated, victim 7.6, Jain 0.99. 4d (clean bg): victim 10.0, Jain 1.0. Traceable to `results/**/*.summary.csv`.
- Exp 5 crossover: measured `t_try` → analytical $T_{bf}\approx14.8$ s (19-bit weak-PRNG anchor, OQ10-1 decision);
  intervals 60/30 s saturate, 10 s and faster do not → empirical crossover 10 s, just inside $T_{bf}$. Graph 2 renders.
- Graph 1 + Graph 2 render (`results/graph{1,2}_*.{png,svg}`) and are copied to `thesis/`; both embedded in `thesis.tex`.
  Replay subset written to `web/public/replay/*.json` (3 scenes + 7-interval sweep); `qrng-provenance.json` kept as the
  placeholder (see below). Grep gate passes: no `mininet|open vswitch|ovs` token remains in `thesis.tex`.
- Offline gate `testbed/analysis/analysis_check.py` still exits 0 (analysis layer untouched).

**exp5 modelling decision (OQ10-1, developer-approved).** The frozen matrix tags exp5 `csprng`, but a CSPRNG salt is
not seed-reconstructable, so the real brute-force would hang and $T_{bf}$ (32-bit) sits far outside the 0.5–60 s sweep.
Resolution: the partial attacker reconstructs a **weak-PRNG anchor** salt with a reduced seed space (`PRNG_SEED_SPACE_BITS=19`,
set as an env default by `run_sim` so the frozen `graphs.py` T_bf line uses the same bits); `matrix.py` unedited. Documented
in `thesis.tex` §VI.

**Deferred (two items).**
1. **Local `pdflatex` compile (MV step 9 / plan-7 MV item 1):** no LaTeX toolchain is installed in this environment.
   Static checks pass (no undefined `\ref`/`\cite`, no `TODO(P5)`, both figures present). Developer must run
   `pdflatex thesis/thesis.tex` twice locally.
2. **QRNG null result + real receipt — RESOLVED (2026-07-28).** The prod 500 was a server-side fault: the `issue_log`
   table (migration `004_provenance.sql`) was never applied to the prod Neon DB, so `db.insert_issue_log` on the keyed
   `GET /v1/random/bytes` path threw (isolated by bisect: `POST /v1/verify`, the only other `issue_log` reader, also 500'd
   while `/random`/`/dice`/`/v1/pubkey` were 200). Fix: applied `hotfix_issue_log.sql` (idempotent, mirrors 004) to prod.
   Endpoint now 200. Re-ran the **full grid** `run_sim.py --exp all` + `replay_export.py`: **all cells PASS**, including the
   six graph1 partial/blind cells (the qrng partial/blind cells live in the `graph1` group, only run by `--exp all`, not
   `--exp 4` — that is why an earlier `--exp 4` rerun left them "no data"). Final coherent snapshot: Exp 4c (qrng+rot)
   `saturated=False`, victim `7.32` Mbps, Jain `0.992`; vs 4b (csprng+rot) victim `7.68`, Jain `0.979` — Δvictim `0.36`
   Mbps, ΔJain `0.013`, both within noise → **4c ≡ 4b measured**. Graph 1 is now a full 3×3: the entire qrng column
   (full/partial/blind = fail) mirrors the csprng column. Exp 5 (real measured brute-force wall-clock this run):
   `T_bf ≈ 9.51` s, empirical crossover `5` s (60/30/10 s saturate, 5 s and faster safe — note 10 s now saturates because
   the faster measured `t_try` shortened `T_bf` below 10 s; the analytic bound still brackets the crossover). Both graphs
   re-copied to `thesis/`; `qrng-provenance.json` carries a real receipt (`request_id 11f1500a…`, `entropy_epoch 30`,
   Ed25519 sig). `thesis.tex` §V table + prose, §VI `T_bf`/crossover, both figure captions, and §Limitations all re-synced
   to this snapshot; skipped-with-reason removed everywhere.

**Secret handling.** The Q-EaaS API key is stored in a gitignored `TargetedDosColisionsAndRNGAngle/.env`
(`.gitignore` updated), never committed and never written into any result, log, or the paper.
