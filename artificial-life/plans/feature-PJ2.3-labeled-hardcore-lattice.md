# Feature Plan — PJ2.3: Labeled hard-core lattice — exclusion, lineage identity, and emergent carrying capacity

**Ticket:** PJ2.3 (stage; sibling of PJ2.2 — this research repo decomposes epics into stages, no GitHub issue)
**Owning epic:** `artificial-life/plans/epic-qalife-darwinian-richness.md`, stage **P3** (successor to PJ2.2)
**Relation to PJ2.2:** PJ2.2 gave each organism its **own** body block (`lat_body_q(org, cell)`), so fields pass
through each other — no volume, no exclusion. PJ2.3 replaces the body substrate with a **single shared lattice**
where a cell qubit is binary (0 empty / 1 present), so two particles **cannot** occupy one cell — hard-core
exclusion emerges from the encoding, not a scripted rule. A second **label** qubit per cell tags lineage
(0 = parent line, 1 = daughter line) so parent and daughter stay distinguishable on screen. The germ line and
the ⟨X^⊗W⟩ witness are **unchanged** — the body-encoding change is orthogonal to the quantum claim.
**Substrate:** extend `code/pj_qalife.py` (new labeled-lattice builders alongside the PJ2.2 ones, byte-stable) +
new driver `code/pj_lattice_labeled.py` + extend `analysis/pj_lattice_render.py`.
**Slug:** labeled-hardcore-lattice
**Author:** Claude (Opus)
**Date:** 2026-09-26
**Status:** DRAFT — spec for review

> **No tests (repo convention, CD-7).** Verification = `--selftest` (static circuit-structure checks) +
> `--dump-circuit` + `--sim` runs + a written correctness evaluation. No test framework, no test files.
>
> **Certified frames, not a sim-movie (PJ2.2 lock, inherited).** On hardware each generation is its own
> measured circuit (depth scan 0..GENS−1), each measured for occupancy + label + witness with a separable-null
> control. Integer-generation frames are certified; smooth playback is a labelled sim artifact.

---

## 1. Summary

The organism's body becomes a **labeled hard-core quantum field** on a shared `grid×grid` lattice. Two qubits
per cell:

- **occupancy** `occ[i]` — 0 empty / 1 present. Binary ⇒ at most one particle per cell per shot = **exclusion**.
- **label** `lbl[i]` — 0 parent line / 1 daughter line. Rides with the particle so lineage stays identifiable.

Movement is an **excitation-conserving hard-core hop** between von-Neumann neighbours (the occupancy amplitude
flows; the label is transported with it). Because occupancy is binary, a particle can never hop onto an occupied
cell — the "sense of space" the user asked for falls out of the physics, exactly like the drift-to-centre did.

The germ line stays as in PJ2.2: a separate `W`-qubit GHZ block per organism, CNOT-cloned parent→daughter at
`LAT_REP_GEN`, read as ⟨X^⊗W⟩ with the isolated/coupled A/B kill-switch. **Only the witness is the quantum
claim.** Occupancy and label are honest readout aids (CD-3/CD-4).

**Three new emergent results (the reason to build this):**
1. **Exclusion / volume** — parent and daughter clouds never share a cell in a shot; per-cell double-occupancy = 0
   is a structural witness of space.
2. **Carrying capacity** — replication can only bud into an *empty* neighbour, so a filling lattice caps its own
   population at `N = grid*grid` (3×3 → ≤9). The cap is emergent, not coded.
3. **Decoherence-as-spurious-birth** — on hardware, noise flipping an `occ` qubit reads as a *fake* particle.
   Population above the true count is a direct, visual decoherence meter (ties back to the PJ2.2 "sum > 1"
   observation, now made a first-class readout).

---

## 2. Qubit layout (byte-stable additions to `pj_qalife.py`)

Shared body registers (NOT per-organism blocks):

```
segment = [ germ(parent) W | germ(daughter) W | occ[0..N-1] | lbl[0..N-1] ]
```

New helpers (mirror the PJ2.2 `lat_*` naming):

- `latl_occ_q(i, width, grid)`  → occupancy qubit of cell i
- `latl_lbl_q(i, width, grid)`  → label qubit of cell i
- `latl_germ_q(org, k, width, grid)` → germ locus k of organism org (parent org=0, daughter org=1)
- `latl_segment_len(width, grid, mode)` → `n_germ_blocks*W + 2*N`

Counts (W=3):
| grid | germ blocks | N | germ q | body q (2N) | total |
|------|-------------|---|--------|-------------|-------|
| 3×3 solo      | 1 | 9  | 3 | 18 | **21** |
| 3×3 replicate | 2 | 9  | 6 | 18 | **24** |
| 4×4 solo      | 1 | 16 | 3 | 32 | **35** (sim-cap; HW only) |

3×3 replicate = 24 qubits = **same as today's PJ2.2 replicate/duo** → fits Heron, fits the `_SV_MAX_QUBITS=27`
statevector cap. 4×4 replicate is HW-only (past laptop statevector), same ceiling story as PJ2.2.

---

## 3. Movement — the labeled hard-core hop (the key circuit primitive)

Per von-Neumann edge `(i, j)`, in the existing 4-colour edge order (`lat_edges`, keeps depth ≈1 per colour):

**Step A — hop occupancy (hard-core, exclusion-exact):**
```
rxx(θ, occ[i], occ[j]); ryy(θ, occ[i], occ[j])
```
XX+YY conserves excitation and, on binary qubits, is hard-core automatically: it moves amplitude between an
occupied and an empty cell and does nothing on empty↔empty; two particles can never land on one cell.

**Step B — transport the label with the particle.** After Step A the particle is in a superposition of
"stayed at i" / "hopped to j"; its label must follow coherently. Use a Fredkin (controlled-SWAP) that exchanges
the labels exactly when the occupancy moved:
```
CSWAP(ctrl = occ[j], lbl[i], lbl[j])
```
Reasoning: in the branch where the particle hopped i→j, `occ[j]=1` and the label that was at i must now be at j —
the CSWAP moves it. In the stay branch `occ[j]=0`, CSWAP is identity, label stays at i. (Empty↔empty: both
labels 0, no-op.) This is the honest coherent transport; see **OQ-1** for the exact-vs-approx trade.

θ = `LAT_HOP` (isotropic, uniform — inherited; the drift-to-centre emergence is preserved).

**Depth cost:** Step B adds one Fredkin per edge on top of the PJ2.2 hop. Fredkin = 2 CX + a Toffoli-decomp
(~6–8 two-qubit gates) → the labeled hop is ~4–5× the two-qubit count of the bare walk. This is the dominant new
cost and the reason the gen ceiling tightens (**OQ-2**).

---

## 4. Replication — budding into empty space (emergent carrying capacity)

At `gen == LAT_REP_GEN`:

1. **Germ clone (unchanged):** `CX(germ(0,k) → germ(1,k))` for k in 0..W−1 — the shared GHZ genealogy.
2. **Body bud (new, exclusion-respecting):** spawn a daughter into an *empty* von-Neumann neighbour `t` of a
   parent-occupied seed cell `s`:
   ```
   # birth only if parent present at s AND target t empty  → multi-controlled
   MCX(ctrl = occ[s]=1, occ[t]=0(neg) → occ[t])   # set occ[t]=1
   CX(occ[t] → lbl[t])                             # newborn label = 1 (daughter line)
   ```
   The negated control on `occ[t]` is what enforces "bud only into free space." When the lattice is full around
   `s`, every neighbour control fails → **no birth** → population self-caps at N. Carrying capacity emerges from
   exclusion; nothing counts or clamps population explicitly.

**Cost / faithfulness trade in OQ-3.** The exact version is a Toffoli-with-negated-control (deep). A shallow
prototype drops the empty-check (`CX(occ[s]→occ[t])`), accepting a small error while the parent is still
localized at gen 2 (target neighbour is empty in almost all branches early). Prototype with the shallow bud,
report the exact bud as the certified path.

---

## 5. Arms (unchanged A/B) + the coupled wound

- **isolated** — body never touches germ; witness survives the walk (Weismann barrier intact).
- **coupled** — one coherent `rxx+ryy` between a centre `occ` cell and germ locus 0 (the soma→germ wound);
  witness collapses. Identical kill-switch to PJ0/PJ1/PJ2.2, now on the shared-lattice body.

The exclusion + carrying-capacity results are reported in the **isolated** arm (the biology); coupled remains the
honesty control that proves the witness is a real genealogical claim.

---

## 6. Observables — split the field by label (`reduce_counts` extension)

From one counts dict per certified frame:

- **total field** `p_present[i] = P(occ[i]=1)` — where the body is (any lineage).
- **parent field** `p_par[i]  = P(occ[i]=1 ∧ lbl[i]=0)`.
- **daughter field** `p_dau[i] = P(occ[i]=1 ∧ lbl[i]=1)`.  → renderer's two coloured clouds.
- **population** `pop = Σ_i p_present[i]` — true count on sim ≈ #particles; on HW the excess over the true count
  is the **spurious-birth / decoherence meter** (§1.3).
- **exclusion witness** `dbl = mean over shots of #cells with >1 particle` — structurally 0 per shot (binary
  qubit); any nonzero is a bug, so it's a cheap self-check.
- **germ witness** `⟨X^⊗W⟩` joint + separable null — unchanged from PJ2.2 (`xbasis_witness_from_counts`).

`survives` / `collapse@gen` / `k·σ` significance logic is inherited verbatim.

---

## 7. Driver + renderer

- **`code/pj_lattice_labeled.py`** — clone of `pj_lattice_vivarium.py` structure (depth scan, QRNG environment,
  selective DD on germ physical qubits only, fail-closed on HW, banked JSON to `research_runs/pj2_labeled/`).
  Modes: `solo`, `replicate` (duo is a follow-up — two founders on one shared lattice needs a second label value
  = a 2-bit label; **OQ-4**). Same `--backend/--grid/--gens/--shots/--arm` CLI.
- **`analysis/pj_lattice_render.py`** — extend: map `parent field → fields[0]`, `daughter field → fields[1]`
  (the mockup already renders two coloured fields for replicate/duo), add a **"cells N/N" carrying-capacity HUD**
  and a **population line** on the plot beside the witness. The 3-guard robustness fixes from PJ2.2 (normalize
  mode/arm to available data, skip missing arms) already cover single-mode runs.

The JSON schema stays the mockup contract (`scenarios[mode][arm] = [{fields, w, ...} per gen]`) with two extra
per-frame keys: `pop`, `dbl`.

---

## 8. Honesty invariants (CD-3/CD-4)

- **Only ⟨X^⊗W⟩ is a quantum claim.** Occupancy, label, population, and exclusion are classical readouts of a
  quantum state — reported as such.
- **Exclusion is enforced by the encoding, not discovered.** State plainly: a binary occ qubit *cannot* hold two
  particles; the *emergent* part is the carrying-capacity **dynamics** and how fast noise counterfeits population.
- **Certified integer frames only** (PJ2.2 lock); smooth playback is a labelled sim artifact.

---

## 9. Open questions

- **OQ-1 (label transport exactness):** is `CSWAP(occ[j], lbl[i], lbl[j])` the correct coherent transport under a
  *partial* hop (θ ≠ π/2), or does the label need a hop-angle-matched partial-Fredkin? Verify on a 2-cell,
  1-particle statevector: label fidelity vs θ. Fall back to θ = π/2 (full swap) if partial transport leaks.
- **OQ-2 (depth ceiling):** with the Fredkin-per-edge label cost, what's the real gen ceiling on Heron-r2? Likely
  below PJ2.2's 5–6. Measure; if <4, consider the shallow label approx.
- **OQ-3 (bud faithfulness):** shallow `CX` bud vs exact negated-control Toffoli bud — quantify the exclusion
  error of the shallow version at gen 2 (parent localization).
- **OQ-4 (duo on shared lattice):** two independent founders need label ∈ {A, B, daughter…} = a 2-qubit label
  register per cell (3× body qubits). Defer to PJ2.4 unless 3×3 solo+replicate lands with depth to spare.
- **OQ-5 (label init):** parent line = lbl 0 on seed only (all other cells lbl 0 but occ 0 = "empty", so lbl is
  don't-care on empty cells). Confirm the readout convention `P(occ=1 ∧ lbl=v)` makes empty-cell label
  irrelevant — yes, but state it in `--selftest`.

---

## 10. Verification (CD-7)

`--selftest` static checks: (i) `latl_segment_len` matches the table; (ii) hop is rxx+ryy+CSWAP only (mass
conserved on occ); (iii) exclusion — no gate can set two occ qubits from a single-particle basis state (structural);
(iv) germ witness loci isolated in the isolated arm; (v) empty-cell label is don't-care in the reduce path.
Then `--sim` runs (statevector, exact population + zero double-occupancy expected) and a written evaluation
before the developer runs the live Heron-r2 depth scans.
```
