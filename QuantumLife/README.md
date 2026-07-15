# Quantum Tree

A hardware-grown **tree** you watch come to life. Pure fun — no paper, no
metrics, no target. Each generation is one growth step run as one real circuit
on IBM Heron r2, using a **108-qubit register** (18 branch-slots × 6 bits) laid
out as a SWAP-free chain — the longest low-error simple path that actually fits
on Heron's heavy-hex (a full 120-qubit path does not exist). A belief vector
encodes the tree's growth habit in superposition; an entangling network
**correlates neighbouring branches** so nearby limbs resemble each other
(natural clustering, not white-noise jitter); environment (wind, light, season)
bends the growth; and
the register collapses to one field of branch decisions per shot. Between steps
the belief **reinforces** what it just measured — the tree's character
crystallises as it matures — while hardware noise keeps every branch individual.
Environment is randomised per run, so **every run grows a different, natural
tree**.

The web viewer replays a recorded run as a tree growing from a seed: branches
sprout step by step, sway in the wind, and leaf out in seasonal colour.

```
code/genome.py          bits -> branch-decision contract (angle, length, fork, leaf)
code/qtree.py           growth runner (real hardware + local --sim), writes runs/*_run.json
code/layout.py          picks a low-error SWAP-free qubit chain from live calibration
web/quantum_tree.html   the living viewer (open in any browser)
runs/                   recorded runs land here
```

## The one circuit, per growth step

1. **belief encode** — `Ry(theta_i)` on all 108 qubits (the growth belief)
2. **correlation** — `--layers` entangling layers: a `CX` open chain +
   controlled-`Rx` neighbour mixing. This makes adjacent branches resemble each
   other. More layers = more correlated (and more QPU used).
3. **environment** — classical bias rotations: wind + light → `Rx` on the angle
   bits (branches lean); season → `Ry` on the length/fork bits (good year =
   longer, more forks; dry year = short, sparse)
4. **self-mutation** — `Rx(kick_i)` from the *previous* step's measured bits
5. **collapse** — measure all 120; each shot is one field of branch decisions

Between steps the belief reinforces the measured habit (`next_belief`,
`CHARACTER_LR`) plus a small organic wiggle. No target.

## Genome → tree

18 slots × 6 bits. Each slot decides one branch:

| bits (in slot) | field | meaning |
|---|---|---|
| 0,1 | angle | bend relative to parent, −1..+1 |
| 2,3 | length | segment length, 0.4..1.0 |
| 4 | fork | 1 = split into two child branches (biased ON → branches a lot) |
| 5 | leaf | 1 = grow a green leaf cluster here — **branch keeps growing** (biased ON) |

The viewer walks these fields step by step: active tips consume slot decisions,
bend + grow, fork, and sprout green leaves. Every branch is pulled toward
vertical (gravitropism, `UP` in the viewer) so the tree grows **up**. Branches
only stop at the depth cap `MAXDEPTH` (24) — so they rarely die; raise `MAXDEPTH`
if you run more than ~24 generations. `FORK_BIAS` / `LEAF_BIAS` (top of
`qtree.py`) control how much it branches and leafs; `MAXTIPS` (viewer) caps how
lush it gets.

## Run it

Reuses the submission pipeline from `../CalibrationGuidedHighYieldQRNG/code/`
(imported, never edited), so the same saved IBM account works.

**1 — test locally first, zero IBM cost:**

```
cd QuantumLife/code
python qtree.py --sim --generations 14 --shots 2048
```

> `--sim` is a **classical surrogate** — 108 qubits cannot be statevector-
> simulated, so it samples each qubit from its belief+bias with light neighbour
> smoothing to fake the correlation. **No true entanglement.** It proves the
> pipeline and feeds the viewer; real correlation only appears on hardware.

**2 — real hardware:**

```
python qtree.py --generations 10 --shots 1024 --layers 2 --backend ibm_marrakesh
```

By default (no `--qubits`) it queries the backend's **live calibration** and
lays the 108-qubit chain on the longest low-error SWAP-free path it can find,
avoiding dead qubits (`layout.best_chain`) — calibration drifts daily, so this
re-picks every run. Pass `--qubits a,b,..` to override, or `--no-auto-qubits` to
just use `0..107`. Transpilation runs at `optimization_level=3` (free depth cut).

Each step is a separate job (step g+1 depends on g's measured results — that is
the growth), so they queue one after another. Fire it and walk away. Writes
`runs/tree_<backend>_<ts>_run.json`.

**3 — watch it grow:**

Open `web/quantum_tree.html` in a browser. It opens on a demo tree; click
**load run.json** and pick your file from `runs/`. Play / pause / drag the
timeline to scrub across growth steps.

## Knobs

| flag | default | effect |
|------|---------|--------|
| `--generations` | 14 | growth steps (tree depth); use ~10 live |
| `--shots` | 2048 | shots per step; 1024 is plenty live |
| `--layers` | 2 | correlation layers — **raise for more correlated, more QPU** |
| `--qubits a,b,..` | auto | physical qubits; default = live-calibration chain, must match genome (108) |
| `--no-auto-qubits` | off | skip the live chain pick, use `0..107` |
| `--backend NAME` | least-busy | target Heron r2 |
| `--sim` | off | classical surrogate, no cost, no entanglement |
| `--seed N` | random | seed the per-run environment (omit = different tree each run) |
| `--name TAG` | tree | output filename tag |

Want it deeper / lusher: raise `--layers` (correlation) or `--generations`
(depth). Widen the genome by editing `code/genome.py` (`N_SLOTS`, `SLOT_BITS`)
**and** the JS mirror `demo()` spec in the viewer — real runs otherwise read the
genome spec straight from the loaded run file, so they stay in sync
automatically.

## Budget notes

- 120 qubits × `--layers` entangling layers is a deep circuit, so each step
  costs real quantum-seconds — check the printed `QPU seconds` total. Start with
  few generations.
- `--sim` costs nothing — use it to tune `--layers`, `--generations`, and the
  evolution/environment constants (`CHARACTER_LR`, `WIND_SCALE`, `SEASON_SCALE`,
  … at the top of `qtree.py`) before the real run.
