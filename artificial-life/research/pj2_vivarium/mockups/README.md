# PJ2 Vivarium — 2D visualization mockups

Three saved iterations of "one quantum organism living in a small 2D space," plus the honest
account of how they were made and what it would take to run them on a real quantum computer.

All three are **self-contained HTML** (no network, no build). Open in a browser. Data is a
deterministic **statevector-simulation mock** produced by
`../mock/mock_3x3_scenarios.json` / `mock_2d_scenarios.json` (generators:
`scratchpad/gen_scenarios.py`). Nothing here has run on hardware yet — that is the point of the
"what needs to be worked out" section below.

## The files

| File | Grid | Motion style | Notes |
|------|------|--------------|-------|
| `vivarium_4x4_scenarios.html` | 4×4 (16 cells) | additive-glow field, centroid nucleus | The last 4×4 iteration. Sits at the top edge of laptop statevector. |
| `vivarium_3x3_snap.html` | 3×3 (9 cells) | **superposition cloud + body that snaps to the dominant cell** | Discrete localization — body holds, then jumps with overshoot + trail when the argmax cell flips. |
| `vivarium_3x3_smooth.html` | 3×3 (9 cells) | superposition cloud + body that **glides at the probability centroid** | Continuous complement to the snap version. |

Each has three **scenarios** (Solo / Replicate / Two organisms) and two **arms**
(Isolated germ line / Coupled = barrier broken), plus a witness-vs-generation plot and a `Ψ`
toggle that exposes the raw per-cell probabilities.

## How it was done

### 1. The model (what the numbers are)
- The habitat is a small square lattice (3×3 or 4×4). The organism is an **occupancy field**:
  one number per cell, the per-site probability ⟨n⟩ that a statevector run would report.
- **Movement** is a discrete-time quantum walk: each generation the field hops to von-Neumann
  neighbours with a directional bias, `stay = 0.42`, mass conserved. Nothing is scripted — position
  is just where probability flows. (Earlier drafts also had eating/energy/budding; those were cut
  as overclaiming. The honest scope is **movement + witness only**.)
- **Replicate**: at generation 2 the germ line is copied into a daughter (a CNOT clone in the real
  model), doubling the organism into parent + daughter that share **one** genealogical witness.
- **Two organisms**: two fields seeded at opposite corners drift together; their spatial `overlap`
  builds a joint two-body witness.
- **Witness** ⟨X<sup>⊗W</sup>⟩ (W = 3) is the one quantum claim. In the **isolated** arm it decays
  gently with depth but stays above the certified line (0.15); in the **coupled** arm the mortal
  body is wired back into the germ line and the witness collapses. The decay-with-depth is exactly
  why ~5–6 generations is the ceiling.

### 2. The rendering (what is real vs. drawn)
- **Real**: the cloud (per-cell ⟨n⟩), the witness value, the mass, the overlap — all straight from
  the mock's statevector-shaped snapshots. The `Ψ` view prints these numbers.
- **Reading aid**: the bright "body." In the *snap* build it marks the **dominant cell** (argmax)
  and jumps when that changes (`easeBack` overshoot + a short motion trail), the way a measurement
  localizes a superposition. In the *smooth* build it sits at the **centre of mass** and glides.
  In the *4×4* build there is no cloud/body split — the field is drawn as one additive glow with a
  nucleus at the centroid.
- **Artistic**: the bioluminescent glow, gold membrane rim, and the interaction bond are styling on
  top of true values. Aesthetic lineage: cryo-EM of ultra-small bacteria; Haeckel; Andy Lomas.
- Frames between integer generations are **linear interpolation** for smooth playback. On hardware
  those in-between frames do not exist (see below).

### 3. The data contract
```
scenarios[mode][arm][gen] = {
  fields : [ occ[C], ... ]   # C = cells; 1 field solo, 2 for replicate/duo
  w      : number            # ⟨X^⊗W⟩ witness
  overlap: number            # duo only
}
endpoint[mode][arm] = { w, survives }
```

## What needs to be worked out to run these on a quantum computer

The mockups are **classical statevector simulations** dressed as life. Making them *actually
quantum* — i.e. the cloud and witness coming off a QPU — requires solving each of these:

1. **Encoding the space into qubits.** The 2D field has to become a register.
   - Unary/one-hot (one qubit per cell): 9 qubits for a 3×3 body, 16 for 4×4. Simple hops, but
     expensive in qubit count.
   - Binary encoding (⌈log₂ cells⌉ qubits): 4 qubits for 9 cells, but the walk operator becomes a
     dense, hard-to-compile unitary.
   The unary scheme matches the existing `pj_qalife.py` vivarium register layout and is the honest
   starting point.

2. **Qubit budget (the reason 3×3 wins).** Roughly `body + witness (W=3) + ancillas`, doubled for
   replicate/duo:
   - 3×3 solo ≈ 9 + 3 ≈ **12 qubits** — comfortable on sim and on hardware.
   - 3×3 duo / replicate ≈ **20–24 qubits** — fine on hardware, near the laptop statevector edge.
   - 4×4 solo ≈ 16 + 3 ≈ 19; 4×4 duo ≈ **~35 qubits** — past laptop statevector (2³⁵ amplitudes),
     needs MPS/tensor-network sim or a real device. This is why 3×3 is the sweet spot.

3. **The walk as a real Hamiltonian.** Movement must come from Trotterizing one fixed local
   Hamiltonian (excitation-conserving `rxx + ryy` hops between neighbouring cells), not from
   `if(...)` logic. Each generation = one Trotter layer = a stack of two-qubit gates.

4. **Depth is the scarce axis (~5–6 generations).** Every generation adds gate depth; two-qubit
   gate error and T1/T2 decoherence eat the witness. On IBM Heron-class hardware the witness has
   been seen to survive idle but collapse under a full life cycle by a handful of steps. Pushing the
   ceiling needs: fewer/cheaper 2-qubit gates per step, dynamical decoupling on idle qubits, and
   error mitigation. **Readout error now dominates 2-qubit error on modern hardware**, so the
   witness (which needs an X-basis rotation + parity read) is more fragile than the occupancy
   (diagonal, cheap to read).

5. **There is no movie on hardware.** A real device measures **once**, at one terminal depth — the
   circuit is measured, collapsed, done. To get honest "frames" you run a **depth scan**: separate
   circuits at depth 1, 2, …, 5, each measured with many shots; each yields an occupancy histogram
   (the cloud) and a witness estimate (with a separable-null baseline). Stitching those certified
   snapshots is legitimate; a continuous interpolated movie is not — it is a sim artifact. Label it
   accordingly.

6. **Measuring the two observables.**
   - Occupancy ⟨n⟩ per cell: computational-basis measurement, straightforward.
   - Witness ⟨X<sup>⊗W</sup>⟩: rotate the W germ-line qubits into the X basis, measure parity,
     subtract the separable-null baseline, and take `signal > k·σ` as "certified." Needs enough
     shots for the error bars.

7. **Replication with the Weismann barrier.** The CNOT clone of the germ line needs extra qubits and
   qubit connectivity, and the discipline that **no gate ever couples soma → germ** (that is the
   `coupled` arm's deliberate violation). Verifying isolation is a static circuit check.

8. **Two organisms + interaction.** Doubles the register and adds interaction gates
   (`rxx + ryy` between co-located body sites of A and B). On a device with limited connectivity this
   means SWAP/routing overhead, which adds depth — directly fighting the ~5-generation ceiling.

9. **Emergence discipline.** Everything (walk, replication, interaction) must fall out of evolving
   one fixed `H_viv`, applied `steps` times. No per-step scripting. This keeps the "it just does
   this" claim honest.

### Minimal honest first hardware run
3×3 **solo**, unary body (9q) + W=3 witness (12q total), a **depth scan** from 1 to 5 generations,
each circuit measured for occupancy + witness with a separable-null control. That produces a real
"organism that moves in space, with a witness that survives or collapses" — the truthful version of
these mockups — without any of the overclaiming.
