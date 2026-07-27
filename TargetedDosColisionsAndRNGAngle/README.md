# Targeted DoS Collisions and the RNG Angle

A security-research testbed and interactive web demo showing how the **quality of the random number generator (RNG) feeding an ECMP load-balancing salt** decides whether an attacker can mount a low-volume, targeted denial-of-service (DoS) attack — and how the *same* weak RNG silently unbalances a data-center fabric even with no attacker present.

- `testbed/` — the real system: an SDN controller (os_ken/Ryu), a salt engine, an attacker, defences, metrics, a fat-tree model, and offline verification gates. Written in Python.
- `web/` — an interactive Next.js demo that re-runs the exact same routing math in the browser and visualizes it.
- `plans/`, `epic-ecmp-collision-dos.md` — design documents (one epic, eight plans).
- `tex/` — the LaTeX write-up.

---

## How it works

### 1. The mechanism under attack: ECMP link selection

Equal-Cost Multi-Path routing spreads flows across N parallel links by hashing each flow's 5-tuple together with a per-deployment **salt**, then taking the result modulo N:

```
link = SHA256( 5-tuple ‖ salt )[:8]  mod  N
```

- The 5-tuple is serialized canonically: `src_ip(4) ‖ dst_ip(4) ‖ src_port(2) ‖ dst_port(2) ‖ proto(1)` (network byte order), then the raw salt bytes are appended.
- The link index is the top 8 bytes of the SHA-256 digest, read big-endian, `mod N`.
- Implemented once in `testbed/hash_core.py:14` (`ecmp_link`) and **never re-implemented anywhere**. The controller, the attacker, the fat-tree model, and the browser all call this one function so a drift can't silently invalidate a result.

**Key property:** the chosen link is a pure deterministic function of `(5-tuple, salt)`. Change the salt and every flow's link changes. That single fact is what makes salt *rotation* a defence and salt *recovery* an attack.

### 2. The variable that decides everything: the salt source

The salt is minted from one of three RNGs (`testbed/salt/sources.py`). They feed the *identical* hash — the only thing that differs is how predictable the salt is:

| Source | How it's produced | Predictable? |
|---|---|---|
| `prng` | `random.Random(PRNG_SEED).randbytes(size)`, drawn sequentially | **Yes** — Mersenne-Twister is fully determined by a small (32-bit) seed. The provenance even records `seed` and `draw_index`. |
| `csprng` | `secrets.token_bytes(size)` | No — no small internal state to recover. |
| `qrng` | Bytes fetched over HTTP from a hosted Quantum-RNG service, with an attestable provenance receipt | No — physically unpredictable. |

`prng` is the deliberately weak, reconstructable target. `csprng` and `qrng` are cryptographically unpredictable; the project is explicit that **QRNG buys attestable provenance, not better security or balancing than CSPRNG** (an honest null result).

### 3. The attack (angle 1)

The attacker's goal: make many *distinct-looking* flows all land on one chosen link, saturating it, while staying under any per-source rate limit.

1. **Recover the salt** (`testbed/attacker/reconstruct.py`). Against a `prng` deployment, the `SeedBruteForcer` iterates every candidate 32-bit seed, reproduces the exact `random.Random(seed).randbytes(...)` stream the victim used, and validates each candidate against a handful of observed flow→link placements (an oracle). Enough probes make a false match astronomically unlikely. It records `attempts` and elapsed time — the timing anchor for the defence analysis. Against `csprng`/`qrng` there is no seed to search, so this step fails.
2. **Craft collisions** (`testbed/attacker/collision.py`). With the salt known, `CollisionCrafter` enumerates `(src_ip, src_port)` combinations and keeps only those whose `ecmp_link(...)` equals the target link. Each kept flow varies its source, so the flows look individually distinct — but all route to the same link.
3. **Send them stealthily** (`testbed/attacker/traffic.py`). In *precision* mode each spoofed source is paced below a per-source packet-rate cap, so the aggregate saturates the target link while no single source ever trips a per-source rate limiter. (*Volumetric* mode is the naive, easily-blocked control.)

Three **knowledge levels** (`testbed/attacker/knowledge.py`) form the experiment columns: `full` (salt leaked, upper bound), `partial` (brute-force — the realistic, thesis-critical case), `blind` (no salt, traffic spreads uniformly — the baseline that fails).

### 4. The defences

- **Per-source rate limiting / throttling** (`testbed/controller/defences.py`): an OpenFlow meter drops traffic above `RATE_LIMIT_KBPS`, and a sliding-window throttle blocks a source opening too many new flows. This stops a volumetric flood — but the *precision* attacker stays under the cap, so the aggregate collision still saturates the link while these defences sit idle. That gap is the whole point.
- **Salt rotation** (`testbed/controller/ecmp_controller.py`, `_rotation_loop` / `rotate_salt`): every `ROTATION_INTERVAL_SECONDS` the controller mints a fresh salt, recomputes the egress port for every tracked flow, and atomically reinstalls them (OpenFlow bundle, with a delete-and-re-resolve fallback). Each rotation invalidates the attacker's crafted collision set. Because rotation only helps if it outpaces recovery, the analysis compares the analytical mean brute-force time `T_bf = (2^bits / 2) · t_try` against the rotation interval to find the crossover — the point where "rotate faster than the attacker can re-derive the salt" defeats the attack.

### 5. The load-balancing effect (angle 2 — no attacker)

The same weak RNG hurts a fat-tree even with no adversary (`testbed/topology/fabric.py`). The model builds a canonical k=4 Al-Fares fat-tree (4 core, 8 aggregation, 8 edge switches, 16 hosts) and routes flows by hashing **only the upward hops** (edge→agg, agg→core), matching real ECMP.

- Under `prng`, every switch is given the **same** salt (modelling a same-seed deployment image). Because the per-pod aggregation count and per-group core count are equal for k=4, two switches on a path hashing the same input against the same modulus make **correlated** choices — collapsing traffic onto a diagonal subset of links. This is *polarization*, produced purely by low-entropy reuse.
- Under `csprng`/`qrng`, each switch draws an **independent** salt, the hops decorrelate, and load spreads evenly.

### 6. Measuring it

Two scale-free metrics quantify concentration (`testbed/metrics/fairness.py`):

- **Jain's fairness index** `= (Σx)² / (n·Σx²)` — `1.0` = perfectly even spread, `1/n` = everything on one link.
- **Polarization** `= max / mean` — `1.0` = even, `n` = one link carries everything.

Both return `1.0` for an idle (all-zero) fabric. They are the two numbers the paper reports, computed identically in Python and in the browser.

### 7. Why the results can be trusted: parity + offline gates

There is **no unit-test suite** (a deliberate project directive). Instead:

- Standalone `*_check.py` gates each assert one claim and exit non-zero on failure — e.g. `salt_remap_check` (different salt ⇒ different link), `collision_check` (crafted collisions are real and distinct; a planted seed is recovered), `polarization_check` (prng *must* polarize, csprng/qrng must not), `metrics_check`, and `analysis_check` (success predicate and rotation threshold).
- `vectors/check_parity.py` shells out to Node and asserts the browser's JS hash returns the **byte-identical** link to Python for every test vector, so the web demo can never show a fabricated number.

### 8. The web demo

Everything above is re-run live in the browser (`web/`), routed through the **vendored, byte-identical** hash and metrics.

- **`/` — attack demo** (`web/components/SceneController.tsx`): three scenes — (1) a naive flood that rate limiting absorbs, all links green; (2) a precision collision on a predictable salt that collapses one link and the victim while the defence lamps sit idle; (3) CSPRNG + salt rotation, where a slider lets you find the rotation interval below which the attacker can never "lock on". Visualized with a topology SVG, per-link utilization bars, a victim-throughput bar, defence status lamps, and salt/provenance panels.
- **`/load-balancing`** (`web/components/LoadBalanceController.tsx`): the full k=4 fat-tree under uniform traffic with a `weak-prng | csprng | qrng` selector. Switching the source re-derives per-switch salts and re-routes the same flows; `weak-prng` visibly polarizes (some links red/solid, others faint/unused; low Jain's index, high polarization), while `csprng`/`qrng` spread evenly. The QRNG option additionally shows its provenance receipt — explicitly labelled as attestation, not better balancing.

### In one line

One frozen hash `link = SHA256(5-tuple ‖ salt) mod N` sits under everything; the **salt's RNG** is the single knob that flips the system between safe and broken — a predictable PRNG salt is both brute-forceable (targeted DoS) and self-polarizing (unfair load), while a CSPRNG/QRNG salt with fast-enough rotation is neither.
