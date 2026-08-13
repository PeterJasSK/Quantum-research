# Perun Web Spectacles — Ideas 2 & 3
### In the style of tree.peterjas.sk — live, visual, falsifiable, presentation-ready

---

## 2. "Perun Storm"

**The hook for the audience:** *"This is genuinely how real weather
forecasting works — many possible futures run in parallel and blended
together. We're showing you a cutting-edge version of that same idea, live."*

That framing isn't just presentation flair — it's grounded in real, current
research. Real numerical weather prediction already runs **ensembles**:
many slightly-perturbed simulations of the same atmosphere, because the
underlying equations are chaotic and a single run can't capture the range of
possible outcomes. There's also an active, published research line
specifically on quantum computing for weather and climate — including a
well-known 2023 paper literally titled *"Quantum Computers for Weather and
Climate Prediction: The Good, the Bad, and the Noisy,"* plus more recent work
using quantum neural networks for cloud-cover parameterization inside real
climate models. So the framing is honest: quantum-assisted weather modeling
is a real, active field — just an early one.

### What's on screen
A live storm/weather system evolving over a map. Underneath it, the same
underlying circuit runs two ways, side by side:
- **Qaptiva (noiseless, exact, up to 40 qubits):** the storm stays sharp,
  structured, physically coherent.
- **Simulated real-hardware noise model (decoherence, crosstalk):** the same
  storm visibly degrades — loses structure, gets noisy over time.

### The falsifiable hook
Same correlation-decay measurement style as tree.peterjas.sk — plot C(d)
live for both versions. Noiseless line stays strong; noisy line decays. Put
real σ numbers on screen, not just a visual impression.

### Why it needs Perun specifically
The punchline: this is the exact problem the BAMS paper's title warns about —
noise breaking quantum weather models — and Perun's dedicated 40-qubit exact
simulator is what lets you show the *clean* version that current real quantum
hardware still can't deliver reliably. That's a defensible, cutting-edge
claim, not an oversell.

### Honest caveat (say this out loud in the talk)
Current published quantum weather research is mostly single-component pieces
(e.g. cloud parameterization) bolted onto classical models, not full quantum
weather models. Frame this as *"a live demonstration of the core noise
problem the field is actively solving,"* not *"we forecast weather with
quantum computers."* Still an impressive, true story.

---

## 3. "Perun Symphony"

**The hook for the audience:** a live generative audio-visual performance
where you can visibly watch two different kinds of compute working together
in real time — not a pre-rendered video, an actual running system.

### What's on screen
Two synced panels:
- **Left panel:** a classical neural network training live on the H200s — a
  real loss curve dropping, visualized as evolving visuals (color fields,
  shapes) and generated audio.
- **Right panel:** the quantum sampler (Qaptiva) — a small qubit-readout
  display showing live measurement outcomes feeding into the generator as
  fresh entangled variation.

### What's actually happening underneath
This is the QCBM-as-GAN-prior idea (project #7) made visible. The quantum
circuit proposes variation; the GPU-trained discriminator judges it; the
loop runs continuously, thousands of times per minute, live during the talk —
not simulated for show.

### The falsifiable hook
Run a third, muted "control" version in the corner — same GPU model, but fed
classical PRNG noise instead of the quantum sampler. Ask the audience
directly: can you tell them apart? Same honesty check as the original tree
project testing whether a difference is real or just looks real.

### Why it needs Perun specifically
It's the only one of these ideas where the GPU fleet is doing genuine heavy
lifting (real training, not rendering) *at the same time* as the quantum
simulator is in the loop — the clearest possible visual of "tightly
integrated hybrid architecture," and it's the most stage-friendly (sound +
visuals hold a room's attention in a way a chart never does).

### Honest caveat (say this out loud in the talk)
Whether the quantum-fed version is *actually better* — not just different —
than the classical-noise control is an open, testable question. The most
likely outcome (per idea #7's own bear case) is comparable quality, no clear
win. Frame it as *"watch the experiment happen live,"* not *"watch quantum
beat classical."* Same intellectual honesty that makes the original tree
project credible.

---

## Common thread across both

Both ideas follow the tree's exact winning formula:
1. Real compute underneath, not a pre-baked animation.
2. A visually alive, presentation-friendly front end.
3. A side-by-side control/baseline the audience can actually judge for
   themselves.
4. An explicit, spoken caveat about what's proven vs. what's still open —
   which is what makes the spectacle credible rather than hype.