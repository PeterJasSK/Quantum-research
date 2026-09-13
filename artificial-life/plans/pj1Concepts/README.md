# PJ1 visualization concepts — exploration before the plan

Pre-plan visual study for **PJ1** (two germ/soma organisms colliding in one environment).
Goal: find a legible way to show two organisms *interacting as if alive* — before locking the
feature plan. All prototypes are **SIM only** (throwaway); they test the *visualization*, not the
science number. Real PJ1 = W=12 per organism on Heron-r2.

## The pick

**`4_wave-bars_PICKED.html` — LOCKED (2026-09-13).** ✅

The "wave-bars" model: position **bars** per organism (additive blend → white flare on overlap =
contact) + glowing **ψ-wave envelope** + interference bloom + travelling labelled **A/B heads** with
droplines, live **genealogy** witness meter (green +1 / red on collapse) + **contact** entanglement
meter, smooth interpolated motion, and a plain-language caption narrating *approach → contact → part*.
Merge of the two models the developer liked (bars + wavefunction scope).

## All concepts (chronological)

| File | What | Verdict |
|------|------|---------|
| `1_first-preview_bars.html` | first single-panel preview, up/down bars, arm toggle | rejected — bars unclear |
| `2_gallery_4models.html` | 4 side-by-side: ridge / spacetime waterfall / creatures / scope | compare pass |
| `3_refined_3models_cells-bars-scope.html` | refined 3: living-cells / bars-v2 / scope-v2, clean traveling packets, captions | narrowed to bars + scope |
| `4_wave-bars_PICKED.html` | **bars + scope merged** — the chosen model | **PICKED** |

## Data provenance

- `gen_proto_qiskit.py` → `proto.min.json` — early qiskit statevector prototype (one-hot walker,
  W=2 germ, 5-site track). Walkers spread too fast to read → motivated the clean rebuild.
- `gen_clean_packets.py` → `clean.min.json` — **clean traveling wavepackets** used by concepts 3 & 4.
  Real single-excitation lattice walk (mathematically = the one-hot soma walker in the 1-excitation
  subspace), tuned + lengthened (L=25 sites, momentum kick) so the *approach → meet → scatter → part*
  narrative reads. Occupancy + entanglement entropy are exact; the "wrong wiring" witness-collapse
  curve is schematic.

## Locked design decisions (feed the plan)

- **Visual:** wave-bars (this dir, file 4).
- **Soma encoding:** binary position register + 1–2 trait qubits (leaner than one-hot; fits 2×W12 on-chip).
- **Interaction gate:** XX+YY exchange (energy transfer, emergent — always-on, acts only on overlap).
- **Headline output:** the live collision spectacle (wave-bars), with the 3-arm witness contrast.
- **Run target:** build + sim + live Heron-r2 run in-ticket.

Three arms throughout: **pass-through** (control) · **they interact** (soma↔soma, genealogy survives) ·
**wrong wiring** (germ-routed A/B, genealogy collapses).
