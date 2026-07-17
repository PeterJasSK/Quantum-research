# Quantum Tree

A **living tree grown on a real quantum computer.** Every growth step is one
circuit executed on IBM Heron r2 hardware; the measured bits decide how the tree
branches, bends, and leafs; and what the tree learned in one step is carried
into the next. Watch a recorded run replay in the browser and you are watching
an organism that grew, generation by generation, out of genuine quantum
measurement.

There are two halves to the project:

- **The art** (`qtree.py` + the web viewers) — grow a beautiful tree, no
  metrics, no target. Pure fun.
- **The research fork** (`research_qtree.py`) — same growth engine, but
  instrumented to answer a *falsifiable* question: does the hardware
  entanglement imprint a spatial correlation on the genome that a classical,
  no-entanglement surrogate cannot reproduce?

This README walks the whole thing top to bottom — the idea, every part of the
code, how the quantum computer is wired in, and an honest statement of what is
really happening (and what is not).

---

## File map

```
code/genome.py            the bits -> branch-decision contract (the "DNA")
code/qtree.py             ART growth runner (hardware + local --sim) -> runs/*_run.json
code/research_qtree.py    RESEARCH fork: adds the C(d)/xi entanglement metric + repeats
code/layout.py            picks a low-error SWAP-free qubit chain from live calibration
web/quantum_tree.html     the living viewer (line-art)
web/quantum_tree_pixel.html   the pixel-art "grove" viewer, auto-cycles recorded runs
runs/                     ART recorded runs land here
research_runs/            RESEARCH runs + per-generation statistics summaries
research/                 study design, runbook, hypotheses
```

The pipeline for talking to IBM hardware is **reused, not copied** from the
sibling project `../CalibrationGuidedHighYieldQRNG/code/` (imported via
`pipeline_common`), so the same saved IBM account works and the submission path
is battle-tested.

---

## Chapter 1 — The idea

Take a quantum register and treat it as the **genome of a growing plant**. Each
generation:

1. the register is prepared in a superposition that encodes the tree's current
   "growth belief",
2. an entangling network correlates neighbouring genes,
3. the environment (wind, light, season) bends the growth,
4. the register is measured — each shot is one complete plan for the tree,
5. the tree **learns** from what it measured and grows from there next time.

The result is not a random image regenerated each frame. It is a *cumulative,
inherited* structure — the definition of growth. Chapter 4 explains precisely
why this is evolution and not noise.

---

## Chapter 2 — The genome (`genome.py`)

The register is **108 qubits = 18 slots × 6 bits**. One slot = one branch
decision:

| bits (in slot) | field | meaning |
|---|---|---|
| 0,1 | angle | bend relative to parent, −1..+1 |
| 2,3 | length | segment length, 0.4..1.0 |
| 4 | fork | 1 = split into two child branches (biased ON) |
| 5 | leaf | 1 = sprout a green leaf cluster; the branch **keeps growing** |

`GENOME_SPEC` is embedded verbatim into every `run.json` so the viewer decodes
exactly the way Python encoded. `decode_slot()` / `decode_field()` are the
reference decoder; the viewer keeps a JS mirror.

Why 108? It is the longest low-error, SWAP-free simple path that actually fits
on a 156-qubit Heron r2 heavy-hex lattice. A full 120-qubit path does not exist
on that topology.

---

## Chapter 3 — The one circuit, gate by gate (`build_circuit`)

Every generation builds and runs **one** circuit. Construction order (this is
literally what the code emits):

```python
# 1. belief encode — the tree's growth habit, as superposition
for i in range(108):
    qc.ry(theta[i], i)                 # theta starts at pi/2 (a fair coin)

# 2. correlation — the entangling network, repeated `layers` times
for _ in range(max(1, layers)):
    for i in range(107):
        qc.cx(i, i + 1)                # CNOT open chain: entangle each neighbour pair
    for i in range(107):
        qc.crx(0.7, i, i + 1)          # controlled-Rx (CROSS_ANGLE): soft neighbour mixing

# 3. environment — classical bias rotations, per slot
for s in range(18):
    base = s * 6
    qc.rx(angle_bias,  base+0); qc.rx(angle_bias, base+1)   # wind + light on angle bits
    qc.ry(season_bias, base+2); qc.ry(season_bias, base+3); qc.ry(season_bias, base+4)
    qc.ry(FORK_BIAS,   base+4)         # steady push: branch more
    qc.ry(LEAF_BIAS,   base+5)         # steady push: more leaves

# 4. self-mutation — a kick carried from the PREVIOUS generation's bits
for i in range(108):
    if kick[i]:
        qc.rx(kick[i], i)

# 5. collapse
qc.measure(range(108), range(108))
```

**The two entangling gates (step 2) are the heart.** `CX(i,i+1)` with a qubit in
superposition creates a Bell-type state `|00⟩+|11⟩` — the neighbours are now
*entangled*: measuring one constrains the other. `CRX(0.7, i, i+1)` adds a soft,
tunable (`CROSS_ANGLE = 0.7 rad`) partial rotation on top. Together they weave a
correlation along the chain, so nearby branches resemble each other — natural
clustering instead of white-noise jitter. `--layers` repeats the block; more
layers push the correlation further down the chain (and cost more QPU).
`--layers 0` removes them entirely → independent qubits → the correlation floor.

Growth/evolution constants (top of the file), kept identical between the art and
research runners so results transfer:

```
CHARACTER_LR = 0.18   reinforcement strength (how hard belief locks onto measured habit)
WIGGLE       = 0.05   organic per-generation jitter
MUT_SCALE    = 0.30   self-mutation kick magnitude
CROSS_ANGLE  = 0.7    controlled-Rx neighbour angle
WIND_SCALE   = 0.4    wind -> Rx on angle bits
LIGHT_SCALE  = 0.5    steady phototropic lean
SEASON_SCALE = 0.9    season -> Ry on length/fork bits
FORK_BIAS = 0.3 ; LEAF_BIAS = 0.45   steady pushes
THETA_LO, THETA_HI = 0.08 .. pi-0.08 belief clamp (never fully 0 or 1)
```

---

## Chapter 4 — Evolution between generations (`next_belief`), and why it is NOT random

This is the part that turns "repeated random measurement" into "an organism that
grows". There are **two layers of randomness, and one of them has memory.**

**Layer A — inside one generation (no memory).** The 4096 shots are independent
quantum coin-flips. Pure noise on their own.

**Layer B — across generations (with memory).** After measuring, the code
computes `p[i]` = how often qubit *i* came up 1 across all 4096 shots, then:

```python
drift = CHARACTER_LR * (2*p[i] - 1)          # push belief TOWARD what was measured
theta_next[i] = clamp(theta[i] + drift + wiggle)
kick_next[i]  = MUT_SCALE * (2*p[i] - 1)     # carry a mutation into the next step
```

This is **feedback**: the outcome of generation *N* shapes the belief of
generation *N+1*. That is the whole difference from a random walk:

| pure random walk | this system |
|---|---|
| `theta_next = theta + noise` | `theta_next = theta + 0.18·(direction it actually fell) + small noise` |
| no memory, wanders forever | reinforces the habit — an **attractor** |
| entropy stays high | entropy **drops**: character crystallises |

Because the drift keeps pushing belief toward whatever the qubits already prefer,
the tree's branching *character* locks in as it matures, while `WIGGLE` keeps
individual branches alive and noisy. This is exactly the shape of biological
evolution: **random variation + heredity (the carried belief) + environmental
pressure (Chapter 5) = directed change**, not blind noise.

> **Important nuance.** Two different numbers come out of the 4096 shots:
> - `modal` — the single most frequent 108-bit field. This is saved as the
>   *representative* and is what the **viewer draws**.
> - `p[i]` — the per-qubit frequency across all shots. This is what **drives the
>   evolution** (`next_belief` uses `p`, never `modal`).
>
> So "the most frequent plan is how the tree behaved" is true *for the picture*,
> but the learning is built from the *full distribution* of all 4096 shots, which
> is far more robust than any single sample.

---

## Chapter 5 — The environment (`build_env`)

The environment is **not** re-rolled each generation — the entire schedule for
all generations is generated **once at the start** and each generation reads its
row. It is structured, smooth, seeded:

```python
season = 0.5 + 0.5*sin(2*pi*g/period + phase)        # period 6..12 gens, 0 dry .. 1 good
gust   = wind_prevail + 0.3*sin(2*pi*g/wind_period + wind_phase) + small_noise
angle_bias  = WIND_SCALE*gust + LIGHT_SCALE*light_side*light_str   # -> Rx on angle bits
season_bias = SEASON_SCALE*(2*season - 1)                          # -> Ry on length/fork bits
```

A good season lengthens branches and forks more; a dry year is short and sparse;
wind swings the lean; light pulls a steady phototropic tilt. Because it is a
smooth cycle rather than per-step noise, the tree responds *coherently* over
time — a visible trend, not flicker. Seeding it means an art run is repeatable
and, crucially, a `--sim` run and a hardware run launched at the same `--seed`
see the **identical** environment → a fair paired comparison.

---

## Chapter 6 — Wiring in the quantum computer

You never touch hardware physically. A job is submitted over the internet to
IBM's cloud and queued on a real chip. The path, in order:

**1. Connect (`pipeline_common.connect`).**
```python
service = QiskitRuntimeService()                     # loads your saved IBM token
backend = service.least_busy(min_num_qubits=100,     # least-busy Heron r2:
              filters=lambda b: b.name in ["ibm_kingston","ibm_fez","ibm_marrakesh"])
```

**2. Calibration snapshot (`read_snapshot`).** Pulls that day's gate/readout
error rates for the chip — free metadata, no QPU cost. Stored in the run file.

**3. Qubit layout (`layout.best_chain`).** The circuit entangles an *open chain*
`cx(i,i+1)`. To map it without expensive SWAPs, the 108 physical qubits must be
a genuine connected path on the heavy-hex lattice. `best_chain`:
- reads live 2-qubit / readout / `sx` errors per qubit,
- drops **dead** qubits (`sx ≥ 0.5` or `readout ≥ 0.25`),
- runs a time-boxed **DFS** (40 s) to find the longest 108-qubit simple path that
  **minimises total error** along it,
- returns the ordered `qubit_list` + stats (`twoq_err_mean`, `readout_max`, …).

Re-picked every run because calibration drifts daily. `--qubits a,b,..` overrides;
`--no-auto-qubits` just uses `0..107`.

**4. Transpile.**
```python
pm  = generate_preset_pass_manager(optimization_level=3, backend, initial_layout=qubit_list)
isa = pm.run(qc)
```
Your logical `Ry/CX/CRX/Rx` circuit is rewritten into the chip's **native** gates
(`sx`, `rz`, `CZ`/`ECR`) on exactly the chosen qubits, at the most aggressive
optimisation level.

**5. Submit (`pipeline_common.run_sampler`).** A `SamplerV2` job is queued in
chunks (up to 50 000 shots each). The printed `job N: d9c6...` line is the real
IBM job id; `qpu 3.00s` is the real quantum-seconds billed. The chip prepares →
gates → measures, 4096 times.

**6. Bit order.** Qiskit returns bitstrings MSB-first, so `s[::-1]` reverses them
→ index *i* is qubit *i* is gene *i*.

Each generation is a **separate job** (generation g+1 depends on g's measured
bits — that dependency *is* the growth), so they queue one after another. Fire it
and walk away.

---

## Chapter 7 — From bits to a tree (`buildTree` in the viewer)

The viewer does **not** draw 14 independent trees. It grows **one** tree in
layers. The key is a `tips` array — the live growing ends:

```javascript
let tips = [{x:0, y:0, heading:-PI/2, depth:0}];      // generation 0: one trunk tip
for (g = 0; g < generations; g++) {
    field = decodeField(gens[g].bits);                // 18 branch decisions this gen
    for (each live tip k) {
        slot = field[(k + g) % 18];
        heading = upright(tip.heading + slot.bend*MAXBEND + windLean);  // pulled toward vertical
        len     = BASELEN * slot.length * (0.5 + 0.7*season);           // season scales length
        extend tip into a new segment;
        if (slot.leaf && depth >= 3) sprout a leaf;
        if (slot.fork && spacing ok) tip splits into TWO child tips;
    }
    tips = next;                                       // new ends carry into the next generation
}
```

So **one generation = one growth ring**. Generation 0 is the trunk; generation 1
is the branches sprouting from the trunk's tip; generation 2 grows from those;
and so on. The `tips` carry forward, so each generation grows *from where the
last one ended* — cumulative, inherited structure. Branches only terminate at the
depth cap `MAXDEPTH = 24`; `MAXTIPS = 90` caps how lush it gets. The pixel viewer
adds Fibonacci secondary thickening, seasonal leaf colour, sway, sky, and
auto-cycles through every recorded run.

---

## Chapter 8 — The research fork: measuring entanglement (`research_qtree.py`)

The art viewer only ever tracked **diversity** (mean per-qubit binary entropy),
which is blind to correlation *between* qubits — it cannot see entanglement. The
research fork keeps the identical growth engine and adds the quantity that can:

```
connected two-point correlation   C(d) = <b_i · b_{i+d}> − <b_i>·<b_{i+d}>
normalised                         c(d) = C(d) / C(0)
integrated correlation length      xi   = sum over d>=1 of c(d)
```

- `C(d) = 0` for all `d>0` ⇒ independent qubits ⇒ a classical / product state ⇒
  **no entanglement**.
- A nonzero, distance-decaying `C(d)` is the **fingerprint of the entangling
  chain** — as much of it as the device noise leaves intact.

`xi` collapses the whole `C(d)` curve into one number: `xi ≈ 0` means no
correlation; `xi ≠ 0` means the qubits know about each other. The fork also runs
`--repeats R` independent seeded runs (seed, seed+1, …) so every number carries a
mean ± std and can be fed to a two-sample test. Output:

```
research_runs/<TAG>_..._seedK_..._run.json      per-repeat, with a correlation block per generation
research_runs/<TAG>_..._summary.json            per-generation mean/std of diversity, C0, xi
```

**The experimental logic.** `--sim` is the **null model** — a classical surrogate
with *no* entangling gates, only light neighbour smoothing (`0.7·self +
0.15·each neighbour`). It can grow a tree that *looks* similar, but it can never
produce true `C(d)`. So: run hardware and sim at matched seeds; if hardware shows
`C(d) ≠ 0` where sim shows `C(d) ≈ 0`, the entanglement survived the noise and
left a measurable mark.

Even cleaner is the on-hardware control: run `--layers 0` (the **B0** floor: no
entangling gates, pure device/readout artefact) and subtract it from `--layers N`
(**B**). The real signal is `xi(B) − xi(B0)`, never raw `xi(B)`.

---

## Chapter 9 — How to read the numbers

Latest paired hardware run (`ibm_kingston`, 8 generations, 3 repeats, 4096 shots):

| run | `xi` mean | what it is |
|---|---|---|
| B0 (`--layers 0`) | +0.017 | correlation floor — device/readout artefact, ≈ 0 |
| B (`--layers 2`) | −0.031 | with entanglement, shifted below the floor |

Real signal `xi(B) − xi(B0) = −0.048`, roughly `t ≈ −5.5` across the 24
generation-samples — **not noise, a real effect.** The floor sitting at ≈ 0
confirms the pipeline is clean (no spurious correlation faked by the device). The
effect is concentrated in the early generations (generation 0–3 dip hard, then
decay toward 0 by generation 5–7), so **report `xi` per generation, not just the
scalar mean** — the decay curve is the result. Whether that offset is genuine
entanglement or a circuit-depth systematic is exactly what a `--layers 0 1 2 3 4
8` sweep is for: if `|signal|` scales linearly with depth it is a systematic; if
it saturates or is non-monotonic, the entanglement hypothesis survives.

---

## Chapter 10 — Running it

Reuses the IBM submission pipeline from `../CalibrationGuidedHighYieldQRNG/code/`
(imported, never edited), so the same saved account works.

**Art — test locally first, zero IBM cost:**
```bash
cd QuantumLife/code
python qtree.py --sim --generations 14 --shots 2048
```

**Art — real hardware:**
```bash
python qtree.py --generations 10 --shots 1024 --layers 2 --backend ibm_marrakesh
# then open web/quantum_tree.html (or quantum_tree_pixel.html) and load runs/*_run.json
```

**Research — paired null vs hardware, matched seeds:**
```bash
# classical baseline (no entanglement)
python research_qtree.py --sim --generations 8 --shots 4096 --seed 100 --repeats 3 --name baseline
# on-hardware floor (no entangling gates)
python research_qtree.py --generations 6 --shots 4096 --seed 100 --repeats 3 --layers 0 --name B0
# hardware with entanglement
python research_qtree.py --generations 6 --shots 4096 --seed 100 --repeats 3 --layers 2 --name B
# depth sweep to separate entanglement from circuit-depth systematics
for L in 0 1 2 3 4 8; do
  python research_qtree.py --generations 6 --shots 4096 --seed 100 --repeats 3 --layers $L --name C_L$L
done
```

### Knobs

| flag | default | effect |
|------|---------|--------|
| `--generations` | 14 | growth steps (tree depth) |
| `--shots` | 4096 (research) / 2048 (art) | shots per generation |
| `--layers` | 2 | entangling layers — raise for more correlation, more QPU; **0 = floor** |
| `--seed N` | random / 0 | environment seed; research: repeat *r* uses `seed+r` |
| `--repeats R` | 1 | *(research)* independent seeded runs for statistics |
| `--corr-dmax D` | 30 | *(research)* max separation *d* for `C(d)` |
| `--qubits a,b,..` | auto | physical qubits; must total 108 |
| `--no-auto-qubits` | off | skip live chain pick, use `0..107` |
| `--backend NAME` | least-busy | target Heron r2 |
| `--sim` | off | classical surrogate: no entanglement, no cost |
| `--name TAG` | tree / study | output filename tag |

### Budget notes

- 108 qubits × `--layers` entangling layers is a **deep** circuit — each
  generation costs real quantum-seconds (check the printed `QPU seconds`). Start
  small.
- `--sim` costs nothing — use it to tune `--layers`, `--generations`, and the
  evolution/environment constants before a real run.

---

## What is actually happening (the honest version)

Stripped of the poetry, end to end:

1. An environment schedule is generated (random, or fixed by `--seed`), and the
   tree starts undecided — every gene a fair coin (`theta = pi/2`).
2. Each generation runs **one circuit of 4096 shots on a real Heron r2 chip**.
   From those shots the code takes the **per-qubit frequency `p[i]`** (drives
   evolution) and the **single most frequent field `modal`** (drawn by the
   viewer).
3. The next generation's belief is the previous belief **reinforced toward `p`**
   (plus a small wiggle and a mutation kick), combined with that generation's
   scheduled environment, and run on the chip again.
4. Entropy falls over generations because the belief crystallises — the tree
   changes less and less and mostly just *grows as it has become*.
5. When the generations run out, the recorded history is replayed as a pixel-art
   film: you watch the tree grow, layer by layer, under the conditions it was
   exposed to.

**Is it "impossible to simulate"?** Two honest senses, kept separate:

- **Scale (true, hard):** 108 entangled qubits would need `2^108 ≈ 3×10^32`
  amplitudes held at once — more than could ever be stored. No classical machine
  can hold that state. That is why `--sim` is *not* a simulation of the quantum
  state at all; it is a cheap classical surrogate that fakes per-qubit behaviour.
- **The quantum signature (must be measured, not asserted):** the *visual* tree
  can be faked classically — `--sim` grows one too. What a classical surrogate
  **cannot** produce is the genuine entanglement correlation `C(d)`. Whether that
  correlation actually survives the device noise is not a slogan — it is the
  hypothesis the research fork *tests*. Current result: it does, and the signal
  (`xi(B) − xi(B0) ≈ −0.048`) is statistically real but **small**.

So the fair statement is: **the tree's growth is genuinely quantum** — it is
driven by physical measurement collapse on hardware no classical computer could
simulate at this scale, and it carries a real (if small) entanglement fingerprint
that the classical surrogate provably cannot reproduce. The picture is art; the
`C(d)/xi` measurement is what makes the claim science rather than decoration.
