# Quantum Tree — full pipeline from code

Step by step — genome build, measure, interpret.

## Genome layout — what a "genome" is

102 qubits = **17 slots × 6 bits** (`genome.py`). One slot = one branch decision:

| bits | field | meaning |
|------|-------|---------|
| 0,1 | angle 0–3 | branch bend vs parent |
| 2,3 | length 0–3 | segment length |
| 4 | fork | 1 = split in two |
| 5 | leaf | 1 = leaf cluster (branch keeps growing) |

**One shot = one full 102-bit string = one complete field of 17 branch decisions.** Circuit fired many shots per generation (up to 16384).

## Build — one generation circuit (`build_circuit`, 6 stages)

Registers: `q` (102 genome) + `a` (2 per bond, teleport ancillas) + `c` (genome readout) + `tel` (ancilla readout).

1. **Belief encode** — `Ry(theta[i])` each qubit. Start `theta = π/2` everywhere = fair coin, tree fully undecided (`:453`).
2. **Local entangle** — `layers` brick-wall neighbour passes: `CX(i,i+1)` + `controlled-Rx(0.7)`. Correlates adjacent genes (short-range).
3. **Long-range teleport CX** — for each bond slot `si→sj`, apply `CX` between their **angle bit-0 qubits** (`qi=si*6`, `qj=sj*6`) via teleportation (`_teleport_cx :201`):

   ```
   H(a1); CX(a1,a2)        # Bell pair spans the gap
   CX(ctrl,a1); measure a1->tel   # inject control parity
   if tel: X(a2)                  # feed-forward
   CX(a2,tgt); H(a2); measure a2->tel
   if tel: Z(ctrl)                # feed-forward
   ```

   ctrl and tgt **never physical neighbours**. Constant depth regardless of gap.
4. **Environment bias** — `Rx(angle_bias)` on angle bits, `Ry(season_bias)` on length/fork bits, plus `FORK_BIAS=0.3`, `LEAF_BIAS=0.45`. Wind/season lean growth.
5. **Self-mutation kicks** — `Rx(kick[i])`, kick carried from previous generation (`:270`).
6. **Collapse** — `measure(q→c)`. Each shot = one genome (`:275`).

## Measure — shots to numbers (`field_stats :288`)

- **`p[i]`** = fraction of shots where bit `i`=1 → the **per-qubit frequency**, what belief learns from.
- **`modal`** = single most-frequent 102-bit string → stored as `bits`, the tree you actually see that gen.
- **`samples`** = next 4 frequent strings.
- **`diversity`** = mean binary entropy of `p` → how undecided (1=coin, 0=locked).

**Heralded runs** (`:476`): keep only shots where all `tel` ancilla bits = 0 (correctly-teleported branch, ~25% per bond). Filter uses **ancilla bits only, never genome bits** → valid noise filter, not selection bias.

## Interpret — two readings

**A. Research metric (correlation):**

- `two_point_correlation :298` — chain average `C(d)=mean_i[⟨b_i b_{i+d}⟩ − ⟨b_i⟩⟨b_{i+d}⟩]`, `c(d)=C(d)/C0`, `xi=Σc(d≥1)`.
- `bond_correlations :327` — at **exact bonded angle qubits**: `conn=⟨b_qi b_qj⟩ − ⟨b_qi⟩⟨b_qj⟩`, `c_at_d = conn/C0`. This is the **crosstalk-immune long-range signal** (the headline `−0.065`) (best run `-0.116 `) . Classical `--sim` null = ~0; hardware nonzero at bond distance = entanglement signature crosstalk cannot fake.

**B. Evolution (belief carried to next gen, `next_belief :349`):**

```
drift = 0.18*(2p-1)      # nudge theta toward measured habit (heredity)
wig   = uniform(-0.05,0.05)   # jitter (variation)
theta_next = clamp(theta+drift+wig, 0.08, π-0.08)
kick_next  = 0.30*(2p-1)      # next-gen self-mutation
```

Belief locks onto its own habit → entropy falls over generations → tree crystallizes. Heredity + variation + environment = evolution, not fresh random each frame.

## Interpret — tree render (`buildTree` JS in index.html)

Per generation, decode `modal` bits → 17 slots → `{bend = angle/3*2−1 ∈[−1,1], length = 0.4+len/3*0.6, fork, leaf}`. Walk generations as growth steps: each tip bends by `slot.bend*MAXBEND + windLean`, length scaled by season, `fork` splits tip in two, `leaf` sprouts, stop at `MAXDEPTH`. Slot picked per tip = `(k+g)%17`.

**Loop:** encode belief → run chip → measure `p`+modal → correlation metric + draw modal → reinforce belief → next gen. run.json stores every gen's `bits`/`p`/`correlation`/`bonds`/`env`; viewer replays as the film.
