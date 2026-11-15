"""Section D: quantum growth. What the quantum computer does at the start of each tumour's growth.

Set CIRCUIT below; that is the only switch. Every circuit runs on the run's backend (or the local fake in a dry
run), writes <run>/qhard/<CIRCUIT>/result.json and its claims. DSCALE, CH-QCA and the R6 rings also write per-tumour seed
shapes (<run>/dscale/seed_shapes.npz); with any other circuit section E grows from the 2 mm ball.

Plans: plans/qhard-D-L2-ring-configurations.md, plans/qhard-R1-R5-configurations-and-BD-flagship.md. Sizes below
are first-run sizes; the plan's published size is in the comment where it differs. `dry` = the sizes a dry run
uses instead (small: it tests the pipeline). `refuse` is the plans'
"do not build" list: a circuit is not run on a backend whose name contains that fragment.
"""
from __future__ import annotations

from common import quantum as Q, runio
from common.runio import Ctx

CIRCUIT = "R3-TEST"  # DSCALE | GHZ-SPINE | CH-QCA | PMD-BANK | R1-STAR-001 | R1-TILE24 | R1-M2-00001 | R3-LADDER | R3-TEST | R3-CHIP64 | R3-INTRINSIC | R5-LADDER | R6a-S36 | R6a-S44 | R6b-LEAN64 | R6b-PUB64 | L2-BAND

_R1 = {"run": "D_quantum_growth.clock:run", "level": "L1'-T", "bound": 0.29641,
       "rigour": "computer-certified upper bound 0.29641 for 2-state machines, attained value 8/27 (2005.04241 Table 3) [verify]",
       "witness": "p(sequence 001) of a one-qubit division clock", "memory_qubits": 1, "seq": "001",
       "adversary": "Adversary: every one-bit classical clock; the memory is assumed to be one qubit"}
_R3 = {"run": "D_quantum_growth.pairs:run", "level": "L1'-L", "bound": 2.0, "channel": "programmed",
       "rigour": "memoryless per-qubit sample overhead 2 [verify; gap G3]",
       "adversary": "Adversary: every learner without a quantum memory (a theorem, no baseline arm is run)"}
_R6 = {"run": "D_quantum_growth.ring_l2:run", "bound": 0.0,
       "dry": {"n": 12, "depth": 6, "t": [0, 4], "n_anc": 2, "m_dfe": 2},
       "witness": "lower bound on the sample fidelity (DFE on the Clifford reference, accepted shots)",
       "rigour": "certificate formula not transcribed from 2607.25941 [verify]; doping loss is a placeholder",
       "adversary": "Adversary: any classical sampler (conjectured: cut entropy >= 27 and t >= 200); about the device, "
                    "never the tumour"}
CIRCUITS = {
    # today
    "DSCALE": {"run": "D_quantum_growth.dscale:run"},
    # the three families of DSCALE, each alone on the chip (first pick of the qubits, nothing running next to it)
    "GHZ-SPINE": {"run": "D_quantum_growth.dscale:run", "families": ["ghz-spine"],
                  "request": {"n": 14, "checks": 0, "by_cost": True},     # heavy-hex: a tree this shallow has no check
                  "dry": {"request": {"n": 8, "checks": 0, "by_cost": True}}},
    "CH-QCA": {"run": "D_quantum_growth.dscale:run", "families": ["ch-qca"], "request": {"n": 30},
               "dry": {"request": {}}},
    "PMD-BANK": {"run": "D_quantum_growth.dscale:run", "families": ["pmd-bank"], "circuits": 27,
                 "dry": {"circuits": 3}},
    # R1 temporal memory: a degree-3 qubit is the clock's memory, its 3 neighbours the outputs
    "R1-STAR-001": _R1 | {"tiles": 1, "identical_steps": [True, False], "pass": "p > 0.29641 by 3 sigma"},
    "R1-TILE24": _R1 | {"tiles": 24, "identical_steps": [False], "min_pass": 20, "dry": {"tiles": 3, "min_pass": 2},
                        "pass": ">= 20 of 24 tiles pass at 3 sigma after Bonferroni"},
    "R1-M2-00001": _R1 | {"memory_qubits": 2, "seq": "00001", "tiles": 1, "restarts": 4,      # plan: 12 restarts
                          "dry": {"restarts": 1},
                          "level": "L1'-T (4-state adversary)", "bound": 0.328,
                          "witness": "p(sequence 00001) of a two-qubit clock",
                          "rigour": "published form ((L-1)/L)^L [verify]; quantum value is an own numerical optimum",
                          "pass": "cannot pass before gap G1 is closed"},
    # R3 learning with a sister memory: Bell pairs, hidden full-weight Pauli
    "R3-LADDER": _R3 | {"pairs": [8, 16], "instances": 8,                                    # plan: 8..64 pairs, 24
                        "dry": {"pairs": [4, 8], "instances": 2},
                        "witness": "fitted per-qubit sample overhead 1/r^2 of Bell-memory Pauli learning",
                        "pass": "fitted overhead < 2 by 3 sigma"},
    "R3-CHIP64": _R3 | {"pairs": [64], "instances": 32, "dry": {"pairs": [8], "instances": 2},
                        "witness": "hidden full-weight Pauli sign on 64 selected Bell pairs (128 qubits)",
                        "pass": "hidden Pauli sign recovered at 5 sigma and overhead < 2"},
    "R3-TEST": _R3 | {"channel": "test", "pairs": [8, 16, 24, 32, 40], "pool": 400, "trials": 200,
                      "dry": {"pairs": [4, 8], "pool": 24, "trials": 40},
                      "witness": "success rate of naming the hidden Pauli channel with a sister memory (hypothesis test)",
                      "rigour": "1/2 + 0.43 M 2^-n without a quantum memory (2408.03376 Eq. 4) [verify]; emulated channel",
                      "pass": "success above the no-memory bound by 3 sigma at some n >= 4"},
    "R3-INTRINSIC": _R3 | {"channel": "intrinsic", "ring": 12, "pairs": 6, "instances": 8,    # plan: 64-ring, 32 pairs
                           "dry": {"instances": 2},
                           "witness": "Pauli rates of the ring's own twirled CZ layer",
                           "pass": "calibration (noise model for R6)"},
    # R5 loss meter for R6
    "R5-LADDER": {"run": "common.game:run_ladder", "level": "calibration", "bound": None, "rigour": "none",
                  "witness": "effective loss per CZ, lambda = -ln F_n / N_CZ, from the game score",
                  "n": [12, 20], "inputs": 16,                                                # plan: 12..44, 32 inputs
                  "dry": {"n": [12], "inputs": 4},
                  "adversary": "No adversary: a loss meter", "pass": "none (calibration)"},
    # R6 deep T-doped ring with ancilla checks: the L2 attempt (L2 stays blocked)
    "R6a-S36": _R6 | {"level": "L2 protocol, below threshold", "n": 36, "depth": 22, "t": [0, 5, 40], "n_anc": 8,
                      "m_dfe": 8, "pass": "bound > 0 at 95 %"},                               # plan: m_dfe 24
    "R6a-S44": _R6 | {"level": "L2 protocol, below threshold", "n": 44, "depth": 26, "t": [0, 5, 60], "n_anc": 10,
                      "m_dfe": 8, "pass": "bound > 0 at 95 %"},
    "R6b-LEAN64": _R6 | {"level": "NOT hard: depth-36 ring contracts exactly at ~2^48 (2608.13110)", "n": 64, "depth": 36, "t": [0, 200], "n_anc": 12,
                         "m_dfe": 8, "min_entropy": 27, "min_t": 200,                         # plan: m_dfe 40
                         "pass": "bound > 0 at 95 % with min cut entropy >= 27 and t >= 200",
                         "refuse": {"marrakesh": "acceptance 5e-5: the reference alone needs ~20 h",
                                    "kingston": "ring readout error 2.6 %"}},
    # L2 attempt on a 2-D patch, no post-selection: half the CZ of a ring for the same classical cost (band_l2.py)
    "L2-BAND": {"run": "D_quantum_growth.band_l2:run", "level": "L2 attempt (raw fidelity)", "bound": 0.0,
                "witness": "lower bound on the raw sample fidelity (DFE on the Clifford reference, no post-selection)",
                "rigour": "placeholder doping loss; hardness = cost ledger of known exact methods (2608.13110)",
                "adversary": "Adversary: exact tensor-network sweep, statevector, stabilizer decomposition (>= 2^73 each)",
                "n": 72, "width": 60, "t": 300, "min_t": 200, "m_dfe": 16, "mirrors": 4,
                "dry": {"n": 12, "width": 8, "t": 4, "m_dfe": 1, "mirrors": 1},
                "pass": "bound > 0 at 95 %, ledger hard, t >= 200",
                "refuse": {"marrakesh": "forecast raw fidelity ~1e-5: the reference needs > 1e9 shots"}},
    "R6b-PUB64": _R6 | {"level": "L2 (published reference)", "n": 64, "depth": 73, "t": [0, 314], "n_anc": 12,
                        "m_dfe": 8, "min_entropy": 27, "min_t": 200, "pass": "as published",
                        "refuse": {"marrakesh": "acceptance ~4e-9", "kingston": "ring readout error 2.6 %"}},
}
HONEST = ("the seed shape is a quantum snapshot measured on the device; growth and image are classical; every claim "
          "names its adversary; a certificate is about the device, never the tumour")


def run(ctx: Ctx) -> None:
    claims = Q.run_circuit(ctx, CIRCUIT, CIRCUITS[CIRCUIT])
    runio.add_claims(ctx, "D", claims)
    s = Q.session(ctx)
    runio.save_json(ctx.path("dscale", "dscale_run.json"),
                    {"circuit": CIRCUIT, "target": s.target.name, "target_label": s.target.label,
                     "sim_label": claims[0]["label"] if claims else s.label(), "honest_label": HONEST})
