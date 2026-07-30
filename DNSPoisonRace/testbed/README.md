# DNS Poison Race — testbed runbook

Root-free, network-free discrete-event simulator of a DNS resolver's cache-poisoning
race (epic `../plans/epic-dns-poison-race.md`). Python 3.12+, stdlib only for the core.

## Run the smoke race (AC-1.1)

```
python3 testbed/sim/run_sim.py --smoke
```

Prints one race's terminal outcome and a final `PASS`. No network, no root required —
confirm by running under an unprivileged shell / with networking down.

Run N races:

```
python3 testbed/sim/run_sim.py --trials 10
```

## Regenerate the parity vectors (AC-1.3)

```
python3 testbed/vectors/gen_race_vectors.py
```

Deterministic from each scenario's seed — running it twice must leave
`testbed/vectors/race_vectors.json` byte-identical (`git diff` empty). This file is the
Python source of truth the P6 JS parity gate vendors unchanged.

## Environment variables (`testbed/config.py`)

All values are env-overridable; `config.py` is the single source of truth — no other
module reads `os.environ` directly.

| Variable | Default | Notes |
|---|---|---|
| `PORT_BITS` | `16` | UDP source-port entropy width (OS ephemeral range is ~11–16 bits) |
| `RTT_SECONDS` | `0.02` | Authoritative reply arrival time |
| `RETRANSMIT_SECONDS` | `0.5` | Retransmit timer (consumed by P3) |
| `PARALLEL_QUERIES` | `1` | In-flight windows / birthday amplification (consumed by P3) |
| `QEAAS_BASE_URL` | `https://api.qeaas.eu` | Q-EaaS hosted endpoint (consumed by P2) |
| `QEAAS_API_KEY` | `` (empty) | Q-EaaS key — **never** commit, print, or log this |
| `PRNG_SEED` | `0` | Weak-PRNG seed (consumed by P2) |
| `EFF_BITS_MIN` / `EFF_BITS_MAX` / `EFF_BITS_STEP` | `8` / `32` / `1` | Effective-entropy sweep (consumed by P5) |
| `TRIALS_PER_CELL` | `10000` | Trials per sweep cell (consumed by P5) |
| `SEND_RATE_PPS` | `100,1000,10000,100000` | Attacker send-rate axis, comma-separated (consumed by P4/P5) |
| `SAD_DNS_LEAK_BITS` | `0` | SAD-DNS port-entropy-leak knob (consumed by P2/P5) |

`QEAAS_API_KEY` is loaded from `DNSPoisonRace/.env` (gitignored), never read directly
into an agent's context:

```
set -a && . ./.env && set +a
```

## Draw sources (AC-2)

Four arms behind one factory, `draw_source(kind, *, txid_bits, port_bits) -> Draw`
(`testbed/draw/sources.py`): `fixed` (pre-2008 model, port pinned to `FIXED_PORT`,
TXID only), `prng` (deliberately weak, reproducible, seeded from `PRNG_SEED`),
`csprng` (`secrets.randbits`, full entropy), `qrng` (live Q-EaaS bytes, full
entropy). All four return the same P1-frozen `Draw` shape.

`testbed/draw/sad_dns.py`'s `sad_dns_leak(port_bits, k)` is a pure, source-independent
knob that reduces effective port entropy once an off-path attacker knows `k` bits via
the SAD-DNS side channel (epic §3.5, OQ-4).

Run the offline gate, no network required:

```
python3 testbed/draw/draw_check.py
```

With `QEAAS_API_KEY` set (see above), the same command also exercises the `qrng` arm
against the live hosted service.

| Variable | Default | Notes |
|---|---|---|
| `FIXED_PORT` | `33333` | Port the `fixed` arm always returns |

## Running the poison race (AC-3)

The off-path attacker package (`testbed/attacker/`) floods forged `(TXID, port)` guesses at
the resolver's outbound query while the authoritative reply races back, with retransmit-driven
fresh-draw windows (birthday amplification). Dependency-free (stdlib only, no scapy/root/network
except the opt-in `qrng` kind).

Offline gate, no network required:

```
python3 testbed/attacker/attack_check.py
```

CLI runner — sweep any of send-rate, entropy, or parallelism by hand:

```
python3 testbed/attacker/run_attack.py --kind csprng --eff-bits 12 --send-rate 100000 --trials 2000
python3 testbed/attacker/run_attack.py --kind csprng --eff-bits 28 --send-rate 100000 --trials 2000
python3 testbed/attacker/run_attack.py --kind csprng --trials 5 --seed 123
```

The four `--kind` arms (`fixed`, `prng`, `csprng`, `qrng`) mirror `draw_source`. `--eff-bits`
solves for the SAD-DNS leak `-k` needed to hit that effective-bit count at the current
`--port-bits`. With `QEAAS_API_KEY` set, `--kind qrng` also carries the live Q-EaaS provenance
receipt in the printed result.

All reproducible randomness (guess order, RTT jitter, parity-vector targets) flows through
`testbed/attacker/portable_prng.py`'s `splitmix64` — the parity contract P6's JS mirror vendors
verbatim. `race_vectors.json`'s schema is frozen (P1); P3 fills the `send_schedule` /
`parallel_queries` / `retransmit` fields with real flood scenarios via `gen_race_vectors.py`.

| Variable | Default | Notes |
|---|---|---|
| `ATTACKER_SEND_RATE_PPS` | `10000` | Single-race/CLI forged send-rate default |
| `RTT_JITTER_FRAC` | `0.1` | Authoritative-arrival jitter, as a fraction of `rtt` |
| `MAX_RETRANSMITS` | `3` | Retransmit rounds per query (each opens a fresh-draw window) |

## Resolver cache + metrics collector (AC-4)

`testbed/resolver/cache.py` gives the epic §5 diagram's four cache states
(`POISONED`/`RESOLVED_LEGIT`/`WINDOW_CLOSED`) a named `CacheEntry` + TTL, purely as a vocabulary
over `PoisonRaceResult.outcome` — it never re-derives the race decision, that stays P3's.
`testbed/resolver/metrics.py`'s `collect_cell(...)` runs `run_poison_race` `--trials` times at one
`(source, effective-bits, send-rate, parallel-queries)` cell and aggregates the five headline
metrics (M1 poison probability, M2 mean forged packets / mean time-to-poison, M3 amplification
factor vs a `parallel_queries=1` baseline, M4 `k`/`effective_bits` passthrough, M5 first-trial
QRNG provenance).

Offline gate, no network required:

```
python3 testbed/resolver/metrics_check.py
```

CLI runner — writes one CSV row + one `.record.json` per `(kind, parallel)` cell:

```
python3 testbed/resolver/run_metrics.py --kind csprng --eff-bits 16 --send-rate 100000 --trials 2000
python3 testbed/resolver/run_metrics.py --kind csprng --eff-bits 16 --send-rate 100000 --trials 2000 --parallel 1,8
python3 testbed/resolver/run_metrics.py --kind qrng --eff-bits 16 --trials 5 --seed 1   # needs QEAAS_API_KEY
```

`--parallel` is comma-separated; its **first** value is the amplification baseline
(`--parallel 1,8`, not `--parallel 8` alone, or `amplification_factor` stays `None`). `--kind`
accepts a comma-separated list too (OQ-P4.3), looping cells across sources in one invocation.

CSV schema (frozen, `results/metrics.csv` by default — P5/P6 read it): `run_tag, timestamp, kind,
effective_bits, k, send_rate_pps, parallel_queries, trials, poison_rate, mean_forged_packets,
mean_time_to_poison, amplification_factor`. Provenance is not a CSV column — it lives in the
per-cell `results/records/<tag>.record.json` sidecar (`DrawProvenance.detail`'s nested dict
doesn't flatten cleanly into one CSV cell), embedding the **first** trial's provenance for the
cell (documented simplification, not exhaustive per-draw enumeration).

| Variable | Default | Notes |
|---|---|---|
| `CACHE_TTL_SECONDS` | `300` | Nominal DNS record TTL for the cache-wrapper edge (cosmetic — no metric reads it yet) |
| `RESULTS_CSV_PATH` | `results/metrics.csv` | Run-tagged CSV, one row per cell |
| `RESULTS_RECORD_DIR` | `results/records` | Per-cell `.record.json` provenance sidecars |
