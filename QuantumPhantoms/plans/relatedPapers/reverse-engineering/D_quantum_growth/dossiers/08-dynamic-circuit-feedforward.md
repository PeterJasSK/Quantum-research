# #08 — Dynamic-circuit feed-forward (Bäumer; Córcoles)

**Letter:** D ([`D_quantum_growth`](../README.md)) · **Priority:** ★★★ · **Kind:** quantum · **Papers:** HW05, HW06 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

<!-- The method in plain words: what problem it solves, the core idea. -->
Mid-circuit measurement plus classical feed-forward lets a constant-depth circuit do what a unitary needs linear depth for: Bäumer et al. [HW05] create long-range entanglement (and teleported CNOTs) over a heavy-hex chain by entanglement swapping with parity-controlled corrections. D-2 uses the same primitive to run a multi-generation lineage in one job: divide, measure, feed-forward the next parent, reset.

## Equations

<!-- The equations we re-implement, with symbols defined. -->
```text
Long-range Bell pair over n qubits: pairs (q0 q1)(q2 q3)...; Bell measurement (CNOT, H, measure) between neighbouring pairs;
    far end gets X^{sum b_k} Z^{sum a_k} via sequential if_test corrections; odd n: one extra SWAP. Depth O(1) (dynamic) vs O(n) (SWAP chain).
Bell fidelity (Phi+):  F = (1 + <XX> - <YY> + <ZZ>) / 4
Lineage, per generation g (inside if dead == 0):
    pair (d0,d1) = Phi+ ; fate rotation RY(0.5) on d1 + controlled RY(0.35) from the parent
    basis coin (ancilla H, measure) -> X or Z readout; fate from the pair's joint outcome:
    (0,1) rest, (1,0) necrotic -> dead flag on-chip, else divide; next parent = X^{a_g} via if_test; reset
    hidden test generation (~25 %, >= 2): per-shot coin ancillas pick CHSH settings, S = E00 + E01 + E10 - E11
Witness: <XX>_g + <ZZ>_g > 1 (3 sigma) for every non-test g; CHSH S > 2 else the run is rejected
```

## Parameters

<!-- Every parameter with its published value/range and source (paper code, section, table). -->
- Bäumer reproduction: distances n = 2…12 on a FakeMarrakesh path, 2 000 shots per basis, ideal + Heron-class noise.
- Lineage: G = 8 generations, 7 logical qubits on physical path qubits 0–6, 4 000 shots in **one** `AerSimulator.run` job, test mask from `derive_seed(seed,"D2-test-mask")` (2 of 8 generations). Fate-rotation angles 0.5 and 0.35 rad are illustrative constants (plan Q1), not fitted biology.
- DD lever: X–X echo pairs (X, delay, X) inside explicit idle windows of one measure+reset duration on the idle pair; DD off uses the same explicit delays so thermal relaxation applies in both arms.

## Paper's claimed result

<!-- The single published number or figure we will reproduce, with exact reference. -->
[HW05]: on up to 101 qubits of ibm_sherbrooke, dynamic circuits give higher CNOT-teleportation fidelity than the unitary version for chains ≳ 10 qubits (Fig. 1c); for GHZ preparation "we do not find a crossover point", genuine entanglement up to 6 qubits. Dynamic-circuit depth is constant by construction.

## Our reproduction (number + figure)

<!-- Our number vs the paper's, agreement, figure in ../figures/, run id. Quantum: label the sim mode. -->
`python -m D_quantum_growth.repro.baumer_long_range` (figure `baumer_fidelity_vs_distance.png`).

- **Simulated: ideal:** dynamic Bell fidelity = 1.0000 at every n = 2…12 (defining property reproduced); dynamic depth stays at 18–33 vs unitary 8…128.
- **Simulated: Heron-class noise (FakeMarrakesh):** dynamic F falls from 0.972 (n = 2) to 0.881 (n = 12); unitary from 0.972 to 0.890. The difference never exceeds 2 combined standard errors in dynamic's favour: **no crossover** (largest gap at n = 10: unitary 0.902 vs dynamic 0.890, −1.8σ). Published crossover ≳ 10 qubits: **not matched.** Suspect: readout error ≫ two-qubit error in the Heron-r2 noise model (this repo's QDEP finding: teleport routing does not pay off on Heron r2), plus the simulation applies no feed-forward latency.

Lineage (runs `20261029-112717-grow-ideal`, `…-112719-grow-heron`):

| mode | S_chsh | ⟨XX⟩+⟨ZZ⟩ per generation | witness passed |
|---|---|---|---|
| simulated: ideal | 2.867 ± 0.033 | 1.54 – 1.76 | yes |
| simulated: Heron-class noise (FakeMarrakesh) | 2.602 ± 0.038 | 1.40 – 1.62 | yes |

Ideal witness is below 2 by design (the fate rotation lowers 2·cos φ); the threshold is 1. S_chsh label: "certification-ready, not certified (simulated)". Forcing `--chsh-settings classical` gives S = 0.02, run rejected and logged, no seed shape (exit 3).

**DD lever** (Heron, 20 000 shots, runs `20261029-123452-lineage-heron` vs `…-123546-lineage-heron-dd`): mean witness 1.4696 (off) vs 1.4669 (on), difference −0.0027 ± 0.0060 (−0.4σ): **no measured effect**; the idle windows (~µs) are short against T₁. Reported as "no measured effect", not a gain.

## Adaptation

<!-- How it is adapted to lungs, 3-D, certification and our contracts. -->
`src/lineage.py` (one-job dynamic lineage), `src/witness.py` (⟨XX⟩/⟨ZZ⟩, CHSH, bootstrap), outputs `quantum_lineage` (claim L1), `witness_record_lineage`, `quantum_job_record_lineage`. Contract fits: `fate` is an array (one entry per generation here), the hidden mask is stored inline in the job record. The transpiler leaves `cx`/`cry` inside control-flow blocks untranslated, so the circuit is written in CZ + 1q gates. XY4 DD via `PadDynamicalDecoupling` is impossible here (the FakeMarrakesh target has no `y`, and ALAP scheduling fails on `if_else`), so X–X pairs are inserted by hand.

## Verdict

<!-- integrated | rejected (with reason). Claim level for quantum targets. -->
**dissected** (published number not matched: no crossover in simulation); the ideal defining property (constant-depth Bell pair, F = 1) is reproduced and the primitive is used for the lineage. Claim level **L1** (in-job CHSH is "certification-ready, not certified"). DD: no measured effect.

## What to reuse next

<!-- Pointers for downstream letters / INT. -->
Dynamic-circuit pattern (`if_test`, reset, per-shot coin ancillas, on-chip dead flag, one job) for any later multi-generation quantum step. INT: wire B's real founder circuit into the lineage in place of the fixed |0⟩ parent. A noise model with feed-forward latency and a larger readout budget would be needed to test the paper's crossover.
