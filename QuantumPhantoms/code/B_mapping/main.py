"""Section B: mapping. Published nodule statistics + the run's bit pool -> tumour parameters (B_mapping/roll.py).

Set CIRCUIT below; that is the only switch. "ROLL" draws the cohort and stops. Any other value draws the cohort
first (it never changes) and then runs that hypothesis circuit on the same backend; its claim goes to
<run>/claims.json and <run>/qhard/<CIRCUIT>/result.json. A hypothesis is about the device that gave the bits, never
about the tumour. The cohort needs section C's bit pool: no certificate, no bits, no tumours.

Plan: plans/qhard-R1-R5-configurations-and-BD-flagship.md. Sizes are first-run sizes; the plan's published size is
in the comment where it differs. `dry` = the sizes a dry run uses instead (small: it tests the pipeline). `refuse` = the plan's "do not build" list by backend name.
"""
from __future__ import annotations

from common import quantum as Q, runio
from common.runio import Ctx

CIRCUIT = "R5-H12"  # ROLL | R2-Q2 | R2-Q3 | R2-D4 | R2-MAP | R4-HEX | R5-H12 | R5-MAP8 | R5-D20 | R5-Y18 | B-GHZ | B-MSQ | B-KS | B-IQP

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
    "R2-MAP": _R2 | {"d": 2, "n_inputs": 2, "bound": 0.75, "rigour": "textbook [verify]", "tiles": 24, "min_pass": 20,
                     "dry": {"tiles": 3, "min_pass": 2},
                     "witness": "success of a quantum random access code on each of many qubits at once (median qubit)",
                     "pass": ">= 20 of 24 qubits above 0.75 by 3 sigma after Bonferroni"},
    # R4 information supremacy on the 12-qubit seed hexagon
    "R4-HEX": {"run": "B_mapping.xeb:run", "level": "L1'-C (n = 12)", "bound": 12.0,
               "witness": "classical-bit lower bound from the XEB score on the 12-qubit seed hexagon",
               "rigour": "bits(eps): two-point linear reading of 2509.07255 [verify]",
               "adversary": "Adversary: any one-way classical message of 12 bits; needs Haar targets, global "
                            "Clifford measurements, ONE shot per circuit; inputs: Bell-test bits of the same device "
                            "(setting-independence loophole open)",
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
    # QCAND candidates (plans/feature-QCAND-*.md): games on one chip, so "locality assumed (same chip)" in every claim
    "B-GHZ": {"run": "B_mapping.games:run_ghz", "level": "L1.5", "bound": 0.5, "n": [8, 16, 24, 32, 40], "inputs": 32,
              "dry": {"n": [4, 6]},
              "witness": "win rate of the N-player GHZ parity game on a breadth-first tree (raw counts)",
              "rigour": "1/2 + 2^-ceil(N/2) for local players on uniform inputs (2512.02284) [verify]",
              "adversary": "Adversary: N local players without communication; locality assumed (same chip)",
              "pass": "win above 1/2 + 2^-ceil(N/2) by 3 sigma (Bonferroni over sizes); the claim is the largest passing N"},
    "B-MSQ": {"run": "B_mapping.games:run_msq", "level": "L1.5", "bound": 8 / 9, "tiles": 16, "min_pass": 12,
              "dry": {"tiles": 2, "min_pass": 2},
              "witness": "win rate of the Mermin-Peres magic square game on two Bell pairs per 4-qubit path (median tile)",
              "rigour": "8/9 for local players, textbook [verify]",
              "adversary": "Adversary: two local players without communication, per tile; locality assumed (same chip)",
              "pass": ">= 12 of 16 tiles above 8/9 by 3 sigma after Bonferroni"},
    "B-KS": {"run": "B_mapping.games:run_ks", "level": "L1'-C", "bound": 4.0, "tiles": 8, "min_pass": 6,
             "dry": {"tiles": 1, "min_pass": 1},
             "witness": "chi of the sequential Peres-Mermin test on 2 qubits read through an ancilla (median tile)",
             "rigour": "chi <= 4 for noncontextual models; simulating the square needs >= log2 6 bits of memory "
                       "(2506.06869, abstract only) [verify]",
             "adversary": "Adversary: a noncontextual model of the 9 observables; compatibility and sharpness are assumed, "
                          "no dimension-free claim",
             "pass": ">= 6 of 8 tiles with chi > 4 by 3 sigma after Bonferroni"},
    "B-IQP": {"run": "B_mapping.iqp:run", "level": "L0", "bound": None, "tumours": 12, "dry": {"tumours": 2},
              "witness": "squared MMD between the cohort words sampled from a classically trained IQP circuit and the rulebook",
              "rigour": "none: no hardness claim (deep noisy IQP is classically easy, 2403.14607 [verify])",
              "adversary": "No adversary: a socket, not a separation",
              "pass": "MMD of the hardware samples below the untrained circuit's"},
}


def run(ctx: Ctx) -> None:
    from B_mapping import roll

    roll.roll(ctx)
    if CIRCUITS[CIRCUIT] is not None:
        runio.add_claims(ctx, "B", Q.run_circuit(ctx, CIRCUIT, CIRCUITS[CIRCUIT]))
