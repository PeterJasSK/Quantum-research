# #01 — Bayesian-network → circuit compiler (Low–Yoder–Chuang; Borujeni)

**Letter:** B ([`B_mapping`](../README.md)) · **Priority:** ★★★ · **Kind:** quantum · **Papers:** B01, B09, B10 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

A Bayesian network over discrete nodes is a product of conditional probability tables (CPTs). A quantum circuit can hold the same joint distribution in the amplitudes of a basis-state superposition: each node gets ⌈log₂ n⌉ qubits, a root node is loaded with a tree of Ry rotations, and a child is loaded by one Ry tree per parent-state combination, controlled on the parents' qubits. One measurement of all node qubits is then one joint sample of the network, in a single shot, with no forward-sampling loop. Low–Yoder–Chuang [B01] give the construction, Borujeni et al. [B09, B10] implement it for multi-state nodes with Toffoli-plus-ancilla controls and run it on hardware.

Our compiler (`B_mapping/src/compiler.py`) works for any contract-valid `rulebook.json`: any node count, any state count ≥ 2, any parents in topological order. Unused codes (e.g. the 4th code of a 3-state node) get probability 0. The CT context (`placement_class`) selects the `cpt_by_context` row at compile time, so context costs no qubits (B-1). B-2 puts a site register in superposition and controls the phenotype nodes on it, so one shot draws site and phenotype jointly.

## Equations

```text
Node with n states      → k = ⌈log₂ n⌉ qubits, little-endian code = state index
Binary Ry tree          → at split j, with prefix mass M₀ (bit j = 0) and M₁ (bit j = 1):
                          θ = 2·atan(√(M₁ / M₀))                    [B01, B09]
Child node              → for every parent-state combination π:  Ry-tree(P(· | π)),
                          controlled on the parent qubits with ctrl_state = code(π)
Context (B-1)           → P(· | π, c): row chosen when compiling, key = '|'.join(context values)
B-2 joint               → |site⟩ = Σ √w_s |s⟩,  w_s = P(class(s)) / n_class
                          phenotype trees controlled on the site register
Drift                   → TVD(p, q) = ½ Σ |p − q| ;  RMSPE = 100·√mean(((m − e)/e)²)  over marginals
```

## Parameters

| Parameter | Value | Source |
|---|---|---|
| Oil-stock network CPTs | P(IR=1)=0.25; P(OI=1)=0.4; P(SM=1\|IR)=0.7/0.2; P(SP=1\|OI,SM)=0.1/0.6/0.5/0.8 | [B09]. The SM and SP orderings were fixed by checking the Netica marginals 0.750 / 0.600 / 0.425 / 0.499. |
| Shots | 10 runs × 8192 | [B09] protocol |
| Lung rulebook | `tumor_type`, `size_bin` (3/6/10/20/30 mm edges), `margin` | LIDC-IDRI aggregate ratings (pylidc, 2567 nodules after the size filter), counts in `data/lidc_counts.json` |
| Context tilts | multiplicative, juxtapleural → more solid and smooth | Ahn 2010, de Hoop 2012 — **(verify)**, paper not in `../papers/` |
| Placement-class prior | free 0.33 / juxtavascular 0.45 / juxtapleural 0.22 | Ambrosini, Kostis [F01] — **(verify)** |
| B-2 sites | K = 8 (3 qubits), w = P(class) / n_class | plan Q4 |

## Paper's claimed result

Borujeni et al. [B09]: on a simulator the 4-node oil-stock network reproduces the Netica marginals with RMSPE 0.1 %; on 2020 IBM devices RMSPE is 4.9 % (Yorktown) … 36.3 % (Burlington) at optimization level 0 and 9.1–24 % at level 3. Netica marginals P(X=0): IR 0.750, OI 0.600, SM 0.425, SP 0.499.

## Our reproduction (number + figure)

Ideal (`python -m B_mapping.repro.borujeni --mode ideal`), **simulated: ideal**, 10 × 8192 shots:

| Control | RMSPE | joint TVD | depth | CZ | IR / OI / SM / SP |
|---|---|---|---|---|---|
| `mcry` | 0.36 % | 0.0041 | 208 | 57 | 0.750 / 0.599 / 0.422 / 0.498 |
| `ancilla` (Borujeni) | 0.18 % | 0.0042 | 370 | 105 | 0.748 / 0.599 / 0.425 / 0.498 |

Every marginal is within ±0.01 of Netica and RMSPE ≤ 0.5 %: **match**. We do not hit the paper's 0.1 % exactly; at 81 920 shots the shot-noise floor of this metric is ≈ 0.2–0.4 %.

Heron-class noise (`--mode heron`), **simulated: Heron-class noise (FakeMarrakesh)**, RMSPE (%) by transpiler level:

| Control | L0 | L1 | L2 | L3 |
|---|---|---|---|---|
| `mcry` | 1.70 | 0.87 | 0.82 | 0.82 |
| `ancilla` | 2.89 | 2.35 | 1.92 | 1.19 |

Figure: [`figures/borujeni_rmspe_vs_level.png`](../figures/borujeni_rmspe_vs_level.png). This is a comparison, not a match test: a 2025 Heron noise model is far better than the 2020 devices (4.9–36.3 %), so the lower drift reflects hardware progress and is not a quantum effect. Fewer gates win: `mcry` has fewer CZ than the ancilla version and lower drift at every level.

## Adaptation

- **Lung rulebook** (`data/rulebook_lung.json`): type → size → margin, context-conditioned on placement class. Rows sum to 1, validated by `shared.validate`.
- **B-1** (`python -m B_mapping.src.map --variant b1`): site context → compiled circuit → job record → decoded `TumorDraw`. Seeds are derived from the certificate's extracted seed (`B.sim`, `B.shot_select`, `B.size`, `B.shape`); same certificate → same draw. Noisy invalid codes are counted and skipped.
- **B-2** (`--variant b2`): site register 3 qubits + type 2 + size 2 + margin 2 = 9 logical qubits at K = 8 (plus up to 7 Toffoli-chain ancillas, which is the default control mode for B-2). Statevector equals the classical joint to < 1e-9. One controlled tree per *site code* instead of per class (sites of one class share identical rows) — the same distribution, more gates.
- Honest cost: the lung rulebook compiles to depth ≈ 5900 / 2000 CZ (B-1, `mcry`) and ≈ 32 000 / 11 500 CZ (B-2, 3 sites) — far beyond what Heron-class noise tolerates; see README for the drift numbers.

## Verdict

**Adapted**, claim level **L0**. B-1 is provenance only: a certified sample of a classical distribution; the classical ancestral sampler draws the same distribution at lower cost and with lower error (`drift.json` records both). B-2 is a joint lookup table classically — L0, no interference claim. Belief-propagation simulability number: pending D #9.

## What to reuse next

- `compile_rulebook`, `joint.compile_joint`, `decode.py`: D (growth) can compile its own rulebooks; INT swaps A's real `sites.json` and C's real `certificate.json` through the `--sites` / `--certificate` flags.
- B-3 (amplitude-amplified evidence inference) is only cited here: 0–1 Grover rounds are feasible on Heron.
- Reduce depth before any hardware talk: share the context across margin rows (low-rank tilt), or lift the context into a small class register instead of per-site controls.
