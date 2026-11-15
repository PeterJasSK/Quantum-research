"""Section B: mapping. Published nodule statistics -> circuit -> tumour parameters (the roll, B_mapping/roll.py).

Set CIRCUIT below; that is the only switch. "ROLL" is today's run. Any other value runs the roll first (it is the
seed draw and never changes) and then that hypothesis circuit on the seed register of the same backend; its claim
goes to <run>/claims.json and <run>/qhard/<CIRCUIT>/result.json. A hypothesis is about the device that drew the
seed, never about the tumour.

Plan: plans/qhard-R1-R5-configurations-and-BD-flagship.md. Sizes are first-run sizes; the plan's published size is
in the comment where it differs. `dry` = the sizes a dry run uses instead (small: it tests the pipeline). `refuse` = the plan's "do not build" list by backend name.
"""
from __future__ import annotations

from common import quantum as Q, runio
from common.runio import Ctx

CIRCUIT = "R5-H12"  # ROLL | R2-Q2 | R2-Q3 | R2-D4 | R4-HEX | R5-H12 | R5-MAP8 | R5-D20 | R5-Y18

_R2 = {"run": "B_mapping.rac:run", "level": "L1'-C",
       "witness": "average success of a quantum random access code on the hand-off register",
       "adversary": "Adversary: a classical message of the same dimension; the dimension is assumed (not "
                    "device-independent)"}
_R5 = {"run": "common.game:run", "level": "L1.5", "bound": 0.80,
       "witness": "win rate of the stabilizer-submeasurement game on the cyclic cluster state (raw counts)",
       "rigour": "[verify]: bound from 2110.04277; the win rule here is derived, not transcribed"}
CIRCUITS = {
    "ROLL": None,
    # R2 hand-off: a random access code
    "R2-Q2": _R2 | {"d": 2, "n_inputs": 2, "bound": 0.75, "rigour": "textbook [verify]", "pass": "success > 0.75 by 3 sigma"},
    "R2-Q3": _R2 | {"d": 2, "n_inputs": 3, "bound": 0.75, "rigour": "textbook [verify]", "pass": "success > 0.75 by 3 sigma"},
    "R2-D4": _R2 | {"d": 4, "n_inputs": 2, "bound": 0.625, "rigour": "textbook [verify]", "pass": "success > 0.625 by 3 sigma"},
    # R4 information supremacy on the 12-qubit seed hexagon
    "R4-HEX": {"run": "B_mapping.xeb:run", "level": "L1'-C (n = 12)", "bound": 12.0,
               "witness": "classical-bit lower bound from the XEB score on the 12-qubit seed hexagon",
               "rigour": "bits(eps): two-point linear reading of 2509.07255 [verify]",
               "adversary": "Adversary: any one-way classical message of 12 bits; needs Haar targets, true-random "
                            "inputs, global Clifford measurements, ONE shot per circuit",
               "n": 12, "layers": 8, "circuits": 16, "train_iters": 40, "shots_each": 1,       # plan: 86 layers, 10000
               "dry": {"layers": 2, "circuits": 4, "train_iters": 5},
               "pass": "proven bits > 12", "refuse": {"marrakesh": "forecast eps 0.14 < 0.16"}},
    # R5 cluster-state game on hexagons / rings
    "R5-H12": _R5 | {"n": 12, "tiles": 1, "inputs": "all", "dry": {"inputs": 8}, "pass": "win > 0.80 by 3 sigma",
                     "adversary": "Adversary: depth-1 local classical circuits only"},
    "R5-MAP8": _R5 | {"n": 12, "tiles": 8, "inputs": "all", "min_pass": 6, "dry": {"tiles": 2, "min_pass": 2, "inputs": 8}, "pass": ">= 6 of 8 hexagons above 0.80 by 3 sigma",
                      "adversary": "Adversary: depth-1 local classical circuits, per hexagon"},
    "R5-D20": _R5 | {"n": 20, "inputs": 32, "dry": {"n": 12, "inputs": 4},      # plan: 64 inputs
                     "pass": "win > 0.80 by 3 sigma",
                     "adversary": "Adversary: depth-3 local classical circuits IF the general-even-n bound holds (G3)"},
    "R5-Y18": _R5 | {"n": 20, "spacers": 2, "inputs": 32, "dry": {"n": 12, "inputs": 4}, "pass": "win > 0.80 by 3 sigma",
                     "adversary": "Adversary: depth-3 circuits under Theorem 1 (n = 18), IF it survives two helper qubits"},
}


def run(ctx: Ctx) -> None:
    from B_mapping import roll

    S = roll.roll(ctx)
    if S <= 2:
        Q.log(f"CHSH S = {S:.3f} <= 2: draw rejected, no seed, no retry")
        return
    if CIRCUITS[CIRCUIT] is not None:
        runio.add_claims(ctx, "B", Q.run_circuit(ctx, CIRCUIT, CIRCUITS[CIRCUIT]))
