# Conclusion: entanglement-correlation study

**Status:** Phase 1 complete + partial Phase 2 (C sweep, serial entangler).
**Date:** 2026-07-16
**Companion docs:** `STUDY_ENTANGLEMENT_CORRELATION.md` (design),
`RUNBOOK_ENTANGLEMENT_CORRELATION.md` (execution log).
**Data:** `QuantumLife/research_runs/*_summary.json`.

---

## 1. What this research was trying to prove

The QuantumTree art project runs a genuine 108-qubit circuit every generation,
but the only quantity it ever measured was **per-qubit diversity** (mean binary
entropy). Diversity is blind to entanglement: 108 independent biased coins give
the same diversity as 108 maximally-entangled qubits. So nothing in the art
pipeline could tell "quantum" apart from "classical noise with a quantum logo."

This study set the smallest honest, falsifiable claim the hardware can support:

> When we grow the tree on real hardware, does the neighbour-entangling layer
> (CX ladder + controlled-Rx of angle `CROSS_ANGLE` down a qubit chain) leave a
> **spatial correlation signature** in the measured genome bits that the
> classical, no-entanglement `--sim` surrogate **cannot** reproduce?

If yes: the quantum connection does real, measurable work — not just supplying
randomness a PRNG could fake. If no: it is a random-number-driven L-system with
a quantum-flavoured logo, and we say so plainly.

**Metric.** Connected two-point correlation along the chain:

```
C(d) = mean_i [ <b_i b_{i+d}> - <b_i><b_{i+d}> ]
c(d) = C(d) / C(0)                 (normalised, c(0)=1)
xi   = sum_{d>=1} c(d)             (integrated correlation length)
```

`C(d)=0` for all `d>0` is the null (independent qubits = classical surrogate).
`C(d) > noise`, decaying with `d`, is the fingerprint of surviving correlation.

**Three arms carry the proof:**
- **A — classical null (`--sim`):** no entangler. Predicts `xi ≈ 0`, flat `c(d)`.
- **B0 — hardware control (`--layers 0`):** encode + measure, no entangling
  gates. Any `c(d)` here is pure device/readout artefact. This is the floor we
  subtract, so a signal is never compared against literal zero.
- **B — hardware main (`--layers 2`):** entangler on, same seeds/environment as
  A. Difference vs A and B0 is attributable to the entangling chain.

Plus **C** — an entanglement dose–response sweep (`--layers 0,1,2,4`) to test
whether the effect grows with entangling depth (causal), not luck.

---

## 2. Results

Means over generations (3 seeded repeats, 4096 shots, `ibm_kingston`):

| Arm | Layers | c(1) | c(2) | xi | Reading |
|-----|--------|------|------|-----|---------|
| A — sim null | 2 | 0.000 | 0.000 | +0.000 | flat, floor σ≈0.008 — baseline behaves |
| B0 — hw control | 0 | +0.015 | 0.000 | +0.017 | weak +, dies at d=1 — readout floor |
| **B — hw main** | **2** | **−0.077** | **+0.040** | **−0.031** | strong **alternating** structure |
| C_L0 | 0 | +0.020 | 0.000 | +0.019 | = control |
| C_L1 | 1 | +0.019 | −0.002 | +0.015 | = control |
| C_L2 | 2 | −0.071 | +0.038 | −0.030 | flips — reproduces B |
| C_L4 | 4 | +0.012 | −0.050 | +0.043 | noisy, σ_xi=0.042 — degraded |

**Significance of the hardware c(1) signature (L=2):**
- vs classical sim: **z = −9.9**
- vs hardware readout control: **z = −10.6**

Both far past the 3σ bar. The signature is not finite-shot noise and not a
readout artefact.

**Dose–response is causal.** L0 and L1 look identical to the L0 control (weak
`+0.02`, dies immediately). At **L2 the sign flips** to a strong staggered
pattern (`c(1)<0`, `c(2)>0`). Turning the entangler up is what produces the
structure. By L4 the signal is swamped by scatter (σ_xi ≈ 0.042) — consistent
with the NISQ story that deeper circuits add more two-qubit-gate error than
correlation.

**Diversity stays comparable across arms** (0.86 sim vs 0.93–0.98 hw) while
`c(d)` differs by ~10σ — so the effect is *correlation between bit positions*,
not a shift in per-bit bias. That was the whole point.

---

## 3. What is proven — and what is not

**Proven:**
1. **Not PRNG art.** The classical surrogate produces flat `c(d)=0`. The
   hardware produces structure it cannot reproduce, at z≈10. The connection is
   doing measurable work a PRNG cannot fake.
2. **Not a readout artefact.** The `--layers 0` hardware control gives only a
   weak `+0.015` that dies at d=1. Switching the entangler on flips `c(1)` to
   `−0.077` with a staggered `c(2)>0` tail. The entangling gates *cause* the
   signal.

**Not yet proven — entanglement specifically.** The serial entangler lays the
CX/CRX bonds one gate at a time down 108 qubits, so each sweep is ~107 deep and
`--layers 2` reaches ~800 logical depth — well past Heron's coherence budget.
At that depth the measured `c(d)` may be **decoherence and coherent crosstalk
structure rather than surviving entanglement correlation.** The alternating
`c(1)<0, c(2)>0` shape is as consistent with a coherent-error / crosstalk
pattern from the serial ladder ordering as with a genuine entanglement decay.
Origin is confounded with circuit depth.

**Metric caveat.** `xi` is a poor headline number for *this* signal. Because
the signature alternates sign, the sum `xi = Σ c(d)` partially cancels: it
reads a tiny `−0.03` while the real effect lives in `|c(1)| ≈ 0.077`. Future
summaries should headline `|c(1)|` (or a staggered sum `Σ (−1)^{d+1} c(d)`),
not `xi`. The runbook decision rule keyed on `xi > 0.024` would have missed
this.

---

## 4. Conclusion

The study achieved its primary goal: it **rules out the deflationary reading of
the art project.** The QuantumTree genome carries spatial structure that neither
a classical no-entanglement surrogate nor a no-entangler hardware control can
produce, at ~10σ, and that structure is causally switched on by the entangling
layer. So the "quantum connection" is more than decoration and more than readout
noise — it is real, device-produced, tunable structure.

It has **not** yet earned the stronger claim of *entanglement*. The serial
circuit is too deep for the entangled state to survive to measurement, so the
observed correlation cannot be cleanly separated from decoherence and crosstalk.
Until that confound is removed, the honest statement is: **"the entangling layer
imprints a measurable, causal correlation signature absent from the classical
model" — not "we observe entanglement."**

---

## 5. Brick-wall redesign is required to prove entanglement

To convert the causal-signal result into an entanglement result, the circuit
depth must drop below the coherence cliff so the entangled state is still alive
when we measure it. That is the brick-wall redesign (`research_qtree_brickwall.py`):

- **Serial (current):** `cx(0,1), cx(1,2), cx(2,3)...` — adjacent gates share a
  qubit, run one at a time → ~107 deep per sweep, ~800 logical depth at L2.
- **Brick-wall:** even bonds `(0,1)(2,3)(4,5)...` fire together (depth 1), then
  odd bonds `(1,2)(3,4)...` fire together (depth 1). Every neighbour bond
  `(i,i+1)` is covered exactly once per sweep — **identical physics, ~50× less
  depth** (depth 2 per sweep instead of ~107).

**Decisive test.** Run the brick-wall entangler at matched `--seed` and
`--layers` against the serial version (`--entangler brickwall` vs `serial`),
plus its own `--sim` null and `--layers 0` control:

- **Signature persists (and decays cleaner / more monotonically):** the
  correlation survives a coherence-preserving circuit → it is real entanglement.
  H1 confirmed, entanglement claim earned.
- **Signature vanishes or changes shape:** the serial signal was decoherence /
  crosstalk. The entanglement claim is withdrawn; the serial C(d) is reported as
  a device-noise structure, not entanglement.

**Until the brick-wall A/B is run, the entanglement claim stays open.** The
brick-wall arms are not optional polish — they are the experiment that decides
whether "measurable quantum structure" (proven) becomes "measurable
entanglement" (not yet proven).

### Action items
1. Run brick-wall arms: `--sim` null, `--layers 0` control, `--layers 1/2/4`
   main — matched `--seed 100`, `--repeats 3`, `--shots 4096`.
2. Re-summarize all arms on `|c(1)|` / staggered sum, not `xi`.
3. Overlay `c(d)` decay: serial-hw vs brick-wall-hw vs sim; plot `|c(1)|` vs
   `--layers` for both entanglers.
4. Update the runbook decision rule to key on `|c(1)|` above the sim floor,
   B0-subtracted.

  for L in 1 2 4; do                                                                                                                                                                                                                                                
    python code/research_qtree_brickwall.py --generations 6 --shots 4096 --seed 100 --repeats 3 --layers 2 --entangler brickwall --backend ibm_kingston --name bw_C_L2L                                                                                                                                                                                                                      
  done